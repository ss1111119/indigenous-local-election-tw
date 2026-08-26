## 二、建立代碼對照表

- [ ] 2.1 （實作 spec requirement「A mountain indigenous township is identified by administrative code, never by name」；design 決策 2：以代碼對照表識別山地鄉，名稱只用於建表時的人工核對）撰寫核對腳本，對七屆各自的 `elbase` 逐一確認 30 個山地鄉（2009 為 25、2014 起為 24）的（省市, 縣市, 鄉鎮市區）代碼三元組，並輸出該屆該代碼在來源中的實際名稱。腳本須處理前綴撇號，且不得以名稱比對決定命中——名稱僅作為人工核對的佐證輸出。
- [ ] 2.2 （實作 spec requirement「The code mapping is recorded per term, not as a single snapshot」；design 決策 3：對照表逐屆記錄，不用單一快照）依 2.1 的輸出建立 `data/reference/mountain-township-codes.csv`，欄位為 `屆別, 省市, 縣市, 鄉鎮市區, 山地鄉名, 來源屆名稱, 備註`，共 187 列（30／30／30／25／24／24／24）。`屆別` 使用長表既有字串（`2009-2010` 而非 `2009`）。六個名稱變體（霧台／霧臺、烏來、和平、桃源、茂林、三民即那瑪夏）於 `備註` 欄具名。
- [ ] 2.3 在 `data/sources.json` 為 `mountain-township-codes.csv` 補上來源登記，說明其為本專案由 `cip-indigenous-areas` 名單與 `cec-votedata` 交叉核對而得的衍生對照表，並記錄「91 年公告後是否有修正未查證」這項限制。

## 三、建置腳本與 oracle

- [ ] 3.1 （實作 spec requirement「The mountain township chief type is a subset of an official type, and is marked as project-defined」；design 決策 1：`D1-MT` 為自訂代碼，而非官方 D1）在 `scripts/oracles.py` 的 `CUSTOM_ELECTION_TYPES` 新增 `D1-MT`（值為 `山地鄉鄉長選舉`），並確認 `ADMIN_CODE_SYSTEMS`、`ELECTION_TYPE_GRANULARITY`、`office_type()` 等既有 oracle 函式皆已涵蓋此代碼。完成判準：以 `D1-MT` 呼叫每個 oracle 函式皆不拋 `OracleError`。
- [ ] 3.2 在 `scripts/build_local_election.py` 新增 `load_mountain_township_codes()`，讀取對照表並回傳 `dict[(屆別, 省市, 縣市, 鄉鎮市區), str]`。對照表缺屆或某屆零列時中止並具名該屆。
- [ ] 3.3 在 `YEARS` 各屆的 `parts` 新增 `D1-MT` 項，指向該屆 D1 資料夾：2022 為 `D1`、2014／2018 為中文子資料夾名、2009-2010 為 `鄉鎮市長` 子資料夾、1998／2002／2005 為無子目錄的根。資料夾名須以實際開啟壓縮檔確認，不得由既有屆別的命名慣例推導。
- [ ] 3.4 在 `process_one()` 的路徑上加入山地鄉篩選：`D1-MT` 讀取該屆 D1 來源後，只保留代碼三元組落在對照表內的單位。篩選須在行政層級判定之後、跨檔比對之前。
- [ ] 3.5 （實作 spec requirement「Selection is verified by a per-term count that fails when selection silently returns nothing」；design 決策 4：撇號剝除在讀取層，且必須可被驗證）新增 `check_mountain_township_hit_count()`，斷言每屆選中的山地鄉單位數等於前置 change census-elctks-elprof-township-chief 的「可納入性結論」一節所定的逐屆預期值，不符時中止並同時具名屆別、預期值與實際值。
- [ ] 3.6 （實作 spec requirement「The mountain township chief series is not joined to the indigenous district chief series」；design 決策 5：`D1-MT` 與 `D2` 的不可接續由檢查強制，不靠文件）新增 `check_no_d1mt_d2_merge()`，斷言 `D1-MT` 與 `D2` 不會落入同一條主序列（`is_main_sequence`），違反時中止並具名兩個代碼。
- [ ] 3.7 執行 `python scripts/build_local_election.py` 重新產生三份長表，確認 exit code 為 0（不得以管線接 `tail` 等指令，否則回報的是最後一個指令的 rc）。

## 四、驗證

- [ ] 4.1 驗證既有六種官方代碼與三種自訂代碼的列未被本 change 改動：從新舊三份長表各自篩掉 `D1-MT` 的列後計算 SHA-256，比對兩者相同。不相同時具名差異的選舉種類與屆別。
- [ ] 4.2 在 `scripts/test_build_local_election.py` 新增測試，涵蓋：對照表缺屆、某屆命中數少一個、`D1-MT` 與 `D2` 被接為同一序列、前綴撇號未剝除導致零命中。每項須為合成髒資料輸入，且須在該項防護被移除時失敗。
- [ ] 4.3 在 `scripts/mutate_build_local_election.py` 為 4.2 的每項檢查新增對應變異，並確認新測試已加入該腳本的 `SEL` 篩選器（HANDOFF 地雷 1j：未加入的測試變異測試看不到）。
- [ ] 4.4 執行 `python scripts/mutate_build_local_election.py`，確認全部變異被偵測、基準對照通過、無測試被跳過。任一變異未被偵測時，補測試而非調降判準。

## 五、文件

- [ ] 5.1 更新 `docs/schema/cec-local-election.md`：新增 `D1-MT` 的欄位說明、七屆涵蓋範圍、以及「`D1-MT` 與 `D2` 不可接為同一序列」的具名說明（含 2009 與 2014 兩種缺額成因的差異）。
- [ ] 5.2 更新 `README.md`：涵蓋範圍表與「尚未解決」第 3 點改記為已納入資料層，並明文記載「站台尚未呈現」及其理由。確認未新增任何比值或代表性指標。
- [ ] 5.3 執行 `git status` 確認 `docs/` 下除 `docs/schema/` 的兩份文件外無任何修改，`docs/*.html` 與 `docs/en/` 皆未變動。
