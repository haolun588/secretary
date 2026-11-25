# Secretary 專案開發進度清單 (Development Progress)

## 📌 Phase 1: 基礎架構與桌面 UI 介面 (已完成；UI 已由階段 C 取代)
- [x] PyQt6 專案目錄結構與主程式建立 (`main.py`, `ui/`)
- [x] 暗黑高顏值主題與電光紫配色 (`#121217`, `#1c1c24`, `#8b5cf6`)（已由階段 C 的 `ui/theme.py` token 取代；現行為深藍底＋天空藍主色，見「配色改版」與「藍色 logo 與主色改版」）
- [x] 左側導覽列 `NavSidebar` (日曆與行程 / 喝水與設定)（階段 C 改為 52px 圖示導覽列）
- [x] 中間月曆 `CalendarView` (440px 寬、1:1 置中、週末電光紫字體)（階段 C 改為自繪月／週／日視圖，已無 QCalendarWidget）
- [x] 右側提醒面板 `SidebarFrame` (340px 緊貼右側、雙行頂部導覽列)（階段 C 改為 300px `SidePanel`）
- [x] 選取日期當日行程卡片 `TodayEventCard` (標題/地點/備註獨立三行、100% 依字數自適應高度、`word-break: break-all` 自動折行)

## 📌 Phase 2: 喝水提醒與系統整合 (已完成)
- [x] 螢幕右下角 3 秒淡出 Toast 提醒視窗 (`ToastWindow`)（階段 C 起喝水 toast 含按鈕時顯示 8 秒、hover 暫停）
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
- [x] 桌面 256x256 高畫質電光圖示 `icon.png` / `icon.ico`（現為深藍底 S 字時鐘 logo，見「藍色 logo 與主色改版」）
- [x] Windows 桌面捷徑 `Secretary 智能桌面小助理.lnk` 自動建立

## ⚠️ 已知問題（2026-11-24 審查）
1. ~~編輯行程時對話框不帶入原日期時間、全天行程被轉成定時、`events().update` 整筆覆蓋。~~（2026-11-24 階段 B 已處理：對話框新增「全天」核取方塊並帶入原日期時間；更新改用 `events().patch`，由 `build_patch_body` 只送變動欄位）
2. ~~OAuth 在主執行緒執行且 `run_local_server` 無逾時。~~（2026-11-24 階段 B 已處理：OAuth 改在 `DaemonThreadRunner` 獨立 daemon 執行緒執行，`timeout_seconds=180`；僅 8080 綁定失敗才改 port 0，不會開第二次瀏覽器）
3. ~~新增行程使用假 id、寫入失敗仍修改本地資料且無提示。~~（2026-11-24 階段 B 已處理：使用 Google 回傳的 id，寫入成功才更新本地；失敗發出 `operation_failed`，由 `main.py` 以 toast + QMessageBox 提示）
4. ~~雲端回傳空清單時本地不清空，離線與無行程無法區分。~~（2026-11-24 階段 B 已處理：`EventStore` 區分 fetch 失敗（保留本地並提示）與成功但空清單（清空））
5. ~~新增/編輯/刪除與啟動時 `check_connection` 在主執行緒阻塞。~~（2026-11-24 階段 B 已處理：全部經 `EventStore` 的單執行緒 `ThreadPoolRunner` 在背景執行，結果以 QueuedConnection 回主執行緒）
6. ~~背景 fetch 與 UI 共用同一個 service，httplib2 非 thread-safe。~~（2026-11-24 階段 B 已處理：每個 worker 自建 service，`httplib2.Http(timeout=15)` + `AuthorizedHttp`，且 API 呼叫由單執行緒 pool 序列化）
7. ~~日誌使用 `print`，在 `pythonw` 下全部遺失。~~（2026-11-24 階段 A 已處理：改用 `utils/logger.py`，寫入 `data/logs/secretary.log`）
8. ~~autostart 預設開啟，且每次啟動都寫入 Registry。~~（2026-11-25 階段 D 已處理：預設改為關閉；啟動改呼叫 `AutoStartManager.sync`，只在 Registry 與設定不一致時才寫入或刪除；寫入失敗以 danger toast 提示。注意：已存有 `autostart: true` 的舊 config 仍維持開啟）
9. ~~只抓 `timeMin=now`、`maxResults=100`，未處理 `nextPageToken`；過去日期空白。~~（2026-11-24 階段 B 已處理：改拉取目前顯示月份前後各一個月（`ensure_month`），切換月份自動拉取，處理分頁，過去日期可顯示）
10. ~~箭頭圖示 QSS 使用相對路徑 `assets/...`~~（2026-11-24 工作區整理已修正：改用 `utils/paths.py` 絕對路徑）。
11. ~~尚無自動化測試。~~（2026-11-24 階段 A 已建立 `tests/` 測試骨架，`python -m pytest` 全數通過）
12. ~~重複／未使用程式碼~~（2026-11-24 工作區整理已修正：刪除 `preview_ui.py`、`utils/shortcut_creator.py`，產生器與捷徑腳本移至 `scripts/`）。
13. logout 與排隊中 job 寫回 token 的競態：`EventStore.logout()` 後，已排隊的 job 仍可能把憑證寫回 token 檔（UI 尚未接上 logout，目前不會觸發）。
14. `local_tz()` 取目前時間的固定 offset，有夏令時間（DST）的地區，跨 DST 的日期會差 1 小時（台灣不受影響）。
15. 定時行程改成全天時，原 `start.timeZone` 是否需一併清除，尚未對 Google 實測。
16. 任何 `RefreshError` 都會清掉本地憑證，含可能可重試的情況（例如暫時性網路／伺服器錯誤）。
17. 右側「即將到來」側欄仍受拉取範圍影響（`ensure_month` 前後各一個月），瀏覽到 2 個月以外時可能變空。現行規則：明天以後的行程依等級 30/7/3 天內顯示、含進行中行程、排除已結束的定時行程；今天開始的只出現在選取日清單。
18. `main.py` 單一實例 socket 名稱（`SINGLE_INSTANCE_SOCKET`）含使用者名稱，屬寫死個人資訊，應改為動態或通用名稱。

