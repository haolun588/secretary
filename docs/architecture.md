# 系統架構與檔案結構 (System Architecture & File Structure)

## 1. 目錄與檔案結構預覽
```
secretary/
├── docs/
│   ├── dev_rules.md              # 技術規範與設計指南 (含托盤化與開機靜默啟動)
│   ├── progress.md               # 任務進度清單
│   ├── architecture.md           # 本系統架構文件
│   └── dev_logs/                 # 開工/收工日誌目錄
├── config.json                   # 使用者設定檔 (時間間隔、開機自啟、關閉隱藏等)
├── main.py                       # 主程式入口 (托盤圖示 QSystemTrayIcon、closeEvent 攔截與背景計時器)
├── ui/
│   ├── main_window.py            # 主視窗外框 (包含 closeEvent 重寫，點擊 ✕ 隱藏至托盤)
│   ├── nav_sidebar.py            # 左側選單欄元件
│   ├── calendar_view.py          # 日曆頁面 (含大/中/小色彩標籤過濾提醒側邊欄)
│   ├── settings_view.py          # 設定頁面 (喝水提醒間隔、開機自啟動控制)
│   ├── calendar_dialog.py        # 行程新增/修改對話框
│   └── toast_window.py           # 右下角喝水提醒彈窗 (含 3 秒淡出動畫)
└── utils/
    ├── autostart.py              # 開機自啟動登錄檔控制模組 (支援 --minimized 靜默啟動)
    ├── config_manager.py         # 設定檔讀寫模組 (config.json 持久化)
    └── google_calendar.py        # Google Calendar API 串接與 colorId 解析模組
```

## 2. 資料流與組件交互說明
1. **開機靜默啟動與托盤化**：
   - 當系統開機啟動，`main.py` 接收到 `--minimized` 參數，不呼叫 `window.show()`，直接隱藏於 `QSystemTrayIcon`。
2. **視窗關閉攔截 (`closeEvent`)**：
   - 當使用者點擊視窗右上角的 `✕` 關閉按鈕，`main_window.py` 攔截事件並呼叫 `event.ignore()` 與 `self.hide()`，視窗隱藏至系統托盤持續運作。
3. **托盤右鍵選單**：
   - 提供「顯示主介面」、「測試喝水提醒」、「設定」、「退出程式」選項。
4. **Google 日曆與提醒過濾**：
   - `google_calendar.py` 解析 Google 日曆的 `colorId`（紅:大30天 / 黃:中7天 / 綠藍:小3天），並呈現於右側提醒欄。
