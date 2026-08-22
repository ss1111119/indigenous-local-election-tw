## 1. 讀檔與宣告

- [x] 1.1 建立 `scripts/build_party_list_election.py` 的讀檔層：五屆的資料夾、`QUOTED_FILES` 具名宣告帶前置單引號的 7 個檔（2008 `elcand`／`elrepm`；2012 `elbase`／`elcand`／`elprof`／`elctks`／`elrepm`）並沿用 `check_quoting_declaration` 雙向核對、`FILES_WITHOUT_SUFFIX` 沿用（2016 的 `elpaty` 不帶 `_T4`）、七個檔的欄數逐列檢查（elbase 6／elcand 16／elpaty 2／elprof 20／elctks 10／elrepm 10／elretks 5）。落實需求 `Party-List Votes Are Built From The Same Archive As Every Other Dataset` 的情境 `Column counts follow the official format document`、`The quoting convention varies within a term`、`One file in a term carries no filename suffix`。⚠️ 「引號」有兩種：CSV 雙引號由 `csv.reader` 透明處理、**不需宣告**；要宣告的是**值內的前置單引號**（Excel 強制文字），因為它要被剝除而剝除與否會改變鍵。我在普查時量錯了屬性，design 已更正。⚠️ **不可用嗅探**——嗅探會自動適應來源變化，永遠不會失敗。數字來源為 design 的「實作前的完整普查結果（五屆逐檔，非抽樣）」。驗證方式：五屆七檔皆讀入成功，列數與該表相符（2008 elprof 22,581／elctks 270,972，2024 elprof 25,924／elctks 414,784）；把某檔的宣告欄數改錯一個，斷言中止且訊息含檔名。
- [x] 1.2 宣告選區欄的允許值：`elbase` 全 `00`、`elcand` 全 `01`、`elprof` 2008 為 `{00}`／2012 起為 `{00,01}`、`elctks` 為 `{00,01}`。出現宣告外的值即中止。落實需求 `The District Column Is Declared Per File And Ignored When Joining` 的情境 `An undeclared district value appears`，以及「決策 6：選區欄逐檔宣告允許值，並在配對時忽略」。驗證方式：五屆皆通過；把 2024 `elprof` 的宣告改成只允許 `{01}`，斷言中止且訊息含實得值集合。
- [x] 1.3 加 `--census` 模式：由來源量出全部宣告值，印成可直接貼上的 Python 常數區塊（`EXPECTED_ROWS`、`EXPECTED_RATE_SUMS`、`EXPECTED_RETKS`、`EXPECTED_JOIN`、`EXPECTED_INDIGENOUS_ELECTORS`），並用它重新產生已寫入的那五組常數。⚠️ census 模式**不得讀取被它量測的宣告值**，否則檢查變成自我證明；`load_source` 需要一個不比對列數的路徑。引號宣告的核對要保留——那一條是對來源雙向自我驗證的，不循環。

  ⚠️ **為什麼要有這一項**：實作到 3.1 時我已在宣告值上錯八次，其中四次（2016 elpaty 列數、漂移代號數、得票率合計、2020 可接率）的共同根因是**我跑了普查、印出摘要，然後把摘要當成資料**——截斷、四捨五入、只印一個分母各自銷毀了資訊，而摘要看起來永遠是完整的。第五次（原住民選舉人四屆的值）更糟：我沒量就寫，還標成「普查值」。手抄宣告值這個動作本身就是錯誤來源。

  驗證方式：`--census` 的輸出貼回程式後，正常建置通過且五組常數與貼上前逐字元相同（相同代表手抄的那些是對的；不同代表又抓到一個）。並斷言 census 模式在 `EXPECTED_ROWS` 被清空時仍能跑完——證明它不依賴被量測的宣告。

## 2. 跨檔對帳

