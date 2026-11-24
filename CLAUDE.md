# Secretary 專案 AI 協作規範

## 溝通
- 一律使用繁體中文（台灣用語）回覆；程式碼、指令、檔名與錯誤訊息保持原文。
- 使用者提出問題或諮詢時，**必須先以清晰簡潔的中文回答說明**，**絕不可未經確認直接修改程式碼或檔案**。
- 需等與使用者討論確認，或使用者明確指示修改時，方可進行編輯。

## 必讀文件
- `docs/dev_rules.md`：技術規範
- `docs/architecture.md`：系統架構與檔案結構
- `docs/progress.md`：開發進度與已知問題

## 作業紅線
- 不得讀取、印出、提交 `data/` 內的 `credentials.json`、`token.json`、`config.json`（整個 `data/` 不得讀取或提交）。
- 未經使用者同意，不得啟動 GUI、不得呼叫 Google Calendar API（會改動使用者真實日曆）、不得寫入 Windows Registry（autostart）。
- 不得寫死個人路徑（使用者名稱、磁碟代號、Python 安裝路徑）；路徑以專案目錄或 `sys.executable` 動態推導。
- 網路呼叫（Google API、OAuth）不得在 Qt 主執行緒同步執行。
- 寫入雲端失敗時必須提示使用者，不可只 `print`。

## 驗證指令
- 修改 `.py` 後至少執行語法檢查：
  ```
  python -c "import py_compile,glob;[py_compile.compile(f,doraise=True) for f in glob.glob('**/*.py',recursive=True)]"
  ```
- 之後若有 `tests/` 目錄，執行 `python -m pytest`。

## 提交規範
- 使用 Conventional Commits：`feat:` / `fix:` / `docs:` / `refactor:` / `chore:` + 簡述（描述可用中文）。
- 一個 commit 只做一件事，不要把多個 Phase 混在一起。
- commit 訊息要提到所有行為變更。

## 文件同步
- 完成功能或修正後，更新 `docs/progress.md`。
- 每次開發階段在 `docs/dev_logs/` 新增 `YYYYMMDD_主題.md`。
- 架構或檔案增減時，更新 `docs/architecture.md`。

## 依賴
- 新增套件時同步更新 `requirements.txt` 並固定版本。
