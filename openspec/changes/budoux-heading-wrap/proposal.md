## Why

站台中文頁面（`docs/index.html`、`docs/legislative.html`）的標題文字沒有空白可供瀏覽器判斷語意斷詞，窄螢幕下會把「投票率」「推到」這類本該是一個詞的片語從中間切開跨行顯示。目前唯一已知案例是 `docs/index.html` 的 `<h1>` 手動插入了一個 `<br>` 釘死斷點，但這只對單一寬度有效，換一個視窗寬度該手動斷點本身也可能造成新的斷詞問題；其餘 `<h2>` 完全沒有防護。這個問題在改版樣稿（不在本專案 git 內、僅為 Claude Artifact）階段已用 BudouX（Google 的中文語意斷詞工具）＋ CSS `word-break:keep-all`／`overflow-wrap:anywhere` 驗證過修法，此變更把它搬進正式建置流程。

## What Changes

- `scripts/build_site_data.py` 新增一個建置期步驟：讀取 `docs/index.html`、`docs/legislative.html` 的 `<h1>`／`<h2>` 純文字內容，用 `budoux` 套件（Python，`zh-hant` 模型）算出語意分段，在段落之間插入 `<wbr>`，就地改寫該行 HTML。
- 既有 `docs/index.html` 的 `<h1>` 手動 `<br>` 一併移除，改由 BudouX 產生的 `<wbr>` 取代（驗證兩者在該標題文字上的斷點是否等價或至少同樣合理）。
- 站台 CSS（zh 頁面共用樣式）替 `h1`、`.sh h2` 選擇器加上 `word-break: keep-all` 與 `overflow-wrap: anywhere`，確保 `<wbr>` 真正生效、不被瀏覽器預設逐字斷行規則蓋過。
- `requirements.txt`（新檔案，本專案目前完全沒有第三方 Python 依賴）新增 `budoux`。
- `docs/en/index.html`、`docs/en/legislative.html`、`docs/roster.html` 不在本次範圍內：英文本身以空白斷詞，瀏覽器原生行為已經正確；`roster.html` 的 `<h2>` 是 JS 在瀏覽器端用縣市名稱動態產生（`docs/roster.html:317`），縣市名固定 2-4 個中文字，不會有跨行風的斷詞問題，且屬於執行期產生而非建置期靜態文字，套用建置期方案的方式不同，留待未來需要時另案處理。
- `scripts/test_build_site_data.py` 新增測試，驗證：(1) 所有 zh 頁面 `<h1>`／`<h2>` 的文字內容都含至少一個 `<wbr>`（若原文語意分段結果只有一段則允許零個 `<wbr>`，測試需針對這個邊界情況個別確認）；(2) CSS 中 `word-break: keep-all` 與 `overflow-wrap: anywhere` 同時作用於 `h1` 與 `.sh h2`；(3) 插入 `<wbr>` 後每個標題的可見文字（去除 `<wbr>`／`<br>` 標籤）與原文字完全相同，不遺失、不重複任何字元。
- `scripts/mutate_build_site_data.py` 新增至少一項真檔變異，證明上述測試在斷詞邏輯被破壞（例如漏插 `<wbr>`、CSS 屬性被拿掉）時會失敗。

## Non-Goals

- 不處理英文頁面（`docs/en/*.html`）：英文原生依空白斷行，沒有這個問題。
- 不處理 `docs/roster.html` 由 JS 在執行期動態產生的縣市名稱標題：縣市名稱固定 2-4 字不會有斷詞需求，且屬於執行期而非建置期產生的文字，機制不同。
- 不在前端載入 BudouX 的 JavaScript 版本或其斷詞模型檔：本變更明確選擇建置期（Python）方案，不引入任何前端執行期 JS 依賴或額外頁面重量。
- 不重新設計標題文案或版面（字級、間距、配色等）：純粹是斷行正確性的修正，不是本次美化改版討論的一部分。

## Capabilities

### New Capabilities

- `site-heading-segmentation`：建置期用 BudouX 替中文頁面的靜態標題（`<h1>`／`<h2>`）插入語意斷詞點，並搭配 CSS 屬性使斷詞點在窄螢幕下真正生效。

### Modified Capabilities

(none)

## Impact

- Affected specs: `site-heading-segmentation`（新增）
- Affected code:
  - New: `requirements.txt`
  - Modified: `scripts/build_site_data.py`, `docs/index.html`, `docs/legislative.html`, `scripts/test_build_site_data.py`, `scripts/mutate_build_site_data.py`
  - Removed: (none)
