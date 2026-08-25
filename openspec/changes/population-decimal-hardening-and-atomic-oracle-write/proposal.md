## Why

上一個 change（`legislative-oracle-doc-and-population-check`）替
`build_legislative_election.py` 補上了跟 `build_local_election.py` 對等的
`人口數` 欄位驗證（`Decimal()` 可解析性＋非負值），完成後請 Codex 做實作審查，
查出兩支腳本這段邏輯共同帶有三個既有弱點（不是這次改動新引入的，是逐行
比照複製過去的既有邏輯，兩邊完全對稱）：

1. `Decimal("Infinity")` 能通過非負值檢查，但不是合理的人口數。
2. `Decimal("NaN")` 能被 `Decimal()` 解析成功（不觸發 `except`），但後續
   `pop < 0` 比較 NaN 時會拋出 `decimal.InvalidOperation`，這個例外沒有被
   攔截、不會變成專案統一的 `ValidationError`，會以未預期的例外類型中止。
3. 若輸入不是字串（例如 `None`），`Decimal()` 會拋 `TypeError`，同樣沒有
   被攔截、不會變成 `ValidationError`。

目前真實資料不會觸發這三種情況（每筆 `人口數` 都來自 CSV 讀出的字串，
從未出現 `Infinity`／`NaN`／`None`），所以不是現有資料的回歸，但驗證函式
本身沒有完整實現它宣稱的「可解析、非負的十進位人口數」這個意圖。

同一輪審查也指出：`build_local_election.py` 與 `build_legislative_election.py`
各自呼叫 `oracles.render_markdown()` 並用 `write_text()` 整段覆寫
`docs/schema/oracles.md`，這不是原子寫入——若兩支腳本未來真的並行執行，
理論上可能寫出交錯或中斷後的半份檔案。目前建置流程是人工依序執行、不算
實際風險，但值得預先補上防護。

## What Changes

- 把 `人口數` 的可解析性與非負值驗證邏輯統一搬進 `scripts/oracles.py`，
  成為單一共用函式（例如 `check_population_column(rows, label, column="人口數")`），
  修正上述三個弱點：`except` 同時攔截 `ArithmeticError` 與 `TypeError`；
  額外檢查 `pop.is_finite()`（同時擋下 `Infinity` 與 `NaN`，因為
  `Decimal.is_finite()` 對兩者皆回傳 `False`），檢查放在 `pop < 0` 之前，
  避免比較 NaN 時拋出未攔截的 `InvalidOperation`。
- `build_local_election.py` 的 `cross_validate()` 改為呼叫這個共用函式，
  取代原本內嵌在函式中段的那幾行判斷；`build_legislative_election.py` 的
  `check_population_is_valid_decimal` 改為直接呼叫（或整個替換為呼叫）
  這個共用函式，不再各自維護一份邏輯。
- 在 `scripts/oracles.py` 新增 `write_oracle_document()`，把
  `render_markdown()` 的輸出寫進暫存檔後以 `os.replace()` 原子替換
  `docs/schema/oracles.md`；`build_local_election.py` 與
  `build_legislative_election.py` 收尾時都改為呼叫這個函式，取代原本
  各自的 `(ROOT / "docs" / "schema" / "oracles.md").write_text(...)` 那一行。

## Non-Goals

- 不改變 `人口數` 欄位對合法值（非負、有限的十進位字串，含 `"0"` 與帶小數
  的字串）的判定結果——這次只補邊界情況的例外處理，不改變既有真實資料的
  驗證結果。
- 不處理跨行程／跨機器層級的檔案鎖定或分散式寫入協調——`os.replace()`
  只解決「寫到一半被中斷留下半份檔案」與「單一檔案系統上的寫入不可切割」
  這兩件事，不處理真正意義上的並行寫入排程。
- 不替 `人口數` 以外的欄位新增驗證。
- 不動 `PARTY_LIST_MANIFEST` 或政黨票長表的任何邏輯。

## Capabilities

### Modified Capabilities

- `column-oracle-documentation`：新增「人口數欄位驗證必須拒絕非有限值
  （Infinity／NaN）與非字串輸入，且失敗一律以本專案統一的例外類型呈現」
  與「oracle 文件的寫入必須是原子操作」這兩項要求。

## Impact

- Affected specs: `column-oracle-documentation`（修改）
- Affected code:
  - New: (none)
  - Modified: `scripts/oracles.py`, `scripts/build_local_election.py`,
    `scripts/build_legislative_election.py`
  - Removed: (none)
