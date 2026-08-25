## Context

`scripts/oracles.py` 目前是「零內部依賴」的基礎模組（只 `from __future__ import
annotations`），`build_local_election.py`、`build_legislative_election.py`
都從它匯入 `MANIFEST`／`LEGISLATIVE_MANIFEST`／`check_manifest_against`／
`render_markdown`。反過來，`ValidationError` 目前定義在
`build_local_election.py`（第 729 行），`build_legislative_election.py`、
`build_party_list_election.py` 與各自的測試檔、變異測試檔都是
`from build_local_election import ValidationError`。

若要把 `人口數` 的驗證邏輯搬進 `oracles.py` 成為單一共用函式並讓它拋出
`ValidationError`，`oracles.py` 就必須匯入 `build_local_election.py`——
但 `build_local_election.py` 已經匯入 `oracles.py`，這會形成循環匯入。

## Goals / Non-Goals

**Goals:**
- `人口數` 驗證邏輯只有一份，`build_local_election.py` 與
  `build_legislative_election.py` 都呼叫同一份，不能再各自維護一份
  容易漂移的複本。
- 驗證邏輯正確處理 `Infinity`／`NaN`／非字串輸入，全部歸一成本專案的
  `ValidationError`。
- `docs/schema/oracles.md` 的寫入是原子操作。

**Non-Goals:**
- 不處理跨行程／跨機器的寫入協調（見 proposal Non-Goals）。
- 不改變任何合法人口數值的驗證結果。

## Decisions

### `ValidationError` 搬到 `oracles.py`，`build_local_election.py` 改為匯入它

解決循環匯入的根本辦法是把依賴方向理順：`oracles.py` 本來就是兩支腳本
共用的基礎模組，`ValidationError` 這個共用例外類別的自然歸屬也是這裡，
而不是某一支腳本。把類別定義搬到 `oracles.py`，`build_local_election.py`
改為 `from oracles import ValidationError`（不再自己定義）。因為 Python
的 import 是名稱綁定，`build_party_list_election.py`、
`build_legislative_election.py` 與各測試檔既有的
`from build_local_election import ValidationError` 完全不用改，
`build_local_election.ValidationError` 仍然指向同一個類別物件。

### 共用函式命名 `check_population_column`，可重用於任何欄位而不寫死欄名

雖然目前只用在 `人口數`，但把欄位名稱寫死在函式名稱或邏輯裡會讓「共用」
名不符實——之後若有其他欄位需要同樣的可解析非負十進位檢查，又要複製一份。
簽名為 `check_population_column(rows: list[dict], label: str, column: str =
"人口數") -> None`，預設值涵蓋現有兩個呼叫端都只驗 `人口數` 的情況，
不強迫呼叫端每次都要打欄名。

### 檢查順序：先 `is_finite()` 再比較負值，避免對 NaN 做比較

`Decimal.is_finite()` 對 `NaN`、`Infinity`、`-Infinity` 皆回傳 `False`，
對一般有限數值回傳 `True`。把這個檢查放在 `pop < 0` 之前，NaN 與 Infinity
都會在到達比較運算之前就被攔下，不會有機會觸發
`decimal.InvalidOperation`。`except` 子句同時攔截 `ArithmeticError`（涵蓋
`Decimal()` 解析失敗）與 `TypeError`（涵蓋輸入不是字串，例如 `None`），
兩種都轉成同一種 `ValidationError` 訊息格式、只有描述失敗原因的文字不同。

### 原子寫入函式 `write_oracle_document()` 一併放進 `oracles.py`

跟 `render_markdown()` 同一個模組，呼叫端只需要
`oracles.write_oracle_document()`，不需要自己組 `ROOT / "docs" / "schema" /
"oracles.md"` 路徑或處理暫存檔案。實作用 `tempfile.NamedTemporaryFile`
在目標檔案的同一個目錄下建立暫存檔（同目錄才能保證 `os.replace()` 在
同一個檔案系統內，是真正原子的），寫完、`flush()`、`os.replace()`
取代目標檔案；任何步驟拋出例外時暫存檔不會被留下未清理（用
`try`/`finally` 或以暫存檔案本身的自動清理機制確保）。

## Implementation Contract

**行為**：
- 執行 `python scripts/build_local_election.py` 或
  `python scripts/build_legislative_election.py`，若對應長表的 `人口數`
  欄位任何一列不是可解析、有限、非負的十進位數字串，流程中止並拋出
  `ValidationError`，訊息文字依失敗原因分為三種（不是十進位數／非有限值
  Infinity 或 NaN／為負數），且都指名該筆資料的識別資訊。
- 兩支腳本執行完成後，`docs/schema/oracles.md` 的內容與呼叫
  `render_markdown()` 當下的輸出完全一致；即使腳本在寫入過程中被中斷，
  該檔案要嘛保持中斷前的舊內容、要嘛是完整的新內容，不會出現半份或
  交錯的內容。

