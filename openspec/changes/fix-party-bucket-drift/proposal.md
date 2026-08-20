## Why

站台把政黨分成四桶時用**政黨名稱字串**比對，而無黨籍在來源裡有兩套完全不重疊的編碼：舊屆是代號 `99`／名稱「無」，新屆是代號 `999`／名稱「無黨籍及未經政黨推薦」。結果是站台上 1994、1998、2002、2005、2006 五個屆別的「無黨籍」系列**全部顯示為 0**（1998 T2 的常數即為 `[0,0]`），151 位候選人、25 席被靜靜歸進灰色的「其他」桶。這是九屆擴充帶進來的錯，既有的 `--check` 抓不到它，因為那五個舊屆沒有可比對的基準。

同時，「無黨籍」目前使用橘色，而橘色在臺灣政治語境中是親民黨的顏色；親民黨確實出現在這份資料裡（128 位候選人、40 席、橫跨七屆），且是「其他」桶中最大的一個。讀者可能把橘色長條誤讀為親民黨。

## What Changes

- 分桶改用**具名的政黨身分對照表**，鍵為 `(政黨代號, 政黨名稱)` 配對，明確把 `(99, 無)` 與 `(999, 無黨籍及未經政黨推薦)` 映射到同一桶。
- `政黨代號` 加入 `REQUIRED_COLUMNS` 的 candidates 清單（目前程式未讀取此欄，故亦未宣告）。
- 新增「無黨籍逐屆非零」的具名斷言與對應的變異測試。
- **BREAKING（對站台讀者）**：1994、1998、2002、2005、2006 五屆的「無黨籍」與「其他」兩個系列數字都會改變。這是修正，不是資料變動。
- 無黨籍改用中性深色，橘色不再指派給它；並在設計中明訂「顏色不是唯一編碼」。
- 補上 `site-data-generation` 與 `legacy-source-quirks` 兩份主 spec 的 Purpose 段落（目前是歸檔工具留下的 TBD 佔位文字）。

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `site-data-generation`: 新增政黨分桶的身分對照要求，以及「顏色不是唯一編碼」的呈現要求
- `legacy-source-quirks`: 新增跨屆政黨編碼漂移的具名處置要求

## Impact

- Affected specs: `site-data-generation`、`legacy-source-quirks`
- Affected code:
  - Modified:
    - `scripts/build_site_data.py`
    - `scripts/test_build_site_data.py`
    - `scripts/mutate_build_site_data.py`
    - `docs/index.html`
    - `docs/roster.html`
    - `openspec/specs/site-data-generation/spec.md`
    - `openspec/specs/legacy-source-quirks/spec.md`
    - `README.md`
  - New: (none)
  - Removed: (none)
