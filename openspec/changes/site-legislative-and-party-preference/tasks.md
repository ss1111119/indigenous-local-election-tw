## 1. 產生器讀入三個資料集

- [x] 1.1 在 `scripts/build_site_data.py` 加入立委三張長表與界限表的讀取（`cec-legislative-election-summary-long.csv.gz`、`cec-legislative-election-candidates-long.csv`、`cec-legislative-election-votes-long.csv.gz`、`indigenous-party-preference-bounds.csv`），沿用既有的 `read_long_table` 與必要欄位宣告。落實需求 `Site Data Is Generated From The Long Tables` 的情境 `A new dataset is added to the site` 與「決策 5：資料常數仍由腳本產生，且既有屆別逐鍵重現」。數字來源為 design 的「實作前的完整清點」。⚠️ 席次一律取自 `當選`（權威值）欄，不可數 `當選註記`——落實 `Seats Come From The Authoritative Elected Field`。驗證方式：四份皆讀入成功；立委的九屆政黨得票率與 design 普查表逐格相符（1995 國民黨 77.0%、2024 國民黨 41.4%／無黨籍 32.9%／民進黨 22.5%）；把必要欄位清單加一個不存在的欄名，斷言中止且訊息含該欄名。
- [x] 1.2 宣告立委的分桶集合為腳本內的**單一常數** `LEGISLATIVE_PARTY_BUCKETS`（中國國民黨、民主進步黨、親民黨、無黨團結聯盟、無黨籍、其他），與地方公職既有的 `PARTY_BUCKETS` 並存但不共用。分桶鍵仍為（政黨代號, 政黨名稱）配對。落實需求 `Bucket Sets Are Declared Per Dataset And Are Not Shared` 的三個情境，以及「決策 3：立委的分桶集合與地方公職不同，且逐頁宣告」。⚠️ 直接沿用地方公職那三桶會讓**親民黨 2001 年的 27.7%、無黨團結聯盟 2004 年的 26.0%** 掉進「其他」，而那正是那兩屆的主要故事。驗證方式：斷言兩個集合**不相等**（合併成一套時這條要失敗）；斷言 2001 年親民黨與 2004 年無黨團結聯盟各自有獨立的桶且非零；斷言九屆的無黨籍桶皆非零（來源有「無」與「無黨籍及未經政黨推薦」兩套編碼）。

## 2. 立委頁

- [x] 2.1 新增 `docs/legislative.html`：九屆的政黨得票率折線、席次、投票率，山地（L3）／平地（L2）分列；頂端固定一段「本頁的資料集是什麼、不是什麼」。資料常數標記為 `const LEG = `，由 1.1 產生。落實需求 `Datasets With Different Populations Are Presented Apart` 的情境 `A reader arrives on a page`、「決策 1：主軸是立委得票率，政黨票界限是次要」與「決策 2：立委另立一頁，不併入既有頁面」。⚠️ 圖表標題寫「立委選舉的政黨得票率」，**不寫「政黨支持度」**——那個數字受候選人是誰、現任優勢、單一席次選區影響，不等於政黨認同（design 風險 1）。驗證方式：頁面的投票率九屆為 57.9／55.6／57.8／48.8／47.4／62.0／54.8／65.6／61.4%；席次國民黨為 6／6／4／4／4／4／4／3／3、民進黨為 0／0／0／1／0／0／1／2／2；以指令確認頁面不含「政黨支持度」字樣。
- [x] 2.2 在立委頁加入**政黨傾向區塊**：不分區政黨票的觀察值與三個門檻的界限，常數標記為 `const BOUNDS = `。落實需求 `Coverage And Its Skew Are Stated Before The Figure, Not After It` 的情境 `The figure appears on a page rather than in a document` 與 `Presenting more than one threshold`，、需求 `A Page Built For General Readers Resists Extraction Of A Figure From Its Scope` 的四個情境，以及「決策 4：界限的呈現以涵蓋率為主視覺，不是誤差線」。⚠️ 區塊標題寫「原住民族地區的 90 個投開票所」不寫「原住民」；涵蓋率（11.0%）與「山地鄉」必須出現在該區塊**任何百分比之前**；限定語與數字必須在**同一個可複製的區塊**內。驗證方式：以指令比對字元位置，斷言「11.0%」與「山地鄉」的位置早於該區塊第一個百分比數字；斷言標題不含未限定的「原住民的政黨傾向」；斷言三個門檻都出現（不挑一個）。
- [x] 2.3 三頁互相連結，並各補 `description` 與 Open Graph 標籤；新增 `docs/sitemap.xml` 涵蓋三頁。落實「決策 6：補上可被發現性的必要條件」。⚠️ 這是必要條件不是充分條件——它讓頁面被找到時不會漏掉，不會讓任何人開始找。驗證方式：三頁皆含 `description` 與 `og:title`／`og:description`；`sitemap.xml` 列出三個網址且格式可被 XML 解析；三頁的導覽皆含另外兩頁的連結。

