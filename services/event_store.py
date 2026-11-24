"""
services/event_store.py
行程資料的單一來源（Single Source of Truth）。

- Google Calendar 為唯一資料來源；寫入成功後才更新本地清單，使用 Google 回傳的 id。
- 所有網路呼叫經由 runner 在背景執行緒執行（預設 ThreadPoolRunner，單一執行緒序列化），
  結果以 Qt signal 在主執行緒回報，不阻塞 UI。
- 失敗一律以 operation_failed 通知 UI，不可只寫日誌。
- 日誌不記錄行程標題等個資，僅記錄 id 與操作種類。
"""

import os
import socket
import threading
from datetime import date

import httplib2
from google.auth.exceptions import RefreshError, TransportError
from googleapiclient.errors import HttpError
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, Qt, pyqtSignal

from services import event_mapping as mapping
from services import google_client
from utils.logger import get_logger
from utils.paths import CREDENTIALS_PATH, TOKEN_PATH

logger = get_logger(__name__)

NOT_AUTHORIZED_MESSAGE = "尚未連線 Google 日曆，請先到設定頁授權"
NETWORK_MESSAGE = "網路連線逾時或離線"


class _JobSignals(QObject):
    done = pyqtSignal(object)
    failed = pyqtSignal(object)  # Exception


class _Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = _JobSignals()  # 在主執行緒建立 → affinity 為主執行緒

    def run(self):
        try:
            result = self.fn()
        except Exception as e:
            self.signals.failed.emit(e)
            return
        self.signals.done.emit(result)


class ThreadPoolRunner:
    """在專屬 QThreadPool（最多 1 條執行緒）執行 fn，callback 回到建立者（主）執行緒。"""

    def __init__(self):
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(1)
        self._jobs = set()

    def __call__(self, fn, on_success, on_error):
        job = _Job(fn)
        job.setAutoDelete(False)
        self._jobs.add(job)

        def finish(callback, value):
            try:
                callback(value)
            finally:
                self._jobs.discard(job)

        job.signals.done.connect(
            lambda r: finish(on_success, r), Qt.ConnectionType.QueuedConnection
        )
        job.signals.failed.connect(
            lambda e: finish(on_error, e), Qt.ConnectionType.QueuedConnection
        )
        self._pool.start(job)

    def shutdown(self):
        self._pool.clear()
        self._pool.waitForDone(2000)


class DaemonThreadRunner:
    """每次呼叫開一條 daemon 執行緒執行 fn（用於可能長時間阻塞的 OAuth），
    不占用 ThreadPoolRunner 的執行緒，也不會卡住程式結束。callback 回到建立者（主）執行緒。"""

    def __init__(self):
        self._jobs = set()

    def __call__(self, fn, on_success, on_error):
        signals = _JobSignals()  # 在主執行緒建立 → affinity 為主執行緒
        self._jobs.add(signals)

        def finish(callback, value):
            try:
                callback(value)
            finally:
                self._jobs.discard(signals)

        signals.done.connect(
            lambda r: finish(on_success, r), Qt.ConnectionType.QueuedConnection
        )
        signals.failed.connect(
            lambda e: finish(on_error, e), Qt.ConnectionType.QueuedConnection
        )

        def target():
            try:
                result = fn()
            except Exception as e:
                signals.failed.emit(e)
                return
            signals.done.emit(result)

        threading.Thread(target=target, name="secretary-oauth", daemon=True).start()

    def shutdown(self):
        pass


_STALE = object()  # fetch job 開始時發現已過期，不連網直接回傳


def _is_network_error(e):
    return (
        isinstance(e, (TimeoutError, socket.timeout, OSError, httplib2.HttpLib2Error, TransportError))
        and not isinstance(e, google_client.AuthError)
    )


def describe_error(e):
    """把例外轉成給使用者看的中文訊息"""
    if isinstance(e, google_client.AuthError):
        return str(e)
    if isinstance(e, RefreshError):
        return "Google 授權已失效，請重新授權"
    if isinstance(e, HttpError):
        status = getattr(getattr(e, "resp", None), "status", None)
        if status in (401, 403):
            return f"Google 拒絕存取（HTTP {status}），請確認授權狀態"
        return f"Google 伺服器回應錯誤（HTTP {status}）"
    if _is_network_error(e):
        return NETWORK_MESSAGE
    return f"發生未預期的錯誤（{type(e).__name__}）"


