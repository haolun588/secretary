# 專案進度與任務清單 (Progress Checklist)

## Phase 1: 規格與文件建立 (Documentation & Specification)
- [x] 建立 `docs/progress.md` 專案進度清單 (含左側導覽選單列與分頁架構)
- [x] 建立 `docs/dev_rules.md` 開發規範與技術設計說明
- [x] 建立 `docs/architecture.md` 系統架構與檔案結構說明

## Phase 2: UI 介面視覺設計 (UI-First Design - Static Mockup)
- [ ] 設計主視窗 Layout (Main UI Window with Left Sidebar)：
  - **左側側邊導覽選單欄 (Left Navigation Sidebar)**：包含「日曆儀表板」、「系統與喝水設定」、「Google 帳號與關於」分頁標籤
  - **分頁一：日曆儀表板 (Calendar View)**：包含日曆、右側近期提醒欄位（大中小事件 30天/7天/3天 過濾）
  - **分頁二：喝水與系統設定 (Settings View)**：喝水提醒間隔分鐘數、開機啟動開關、測試提醒按鈕
- [ ] 設計行程新增/修改對話框 (Add/Edit Event Dialog)：包含「大/中/小」事件等級下拉選單
- [ ] 設計螢幕右下角彈出通知視窗 (Toast Notification)：具備 3 秒淡出 (Fade-out) 動畫與現代感視覺
- [ ] 請使用者進行 UI 畫面視覺確認與審核

## Phase 3: 核心邏輯實現與自動化 (Logic Implementation & Automation)
- [ ] 實現背景計時器邏輯 (預設 10 分鐘，支援 UI 即時更新間隔)
- [ ] 實現 Windows 右下角淡入/淡出彈窗動畫與自動銷毀機制
- [ ] 實現系統托盤 (System Tray) 圖示與背景執行 (Minimize to Tray)
- [ ] 實現 Windows 開機自動啟動 (Auto-start on boot via Registry / Startup)
- [ ] 實現 Google Calendar API 整合 (OAuth 2.0 授權登入、行程讀取、新增、編輯、等級註記 Extended Properties)
- [ ] 實現事件等級篩選邏輯 (大事件 30天、中事件 7天、小事件 3天)
- [ ] 整合設定檔持久化儲存 (JSON Config Persistent Storage)
- [ ] 測試與例外處理 (無障礙啟動、防重複執行 Single Instance Lock)
