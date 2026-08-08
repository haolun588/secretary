# 專案開發規範與技術指南 (Dev Rules & Tech Guidelines)

- **Obey User Communication Preference**:
  - 當使用者提出問題或諮詢時，**必須先以清晰簡潔的中文回答說明**，**絕不可未經確認直接修改程式碼或檔案**。
  - 需等與使用者討論確認或使用者明確指示修改時，方可進行程式碼編輯。

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
  - **Google 日曆色彩標籤 (Event Color ID) 對應規則**：
    - 🔴 **紅色系 (Color ID 11 / Tomato)** ➔ **大事件 (提前 30 天/1個月顯示於右側提醒欄)**
    - 🟡 **黃色/橘色系 (Color ID 5 / Banana 或 Color ID 4 / Flamingo)** ➔ **中事件 (提前 7 天/1週顯示於右側提醒欄)**
    - 🟢 **綠色系 / 預設色 (Color ID 2 / Sage 或預設藍)** ➔ **小事件 (提前 3 天顯示於右側提醒欄)**

## 2. 技術選型與約束 (Tech Stack & Constraints)
- **作業系統目標**：Windows 10 / 11
- **UI & 框架**：採用 Python + PyQt6，以 `QStackedWidget` 結合左側側邊欄導覽按鈕 (`Navigation Bar`)，建構流暢無縫的分頁切換體驗。
- **系統托盤與關閉事件**：使用 `QSystemTrayIcon`，實現右鍵選單 (顯示主視窗 / 測試喝水提醒 / 退出程式)。
- **開機自啟**：透過 Windows Registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`) 寫入包含 `pythonw main.py --minimized` 之啟動命令。
- **設定儲存**：採用 JSON 格式儲存使用者設定 (`config.json`)。
- **異常處理**：外部 API、檔案存取、登錄檔寫入皆須包含 Try-Except 區塊與時間戳日誌。

## 3. 開發三階段流程守則
1. **Phase 1 (文件與規格)**：完成 `progress.md`, `dev_rules.md`, `architecture.md` 建立。
2. **Phase 2 (UI 優先設計)**：完成靜態視覺設計。
3. **Phase 3 (邏輯實現與自動化)**：實現定時器、托盤選單、關閉隱藏、開機靜默自啟、Google 日曆 API 串接與色彩標籤過濾。
