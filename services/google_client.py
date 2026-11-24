"""
services/google_client.py
Google Calendar API 薄封裝（取代舊的 utils/google_calendar.py）。

- 匯入時無任何副作用：不改全域 socket、不連網。
  （舊版曾 monkeypatch socket.getaddrinfo 並設定全域逾時，會影響整個行程；
  若日後在 IPv6 環境逾時，改在 httplib2 層級處理。）
- 所有函式皆為同步阻塞，必須在背景執行緒呼叫（見 services/event_store.py）。
- 例外一律往上拋，由呼叫端決定如何呈現。
"""

import errno
import os
import tempfile
import threading

import google_auth_httplib2
import httplib2
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, WSGITimeoutError
from googleapiclient.discovery import build

from utils.logger import get_logger
from utils.paths import CREDENTIALS_PATH, TOKEN_PATH

logger = get_logger(__name__)

HTTP_TIMEOUT = 15
OAUTH_TIMEOUT = 180
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = "primary"
OAUTH_PORT = 8080

_SUCCESS_MESSAGE = (
    '<h1 style="color:#8b5cf6;text-align:center;font-family:sans-serif;margin-top:50px;">'
    "授權成功！</h1>"
    '<p style="text-align:center;color:#666;">'
    "您現在可以關閉此瀏覽器分頁，並回到 Secretary 桌面小助理。</p>"
)

# 本機埠無法綁定時的 errno（Windows: 10048 位址已被使用、10013 權限不足）
_BIND_ERRNOS = {errno.EADDRINUSE, errno.EACCES, 10048, 10013}


class AuthError(Exception):
    """授權流程失敗（訊息為中文，可直接顯示給使用者）"""


_token_lock = threading.Lock()


def save_token(creds, token_path=TOKEN_PATH):
    """把憑證寫回 token 檔：加鎖，並先寫同目錄暫存檔再 os.replace（原子取代）"""
    directory = os.path.dirname(os.path.abspath(token_path))
    with _token_lock:
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".token_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            os.replace(tmp_path, token_path)
        except BaseException:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise


def load_credentials(token_path=TOKEN_PATH):
    """讀取 token 檔；憑證有效或可用 refresh_token 續約才回傳，否則回傳 None。
    不會自行 refresh（續約請呼叫 refresh_if_needed）。"""
    if not os.path.exists(token_path):
        return None
    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    except Exception:
        logger.exception("token 檔讀取異常")
        return None
    if creds.valid or (creds.expired and creds.refresh_token):
        return creds
    return None


def refresh_if_needed(creds, token_path=TOKEN_PATH):
    """憑證過期且有 refresh_token 時續約並寫回 token。回傳是否有續約。"""
    if creds.expired and creds.refresh_token:
        logger.info("偵測到 Token 過期，正在續約")
        request = google_auth_httplib2.Request(httplib2.Http(timeout=HTTP_TIMEOUT))
        creds.refresh(request)
        save_token(creds, token_path)
        logger.info("Token 續約成功")
        return True
    return False


def run_oauth_flow(credentials_path=CREDENTIALS_PATH, token_path=TOKEN_PATH, timeout=OAUTH_TIMEOUT):
    """互動式 OAuth（會開啟瀏覽器，必須在背景執行緒呼叫）。
    先用固定 port 8080；只有在該 port 綁定失敗（此時瀏覽器尚未開啟）才改用隨機 port 重試一次。
    逾時、使用者未完成或其他失敗一律 raise AuthError，不會再開第二次瀏覽器。"""
    if not os.path.exists(credentials_path):
        raise AuthError("找不到 credentials.json，請先放入 data 資料夾")
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)

    def attempt(port):
        return flow.run_local_server(
            host="localhost",
            port=port,
            access_type="offline",
            prompt="consent",
            authorization_prompt_message="",  # 空字串：不 print（pythonw 無 stdout）
            success_message=_SUCCESS_MESSAGE,
            open_browser=True,
            timeout_seconds=timeout,
        )

    try:
        try:
            creds = attempt(OAUTH_PORT)
        except OSError as e_server:
            if getattr(e_server, "errno", None) not in _BIND_ERRNOS:
                raise
            logger.warning(f"固定 port {OAUTH_PORT} 無法使用，改用隨機 port: {e_server}")
            creds = attempt(0)
    except WSGITimeoutError as e:
        raise AuthError("授權逾時，請重新操作") from e
    except AuthError:
        raise
    except Exception as e:
        logger.exception("授權流程失敗")
        raise AuthError("授權流程失敗，請重新操作") from e

    if creds is None or not creds.valid:
        raise AuthError("授權未完成，請重新操作")
    save_token(creds, token_path)
    logger.info("授權成功，已儲存 token")
    return creds


def build_service(creds):
    """建立 Calendar service（每個 worker 各建一個，httplib2 非執行緒安全）。
    build() 在未指定 discoveryServiceUrl 時預設 static_discovery=True，
    使用套件內附的 discovery 文件，不會連網。"""
    authed_http = google_auth_httplib2.AuthorizedHttp(
        creds, http=httplib2.Http(timeout=HTTP_TIMEOUT)
    )
    return build("calendar", "v3", http=authed_http, cache_discovery=False)


def list_events(service, time_min, time_max):
    """列出 [time_min, time_max) 區間內所有行程（處理分頁）。例外直接 raise。"""
    items = []
    page_token = None
    while True:
        params = {
            "calendarId": CALENDAR_ID,
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": 250,
        }
        if page_token:
            params["pageToken"] = page_token
        result = service.events().list(**params).execute()
        items.extend(result.get("items", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            return items


def insert_event(service, body):
    created = service.events().insert(calendarId=CALENDAR_ID, body=body).execute()
    logger.info(f"已新增行程至 Google，id={created.get('id')}")
    return created


def patch_event(service, event_id, body):
    updated = service.events().patch(calendarId=CALENDAR_ID, eventId=event_id, body=body).execute()
    logger.info(f"已更新 Google 行程，id={event_id}")
    return updated


def delete_event(service, event_id):
    service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
    logger.info(f"已刪除 Google 行程，id={event_id}")


def check_connection(service):
    """實際打一次 API 確認連線；失敗 raise"""
    service.calendarList().get(calendarId=CALENDAR_ID).execute()
