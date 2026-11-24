# 收工日誌 (Dev Log) - 2026-11-24 (階段 B：同步修正與架構調整)

## 📌 目標
- 修正已知問題 1–6、9（編輯行程資料遺失、主執行緒阻塞、假 id、空清單處理、service 共用、拉取範圍）。
- 以 `services/` 取代 `utils/google_calendar.py`，讓 UI 不再直接碰網路。

## 📌 修改檔案
- 新增：`services/__init__.py`、`services/event_mapping.py`、`services/google_client.py`、`services/event_store.py`
- 新增測試：`tests/test_event_mapping.py`、`tests/test_event_store.py`、`tests/test_google_client.py`、`tests/test_calendar_view.py`、`tests/test_calendar_dialog.py`
- 刪除：`utils/google_calendar.py`、`tests/test_google_calendar.py`
- 修改：`main.py`（建立 `EventStore` 並注入、錯誤提示、單一實例流程）、`ui/calendar_view.py`、`ui/calendar_dialog.py`（「全天」核取方塊、帶入原日期時間）、`ui/settings_view.py`、`ui/main_window.py`
- 文件：`docs/progress.md`、`docs/architecture.md`、`docs/dev_rules.md`

## 📌 設計決策
- **單執行緒 pool 序列化**：`ThreadPoolRunner` 使用 `maxThreadCount=1` 的 `QThreadPool`，讓 fetch 與寫入依序執行，避免寫入與拉取交錯造成本地狀態競態；每個 worker 仍自建 service（httplib2 非 thread-safe）。
- **OAuth 獨立 daemon 執行緒**：授權最長可等 180 秒，若佔用單執行緒 pool 會卡住所有同步；改用 `DaemonThreadRunner`，結束程式時不會被它擋住。OAuth 先用 port 8080，只有綁定失敗才改 port 0，不會開第二次瀏覽器。
- **移除 IPv4 `getaddrinfo` monkeypatch 與 `socket.setdefaulttimeout`**：匯入時修改全域 socket 會影響整個行程所有連線（含 OAuth 本機 server 與第三方套件），測試也必須還原。逾時改由 `httplib2.Http(timeout=15)` 設定。若日後 IPv6 環境出現連線逾時，再改在 httplib2／連線層處理。
- **內部 event dict**：`id, title, all_day, start, end, priority, location, notes, color_id`。全天事件 `start`/`end` 為 `YYYY-MM-DD`，`end` 含當天（Google `end.date` 為 exclusive，轉入時減 1 天、寫出時加 1 天）；定時事件為本機時區的 naive ISO 字串。
- **patch 以 None 清除另一型態 key**：`build_patch_body` 只送變動欄位；start/end 或 all_day 變動時同時送 start 與 end，並把另一型態的 key（`dateTime` 或 `date`）設為 `None`，以支援全天與定時互相切換。
- **時區**：以系統時區（`local_tz()`）解析與寫入，不寫死 offset；目前為固定 offset，跨 DST 地區的限制見後續事項。
- **結果回主執行緒**：job 的 signals 在主執行緒建立，以 QueuedConnection 回呼；寫入成功才更新本地；fetch 失敗與空清單區分；過期世代的 fetch 結果丟棄。
- **UI 安全**：rich text 用 `html.escape`，純文字 QLabel 設 PlainText；錯誤以 toast + QMessageBox（寫入類）提示，fetch/check 相同錯誤去重。

## 📌 驗證
- `python -m pytest -q`：125 passed（2.20s）。
- 語法檢查沿用 pytest 匯入結果；其餘見下方未驗證項目。

## 📌 未驗證項目
- 未實際開啟 app（GUI），未連線 Google（未跑真實 OAuth 與日曆讀寫）。
- 全天與定時互轉對真實 Google 的行為（含 `start.timeZone`）尚未實測。

## 📌 後續補強（最後一批）
- `requirements.txt` 已固定 `httplib2==0.32.0`。
- `google_client.save_token` 加模組層級 `threading.Lock`，並以同目錄暫存檔 + `os.replace` 原子寫入，避免寫到一半被讀取或並行寫入。
- `EventStore.is_authorizing` 屬性；設定頁改讀它，授權期間收到 `ok`/`syncing` 不覆蓋「等待瀏覽器授權」文字。
- 未授權時手動按「雲端同步」會顯示 tooltip 並跳一次提示（請到設定頁授權）；60 秒計時器維持靜默。

## 📌 後續事項
- logout 與排隊 job 寫回 token 的競態（UI 尚未接 logout）。
- `local_tz()` 為固定 offset，有 DST 的地區跨 DST 日期會差 1 小時（台灣不受影響）。
- 定時改全天時，原 `start.timeZone` 是否需清除，尚未實測。
- 任何 `RefreshError` 都會清掉憑證（含可重試的情況）。
- 「即將到來」側欄受目前瀏覽月份範圍影響，瀏覽 2 個月以外時可能變空。
- `main.py` 單一實例 socket 名稱含使用者名稱。
- 階段 C（視覺重設計）、階段 D（清理，含 autostart）。
