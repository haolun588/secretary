# 收工日誌 (Dev Log) - 2026-11-25 (等級改存 extendedProperties)

## 📌 目標
- 行程等級（major/medium/minor）改存於 Google 事件的 `extendedProperties.private.secretary_priority`，顏色（colorId）只當顯示與備援。

## 📌 動機
- 原本只以 `colorId` 判斷等級，使用者在網頁或手機改顏色就會悄悄改變等級；且多種 colorId 對應同一等級，資訊不精確。

## 📌 做法
- `services/event_mapping.py`：
  - 新增 `PRIORITY_PROP_KEY`、`VALID_PRIORITIES`、`priority_from_item(item, default)`（ext 合法值優先，缺失/None/非字串/不合法皆退回 `priority_from_color`，不拋例外）、`extended_properties_for(priority)`（未知等級寫 "minor"）。
  - `from_google` 的 `priority` 改用 `priority_from_item`；內部 dict 欄位不變。
  - `to_google_body` 加上 `extendedProperties`；`build_patch_body` 等級變動時同時送 `colorId` 與 `extendedProperties`，未變動不送，完全沒變仍為 `{}`。
- `tests/test_event_mapping.py`：新增優先序、不合法值、缺失結構、body 內容、patch 行為與 round-trip 測試；既有 `test_patch_priority_changed_sends_color` 的斷言因多了 `extendedProperties` 而調整。
- 文件：`docs/architecture.md`、`docs/dev_rules.md`、`docs/progress.md` 同步。

## 📌 決策
1. 衝突時以 `extendedProperties` 為準：網頁/手機手動改顏色不會改變已存的等級。
2. 舊事件不主動補寫：僅在從程式新增或修改等級時才寫入，避免啟動時大量呼叫 API 改動使用者日曆。

## 📌 未驗證事項
- Google Calendar API `events.patch` 對 `extendedProperties.private` 是否合併 key（依 patch 一般語意，巢狀物件應為合併；且本程式只寫這一個 key，影響有限），尚未對真實日曆實測。
- 尚未實機驗證。
