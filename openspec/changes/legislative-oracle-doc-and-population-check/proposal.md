## Why

`scripts/oracles.py` 已經宣告了立委三張長表的欄位語意（`LEGISLATIVE_MANIFEST`，
含 `人口數`、`政黨代號`、`性別` 等 25 個欄位各自的來源、語意 oracle、備註），
但產生 `docs/schema/oracles.md` 的 `render_markdown()` 只遍歷本地選舉的
`MANIFEST`，從未處理 `LEGISLATIVE_MANIFEST`；且只有 `build_local_election.py`
呼叫這個算繪函式寫入該檔，`build_legislative_election.py` 從未呼叫過。
結果是：`docs/schema/oracles.md` 完全沒有立委欄位的任何內容——`LEGISLATIVE_MANIFEST`
是已經宣告卻沒被算繪出來的死碼，讀者只能去讀 Python 原始碼才看得到這些語意。
這件事是在評估「立委 schema 文件是否有缺口」時，實際去讀
`scripts/oracles.py`、比對 `docs/schema/oracles.md` 的產出內容才發現的
（不是猜測，已用 `grep` 對 `docs/schema/oracles.md` 找立委獨有欄位如
`選舉區_語意`、`投票率_檔案`，零筆命中）。

同一輪查證另外發現：`build_legislative_election.py` 的 `人口數` 欄位
（`"人口數": r[10].strip()`）沒有 `build_local_election.py` 那種
`Decimal()` 可解析性與非負值的自我驗證（`cross_validate` 裡對
`s["人口數"]` 做的檢查）。這是輸入資料品質的防護缺口——非數字或負值字串
會靜默流到輸出，沒有任何自我驗證會擋下來。

## What Changes

- `scripts/oracles.py` 的算繪邏輯改為可重用：抽出一個內部輔助函式，
  接受任一份 manifest（`MANIFEST` 或 `LEGISLATIVE_MANIFEST`）與其欄位分類
  名稱對照表，回傳該 manifest 的 Markdown 區塊。`render_markdown()`
  改為呼叫這個輔助函式兩次（本地選舉一次、立委一次），組成同一份文件，
  立委的三張表各自成一節、標題清楚區分於本地選舉的三節之外。
- `build_legislative_election.py` 的 `main()` 收尾時，比照
  `build_local_election.py` 現有的呼叫方式，呼叫同一個
  `render_markdown()` 並寫入 `docs/schema/oracles.md`。兩支腳本都可能
  各自呼叫寫入同一份檔案，但因為輸出只由靜態的 `MANIFEST`／
  `LEGISLATIVE_MANIFEST` 決定、與呼叫端的執行順序或執行時期算出的資料
  無關，兩邊寫出的位元組必然相同，不存在互相覆寫掉對方內容的風險。
- `build_legislative_election.py` 新增一個獨立的自我驗證函式，驗證
  `人口數` 欄位的每一列都能被 `Decimal()` 解析且不為負值，比照
  `build_local_election.py` 對同一欄位的既有驗證邏輯與錯誤訊息風格。

## Non-Goals

- 不處理 `PARTY_LIST_MANIFEST`（政黨票不分區長表的欄位宣告）——同類但
  獨立的缺口，留待之後另開 change。
- 不重寫或擴充 `docs/schema/cec-legislative-election.md`（既有的敘述式
  文件）——這次的修法是讓 `LEGISLATIVE_MANIFEST` 透過既有的
  `docs/schema/oracles.md` 曝光，不是在敘述式文件上疊加內容。
- 不改變 `LEGISLATIVE_MANIFEST` 本身宣告的任何欄位語意內容，純粹是讓
  既有宣告被算繪出來。
- 不替 `人口數` 以外的欄位新增驗證——這次只補查證過的那一個具體缺口。

## Capabilities

### New Capabilities

- `column-oracle-documentation`：每張長表的欄位語意宣告（manifest）必須透過共用的欄位 oracle 文件對所有資料集一致地曝光，不能有宣告了卻沒被算繪出來的 manifest；且欄位的自我驗證覆蓋率在不同資料集之間應保持一致，不能同一欄位在一個資料集有防護、另一個沒有。

## Impact

- Affected specs: `column-oracle-documentation`（新增）
- Affected code:
  - New: (none)
  - Modified: `scripts/oracles.py`, `scripts/build_legislative_election.py`
  - Removed: (none)
