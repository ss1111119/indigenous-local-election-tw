## Context

站台目前只呈現三個資料集中的一個。`docs/index.html` 與 `docs/roster.html`
提到「立委」的次數是 **0**；`build_site_data.py` 只讀
`cec-local-election-summary-long.csv.gz` 與 `cec-local-election-candidates-long.csv`。

讀者設定為**一般讀者與媒體**。這個設定是本設計的主要約束來源。

### 實作前的完整清點

**站台現況**

| 項目 | 現況 |
| --- | --- |
| 頁面 | `index.html`、`roster.html`，僅互相連結 |
| 資料常數 | `index.html` 的 `DATA`、`roster.html` 的 `D` 與 `MAIN` |
| 替換機制 | `build_site_data.py` 就地替換標記行；`--check` 驗「重建 == 現況」 |
| `DATA.types` | 9 種，全為地方職位（T2／T3／D2／R3／R2／T1／T-COMBO／T-PRV3／T-PRV2） |
| `DATA.years` | 9 屆，全為地方選舉年 |
| 分桶 | `PARTY_BUCKETS` 三個 ＋ `其他` |
| 可被發現性 | 只有 `charset` 與 `viewport` 兩個 meta；無 description、無 og、無 sitemap |
| 腳本規模 | 836 行 |

**立委資料（零推論，涵蓋全體原住民選民）**

政黨得票率逐屆：

| 屆別 | 國民黨 | 第二名 | 第三名 |
| --- | ---: | --- | --- |
| 1995 | 77.0% | 無黨 13.3% | 中國台灣原住民黨 4.4% |
| 1998 | 71.5% | 全國民主非政黨聯盟 15.5% | 民進黨 7.1% |
| 2001 | 47.7% | 親民黨 27.7% | 民進黨 6.5% |
| 2004 | 40.6% | 無黨團結聯盟 26.0% | 親民黨 17.6% |
| 2008 | 54.9% | 親民黨 17.5% | 無黨團結聯盟 13.4% |
| 2012 | 51.5% | 無黨籍 15.6% | 親民黨 13.7% |
| 2016 | 49.0% | 民進黨 16.2% | 無黨團結聯盟 13.3% |
| 2020 | 48.1% | 無黨籍 27.4% | 民進黨 19.4% |
| 2024 | 41.4% | 無黨籍 32.9% | 民進黨 22.5% |

投票率逐屆：57.9／55.6／57.8／48.8／47.4／62.0／54.8／65.6／61.4%。

當選席次：國民黨 6／6／4／4／4／4／4／3／3；民進黨 0／0／0／1／0／0／1／2／2。
（1998–2004 每屆 8 席，其餘 6 席。）

九屆合計得票率：國民黨 51.7%、無黨籍 13.4%、民進黨 12.1%、
**親民黨 7.8%、無黨團結聯盟 6.9%**、無 1.8%。

**政黨票的界限**（已在 `indigenous-party-preference-bounds.csv`，228 列）

2024 ≥95% 層：國民黨觀察 68.10%、界限 [67.13%, 70.17%]，90 所、涵蓋 11.0%。

### 五份既有 spec 的約束

| Spec | 直接約束本設計的需求 |
| --- | --- |
| `indigenous-legislative-elections` | Legislative Data Is Published Separately From Local Office Data |
| `site-data-generation` | Existing Terms Must Be Reproduced Before Extending／Party Buckets Are Keyed By Source Identity／The Independent Bucket Is Non-Empty In Every Term／Bucket Membership Has A Single Source |
| `site-chart-accessibility` | 六條全部適用（類別色兩兩互比、標記內文字 4.5:1、**顏色編碼必須有表格等價物**、列印與強制色彩、頁面宣告、量測留紀錄） |
| `bounded-estimates` | Coverage And Its Skew Are Stated Before The Figure, Not After It |
| `party-list-votes` | Party Identity Is Keyed On Code And Name Together |

## Goals / Non-Goals

**Goals:**

- 立委的九屆資料在站台上有出口，且以**零推論的完整事實**為主軸
- 政黨票的界限有出口，且**不可能被單獨引用而不帶涵蓋率**
- 三個資料集在站台上明確分開，讀者不會把它們當成可比
- 地方公職既有的資料常數**逐鍵重現**
- 六條可及性需求全部通過，並留下量測紀錄

**Non-Goals:**

- 不把立委與地方公職畫在同一條折線
- 不改動地方公職既有的呈現
- 不改倉庫名稱
- 不做總統票、區域立委票、公投
- 不在前端做任何新的統計推論

## Decisions

### 決策 1：主軸是立委得票率，政黨票界限是次要

