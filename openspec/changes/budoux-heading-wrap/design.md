## Context

`docs/index.html`、`docs/legislative.html` 是靜態、自我完整的頁面：CSS 內嵌在各自的 `<style>` 區塊裡（不是共用檔案），JS 邏輯與資料常數也都內嵌，整個站台明確不連外部資源（見 `scripts/build_site_data.py` 檔頭說明）。這兩個頁面的 `<h1>`／`<h2>` 目前是人工寫死的中文純文字，其中 `index.html` 的 `<h1>` 已經有一個手動 `<br>`。

`scripts/build_site_data.py` 目前的職責是「讀長表算常數、就地替換 HTML 中對應的那一行」，本變更替它新增第二種職責：讀取標題純文字、算出語意分段、就地改寫該行的 HTML 內容。這跟原本的常數替換不是同一種操作（常數替換是整行找一個固定前綴後接 JSON 的樣式；這裡是替一段可能本來就含子標籤的文字插入 `<wbr>`），所以用獨立的函式處理，不與既有常數替換共用程式碼路徑。

## Goals / Non-Goals

**Goals:**
- 在 `docs/index.html`、`docs/legislative.html` 的每個 `<h1>`／`<h2>` 純文字內容中插入 BudouX 算出的語意斷詞點（`<wbr>`），並確保對應 CSS 讓斷詞點在任何寬度下都優先於瀏覽器預設的逐字斷行。
- 建置流程可重複執行（re-run `python scripts/build_site_data.py` 兩次結果一致，不會疊加插入 `<wbr>`）。
- 移除 `docs/index.html` `<h1>` 現有的手動 `<br>`，改由生成的 `<wbr>` 取代。

**Non-Goals:**
- 不處理英文頁面、不處理 `roster.html` 執行期動態產生的縣市名稱標題（詳見 proposal 的 Non-Goals，理由不重複）。
- 不改標題文案或版面樣式（字級、間距、配色）。
- 不引入前端執行期 JS 斷詞（BudouX 的 JS 版與模型檔不會出現在任何頁面的 `<script>` 裡）。

## Decisions

### 用 Python `budoux` 套件而非自製斷詞演算法

`budoux` 套件（PyPI，Apache-2.0）內建 `zh-hant`（繁體中文）模型，跟已在樣稿階段驗證過的 JS 版本同一套模型與同一套演算法，斷點結果可預期一致。自製一份斷詞邏輯要多維護一份繁體中文的分類權重資料且需要自行驗證跟官方套件行為是否一致，沒有對應的好處。代價是這是本專案第一個第三方 Python 依賴，因此需要新增 `requirements.txt`（目前不存在）。

### 插入時機：建置期一次性改寫，不是執行期動態插入

延續本專案既有「內嵌常數在建置期就地替換」的模式（見 `scripts/build_site_data.py` 檔頭），標題斷詞點在建置期算好、直接寫進靜態 HTML，執行期瀏覽器不需要載入任何斷詞邏輯或模型資料。相較於樣稿驗證過的「執行期 JS 插入」方案，這個方向零額外頁面重量、JS 關閉時仍正確、且跟本專案「不連外部資源、頁面自我完整」的既有設計原則更一致。

### 只處理 `<h1>`／`<h2>`，用純文字比對後就地替換該行

`build_site_data.py` 讀取整份 HTML 後，用正則表達式抓出 `<h1>...</h1>` 與 `<div class="sh">...<h2>...</h2></div>` 兩種既有樣式（`<h1>` 直屬純文字或既有的手動 `<br>`；`<h2>` 一律是純文字，不含子標籤——已用 `grep -n "<h1\|<h2" docs/index.html docs/legislative.html` 確認過所有既有標題都符合這兩種樣式），取出純文字（去除既有的 `<br>`），交給 `budoux` 斷詞，重新組回 `<h1>片段<wbr>片段...</h1>`／`<h2>...</h2>`，就地替換原本那一段。

### 冪等性：先算出「這個標題的目標 HTML」，比對後才寫入

不是「找到 `<wbr>` 就跳過整個檔案」這種粗略判斷（會在第二次執行時漏掉「新增了一個原本沒有的標題」的情境），而是每個標題都各自：純文字 → 跑 BudouX → 組出目標 HTML 字串 → 跟目前檔案中這個標題的 HTML 字串比較，相同則不動，不同才替換。這樣不論執行幾次，只要原始純文字不變，輸出就穩定不變。

### CSS 加在既有的 `h1{...}`／`h2{...}` 規則上，不新增選擇器

