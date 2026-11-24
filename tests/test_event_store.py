import threading
import time

import httplib2
import pytest

pytest.importorskip("PyQt6.QtCore")
from PyQt6.QtCore import QCoreApplication, QEvent  # noqa: E402

from services import event_store as es  # noqa: E402
from services.event_store import (  # noqa: E402
    DaemonThreadRunner, EventStore, ThreadPoolRunner, describe_error,
)


@pytest.fixture(scope="module")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


def sync_runner(fn, on_success, on_error):
    try:
        result = fn()
    except Exception as e:
        on_error(e)
        return
    on_success(result)


class FakeCreds:
    token = "t0"


class FakeClient:
    """假的 google_client：不連網，記錄呼叫。"""

    def __init__(self):
        self.creds = FakeCreds()
        self.items = []
        self.fail = None          # 設為例外則所有 API 呼叫皆 raise
        self.calls = []
        self.saved = []
        self.insert_result = None
        self.patch_result = None
        self.hook = None

    def load_credentials(self, token_path):
        return self.creds

    def refresh_if_needed(self, creds, token_path):
        return False

    def save_token(self, creds, token_path):
        self.saved.append(creds.token)

    def run_oauth_flow(self, credentials_path, token_path, timeout=0):
        self.calls.append(("oauth",))
        if self.fail:
            raise self.fail
        return self.creds

    def build_service(self, creds):
        return object()

    def _maybe_fail(self):
        if self.fail:
            raise self.fail

    def list_events(self, service, time_min, time_max):
        self.calls.append(("list", time_min, time_max))
        self._maybe_fail()
        if self.hook:
            self.hook()
        return list(self.items)

    def insert_event(self, service, body):
        self.calls.append(("insert", body))
        self._maybe_fail()
        return self.insert_result

    def patch_event(self, service, event_id, body):
        self.calls.append(("patch", event_id, body))
        self._maybe_fail()
        return self.patch_result

    def delete_event(self, service, event_id):
        self.calls.append(("delete", event_id))
        self._maybe_fail()

    def check_connection(self, service):
        self.calls.append(("check",))
        self._maybe_fail()


def item(event_id, title="T", date="2026-03-10", color=None):
    d = {"id": event_id, "summary": title,
         "start": {"date": date}, "end": {"date": date}}
    if color:
        d["colorId"] = color
    return d


class Recorder:
    def __init__(self, store):
        self.events = []
        self.sync = []
        self.failed = []
        self.ok = []
        self.auth = []
        store.events_changed.connect(self.events.append)
        store.sync_state_changed.connect(lambda s, m: self.sync.append((s, m)))
        store.operation_failed.connect(lambda a, m: self.failed.append((a, m)))
        store.operation_succeeded.connect(self.ok.append)
        store.auth_state_changed.connect(self.auth.append)


@pytest.fixture
def setup(qapp, tmp_path):
    client = FakeClient()
    store = EventStore(client=client, runner=sync_runner, oauth_runner=sync_runner,
                       token_path=str(tmp_path / "token.json"),
                       credentials_path=str(tmp_path / "credentials.json"))
    rec = Recorder(store)
    store.start()  # 同步 runner：載入憑證 → 自動 refresh
    return client, store, rec


def test_start_loads_and_fetches(setup):
    client, store, rec = setup
    assert store.is_authenticated
    assert rec.auth == [True]
    assert rec.events[-1] == []
    assert ("fetch" in rec.ok)


def test_fetch_success_emits_mapped_events(setup):
    client, store, rec = setup
    client.items = [item("a", "甲", color="11"), item("b", "乙")]
    store.refresh()
    ev = rec.events[-1]
    assert [e["id"] for e in ev] == ["a", "b"]
    assert ev[0]["priority"] == "major"
    assert ev[0]["title"] == "甲"
    assert rec.sync[-1][0] == "ok"
    assert store.events() == ev


def test_fetch_empty_clears_old_events(setup):
    client, store, rec = setup
    client.items = [item("a")]
    store.refresh()
    assert len(store.events()) == 1
    client.items = []
    store.refresh()
    assert rec.events[-1] == []
    assert store.events() == []


