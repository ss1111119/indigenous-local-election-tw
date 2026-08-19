<!--
Each task description MUST state:
- the behavior or contract being delivered (what is observably true when the
  task is complete), and
- the verification target that proves completion (test, CLI invocation,
  analyzer check, manual assertion, or content review).
-->

## 1. 建立對照表與基礎建設

- [ ] 1.1 建立 1998/2002 縣市代碼對照表 (County Code Crosswalk) `cec-county-code-crosswalk-1998-2002.csv`，使「以同屆「區域」檔為基準建立跨檔縣市代碼對照表」設計得以實現。完成時應能以指令或腳本載入此檔案且無語法錯誤。
- [ ] 1.2 在 `data/sources.json` 中補記 1994-2006 各檔的涵蓋範圍與已知瑕疵。完成時應能通過 JSON 語法驗證且檔案內含對應屆別。
- [ ] 1.3 更新 `scripts/oracles.py`，加入 Custom Election Type Codes，為 1994 省議員與直轄市合併原住民類別建立專案自訂代碼，並在長表新增可比性標記欄位 (Comparability Flags) 的資料結構。驗證方式：撰寫或修改單元測試確保新增的代碼與「新增專案自訂的選舉種類代碼以處理不連續職位」、「在長表新增可比性標記欄位 (Comparability Flags)」的資料結構被正確識別。

## 2. 解析腳本修正 (處理來源瑕疵)

- [ ] 2.1 修改 `scripts/build_local_election.py`，實現 Administrative Code Trailing Whitespace Normalization，針對 CSV 讀取時無引號的欄位進行 `.strip()`。驗證方式：執行現有 2009-2022 的測試，確保輸出 CSV 的內容逐位元組不變（除預期新增的欄位外）。
- [ ] 2.2 在建置腳本中實作 Population String Preservation and Level Restriction（人口數欄位加入可用層級限制並原樣保留），確保字串不轉型且限制在縣市層級以上。驗證方式：執行建置腳本並斷言鄉鎮以下層級的人口數欄位帶有特定的可用層級限制標記或預設值。
- [ ] 2.3 在建置腳本中實作 Authoritative Elected Status Derivation for 2005（由 elctks 候選人星號推導 2005 年當選權威值），將 `elcand` 的當選註記原樣保留，由 `elctks` 候選人星號或 `elprof` 當選人數推導出 `elected_authoritative` 布林值。驗證方式：寫一個單元測試提供模擬的 2005 資料，斷言 `elected_authoritative` 欄位產出正確結果且原欄位不變。

## 3. 資料整合與主序列輸出

- [ ] 3.1 修改建置腳本，載入 `cec-county-code-crosswalk-1998-2002.csv` 並在處理舊屆資料時進行代碼轉換。若代碼對應失敗需 abort build。驗證方式：執行建置腳本處理 1998/2002 資料，確認能成功對應且遇到未知縣市會拋出例外。
- [ ] 3.2 實作 T2 and T3 Main Sequence Inclusion，將 1998、2002、2005 的 T2/T3 資料納入處理流程，並寫入三張 CSV 長表。驗證方式：執行建置腳本，透過查閱輸出的 CSV，確認包含 1998、2002、2005 的對應記錄且 `is_main_sequence` 標為 true。
- [ ] 3.3 確保 1994 省議員及直轄市合併類別正確寫入長表，且依照「新增專案自訂的選舉種類代碼以處理不連續職位」的決策給予新代碼與降級標記（`is_main_sequence` = false）。驗證方式：執行建置腳本，查閱輸出 CSV 確認上述記錄的 `is_main_sequence` 皆為 false。
- [ ] 3.4 執行全端建置腳本 `python scripts/build_local_election.py` 並跑完全部 `pytest` 測試（包含針對舊屆地雷的變異測試）。驗證方式：所有測試通過，且 `data/processed/` 下的三張長表 (`cec-local-election-candidates-long.csv` 等) 及 `validation-report.json` 成功重新產生並包含所有舊屆與新標記欄位。