`docs/index.html`、`docs/legislative.html` 各自的 `<style>` 內都已有裸的 `h1{...}` 與 `h2{...}` 規則（例如 `docs/index.html` 第 52-53 行），直接在這兩條規則裡追加 `word-break:keep-all;overflow-wrap:anywhere`，不新增 `.sh h2` 這種更窄的選擇器，避免多一層特異性需要之後維護。

## Implementation Contract

**行為**：對 `docs/index.html`、`docs/legislative.html` 執行 `python scripts/build_site_data.py`（含 `--check`／`--write` 兩種既有模式）後：
- 每個 `<h1>`／`<h2>` 標籤內的可見文字（拿掉所有 `<wbr>`／`<br>` 之後）與變更前完全相同，一個字都不多不少。
- 若 BudouX 對該標題文字的斷詞結果多於一段，標籤內容含至少一個 `<wbr>`，且 `<wbr>` 只出現在 BudouX 回傳的分段邊界上。若斷詞結果只有一段（例如「性別」「席次」這種本來就不會跨行的短標題），允許沒有任何 `<wbr>`——這不是失敗，是正確行為。
- `docs/index.html` 的 `<h1>` 不再含手動寫死的 `<br>`。
- 兩個檔案各自的 `<style>` 區塊中，`h1{...}` 與 `h2{...}` 規則同時含 `word-break:keep-all` 與 `overflow-wrap:anywhere`。
- 連續執行兩次建置，第二次的 diff 為零（冪等）。

**介面**：`build_site_data.py` 新增一個函式（例如 `segment_headings(html: str) -> str`），輸入整份 HTML 字串、輸出替換過標題後的 HTML 字串；在既有的 `--write` 主流程中，對 `docs/index.html`、`docs/legislative.html` 各呼叫一次，寫回檔案。`--check` 模式下改為呼叫同一函式比對輸出是否與檔案現況一致，不一致則視為檢查失敗（沿用既有 `check_*` 函式「回傳問題描述字串、由呼叫端彙整」的慣例）。

**失敗模式**：若某個 `<h1>`／`<h2>` 的內容不符合「純文字或純文字加一個既有 `<br>`」這個既有樣式假設（例如含有除了 `<br>` 以外的子標籤），函式必須中止並拋出明確錯誤，指出是哪一行、哪個標籤——不可靜默略過或以原文字通過去。這跟本腳本檔頭承諾的「任何自我驗證未通過即中止，不產出半套結果」一致。

**驗收標準**：
- `scripts/test_build_site_data.py` 新增測試涵蓋：純文字不失真（新增測試逐一驗證每個標題去除 `<wbr>`／`<br>` 後等於原文字）、CSS 屬性存在、`docs/index.html` 不再含手動 `<br>`、對同一輸入重跑一次結果不變（冪等）。
- `scripts/mutate_build_site_data.py` 新增至少一項真檔變異（例如把某個 `<wbr>` 拿掉，或把 CSS 的 `word-break:keep-all` 拿掉），並證明對應測試會抓到。

**範圍邊界**：只動 `docs/index.html`、`docs/legislative.html` 的 `<h1>`／`<h2>`。不動這兩個檔案裡其他文字（`.sh` 內的 `<span class="sn">` 編號、內文段落、圖表 tooltip 文字等）。不動 `docs/en/*.html`、`docs/roster.html`。

## Risks / Trade-offs

[新增第三方 Python 依賴，跟專案現有「零依賴、只用標準庫」的慣例不同] → 這個依賴只在建置期執行，不影響站台本身「不連外部資源」的執行期承諾；`requirements.txt` 明確記錄唯一的依賴與版本，安裝成本很低（純 Python、無 C extension）。

[BudouX 的斷詞模型是訓練出來的統計結果，未來版本更新可能讓同一段文字的斷點跟現在不同] → 用 `requirements.txt` 釘住確切版本號，版本升級是有意識的操作而非建置時自動抓最新版；斷點跟現在不同不算錯誤（仍是合法語意邊界），但若要避免站台外觀無預警變動，之後升級版本時應人工比對輸出差異。

[未來若新增標題不符合「純文字或純文字加一個既有 `<br>`」的既有樣式（例如標題裡想放一個 `<span>` 強調字）] → Implementation Contract 明訂遇到不符合樣式時必須中止並報錯，不會靜默錯誤地把子標籤文字也丟給斷詞器，這個限制留給未來需要時再擴充函式支援範圍。
