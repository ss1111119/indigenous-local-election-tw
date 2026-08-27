## 二、建立代碼對照表

- [x] 2.1 （實作 spec requirement「A mountain indigenous township is identified by administrative code, never by name」；design 決策 2：以代碼對照表識別山地鄉，名稱只用於建表時的人工核對）撰寫 `scripts/build_mountain_township_codes.py`（比照 `scripts/build_town_crosswalk.py` 的體例），對七屆各自的 `elbase` 逐一確認 30 個山地鄉（2009 為 25、2014 起為 24）的（省市, 縣市, 鄉鎮市區）代碼三元組，並輸出該屆該代碼在來源中的實際名稱。腳本須處理前綴撇號，且不得以名稱比對決定命中——名稱僅作為人工核對的佐證輸出。
- [x] 2.2 （實作 spec requirement「The code mapping is recorded per term, not as a single snapshot」；design 決策 3：對照表逐屆記錄，不用單一快照）依 2.1 的輸出建立 `data/reference/mountain-township-codes.csv`，欄位為 `屆別, 省市, 縣市, 鄉鎮市區, 山地鄉名, 來源屆名稱, 備註`，共 187 列（30／30／30／25／24／24／24）。`屆別` 使用長表既有字串（`2009-2010` 而非 `2009`）。六個名稱變體（霧台／霧臺、烏來、和平、桃源、茂林、三民即那瑪夏）於 `備註` 欄具名。
- [x] 2.3 （實作 spec requirement「A district column that disagrees across source files is normalised, not trusted and not ignored」；design 決策 7：選舉區欄比照既有登記表正規化，不自行放寬）在 `scripts/build_local_election.py` 的 `DISTRICT_COLUMN_INCONSISTENT` 為 `D1-MT` 補上五筆登記（1998／2002／2005／2009-2010／2014），逐檔釘死允許值：`elbase` 皆為 `00`；`elcand` 1998 為 `00`、其餘四屆為 `01`；`elprof` 五屆皆為 `00` 與 `01` 兩種；`elctks` 1998／2002 為 `00`、2005／2009-2010／2014 為 `01`。**不為 2018／2022 登記**——四檔一致，多餘的條目會讓日後真的出現分歧時被靜默吸收。
- [x] 2.4 擴充 `scripts/build_town_crosswalk.py` 的 `PAIRS`，加入 1998 與 2002 的 `D1-MT`（本地檔為該屆鄉鎮市長，目標為同屆縣市議員區域檔），重新產生 `data/reference/cec-town-code-crosswalk-1998-2005.csv`，並同步更新該腳本的 `EXPECTED_TOTAL`／`EXPECTED_DIFFERENT` 為重新產生後的實測值。**不手改 CSV。**⚠️ **2005 的 D1 實測不需要對照**（319 個共同代碼逐一相符），不可因同屆 T2／T3 需要就一併補。完成判準：補列後，1998／2002 的 D1 鄉鎮市區代碼經對照表換算後，與同屆區域檔的代碼→名稱對應完全一致。
- [x] 2.5 在 `data/sources.json` 為 `mountain-township-codes.csv` 補上來源登記，說明其為本專案由 `cip-indigenous-areas` 名單與 `cec-votedata` 交叉核對而得的衍生對照表，並記錄「91 年公告後是否有修正未查證」這項限制。

## 三、建置腳本與 oracle