class EventStore(QObject):
    events_changed = pyqtSignal(list)
    sync_state_changed = pyqtSignal(str, str)   # state, message
    operation_failed = pyqtSignal(str, str)     # action, 中文訊息
    operation_succeeded = pyqtSignal(str)       # action
    auth_state_changed = pyqtSignal(bool)

    def __init__(self, client=google_client, runner=None, token_path=TOKEN_PATH,
                 credentials_path=CREDENTIALS_PATH, oauth_runner=None, parent=None):
        super().__init__(parent)
        self._client = client
        self._runner = runner if runner is not None else ThreadPoolRunner()
        self._oauth_runner = oauth_runner if oauth_runner is not None else DaemonThreadRunner()
        self._token_path = token_path
        self._credentials_path = credentials_path
        self._creds = None
        self._events = []
        self._range = None
        self._fetch_gen = 0
        self._authorizing = False

    # ---- 查詢 ----
    def events(self):
        return [dict(e) for e in self._events]

    @property
    def is_authenticated(self):
        return self._creds is not None

    @property
    def is_authorizing(self):
        return self._authorizing

    # ---- 內部工具 ----
    def _emit_events(self):
        self.events_changed.emit(self.events())

    def _find(self, event_id):
        for i, ev in enumerate(self._events):
            if ev.get("id") == event_id:
                return i
        return -1

    def _make_job(self, op, is_stale=None):
        """建立背景工作：續約 → 建 service → 執行 op；結束時 token 有變就寫回。
        runner 為單一執行緒，所以 creds 的 refresh 與寫檔不會競態。"""
        creds = self._creds
        client = self._client
        token_path = self._token_path

        def job():
            if is_stale is not None and is_stale():
                return _STALE
            client.refresh_if_needed(creds, token_path)
            token_before = creds.token
            try:
                service = client.build_service(creds)
                return op(service)
            finally:
                if creds.token != token_before:
                    try:
                        client.save_token(creds, token_path)
                    except Exception:
                        logger.exception("寫回 token 失敗")
        return job

    def _fail(self, action, e, sync_state=None):
        logger.error(
            f"{action} 失敗：{type(e).__name__}",
            exc_info=(type(e), e, e.__traceback__),
        )
        message = describe_error(e)
        if isinstance(e, RefreshError) and self._creds is not None:
            self._creds = None
            self.auth_state_changed.emit(False)
        if sync_state is None:
            sync_state = "offline" if _is_network_error(e) else "error"
        self.sync_state_changed.emit(sync_state, message)
        self.operation_failed.emit(action, message)

    def _require_auth(self, action):
        if self._creds is None:
            self.operation_failed.emit(action, NOT_AUTHORIZED_MESSAGE)
            return False
        return True

    # ---- 啟動 / 授權 ----
    def start(self):
        """背景靜默載入 token；有效則開始拉取資料。"""
        def on_success(creds):
            self._creds = creds
            self.auth_state_changed.emit(creds is not None)
            if creds is not None:
                self.refresh()
            else:
                self.sync_state_changed.emit("idle", "尚未授權 Google 日曆")

        def on_error(e):
            logger.error(f"載入 token 失敗：{type(e).__name__}")
            self._creds = None
            self.auth_state_changed.emit(False)
            self.sync_state_changed.emit("idle", "尚未授權 Google 日曆")

        client, token_path = self._client, self._token_path
        self._runner(lambda: client.load_credentials(token_path), on_success, on_error)

    def authorize(self):
        """互動式 OAuth（背景）；進行中再呼叫會被忽略。"""
        if self._authorizing:
            return
        self._authorizing = True
        self.sync_state_changed.emit("authorizing", "請在瀏覽器完成 Google 授權")

        def on_success(creds):
            self._authorizing = False
            self._creds = creds
            self.auth_state_changed.emit(True)
            self.operation_succeeded.emit("auth")
            self.refresh()

        def on_error(e):
            self._authorizing = False
            self._fail("auth", e, sync_state="error")
            self.auth_state_changed.emit(self.is_authenticated)

        client, cred_path, token_path = self._client, self._credentials_path, self._token_path
        # OAuth 可能阻塞數分鐘，使用獨立 daemon 執行緒，不占用 API pool
        self._oauth_runner(lambda: client.run_oauth_flow(cred_path, token_path), on_success, on_error)

    def check_connection(self):
        if self._creds is None:
            # 未授權屬正常狀態，不視為錯誤，只回報授權狀態
            self.auth_state_changed.emit(False)
            return
        client = self._client

        def on_success(_):
            self.auth_state_changed.emit(True)
            self.operation_succeeded.emit("check")

        def on_error(e):
            # 網路錯誤（offline）不改授權狀態；RefreshError 由 _fail 清除憑證並發 False
            self._fail("check", e)

        self._runner(self._make_job(client.check_connection), on_success, on_error)

    def logout(self):
        """刪除本機 token、清空資料（本機檔案操作，在主執行緒執行）。"""
        try:
            os.remove(self._token_path)
        except FileNotFoundError:
            pass
        except OSError:
            logger.exception("刪除 token 失敗")
        self._creds = None
        self._events = []
        self._fetch_gen += 1  # 讓進行中的 fetch 結果失效
        self._emit_events()
        self.auth_state_changed.emit(False)
        self.sync_state_changed.emit("idle", "已登出")

    # ---- 範圍 / 拉取 ----
    def set_range(self, start_date, end_exclusive):
        new_range = (start_date, end_exclusive)
        if new_range == self._range:
            return
        self._range = new_range
        if self.is_authenticated:
            self.refresh()

    def ensure_month(self, year, month):
        start, end = mapping.month_range(year, month)
        self.set_range(start, end)

    def refresh(self):
        if not self._require_auth("fetch"):
            return
        if self._range is None:
            today = date.today()
            self._range = mapping.month_range(today.year, today.month)
        self._fetch_gen += 1
        gen = self._fetch_gen
        rng = self._range
        client = self._client
        time_min = mapping.to_rfc3339(rng[0])
        time_max = mapping.to_rfc3339(rng[1])
        self.sync_state_changed.emit("syncing", "同步中")

        def on_success(items):
            if items is _STALE or gen != self._fetch_gen:
                logger.info("丟棄過期的拉取結果")
                return
            mapped = []
            for item in items:
                try:
                    mapped.append(mapping.from_google(item))
                except Exception:
                    logger.warning(f"略過無法解析的事件，id={item.get('id')}")
            self._events = mapped
            self._emit_events()
            self.sync_state_changed.emit("ok", "已同步")
            self.operation_succeeded.emit("fetch")

        def on_error(e):
            if gen != self._fetch_gen:
                return
            self._fail("fetch", e)

        self._runner(
            self._make_job(
                lambda s: client.list_events(s, time_min, time_max),
                is_stale=lambda: gen != self._fetch_gen,
            ),
            on_success, on_error,
        )

    # ---- 寫入 ----
    def add_event(self, data):
        if not self._require_auth("add"):
            return
        client = self._client
        body = mapping.to_google_body(data)

        def on_success(item):
            self._events.append(mapping.from_google(item))
            self._emit_events()
            self.operation_succeeded.emit("add")

        self._runner(
            self._make_job(lambda s: client.insert_event(s, body)),
            on_success, lambda e: self._fail("add", e),
        )

    def update_event(self, event_id, data):
        if not self._require_auth("update"):
            return
        index = self._find(event_id)
        if index < 0:
            self.operation_failed.emit("update", "找不到要更新的行程，請重新整理後再試")
            return
        patch = mapping.build_patch_body(self._events[index], data)
        if not patch:
            self.operation_succeeded.emit("update")
            return
        client = self._client

        def on_success(item):
            i = self._find(event_id)
            if i >= 0:
                self._events[i] = mapping.from_google(item)
                self._emit_events()
            self.operation_succeeded.emit("update")

        self._runner(
            self._make_job(lambda s: client.patch_event(s, event_id, patch)),
            on_success, lambda e: self._fail("update", e),
        )

    def delete_event(self, event_id):
        if not self._require_auth("delete"):
            return
        client = self._client

        def on_success(_):
            i = self._find(event_id)
            if i >= 0:
                del self._events[i]
                self._emit_events()
            self.operation_succeeded.emit("delete")

        self._runner(
            self._make_job(lambda s: client.delete_event(s, event_id)),
            on_success, lambda e: self._fail("delete", e),
        )

    def shutdown(self):
        for runner in (self._runner, self._oauth_runner):
            shutdown = getattr(runner, "shutdown", None)
            if shutdown is not None:
                shutdown()

