# Secretary 專案開發進度清單 (Development Progress)

## 📌 Phase 1: 基礎架構與桌面 UI 介面 (已完成)
- [x] PyQt6 專案目錄結構與主程式建立 (`main.py`, `ui/`)
- [x] 暗黑高顏值主題與電光紫配色 (`#121217`, `#1c1c24`, `#8b5cf6`)
- [x] 左側導覽列 `NavSidebar` (日曆與行程 / 喝水與設定)
- [x] 中間月曆 `CalendarView` (440px 寬、1:1 置中、週末電光紫字體)
- [x] 右側提醒面板 `SidebarFrame` (340px 緊貼右側、雙行頂部導覽列)
- [x] 選取日期當日行程卡片 `TodayEventCard` (標題/地點/備註獨立三行、100% 依字數自適應高度、`word-break: break-all` 自動折行)

## 📌 Phase 2: 喝水提醒與系統整合 (已完成)
- [x] 螢幕右下角 3 秒淡出 Toast 提醒視窗 (`ToastWindow`)
- [x] Windows 系統訊息提示音 (`winsound.MessageBeep`)
- [x] 1 秒實時動態背景倒數計時器 (左下角 `下次提醒: MM:SS 後` 每秒秒數更新)
- [x] 設定頁面喝水提醒總開關與間隔設定
- [x] 關閉視窗縮小至系統托盤 (`QSystemTrayIcon`)
- [x] 開機自動啟動與 `--minimized` 靜默托盤啟動
- [x] 單一實體防護鎖 (`QLocalServer` & `QLocalSocket` - 避免重複開啟進程，點擊捷徑喚醒原視窗)

## 📌 Phase 3: Google Calendar 雲端雙向串接與進階防護 (已完成)
- [x] Google OAuth2 API 授權整合 (`google-api-python-client`, `credentials.json`, `token.json`)
- [x] `.gitignore` 檔案維護，徹底保護敏感憑證與 Token 不遭 Git 追蹤
- [x] 背景非同步 QThread 載入 (`GoogleFetchWorker`) 與全局 IPv4 socket 逾時防護 (0.0 秒瞬間秒開，完全防卡死閃退)
- [x] 背景無感自動續約 (Auto-Refresh `refresh_token`)
- [x] 實質 API 健康度通訊檢查 (`check_connection()`)
- [x] Google 日曆全色彩標籤級別對應 (紅:大30天 / 黃橘:中7天 / 綠:小3天)
- [x] 編輯行程右下角三鈕區 (`[取消]` `[🗑️ 刪除行程]` `[儲存行程]`)
- [x] 專屬暗黑紫紅刪除確認對話框 (`ConfirmDeleteDialog`)
- [x] 雲端 2-Way 雙向讀取、新增 (`add_event`)、更新 (`update_event`) 與刪除 (`delete_event`)
- [x] 桌面 256x256 高畫質紫光電光圖示 `icon.png` / `icon.ico`
- [x] Windows 桌面捷徑 `Secretary 智能桌面小助理.lnk` 自動建立

## 📌 Phase 4: Google 日曆原生多階段提醒支援 (規劃中)
- [ ] `utils/google_calendar.py`: 擴充 `add_event` / `update_event` 支援傳送 `reminders.overrides`（包含 10 分鐘、30 分鐘、1 小時、1 天等多階段提醒）
- [ ] `utils/google_calendar.py`: 擴充 `get_events` / 行程解析讀取 Google API `reminders` 屬性
- [ ] `ui/calendar_dialog.py`: 行程新增/編輯對話框新增提醒時間選單（支援自訂多階段提醒）
- [ ] 跨平台與 Discord 整合相容：相容手機 App、網頁版與桌面端設定之提醒時間，棄用舊 `Calender` 專案獨特標籤，改為統一讀取 Google 原生 `reminders.overrides`

