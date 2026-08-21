## Problem

候選人長表的 `當選` 欄忠實反映來源的已知錯誤：2005 縣市議員兩檔的 `elcand` 當選註記損壞，山原以 `當選` 只算出 18 席（正確 30）、平原 20（正確 27），1994 高雄市另有 2 筆標錯人。合計 **63 位候選人**的 `當選` 與事實不符。

正確值在 `elected_authoritative`，文件也寫著「要席次請用 `elected_authoritative`」。但那正是 `candidate-age-valid-column` 已判定為**不夠**的做法——不讀文件的分析者第一直覺是用 `當選`，而 `當選` 這個名字有最強的預設吸引力。

年齡那次錯 3 歲；這裡錯 **19 席**。

## Root Cause

`當選` 由來源的 `當選註記` 推導（註記為 `*` 或 `!` 即為 `Y`），忠實但不可靠。權威值由 `elctks` 跨檔推導，放在名字較長、需要先讀文件才會知道的 `elected_authoritative`。

專案已於 `candidate-age-valid-column` 確立慣例：**最直覺的欄位名，必須存放對分析最安全的資料。** `當選` 沒有跟上。

## Proposed Solution

`當選` 改存**權威值**，維持既有的 `Y`／`N` 編碼。

**不新增 `當選_原始`。** 與年齡那次不同：`當選` 本來就不是來源原值，來源原樣是 `當選註記`（`*`／空白／`!`／`-`），而它與解碼後的 `當選註記語意` 都已完整保留在長表中。再加一個 `當選_原始` 會是同一事實的第三份表述，正是本專案反覆在消除的重複。

`elected_authoritative` 移除——它的值與 `當選` 完全相同，留著就是同一事實的兩份來源。`elected_authoritative_basis` 更名為 `當選_依據`，內容不變。

## Non-Goals

- **不改變 `Y`／`N` 編碼。** 同時改語意與編碼會讓靜默破壞最大化。而且移除 `elected_authoritative` 之後，`true`／`false` 這個形式自然從這個概念中消失。
- **不新增 `當選_原始`。** 理由見上。
- **不改動 `當選註記` 與 `當選註記語意`。** 那兩欄是來源原樣與其解碼，必須維持。
- 不改動 summary 與 votes 兩張長表。
- 不改變站台的任何顯示結果。

## Success Criteria

- `當選` 逐列等於本變更前的 `elected_authoritative`（`true`→`Y`、`false`→`N`）。
- `當選註記` 與 `當選註記語意` 逐列不變。
- 長表不再有 `elected_authoritative` 欄；`當選_依據` 的內容逐列等於本變更前的 `elected_authoritative_basis`。
- 欄位數由 29 變 28。
- **那 63 筆具名異常仍然被偵測到**：補償檢查改為比對「由 `當選註記` 推導的值」與「權威值」，而非兩個權威值。
- 站台 `--check` 通過，兩個 HTML 位元組不變。

## Impact

- Affected specs: `legacy-source-quirks`（MODIFIED：權威值的存放位置）
- Affected code:
  - Modified:
    - `scripts/build_local_election.py`
    - `scripts/oracles.py`
    - `scripts/test_build_local_election.py`
    - `scripts/mutate_build_local_election.py`
    - `scripts/build_site_data.py`
    - `scripts/test_build_site_data.py`
    - `scripts/mutate_build_site_data.py`
    - `data/processed/cec-local-election-candidates-long.csv`
    - `data/sources.json`
    - `docs/schema/cec-local-election.md`
    - `README.md`
  - New: (none)
  - Removed: (none)
