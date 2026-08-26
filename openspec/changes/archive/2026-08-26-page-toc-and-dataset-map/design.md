## Context

`docs/index.html`（7 節）與 `docs/legislative.html`（5 節）都是只能靠捲動閱讀的長頁面，沒有頁內錨點或目錄。導覽列（`<nav class="nav">`）只列頁面連結，不說明三個資料集（地方公職、原住民立委、不分區政黨票界限估計）彼此的範圍差異。站台既有「靜態限定語必須與 `STRINGS` 逐字相同」的機制（`STATIC_QUALIFIERS`／`check_static_qualifiers()`），本次沿用同一種模式：內容手寫在 HTML 原始碼裡，用檢查釘住與 `STRINGS` 逐字相同、以及新結構（section id 與目錄）彼此一致。

## Goals / Non-Goals

**Goals:**
- 讓 `docs/index.html`、`docs/legislative.html`（及其英文版）的每節都有穩定 `id`，並在頁首提供可點擊跳轉的頁內目錄
- 讓五個已發布頁面（`index.html`／`roster.html`／`legislative.html`／`en/index.html`／`en/legislative.html`）都在導覽附近說明三個資料集彼此的範圍差異
- 新增自動化檢查，讓「目錄與實際 section 不一致」「資料集地圖文字漏掉或與 STRINGS 不同」都會讓 `--check`／`--write` 中止

**Non-Goals:**
- 不做捲動監測（scroll-spy）或任何 JS 高亮目前所在節——純錨點連結即可，JS 高亮不是本次要解決的問題，且會增加前端狀態複雜度
- 不改任何資料數字、不改既有「範圍」節的規範文字
- 不改 `docs/roster.html` 的頁內結構（它是單頁名錄，不加目錄，只加資料集地圖）
- 不新增資料集或頁面

## Decisions

### Section id 直接手寫在 HTML 原始碼裡，不由 build_site_data.py 動態產生
Section 的數量、順序、標題都是手寫內容（跟頁面其餘結構一樣），不是由資料驅動產生，所以 id 也手寫最直接。id 命名採用頁面既有的 `<span class="sn">` 代碼轉小寫英文短詞：
- `index.html`：`scope`／`turnout`／`party`／`gender`／`scale`／`perseat`／`custom`
- `legislative.html`：`scope`／`partyvote`／`seats`／`turnout`／`bounds`（`bounds` 已存在，沿用不改）
英文版 id 與中文版逐一對應相同字串（同一個錨點在兩版都能用同一個 URL fragment）。

**替代方案考慮過**：用數字流水號（`s1`／`s2`）——否決，因為新增或搬動一節時流水號要整批重新編號，而描述性 id 只要新節本身命名一次。

### 頁內目錄是手寫的 `<nav class="toc">`，用一致性檢查而非生成保證正確
目錄清單（`<a href="#id">標籤</a>`）手寫在 `<nav class="nav">` 之後，標籤文字取各節 `sn` 代碼＋簡短節名（不搬 `<h2>` 內含 `<wbr>` 的 BudouX 斷詞 HTML，避免目錄文字裡出現不必要的斷詞標記）。新增 `check_section_ids_match_toc()`：對每個列在 `TOC_PAGES` 的頁面，解析其 `<section id="...">` 的 id 序列與 `<nav class="toc">` 內 `href="#..."` 的 id 序列，兩者必須是**相同的集合且順序一致**；不一致（目錄連到不存在的 id、section 沒被目錄列到、順序被打亂）一律中止並具名頁面與差異。

**替代方案考慮過**：由 `build_site_data.py` 掃描 `<section>` 自動產生整段 `<nav class="toc">` 並在 `--write` 時插入——否決，因為目錄標籤文字需要人工判斷簡潔用詞（例如「04 規模、現任者與同額競選」節在目錄裡要縮寫成「規模」還是保留全名），這屬於編輯判斷而非機械轉換；改用一致性檢查以維持「內容手寫、結構被驗證」的既有模式（與 `STATIC_QUALIFIERS` 同一種取捨）。

### 資料集地圖是新的 `STRINGS["dataset_map"]` 鍵，跨五個頁面共用同一段文字
內容說明三個資料集（地方公職／原住民立委／不分區政黨票界限估計）各自涵蓋什麼、彼此不可比較，呼應 `site-multi-dataset` 能力既有 Requirement 的精神。中英文各一份，五個頁面各自的語言版本必須逐字相同（跟 `datasets_not_comparable` 目前的作法一樣），用新的 `DATASET_MAP_PAGES` 對映表 ＋ `check_dataset_map_present()` 驗證，函式簽名與排除 `<script>` 區塊的邏輯直接沿用 `check_static_qualifiers()` 的既有模式（同一份 `STRINGS`、同一種「頁面上的字，不是 `T` 常數裡的字」判準）。

