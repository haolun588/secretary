# 收工日誌 (Dev Log) - 2026-11-25 (階段 D：autostart 與清理)

## 📌 目標
- 解決已知問題 8：autostart 預設開啟，且每次啟動都寫入 Registry。
- 解決已知問題 21：清理已無引用的箭頭圖示、產生器與 `qss_url`。
- 解決已知問題 22：`test_event_store` 的 `processEvents` 遺留事件造成全套件不穩。

## 📌 改動
- **autostart**
  - 預設改為關閉（`utils/config_manager.py`、`main.py`、`ui/settings_view.py`）。
  - `utils/autostart.py`：新增 `get_registered_command()`（KEY_READ 唯讀）、純函式 `plan_sync(desired, current_cmd, expected_cmd)`、`AutoStartManager.sync(desired)`。啟動改呼叫 `sync`，只在 Registry 與設定不一致時才寫入或刪除；路徑變動會自動修正。
  - `set_autostart` 權限由 KEY_ALL_ACCESS 縮為 KEY_SET_VALUE，並以 try/finally CloseKey。
  - 失敗提示：啟動同步失敗或設定頁切換失敗以 danger toast 提示；切換失敗時還原核取方塊且不寫 config。
  - 注意：已存有 `autostart: true` 的舊 config 仍維持開啟（不強制關閉）。
- **清理**：刪除 `assets/arrow_up.png`、`assets/arrow_down.png`、`scripts/arrow_generator.py`；移除 `utils/paths.qss_url` 與其測試。
- **測試穩定**：`tests/test_event_store.py` 的 `_wait` 改用 `QCoreApplication.sendPostedEvents(None, QEvent.Type.MetaCall)`，只派送 QueuedConnection 回呼，不處理其他測試遺留的 DeferredDelete。
- **測試調整**：`tests/test_settings_view.py::test_autostart_signal` 因預設改 False 調整切換順序；`tests/test_paths.py` 移除 `qss_url` 測試。

## 📌 驗證
- py_compile 全專案通過。
- `python -m pytest`：405 passed（階段 C 後為 389）。
- 新增 `tests/test_autostart.py`（12 個測試，假 winreg，不碰真 Registry）。
- `main.py` 的 `on_autostart_toggled` 需整個 GUI 才能測，未寫單測，需實機驗證。

## 📌 待使用者實機測試清單
- [ ] 設定頁開啟「開機啟動」後，Registry（`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`）出現正確指令（含 `--minimized`）；關閉後該值被移除
- [ ] 重開機後自動啟動並最小化到系統匣
- [ ] 舊 config（`autostart: true`）升級後行為：維持開啟，Registry 與設定一致時啟動不重複寫入
- [ ] 新環境（無 config）預設為關閉，Registry 無對應值
- [ ] 移動專案資料夾後啟動，Registry 路徑自動修正
- [ ] Registry 寫入失敗（例如權限被限制）時出現 danger toast，且核取方塊還原、config 未改

## 📌 後續事項
- 階段 D 後剩餘已知問題見 `docs/progress.md`（13~20、23、24 等）。
- Phase 4：Google 日曆原生多階段提醒支援（規劃中）。
