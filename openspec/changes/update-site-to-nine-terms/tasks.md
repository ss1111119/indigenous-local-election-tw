<!--
Each task description MUST state:
- the behavior or contract being delivered (what is observably true when the
  task is complete), and
- the verification target that proves completion (test, CLI invocation,
  analyzer check, manual assertion, or content review).
-->

## 1. 產生器骨架與重現既有四屆

- [ ] 1.1 建立 `scripts/build_site_data.py`，實現 Site Data Is Generated From The Long Tables 的讀取端：能讀入 `data/processed/` 的三張長表並取得九屆資料，且在缺少所需欄位（如 `elected_authoritative`）時中止。此為設計決策「腳本產生，但仍內嵌為常數而非改抓外部檔」的第一步。驗證方式：以缺欄的暫時副本執行，斷言拋出例外且未寫出任何檔案。
- [ ] 1.2 實作 `index.html` 的 `DATA` 常數計算，落實 Seats Come From The Authoritative Elected Field 與設計決策「席次一律採 `elected_authoritative`，名錄的當選標記亦同」：逐（選舉種類, 屆別）算出 `electors`、`votes`、`turnout`、`seats`、`cands`、`districts`、`party`、`femaleSeats`、`femaleCands`、`quota`、`displaced`、`incCands`、`incWon`、`uncontestedDist`、`uncontestedSeats`、`perSeat`，席次相關一律取自 `elected_authoritative`。驗證方式：以 `--only-existing-terms` 模式輸出 2009-2010／2014／2018／2022 四屆，與 `docs/index.html` 現有常數逐鍵比對，列出所有差異。
- [ ] 1.3 落實 Existing Terms Must Be Reproduced Before Extending 與設計決策「先重現四屆、逐項比對，差異必須具名」：逐項查明 1.2 列出的每一個差異，判定是站台舊值錯還是產生器算錯，修正產生器並把「站台舊值錯」的項目具名記錄於腳本內的常數。驗證方式：`--only-existing-terms --check` 模式在差異全部具名後回傳成功；未具名的差異必須中止。
- [ ] 1.4 實作 `roster.html` 的 `D` 常數計算（`parties`、`years`、`rows`），同樣落實 Seats Come From The Authoritative Elected Field：當選標記取自 `elected_authoritative`，婦女保障（`!`）與被排擠（`-`）仍取自 `當選註記`。驗證方式：`--only-existing-terms` 模式與現有常數逐鍵比對，差異依 1.3 的同一規則處理。

## 2. 就地替換與擴充至九屆

- [ ] 2.1 實作 HTML 的就地替換，完成 Site Data Is Generated From The Long Tables 的寫入端與設計決策「腳本產生，但仍內嵌為常數而非改抓外部檔」：以固定標記行界定 `DATA` 與 `D` 所在的那一行，只替換該行，其餘位元組不變；找不到標記行即中止。驗證方式：對未變更資料的情況執行，斷言兩個 HTML 檔逐位元組不變；再以移除標記行的暫時副本執行，斷言中止。
- [ ] 2.2 產生九屆的常數並寫入兩個 HTML。驗證方式：執行後以指令讀出兩個常數，斷言 `years` 含 1994、1998、2002、2005、2006、2009-2010、2014、2018、2022 九屆。

## 3. 站台呈現的兩項約束

- [ ] 3.1 修改 `docs/index.html` 的折線繪製邏輯，實現 Cross-Term Lines Are Restricted To The Main Sequence 與設計決策「自訂選舉種類代碼不進跨屆折線，獨立區塊呈現」的過濾側：只取 `is_main_sequence` 為 true 的選舉種類，`DATA` 的每個選舉種類新增 `mainSequence` 布林欄位供前端判斷。驗證方式：以指令檢查產生的常數中 `T-PRV2`、`T-PRV3`、`T-COMBO` 的 `mainSequence` 為 false，且在瀏覽器開啟後折線圖不含這三種。
- [ ] 3.2 在 `docs/index.html` 新增獨立區塊呈現三個自訂選舉種類代碼，完成 Cross-Term Lines Are Restricted To The Main Sequence 的呈現側：明文標示「臺灣省議會 1998 年精省後廢除」與「直轄市合併類別未分平地／山地」，以及不可與 T2／T3 相加的理由。驗證方式：以瀏覽器開啟確認該區塊存在且文字到位，並確認它不在任何折線圖內。
- [ ] 3.3 實現 Absent Election Types Are Marked Rather Than Zero-Filled 與設計決策「缺屆維持以 `×` 標示」：確認缺屆的選舉種類以 `×` 標示而非 `0`。驗證方式：以瀏覽器開啟，檢查 D2 在 2009 以前、T2／T3 在 1994 與 2006 皆顯示 `×`。

## 4. 測試與文件

- [ ] 4.1 建立 `scripts/test_build_site_data.py`，涵蓋「席次取自權威值而非 `當選`」與「主序列過濾」兩項，各以合成資料撰寫。驗證方式：`pytest` 通過；另為這兩項各寫一個變異測試，確認改壞會失敗、還原會通過。
- [ ] 4.2 更新 `README.md` 中站台的涵蓋範圍敘述（目前寫「四屆」），並移除「站台前端尚未跟上」那條待辦。驗證方式：以指令搜尋 README 中的「四屆」，確認殘留者皆為刻意保留的歷史敘述。