**替代方案考慮過**：五頁各自客製一段話（例如 index.html 說「你在地方公職頁」、legislative.html 說「你在立委頁」）——否決，會員需要五份互相同步的文字，任何一頁改了措辭而漏改其他頁，檢查如果只驗「內容存在」不驗「五頁相同」就抓不到；而且本次目標是讓讀者知道**還有哪些資料集**，不是自我介紹目前在哪一頁（`aria-current="page"` 已經做了那件事）。

## Implementation Contract

**行為**：讀者打開 `docs/index.html` 或 `docs/legislative.html`（含英文版）時，`<h1>`／`<nav class="nav">` 之後會看到一段可點擊的頁內目錄，點擊任一項會跳轉到對應 `<section>`；五個已發布頁面的導覽附近都會看到一段說明三個資料集範圍差異的文字。

**資料形狀**：
- `scripts/build_site_data.py` 新增 `STRINGS["dataset_map"]`：`{"zh": <str>, "en": <str>}`，透過既有 `check_strings_complete()` 一併驗證兩語言都有值
- 新增 `DATASET_MAP_PAGES: dict[str, str]`（頁面相對路徑 → 語言碼），五個鍵：`index.html`／`roster.html`／`legislative.html`／`en/index.html`／`en/legislative.html`
- 新增 `TOC_PAGES: dict[str, tuple[str, ...]]`（頁面相對路徑 → 該頁 section id 的期望順序），四個鍵：`index.html`／`legislative.html`／`en/index.html`／`en/legislative.html`
- 四個 HTML 檔各自的 `<section>` 加上前述 id；四個檔各自在 `<nav class="nav">` 之後手寫 `<nav class="toc">`，內含對每個 section 的 `<a href="#id">`
- 五個 HTML 檔各自在導覽附近手寫資料集地圖段落，文字與 `STRINGS["dataset_map"][lang]` 逐字相同

**失敗模式**：
- `check_dataset_map_present()`：任一列在 `DATASET_MAP_PAGES` 的頁面缺少對應語言的資料集地圖文字 → `SiteDataError`，具名頁面
- `check_section_ids_match_toc()`：任一列在 `TOC_PAGES` 的頁面，其 `<section id>` 序列與 `<nav class="toc">` 的 `href` 序列不一致（多、少、順序不同）→ `SiteDataError`，具名頁面與差異（哪些 id 只在其中一邊出現）

**驗收標準**：
- `python scripts/build_site_data.py --check` 與 `--write` 都通過，且印出對應的確認訊息（沿用既有 `print("✓ ...")` 慣例）
- `scripts/test_build_site_data.py` 新增至少兩組合成測試（`check_dataset_map_present` 缺文字時中止、`check_section_ids_match_toc` 目錄與 section 不一致時中止），並各自有一段對真實 `docs/` 的驗證
- `scripts/mutate_build_site_data.py` 為兩個新檢查各補至少一則真實檔案變異，確認變異會被對應測試抓到
- Playwright 截圖確認目錄可點擊跳轉、資料集地圖文字可見

**範圍邊界**：
- 範圍內：`docs/index.html`／`docs/legislative.html`／`docs/roster.html`／`docs/en/index.html`／`docs/en/legislative.html`、`scripts/build_site_data.py`、`scripts/test_build_site_data.py`、`scripts/mutate_build_site_data.py`
- 範圍外：不改 `docs/sitemap.xml`、不改任何資料數字、不改既有「範圍」節文字、不做捲動監測 JS、不新增頁面或資料集

## Risks / Trade-offs

[目錄手寫可能與實際 section 順序脫節] → `check_section_ids_match_toc()` 在 `--check`／`--write` 都會跑，脫節會直接中止建置，不會靜默通過
[五頁的資料集地圖文字未來各自被改順但改弱（跟 1k 的教訓同類）] → 沿用 `check_static_qualifiers()` 已驗證過的「逐字比對 STRINGS」機制，而不是只驗「有沒有提到資料集」這種弱檢查
[錨點連結在窄螢幕或列印時的可及性] → 用原生 `<a href="#id">`，不依賴 JS，鍵盤與螢幕報讀器都能操作；不在本次新增額外樣式驗證，行為由瀏覽器原生錨點跳轉保證
