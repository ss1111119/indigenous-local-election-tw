## 1. 解決循環匯入前提

- [x] 1.1 把 `class ValidationError(Exception)` 從 `scripts/build_local_election.py` 搬到 `scripts/oracles.py`，`build_local_election.py` 改為 `from oracles import ValidationError`，依循設計決定「`ValidationError` 搬到 `oracles.py`，`build_local_election.py` 改為匯入它」。驗證：`git grep "class ValidationError" scripts/` 只找到一處定義（在 `oracles.py`）；執行 `python -m pytest scripts/test_build_local_election.py scripts/test_build_legislative_election.py scripts/test_build_party_list_election.py -q`，確認既有測試（含既有對 `ValidationError` 的 `except`／`isinstance` 斷言）全數通過，證明搬移後其他檔案既有的 `from build_local_election import ValidationError` 仍能拿到同一個類別物件。

## 2. 共用的人口數驗證函式

- [x] 2.1 在 `scripts/oracles.py` 新增 `check_population_column(rows, label, column="人口數")`，依循設計決定「共用函式命名 `check_population_column`，可重用於任何欄位而不寫死欄名」與「檢查順序：先 `is_finite()` 再比較負值，避免對 NaN 做比較」，`except` 同時攔截 `ArithmeticError` 與 `TypeError`，實作 Requirement「Population column validation rejects non-finite and non-string values」的四個情境（Infinity、NaN、非字串、合法值）。驗證：新增合成測試，分別餵入 `"abc"`（非數字）、`"Infinity"`、`"-Infinity"`、`"NaN"`、`None`（非字串）、`"-5"`（負值）、`"0"`、`"1234.5"` 八種 `人口數` 值，斷言前六種都拋出 `ValidationError` 且各自的錯誤訊息可互相區分（不是同一段文字），後兩種不拋例外。
- [x] 2.2 讓 `scripts/build_local_election.py` 的 `cross_validate()` 改為呼叫 `check_population_column`，取代原本內嵌的 `人口數` 判斷；讓 `scripts/build_legislative_election.py` 移除自己的 `check_population_is_valid_decimal` 函式定義，改為直接呼叫 `oracles.check_population_column`。驗證：對 `data/processed/` 現有的地方公職與立委長表分別執行 `python scripts/build_local_election.py`、`python scripts/build_legislative_election.py`，兩者都正常完成、不中止；用 `git diff --stat data/processed/` 確認兩支腳本的既有輸出檔案內容不變（重構沒有改變任何合法資料的驗證結果或輸出）。

## 3. Oracle 文件的原子寫入

- [x] 3.1 在 `scripts/oracles.py` 新增 `write_oracle_document()`，依循設計決定「原子寫入函式 `write_oracle_document()` 一併放進 `oracles.py`」，在 `docs/schema/` 目錄下建立暫存檔、寫入 `render_markdown()` 的輸出、以 `os.replace()` 取代目標檔案，實作 Requirement「The shared oracle document is written atomically」的兩個情境（原子替換、兩支腳本共用同一個寫入路徑）。驗證：新增測試呼叫 `write_oracle_document()`，讀回 `docs/schema/oracles.md` 的內容，斷言與呼叫當下 `render_markdown()` 的回傳字串逐字元相同；且測試後確認 `docs/schema/` 目錄下沒有殘留任何暫存檔案（沒有以暫存檔案命名模式殘留的檔案）。
- [x] 3.2 讓 `scripts/build_local_election.py` 與 `scripts/build_legislative_election.py` 收尾寫入 `docs/schema/oracles.md` 的那一行都改為呼叫 `write_oracle_document()`，移除各自手寫的 `write_text(...)` 呼叫。驗證：依序執行兩支腳本，用 `git diff --stat docs/schema/oracles.md` 確認這次變更之前與之後的檔案內容逐位元組相同（只改變寫入手法，不改變輸出內容）。
