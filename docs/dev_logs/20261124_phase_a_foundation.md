# 收工日誌 (Dev Log) - 2026-11-24 (階段 A：基礎建設)

## 📌 今日完成項目
1. **日誌**：新增 `utils/logger.py`（`get_logger(__name__)`，`RotatingFileHandler` 寫入 `data/logs/secretary.log`，1MB x 3 份備份，UTF-8）。
   - 設定冪等，掛在 `secretary` 根 logger 下；pythonw 無 stdout 時不加 StreamHandler；目錄或開檔失敗退回 stream / NullHandler，不崩潰。
   - 循環匯入處理：`logger.py` 於首次設定時才延遲匯入 `utils.paths`；`utils/paths.py` 於函式內才取得 logger。
   - `main.py`、`ui/`、`utils/` 所有 `print` 改為 logger（`except` 內用 `logger.exception`）。
2. **主題 token**：新增 `ui/theme.py`（深色精緻版 token、`TOKENS`、`qss()`），尚未套用到現有 UI。
3. **測試骨架**：新增 `tests/` 與 `requirements-dev.txt`（pytest==9.2.0），涵蓋 theme、paths、config_manager、google_calendar（顏色對應）、logger。
4. **文件**：更新 `progress.md`（已知問題 7、11）、`architecture.md`、`dev_rules.md`、`.gitignore`（補 `.pytest_cache/`）。

## 📌 設計決策
- 測試的 `conftest.py` 在載入階段就把日誌目錄導向暫存目錄，避免被測模組匯入時寫入真實 `data/logs/`。
- `tests/test_google_calendar.py` 以 module-scope fixture 匯入，並還原 `socket.getaddrinfo` 與 `socket.setdefaulttimeout`。

## 📌 審查後修正
- 日誌不記個資：Google 新增成功改記事件 id，自啟命令降為 debug。
- `googleapiclient`、`google.auth` 的 WARNING 以上共用同一個 file handler（冪等，`_reset_for_tests` 一併清除）。
- `RotatingFileHandler` 加 `delay=True`，避免第二個實例在單例檢查前就開檔。
- 補測試：stdout=None 且目錄有效、時間戳格式、第三方 logger 冪等；`conftest.py` 於 `pytest_sessionfinish` 關閉 handler 並刪除暫存日誌目錄。
- `calendar_view.py` 的 logger 定義移到所有 import 之後；`google_calendar.py` 授權流程吞錯處補 `logger.warning`。

## 📌 下次開工
- **B 同步修正**（已知問題 1–6、9）、**C 視覺重設計**（套用 `ui/theme.py`）、**D 清理**。
