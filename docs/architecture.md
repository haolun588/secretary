# 系統架構與檔案結構 (System Architecture & File Structure)

## 1. 目錄與檔案結構預覽
```
secretary/
├── docs/
│   ├── dev_rules.md              # 技術規範與設計指南 (含左側選單與分頁)
│   ├── progress.md               # 任務進度清單
│   ├── architecture.md           # 本系統架構文件
│   └── dev_logs/                 # 開工/收工日誌目錄
├── config.json                   # 使用者設定檔 (時間間隔、開機自啟等)
├── main.py                       # 主程式入口 (托盤圖示與背景邏輯)
├── ui/
│   ├── main_window.py            # 主視窗外框 (左側 NavSidebar + QStackedWidget 頁面切換)
│   ├── nav_sidebar.py            # 左側選單欄元件 (日曆頁 / 設定頁 切換按鈕)
│   ├── calendar_view.py          # 日曆頁面 (日曆元件 + 右側 Upcoming Reminders 側邊欄)
│   ├── settings_view.py          # 設定頁面 (喝水提醒間隔、開機自啟動、測試按鈕)
│   ├── calendar_dialog.py        # 行程新增/修改對話框 (選取大/中/小等級)
│   └── toast_window.py           # 右下角喝水提醒彈窗 (含淡出動畫)
└── utils/
    ├── autostart.py              # 開機自啟動登錄檔控制模組
    ├── config_manager.py         # 設定檔讀寫模組
    └── google_calendar.py        # Google Calendar API 串接模組
```

## 2. 資料流與組件交互說明
1. **主程式與視窗結構**：
   - `main_window.py` 包含左側 `nav_sidebar.py` 與右側 `QStackedWidget`。
   - 點擊左側選單可在「日曆頁面 (`calendar_view.py`)」與「設定頁面 (`settings_view.py`)」無縫切換。
2. **Google 日曆與提醒側邊欄**：
   - `calendar_view.py` 整合左邊日曆與右邊 `upcoming_sidebar`。
   - `upcoming_sidebar` 根據大事件 (30天)、中事件 (7天)、小事件 (3天) 篩選呈現近期行程。
3. **定時喝水與淡出彈窗**：
   - 背景 `QTimer` 定時觸發 `toast_window` 於螢幕右下角顯示並於 3 秒後自動淡出。
4. **設定變更**：
   - `settings_view.py` 提供時間與自啟動設定，儲存後即時生效。
