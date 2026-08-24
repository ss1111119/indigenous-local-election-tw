## Why

站台三頁全部只有中文（`lang="zh-Hant"`）。要讀懂原住民立委九屆的政黨版圖或
政黨傾向界限，目前必須讀中文。唯一已經是英文的是主 spec，而那是 Spectra
的規範性語言要求，不是為了讀者。

文案量不大——三頁合計約 5,400 個中文字（HTML 內文 3,660、JS 裡的圖表標籤與
限定語 1,724）。**真正的成本在維護**：這個專案的主要價值是限定語
（涵蓋率 11.0%、「不是全體原住民」、「這不等於政黨認同」、
「三個資料集不可互相比較」），而限定語一旦有兩份就會漂移。
本 repo 已經因為「同一個規則在兩處各有一份實作」出過兩個 bug
（名錄的 `MAIN` 手寫一份、政黨分桶只認一種名稱）。

## What Changes

- 新增 `docs/en/index.html` 與 `docs/en/legislative.html`，資料常數與**限定語**
  皆由 `scripts/build_site_data.py` 產生，中英各一組標記行。
- 新增能力 `site-translation`：規範「翻譯不得弱化限定語」與
  「顯示標籤的英譯須逐項宣告並註明來源」。
- 選舉種類名稱（11 個）與政黨名稱的英譯做成宣告表，逐項標明是中選會英文站
  的用法或本專案自訂。⚠️ 中選會英文站的頁面是 JS 渲染的，抓不到本文；
  可查證的用法來自搜尋摘要（"Lowland/Highland Indigene Legislator"），
  不足的部分一律標為本專案自訂。
- 中英頁面互相 `hreflang`；`docs/sitemap.xml` 補兩個網址。
- 兩個英文頁各自在 `docs/發布判定紀錄.md` 加一列——這不是額外要求，
  `check_publication_record()` 會直接中止。

## Non-Goals

- **不做 `roster.html` 的英文版。** 它有 4,607 位候選人姓名與 27 個選舉區名稱，
  那是音譯工程不是翻譯：臺灣的人名羅馬拼音有威妥瑪／漢語／通用數套並存，
  原住民候選人另有族語名與漢名的問題，本專案沒有權威來源可以決定每個人的
  名字怎麼拼，而猜出來的拼法會被當成那個人的英文名。該頁對英文讀者的價值
  也最低（它是查詢工具，不是敘事）。
- **不英文化長表的欄位名。** `當選`、`選舉種類`、`鄉鎮市區_正規化` 等維持中文。
  那等於第二套 schema，量級完全不同。
- **不新增任何指標。** 依 `election-period-publication`，現在是選舉期間；
  翻譯既有的凍結歷史數據不算新增，但英文頁一樣受凍結約束、
  一樣要帶本屆限定語的英文版。
- 不改任何資料、不重建任何長表、不重算任何數字。

## Capabilities

### New Capabilities

- `site-translation`: 翻譯版頁面的限定語來源、標籤英譯的宣告與出處、
  以及「翻譯不得弱化限定語」如何被檢查

### Modified Capabilities

- `site-data-generation`: 產生器現在要寫入多語版本的頁面，
  同一份資料常數餵給不只一個語言的頁面

## Impact

- Affected specs: `site-translation`（新增）、`site-data-generation`（修改）
- Affected code:
  - New: `docs/en/index.html`、`docs/en/legislative.html`、
    `openspec/specs/site-translation/spec.md`
  - Modified: `scripts/build_site_data.py`、`scripts/test_build_site_data.py`、
    `scripts/mutate_build_site_data.py`、`docs/index.html`、
    `docs/legislative.html`、`docs/sitemap.xml`、`docs/發布判定紀錄.md`、
    `README.md`
  - Removed: （無）
