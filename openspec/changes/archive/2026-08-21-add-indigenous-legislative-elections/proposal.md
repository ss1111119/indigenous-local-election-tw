## Why

本專案宣稱涵蓋「原住民族選舉」，實際只有地方公職。原始壓縮檔裡另有**九屆山地／平地原住民立法委員**（1995、1998、2001、2004、2008、2012、2016、2020、2024），一直沒有處理。

這個缺口不只是「少了一批資料」，它讓既有結論被誤讀。本專案的地方議員資料顯示民進黨在原住民選區得票 2–5%，容易被讀成「原住民不投民進黨」。但同一群選民在 2020 年山地立委投給民進黨的比例是 **17.81%**、平地立委陳瑩 **21.2%**。差異來自地方議員選舉的政黨屬性本來就弱（無黨籍得票率 2022 年達 46%）加上民進黨在地方層級幾乎不提名，不是選民傾向。

立委資料在方法上也優於地方議員：**選民就是全國原住民本身**，不需要用山地鄉當地理代理，沒有生態推論謬誤的問題。

## What Changes

- 新增九屆山地原住民立委（T3）與平地原住民立委（T2）共 18 個來源檔的解析
- 產出**獨立的三張長表**：`data/processed/cec-legislative-election-summary-long.csv.gz`、`cec-legislative-election-candidates-long.csv`、`cec-legislative-election-votes-long.csv.gz`
- 既有的 `cec-local-election-*` 三張長表**完全不動**，不新增欄位、不新增 office_type
- 記錄三項具名來源瑕疵並各配補償性檢查
- 產出獨立的驗證報告，並更新資料集說明文件與 `data/sources.json`

**不是 BREAKING**：既有長表的欄位、列數、SHA-256 皆不變。

## Non-Goals

- **不納入對照組**。區域立委與不分區政黨票都不做。區域立委的 `elctks` 體積龐大（73 個選區），會顯著拉長建置時間；不分區政黨票只有 2008 之後才有，涵蓋範圍不齊。兩者要做應各自另開變更。
- **不併入既有長表、不改既有檔名**。立委沒有「選舉區」「鄉鎮市區」這些地方公職的層級語意，併入會在既有 28 欄裡塞進大量空值；改名 `cec-election-*` 則是破壞性更名，會讓所有下游路徑失效，且與剛完成的 `elected-column-swap` 疊成連續兩次破壞。
- **不做站台呈現**。本變更只到長表與驗證報告為止，站台圖表另議。
- **不納入 1996 國大代表（山原／平原）**。那是任務型國代之前的舊制，與立委不同體系。
- **不建立跨資料集的 join 鍵或對照表**。地方與全國要比較時由使用者自行以年度與政黨欄位串接。

## Capabilities

### New Capabilities

- `indigenous-legislative-elections`: 九屆山地／平地原住民立委的涵蓋範圍、輸出結構、席次序列，以及全國單一選區與地方公職在層級語意上的差異。

### Modified Capabilities

- `legacy-source-quirks`: 既有的來源瑕疵紀律以地方公職檔為對象，新增三項立委檔特有的瑕疵：2012 鍵欄前置單引號、2016 檔名後綴與 `old/` 重複目錄、以及九屆之間應選名額不固定。

## Impact

- Affected specs: `indigenous-legislative-elections`（新增）、`legacy-source-quirks`（修改）
- Affected code:
  - New:
    - `scripts/build_legislative_election.py`
    - `scripts/test_build_legislative_election.py`
    - `scripts/mutate_build_legislative_election.py`
    - `data/processed/cec-legislative-election-summary-long.csv.gz`
    - `data/processed/cec-legislative-election-candidates-long.csv`
    - `data/processed/cec-legislative-election-votes-long.csv.gz`
    - `data/processed/legislative-validation-report.json`
    - `data/processed/cec-legislative-county-crosswalk.csv`
    - `docs/schema/cec-legislative-election.md`
  - Modified:
    - `scripts/oracles.py`
    - `data/sources.json`
    - `README.md`
    - `HANDOFF.md`
  - Removed: 無
