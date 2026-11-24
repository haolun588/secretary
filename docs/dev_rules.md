# 專案開發規範與技術指南 (Dev Rules & Tech Guidelines)

> AI 協作規範見根目錄 `CLAUDE.md`。

## 1. 專案目標與核心功能
本專案名為 **Secretary (桌面小助理)**，主要功能包括：
- **背景執行與托盤化 (Minimize to Tray)**：
  - 點擊主視窗右上角「✕ (關閉)」按鈕時，攔截 `closeEvent`，**隱藏視窗至系統托盤 (System Tray) 並持續於背景運行**，不直接結束程式。退出程式僅能透過托盤右鍵選單點擊「退出程式」。
- **開機自動靜默啟動 (Silent Boot Auto-Start)**：
  - Windows 開機自動啟動時代入 `--minimized` 參數，**直接隱藏於背景系統托盤**，不主動跳出主視窗干擾使用者。
- **左側側邊導覽選單 (Left Navigation Sidebar)**：採用現代化的側邊選單欄位，將「日曆儀表板」、「喝水與系統設定」等功能獨立分頁切換。
- **定時喝水提醒**：每 N 分鐘（預設 10 分鐘，可透過 UI 調整）於螢幕右下角彈出提醒視窗，顯示約 3 秒後自動淡出 (Fade-out)。
- **Google 日曆整合與色彩標籤等級對應**：
  - 主介面整合日曆，支援串接 Google Calendar API。
  - **Google 日曆色彩標籤 (Event Color ID) 對應規則**（以 `utils/google_calendar.py` 的 `COLOR_PRIORITY_MAP` 為準）：
    - **Color ID 11 (Tomato)、4 (Flamingo)** ➔ **大事件 (提前 30 天/1個月顯示於右側提醒欄)**
    - **Color ID 5 (Banana)、6 (Tangerine)** ➔ **中事件 (提前 7 天/1週顯示於右側提醒欄)**
    - **Color ID 2 (Sage)、10 (Basil)** ➔ **小事件 (提前 3 天顯示於右側提醒欄)**
    - **未對應的顏色與預設色（無 colorId，或其他 ID 如 1、3、7、8、9）** ➔ 實際被當成**小事件**（`parse_priority_from_color` 預設值為 `minor`）。
- **Google 日曆原生多階段提醒 (reminders.overrides)**：
  - 全面使用 Google API 原生 `reminders` 欄位傳遞與讀取通知時間（支援多選：如 10 分鐘前、30 分鐘前、1 小時前、1 天前）。
  - 與手機 App 及網頁版設定完美跨平台同步，棄用外掛獨立文字標籤，供其他提醒端統一讀取。（雲端 Bot / Discord 不屬於本 repo 範圍。）

## 2. 技術選型與約束 (Tech Stack & Constraints)
- **作業系統目標**：Windows 10 / 11
- **UI & 框架**：採用 Python + PyQt6，以 `QStackedWidget` 結合左側側邊欄導覽按鈕 (`Navigation Bar`)，建構流暢無縫的分頁切換體驗。
- **系統托盤與關閉事件**：使用 `QSystemTrayIcon`，實現右鍵選單 (顯示主視窗 / 測試喝水提醒 / 系統與提醒設定 / 退出程式)。
- **開機自啟**：透過 Windows Registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`) 寫入包含 `pythonw main.py --minimized` 之啟動命令。
- **設定儲存**：採用 JSON 格式儲存使用者設定 (`config.json`)。
- **異常處理與日誌**：外部 API、檔案存取、登錄檔寫入須有 try-except，並使用 Python `logging` 寫入檔案（含時間戳，建議 `RotatingFileHandler`；日誌檔已被 `.gitignore` 的 `*.log` 排除）。因 `pythonw` 沒有 stdout，`print` 不能當作日誌。

## 3. 開發階段
（名稱與 `docs/progress.md` 一致）
1. **Phase 1 基礎架構與桌面 UI 介面**
2. **Phase 2 喝水提醒與系統整合**
3. **Phase 3 Google Calendar 雲端雙向串接與進階防護**
4. **Phase 4 Google 日曆原生多階段提醒支援**（規劃中）：實現行程編輯對話框提醒選擇 UI 與 `reminders.overrides` 讀寫。

## 4. 同步原則
> 以下為目標規範，現行程式尚未完全符合（見 `docs/progress.md` 已知問題）。

- Google Calendar 為唯一資料來源。
- 寫入成功後才更新本地 UI（或寫入後重新拉取）。
- 使用 Google 回傳的 event id，不自行產生假 id。
- 部分更新使用 `events().patch`，避免 `update` 整筆覆蓋清掉未帶欄位。
- 全天行程使用 `{'date': ...}` 而非 `dateTime`。
- 網路呼叫（Google API、OAuth）在背景執行緒執行，不阻塞 Qt 主執行緒。
