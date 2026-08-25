## Context

`scripts/oracles.py` 是 `build_local_election.py` 與 `build_legislative_election.py`
共用的模組，內含三份 manifest：`MANIFEST`（本地選舉三張表）、
`LEGISLATIVE_MANIFEST`（立委三張表）、`PARTY_LIST_MANIFEST`（政黨票長表，
不在本次範圍）。`render_markdown()` 目前的實作（第 714-757 行）寫死只讀
`MANIFEST`，用一個寫死的 `names = {"summary": ..., "candidates": ...,
"votes": ...}` 對照表產生三個 `##` 區塊。只有 `build_local_election.py`
的 `main()` 收尾呼叫它並寫入 `docs/schema/oracles.md`（`# oracle 文件由
manifest 生成，手寫會脫節` 那一行）；`build_legislative_election.py` 從未
呼叫。因此 `LEGISLATIVE_MANIFEST` 完整存在於原始碼裡（`人口數`、
`政黨代號`、`性別` 等 25 欄，每欄都有 `provenance`／`structure`／
`arithmetic`／`semantic`／`note` 五個欄位），卻沒有任何管道讓不讀原始碼
的人看到。

`build_legislative_election.py` 的 `main()` 已經呼叫
`check_manifest_against(LEGISLATIVE_MANIFEST, ...)` 驗證欄位集合與
manifest 相符（結構層），但沒有像 `build_local_election.py`
`cross_validate()` 那樣對 `人口數` 做語意層的 `Decimal()` 可解析性與
非負值檢查。已用 `grep` 確認立委資料的 `人口數` 欄實測沒有空字串
（`LEGISLATIVE_MANIFEST` 的備註「細層級為 0 代表該層級不適用」與實測
一致），所以直接比照本地選舉的驗證邏輯不會誤殺合法資料。

## Goals / Non-Goals

**Goals:**
- `docs/schema/oracles.md` 涵蓋本地選舉與立委兩個資料集全部已宣告的
  manifest 欄位，讀者不需要讀 Python 原始碼就能看到立委欄位的語意宣告。
- `build_legislative_election.py` 的 `人口數` 欄位有跟本地選舉對等的
  可解析性與非負值自我驗證。

**Non-Goals:**
- 不處理 `PARTY_LIST_MANIFEST`（見 proposal Non-Goals）。
- 不改變任何 manifest 已宣告的欄位語意內容本身。
- 不對 `人口數` 以外的欄位新增驗證。

## Decisions

### `render_markdown()` 改為可重用的雙 manifest 算繪，不是新增第二支算繪函式

抽出一個接受 `(manifest, names, section_prefix)` 的內部輔助函式（例如
`_render_manifest_sections`），`render_markdown()` 呼叫它兩次分別處理
`MANIFEST`（沿用既有的 `summary`／`candidates`／`votes` 三個區塊名稱）與
`LEGISLATIVE_MANIFEST`（用 `legislative_summary`／`legislative_candidates`／
`legislative_votes` 這三個既有鍵名對應到「立委選舉概況 summary」等區塊
標題），輸出串接成同一份文件。不另外寫一支
`render_legislative_markdown()` 各自輸出到不同檔案——`docs/schema/oracles.md`
的既有讀者（README 若有連結、開發者書籤）預期是單一入口，拆成兩份檔案會
造成新的「該看哪一份」的困惑，且與 proposal 的「同一份文件、分節呈現」
決定一致。

### 兩支腳本都呼叫同一個 `render_markdown()`，不做「誰該負責寫入」的協調機制

`render_markdown()` 的輸出完全由兩份靜態 manifest 的內容決定，不依賴呼叫
腳本當次執行算出的任何資料（不像 `DATA`／`LEG` 那類常數）。所以
`build_local_election.py` 與 `build_legislative_election.py` 各自獨立呼叫
`render_markdown()` 並整段覆寫 `docs/schema/oracles.md`，兩者永遠寫出
逐位元組相同的內容——不需要「保留對方那一節」的協調機制，也不需要限定
執行順序。這比引入寫入鎖定或差異合併機制簡單，且沒有協調機制本身出錯
（例如漏合併、順序依賴）的風險。

### `人口數` 驗證獨立成新函式，不塞進既有的 `check_manifest_against` 呼叫

`check_manifest_against` 驗證的是**結構層**（欄位集合是否與 manifest
相符），`人口數` 的可解析性與非負值屬於**語意層**（見
`docs/schema/oracles.md` 開頭的三層框架），兩者是不同層級的驗證、不應該
混進同一個函式，也不應該假裝結構驗證通過就代表語意也對。新函式命名
`check_population_is_valid_decimal`，比照專案既有 `check_*` 函式的單一
職責慣例（例如 `check_age_sentinel`、`check_zero_turnout`），在 `main()`
裡跟其他 `check_*` 呼叫並列。

## Implementation Contract

**行為**：執行 `python scripts/oracles.py` 內部邏輯經由
`build_local_election.py --write`（或等效流程）或
`python scripts/build_legislative_election.py` 執行後：
- `docs/schema/oracles.md` 同時含本地選舉三個區塊（`## 選舉概況 summary`
  等既有標題不變）與立委三個新區塊（例如 `## 立委選舉概況 summary`、
  `## 立委候選人 candidates`、`## 立委候選人得票 votes`），立委三個區塊
  逐欄列出 `LEGISLATIVE_MANIFEST` 對應表的全部欄位，欄位數與
  `LEGISLATIVE_MANIFEST` 宣告數逐一相符。