## 3. 既有頁面不得被動到

- [x] 3.1 執行 `python scripts/build_site_data.py --check`，確認 `docs/index.html` 與 `docs/roster.html` 的既有屆別資料常數**逐鍵完全相同**，只允許本變更刻意新增的鍵。落實需求 `Existing Terms Must Be Reproduced Before Extending`。⚠️ 這條在 `update-site-to-nine-terms` 已經用過一次；它擋的是「擴充時順手改壞既有屆別」。驗證方式：`--check` 對兩頁皆回報完全重現；並斷言六張既有長表（地方公職三張、立委三張）與界限表的 SHA-256 與本變更前相同——本變更不重建任何資料。

## 4. 可及性

- [x] 4.1 新圖表的配色通過 `scripts/palette_metrics.py` 的量測並留下紀錄：相鄰類別色在正常視覺 ΔE ≥ 15、protan／deutan 模擬 ΔE ≥ 8，明暗兩主題各自量測。落實 `site-chart-accessibility` 的 `Categorical Colors Are Measured Against Each Other` 與 `Color Verification Is Recorded, Not Asserted`——該份 spec 的六條需求見 design 的「五份既有 spec 的約束」。⚠️ 立委頁有**五個政黨桶**，比地方公職多兩個，相鄰配對數從 3 增為 10——既有配色不保證還夠用。驗證方式：量測腳本對新配色全數達標且輸出寫入版控；把任兩個相鄰色改成相近值，斷言量測回報未達標。
- [x] 4.2 新圖表的標記內文字對其填色達 4.5:1，且**每一張以顏色編碼的圖表都有表格等價物**；列印與強制色彩模式下編碼不消失。落實 `Labels Drawn Inside A Mark Meet 4.5:1 Against That Mark`、`Color-Encoded Data Has A Tabular Equivalent`、`Print And Forced Colors Do Not Erase The Encoding`。驗證方式：量測腳本回報每個標記／填色配對的對比值皆 ≥ 4.5；以指令確認每個帶顏色編碼的圖表區塊都有對應的 `<table>`；列印樣式與 `forced-colors` 媒體查詢皆存在且不只改顏色。

## 5. 測試與變異

- [ ] 5.1 擴充 `scripts/test_build_site_data.py`：立委常數的迴歸值（九屆得票率、席次、投票率）、兩個分桶集合不相等、無黨籍桶九屆皆非零、界限常數與 CSV 逐列相符、既有兩頁逐鍵重現、界限區塊的涵蓋率位置早於任何百分比。⚠️ 每一條 Failure mode 都要有一組會觸發它的輸入，且斷言錯誤訊息含**只有該檢查會輸出的字串**。驗證方式：`pytest scripts/test_build_site_data.py` 通過，且該檔的檢查項數比變更前增加不少於 25 項。
- [ ] 5.2 擴充 `scripts/mutate_build_site_data.py`：為 5.1 的每一條檢查各加一個變異，並**為每個被變異的檔各加一個 canary**。⚠️ canary 是必要的：本專案在政黨票那個 change 遇過「36 個變異全部漏網而基準通過」，成因是副本沒被載入（`sys.path` 指回真正的 `scripts/`），而單一 canary 看不出另一個檔沒生效。驗證方式：執行後輸出「變異測試全部被偵測到」、每個 canary 皆被抓到、基準對照通過、無測試被跳過。

## 6. 文件

- [ ] 6.1 更新 `README.md`：線上瀏覽的連結加入立委頁；說明站台現在涵蓋三個資料集且**不可互相比較**；把「尚未解決」中與站台涵蓋範圍有關的敘述改為現況。更新 `HANDOFF.md`：地雷區新增一條「三個資料集在站台上分開呈現的理由」，並更新第一節的狀態（主 spec 數、已歸檔的 change 數）。⚠️ `HANDOFF.md` 第一節目前停在 2026-08-20／21，說「三個能力、25 條 Requirement」而實際是七個、57 條——那是交接文件用來定位的部分。驗證方式：以指令確認 README 含立委頁連結、`HANDOFF.md` 不再出現「25 條 Requirement」與「site-accessibility-baseline …尚未歸檔」。
