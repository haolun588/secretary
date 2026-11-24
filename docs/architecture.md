# 系統架構與檔案結構 (System Architecture & File Structure)

## 1. 目錄與檔案結構預覽
```
secretary/
├── CLAUDE.md                     # AI 協作規範與作業紅線
├── requirements.txt              # 直接依賴（固定版本）
├── .gitignore
├── assets/                       # 圖示資源 (icon.ico / icon.png / arrow_up.png / arrow_down.png)
├── docs/
│   ├── dev_rules.md              # 技術規範與設計指南 (含托盤化與開機靜默啟動)
│   ├── progress.md               # 任務進度清單與已知問題
│   ├── architecture.md           # 本系統架構文件
│   └── dev_logs/                 # 開工/收工日誌目錄 (YYYYMMDD_主題.md)
├── config.json                   # 使用者設定檔 (已被 .gitignore 排除，不納入版控)
├── main.py                       # 主程式入口 (托盤圖示 QSystemTrayIcon、closeEvent 攔截與背景計時器)
├── create_shortcut.py            # 建立桌面捷徑與啟動 .bat
├── preview_ui.py                 # UI 預覽腳本 (注意：實際會連線 Google)
├── ui/
│   ├── main_window.py            # 主視窗外框 (包含 closeEvent 重寫，點擊 ✕ 隱藏至托盤)
│   ├── nav_sidebar.py            # 左側選單欄元件
│   ├── calendar_view.py          # 日曆頁面 (含大/中/小色彩標籤過濾提醒側邊欄)
│   ├── settings_view.py          # 設定頁面 (喝水提醒間隔、開機自啟動控制)
│   ├── calendar_dialog.py        # 行程新增/修改對話框 (含事件等級選單與刪除確認；提醒時間選單尚未實作)
│   └── toast_window.py           # 右下角喝水提醒彈窗 (含 3 秒淡出動畫)
└── utils/
    ├── autostart.py              # 開機自啟動登錄檔控制模組 (支援 --minimized 靜默啟動)
    ├── config_manager.py         # 設定檔讀寫模組 (config.json 持久化)
    ├── google_calendar.py        # Google Calendar API 串接與 colorId 解析 (reminders.overrides 尚未實作)
    ├── shortcut_creator.py       # 捷徑建立工具 (與 create_shortcut.py 重複)
    ├── arrow_generator.py        # 箭頭圖示產生器 (目前未被引用)
    └── icon_generator.py         # 應用程式圖示產生器 (目前未被引用)
```

## 2. 資料流與組件交互說明
1. **開機靜默啟動與托盤化**：
   - 當系統開機啟動，`main.py` 接收到 `--minimized` 參數，不呼叫 `window.show()`，直接隱藏於 `QSystemTrayIcon`。
2. **視窗關閉攔截 (`closeEvent`)**：
   - 當使用者點擊視窗右上角的 `✕` 關閉按鈕，`main_window.py` 攔截事件並呼叫 `event.ignore()` 與 `self.hide()`，視窗隱藏至系統托盤持續運作。
3. **托盤右鍵選單**：
   - 提供「顯示小助理主視窗」、「測試喝水提醒彈窗」、「系統與提醒設定」、「退出程式」四項。
4. **Google 日曆與色彩標籤過濾**：
   - `google_calendar.py` 解析 Google 日曆的 `colorId`（11、4 大 30 天 / 5、6 中 7 天 / 2、10 小 3 天；未對應顏色視為小事件），並呈現於右側提醒欄。
5. **Google 日曆原生多階段提醒 (reminders.overrides)**（Phase 4 規劃中，尚未實作）：
   - 透過 `google_calendar.py` 傳遞與讀取 API 原生 `reminders` 屬性（如 10 分鐘前、1 小時前、1 天前等多重提醒分鐘數）。
   - 確保在 `secretary` 桌面端、手機 Google 日曆 App 或網頁版設定的提醒皆能同步，並供背景/雲端 Bot 統一輪詢發送提醒。
