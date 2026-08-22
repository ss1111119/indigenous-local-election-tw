## 1. 對照表

- [x] 1.1 寫一支產生對照表的腳本並產出 `data/reference/cec-town-code-crosswalk-1998-2005.csv`，欄位為 `屆別,選舉種類,縣市名稱,本地鄉鎮代碼,本地鄉鎮名稱,目標鄉鎮代碼,目標鄉鎮名稱`，共 1,290 列（1998 T2 177、1998 T3 226、2002 T2 211、2002 T3 226、2005 T2 224、2005 T3 226）。落實需求 `Town Codes Re-Numbered Per File Are Resolved Through The Same-Term Regional File`，以及設計的「決策 1：正規化目標選同屆「縣市議員（區域）」檔，不選「鄉鎮市長」檔」與「決策 2：配對鍵用（縣市名稱, 鄉鎮市區名稱），不用代碼」。數字來源為 design 的「實作前的完整普查結果」。⚠️ 放 `data/reference/` 不放 `data/processed/`——它是輸入不是產物，既有的位置檢查已守著這條紀律。驗證方式：CSV 列數為 1,290；其中 `本地鄉鎮代碼 != 目標鄉鎮代碼` 者為 829 列；（屆別, 選舉種類, 縣市名稱, 本地鄉鎮代碼）不重複；（屆別, 選舉種類, 縣市名稱, 目標鄉鎮代碼）亦不重複。

## 2. 建置端的解析

- [x] 2.1 在 `scripts/build_local_election.py` 加入 `TOWN_NAME_ALIASES` 具名常數，鍵為（屆別, 選舉種類, 縣市名稱, 原始名稱），值為（目標名稱, 目標鄉鎮代碼, 預期使用次數），共四筆，內容見 design 的「四筆截斷名稱」表：2002 T3 嘉義縣 里山鄉→阿里山鄉、2002 T3 屏東縣 地門鄉→三地門鄉、2002 T3 臺東縣 麻里鄉→太麻里鄉、2005 T3 臺東縣 麻里鄉→太麻里鄉。落實需求 `Truncated Town Names Are Named, Never Pattern-Matched` 與「決策 3：四筆截斷寫成具名 alias，不用任何字串通則」。⚠️ 鍵必須含屆別與選舉種類——2002 T3 與 2005 T3 都有「麻里鄉」，鍵只到縣市與名稱會讓一筆 alias 同時套用到兩屆。驗證方式：常數長度為 4；四個鍵的（屆別, 選舉種類）分別為三筆 2002 T3、一筆 2005 T3。
- [x] 2.2 加入 `load_town_crosswalk()` 讀取 1.1 的 CSV，並在讀取時中止於：檔案不存在、無資料列、鍵重複、目標鍵重複。回傳鍵為（屆別, 選舉種類, 縣市名稱, 本地鄉鎮代碼）、值為目標鄉鎮代碼的 dict。驗證方式：對真實檔呼叫回傳 1,290 筆；以合成輸入分別觸發四種中止，各自的錯誤訊息可區別。
- [x] 2.3 在 `process_one` 的鄉鎮市區正規化處，對 `TOWN_CODES_FILE_LOCAL` 內的六個檔改為查 2.2 的對照表填值，查不到即中止。既有四屆與其他檔的路徑不變。落實需求 `An Unresolved Town Is An Abort, Not An Empty Cell`、改寫既有需求 `Normalization Depth Is Limited To County Level`（更名為 `Normalization Depth Reaches Township, Not Below`——原名在本變更後已成假敘述），與「決策 4：配不到就中止，不留空」，同時落實需求 `Town-Level Comparability Is Declared Per File, Not Assumed From The Term`——變更後為空字串的只剩 T-COMBO 與 1994 省議員檔。驗證方式：跑 `process_one` 於 1998 T3，該檔 226 個鄉鎮的 `鄉鎮市區_正規化` 皆非空；跑於 2022 T2，輸出與變更前相同；跑於 1998 T-COMBO，該欄仍填原碼不變——實測更正：T-COMBO 與 1994 省議員檔本來就不是空字串，變更前有空值的只有這六個 T2／T3 檔。

## 3. 驗證

以下五條共同落實「決策 5：驗證雙向且逐檔，不只驗「有對到」」。

⚠️ 實作時的位置更正：這五條寫在 `process_one` 呼叫的 `verify_town_crosswalk()`，不是 `cross_validate`。兩個理由——`cross_validate` 拿不到壓縮檔因而讀不到區域檔；且對照表已把 alias 解開了，只查表的話 3.3／3.4 在建置時**永遠不會失敗**。改為每次建置都由來源重新推導再與對照表逐列比對，落實 design 風險 2 的承諾。

