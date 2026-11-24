# Secretary 專案開發進度清單 (Development Progress)

## 📌 Phase 1: 基礎架構與桌面 UI 介面 (已完成)
- [x] PyQt6 專案目錄結構與主程式建立 (`main.py`, `ui/`)
- [x] 暗黑高顏值主題與電光紫配色 (`#121217`, `#1c1c24`, `#8b5cf6`)
- [x] 左側導覽列 `NavSidebar` (日曆與行程 / 喝水與設定)
- [x] 中間月曆 `CalendarView` (440px 寬、1:1 置中、週末電光紫字體)
- [x] 右側提醒面板 `SidebarFrame` (340px 緊貼右側、雙行頂部導覽列)
- [x] 選取日期當日行程卡片 `TodayEventCard` (標題/地點/備註獨立三行、100% 依字數自適應高度、`word-break: break-all` 自動折行)

## 📌 Phase 2: 喝水提醒與系統整合 (已完成)
- [x] 螢幕右下角 3 秒淡出 Toast 提醒視窗 (`ToastWindow`)
- [x] Windows 系統訊息提示音 (`winsound.MessageBeep`)
- [x] 1 秒實時動態背景倒數計時器 (左下角 `下次提醒: MM:SS 後` 每秒秒數更新)
- [x] 設定頁面喝水提醒總開關與間隔設定
- [x] 關閉視窗縮小至系統托盤 (`QSystemTrayIcon`)
- [x] 開機自動啟動與 `--minimized` 靜默托盤啟動
- [x] 單一實體防護鎖 (`QLocalServer` & `QLocalSocket` - 避免重複開啟進程，點擊捷徑喚醒原視窗)

## 📌 Phase 3: Google Calendar 雲端雙向串接與進階防護 (已完成)
- [x] Google OAuth2 API 授權整合 (`google-api-python-client`, `credentials.json`, `token.json`)
- [x] `.gitignore` 檔案維護，徹底保護敏感憑證與 Token 不遭 Git 追蹤
- [x] 行程讀取已移至背景 QThread (`GoogleFetchWorker`)，（階段 B 起新增/編輯/刪除、OAuth 與 `check_connection` 皆改由 `EventStore` 在背景執行）
- [x] 背景無感自動續約 (Auto-Refresh `refresh_token`)
- [x] 實質 API 健康度通訊檢查 (`check_connection()`)
- [x] Google 日曆全色彩標籤級別對應 (紅:大30天 / 黃橘:中7天 / 綠:小3天)
- [x] 編輯行程右下角三鈕區 (`[取消]` `[🗑️ 刪除行程]` `[儲存行程]`)
- [x] 專屬暗黑紫紅刪除確認對話框 (`ConfirmDeleteDialog`)
- [x] Google 日曆讀取、新增 (`insert_event`)、更新 (`patch_event`) 與刪除 (`delete_event`) 功能（`services/google_client.py`，經 `EventStore` 呼叫；同步缺陷已於階段 B 修正）
- [x] 桌面 256x256 高畫質紫光電光圖示 `icon.png` / `icon.ico`
- [x] Windows 桌面捷徑 `Secretary 智能桌面小助理.lnk` 自動建立

