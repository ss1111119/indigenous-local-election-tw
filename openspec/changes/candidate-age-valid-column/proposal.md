## Why

候選人長表的 `年齡` 欄在 1994、1998、2002、2005、2006 五屆整批是 `99`，那是來源格式文件明列的無資料值（`年齡 Num(3) (部分選舉未必有資料，可能 0 或 99)`）。本專案不覆寫來源值，所以長表維持 `99`。

站台已經在呈現端處理了（前一個變更 `age-99-is-unrecorded`），但**直接使用長表的第三方拿不到這層保護**。對 `年齡` 欄跑 `AVG()` 會把 483 個 `99` 當成年齡算進去——實測九屆合計的平均由 **50.80**（n=7,335，排除未記載）被拉高到 **53.78**（n=7,818），差 **2.98 歲**，而且不會有任何錯誤訊息。

外部覆核明確指出這一點：把原始髒值留給下游、只靠說明文件擋，等於期待每個使用者都先讀文件。

## Root Cause

長表目前只有原始的 `年齡` 欄，沒有可直接使用的衍生欄位。本專案對其他同類情況已有既定做法——`縣市_正規化`、`鄉鎮市區_正規化`、`elected_authoritative` 都是「原欄位保留、另加一個可用的衍生欄位」——但 `年齡` 沒有跟上。

## Proposed Solution

把候選人長表的 `年齡` 欄**對調**：`年齡` 改存乾淨值，來源原值退居 `年齡_原始`（緊接其後）。`年齡` 的內容為：

- 該屆該列的年齡**有記載**時，放年齡值（與 `年齡` 相同）。
- **未記載**時留空字串。判準與站台端一致：`0` 在任何屆別都是未記載（不可能是真實年齡）；`99` 只在具名的五個屆別是未記載（它落在合法年齡值域內）。

來源原值**一列不差**地保留在 `年齡_原始`，含 `99`。

**不讀文件的分析者直覺寫 `AVG(年齡)` 就會拿到正確答案**——這才是真正封閉陷阱，而不是另開一條安全通道。要來源原值的人用 `年齡_原始`。

站台的產生器直接讀取 `年齡`（已是乾淨值），不再自行重算——同一個判準只留一個實作。

## Non-Goals

- **不丟失任何來源值。** 原值完整保留在 `年齡_原始`。
- **不比照處理 `當選`／`elected_authoritative`。** 那一組的情況更嚴重（用錯欄位少算 19 席），是否比照對調另開變更處理。
- **不用布林旗標。** 那需要分析者先知道有那一欄才會過濾，保護力較弱。
- **不為其他欄位新增衍生欄位**。已逐欄掃過候選人長表 26 個欄位（含以眾數佔比為判準的第二輪掃描），只有 `年齡` 有此問題；`鄉鎮市區` 的 `000` 已由既有的 `is_blank` 正確處理。
- 不改動 summary 與 votes 兩張長表。

## Success Criteria

- 候選人長表總欄位數由 28 變 29：`年齡` 存乾淨值、`年齡_原始` 緊接其後存來源原值。
- 五個舊屆的 `年齡` 全部為空字串；2009-2010 以後四屆的 `年齡` 與 `年齡_原始` 逐列相同。
- `年齡_原始` 逐列等於本變更前的 `年齡` 欄。
- summary 與 votes 兩張長表的 SHA-256 與重建前相同。
- 站台的 `--check` 通過，兩個 HTML 的常數不因此改變。
- `年齡_原始` 在 oracle 清單中有具名條目，且 `年齡` 的條目改為 `project` 來源，否則 `check_manifest` 不通過。

## Impact

- Affected specs: `legacy-source-quirks`（ADDED 三條、**MODIFIED 一條**）

  ⚠️ 前一個變更 `age-99-is-unrecorded` 歸檔的 `Sentinel Values Are Not Presented As Measurements` 明文寫著「值 SHALL 在長表中原樣保留；替換只發生在呈現端」。本變更把替換移進長表，該條**已不成立**，因此以 MODIFIED 改寫而非只是新增——否則主 spec 會同時存在兩條互相矛盾的要求。
- Affected code:
  - Modified:
    - `scripts/build_local_election.py`
    - `scripts/oracles.py`
    - `scripts/test_build_local_election.py`
    - `scripts/build_site_data.py`
    - `scripts/test_build_site_data.py`
    - `scripts/mutate_build_site_data.py`
    - `data/processed/cec-local-election-candidates-long.csv`
    - `docs/schema/cec-local-election.md`
    - `README.md`
  - New: (none)
  - Removed: (none)
