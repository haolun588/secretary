# 收工日誌 (Dev Log) - 2026-11-24 (專案審查與工作區整理)

## 📌 今日完成項目
1. **專案審查**（程式碼、規則、設計三份審查），重點結論整理於 [progress.md](../progress.md)「已知問題（2026-11-24 審查）」：
   - 程式碼面：編輯行程不帶入／不回寫日期時間、全天行程更新被轉為定時行程、`events().update` 整筆覆蓋（已知問題 1）；OAuth 與 `check_connection` 在主執行緒阻塞（2、5）；新增行程使用假 id、寫入失敗無提示（3）；雲端回傳空清單不清空本地（4）；背景 fetch 與 UI 共用 service，httplib2 非 thread-safe（6）；只抓 `timeMin=now` 且 `maxResults=100`、未處理分頁（9）。
   - 規則面：日誌使用 `print`，在 `pythonw` 下遺失（7）；autostart 預設開啟且每次啟動寫入 Registry（8）；尚無自動化測試（11）。
   - 設計面：視覺與互動需重新設計，規劃為深色精緻版（見下一步）。
2. **建立 `CLAUDE.md` 與 `requirements.txt`，並修正文件矛盾**（已於 commit `eeb95a3`）。
3. **工作區整理**：
   - 新增 `utils/paths.py` 集中管理專案路徑（`PROJECT_DIR`、`ASSETS_DIR`、`DATA_DIR` 等），並提供 `qss_url`、`asset_path`、`ensure_data_dirs`、`migrate_legacy_files`。
   - 機密與設定檔（`config.json`、`credentials.json`、`token.json`）集中於 `data/`，啟動時自動由根目錄搬移舊檔。
   - 產生器與捷徑腳本移至 `scripts/`（`arrow_generator.py`、`create_shortcut.py`、`icon_generator.py`）。
   - 刪除重複／未使用程式碼：`preview_ui.py`、`utils/shortcut_creator.py`（已知問題 12 已修正）。
   - 箭頭圖示 QSS 改用 `utils/paths.py` 絕對路徑，並統一寫成 `url("...")`（已知問題 10 已修正）。
   - `migrate_legacy_files` 改為逐檔處理並回傳結果 dict；`main.py` 初始化失敗不再於匯入階段崩潰。

---

## 📌 下次開工預定任務：深色精緻版視覺重設計與同步修正
分階段進行：
- **A 基礎建設**：logging 取代 `print`、測試骨架、必要的共用工具。
- **B 同步修正**：處理已知問題 1–6、9（編輯回寫、假 id、空清單、主執行緒阻塞、thread-safe、分頁）。
- **C 視覺重設計**：深色精緻版 UI。
- **D 清理**：移除殘留、更新 `docs/progress.md` 與 `docs/architecture.md`。
