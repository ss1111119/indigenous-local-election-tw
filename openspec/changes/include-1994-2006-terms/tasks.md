<!--
Each task description MUST state:
- the behavior or contract being delivered (what is observably true when the
  task is complete), and
- the verification target that proves completion (test, CLI invocation,
  analyzer check, manual assertion, or content review).
-->

## 1. 建立對照表與基礎建設

- [x] 1.1 建立 1998/2002 縣市代碼對照表 (County Code Crosswalk) `cec-county-code-crosswalk-1998-2002.csv`，使「以同屆「區域」檔為基準建立跨檔縣市代碼對照表」設計得以實現。完成時應能以指令或腳本載入此檔案且無語法錯誤。
- [x] 1.2 在 `data/sources.json` 中補記 1994-2006 各檔的涵蓋範圍與已知瑕疵。完成時應能通過 JSON 語法驗證且檔案內含對應屆別。
- [x] 1.3 更新 `scripts/oracles.py`，加入 Custom Election Type Codes，為 1994 省議員與直轄市合併原住民類別建立專案自訂代碼，並在長表新增可比性標記欄位 (Comparability Flags) 的資料結構。驗證方式：撰寫或修改單元測試確保新增的代碼與「新增專案自訂的選舉種類代碼以處理不連續職位」、「在長表新增可比性標記欄位 (Comparability Flags)」的資料結構被正確識別。

## 2. 解析腳本修正 (處理來源瑕疵)

- [x] 2.1 修改 `scripts/build_local_election.py`，實現 Relational Key Field Trailing Whitespace Normalization：以逐檔宣告的白名單對關聯鍵欄位（行政區代碼、`號次`、政黨代號）`.strip()`，不分 `quoted` 與否；非關聯鍵欄位（`得票率`／`人口數`／`投票率`／當選註記）原樣保留。驗證方式：執行現有 2009-2022 的測試，確保輸出 CSV 的內容逐位元組不變；另加單元測試涵蓋「關聯鍵被正規化」與「非關聯鍵未被改動」兩個方向，並配變異測試。
- [x] 2.2 在建置腳本中實作 Population String Preservation and Level Restriction（人口數欄位加入可用層級限制並原樣保留），確保字串不轉型且限制在縣市層級以上。驗證方式：執行建置腳本並斷言鄉鎮以下層級的人口數欄位帶有特定的可用層級限制標記或預設值。
- [x] 2.3 在建置腳本中實作 Authoritative Elected Status Derivation：`elcand` 的當選註記與由它推導的 `當選` 原樣保留，另由 `elctks` 推導 `elected_authoritative` 與 `elected_authoritative_basis`（以候選人非空白代碼欄約束、取最高層級、註記須一致，否則中止；不設 elprof 回退）。第 4／7 項驗證維持檢查來源，權威值另立 4c／4d 補償檢查。驗證方式：寫一個單元測試提供模擬的 2005 資料，斷言 `elected_authoritative` 欄位產出正確結果且原欄位不變；另加推導失敗必須中止的測試，並配變異測試。

## 3. 資料整合與主序列輸出

- [x] 3.1 修改建置腳本，載入 `cec-county-code-crosswalk-1998-2002.csv` 並在處理舊屆資料時進行代碼轉換。若代碼對應失敗需 abort build。驗證方式：執行建置腳本處理 1998/2002 資料，確認能成功對應且遇到未知縣市會拋出例外。
- [x] 3.2 實作 T2 and T3 Main Sequence Inclusion，將 1998、2002、2005 的 T2/T3 資料納入處理流程，並寫入三張 CSV 長表。驗證方式：執行建置腳本，透過查閱輸出的 CSV，確認包含 1998、2002、2005 的對應記錄且 `is_main_sequence` 標為 true。
- [x] 3.3 確保 1994 省議員及直轄市合併類別正確寫入長表，且依照「新增專案自訂的選舉種類代碼以處理不連續職位」的決策給予新代碼與降級標記（`is_main_sequence` = false）。驗證方式：執行建置腳本，查閱輸出 CSV 確認上述記錄的 `is_main_sequence` 皆為 false。
- [x] 3.4 執行全端建置腳本 `python scripts/build_local_election.py` 並跑完全部 `pytest` 測試（包含針對舊屆地雷的變異測試）。驗證方式：所有測試通過，且 `data/processed/` 下的三張長表 (`cec-local-election-candidates-long.csv` 等) 及 `validation-report.json` 成功重新產生並包含所有舊屆與新標記欄位。
