# 系統架構與檔案結構 (System Architecture & File Structure)

## 1. 目錄與檔案結構預覽
```
secretary/
├── CLAUDE.md                     # AI 協作規範與作業紅線
├── requirements.txt              # 直接依賴（固定版本；含 PyQt6-WebEngine 供 MLB 頁使用）
├── requirements-dev.txt          # 開發依賴（pytest，固定版本）
├── .gitignore
├── assets/                       # 圖示資源
│   ├── logo.svg                  # 品牌 logo 原稿（深藍 #042C53 圓角方底＋白色 S 字，S 上半圈為錶面，中間天空藍 #85B7EB 指針與軸心，原色渲染，不重新上色）；側邊欄、get_app_icon 後備、icon.png / icon.ico 皆由它而來
│   ├── icon.ico / icon.png       # 應用程式圖示（由 icon_generator 自 logo.svg 產生；ico 內含 16/24/32/48/64/128/256 七種尺寸）
│   └── icons/*.svg               # UI 線條圖示（專案自繪，24 格、stroke currentColor；風格參考 Lucide（ISC 授權），非複製 Lucide 原始檔）；含 baseball.svg（MLB 導覽圖示）
├── docs/
│   ├── dev_rules.md              # 技術規範與設計指南（含 UI 規範、視覺預覽）
│   ├── progress.md               # 任務進度清單與已知問題
│   ├── architecture.md           # 本系統架構文件
│   └── dev_logs/                 # 開工/收工日誌目錄 (YYYYMMDD_主題.md)
├── data/                         # 執行期資料 (不進版控，整個資料夾被 .gitignore 排除)
│   ├── config.json / credentials.json / token.json
│   └── logs/                     # secretary.log，由 utils/logger.py 寫入，輪替 1MB x 3
├── main.py                       # 主程式入口：托盤、單一實例、喝水計時（WaterCountdown）、EventStore 建立與注入、toast 堆疊、套用全域樣式
├── scripts/                      # 開發/一次性工具腳本
│   ├── create_shortcut.py        # 建立桌面捷徑與啟動 .bat
│   ├── icon_generator.py         # 應用程式圖示產生器：QSvgRenderer 渲染 assets/logo.svg，輸出 icon.png（256）與多尺寸 icon.ico（各尺寸獨立渲染，手寫 PNG 內嵌 ICO）
│   └── render_preview.py         # offscreen 視覺預覽：假資料（FakeStore / FakeConfig）渲染各畫面成 PNG，不連網、不讀 data/
├── tests/                        # 自動化測試 (pytest；不連網、不開可見 GUI、不碰真實 data/)
│   ├── conftest.py               # 專案根加入 sys.path、日誌導向暫存目錄、session 範圍單一 offscreen QApplication
│   ├── test_autostart.py         # autostart 同步邏輯（假 winreg，不碰真 Registry）
│   └── test_*.py
├── services/                     # Google 日曆同步層（不含 UI 繪製）
│   ├── event_mapping.py          # 純函式：色彩<->等級、Google event<->內部 dict、全天 end 換算、patch body、month_range、系統時區
│   ├── google_client.py          # Google Calendar API 薄封裝（同步阻塞，須在背景執行緒呼叫；httplib2 逾時 15 秒；OAuth 逾時 180 秒）
│   └── event_store.py            # EventStore(QObject)：行程資料唯一來源、signals、ThreadPoolRunner / DaemonThreadRunner
├── ui/
│   ├── theme.py                  # 設計 token（顏色、字級、間距、圓角、版面尺寸、PRIORITY_*）與 qss() 範本替換；純資料，不依賴 PyQt6
│   ├── styles.py                 # 全域 QSS（依元件分段：按鈕、輸入、開關、選單、捲軸、導覽、工具列、面板、對話框、設定、toast…）、build_palette、apply_app_style、qcolor、make_font、fit_text、repolish
│   ├── icons.py                  # SVG 圖示載入與上色：icon()/pixmap()，處理高 DPI；QSS 用的上色圖示匯出
│   ├── components.py             # 共用元件：IconButton、SegmentedControl、SyncStatusBadge、LevelDot、level_color、level_bg、level_text、sync_state_presentation
│   ├── nav_sidebar.py            # 52px 圖示導覽列：Logo／日曆／喝水／MLB／設定（checkable 互斥）＋底部喝水倒數（set_countdown、format_countdown）
│   ├── main_window.py            # 主視窗外框：NavSidebar + QStackedWidget(CalendarView, WaterView, MlbView, SettingsView)，首次顯示啟用深色標題列，closeEvent 縮到托盤
│   ├── calendar_view.py          # 日曆頁：工具列（標題、‹ ›、今天、月/週/日、同步徽章、新增）+ 視圖區 + 右側面板；串接 EventStore
│   ├── calendar_logic.py         # 日曆純邏輯（不 import Qt widgets）：月格日期、週日期、行程日期解析、即將到來規則、還有 N 天、時間軸重疊分欄
│   ├── month_grid.py             # 月視圖（QPainter 自繪）
│   ├── time_grid.py              # 週／日共用時間軸視圖（QPainter 自繪）
│   ├── side_panel.py             # 右側 300px 面板：即將到來、選取日清單、等級圖例
│   ├── calendar_dialog.py        # 行程新增/編輯對話框（2 欄排版、等級色點、全天開關、DatePopupButton；開始/結束連動：改開始時結束依「目前長度」跟著移，結束早於開始時標紅並停用儲存）；提醒時間選單尚未實作
│   ├── confirm_dialog.py         # 共用確認對話框 ConfirmDialog（刪除、登出）
│   ├── settings_view.py          # 設定頁：段落式清單（一般、Google 日曆）；喝水提醒已移至 water_view.py
│   ├── water_view.py             # 喝水提醒頁：大字倒數（set_countdown，None 顯示「已停用」）＋啟用開關、提醒間隔、測試按鈕
│   ├── mlb_view.py               # MLB 每日頁：頂部標題＋「重新整理」，QWebEngineView 內嵌 MLB_DAILY_URL（首次顯示才建立並載入）；載入失敗顯示提示 QLabel；新視窗請求交給系統瀏覽器
│   ├── toast_window.py           # ToastWindow（info/water/danger、按鈕、關閉鈕、hover 暫停）與 ToastStack（多則堆疊與重排）
│   └── tray_menu.py              # 托盤右鍵選單建構（圖示、無 emoji）
└── utils/
    ├── autostart.py              # 開機自啟動登錄檔控制模組 (支援 --minimized 靜默啟動)；預設關閉，啟動時 `sync` 僅在 Registry 與設定不一致時才寫入／刪除（`plan_sync` 純函式決策，`get_registered_command` 唯讀）
    ├── config_manager.py         # 設定檔讀寫 (config.json)；save_config_or_warn 寫入失敗時提示使用者
    ├── logger.py                 # 日誌設定 (get_logger，RotatingFileHandler 寫入 data/logs/)
    ├── paths.py                  # 集中路徑定義
    ├── water_timer.py            # WaterCountdown：喝水倒數純邏輯（tick／snooze／reset，無 Qt）
    └── win_titlebar.py           # enable_dark_titlebar：DWM 深色標題列，失敗回傳 False 不 raise
```

