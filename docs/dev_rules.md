# 專案開發規範與技術指南 (Dev Rules & Tech Guidelines)

> AI 協作規範見根目錄 `CLAUDE.md`。

## 1. 專案目標與核心功能
本專案名為 **Secretary (桌面小助理)**，主要功能包括：
- **背景執行與托盤化 (Minimize to Tray)**：
  - 點擊主視窗右上角「✕ (關閉)」按鈕時，攔截 `closeEvent`，**隱藏視窗至系統托盤 (System Tray) 並持續於背景運行**，不直接結束程式。退出程式僅能透過托盤右鍵選單點擊「退出程式」。
- **開機自動靜默啟動 (Silent Boot Auto-Start)**：
  - Windows 開機自動啟動時代入 `--minimized` 參數，**直接隱藏於背景系統托盤**，不主動跳出主視窗干擾使用者。
- **左側圖示導覽列 (Icon Navigation)**：52px 圖示列（日曆／喝水／設定）；喝水按鈕切到設定頁並捲到喝水區塊。
- **定時喝水提醒**：每 N 分鐘（預設 10 分鐘，可透過 UI 調整）於螢幕右下角彈出 toast，提供「延後 10 分鐘」「已喝」按鈕；有按鈕時顯示至少 8 秒，hover 時暫停倒數，之後淡出 (Fade-out)；多則 toast 由 `ToastStack` 堆疊。
- **Google 日曆整合與色彩標籤等級對應**：
  - 主介面整合日曆，支援串接 Google Calendar API。
  - **Google 日曆色彩標籤 (Event Color ID) 對應規則**（以 `services/event_mapping.py` 的 `COLOR_PRIORITY_MAP` 為準）：
    - **Color ID 11 (Tomato)、4 (Flamingo)** ➔ **大事件 (提前 30 天/1個月顯示於右側提醒欄)**
    - **Color ID 5 (Banana)、6 (Tangerine)** ➔ **中事件 (提前 7 天/1週顯示於右側提醒欄)**
    - **Color ID 2 (Sage)、10 (Basil)** ➔ **小事件 (提前 3 天顯示於右側提醒欄)**
    - **未對應的顏色與預設色（無 colorId，或其他 ID 如 1、3、7、8、9）** ➔ 實際被當成**小事件**（`priority_from_color` 預設值為 `minor`）。
- **Google 日曆原生多階段提醒 (reminders.overrides)**：
  - 全面使用 Google API 原生 `reminders` 欄位傳遞與讀取通知時間（支援多選：如 10 分鐘前、30 分鐘前、1 小時前、1 天前）。
  - 與手機 App 及網頁版設定完美跨平台同步，棄用外掛獨立文字標籤，供其他提醒端統一讀取。（雲端 Bot / Discord 不屬於本 repo 範圍。）