## ⚠️ 已知問題（2026-11-24 審查）
1. ~~編輯行程時對話框不帶入原日期時間、全天行程被轉成定時、`events().update` 整筆覆蓋。~~（2026-11-24 階段 B 已處理：對話框新增「全天」核取方塊並帶入原日期時間；更新改用 `events().patch`，由 `build_patch_body` 只送變動欄位）
2. ~~OAuth 在主執行緒執行且 `run_local_server` 無逾時。~~（2026-11-24 階段 B 已處理：OAuth 改在 `DaemonThreadRunner` 獨立 daemon 執行緒執行，`timeout_seconds=180`；僅 8080 綁定失敗才改 port 0，不會開第二次瀏覽器）
3. ~~新增行程使用假 id、寫入失敗仍修改本地資料且無提示。~~（2026-11-24 階段 B 已處理：使用 Google 回傳的 id，寫入成功才更新本地；失敗發出 `operation_failed`，由 `main.py` 以 toast + QMessageBox 提示）
4. ~~雲端回傳空清單時本地不清空，離線與無行程無法區分。~~（2026-11-24 階段 B 已處理：`EventStore` 區分 fetch 失敗（保留本地並提示）與成功但空清單（清空））
5. ~~新增/編輯/刪除與啟動時 `check_connection` 在主執行緒阻塞。~~（2026-11-24 階段 B 已處理：全部經 `EventStore` 的單執行緒 `ThreadPoolRunner` 在背景執行，結果以 QueuedConnection 回主執行緒）
6. ~~背景 fetch 與 UI 共用同一個 service，httplib2 非 thread-safe。~~（2026-11-24 階段 B 已處理：每個 worker 自建 service，`httplib2.Http(timeout=15)` + `AuthorizedHttp`，且 API 呼叫由單執行緒 pool 序列化）
7. ~~日誌使用 `print`，在 `pythonw` 下全部遺失。~~（2026-11-24 階段 A 已處理：改用 `utils/logger.py`，寫入 `data/logs/secretary.log`）
8. autostart 預設開啟，且每次啟動都寫入 Registry。（待階段 D 處理）
9. ~~只抓 `timeMin=now`、`maxResults=100`，未處理 `nextPageToken`；過去日期空白。~~（2026-11-24 階段 B 已處理：改拉取目前顯示月份前後各一個月（`ensure_month`），切換月份自動拉取，處理分頁，過去日期可顯示）
10. ~~箭頭圖示 QSS 使用相對路徑 `assets/...`~~（2026-11-24 工作區整理已修正：改用 `utils/paths.py` 絕對路徑）。
11. ~~尚無自動化測試。~~（2026-11-24 階段 A 已建立 `tests/` 測試骨架，`python -m pytest` 全數通過）
12. ~~重複／未使用程式碼~~（2026-11-24 工作區整理已修正：刪除 `preview_ui.py`、`utils/shortcut_creator.py`，產生器與捷徑腳本移至 `scripts/`）。
13. logout 與排隊中 job 寫回 token 的競態：`EventStore.logout()` 後，已排隊的 job 仍可能把憑證寫回 token 檔（UI 尚未接上 logout，目前不會觸發）。
14. `local_tz()` 取目前時間的固定 offset，有夏令時間（DST）的地區，跨 DST 的日期會差 1 小時（台灣不受影響）。
15. 定時行程改成全天時，原 `start.timeZone` 是否需一併清除，尚未對 Google 實測。
16. 任何 `RefreshError` 都會清掉本地憑證，含可能可重試的情況（例如暫時性網路／伺服器錯誤）。
17. 右側「即將到來」側欄受目前瀏覽月份的拉取範圍影響（前後各一個月），瀏覽到 2 個月以外時可能變空。
18. `main.py` 單一實例 socket 名稱（`SINGLE_INSTANCE_SOCKET`）含使用者名稱，屬寫死個人資訊，應改為動態或通用名稱。

## 📌 階段 A: 基礎建設 (已完成，2026-11-24)
- [x] `utils/logger.py`：`get_logger(__name__)`，RotatingFileHandler 寫入 `data/logs/secretary.log`，pythonw 無 stdout 時不加 StreamHandler，建立目錄或開檔失敗不崩潰
- [x] `main.py`、`ui/`、`utils/` 所有 `print` 改為 logger（`scripts/` 保留 print）
- [x] `ui/theme.py`：深色精緻版主題 token 與 `qss()` 範本替換（尚未套用到現有 UI，留待階段 C）
- [x] `tests/` 測試骨架與 `requirements-dev.txt`（pytest 固定版本）

## 📌 階段 B: 同步修正與架構調整 (已完成，2026-11-24；尚未 commit，未實機驗證)
- [x] 新增 `services/`，取代並刪除 `utils/google_calendar.py` 與 `tests/test_google_calendar.py`
  - `event_mapping.py`：純函式（色彩 <-> 等級、Google event <-> 內部 dict、全天 end exclusive <-> inclusive、patch body、`month_range`、系統時區）
  - `google_client.py`：匯入無副作用；`httplib2.Http(timeout=15)` + `AuthorizedHttp`；分頁；OAuth `timeout_seconds=180`
  - `event_store.py`：`EventStore` 單一實例由 `main.py` 建立並注入 `CalendarView` / `SettingsView`
- [x] 移除 IPv4 `getaddrinfo` monkeypatch 與 `socket.setdefaulttimeout`（逾時改由 httplib2 層級設定）
- [x] 行程對話框新增「全天」核取方塊並帶入原日期時間；更新改用 `events().patch`
- [x] UI 安全與提示：rich text 以 `html.escape`、純文字 QLabel 設 PlainText；錯誤以 toast + QMessageBox 提示，fetch/check 相同錯誤去重
- [x] 新增測試：`test_event_mapping` / `test_event_store` / `test_google_client` / `test_calendar_view` / `test_calendar_dialog`（`python -m pytest -q`：125 passed）
- [x] `requirements.txt` 已固定 `httplib2==0.32.0`

## 📌 Phase 4: Google 日曆原生多階段提醒支援 (規劃中)
- [ ] `services/event_mapping.py` / `services/google_client.py`: 擴充 `to_google_body` / `build_patch_body` 支援傳送 `reminders.overrides`（包含 10 分鐘、30 分鐘、1 小時、1 天等多階段提醒）
- [ ] `services/event_mapping.py`: 擴充 `from_google` 行程解析讀取 Google API `reminders` 屬性
- [ ] `ui/calendar_dialog.py`: 行程新增/編輯對話框新增提醒時間選單（支援自訂多階段提醒）
- [ ] 跨平台與 Discord 整合相容：相容手機 App、網頁版與桌面端設定之提醒時間，棄用舊 `Calender` 專案獨特標籤，改為統一讀取 Google 原生 `reminders.overrides`

