# 收工日誌 (Dev Log) - 2026-11-25 (階段 C：深色精緻版視覺與排版重設計)

## 📌 目標
- 以深色精緻版重做整個 UI：設計系統、52px 圖示導覽、自繪月／週／日日曆、右側面板、對話框、設定頁、toast、托盤。
- 不改變 `services/` 的同步行為與既有介面；既有測試依賴的名稱與行為盡量保留。

## 📌 設計決策
- **喝水按鈕切到設定頁喝水區塊**：喝水只有開關、間隔、測試三個控制，獨立頁太空且與設定重複；導覽列仍一鍵直達（`scroll_to_water()`）。
- **自繪月／週／日**：不用 QCalendarWidget，也不用 QTableView+delegate。格內色條 chip、+N、今天淡底需精細控制；命中測試是純幾何，可直接單元測試；時間軸重疊分欄與現在時間線標準元件無法表達。
- **ensure_month anchor**：月／日視圖以選取日所在月份、週視圖以該週第一天所在月份呼叫 `ensure_month`（store 自帶前後各一個月），避免同週內重複拉取。
- **時間軸並排分欄**：重疊行程以貪婪演算法分欄並排，不互相遮蓋；跨日定時行程在當天裁切到 0~1440 分。
- **即將到來規則**：明天以後依等級 30/7/3 天、含進行中行程、排除已結束的定時行程；今天開始的只在選取日清單。仍受拉取範圍影響（已知問題 17）。
- **ToastStack**：多則 toast 往上堆疊，關閉後重排，避免重疊。
- **WaterCountdown**：倒數邏輯抽成無 Qt 的 `utils/water_timer.py`（tick／snooze／reset），可單元測試；`main.py` 只負責接線。
- **save_config_or_warn**：設定寫入失敗時以 danger toast 提示，符合「寫入失敗必須提示使用者」。
- **自繪圖示**：`assets/icons/*.svg` 為專案手寫的 24 格線條圖示，風格參考 Lucide（ISC 授權），非複製 Lucide 原始檔；`ui/icons.py` 依 token 上色並處理高 DPI。
- **樣式集中**：全域 QSS 依元件分段，以 `variant`／`role` 動態屬性選擇，切換後 `repolish()`；ui/ 內除 theme、styles 外禁用 hex／rgba／emoji。

## 📌 流程與審查摘要（四批，每批經審查後修正）
1. **批次 1（26b4612）設計系統**：全域 QSS 過早套用造成舊 UI 跑版，改為延後到批次 4 在 `main.py` 接線；透明底改以 palette 處理；DWM 呼叫補 `argtypes`；rgba 圖示上色改用 DestinationIn 合成。
2. **批次 2（5beb90c）主視窗與導覽**：倒數每秒都 `repolish` 造成不必要開銷，改為僅狀態變化時；修正無效 index 的處理。
3. **批次 3（3a5fecd）日曆頁**：重疊行程遮蓋改為並排分欄；雙擊後吃單擊的問題，已修正；1px 線在縮放下模糊，改用 `fillRect`；即將到來清單出現重複項，已修正。
4. **批次 4（e3a32ef）對話框／設定／toast／托盤**：toast 重疊改由 `ToastStack` 堆疊；授權失敗文字被後續狀態覆蓋，改為保留；測試提醒原本繞過堆疊，改發 `test_toast_requested` 由 `main.py` 統一顯示。

## 📌 測試
- 測試數量：125（階段 B）→ 382（`python -m pytest -q`：382 passed）。
- 新增測試：`test_theme`/`test_styles`/`test_icons`/`test_components`/`test_win_titlebar`/`test_nav_sidebar`/`test_calendar_logic`/`test_calendar_widgets`/`test_calendar_view`/`test_calendar_dialog`/`test_settings_view`/`test_toast_window`/`test_tray_menu`/`test_water_timer`/`test_save_config_or_warn`。
- UI 測試共用 session offscreen QApplication，避免 `processEvents()`。

## 📌 預覽畫面（`python scripts/render_preview.py --out <資料夾>`）
components、main_shell（1180x740／960x620）、main_water、main_month（1180x740／960x620）、main_week、main_day、main_month_empty、settings、settings_connected、dialog_new、dialog_edit、dialog_allday、confirm_delete、toast_water、toast_danger、tray_menu。

## 📌 待使用者實機測試清單
- [ ] 實際畫面與字型
- [ ] 深色標題列（主視窗與對話框）
- [ ] 高 DPI（125%/150% 下圖示與 1px 線）
- [ ] 最小視窗 960×620
- [ ] 月週日切換與 ‹ › 今天
- [ ] 雙擊新增／點行程編輯
- [ ] 對話框全天切換與儲存回寫
- [ ] 刪除確認
- [ ] toast 按鈕（延後 10 分鐘、已喝）與 hover 暫停
- [ ] 多則 toast 堆疊
- [ ] 托盤選單樣式
- [ ] 設定頁各開關寫入 config
- [ ] Google 登入／登出
- [ ] 關閉視窗縮到系統匣

## 📌 後續事項
- 階段 D：autostart（已知問題 8）、清理 `arrow_*.png`／`arrow_generator.py`／`qss_url`、處理 `test_event_store` 的 processEvents。
- 週視圖 7 欄下 3 筆以上重疊行程很窄（靠 tooltip）；`DatePopupButton` 仍用 `QCalendarWidget`。