## 2. 技術選型與約束 (Tech Stack & Constraints)
- **作業系統目標**：Windows 10 / 11
- **UI & 框架**：採用 Python + PyQt6，以 `QStackedWidget` 結合左側圖示導覽列 (`NavSidebar`) 切換分頁。
- **系統托盤與關閉事件**：使用 `QSystemTrayIcon`，實現右鍵選單 (顯示主視窗 / 測試喝水提醒 / 系統與提醒設定 / 退出程式)。
- **開機自啟**：透過 Windows Registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`) 寫入包含 `pythonw main.py --minimized` 之啟動命令。
- **設定儲存**：採用 JSON 格式儲存使用者設定 (`data/config.json`)。
- **異常處理與日誌**：外部 API、檔案存取、登錄檔寫入須有 try-except，並使用 Python `logging` 寫入檔案（`utils/logger.py`，含時間戳，`RotatingFileHandler`；日誌檔位於被 `.gitignore` 排除的 `data/logs/`）。因 `pythonw` 沒有 stdout，`print` 不能當作日誌。

### 2.1 日誌規範
- 每個模組以 `from utils.logger import get_logger` 與 `logger = get_logger(__name__)` 取得 logger，**不使用 `print`**（`scripts/` 例外）。
- 等級：一般狀態用 `info`，可忽略的異常用 `warning`，`except` 內的錯誤用 `logger.exception(...)` 保留 traceback，其他錯誤用 `error`。
- 日誌檔位於 `data/logs/secretary.log`（`utils/paths.py` 的 `LOGS_DIR`）。`utils/paths.py` 為避免循環匯入，於函式內才取得 logger。
- 第三方套件（`googleapiclient`、`google.auth`）的 WARNING 以上訊息會寫入同一個日誌檔。
- 日誌不得記錄個資：行程標題、自啟命令等內容不寫入 info 以上等級（事件以 Google 回傳的 id 識別）。

### 2.2 UI 規範（主題 token 與樣式）
- **token 唯一來源**：顏色、字級（12/13/15/18/22）、字重（400/600）、間距（4 的倍數，`SPACE_*`）、圓角（6/10/14 或 0）一律取自 `ui/theme.py`；固定尺寸（導覽寬、控制高、圖示、toast 寬等）也放 theme，不在各檔寫死像素。
- **禁止項**：`ui/` 內除 `theme.py`、`styles.py` 外，不得出現 hex 色碼、`rgb(`/`rgba(` 字面值與 emoji。
- **樣式集中於 `ui/styles.py`**：全域 QSS 依元件分段，由 `apply_app_style(app)` 套用（同時設定 palette 與字型；全域 palette 已設 Window=BG）。元件以 objectName、動態屬性 `variant`（`primary`/`secondary`/`ghost`/`danger`，另有 `danger` 的 soft 變體）與 `role` 選擇；切換屬性後呼叫 `repolish(widget)`。不在各 UI 檔以 `setStyleSheet` 寫大段 QSS，少量動態樣式用 `qss()` + token（只替換 `{全大寫TOKEN}`，未知 token 會 raise `KeyError`；`px` 單位自行撰寫）。
- **QPainter**：顏色用 `qcolor(theme.X)`（支援 `#rrggbb` 與 `rgba()`），字型用 `make_font()`，截斷文字用 `fit_text()`。
- **圖示**：用 `ui.icons.icon()` / `pixmap()`。新增圖示需手寫 24 格線條 SVG（viewBox 0 0 24 24、fill none、stroke currentColor、stroke-width 2、round cap/join）放 `assets/icons/`，不下載、不複製他人檔案。
- **色彩使用**：主色 `ACCENT` 只用於選取狀態與主要按鈕，且每頁至多一顆 primary；等級紅/黃/綠只用於色條與圓點，不整顆元件上色。
- **頂層 QWidget**（對話框、toast、彈出視窗）需自設底色或設 `WA_TranslucentBackground`。

### 2.3 測試規範
- 測試放在 `tests/`，以 `python -m pytest` 執行；開發依賴見 `requirements-dev.txt`。
- 測試不得啟動 GUI、不得連網（Google API / OAuth）、不得碰真實 `data/`，檔案一律使用 `tmp_path` + `monkeypatch`。
- `services/google_client` 匯入時無副作用（不修改全域 `socket.getaddrinfo` 與預設逾時），測試以假 service / 假 client 注入，不需額外還原。
- UI 測試共用 `tests/conftest.py` 的 session 範圍 offscreen `QApplication`，不自建 QApplication。
- 避免在測試中呼叫 `QApplication.processEvents()`：全套件執行時曾因 `tests/test_event_store.py` 遺留事件造成 access violation；新測試改以直接呼叫方法或 `QTest` 等方式驗證。

### 2.4 視覺預覽
- 指令：`python scripts/render_preview.py --out <資料夾>`（省略 `--out` 時輸出到系統暫存目錄下的 `secretary_preview`）。
- 以 offscreen、假資料（`FakeStore` / `FakeConfig`）渲染各畫面為 PNG：不連網、不讀 `data/`、不寫 Registry、不 import `main.py` 的 `SecretaryApp`。
- offscreen 下中文字型由腳本載入 `msjh.ttc`，實機不受影響。

## 3. 開發階段
（名稱與 `docs/progress.md` 一致）
1. **Phase 1 基礎架構與桌面 UI 介面**
2. **Phase 2 喝水提醒與系統整合**
3. **Phase 3 Google Calendar 雲端雙向串接與進階防護**
4. **Phase 4 Google 日曆原生多階段提醒支援**（規劃中）：實現行程編輯對話框提醒選擇 UI 與 `reminders.overrides` 讀寫。

## 4. 同步原則
> 以下原則已於階段 B（2026-11-24）落實；尚待處理的相關事項見 `docs/progress.md` 已知問題。

- Google Calendar 為唯一資料來源。
- 寫入成功後才更新本地 UI（或寫入後重新拉取）。
- 使用 Google 回傳的 event id，不自行產生假 id。
- 部分更新使用 `events().patch`，避免 `update` 整筆覆蓋清掉未帶欄位。
- 全天行程使用 `{'date': ...}` 而非 `dateTime`。
- 網路呼叫（Google API、OAuth）在背景執行緒執行，不阻塞 Qt 主執行緒。
- 事件時間以系統時區解析與寫入（`services/event_mapping.py`），不寫死 offset。
- 網路呼叫一律經 `EventStore`（`services/event_store.py`），UI 不直接呼叫 `services/google_client`。
