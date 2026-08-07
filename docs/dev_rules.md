# 專案開發規範與技術指南 (Dev Rules & Tech Guidelines)

## 1. 專案目標與核心功能
本專案名為 **Secretary (桌面小助理)**，主要功能包括：
- **背景執行與托盤化**：應用程式啟動後隱藏於系統托盤 (System Tray)，不干擾使用者日常作業。
- **左側側邊導覽選單 (Left Navigation Sidebar)**：採用現代化的側邊選單欄位，將「日曆儀表板」、「喝水與系統設定」等功能獨立分頁切換。
- **開機自動啟動**：支援設定 Windows 開機自動啟動。
- **定時喝水提醒**：每 N 分鐘（預設 10 分鐘，可透過 UI 調整）於螢幕右下角彈出提醒視窗，顯示約 3 秒後自動淡出 (Fade-out)。
- **Google 日曆整合與大中小等級分級**：
  - 主介面整合日曆，支援串接 Google Calendar API。
  - **行程分為三個等級**：大事件 (Major)、中事件 (Medium)、小事件 (Minor)。
  - **右側近期提醒欄 (Upcoming Reminders Sidebar)**：
    - **大事件**：提前 **1 個月 (30 天)** 顯示在右側提醒欄。
    - **中事件**：提前 **1 個禮拜 (7 天)** 顯示在右側提醒欄。
    - **小事件**：提前 **3 天** 顯示在右側提醒欄。

## 2. 技術選型與約束 (Tech Stack & Constraints)
- **作業系統目標**：Windows 10 / 11
- **UI & 框架**：採用 Python + PyQt6 / PySide6，以 `QStackedWidget` 結合左側側邊欄導覽按鈕 (`Navigation Bar`)，建構流暢無縫的分頁切換體驗。
- **Google Calendar API & 等級持久化**：
  - 使用 Google Calendar API 的 `extendedProperties` 儲存事件等級。
- **開機自啟**：透過 Windows Registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`) 或 Startup 捷徑實現。
- **設定儲存**：採用 JSON 格式儲存使用者設定。
- **異常處理**：外部 API、檔案存取、登錄檔寫入皆須包含 Try-Except 區塊與時間戳日誌。

## 3. 開發三階段流程守則
1. **Phase 1 (文件與規格)**：完成 `progress.md`, `dev_rules.md`, `architecture.md` 建立。
2. **Phase 2 (UI 優先設計)**：完成含左側選單欄的主介面（日曆頁面、右側提醒側邊欄、設定頁面、行程編輯對話框）與右下角彈窗的靜態視覺設計，並取得使用者畫面審核確認。
3. **Phase 3 (邏輯實現與自動化)**：逐步實現定時器、托盤選單、開機自啟、Google 日曆 API 串接與淡出動畫。
