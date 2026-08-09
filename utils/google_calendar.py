"""
utils/google_calendar.py
Google Calendar API 服務模組 (包含二向同步 delete_event 與 update_event)
"""

import os
import socket
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal

try:
    _orig_getaddrinfo = socket.getaddrinfo
    def _ipv4_only_getaddrinfo(*args, **kwargs):
        res = _orig_getaddrinfo(*args, **kwargs)
        ipv4_res = [r for r in res if r[0] == socket.AF_INET]
        return ipv4_res if ipv4_res else res
    socket.getaddrinfo = _ipv4_only_getaddrinfo
except Exception as e:
    print(f"[GoogleCalendar] IPv4 網路修復套用失敗: {e}")

COLOR_PRIORITY_MAP = {
    "11": "major",  # Tomato (番茄大紅)
    "4": "major",   # Flamingo (火鶴粉紅)
    "5": "medium",  # Banana (香蕉鮮黃)
    "6": "medium",  # Tangerine (柑橘亮橘)
    "2": "minor",   # Sage (鼠尾草淺綠)
    "10": "minor"   # Basil (羅勒深綠)
}

PRIORITY_COLOR_MAP = {
    "major": "11",
    "medium": "5",
    "minor": "2"
}

socket.setdefaulttimeout(8.0)