- [x] 3.1 （實作 spec requirement「The mountain township chief type is a subset of an official type, and is marked as project-defined」；design 決策 1：`D1-MT` 為自訂代碼，而非官方 D1）在 `scripts/oracles.py` 的 `CUSTOM_ELECTION_TYPES` 新增 `D1-MT`（值為 `山地鄉鄉長選舉`），並確認 `ADMIN_CODE_SYSTEMS`、`ELECTION_TYPE_GRANULARITY`、`office_type()` 等既有 oracle 函式皆已涵蓋此代碼。完成判準：以 `D1-MT` 呼叫每個 oracle 函式皆不拋 `OracleError`。
- [x] 3.2 在 `scripts/build_local_election.py` 新增 `load_mountain_township_codes()`，讀取對照表並回傳 `dict[(屆別, 省市, 縣市, 鄉鎮市區), str]`。對照表缺屆或某屆零列時中止並具名該屆。
- [x] 3.3 在 `YEARS` 各屆的 `parts` 新增 `D1-MT` 項，指向該屆 D1 資料夾：2022 為 `D1`、2014／2018 為中文子資料夾名、2009-2010 為 `鄉鎮市長` 子資料夾、1998／2002／2005 為無子目錄的根。資料夾名須以實際開啟壓縮檔確認，不得由既有屆別的命名慣例推導。
- [x] 3.4 （design 決策 8：`D1-MT` 是 D1 的投影層，上層彙總由投影資料重算）在 `process_one()` 加入投影層處理，只對 `etype == "D1-MT"` 生效、不改動其餘九種選舉種類的路徑：(1) 讀取該屆 D1 四個來源檔後，只保留代碼三元組落在對照表內、且行政層級為鄉鎮市區的列；(2) 由這些列**重算**縣市層級與檔別合計（有效票、無效票、投票數、選舉人數、候選人數、當選人數），供 `file_total` 與 `cross_validate()` 使用；(3) D1 原始的檔別合計**不寫入長表**。完成判準：`D1-MT` 在三份長表中沒有任何村里或投開票所層級的列，且檔別合計的選舉人數等於該屆各山地鄉選舉人數之和。
- [x] 3.4b 在 `data/processed/validation-report.json` 為 `D1-MT` 的每個檔別記錄機器可讀的彙總血緣：`彙總口徑`（山地鄉代碼篩選後重算）、`來源完整類型`（D1）、`來源原始彙總是否寫入長表`（false）。⚠️ **不新增長表欄位、不改 `檔別` 欄的語意**——`檔別` 表示來源檔分支，混入投影血緣會讓一欄承載兩種語意；新增欄位則會改動每一列既有資料。
- [x] 3.5 （實作 spec requirement「Selection is verified by a per-term count that fails when selection silently returns nothing」；design 決策 4：撇號剝除在讀取層，且必須可被驗證）（design 決策 9：篩選正確性由集合相等驗證，不由彙總對帳驗證）新增 `check_mountain_township_selection()`，逐屆斷言**實際篩出的代碼三元組集合等於對照表該屆的鍵集合**，並斷言對照表鍵不重複、每屆都有對照列、每個鍵在該屆來源中確實存在。不符時中止並具名屆別與差集（多選了哪些、少選了哪些）。⚠️ **不可只比對數量**：「少選 A 鄉、誤選 B 鄉」「對照表某列代碼被改成另一個合法鄉鎮」「重複一列同時漏掉另一列」三種失效在 `len()` 相等下全部通過。逐屆預期數量（1998／2002／2005＝30、2009-2010＝25、2014／2018／2022＝24）仍保留為附帶斷言。
- [x] 3.6 （實作 spec requirement「The mountain township chief series is not joined to the indigenous district chief series」；design 決策 5：`D1-MT` 與 `D2` 的不可接續由檢查強制，不靠文件）在 `scripts/test_build_local_election.py` 新增測試，斷言 `is_main_sequence("D1-MT")` 為偽、`is_main_sequence("D2")` 為真，且長表中每一列 `D1-MT` 的 `is_main_sequence` 欄皆為偽。⚠️ **不新增執行期檢查**：`is_main_sequence()` 的實作是 `etype not in CUSTOM_ELECTION_TYPES`，`D1-MT` 登記為自訂代碼後，任何「斷言兩者不同序列」的執行期檢查都恆為真、永遠不會失敗。此處的測試則會在有人把 `D1-MT` 改列為官方代碼時失敗。
- [x] 3.7 （實作 spec requirement「Ingestion stops at the level the figures are sound at」；design 決策 6：層級限制在建置強制，只納入鄉鎮市區及以上）新增 `check_mountain_township_level()`，斷言 `D1-MT` 進入長表的每一列其行政層級皆為鄉鎮市區或以上，出現村里／投開票所層級時中止並具名層級與屆別。⚠️ 這個檢查存在的理由是 2002／2005 的 `elctks` 當選註記在明細層級 100% 帶星號——那個缺陷**不會報錯**，只靠其他檢查攔不住。
- [x] 3.8 執行 `python scripts/build_local_election.py` 重新產生三份長表，確認 exit code 為 0（不得以管線接 `tail` 等指令，否則回報的是最後一個指令的 rc）。