- [x] 2.1 政黨票逐所加總 ＝ 該所有效票。配對鍵**忽略選區欄**。落實情境 `Party votes reconcile to the station's valid votes` 與 `Joining without ignoring the district column`。⚠️ 不忽略選區欄時 2008 的 22,581 個單位只有 26 個對得上——這一條若寫錯會表現成「2008 幾乎全部對不上」而不是報錯。驗證方式：五屆皆 0 筆不符；把鍵改成含選區欄，斷言 2008 中止且訊息含對不上的單位數。
- [x] 2.2 政黨代號的同屆唯一性與跨屆漂移處置：同一屆內一個代號不得對到兩個名稱（中止）；跨屆的分桶鍵為（政黨代號, 政黨名稱）。落實需求 `Party Identity Is Keyed On Code And Name Together` 的兩個情境，以及「決策 7：政黨分桶鍵含名稱」。⚠️ 實測 9 個代號跨屆指不同政黨（133／134／166／189／195／199／278／102 等）；代號 1 與 16 五屆穩定不是代號穩定的證據。驗證方式：斷言跨屆漂移的代號數為 9 且清單與 design 相符；合成一份同屆同代號兩名稱的 `elpaty`，斷言中止。
- [x] 2.3 `elretks` 的不變量：當選人數合計 ＝ 34（五屆皆 34）、第一階段與第二階段得票率合計皆 ＝ 100.00%。第 4 欄視為候選人數不是席次。落實需求 `Seat Allocation Figures Are Preserved, Not Recomputed` 的三個情境。⚠️ 兩個比率原樣保留，不重算——第二階段是排除未達門檻後的重算值，是席次分配依據。驗證方式：五屆皆通過且與 design 的不變量表相符（政黨數 18／16／29／19／16、候選人 128／127／179／216／177）；把某屆某黨的當選人數加一，斷言中止且訊息含實得合計與 34。

## 3. 原住民佔比與可接性

- [x] 3.1 逐投開票所算原住民選民佔比 `p` 與投票者佔比 `q`：`p = (山原選舉人 + 平原選舉人) / 政黨票選舉人`、`q = (山原投票數 + 平原投票數) / 政黨票投票數`。對不上原住民檔的所依「決策 2b：「不在原住民檔內」有兩種意思，用反向缺口區分」分成三類：該縣市反向缺口為 0 者填 `p=0`（量出來的事實）、兩向皆有缺口者留空並標 `原住民可接=false`、選舉人或投票數為 0 者同樣留空；另立 `缺席原因` 欄記明是哪一類。落實需求 `The Weight Is The Share Of Voters, Not The Share Of Registered Electors` 的兩個情境，以及「決策 2：權重用 q（投票者佔比）不用 p（選舉人佔比）」——那一條是外部覆核抓到的，我原本的框架把 p 當成 q。驗證方式：五屆的可用率為 100%／100%／100%／**100%**（2020 的 189 個嘉義市所是 p=0 不是缺口）／99.38%；2024 未知 110 所；2020 那兩個特設所（村里碼 0999）的 p 恰為 1.0000。
- [x] 3.2 把 2024 那 125 個對不上的所列入報告的具名清單，含所在鄉鎮市區的原住民密度分類；並宣告每屆可接率的下限，低於下限即中止。⚠️ 實測 123 個在 <20% 的鄉鎮市區、2 個在 ≥80%，對高佔比層影響最多 2 所——但「這次影響小」不是不記的理由，來源換版後分布可能改變。驗證方式：報告含該 125 筆的分類統計；把 2024 的可接率下限宣告成 100%，斷言中止且訊息含實得可接率。
- [x] 3.3 原住民選舉人總數與原住民立委的檔別合計核對：逐屆斷言投開票所層級加總 ＝ 山原檔別合計 ＋ 平原檔別合計（2024 為 228,164 ＋ 210,036 ＝ 438,200）。⚠️ 這一條抓的是「分母算錯」——我在探索階段就是拿交集後的 422,774 當分母，比正確值少 3.5%。驗證方式：五屆皆相符；把加總改成只算對得上的所，斷言 2024 中止且訊息含兩個數字。

## 4. 極限法與輸出