## 2. 資料流與組件交互說明
1. **開機靜默啟動與托盤化**：系統開機啟動時 `main.py` 接收 `--minimized`，不呼叫 `window.show()`，直接隱藏於 `QSystemTrayIcon`。
2. **視窗關閉攔截 (`closeEvent`)**：`MainWindow.closeEvent` 依 config 的 `minimize_to_tray`（設定頁可切換）決定隱藏至托盤或結束。
3. **托盤右鍵選單**：`ui/tray_menu.py` 建構，含圖示的「顯示主視窗」「測試喝水提醒」「設定」「退出程式」，樣式由全域 QSS 的 QMenu 分段套用。
4. **Google 日曆與色彩標籤等級**：`services/event_mapping.py` 以 `extendedProperties.private.secretary_priority` 為主判斷等級，缺少或不合法時以 `colorId` 備援（11、4 大 30 天 / 5、6 中 7 天 / 2、10 小 3 天；未對應視為小事件），顯示為色條與圓點。
5. **喝水提醒**：`main.py` 每秒 tick `utils/water_timer.WaterCountdown`，到時以 `ToastStack` 顯示 water 樣式 toast（按鈕「延後 10 分鐘」「已喝」）；導覽列底部與喝水頁大字皆以 `set_countdown` 顯示剩餘時間（停用時餵 `None`）。喝水頁的測試按鈕只發 `test_toast_requested`，由 `main.py` 顯示 toast，確保仍走堆疊。
6. **Google 日曆原生多階段提醒 (reminders.overrides)**（Phase 4 規劃中，尚未實作）：透過 `services/event_mapping.py` 傳遞與讀取 API 原生 `reminders`。

### 2.1 設計系統（階段 C）
- `ui/theme.py` 為所有視覺數值的唯一來源；`ui/styles.py` 把 token 組成全域 QSS，由 `main.py` 以 `apply_app_style(app)` 一次套用（同時設定 palette 與全域字型，頂層視窗底色因此預設為 BG）。
- 元件以 objectName、動態屬性 `variant`（按鈕）與 `role`（語意 label）選擇樣式，切換屬性後呼叫 `repolish()`。
- 圖示：`assets/icons/*.svg` 為專案自繪的 24 格線條圖示，風格參考 Lucide（ISC 授權），非複製其原始檔；`ui/icons.py` 依 token 上色並處理高 DPI。
- 深色標題列：`utils/win_titlebar.py` 只呼叫 DWM 視窗屬性（不碰 Registry），主視窗與對話框 showEvent 時啟用。

