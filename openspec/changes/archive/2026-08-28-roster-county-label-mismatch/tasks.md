## 1. 修正查表

本節實作 spec Requirement `An Identity Lookup Is Keyed So That Re-Numbered Codes Cannot Collide`。

- [x] 1.1 （design 決策 3：把正規化欄位加進必要欄位宣告）把 `縣市_正規化` 加進 `REQUIRED_COLUMNS` 中 `SUMMARY_FILE` 與 `CANDIDATES_FILE` 兩份宣告。完成後：任一份長表缺該欄時 `build_site_data.py` 中止。
- [x] 1.2 （design 決策 1：查表鍵改用正規化縣市代碼，而不是把選舉種類加進鍵）把 `build_roster_data()` 裡的 `county_name` 查表鍵由 `(年度, 省市, 縣市)` 改為 `(年度, 省市, 縣市_正規化)`，並讓 `county_label()` 以候選人列的同三欄查表。完成後：1998 平地原住民的分組取得平地原住民檔的縣名，不再取得山地原住民檔的——即 Requirement `An Identity Lookup Is Keyed So That Re-Numbered Codes Cannot Collide` 的 Scenario `One raw code denotes two counties across election types`。
- [x] 1.3 （design 決策 2：同鍵兩名一律中止，不取任一個）在 `county_name` 建表處加入衝突偵測：同一個鍵出現兩個不同的 `行政區名稱` 時丟出 `SiteDataError`，訊息含該鍵與兩個名稱。完成後：後寫入不再覆蓋前者。
- [x] 1.4 在 `county_name` 建表處寫下註解，說明為何鍵必須用正規化代碼而非原始代碼（1998／2002 逐檔重編、實測 18 組鍵撞名），以及為何不改用 `(年度, 選舉種類, 省市, 縣市)`（查無由 167 增為 486）。

## 2. 測試

- [x] 2.1 在 `test_build_site_data.py` 新增測試：合成兩列彙總資料，同一個 `(年度, 省市, 縣市)` 但 `縣市_正規化` 不同、縣名不同，斷言兩個選舉種類的候選人各自取得正確縣名。
- [x] 2.2 新增測試：合成兩列彙總資料具有相同的 `(年度, 省市, 縣市_正規化)` 但 `行政區名稱` 不同，斷言丟出 `SiteDataError` 且訊息同時含該鍵與兩個名稱（不只斷言「有中止」）。
- [x] 2.3 新增測試：分別移除彙總長表與候選人長表的 `縣市_正規化` 欄，斷言兩種情形都中止。
- [x] 2.4 執行 `python -m pytest scripts/test_build_site_data.py -q`，全數通過。

## 3. 變異測試

- [x] 3.1 在 `mutate_build_site_data.py` 新增變異：把查表鍵改回 `(年度, 省市, 縣市)`，預期被 2.1 偵測。
- [x] 3.2 新增變異：把衝突偵測改為後寫入覆蓋（移除中止），預期被 2.2 偵測。
- [x] 3.3 新增變異：從 `REQUIRED_COLUMNS` 拿掉 `縣市_正規化`，預期被 2.3 偵測。
- [x] 3.4 執行 `python scripts/mutate_build_site_data.py`，確認全部變異皆被偵測、漏網為 0，且新增的三個變異各自對應到不同的測試而非同一個。

## 4. 重新產生站台並驗證

- [x] 4.1 執行 `python scripts/build_site_data.py --write` 重新產生站台常數，確認離開碼為 0（不要用管線包住，管線的離開碼是最後一個指令的）。**必須加 `--write`**：不加時建置器只做檢查與報告，離開碼一樣是 0 但一個位元組都不會寫入——以 `git status` 確認 `docs/roster.html` 確實變動，不可只看離開碼。
- [x] 4.2 以 `git diff --stat docs/` 確認只有 `docs/roster.html` 變動，其餘 HTML 位元組不變。
- [x] 4.3 從重新產生後的 `docs/roster.html` 解析 `D` 常數，比對每一個分組的縣市標題與其選舉區名的縣市前綴：矛盾數必須為 0（修正前為 28 組、123 列）。比對時必須排除鄉鎮層級的市名（臺東市、花蓮市、嘉義市、基隆市、新竹市），否則會產生 6 筆誤判。
- [x] 4.4 確認候選人列的縣市查無筆數不高於 167，且全部落在 1994 臺灣省議員與 1998／2002 山地鄉鄉長兩類既有情形。
- [x] 4.5 逐處檢視 `docs/roster.html` 的差異，確認變動只出現在縣市標籤，沒有夾帶政黨索引重排或分組順序改變。

## 5. 文件

- [x] 5.1 在 `HANDOFF.md` 記錄這個地雷：以行政區代碼為鍵的查表若不含足以區辨的欄位，逐檔重編會讓後寫入覆蓋前者且完全無聲；並記下「加選舉種類入鍵」這個看似合理但會讓查無暴增的方案。
- [x] 5.2 執行 `spectra validate roster-county-label-mismatch --strict`，離開碼為 0。