政黨票的界限是三個資料集裡**最有解釋力也最不可推廣**的東西：
涵蓋 11.0% 的原住民選舉人，且全在原住民族地區的山地鄉。

對一般讀者與媒體，把它當主角等於**設計一個容易被錯誤引用的頁面**——
「原住民 68% 投國民黨」會被抄走，而那句話是錯的。

立委得票率沒有這個問題：那張票只有原住民能投，分母就是全體原住民選民，
不需要極限法、不需要門檻、沒有涵蓋率問題。它回答的問題略窄
（「投給哪個政黨的候選人」而非「政黨傾向」），但**它是完整的**。

替代方案是以政黨票為主軸並加上警語。不採用：警語擋不住複製貼上，
而版面順序擋得住。

### 決策 2：立委另立一頁，不併入既有頁面

`indigenous-legislative-elections` 已明文要求
「Legislative Data Is Published Separately From Local Office Data」。

站台既有的 `is_main_sequence` 是**地方公職內部**的可比性旗標
（1994 省議員與合併類別不進折線）。立委需要**更強的分隔**：
它是中央職位、全國單一選區，與地方公職的席次、選區、選舉人範圍都不同義。

處置：新增 `docs/legislative.html`，三頁互相連結並在每頁頂端標明
「本頁的資料集是什麼、不是什麼」。

⚠️ 不採用「在 `DATA.types` 加上 L2／L3 並用旗標區分」——那會讓兩者
出現在同一份清單裡，只差一個布林值，而前端有多處以 `DATA.types`
迭代繪圖。旗標式的分隔在這個資料上已經證明不夠。

### 決策 3：立委的分桶集合與地方公職不同，且逐頁宣告

既有 `PARTY_BUCKETS` 是（中國國民黨, 無黨籍及未經政黨推薦, 民主進步黨）
＋ 其他。直接套到立委會出事：**親民黨 2001 年拿 27.7%、
無黨團結聯盟 2004 年拿 26.0%**，兩者都會被丟進「其他」，
而那正是那兩屆的主要故事。

立委頁的分桶集合為：中國國民黨、民主進步黨、親民黨、無黨團結聯盟、
無黨籍（含來源的「無」與「無黨籍及未經政黨推薦」兩種編碼）、其他。

⚠️ 分桶鍵仍為（政黨代號, 政黨名稱）配對，不是只比名稱——
`Party Buckets Are Keyed By Source Identity` 與 `party-list-votes` 的
`Party Identity Is Keyed On Code And Name Together` 都要求這一點。
無黨籍在來源有兩套不重疊的編碼，站台既有的分桶就是為此建立的。

⚠️ 兩個分桶集合都必須有**單一來源**（`Bucket Membership Has A Single Source`），
不可在前端與腳本各寫一份。

### 決策 4：界限的呈現以涵蓋率為主視覺，不是誤差線

界限只有 3 個百分點寬。畫成長條加誤差線，看起來會像一個很確定的 68%——
**那在視覺上對那 90 個所是誠實的**，卻會讓讀者以為它適用於全體。

**真正的不確定性不在區間裡，在涵蓋率。** 所以：

- 區塊標題寫「原住民族地區的 90 個投開票所」，不寫「原住民」
- 涵蓋率（11.0%）與地理集中（全在山地鄉）出現在**任何百分比之前**
- 三個門檻並列，讓涵蓋率與精度的取捨可見，不挑一個
- 數字旁固定附「這不是全體原住民」的限定語，且該限定語與數字在
  **同一個可複製的區塊**內

落實 `bounded-estimates` 的 `Coverage And Its Skew Are Stated Before The
Figure, Not After It`——那條需求原本只約束文件，本變更把它擴及站台。

### 決策 5：資料常數仍由腳本產生，且既有屆別逐鍵重現

沿用 `build_site_data.py` 的既有機制：就地替換標記行、`--check` 驗
「重建 == 現況」。新增兩個標記（立委頁的資料常數與界限常數）。

⚠️ `Existing Terms Must Be Reproduced Before Extending` 是硬要求：
擴充後，地方公職既有屆別的常數必須**逐鍵完全相同**，
只允許刻意新增的鍵。這條在 `update-site-to-nine-terms` 已經用過一次。

### 決策 6：補上可被發現性的必要條件

站台目前只有 `charset` 與 `viewport` 兩個 meta。給媒體看的頁面，
分享連結時應有標題與摘要而不是裸網址。

三頁各補 `description` 與 Open Graph 標籤，並加 `docs/sitemap.xml`。