19. 週視圖 7 欄時，3 筆以上重疊的行程欄位很窄，僅顯示標題前幾字，需靠 tooltip 看全文。
20. offscreen 預覽的中文需由 `render_preview` 載入 `msjh.ttc`；實機不受影響。
21. ~~`assets/arrow_up.png`、`arrow_down.png` 與 `scripts/arrow_generator.py` 已無程式引用，`utils/paths.qss_url` 亦已無 UI 使用。~~（2026-11-25 階段 D 已處理：刪除兩張箭頭圖、`arrow_generator.py`，移除 `qss_url` 與其測試）
22. ~~`tests/test_event_store.py` 的 `processEvents` 會遺留事件，全套件中曾造成 access violation。~~（2026-11-25 階段 D 已處理：`_wait` 改用 `QCoreApplication.sendPostedEvents(None, QEvent.Type.MetaCall)`，只派送 QueuedConnection 回呼，不處理其他測試遺留的 DeferredDelete）
23. `DatePopupButton` 的彈出月曆仍是 `QCalendarWidget`（僅供挑日期），未做預覽。
24. 配色改版後，中等級（琥珀 `#fbbf24`）的半透明底疊在深藍 SURFACE_2 上偏橄欖褐色，與大（玫瑰）、小（藍）相比不夠乾淨，之後可能需調整 `PRIORITY_BG` 的中等級值。

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