- [x] 3.1 在 `cross_validate` 加入目標端唯一性檢查：同屆區域檔中，同一縣市內不得出現兩個同名鄉鎮。落實需求 `Town Codes Re-Numbered Per File Are Resolved Through The Same-Term Regional File` 的情境 `Target-side names are not assumed unique`。⚠️ 這一條不能靠 1.1 產生時已經確認過——來源換版時對照表不會自己重新產生，但建置每次都跑。驗證方式：合成一份目標端有同名鄉鎮的輸入，斷言中止且訊息含該縣市與鄉鎮名稱。
- [x] 3.2 加入一對一檢查：同一檔內，兩個本地鄉鎮不得對到同一個（省市, 縣市, 目標鄉鎮）三元組。落實情境 `Two source towns resolve to one target`。⚠️ 只驗「全部有對到」放不掉多對一——兩個鄉鎮的票在下游被合併後，所有加總仍然平衡。驗證方式：合成一份兩個本地鄉鎮指向同一目標的對照表，斷言中止且訊息含兩個本地代碼。
- [x] 3.3 加入 alias 使用次數檢查：每一筆 alias 的實際套用次數必須等於 2.1 宣告的預期次數，多或少都中止。落實情境 `An alias entry is never used` 與 `An alias is applied a different number of times than declared`。⚠️ 只驗「有被用到」不足以證明它套在該套的地方。驗證方式：把某一筆的預期次數改成 2，斷言中止且訊息含該 alias 的鍵與實際／預期次數。
- [x] 3.4 加入 alias 目標一致性檢查：alias 宣告的目標鄉鎮代碼在區域檔中的名稱，必須等於 alias 宣告的目標名稱。落實情境 `An alias points at a target that does not agree`。驗證方式：把某一筆的目標代碼改成同縣市另一個鄉鎮，斷言中止且訊息含兩個名稱。
- [x] 3.5 加入逐檔鄉鎮數檢查：六個檔的鄉鎮市區單位數必須等於宣告值（177／226／211／226／224／226）。同時落實需求 `Town-Level Comparability Is Declared Per File, Not Assumed From The Term` 的情境 `Six files gain town-level joinability`。驗證方式：把其中一個宣告值加一，斷言中止且訊息含該檔與兩個數字。
- [x] 3.6 在 `validation-report.json` 的逐檔別區段加入 `鄉鎮市區正規化數` 與 `經alias解析數` 兩個欄位。驗證方式：報告中六個檔的 `鄉鎮市區正規化數` 分別為 177／226／211／226／224／226，`經alias解析數` 分別為 0／0／0／3／0／1，其餘檔別兩欄皆為 0。

## 4. 測試與變異

- [x] 4.1 在 `scripts/test_build_local_election.py` 新增 `test_town_crosswalk`，涵蓋：完全相符的配對（情境 `A town resolves to a different code than it carries locally`）、經 alias 的配對（情境 `A truncated name resolves through its alias`）、查無即中止（情境 `No matching town in the target` 與 `A new truncation appears in a future source revision`）、多重即中止（情境 `More than one matching town in the target`）、目標端同名即中止、一對一衝突即中止、alias 次數不符即中止、alias 目標不一致即中止、以及配對失敗不得寫出空字串（情境 `Resolution fails partway through a file`）。⚠️ 只斷言「有中止」不算——每一項都要斷言錯誤訊息含只有該檢查會輸出的字串。驗證方式：`pytest -k town_crosswalk` 通過，且該組的檢查項數不少於 12。
- [x] 4.2 在 `test_town_crosswalk` 加入實際對照表的迴歸斷言：1,290 列、829 列代碼不同、六檔各自的鄉鎮數、四筆 alias 的鍵。另斷言六個檔在村里與投開票所欄皆無非零值，落實情境 `These files carry no sub-township rows`——這一條若失敗，代表來源新增了更細的層級，鄉鎮層級的正規化不再足夠。驗證方式：這些數字與 design 的「實作前的完整普查結果」相同。
- [x] 4.3 在 `scripts/mutate_build_local_election.py` 為 3.1–3.5 各加一個變異（共 5 個），並把 `test_town_crosswalk` 加入 `SEL` 選擇器。⚠️ 漏掉 `SEL` 這一步，新測試在變異測試中根本不會被執行，變異會顯示為漏網而看起來像測試沒寫對。驗證方式：執行變異腳本，輸出為「變異測試全部被偵測到」、基準對照通過、且無測試被跳過。

## 5. 重建與文件

- [x] 5.1 跑 `python scripts/build_local_election.py` 完整重建，並比對輸出：1998／2002／2005 的三張長表內容改變（`鄉鎮市區_正規化` 欄），既有四屆（2009-2010／2014／2018／2022）的所有列逐位元不變。⚠️ 管線的 rc 是最後一個指令的——不要用管線包住建置指令，否則失敗會回報成功。驗證方式：以腳本逐列比對變更前後的兩份 summary，斷言差異只出現在屆別為 1998／2002／2005 且選舉種類為 T2 或 T3 的鄉鎮市區層級列，且差異只在 `鄉鎮市區_正規化` 這一欄。
- [x] 5.2 跑 `python scripts/build_site_data.py --check` 確認 `docs/index.html` 與 `docs/roster.html` 的資料常數仍完全重現。⚠️ 站台是否讀這一欄要實測，不憑印象。驗證方式：兩份 HTML 皆回報完全重現。
- [x] 5.3 更新 `docs/schema/cec-local-election.md`：在自我驗證清單加入 3.1–3.5 五條，並依需求 `Town-Level Comparability Is Declared Per File, Not Assumed From The Term` 說明 `鄉鎮市區_正規化` 的語意在本次變更後縮小——為空字串的只剩 T-COMBO 與 1994 省議員檔。同時更新 `README.md` 的檔案表加入新的對照表，以及 `HANDOFF.md` 的地雷 2（該項描述的狀態已改變）。文件描述區域檔時要用「同屆 canonical target」而非「真實行政區代碼的證明」，落實 design 決策 1 的但書。驗證方式：以指令確認三份文件都不再宣稱這六個檔的鄉鎮市區層級「未正規化」。