class GoogleCalendarService:
    def __init__(self):
        self.service = None
        self.is_connected = False
        self.credentials_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.json")
        self.token_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "token.json")

    def parse_priority_from_color(self, color_id, default="minor"):
        if not color_id:
            return default
        return COLOR_PRIORITY_MAP.get(str(color_id), default)

    def get_color_from_priority(self, priority):
        return PRIORITY_COLOR_MAP.get(priority, "2")

    def authenticate(self, force_interactive=False):
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            scopes = ['https://www.googleapis.com/auth/calendar']
            creds = None

            if force_interactive and os.path.exists(self.token_file):
                try:
                    os.remove(self.token_file)
                    print(f"[{datetime.now().isoformat()}] [GoogleCalendar] 已清除舊有 token.json 憑證")
                except Exception as e:
                    print(f"[{datetime.now().isoformat()}] 清除舊 Token 失敗: {e}")

            if os.path.exists(self.token_file):
                try:
                    creds = Credentials.from_authorized_user_file(self.token_file, scopes)
                except Exception as e:
                    print(f"[{datetime.now().isoformat()}] token.json 讀取異常: {e}")
                    creds = None

            if creds:
                if creds.valid:
                    self.service = build('calendar', 'v3', credentials=creds)
                    self.is_connected = True
                    return True
                elif creds.expired and creds.refresh_token:
                    try:
                        print(f"[{datetime.now().isoformat()}] [GoogleCalendar] 偵測到 Token 過期，正在背景自動靜默續約...")
                        creds.refresh(Request(timeout=6))
                        with open(self.token_file, 'w', encoding='utf-8') as token:
                            token.write(creds.to_json())
                        print(f"[{datetime.now().isoformat()}] [GoogleCalendar] 🎉 背景自動續約成功！")
                        self.service = build('calendar', 'v3', credentials=creds)
                        self.is_connected = True
                        return True
                    except Exception as e:
                        print(f"[{datetime.now().isoformat()}] 背景自動續約失敗: {e}")
                        creds = None

            # 若上面無法自動靜默登入 (例如 creds 無效或 refresh 失敗)
            if not force_interactive:
                print(f"[{datetime.now().isoformat()}] [GoogleCalendar] 背景靜默認證失敗，放棄自動彈出瀏覽器視窗")
                self.is_connected = False
                return False

            if not os.path.exists(self.credentials_file):
                self.is_connected = False
                return False

            flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, scopes)
            try:
                creds = flow.run_local_server(
                    host='localhost',
                    port=8080,
                    access_type='offline',
                    prompt='consent',
                    authorization_prompt_message='請在跳出的瀏覽器中完成 Google 帳號授權...',
                    success_message='<h1 style="color:#8b5cf6;text-align:center;font-family:sans-serif;margin-top:50px;">🎉 授權成功！</h1><p style="text-align:center;color:#666;">您現在可以關閉此瀏覽器分頁，並回到 Secretary 桌面小助理。</p>',
                    open_browser=True
                )
            except Exception as e_server:
                creds = flow.run_local_server(
                    port=0,
                    access_type='offline',
                    prompt='consent',
                    success_message='<h1 style="color:#8b5cf6;text-align:center;">🎉 授權成功！</h1>',
                    open_browser=True
                )

            if creds and creds.valid:
                with open(self.token_file, 'w', encoding='utf-8') as token:
                    token.write(creds.to_json())
                self.service = build('calendar', 'v3', credentials=creds)
                self.is_connected = True
                return True
            else:
                self.is_connected = False
                return False
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [GoogleCalendar] 授權認證失敗: {e}")
            self.is_connected = False
            return False

    def check_connection(self):
        if not self.is_connected and os.path.exists(self.token_file):
            self.authenticate(force_interactive=False)

        if not self.is_connected or not self.service:
            return False

        try:
            self.service.calendarList().get(calendarId='primary').execute()
            self.is_connected = True
            return True
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [GoogleCalendar] 實質 API 通訊失敗: {e}")
            self.is_connected = False
            return False

    def fetch_upcoming_events(self, max_results=100):
        if not self.is_connected and os.path.exists(self.token_file):
            self.authenticate(force_interactive=False)

        if not self.is_connected or not self.service:
            return []

        try:
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            items = events_result.get('items', [])

            formatted_events = []
            for item in items:
                color_id = item.get('colorId', '')
                priority = self.parse_priority_from_color(color_id)

                start_raw = item['start'].get('dateTime', item['start'].get('date'))
                end_raw = item['end'].get('dateTime', item['end'].get('date'))

                formatted_events.append({
                    "id": item.get('id'),
                    "title": item.get('summary', '無標題行程'),
                    "start": start_raw,
                    "end": end_raw,
                    "priority": priority,
                    "location": item.get('location', ''),
                    "notes": item.get('description', '')
                })
            return formatted_events
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [GoogleCalendar] 讀取 Google 日曆異常: {e}")
            return []

    def add_event(self, event_data):
        if not self.is_connected and os.path.exists(self.token_file):
            self.authenticate(force_interactive=False)

        if not self.is_connected or not self.service:
            return False

        try:
            priority = event_data.get("priority", "minor")
            color_id = self.get_color_from_priority(priority)

            start_str = event_data.get("start", "")
            end_str = event_data.get("end", "")

            if 'T' not in start_str:
                start_datetime = f"{start_str}T09:00:00"
            else:
                start_datetime = start_str

            if 'T' not in end_str:
                end_datetime = f"{end_str}T10:00:00"
            else:
                end_datetime = end_str

            body = {
                'summary': event_data.get("title", "新行程"),
                'location': event_data.get("location", ""),
                'description': event_data.get("notes", ""),
                'colorId': color_id,
                'start': {
                    'dateTime': f"{start_datetime[:19]}+08:00",
                    'timeZone': 'Asia/Taipei',
                },
                'end': {
                    'dateTime': f"{end_datetime[:19]}+08:00",
                    'timeZone': 'Asia/Taipei',
                },
            }

            created = self.service.events().insert(calendarId='primary', body=body).execute()
            print(f"[{datetime.now().isoformat()}] [GoogleCalendar] 成功新增至 Google 雲端: {event_data.get('title')}")
            return created
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [GoogleCalendar] 寫入 Google 雲端失敗: {e}")
            return False

    def update_event(self, event_data):
        """在 Google 日曆雲端更新現有行程 (包含標題、時間、等級顏色、地點與備註說明)"""
        if not self.is_connected and os.path.exists(self.token_file):
            self.authenticate(force_interactive=False)

        event_id = event_data.get("id")
        if not self.is_connected or not self.service or not event_id:
            return False

        try:
            priority = event_data.get("priority", "minor")
            color_id = self.get_color_from_priority(priority)

            start_str = event_data.get("start", "")
            end_str = event_data.get("end", "")

            if 'T' not in start_str:
                start_datetime = f"{start_str}T09:00:00"
            else:
                start_datetime = start_str

            if 'T' not in end_str:
                end_datetime = f"{end_str}T10:00:00"
            else:
                end_datetime = end_str

            body = {
                'summary': event_data.get("title", "行程"),
                'location': event_data.get("location", ""),
                'description': event_data.get("notes", ""),
                'colorId': color_id,
                'start': {
                    'dateTime': f"{start_datetime[:19]}+08:00",
                    'timeZone': 'Asia/Taipei',
                },
                'end': {
                    'dateTime': f"{end_datetime[:19]}+08:00",
                    'timeZone': 'Asia/Taipei',
                },
            }

            updated = self.service.events().update(calendarId='primary', eventId=event_id, body=body).execute()
            print(f"[{datetime.now().isoformat()}] [GoogleCalendar] 成功於 Google 雲端更新行程 ID: {event_id}")
            return updated
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [GoogleCalendar] Google 雲端更新行程失敗: {e}")
            return False

    def delete_event(self, event_id):
        if not self.is_connected and os.path.exists(self.token_file):
            self.authenticate(force_interactive=False)

        if not self.is_connected or not self.service or not event_id:
            return False

        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            print(f"[{datetime.now().isoformat()}] [GoogleCalendar] 成功於 Google 雲端刪除行程 ID: {event_id}")
            return True
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [GoogleCalendar] Google 雲端刪除行程失敗: {e}")
            return False


class GoogleFetchWorker(QThread):
    fetched_signal = pyqtSignal(list)

    def __init__(self, service):
        super().__init__()
        self.service = service

    def run(self):
        try:
            events = self.service.fetch_upcoming_events()
            self.fetched_signal.emit(events)
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [GoogleFetchWorker] 背景拉取異常: {e}")
            self.fetched_signal.emit([])