## 📌 階段 C: 深色精緻版視覺與排版重設計 (2026-11-25 完成；已 commit，未實機驗證)
- [x] 設計系統（26b4612）：`ui/theme.py` 新增版面與狀態 token；`ui/styles.py`（全域 QSS、palette、`qcolor`、`repolish`）；`ui/icons.py` + `assets/icons/*.svg`（自繪線條圖示）；`ui/components.py`（IconButton、SegmentedControl、SyncStatusBadge、LevelDot）；`utils/win_titlebar.py` 深色標題列；`scripts/render_preview.py`；`tests/conftest.py` 改 session 範圍 offscreen QApplication
- [x] 主視窗與導覽（5beb90c）：`NavSidebar` 52px 圖示列（checkable 互斥，修正舊 `.NavBtn` 選取樣式未生效）；喝水按鈕切到設定頁喝水區塊；底部倒數 `set_countdown`；`MainWindow` 改用 token 並啟用深色標題列
- [x] 日曆頁（3a5fecd）：`calendar_logic`（純邏輯）、`MonthGrid`、`TimeGrid`（QPainter 自繪）、`SidePanel`、重寫 `CalendarView`（月/週/日、同步徽章、重疊並排分欄、現在時間線、即將到來新規則）
- [x] 對話框、設定、toast、托盤（e3a32ef）：`CalendarDialog` 2 欄排版、`ConfirmDialog`、段落式 `SettingsView`（新增「關閉視窗時縮到系統匣」與 Google 登入／登出）、`ToastWindow`／`ToastStack`、`tray_menu`、`WaterCountdown`（延後 10 分鐘／已喝）、`save_config_or_warn`、`main.py` 套用全域樣式
- 測試狀態：`python -m pytest -q`：382 passed。
- 未實機驗證：實際畫面與字型、深色標題列（主視窗與對話框）、高 DPI（125%/150% 下圖示與 1px 線）、最小視窗 960×620、月週日切換與 ‹ › 今天、雙擊新增／點行程編輯、對話框全天切換與儲存回寫、刪除確認、toast 按鈕（延後 10 分鐘、已喝）與 hover 暫停、多則 toast 堆疊、托盤選單樣式、設定頁各開關寫入 config、Google 登入／登出、關閉視窗縮到系統匣。

## 📌 配色改版 (2026-11-25 完成；未 commit，未實機驗證)
- [x] 整體色調改為深藍底（BG `#0d1322` 等）＋青綠主色（ACCENT `#2dd4bf`）；`TEXT_ON_ACCENT` 改深色 `#04201c`，新增 `TEXT_ON_DANGER` `#ffffff` 供 danger 按鈕；DANGER／SUCCESS／WARNING 值調整
- [x] 行程等級色與語意色脫鉤：`PRIORITY` 大 `#fb7185` 玫瑰、中 `#fbbf24` 琥珀、小 `#60a5fa` 藍；新增 `PRIORITY_BG` / `PRIORITY_BG_HOVER` / `PRIORITY_TEXT`；`ui/components.py` 新增 `level_bg()`、`level_text()`
- [x] 月視圖 chip、週／日視圖行程區塊、全天 chip 改為整格依等級上色（先鋪不透明 SURFACE_2 再疊半透明 level_bg，文字用 level_text，保留左側 LEVEL_BAR 色條）
- [x] `scripts/icon_generator.py`、`scripts/arrow_generator.py` 改用 theme token 並補 `sys.path`，重新產生 `assets/icon.png`、`icon.ico`、`arrow_up.png`、`arrow_down.png`（app 圖示改為青綠底）
- [x] `services/google_client.py` 的 OAuth 授權成功頁改用 theme 色值並改為深底
- [x] 新增測試：`PRIORITY_*` 格式、WCAG 對比度、`level_bg`/`level_text` fallback；`python -m pytest -q`：389 passed
- 未實機驗證：實際畫面配色與對比、月／週／日整格上色觀感、新 app 圖示與授權成功頁。

