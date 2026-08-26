## Context

「政黨傾向」這個詞在頁面**內文**是合法且必要的用法——`docs/legislative.html`
第 194 行「真正接近『政黨傾向』的是不分區政黨票」與 `const T` 裡
`bounds_qual` 的限定語「不是全體原住民的政黨傾向」，都是在明確劃清界線、
告訴讀者「這才是政黨傾向、其他數字不是」，跟導覽標籤／標題把它當成
整個頁面的定性完全是相反的用法。已用 `grep -c` 確認這兩處合法用法目前
存在，新檢查不能把它們也擋下來。

## Goals / Non-Goals

**Goals:**
- 導覽標籤與 `<h1>` 不再用「政黨傾向」「政黨版圖」這種暗示比資料能撐起
  的宣稱更強的說法。
- 內文裡正確、限定式地使用「政黨傾向」一詞（用來劃清界線，不是定性）
  不受影響、不被誤判。

**Non-Goals:**
- 不改內文限定語本身的文字。
- 不改版面結構、不改資料內容。

## Decisions

### 檢查只掃描 `<nav ...>...</nav>` 與 `<h1>...</h1>` 這兩個區塊，不是整份檔案

用正則表達式先擷取這兩個元素各自的內容子字串，只在子字串裡找禁用詞。
這樣第 194 行的限定句與 `const T` 裡的 `bounds_qual` 字串（都在
`<nav>`／`<h1>` 之外）不會被誤判，同時仍然擋得住「有人把導覽標籤或
標題改回舊說法」這個真正要防的情況。

### 禁用詞清單：中英各兩個，一次性宣告在檢查函式旁

`("政黨傾向", "政黨版圖", "party leaning", "Party Politics")`——直接寫在
函式定義旁的模組層級常數，理由與行為都在同一個地方，之後要調整禁用詞
不必去別的地方找。

### 中文標題文案：呼應頁面內第 01 節既有用詞，不是重新發明說法

`docs/legislative.html` 第 01 節標題已經是「立委選舉的政黨得票率」，
`<h1>` 改成「原住民立委九屆的政黨得票率」直接沿用這個已經存在、
已經通過語意斷詞驗證的說法，不引入第三種措辭。

## Implementation Contract

**行為**：執行 `python scripts/build_site_data.py --check` 或 `--write`
時：
- 讀取 `docs/index.html`、`docs/roster.html`、`docs/legislative.html`、
  `docs/en/index.html`、`docs/en/legislative.html` 五個檔案，各自擷取
  `<nav ...>...</nav>` 與（若存在）`<h1>...</h1>` 的內容，若任一段含
  「政黨傾向」「政黨版圖」「party leaning」「Party Politics」這四個
  禁用詞其中之一，流程中止並拋出 `SiteDataError`，訊息指名是哪個檔案、
  哪個區塊（導覽或標題）、找到哪個禁用詞。
- 五個頁面本身（改完文案之後）套用這個檢查應該通過。
- 頁面內文（`<nav>`／`<h1>` 以外的地方）出現「政黨傾向」不受這個檢查
  影響，不會被誤判為違規。

**介面**：`scripts/build_site_data.py` 新增
`check_no_overclaiming_labels() -> None`，無參數、無回傳值，比照既有
`check_*` 函式失敗時拋 `SiteDataError` 的慣例。加進 `main()` 既有的
`if args.write or args.check:` 區塊。

**失敗模式**：`<nav>` 或 `<h1>` 含禁用詞其中之一 → `SiteDataError`，
訊息含檔名、區塊名稱（`nav` 或 `h1`）、找到的禁用詞。

**驗收標準**：
- 新增合成測試，構造一段含 `<nav>立委與政黨傾向</nav>` 的暫存 HTML，
  斷言 `check_no_overclaiming_labels()` 對它拋出例外；再構造一段
  `<nav>立委選舉</nav><p>真正的政黨傾向在別的地方</p>` 的暫存 HTML，
  斷言不拋例外（證明內文合法用法不受影響）。
- 對真實的五個頁面執行 `python scripts/build_site_data.py --check`，
  新檢查通過，且既有的所有檢查都不受影響。
- `grep -c "立委與政黨傾向\|政黨版圖" docs/index.html docs/roster.html
  docs/legislative.html docs/en/index.html docs/en/legislative.html`
  每個檔案在 `<nav>`／`<h1>` 範圍內都回傳 0（允許內文範圍內仍有合法
  出現，這一步只人工確認，不是自動化斷言）。

**範圍邊界**：只動導覽標籤與 `<h1>` 這兩處文案本身，以及新增的檢查。
不動內文限定語、不動版面結構。