- [x] 4.1 實作 Duncan-Davis 極限法並輸出 `data/processed/indigenous-party-preference-bounds.csv`：門檻 `(0.95, 0.90, 0.80)` 以 `p` 篩所，逐屆 × 門檻 × 政黨輸出 `觀察_得票率`、`下界_原住民得票率`、`上界_原住民得票率`，以及 `門檻`、`所數`、`涵蓋原住民選舉人`、`涵蓋率`、`q`、`p`、`有效政黨票`。公式為 `下界 = max(0, (y - (1 - q)) / q)`、`上界 = min(1, y / q)`。落實需求 `An Estimate Ships With Bounds That Arithmetic Alone Establishes` 與 `Estimates Are Separated From Official Figures By Table And By Column Name`，以及「決策 1：輸出「觀察值＋極限」而不是單一估計值」、「決策 3：三個門檻都輸出，不挑一個」、「決策 4：估計值與官方數字分表分欄」。驗證方式：2024 ≥95% 層的中國國民黨為觀察 68.10%、界限 [67.13%, 70.17%]，與 spec 的範例表逐格相符；三個門檻的所數為 90／172／237、涵蓋率為 11.0%／20.7%／28.4%。
- [x] 4.2 把界限接成建置時的守門員：斷言 `0 ≤ 下界 ≤ 觀察 ≤ 上界 ≤ 1`，任一違反即中止。落實情境 `Bounds contain the observation` 與「決策 5：極限法本身就是守門員」。⚠️ 這是估計值唯一能寫出「會失敗」的檢查——若權重誤用 `p`（決策 2）或公式寫錯，界限會與觀察值矛盾。驗證方式：把公式裡的 `q` 換成 `p`，斷言中止且訊息含違反的政黨與三個數值；把 `1 - q` 寫成 `1 + q`，同樣斷言中止。
- [ ] 4.3 輸出三張官方數字表：`cec-party-list-summary-long.csv.gz`（投開票所層級，含 `p`／`q`／`原住民可接`）、`cec-party-list-votes-long.csv.gz`（逐所逐政黨得票）、`cec-party-list-seats.csv`（來自 `elretks`，兩個比率原樣保留）。並在 `scripts/oracles.py` 新增這三張表的欄位 manifest。⚠️ 不可動既有的 `MANIFEST`（`build_local_election.py` 會把它寫進 `validation-report.json`）。驗證方式：三份輸出的欄位與 manifest 逐欄相符；六張既有長表的 SHA-256 與變更前相同。
- [ ] 4.4 個資排除：`elrepm` 只讀不輸出，並加一條檢查斷言任何輸出的欄名集合都不含出生日期／出生地／學歷衍生欄。落實需求 `Personal Data In The Party Representative File Is Never Output`。⚠️ 實測五屆的這三欄都有值，不是空欄。驗證方式：把 `elrepm` 的出生地加進某張表的欄位清單，斷言中止且訊息含該欄名。

## 5. 測試與變異

- [ ] 5.1 建立 `scripts/test_build_party_list_election.py`：單元測試涵蓋讀檔層、選區欄宣告、政黨鍵、`elretks` 不變量、`p`／`q` 計算、極限法公式；整合測試以合成壓縮檔跑完整管線；迴歸測試把五屆的實際數字釘死（逐屆所數、可接率、三門檻的所數與涵蓋率、2024 三大黨的界限）。⚠️ 每一條 Failure mode 都要有一組會觸發它的合成輸入，且斷言錯誤訊息含**只有該檢查會輸出的字串**——只斷言「有中止」不算。驗證方式：`pytest -k party_list` 通過，且檢查項數不少於 40。
- [ ] 5.2 建立 `scripts/mutate_build_party_list_election.py`：為每一條 Failure mode 各配一個變異，含基準對照（未變異的副本必須通過、且不得有測試被跳過）與變異字串唯一性自我檢查。⚠️ 變異副本必須放在 repo 根目錄下一層（`_mut/`），放深會讓迴歸測試靜默跳過而 pytest 仍報 passed。驗證方式：執行後輸出「變異測試全部被偵測到」、基準對照通過、無測試被跳過。

## 6. 文件

- [ ] 6.1 新增 `docs/schema/cec-party-list-election.md`：三張官方表與界限表的欄位、五屆的普查結果、七個檔的語意（含 `elrepm`／`elretks` 引自官方格式文件）、選區欄與政黨代號的陷阱、以及建置時的中止點清單。⚠️ **涵蓋率與地理集中要寫在最前面，不是註腳**——落實需求 `Coverage And Its Skew Are Stated Before The Figure, Not After It`。⚠️ 區域檔用詞：描述極限法時要寫「這 90 所裡的原住民」，不可寫「原住民」。驗證方式：以指令確認文件在出現任何界限數字之前，已先出現涵蓋率與地理集中的敘述。
- [ ] 6.2 更新 `data/sources.json` 加入五屆 `不分區政黨` 的來源條目（含 `elrepm`／`elretks` 的語意與個資註記、2008 的引號差異、2016 的後綴例外），並更新 `README.md` 的檔案表與 `HANDOFF.md` 的地雷區（新增「政黨代號跨屆漂移」與「界限不約束地理偏誤」兩條）。驗證方式：以指令確認 `README.md` 的檔案表含四份新輸出，且 `HANDOFF.md` 含那兩條地雷。