⚠️ **這是必要條件不是充分條件**：它讓頁面被找到時不會漏掉，
**不會讓任何人開始找**。真正決定有沒有讀者的是連結放在哪裡，
那不在本變更的範圍內，也不是技術問題。

## Implementation Contract

**Behavior**：站台由兩頁擴充為三頁。

- `docs/legislative.html`（新）：九屆原住民立委的政黨得票率、席次、
  投票率，山地／平地分列；以及**政黨傾向區塊**（不分區政黨票的
  觀察值與三個門檻的界限）
- `docs/index.html`、`docs/roster.html`：新增指向立委頁的連結、
  補 `description` 與 og 標籤；**資料常數逐鍵不變**
- `docs/sitemap.xml`（新）：三頁

**Interface / data shape**：

- `build_site_data.py` 新增讀取 `cec-legislative-election-summary-long.csv.gz`、
  `cec-legislative-election-candidates-long.csv`、
  `cec-legislative-election-votes-long.csv.gz`、
  `indigenous-party-preference-bounds.csv`
- 立委頁的常數標記為 `const LEG = `，界限常數標記為 `const BOUNDS = `
- `LEG` 的形狀：`{types: [{code, name, years: {年度: {electors, votes,
  turnout, seats, cands}}}], years: [...], parties: [...]}`
- `BOUNDS` 的形狀：`{terms: [...], thresholds: [...], rows: [{屆別, 門檻,
  政黨, 所數, 涵蓋率, 觀察, 下界, 上界}]}`
- 分桶集合宣告為腳本內的單一常數，前端由常數讀取，不各寫一份

**Failure modes**（全部中止）：

- 地方公職既有屆別的資料常數與現況不逐鍵相同
- 立委的席次來源不是 `當選`（權威值）欄
- 分桶把某一屆的無黨籍算成 0（來源有兩套編碼）
- 立委與地方公職的資料出現在同一份 `types` 清單
- 界限的任一列不滿足 `0 ≤ 下界 ≤ 觀察 ≤ 上界 ≤ 1`
- 界限區塊在涵蓋率之前出現任何百分比
- 任一圖表的相鄰類別色未通過 ΔE 門檻，或標記內文字未達 4.5:1
- 任一以顏色編碼的圖表沒有表格等價物

**Acceptance criteria**：

- `python scripts/build_site_data.py --check` 回報三頁的現有屆別完全重現
- 立委頁的九屆得票率與本設計普查表逐格相符
  （1995 國民黨 77.0%、2024 國民黨 41.4%／無黨籍 32.9%／民進黨 22.5%）
- 立委頁的投票率九屆為 57.9／55.6／57.8／48.8／47.4／62.0／54.8／65.6／61.4%
- 以指令確認界限區塊中，涵蓋率與「山地鄉」出現在任何百分比數字之前
- `python scripts/palette_metrics.py` 對新圖表的配色留下量測紀錄且全數達標
- `python scripts/test_build_site_data.py` 全數通過
- `python scripts/mutate_build_site_data.py` 全數被偵測
- 地方公職三張長表與立委三張長表**逐位元不變**（本變更不重建資料）

**Scope boundaries**：

- 在範圍內：站台三頁、`build_site_data.py`、其測試與變異、配色量測、
  sitemap 與 meta、README／HANDOFF 的對應更新
- 不在範圍內：資料層（不重建任何長表）、倉庫改名、總統票／區域立委票／
  公投、把連結散布到外部管道

## Risks / Trade-offs

**風險 1：立委頁本身也可能被錯誤引用。**
「原住民 41% 投國民黨」是正確的，但它講的是**立委選舉中投給國民黨籍
候選人的比例**，不是政黨認同。候選人是誰、有沒有現任優勢、
選區只有一個席次——這些都會影響那個數字。
處置：頁面標題與圖表標題都寫「立委選舉的政黨得票率」，不寫「政黨支持度」。

**風險 2：三頁會讓讀者以為三個資料集可以互相比較。**
它們不是同一個母體。處置：每頁頂端固定一段「本頁是什麼、不是什麼」，
且不提供跨資料集的合併檢視。

**風險 3：分桶集合有兩套，會有人把它們搞混。**
地方公職三桶、立委五桶。處置：兩者都由腳本的單一常數宣告，
並在測試中斷言「兩個集合不相等」——若哪天被合併成一套，
那條會失敗而不是靜默地讓親民黨消失。

**取捨：主軸選立委而不是政黨票。**
政黨票更接近讀者真正想問的問題（政黨傾向），但它只涵蓋 11%。
選立委是拿「回答得比較窄」換「不會被錯誤引用」。
對研究者這個取捨可能相反——但讀者設定是一般讀者與媒體。
