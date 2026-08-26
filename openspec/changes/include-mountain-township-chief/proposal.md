## Why

山地鄉鄉長是**法定原住民限定職位**（地方制度法第 57 條第 2 項：「山地鄉鄉長以山地原住民為限」），與本專案已涵蓋的 D2 直轄市原住民區長性質相同；同法第 83 條之 2 更確立兩者的承繼關係——D2 那六個單位正是由山地鄉改制而來。但本專案目前未涵蓋山地鄉鄉長，因此站台呈現的是一條**沒有前身的三點序列**（D2 僅 2014／2018／2022），非直轄市轄下的山地鄉則從未涵蓋。

2026-08-26 完成的來源可用性清點（`docs/schema/山地鄉鄉長資料清點.md`）確認資料存在且可對應：1998／2002／2005 三屆 30 個山地鄉全數命中，2009 為 25 個（五鄉所屬縣正併入直轄市而未參選），2014／2018／2022 為 24 個（六鄉改制為直轄市原住民區、改列 D2）。

⚠️ **本 change 有前置 change**：`census-elctks-elprof-township-chief`。2026-08-26 的清點只開過 `elbase` 與 `elcand`，證實「候選人與單位可對應」；席次、選舉人數、投票數所在的 `elctks` 與 `elprof` 七屆皆未檢查。那筆驗證債由前置 change 補完，本 change 的逐屆預期命中數與可納入屆別清單**以前置 change 的「可納入性結論」為準**，不得沿用本文其他段落引述的既有數字。

依 `election-period-publication` 的兩段式測試，本 change 產出的數字（席次、候選人數、選舉人數、投票數、投票率）全部屬 **frozen historical data** 而非 interpretive indicator——它們可由官方計數加總取得、且不帶方向。惟本 change **完全不修改 `docs/`**，因此該能力所管的「published page」一條都不觸及。

## What Changes

- 建立**以代碼為鍵**的山地鄉對照表 `data/reference/mountain-township-codes.csv`，逐屆記錄（屆別, 省市, 縣市, 鄉鎮市區）到山地鄉的對應。名稱比對只命中 24／30，故建置期一律用代碼、不用名稱
- 新增自訂選舉種類代碼 `D1-MT`（山地鄉鄉長選舉），由官方 D1 鄉(鎮、市)長選舉依上述對照表篩出山地鄉子集，登記於 `scripts/oracles.py` 的 `CUSTOM_ELECTION_TYPES` 並納入 `INDIGENOUS_TYPES`
- 將 1998／2002／2005／2009-2010／2014／2018／2022 七屆的 `D1-MT` 納入三份地方公職長表（summary／votes／candidates）
- 在建置期處理清點已具名的四個陷阱：欄位值前綴撇號（依 `legacy-source-quirks` 既有規範處置）、台↔臺異體字、三民鄉即那瑪夏、省市／縣市代碼跨屆重編
- 新增自動化檢查，阻止 `D1-MT` 與 `D2` 被接成同一條序列
- 補上對應的測試與變異測試

## Non-Goals

- **不做 `elctks`／`elprof` 的清點**：那是前置 change `census-elctks-elprof-township-chief` 的範圍
- **不修改 `docs/`**：不動任何站台頁面、不加圖表、不進 `scripts/build_site_data.py` 的呈現層。站台呈現另案處理
- **不納入 D1 全體**：只納入山地鄉子集。全體鄉鎮市長含大量非原住民限定單位，與本專案母體不同
- **不納入平地原住民鄉的鄉長**：平地鄉鄉長無同等法定身分限制
- **不納入補選資料夾**：十個鄉鎮市層級補選中只有蘭嶼鄉屬山地鄉，且補選的屆別語意與正規選舉不同
- **不把 `D1-MT` 與 `D2` 合併為單一序列**：2014 年的改制會製造假跳點，與 README 已記錄的 R2 情況同類
- **不算任何比值或代表性指標**：不計算跨母體相除的數字
- **不下「站台是否呈現」的結論**：那涉及 `election-period-publication` 的擴張判定，另案

## Capabilities

### New Capabilities

- `mountain-township-chief-elections`: 山地鄉鄉長選舉資料的納入規範——以代碼（非名稱）識別山地鄉、`D1-MT` 為 D1 的篩選子集而非獨立來源、以及 `D1-MT` 與 `D2` 不得接為同一序列的界線

### Modified Capabilities

（無）

⚠️ 前綴撇號**不需要新增或修改任何規範**。既有的來源陷阱能力（spec 目錄 legacy-source-quirks）已有一條 "A Change In Key Formatting Aborts Rather Than Silently Failing To Match"，治理此陷阱且比本 change 原先設想的更嚴格——它要求格式變動時中止建置，而非僅剝除。清點文件稱其為「新發現」指的是在鄉鎮市長那批來源檔上新觀察到，不是規範缺口。本 change 新增的自訂選舉種類依循該既有規範，不修改它。

## Impact

- Affected specs: `mountain-township-chief-elections`（新）
- Affected code:
  - New: `data/reference/mountain-township-codes.csv`
  - Modified: `scripts/build_local_election.py`, `scripts/oracles.py`, `scripts/test_build_local_election.py`, `scripts/mutate_build_local_election.py`, `data/sources.json`, `docs/schema/cec-local-election.md`, `docs/schema/山地鄉鄉長資料清點.md`, `README.md`
  - Removed: (none)
- Affected data: `data/processed/cec-local-election-summary-long.csv.gz`, `data/processed/cec-local-election-votes-long.csv.gz`, `data/processed/cec-local-election-candidates-long.csv` 三份長表將新增 `D1-MT` 的列；既有六種選舉種類的列不得改變
