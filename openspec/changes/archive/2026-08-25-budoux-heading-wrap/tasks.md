## 1. 依賴與斷詞函式

- [x] 1.1 新增 `requirements.txt`（本專案第一個第三方 Python 依賴），釘住確切版本，依循設計決定「用 Python `budoux` 套件而非自製斷詞演算法」：內容為 `budoux==<目前 PyPI 上的最新穩定版本號>`。驗證：`pip install -r requirements.txt` 成功，`python -c "import budoux; budoux.load_default_japanese_parser"`（確認套件可匯入且含 `zh-hant` 模型載入介面）不拋例外。
- [x] 1.2 在 `scripts/build_site_data.py` 新增函式（例如 `segment_headings(html: str) -> str`），依「只處理 `<h1>`／`<h2>`，用純文字比對後就地替換該行」的設計，抓出 `<h1>...</h1>` 與 `<h2>...</h2>` 區塊、取出純文字（若含既有 `<br>` 先移除）、交給 `budoux` 的 `zh-hant` 模型斷詞、以 `<wbr>` 重新組回。實作 Requirement「Semantic word-break points for static Chinese headings」的三個正常情境（多段語意、單段語意、既有手動 `<br>` 被取代）。驗證：新增 `scripts/test_build_site_data.py` 單元測試，對 `docs/index.html` 目前的 `<h1>` 文字（含既有 `<br>`）與 `docs/legislative.html` 的 `<h2>「立委選舉的政黨得票率」` 分別呼叫該函式，斷言輸出中把 `<wbr>`／`<br>` 全部拿掉之後的純文字與原文字逐字元相同。
- [x] 1.3 讓 `segment_headings` 在遇到 `<h1>`／`<h2>` 內含 `<br>` 以外的子標籤時中止並拋出例外，訊息含檔名與該標題的原始文字，實作 Requirement「Semantic word-break points for static Chinese headings」的「Unsupported heading markup aborts the build」情境。驗證：新增測試，餵一段人工建構的 `<h2>前<span>中</span>後</h2>` 字串進 `segment_headings`，斷言拋出例外且例外訊息包含該標題文字。

## 2. 套用到兩個中文頁面並確保冪等

- [x] 2.1 在 `scripts/build_site_data.py` 既有的 `--write` 主流程中，依循設計決定「插入時機：建置期一次性改寫，不是執行期動態插入」，對 `docs/index.html`、`docs/legislative.html` 各呼叫一次 `segment_headings` 並寫回檔案；`--check` 模式改為呼叫同一函式比對輸出是否已與檔案現況一致，不一致視為檢查失敗（沿用既有 `check_*` 函式的錯誤回報慣例）。實作 Requirement「Scope limited to static Chinese page headings」：確認流程中沒有對 `docs/en/index.html`、`docs/en/legislative.html`、`docs/roster.html` 呼叫這個函式。驗證：跑 `python scripts/build_site_data.py --write`，用 `git diff --stat` 確認只有 `docs/index.html`、`docs/legislative.html` 被改動；新增測試斷言 `docs/en/index.html`、`docs/en/legislative.html`、`docs/roster.html` 執行前後內容不變。
- [x] 2.2 確保連續執行兩次 `python scripts/build_site_data.py --write` 之後，第二次相對第一次的輸出沒有任何差異，依循設計決定「冪等性：先算出「這個標題的目標 HTML」，比對後才寫入」，實作 Requirement「Idempotent heading rewrite」。驗證：新增測試，對同一段標題 HTML 連續呼叫 `segment_headings` 兩次，斷言第二次的輸出字串與第一次逐字元相同；並在本機手動跑兩次 `--write` 後執行 `git diff docs/index.html docs/legislative.html` 確認第二次無變更。
- [x] 2.3 移除 `docs/index.html` `<h1>` 目前手動寫死的 `<br>`，改由 `segment_headings` 產生的 `<wbr>` 取代，實作 Requirement「Semantic word-break points for static Chinese headings」的「Existing manual line break is replaced」情境。驗證：跑過 `--write` 後，`grep -n "<br>" docs/index.html` 在 `<h1>` 那一行沒有比對結果；新增測試斷言該 `<h1>` 的輸出不含 `<br>` 字串。

## 3. CSS 與跨寬度驗證

- [x] 3.1 在 `docs/index.html`、`docs/legislative.html` 各自 `<style>` 區塊既有的 `h1{...}` 與 `h2{...}` 規則中追加 `word-break:keep-all;overflow-wrap:anywhere`，依「CSS 加在既有的 `h1{...}`／`h2{...}` 規則上，不新增選擇器」的決定，不新增 `.sh h2` 等額外選擇器，實作 Requirement「CSS enforces the semantic break points at all widths」。驗證：新增測試，對兩個檔案的 `<style>` 內容做正則比對，斷言 `h1{...}` 與 `h2{...}` 規則字串中同時含 `word-break:keep-all` 與 `overflow-wrap:anywhere`。
- [x] 3.2 用瀏覽器（headless Chrome 或既有的 playwright 驗證方式）在窄視窗（例如 400px 寬）分別渲染 `docs/index.html`、`docs/legislative.html`，確認每個因換行而跨行顯示的標題，其斷行位置都落在 `segment_headings` 產生的 `<wbr>` 上，沒有任何標題在 BudouX 判定的同一語意片段中間斷行，實作 Requirement「Narrow viewport does not split a semantic chunk」情境。驗證：截圖或用 DOM 查詢確認斷行點；記錄哪些標題在 400px 下有跨行（若沒有任何標題跨行，記錄為「本次視窗寬度下沒有可驗證案例」，不可視為情境已驗證通過）。

## 4. 變異測試

- [x] 4.1 在 `scripts/mutate_build_site_data.py` 新增一項真檔變異：把 `docs/index.html` 或 `docs/legislative.html` 某個標題輸出中的一個 `<wbr>` 拿掉，證明任務 1.2／2.1 新增的純文字比對測試會抓到（純文字比對本身不會抓到，需搭配一個直接斷言「此標題含 N 個 `<wbr>`」的測試）。驗證：先新增一個斷言特定標題 `<wbr>` 數量的測試，用 `mutate_real_html()` 手動套用此變異、確認該測試由通過變成失敗，再撤銷變異、確認測試恢復通過。
- [x] 4.2 在 `scripts/mutate_build_site_data.py` 新增一項真檔變異：把 `docs/index.html` 的 `h1{...}` 規則中的 `word-break:keep-all` 拿掉，證明任務 3.1 新增的 CSS 測試會抓到。驗證：手動套用此變異、確認 CSS 測試由通過變成失敗，再撤銷變異、確認測試恢復通過；並將此變異併入 `mutate_build_site_data.py` 的真檔變異迴圈中，跑一次完整變異套件確認全數變異都被抓到。