def test_fetch_failure_keeps_local_and_reports(setup):
    client, store, rec = setup
    client.items = [item("a")]
    store.refresh()
    before = store.events()
    client.fail = TimeoutError("boom")
    store.refresh()
    assert store.events() == before
    assert rec.failed[-1][0] == "fetch"
    assert "網路" in rec.failed[-1][1]
    assert rec.sync[-1][0] == "offline"


def test_fetch_failure_generic_is_error_state(setup):
    client, store, rec = setup
    client.fail = RuntimeError("x")
    store.refresh()
    assert rec.sync[-1][0] == "error"
    assert rec.failed[-1][0] == "fetch"


def test_add_success_uses_google_id(setup):
    client, store, rec = setup
    client.insert_result = item("google-id-1", "新", date="2026-03-12")
    store.add_event({"title": "新", "all_day": True, "start": "2026-03-12",
                     "end": "2026-03-12", "priority": "minor",
                     "location": "", "notes": ""})
    assert [e["id"] for e in store.events()] == ["google-id-1"]
    assert rec.events[-1][0]["id"] == "google-id-1"
    assert "add" in rec.ok
    body = [c for c in client.calls if c[0] == "insert"][0][1]
    assert body["end"] == {"date": "2026-03-13"}


def test_add_failure_leaves_local_unchanged(setup):
    client, store, rec = setup
    client.fail = RuntimeError("x")
    store.add_event({"title": "新", "all_day": True, "start": "2026-03-12",
                     "end": "2026-03-12", "priority": "minor"})
    assert store.events() == []
    assert rec.failed[-1][0] == "add"


def test_update_uses_patch_with_changed_fields_only(setup):
    client, store, rec = setup
    client.items = [item("a", "舊")]
    store.refresh()
    client.patch_result = item("a", "新")
    old = store.events()[0]
    store.update_event("a", {**old, "title": "新"})
    patch_calls = [c for c in client.calls if c[0] == "patch"]
    assert len(patch_calls) == 1
    assert patch_calls[0][1] == "a"
    assert patch_calls[0][2] == {"summary": "新"}
    assert store.events()[0]["title"] == "新"
    assert "update" in rec.ok


def test_update_no_change_skips_network(setup):
    client, store, rec = setup
    client.items = [item("a")]
    store.refresh()
    n = len(client.calls)
    store.update_event("a", store.events()[0])
    assert len(client.calls) == n
    assert rec.ok[-1] == "update"


def test_update_failure_leaves_local_unchanged(setup):
    client, store, rec = setup
    client.items = [item("a", "舊")]
    store.refresh()
    before = store.events()
    client.fail = RuntimeError("x")
    store.update_event("a", {**before[0], "title": "新"})
    assert store.events() == before
    assert rec.failed[-1][0] == "update"


def test_update_unknown_id_fails(setup):
    client, store, rec = setup
    store.update_event("nope", {"title": "x"})
    assert rec.failed[-1][0] == "update"


def test_delete_success_and_failure(setup):
    client, store, rec = setup
    client.items = [item("a"), item("b")]
    store.refresh()
    client.fail = RuntimeError("x")
    store.delete_event("a")
    assert len(store.events()) == 2
    assert rec.failed[-1][0] == "delete"
    client.fail = None
    store.delete_event("a")
    assert [e["id"] for e in store.events()] == ["b"]
    assert "delete" in rec.ok


