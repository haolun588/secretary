# 開發日誌 (Dev Log) - 2026-08-09

## 📌 完成任務項目
1. **設定檔持久化管理 (`utils/config_manager.py`)**：
   - 實現 `config.json` 存取，持久化保存提醒間隔分鐘數 (預設 10 分鐘)、開機自啟開關、關閉隱藏至托盤與最後更新時間。
2. **Windows 開機靜默自啟動 (`utils/autostart.py`)**：
   - 透過 Windows 登錄檔 (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`) 自動寫入帶有 `--minimized` 參數之啟動命令。
   - 開機啟動時自動保持在背景系統托盤，不彈出主視窗干擾使用者。
3. **視窗關閉隱藏至系統托盤 (`ui/main_window.py` & `main.py`)**：
   - 重寫 `closeEvent`，使用者點擊右上角 `✕` 關閉按鈕時，視窗自動隱藏至系統托盤持續背景運作與倒數。
   - 托盤右鍵選單包含「🖥️ 顯示主視窗」、「💧 測試喝水提醒」、「⚙️ 系統設定」、「❌ 退出程式」。
4. **Google Calendar API 串接與色彩標籤等級對應 (`utils/google_calendar.py`)**：
   - 支援 OAuth2 授權認證流程。
   - 自動解析 Google 日曆的 `colorId`（紅色 11 ➔ 大事件 30天提醒 / 黃色 5 ➔ 中事件 7天提醒 / 綠色 2 ➔ 小事件 3天提醒）。
5. **主程式整合 (`main.py`)**：
   - 整合 `QSystemTrayIcon`、`QTimer` 背景喝水計時器與 3 秒淡出 Toast 提醒彈窗，順暢完成啟動與測試。

---

## 💡 驗證命令
```powershell
cd c:\GitHub\secretary
python main.py
```
若帶入靜默啟動參數：
```powershell
python main.py --minimized
```