- 若 `LEGISLATIVE_MANIFEST` 未來新增或移除欄位，重新執行
  `build_legislative_election.py` 後 `docs/schema/oracles.md` 的立委區塊
  內容隨之更新（因為是每次執行都重新算繪、整段覆寫，不是只在檔案不存在
  時才寫入）。
- `python scripts/build_legislative_election.py` 執行時，若立委資料的
  `人口數` 欄位任何一列不是可被 `Decimal()` 解析的字串或為負值，流程
  必須中止並拋出例外，錯誤訊息包含該筆資料的行政區識別（比照
  `build_local_election.py` 現有 `人口數不是十進位數`／`人口數為負數`
  訊息的格式，指名是哪一列）；資料合法時流程正常完成、不中止。

**介面**：
- `scripts/oracles.py` 新增內部輔助函式（例如
  `_render_manifest_sections(manifest: dict, names: dict[str, str]) ->
  list[str]`），回傳 Markdown 行的清單；`render_markdown() -> str` 的
  公開簽名不變，內部改為呼叫這個輔助函式兩次再合併回傳。
- `build_legislative_election.py` 新增函式
  `check_population_is_valid_decimal(rows: list[dict], label: str) ->
  None`，無回傳值，驗證失敗時拋出既有的 `ValidationError`（沿用
  `build_legislative_election.py` 既有的例外類別，不新增例外類別）。
- `build_legislative_election.py` 的 `main()` 在既有的
  `check_manifest_against(LEGISLATIVE_MANIFEST, ...)` 呼叫之後、
  `write_outputs(...)` 呼叫之前或之後（依現有其他 `check_*` 呼叫慣例的
  相對位置）新增對 `check_population_is_valid_decimal` 的呼叫，並在
  `write_outputs` 完成後新增
  `(ROOT / "docs" / "schema" / "oracles.md").write_text(render_markdown(),
  encoding="utf-8")` 這一行，比照 `build_local_election.py` 既有寫法與
  註解（`# oracle 文件由 manifest 生成，手寫會脫節`）。

**失敗模式**：
- `人口數` 某一列不是十進位數字串 → `ValidationError`，訊息含該列的
  行政區識別與原始字串值。
- `人口數` 某一列為負值 → `ValidationError`，訊息含該列的行政區識別與值。
- 兩者都不成立時（合法資料）→ 函式正常返回，不影響既有流程。

**驗收標準**：
- 執行 `python scripts/build_legislative_election.py` 後，
  `docs/schema/oracles.md` 含立委三個新區塊，且每個區塊逐欄比對
  `LEGISLATIVE_MANIFEST` 對應鍵的欄位集合完全相符（可用 `grep`／人工核對
  欄位名稱清單）。
- 執行 `python scripts/build_local_election.py --write`（或該腳本既有的
  無參數執行方式）後，`docs/schema/oracles.md` 的本地選舉三個既有區塊
  內容與這次變更之前逐位元組相同（本地部分不應該因為這次改動而改變
  輸出）。
- 新增合成測試，構造一列 `人口數` 為非數字字串與一列為負值字串的立委
  摘要資料，分別餵給 `check_population_is_valid_decimal`，斷言兩者都
  拋出 `ValidationError` 且訊息可分辨是哪一種失敗；構造一列合法值
  （含字串 `"0"` 與含小數的字串）斷言不拋例外。

**範圍邊界**：只動 `scripts/oracles.py` 的算繪邏輯與
`scripts/build_legislative_election.py`。不動 `PARTY_LIST_MANIFEST`、
不動 `docs/schema/cec-legislative-election.md`、不動 `MANIFEST` 或
`LEGISLATIVE_MANIFEST` 已宣告的欄位語意內容本身。

## Risks / Trade-offs

[兩支腳本各自呼叫 `render_markdown()` 整段覆寫同一個檔案，若未來
`render_markdown()` 的輸出開始依賴呼叫端的執行期資料（不再是純函式），
「兩邊寫出結果必然相同」這個假設就會失效，可能出現互相覆寫掉對方內容
的情況] → 這個風險現在不成立（`render_markdown()` 目前確實是純函式，
只讀兩份靜態 manifest），但這是設計決定的前提，值得留一行程式註解說明
「若要讓算繪內容依賴執行期資料，必須重新設計成不會互相覆寫」，避免未來
有人在不知情的狀況下違反這個前提。

[`人口數` 驗證比照本地選舉的邏輯與訊息格式，但兩個資料集的
`人口數適用層級` 概念不完全相同（本地選舉有獨立的 `人口數適用層級`
欄，立委沒有、改用「細層級為 0 代表不適用」的慣例）——若未來立委資料
出現這個慣例被打破的情況（例如某個細層級人口數不是 0 而是空字串），
新驗證會中止建置] → 這是**刻意的**行為，不是風險：中止代表資料形狀
違反了目前已知的慣例，需要人工確認新資料的意義，不應該讓不明字串靜默
流到輸出。