def test_unauthorized_writes_do_not_call_client(qapp, tmp_path):
    client = FakeClient()
    store = EventStore(client=client, runner=sync_runner,
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    rec = Recorder(store)
    store.add_event({"title": "x", "all_day": True, "start": "2026-03-12",
                     "end": "2026-03-12", "priority": "minor"})
    store.update_event("a", {"title": "x"})
    store.delete_event("a")
    assert client.calls == []
    assert [a for a, _ in rec.failed] == ["add", "update", "delete"]
    assert all("設定頁授權" in m for _, m in rec.failed)


def test_stale_fetch_result_is_discarded(qapp, tmp_path):
    """切換月份：第一次 fetch 的結果在第二次 fetch 之後才到，應被丟棄。"""
    client = FakeClient()
    pending = []

    def deferred_runner(fn, on_success, on_error):
        pending.append((fn, on_success, on_error))

    store = EventStore(client=client, runner=sync_runner,
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    rec = Recorder(store)
    store.start()
    store._runner = deferred_runner

    client.items = [item("old-month")]
    store.ensure_month(2026, 3)
    client.items = [item("new-month")]
    store.ensure_month(2026, 4)
    assert len(pending) == 2
    # 先執行第二個（新），再執行第一個（舊、過期）
    for index in (1, 0):
        fn, ok, err = pending[index]
        if index == 1:
            client.items = [item("new-month")]
        else:
            client.items = [item("old-month")]
        ok(fn())
    assert [e["id"] for e in store.events()] == ["new-month"]


def test_stale_fetch_error_does_not_report(qapp, tmp_path):
    client = FakeClient()
    pending = []
    store = EventStore(client=client, runner=sync_runner,
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    rec = Recorder(store)
    store.start()
    store._runner = lambda fn, ok, err: pending.append((fn, ok, err))
    store.ensure_month(2026, 3)
    store.ensure_month(2026, 4)
    pending[0][2](RuntimeError("late"))
    assert not rec.failed


def test_authorize_success_and_ignore_reentry(qapp, tmp_path):
    client = FakeClient()
    oauth_pending = []
    api_pending = []
    store = EventStore(client=client, runner=lambda *a: api_pending.append(a),
                       oauth_runner=lambda *a: oauth_pending.append(a),
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    rec = Recorder(store)
    store.authorize()
    store.authorize()  # 進行中，忽略
    assert len(oauth_pending) == 1
    assert api_pending == []  # OAuth 不占用 API runner
    assert rec.sync[0][0] == "authorizing"
    store._runner = sync_runner
    fn, ok, err = oauth_pending[0]
    ok(fn())
    assert store.is_authenticated
    assert True in rec.auth
    assert "auth" in rec.ok
    assert rec.sync[-1][0] == "ok"  # 授權成功後自動 refresh


def test_api_runner_usable_while_oauth_pending(qapp, tmp_path):
    client = FakeClient()
    oauth_pending = []
    store = EventStore(client=client, runner=sync_runner,
                       oauth_runner=lambda *a: oauth_pending.append(a),
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    rec = Recorder(store)
    store.start()
    store.authorize()
    client.items = [item("a")]
    store.refresh()  # OAuth 進行中，API 照常可用
    assert [e["id"] for e in store.events()] == ["a"]


def test_authorize_failure_reports(qapp, tmp_path):
    client = FakeClient()
    client.fail = es.google_client.AuthError("授權逾時，請重新操作")
    store = EventStore(client=client, runner=sync_runner, oauth_runner=sync_runner,
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    rec = Recorder(store)
    store.authorize()
    assert rec.failed == [("auth", "授權逾時，請重新操作")]
    assert not store.is_authenticated
    # 失敗後可以再次授權
    store.authorize()
    assert len(rec.failed) == 2


def test_start_without_token_emits_auth_false_only(qapp, tmp_path):
    client = FakeClient()
    client.creds = None  # load_credentials 回傳 None
    store = EventStore(client=client, runner=sync_runner, oauth_runner=sync_runner,
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    rec = Recorder(store)
    store.start()
    assert rec.auth == [False]
    assert rec.failed == []


def test_stale_fetch_job_skips_network(qapp, tmp_path):
    """worker 開始執行時世代已過期 → 不連網，回傳 sentinel，callback 忽略"""
    client = FakeClient()
    pending = []
    store = EventStore(client=client, runner=sync_runner, oauth_runner=sync_runner,
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    rec = Recorder(store)
    store.start()
    client.calls.clear()
    store._runner = lambda fn, ok, err: pending.append((fn, ok, err))
    store.ensure_month(2026, 3)
    store.ensure_month(2026, 4)
    first_fn, first_ok, _ = pending[0]
    result = first_fn()  # 第一個已過期
    assert result is es._STALE
    assert [c for c in client.calls if c[0] == "list"] == []
    events_before = len(rec.events)
    first_ok(result)
    assert len(rec.events) == events_before
    # 第二個（最新）正常連網
    second_fn, second_ok, _ = pending[1]
    client.items = [item("new")]
    second_ok(second_fn())
    assert [c[0] for c in client.calls].count("list") == 1
    assert [e["id"] for e in store.events()] == ["new"]


def test_token_saved_when_changed_by_worker(setup):
    client, store, rec = setup

    def bump():
        client.creds.token = "t1"

    client.hook = bump
    store.refresh()
    assert client.saved == ["t1"]


def test_logout_clears_state_and_token(setup, tmp_path):
    client, store, rec = setup
    client.items = [item("a")]
    store.refresh()
    token = tmp_path / "token.json"
    token.write_text("{}", encoding="utf-8")
    store.logout()
    assert not token.exists()
    assert store.events() == []
    assert not store.is_authenticated
    assert rec.auth[-1] is False


def test_check_connection_success(setup):
    client, store, rec = setup
    store.check_connection()
    assert rec.auth[-1] is True
    assert "check" in rec.ok


def test_check_connection_network_error_keeps_auth_state(setup):
    client, store, rec = setup
    auth_before = list(rec.auth)
    client.fail = TimeoutError("boom")
    store.check_connection()
    assert rec.auth == auth_before  # 沒有新的 auth_state_changed
    assert store.is_authenticated
    assert rec.sync[-1][0] == "offline"
    assert rec.failed[-1][0] == "check"


def test_check_connection_refresh_error_clears_auth(setup):
    from google.auth.exceptions import RefreshError
    client, store, rec = setup
    client.fail = RefreshError("invalid_grant")
    store.check_connection()
    assert rec.auth[-1] is False
    assert not store.is_authenticated


def test_check_connection_unauthorized_emits_false(qapp, tmp_path):
    client = FakeClient()
    store = EventStore(client=client, runner=sync_runner,
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    rec = Recorder(store)
    store.check_connection()
    assert rec.auth == [False]
    assert rec.failed == []  # 未授權不是錯誤，不可跳「尚未連線」提示
    assert client.calls == []


def test_events_changed_payload_is_copy(setup):
    client, store, rec = setup
    client.items = [item("a")]
    store.refresh()
    rec.events[-1][0]["title"] = "被改"
    assert store.events()[0]["title"] != "被改"


# ---- ThreadPoolRunner 跨執行緒測試 ----

def _wait(predicate, timeout=3.0):
    # 只派送 MetaCall（QueuedConnection 回呼）事件；不用 processEvents()，
    # 以免處理到其他測試遺留的 DeferredDelete 等事件而造成 access violation。
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QCoreApplication.sendPostedEvents(None, QEvent.Type.MetaCall)
        if predicate():
            return True
        time.sleep(0.005)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.MetaCall)
    return predicate()


def test_thread_pool_runner_success_runs_off_main_thread(qapp):
    runner = ThreadPoolRunner()
    main_ident = threading.get_ident()
    got = {}

    def fn():
        return threading.get_ident()

    def ok(result):
        got["fn_thread"] = result
        got["cb_thread"] = threading.get_ident()

    runner(fn, ok, lambda e: got.setdefault("error", e))
    assert _wait(lambda: "cb_thread" in got or "error" in got)
    runner.shutdown()
    assert "error" not in got
    assert got["fn_thread"] != main_ident
    assert got["cb_thread"] == main_ident
    assert not runner._jobs


def test_thread_pool_runner_error_path(qapp):
    runner = ThreadPoolRunner()
    main_ident = threading.get_ident()
    got = {}

    def fn():
        raise ValueError("bad")

    def err(e):
        got["error"] = e
        got["cb_thread"] = threading.get_ident()

    runner(fn, lambda r: got.setdefault("ok", r), err)
    assert _wait(lambda: "error" in got or "ok" in got)
    runner.shutdown()
    assert "ok" not in got
    assert isinstance(got["error"], ValueError)
    assert got["cb_thread"] == main_ident
    assert not runner._jobs


def test_thread_pool_runner_serializes_jobs(qapp):
    runner = ThreadPoolRunner()
    order = []
    done = []

    def make(n):
        def fn():
            order.append(("start", n))
            time.sleep(0.05)
            order.append(("end", n))
            return n
        return fn

    for n in range(3):
        runner(make(n), done.append, lambda e: done.append(e))
    assert _wait(lambda: len(done) == 3)
    runner.shutdown()
    assert done == [0, 1, 2]
    # 單一執行緒：不可交錯
    assert order == [("start", 0), ("end", 0), ("start", 1), ("end", 1),
                     ("start", 2), ("end", 2)]


# ---- describe_error / 網路錯誤分類 ----

def _http_error(status):
    from googleapiclient.errors import HttpError
    resp = httplib2.Response({"status": status})
    return HttpError(resp, b"{}")


def test_describe_error_http_status():
    assert "404" in describe_error(_http_error(404))
    assert "500" in describe_error(_http_error(500))
    assert "拒絕存取" in describe_error(_http_error(403))
    assert "401" in describe_error(_http_error(401))


def test_describe_error_network_kinds():
    from google.auth.exceptions import TransportError
    for e in (TransportError("x"), TimeoutError("x"), OSError("x"),
              ConnectionError("x"), httplib2.ServerNotFoundError("x"),
              httplib2.HttpLib2Error("x")):
        assert describe_error(e) == "網路連線逾時或離線", type(e).__name__
        assert es._is_network_error(e)


def test_describe_error_auth_and_other():
    from google.auth.exceptions import RefreshError
    assert "重新授權" in describe_error(RefreshError("x"))
    assert not es._is_network_error(RefreshError("x"))
    auth = es.google_client.AuthError("授權逾時")
    assert describe_error(auth) == "授權逾時"
    assert not es._is_network_error(auth)
    other = describe_error(ValueError("x"))
    assert "未預期" in other and "ValueError" in other


def test_transport_error_in_fetch_is_offline(setup):
    from google.auth.exceptions import TransportError
    client, store, rec = setup
    client.fail = TransportError("dns")
    store.refresh()
    assert rec.sync[-1][0] == "offline"
    assert "網路" in rec.failed[-1][1]


def test_daemon_thread_runner_cross_thread(qapp):
    runner = DaemonThreadRunner()
    main_ident = threading.get_ident()
    got = {}
    runner(threading.get_ident,
           lambda r: got.update(fn_thread=r, cb_thread=threading.get_ident()),
           lambda e: got.update(error=e))
    assert _wait(lambda: "cb_thread" in got or "error" in got)
    assert "error" not in got
    assert got["fn_thread"] != main_ident
    assert got["cb_thread"] == main_ident
    assert not runner._jobs


def test_daemon_thread_runner_error_and_daemon_flag(qapp):
    runner = DaemonThreadRunner()
    got = {}
    release = threading.Event()

    def fn():
        raise ValueError("bad")

    runner(fn, lambda r: got.update(ok=r), lambda e: got.update(error=e))
    assert _wait(lambda: "error" in got or "ok" in got)
    assert isinstance(got["error"], ValueError)
    # 長時間阻塞的工作不影響其他工作，且為 daemon 執行緒
    runner(release.wait, lambda r: None, lambda e: None)
    names = [t for t in threading.enumerate() if t.name == "secretary-oauth"]
    assert names and all(t.daemon for t in names)
    release.set()


def test_is_authorizing_property(qapp, tmp_path):
    client = FakeClient()
    pending = []
    store = EventStore(client=client, runner=sync_runner,
                       oauth_runner=lambda *a: pending.append(a),
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    assert not store.is_authorizing
    store.authorize()
    assert store.is_authorizing
    fn, ok, err = pending[0]
    ok(fn())
    assert not store.is_authorizing