**介面**：
- `oracles.py` 新增 `class ValidationError(Exception)`（從
  `build_local_election.py` 搬移過去，行為不變）。
- `oracles.py` 新增 `check_population_column(rows: list[dict], label: str,
  column: str = "人口數") -> None`，驗證失敗拋出 `ValidationError`。
- `oracles.py` 新增 `write_oracle_document() -> None`，內部呼叫
  `render_markdown()` 並以暫存檔＋`os.replace()` 的方式寫入
  `ROOT / "docs" / "schema" / "oracles.md"`（`ROOT` 由 `oracles.py` 自行
  以 `Path(__file__).resolve().parent.parent` 推導，不依賴呼叫端傳入）。
- `build_local_election.py` 移除本地的 `class ValidationError` 定義，
  改為 `from oracles import ValidationError`；`cross_validate()` 裡原本
  對 `人口數` 的內嵌判斷改為呼叫 `check_population_column`。
- `build_legislative_election.py` 移除自己的
  `check_population_is_valid_decimal` 函式定義，`main()` 裡的呼叫點改為
  直接呼叫 `oracles.check_population_column`（或匯入後直接呼叫
  `check_population_column`）。
- 兩支腳本收尾寫入 `docs/schema/oracles.md` 的那一行，改為呼叫
  `oracles.write_oracle_document()`，移除各自手寫的
  `(ROOT / "docs" / "schema" / "oracles.md").write_text(...)`。

**失敗模式**：
- `人口數` 值無法被 `Decimal()` 解析（例如 `"abc"`）→ `ValidationError`，
  訊息含「不是十進位數」字樣。
- `人口數` 值可解析但非有限（`"NaN"`、`"Infinity"`、`"-Infinity"`）→
  `ValidationError`，訊息含「非有限值」或等義字樣，明確與「不是十進位數」
  的訊息文字不同。
- `人口數` 值為負的有限十進位數 → `ValidationError`，訊息含「為負數」
  字樣。
- `人口數` 值不是字串（例如 `None`、`int`）→ 同「不是十進位數」那類
  `ValidationError`（`TypeError` 與 `ArithmeticError` 歸為同一種失敗訊息，
  因為對呼叫端而言兩者都是「這個值本來就不該被當成十進位數字串」）。
- 上述四種都不成立（合法值）→ 函式正常返回。

**驗收標準**：
- 新增合成測試涵蓋以上四種失敗情境與合法值情境（含 `"0"`、帶小數的
  字串），對 `check_population_column` 直接呼叫驗證。
- 對 `data/processed/` 現有的地方公職與立委長表分別執行
  `python scripts/build_local_election.py`、
  `python scripts/build_legislative_election.py`，兩者都正常完成、不中止
  （證明重構沒有改變既有合法資料的驗證結果）。
- 新增測試驗證 `write_oracle_document()` 寫入後的檔案內容與
  `render_markdown()` 的回傳字串逐字元相同。
- 執行兩支腳本後 `docs/schema/oracles.md` 的內容與這次變更之前逐位元組
  相同（重構不改變輸出內容，只改變實作方式與寫入手法）。
- `git grep "class ValidationError"` 確認整個 repo 只有一處類別定義
  （在 `oracles.py`），`build_local_election.py` 不再自行定義。

**範圍邊界**：只動 `scripts/oracles.py`、`scripts/build_local_election.py`、
`scripts/build_legislative_election.py` 三個檔案。不動
`build_party_list_election.py`（它匯入 `ValidationError` 的方式不受影響，
不需要跟著改）、不動 `PARTY_LIST_MANIFEST`、不改變任何合法資料的驗證結果。

## Risks / Trade-offs

[把 `ValidationError` 搬到 `oracles.py`，若之後有人忘記這個歷史脈絡、
在 `build_local_election.py` 重新定義一個同名類別，會製造出兩個同名但
不同的例外類別，`except ValidationError` 可能抓不到另一邊拋出的例外]
→ 用 `git grep "class ValidationError"` 恰好一處作為驗收標準的一部分，
且 `build_local_election.py` 改成明確的 `from oracles import
ValidationError` 匯入陳述式，行為上等同型別別名，不容易被誤會成
「這裡也可以重新定義」。

[`os.replace()` 在同一個檔案系統內是原子的，但若 `docs/schema/` 目錄
所在的磁碟區與暫存檔案預設建立位置不同（例如系統暫存目錄在另一個磁碟
分割區），`os.replace()` 跨檔案系統會失敗或退化為非原子的複製＋刪除]
→ `write_oracle_document()` 明確在目標檔案的同一個目錄（`docs/schema/`）
底下建立暫存檔，不使用系統預設暫存目錄，避免跨檔案系統的問題。