## 📌 階段 D: autostart 與清理 (2026-11-25 完成；未 commit，未實機驗證)
- [x] autostart（已知問題 8）：預設關閉（`config_manager`、`main.py`、`settings_view`）；`utils/autostart.py` 新增 `get_registered_command()`（KEY_READ 唯讀）、純函式 `plan_sync(desired, current_cmd, expected_cmd)`、`AutoStartManager.sync(desired)`；啟動改呼叫 `sync`，僅在不一致時寫入／刪除（路徑變動自動修正）；`set_autostart` 權限由 KEY_ALL_ACCESS 縮為 KEY_SET_VALUE 並 try/finally CloseKey
- [x] 失敗提示：啟動同步失敗或設定頁切換失敗以 danger toast 提示；切換失敗時還原核取方塊且不寫 config
- [x] 清理（已知問題 21）：刪除 `assets/arrow_up.png`、`arrow_down.png`、`scripts/arrow_generator.py`；移除 `utils/paths.qss_url` 與其測試
- [x] 測試穩定（已知問題 22）：`test_event_store._wait` 改用 `sendPostedEvents(None, MetaCall)`
- [x] 新增 `tests/test_autostart.py`（12 個測試，假 winreg，不碰真 Registry）；`test_settings_view::test_autostart_signal` 因預設改 False 調整切換順序
- 測試狀態：`python -m pytest -q`：405 passed。
- 未實機驗證：`main.py` 的 `on_autostart_toggled` 需整個 GUI 才能測，未寫單測。待驗證：設定頁開關開機啟動後 Registry 正確、重開機自啟並最小化、舊 config 升級後行為。

## 📌 Phase 4: Google 日曆原生多階段提醒支援 (規劃中)
- [ ] `services/event_mapping.py` / `services/google_client.py`: 擴充 `to_google_body` / `build_patch_body` 支援傳送 `reminders.overrides`（包含 10 分鐘、30 分鐘、1 小時、1 天等多階段提醒）
- [ ] `services/event_mapping.py`: 擴充 `from_google` 行程解析讀取 Google API `reminders` 屬性
- [ ] `ui/calendar_dialog.py`: 行程新增/編輯對話框新增提醒時間選單（支援自訂多階段提醒）
- [ ] 跨平台與 Discord 整合相容：相容手機 App、網頁版與桌面端設定之提醒時間，棄用舊 `Calender` 專案獨特標籤，改為統一讀取 Google 原生 `reminders.overrides`


## 📌 等級改存 extendedProperties (2026-11-25 完成；未 commit，未對真實 Google 實測)
- [x] 等級改以 `extendedProperties.private.secretary_priority` 為主，`colorId` 為備援；衝突以 extendedProperties 為準，舊事件不主動補寫（`services/event_mapping.py`：`priority_from_item`、`extended_properties_for`；`to_google_body` 與 `build_patch_body` 同步寫入）
- 待驗證：`events.patch` 對 `extendedProperties.private` 的 key 合併行為

## 📌 日期連動與喝水頁 (2026-11-25 完成；未 commit，未實機驗證)
- [x] 事件對話框開始/結束連動：`DatePopupButton` 新增 `dateChanged`（僅使用者選日期時發出，`setDate` 不發）；對話框記錄「目前長度」（定時為分鐘、全天為天數），改開始日期/時間時結束跟著移並正確跨日，非 30 分整的結果會插入 combo 選項
- [x] 結束早於開始時，結束日期鈕與時間 combo 標 `invalid`（紅框，`ui/styles.py`），儲存鈕停用；恢復後清除。切換全天會重算長度並重跑檢查；`accept()` 的 `_validation_error` 保留為最後防線
- [x] 喝水改為獨立頁面 `ui/water_view.py`（大字倒數＋啟用/間隔/測試）；導覽頁面常數改為 `PAGE_CALENDAR=0`／`PAGE_WATER=1`／`PAGE_SETTINGS=2`，移除 `water_requested`、`on_water_requested`、設定頁喝水區塊與 `scroll_to_water`；`main.py` 改綁 `water_view` 並每秒餵倒數；新增 `theme.FONT_DISPLAY`
- 測試狀態：`python -m pytest -q`：439 passed。
- 未實機驗證：對話框連動與紅框在實機的觀感、喝水頁實際畫面、托盤「系統與提醒設定」仍跳到設定頁（程式路徑未變）。

