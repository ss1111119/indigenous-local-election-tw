## Problem

`scripts/oracles.py` 這個 session 新增／搬移過去的三個共用函式——
`check_population_column`、`write_oracle_document`、
`_render_manifest_sections`——完全沒有被任何一支 `mutate_build_*.py`
的變異測試覆蓋到。目前這三個函式的辨識力只靠 `test_build_legislative_election.py`
與 `test_build_party_list_election.py` 裡的合成單元測試，沒有變異測試
證明「這幾個函式的邏輯壞了，測試真的會抓到」。

## Root Cause

問題比「忘記補變異」更根本：`mutate_build_legislative_election.py`與
`mutate_build_party_list_election.py`各自用 `pytest -k SEL` 這種明確
列舉測試函式名稱字串的方式篩選要跑哪些測試（`SEL` 是一段
`"test_a or test_b or ..."` 的字串），而這兩支腳本的 `SEL` 字串裡完全
沒有列到這個 session 新增的五個測試函式名稱：
`test_legislative_oracle_rendered_into_shared_document`、
`test_manifest_rendering_reflects_new_columns`、
`test_population_is_valid_decimal`、
`test_oracle_document_written_atomically`（`mutate_build_legislative_election.py`）
與 `test_party_list_oracle_rendered_into_shared_document`
（`mutate_build_party_list_election.py`）。

這代表即使現在補上針對這三個函式的變異，變異測試套件也**看不到**
對應的斷言——`pytest -k SEL` 會直接把這些測試排除在被執行的集合之外，
不管變異有沒有真的改壞邏輯，結果都是「這些測試沒被跑，看不出差別」。
必須先修 `SEL`，變異才有意義。

## Proposed Solution

- 把 `test_legislative_oracle_rendered_into_shared_document`、
  `test_manifest_rendering_reflects_new_columns`、
  `test_population_is_valid_decimal`、
  `test_oracle_document_written_atomically` 加進
  `mutate_build_legislative_election.py` 的 `SEL` 字串。
- 把 `test_party_list_oracle_rendered_into_shared_document` 加進
  `mutate_build_party_list_election.py` 的 `SEL` 字串。
- 在 `mutate_build_legislative_election.py` 新增至少兩項真檔變異：
  一項針對 `check_population_column`（例如拿掉 `is_finite()` 檢查，讓
  `Infinity`／`NaN` 通過驗證），一項針對 `write_oracle_document`
  （例如讓它在寫入前就直接 `return`，跳過寫入本身）。
- 在 `mutate_build_party_list_election.py` 新增至少一項真檔變異，針對
  `_render_manifest_sections` 在 `render_markdown()` 裡被呼叫處理
  `PARTY_LIST_MANIFEST` 的那一行（例如整行拿掉，讓政黨票區塊不再出現）。
- 每一項變異都手動用該腳本既有的變異測試機制（`fresh_copies()` /
  `prepare()` 加 `run()` 或等效流程）驗證：套用變異後對應測試由通過
  變成失敗，撤銷變異後恢復通過。

## Non-Goals

- 不處理 `mutate_build_local_election.py`——`test_build_local_election.py`
  本身沒有涵蓋 `check_population_column`／`write_oracle_document`／
  `_render_manifest_sections` 的專屬單元測試，這三個函式在
  `build_local_election.py` 那一側的行為驗證，責任邊界不在這裡。
- 不改變 `check_population_column`、`write_oracle_document`、
  `_render_manifest_sections` 本身的任何邏輯或行為，純粹是補測試覆蓋率。
- 不修改 `SEL` 字串以外、與這三個函式無關的既有測試篩選內容。

## Success Criteria

- `mutate_build_legislative_election.py` 與
  `mutate_build_party_list_election.py` 的 `SEL` 字串各自含這次列出的
  新測試函式名稱。
- 兩支腳本各自新增的真檔變異，跑過至少一次「套用變異 → 對應測試失敗
  → 撤銷變異 → 對應測試恢復通過」的手動驗證循環，且已併入各自 `main()`
  的變異迴圈中。
- 執行 `python scripts/mutate_build_legislative_election.py` 與
  `python scripts/mutate_build_party_list_election.py`，全部變異（含
  既有項目與這次新增項目）皆回報偵測到，沒有漏網。

## Impact

- Affected specs: `column-oracle-documentation`（修改）
- Affected code:
  - Modified: `scripts/mutate_build_legislative_election.py`,
    `scripts/mutate_build_party_list_election.py`
  - New: (none)
  - Removed: (none)