### 2.2 日曆頁結構與設計取捨
- **導覽**：`NavSidebar` 為 52px 圖示列。頁面順序為 日曆(0)／喝水(1)／MLB(2)／設定(3)，與側欄按鈕順序一致（`PAGE_CALENDAR`／`PAGE_WATER`／`PAGE_MLB`／`PAGE_SETTINGS`），四顆按鈕都走 `set_active_page`。喝水為獨立頁面（`WaterView`）：頂部大字倒數，下方沿用設定頁的卡片列放開關、間隔、測試；`main.py` 每秒同時餵導覽列與喝水頁。
- **MLB 內嵌頁**：`MlbView` 以 `QWebEngineView` 內嵌 `https://haolun588.github.io/MLB-daily/index.html`（常數 `MLB_DAILY_URL`）。第一次顯示該頁才建立 view 並載入（延遲載入，不拖慢啟動）；`loadFinished(False)` 時顯示「無法載入 MLB 頁面，請檢查網路後按重新整理」；網頁開新視窗（`newWindowRequested`）改由 `QDesktopServices` 用系統瀏覽器開啟。QtWebEngine 要求在建立 `QApplication` 前先 `import PyQt6.QtWebEngineWidgets`，故 `main.py` 與 `tests/conftest.py` 都有此 import。
- **自繪而非現成元件**：月視圖、時間軸以 QPainter 自繪，不用 `QCalendarWidget` 或 `QTableView`+delegate。理由：格內色條 chip、「+N」、今天淡底需精細控制；命中測試是純幾何，可直接單元測試；時間軸的重疊並排分欄與現在時間線，標準元件無法表達。（`DatePopupButton` 彈出的小月曆仍是 `QCalendarWidget`，僅供挑日期。）
- **純邏輯分離**：`calendar_logic.py` 不依賴 Qt widgets，涵蓋月格 42 格、週日期、`parse_event_dates`、`upcoming`、`timed_layout` 等，有完整單元測試。
- **右側面板**：「即將到來」規則為明天以後依等級 30/7/3 天內、含進行中行程、排除已結束的定時行程、今天開始的只出現在選取日清單；另有選取日清單與等級圖例。

### 2.3 日曆資料流
`EventStore` signals → `CalendarView`（`events_changed`、`sync_state_changed`）／`SettingsView`（`sync_state_changed`、`auth_state_changed`）／`SyncStatusBadge`（經 `CalendarView` 轉入 `set_state`）。拉取範圍：月／日視圖以選取日所在月份、週視圖以該週第一天所在月份呼叫 `ensure_month`，`EventStore` 自帶前後各一個月。

## 3. 行程同步資料流（階段 B）
```
UI (CalendarView / SettingsView / CalendarDialog)
   │  呼叫 add_event / update_event / delete_event / ensure_month / authorize
   ▼
EventStore (主執行緒，單一實例，由 main.py 建立並注入各 view)
   │  把工作交給 runner
   ▼
ThreadPoolRunner（單執行緒 QThreadPool，API 呼叫依序執行）
OAuth 授權改用 DaemonThreadRunner（獨立 daemon 執行緒，不佔用 API pool）
   │  worker 內自建 service（每個 worker 一個，httplib2 非 thread-safe）
   ▼
services/google_client.py ──► Google Calendar API
   │  結果（成功值或例外）以 QueuedConnection signal 回主執行緒
   ▼
EventStore 更新本地清單（寫入成功才更新；fetch 失敗保留舊資料；過期世代的 fetch 結果丟棄）
   ├─► events_changed(list) ──► CalendarView 重繪月/週/日視圖、「即將到來」與選取日清單
   ├─► sync_state_changed / auth_state_changed ──► SettingsView 更新狀態
   ├─► operation_succeeded(action)
   └─► operation_failed(action, 訊息) ──► main.py：toast；寫入類（add/update/delete/auth）另跳 QMessageBox
                                          （fetch/check 相同訊息連續只提示一次）
```
- 內部 event dict 欄位：`id, title, all_day, start, end, priority, location, notes, color_id`；全天事件 `end` 為含當天（Google `end.date` 減 1 天）。
- 拉取範圍為 `ensure_month` 指定月份前後各一個月（`month_range`），切換月份／週自動拉取；錨點規則見 2.3。
- UI 不直接呼叫 `google_client`，一律經 `EventStore`。