## 📌 Logo 改版 (2026-11-25 完成；未 commit，未實機驗證)
- [x] 新增 `assets/logo.svg`（青綠漸層圓角方塊＋白色日曆＋時鐘）；`scripts/icon_generator.py` 改為由它渲染 `icon.png`（256）與 7 尺寸 `icon.ico`
- [x] 側邊欄 logo 改以原色渲染（`icons.logo_pixmap`），移除舊 `assets/icons/logo.svg`（單色勾勾方框）；`get_app_icon()` 後備改用新 logo
- [x] `main.py` 於 Windows 建立 QApplication 前設定 AppUserModelID `Secretary.DesktopAssistant`，避免工作列顯示 Python 圖示／群組
- 測試狀態：`python -m pytest -q`：443 passed。
- 未實機驗證：工作列／標題列／系統匣實際顯示；既有桌面捷徑需重新執行 `scripts/create_shortcut.py` 才會換圖示，Windows 圖示快取可能需重新整理（`ie4uinit.exe -show`）。

## 📌 藍色 logo 與主色改版 (2026-11-25 完成；未實機驗證)
- [x] `assets/logo.svg` 換成新 logo：深藍圓角方底 `#042C53`、白色 S 字，S 上半圈當錶面，中間天空藍 `#85B7EB` 指針與軸心；`assets/icon.png`、`icon.ico` 由 `scripts/icon_generator.py` 重新產生（app 圖示、側邊欄 logo、捷徑圖示隨之改變）
- [x] `ui/theme.py` 主色由青綠改為天空藍：ACCENT `#85b7eb`、ACCENT_HOVER `#6aa3e0`、ACCENT_MUTED／SOFT 改為 `rgba(133,183,235,…)`、TEXT_ON_ACCENT `#042c53`
- [x] 行程等級 minor 由藍 `#60a5fa` 改為青綠 `#2dd4bf`（BG／HOVER 為 `rgba(45,212,191,…)`，TEXT `#ccfbf1`），避免與新主色撞色
- 測試狀態：`python -m pytest -q`：450 passed。
- 未實機驗證：實際畫面與圖示；既有桌面捷徑需重新執行 `scripts/create_shortcut.py` 才會換圖示。

## 📌 MLB 每日內嵌頁面 (2026-11-25 完成)
- [x] 新增 `ui/mlb_view.py`（`MlbView`、`MLB_DAILY_URL = https://haolun588.github.io/MLB-daily/index.html`）：`QWebEngineView` 內嵌 MLB-daily 網頁；頂部「MLB 每日」標題與「重新整理」按鈕；第一次顯示才建立 view 並載入（延遲載入）；`loadFinished(False)` 以 QLabel 提示「無法載入 MLB 頁面，請檢查網路後按重新整理」；`newWindowRequested` 交給 `QDesktopServices` 用系統瀏覽器開啟
- [x] 新增 `assets/icons/baseball.svg` 導覽圖示
- [x] `ui/nav_sidebar.py` 新增 `PAGE_MLB = 2`，`PAGE_SETTINGS` 由 2 改為 3；導覽順序 日曆、喝水、MLB、設定；`ui/main_window.py` 堆疊 0=日曆、1=喝水、2=MLB、3=設定
- [x] `main.py` 與 `tests/conftest.py` 在建立 QApplication 前 `import PyQt6.QtWebEngineWidgets`（QtWebEngine 的要求）
- [x] `requirements.txt` 新增 `PyQt6-WebEngine==6.11.0`
- 測試狀態：語法檢查通過；`python -m pytest -q`：447 passed。使用者已在自己環境實際開啟並確認頁面正常顯示。
- 已知注意事項：在 Claude Code 代理的受限執行環境中，初始化 WebEngine 會以 0xC0000409 崩潰（與專案程式無關，推測為環境限制），自動化環境無法實測網頁載入；網頁載入需在使用者本機驗證。

## 📌 標題換行單行化 (2026-11-25 完成)
- [x] 修正行程標題含換行（例如 `Introduction to Digital\nCommunication`）時，月曆 chip、週／日行程區塊與右側面板只預留一行高度、`elidedText` 不處理 `\n` 導致文字上下被切的問題
- [x] `ui/styles.py` 新增 `single_line(text)`（空白字元合併為單一空格並去頭尾）；`fit_text` 先單行化再 elide；`ui/side_panel.py` 的 `_ElidedText` 繪製與 `sizeHint` 改用單行化文字，`text()` 與 tooltip 保留原文
- 測試狀態：語法檢查通過、`python -m pytest -q`：450 passed。未實機驗證畫面。