- [x] 3.9 （實作 spec requirement「Sentinel Recognition Is Named Per Term, Not Global」；design 決策 10：年齡哨兵的具名粒度細化到（屆別, 選舉種類））在 `scripts/build_local_election.py` 新增 `AGE_UNRECORDED_EXTRA`，鍵為（屆別, 選舉種類）、值為該範圍額外適用的哨兵值集合，登記 `("1998", "D1-MT"): {"100"}`。`valid_age()` 與 `check_age_sentinel()` 改為接受選舉種類。完成判準：`check_age_sentinel()` 同時強制三件事——已登記範圍內不得出現宣告外的值、登記的哨兵值不得出現在宣告範圍外的同屆其他選舉種類、登記從未被用到即中止。

## 四、驗證

- [x] 4.1 驗證既有六種官方代碼與三種自訂代碼的列未被本 change 改動：從新舊三份長表各自篩掉 `D1-MT` 的列後計算 SHA-256，比對兩者相同。不相同時具名差異的選舉種類與屆別。
- [x] 4.1b 斷言三份長表中 `D1-MT` 的列其行政層級皆為鄉鎮市區或以上——直接讀長表的層級欄，不依賴建置期的檢查是否執行過。
- [x] 4.2 在 `scripts/test_build_local_election.py` 新增測試，涵蓋：對照表缺屆、某屆命中數少一個、`D1-MT` 與 `D2` 被接為同一序列、前綴撇號未剝除導致零命中、`D1-MT` 出現村里層級的列、來源檔選舉區欄出現登記表未列的第三種值、1998 的 `100` 出現在 `D1-MT` 以外的選舉種類、`AGE_UNRECORDED_EXTRA` 的登記從未被用到。⚠️ 其中「哨兵擴散」那一項以目前的登記會被「已登記範圍出現宣告外的值」先攔下，測試須暫時把 `AGE_UNRECORDED_EXTRA` 改為登記在不屬於 `AGE_UNRECORDED_TERMS` 的屆別，才驗得到它自己。
- [x] 4.2b 為 `scripts/build_mountain_township_codes.py` 的三個補償性檢查補上合成髒資料測試：未命中集合改變但數量不變、同一名稱對到多個鄉鎮市區代碼、輸出列數與宣告值不符。⚠️ 2026-08-27 實測這三個檢查在目前資料上**拿掉也不會失敗**（條件從未成立），依 HANDOFF 第六節的處置一項都不刪，逐項補髒資料。每項須為合成髒資料輸入，且須在該項防護被移除時失敗。
- [x] 4.3 在 `scripts/mutate_build_local_election.py` 為 4.2 的每項檢查新增對應變異，並確認新測試已加入該腳本的 `SEL` 篩選器（HANDOFF 地雷 1j：未加入的測試變異測試看不到）。
- [x] 4.4 執行 `python scripts/mutate_build_local_election.py`，確認全部變異被偵測、基準對照通過、無測試被跳過。任一變異未被偵測時，補測試而非調降判準。

## 五、文件

- [x] 5.1 更新 `docs/schema/cec-local-election.md`：新增 `D1-MT` 的欄位說明、七屆涵蓋範圍、以及「`D1-MT` 與 `D2` 不可接為同一序列」的具名說明（含 2009 與 2014 兩種缺額成因的差異）。
- [x] 5.2 更新 `README.md`：涵蓋範圍表與「尚未解決」第 3 點改記為已納入資料層，並明文記載「站台尚未呈現」及其理由。確認未新增任何比值或代表性指標。
- [x] 5.3 執行 `git status` 確認 `docs/` 下除 `docs/schema/` 的兩份文件外無任何修改，`docs/*.html` 與 `docs/en/` 皆未變動。
