## Summary

把 `PARTY_LIST_MANIFEST`（政黨票不分區長表三張表的欄位語意宣告）算繪進
`docs/schema/oracles.md`，補上跟立委那次同一類的曝光缺口。

## Motivation

`scripts/oracles.py` 已經宣告 `party_list_summary`／`party_list_votes`／
`party_list_seats` 三張表的欄位語意（`PARTY_LIST_MANIFEST`），
`build_party_list_election.py` 也已經用它做欄位集合的結構驗證
（`check_output_manifests`），但 `render_markdown()` 從未處理這份
manifest，`build_party_list_election.py` 也從未呼叫 `render_markdown()`
或 `write_oracle_document()` 寫入 `docs/schema/oracles.md`。跟
`legislative-oracle-doc-and-population-check`（已歸檔）修的是完全同一類
問題：宣告存在、沒被曝光。

上一輪已經把算繪邏輯抽成可重用的 `_render_manifest_sections(manifest,
names)`，且新增了共用的原子寫入函式 `write_oracle_document()`——這次要做
的事情因此範圍很小：多呼叫一次已存在的輔助函式，不需要再抽象化或重構
任何既有邏輯。

## Proposed Solution

- `render_markdown()` 在既有的本地選舉、立委兩組區塊之後，再呼叫一次
  `_render_manifest_sections(PARTY_LIST_MANIFEST, names)`，`names` 對照表
  涵蓋 `party_list_summary`／`party_list_votes`／`party_list_seats` 三個鍵。
- `build_party_list_election.py` 的 `main()` 收尾（`commit_outputs(...)`
  呼叫之後）新增呼叫 `write_oracle_document()`。

## Non-Goals

- 不替政黨票長表新增任何欄位驗證——已查證這三張表都沒有 `人口數` 欄位
  （`grep` 不到），沒有跟立委那次一樣的驗證缺口需要補。
- 不處理 `indigenous-party-preference-bounds.csv`（界限估計表）——它不在
  `PARTY_LIST_MANIFEST` 宣告範圍內，是獨立的衍生表，不是這次要曝光的對象。
- 不改變 `PARTY_LIST_MANIFEST` 已宣告的任何欄位語意內容。

## Impact

- Affected specs: `column-oracle-documentation`（修改）
- Affected code:
  - New: (none)
  - Modified: `scripts/oracles.py`, `scripts/build_party_list_election.py`
  - Removed: (none)
