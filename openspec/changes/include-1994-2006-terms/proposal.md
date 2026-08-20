## Why

本專案目前涵蓋 2009-2010／2014／2018／2022 四屆。中選會壓縮檔內另有 1994–2006 的原住民地方選舉資料，2026-08-19 已逐檔清點完畢（17 個檔：13 個原住民檔＋4 個同屆「區域」對照檔；地方民代的 leaf 資料夾共 21 個，另 4 個為直轄市議員區域腿。先前記載的「19 個檔」為誤記），確認縣市層級的山原／平原分項自 1998 年起連續可用，且結構與現行 T2/T3 的 city 腿同構。納入後議員層級的序列可回溯 11 年、增加三個時間點——本專案已多次證明「兩個點畫不出趨勢」，加長序列直接提升既有圖表的解讀可信度。

清點同時發現四個會**靜默產生錯誤數字**的來源陷阱。這些陷阱不會讓建置失敗，只會讓輸出看起來合理但錯誤，因此必須與納入工作一起處理，不能事後補。

## What Changes

- 建置腳本新增 1998／2002／2005 三屆的縣市山原／平原，延長 T2（平原）與 T3（山原）的 `city` 腿。三屆席次分別為 T2 23／26／27、T3 30／30／30。
- 建置腳本新增 1994 台灣省議員（山原 2 席、平原 2 席分兩選舉區）與 1994／1998／2002／2006 直轄市議員合併「原住民」類別（每屆 2 席），寫入資料層並標記為不可與主序列對齊。
- 三張長表新增可比性標記欄位，使下游可在不讀 README 的情況下判斷某一列能否進入跨屆比較。
- **BREAKING**：`data/processed/` 下三張長表的欄位集合改變（新增可比性標記欄），且列數大幅增加。任何依欄位位置而非欄位名讀取的下游程式會失效。
- 新增 1998／2002 的逐檔縣市代碼對照表，作為可版本控管的資料檔而非硬編碼字典。
- 建置驗證新增針對舊屆的檢查項，並為 2005 的來源矛盾新增具名異常條目與補償性檢查。
- `data/sources.json` 補記 1994–2006 各檔的涵蓋範圍與已知瑕疵。



## Capabilities

### New Capabilities

- `historical-terms-1994-2006`: 1994–2006 屆別的納入範圍、各屆各類別對應到哪一個選舉種類代碼、以及無法對齊主序列者（1994 省議員、直轄市合併類別）的降級標記規則。
- `legacy-source-quirks`: 1994–2006 來源檔特有瑕疵的偵測與處置——代碼欄尾隨空白、縣市代碼逐檔重編、人口欄的可用層級限制、2005 當選註記的跨檔矛盾。

### Modified Capabilities

(none)

## Impact

- Affected specs: `historical-terms-1994-2006`、`legacy-source-quirks`（皆為新增）
- Affected code:
  - Modified:
    - `scripts/build_local_election.py`
    - `scripts/oracles.py`
    - `scripts/test_build_local_election.py`
    - `data/sources.json`
    - `README.md`
  - New:
    - `data/processed/cec-county-code-crosswalk-1998-2002.csv`
  - Removed: （無）
- 重新產生（內容改變，非新增檔案）：
  - `data/processed/cec-local-election-candidates-long.csv`
  - `data/processed/cec-local-election-summary-long.csv.gz`
  - `data/processed/cec-local-election-votes-long.csv.gz`
  - `data/processed/validation-report.json`
- 下游影響：`docs/index.html` 將與資料集不一致（見 Non-Goals），需另開 change 補齊。
