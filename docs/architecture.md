# 系統架構與檔案結構 (System Architecture & File Structure)

## 1. 目錄與檔案結構預覽
```
secretary/
├── CLAUDE.md                     # AI 協作規範與作業紅線
├── requirements.txt              # 直接依賴（固定版本；httplib2 尚待補列，見 progress.md 階段 B）
├── requirements-dev.txt          # 開發依賴（pytest，固定版本）
├── .gitignore
├── assets/                       # 圖示資源 (icon.ico / icon.png / arrow_up.png / arrow_down.png)
├── docs/
│   ├── dev_rules.md              # 技術規範與設計指南 (含托盤化與開機靜默啟動)
│   ├── progress.md               # 任務進度清單與已知問題
│   ├── architecture.md           # 本系統架構文件
│   └── dev_logs/                 # 開工/收工日誌目錄 (YYYYMMDD_主題.md)
├── data/                         # 執行期資料 (不進版控，整個資料夾被 .gitignore 排除)
│   ├── config.json               # 使用者設定檔
│   ├── credentials.json          # Google OAuth 憑證
│   ├── token.json                # Google OAuth token
│   └── logs/                     # 日誌目錄 (secretary.log，由 utils/logger.py 寫入，輪替 1MB x 3)
├── main.py                       # 主程式入口 (托盤圖示 QSystemTrayIcon、closeEvent 攔截與背景計時器)
├── scripts/                      # 開發/一次性工具腳本 (可直接 python scripts/xxx.py 執行)
│   ├── create_shortcut.py        # 建立桌面捷徑與啟動 .bat
│   ├── arrow_generator.py        # 箭頭圖示產生器
│   └── icon_generator.py         # 應用程式圖示產生器
├── tests/                        # 自動化測試 (pytest；不連網、不啟動 GUI、不碰真實 data/)
│   ├── conftest.py               # 專案根加入 sys.path，並將測試期日誌導向暫存目錄
│   └── test_*.py                 # theme / paths / config_manager / logger / event_mapping / event_store / google_client / calendar_view / calendar_dialog
├── services/                     # Google 日曆同步層（不含 UI 繪製）
│   ├── __init__.py
│   ├── event_mapping.py          # 純函式：色彩<->等級、Google event<->內部 dict、全天 end 換算、patch body、month_range、系統時區
│   ├── google_client.py          # Google Calendar API 薄封裝（同步阻塞，須在背景執行緒呼叫；匯入無副作用；httplib2 逾時 15 秒；OAuth 逾時 180 秒）
│   └── event_store.py            # EventStore(QObject)：行程資料唯一來源、signals、ThreadPoolRunner / DaemonThreadRunner
├── ui/
│   ├── main_window.py            # 主視窗外框 (包含 closeEvent 重寫，點擊 ✕ 隱藏至托盤)
│   ├── nav_sidebar.py            # 左側選單欄元件
│   ├── calendar_view.py          # 日曆頁面 (含大/中/小色彩標籤過濾提醒側邊欄)
│   ├── settings_view.py          # 設定頁面 (喝水提醒間隔、開機自啟動控制)
│   ├── calendar_dialog.py        # 行程新增/修改對話框 (含事件等級選單與刪除確認；提醒時間選單尚未實作)
│   ├── theme.py                  # 深色精緻版主題 token 與 qss() 範本替換 (純資料，不依賴 PyQt6)
│   └── toast_window.py           # 右下角喝水提醒彈窗 (含 3 秒淡出動畫)
└── utils/
    ├── autostart.py              # 開機自啟動登錄檔控制模組 (支援 --minimized 靜默啟動)
    ├── config_manager.py         # 設定檔讀寫模組 (config.json 持久化)
    ├── logger.py                 # 日誌設定 (get_logger，RotatingFileHandler 寫入 data/logs/)
    └── paths.py                  # 集中路徑定義 (data/、assets/ 絕對路徑與舊檔搬遷)
```

## 2. 資料流與組件交互說明
1. **開機靜默啟動與托盤化**：
   - 當系統開機啟動，`main.py` 接收到 `--minimized` 參數，不呼叫 `window.show()`，直接隱藏於 `QSystemTrayIcon`。
2. **視窗關閉攔截 (`closeEvent`)**：
   - 當使用者點擊視窗右上角的 `✕` 關閉按鈕，`main_window.py` 攔截事件並呼叫 `event.ignore()` 與 `self.hide()`，視窗隱藏至系統托盤持續運作。
3. **托盤右鍵選單**：
   - 提供「顯示小助理主視窗」、「測試喝水提醒彈窗」、「系統與提醒設定」、「退出程式」四項。
4. **Google 日曆與色彩標籤過濾**：
   - `services/event_mapping.py` 解析 Google 日曆的 `colorId`（11、4 大 30 天 / 5、6 中 7 天 / 2、10 小 3 天；未對應顏色視為小事件），並呈現於右側提醒欄。
5. **Google 日曆原生多階段提醒 (reminders.overrides)**（Phase 4 規劃中，尚未實作）：
   - 透過 `services/event_mapping.py`（`to_google_body` / `build_patch_body` / `from_google`）傳遞與讀取 API 原生 `reminders` 屬性（如 10 分鐘前、1 小時前、1 天前等多重提醒分鐘數）。
   - 確保在 `secretary` 桌面端、手機 Google 日曆 App 或網頁版設定的提醒皆能同步，並供背景/雲端 Bot 統一輪詢發送提醒。

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
   ├─► events_changed(list) ──► CalendarView 重繪月曆與「即將到來」側欄
   ├─► sync_state_changed / auth_state_changed ──► SettingsView 更新狀態
   ├─► operation_succeeded(action)
   └─► operation_failed(action, 訊息) ──► main.py：toast；寫入類（add/update/delete/auth）另跳 QMessageBox
                                          （fetch/check 相同訊息連續只提示一次）
```
- 內部 event dict 欄位：`id, title, all_day, start, end, priority, location, notes, color_id`；全天事件 `end` 為含當天（Google `end.date` 減 1 天）。
- 拉取範圍為目前顯示月份前後各一個月（`ensure_month` / `month_range`），切換月份自動拉取。
- UI 不直接呼叫 `google_client`，一律經 `EventStore`。
