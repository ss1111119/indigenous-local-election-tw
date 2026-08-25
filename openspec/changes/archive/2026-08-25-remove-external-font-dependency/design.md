## Context

五個頁面的 CSS 與內嵌 JS 對 `font-family` 的寫法已經全部帶有可用的通用或
系統字型作為 fallback（例如 `font-family:"Noto Sans TC",-apple-system,
"Segoe UI",sans-serif`、`font-family:"IBM Plex Mono",ui-monospace,
monospace`），只是排在具名字型之後。這代表拿掉具名字型不需要重新設計
字型堆疊，只需要移除堆疊裡指向 Google Fonts 的那一段，其餘 fallback
原樣保留。

已逐檔核對過三種 `font-family` 出現形式，都要處理：
1. CSS 屬性寫法：`font-family:"字型名",其餘堆疊`（`docs/index.html`、
   `docs/roster.html`、`docs/legislative.html` 及其英文版皆有）。
2. JS 內嵌 SVG 屬性，無空白：`"font-family":"IBM Plex Mono, monospace"`
   （只出現在 `docs/index.html`、`docs/en/index.html`，各 5 處）。
3. JS 內嵌 SVG 屬性，冒號後有空白：
   `"font-family": "IBM Plex Mono, monospace"`（只出現在
   `docs/legislative.html`、`docs/en/legislative.html`，各 5 處）。
`docs/roster.html` 沒有第 2、3 種形式。

已核對過站台目前唯一非字型的外部樣式資源是
`document.createElementNS("http://www.w3.org/2000/svg", n)`——這是 SVG
規格要求的固定命名空間 URI 字串，瀏覽器不會對它發出網路請求，新檢查
必須明確排除這個字串，否則會誤判。

## Goals / Non-Goals

**Goals:**
- 五個頁面不再對外連線（Google Fonts 或其他任何外部主機）。
- 拿掉具名字型後，`font-family` 堆疊仍保有至少一個通用或系統字型關鍵字，
  不會出現空堆疊或语法錯誤。
- 新增的外部資源檢查具備真正的辨識力，且不會誤判 SVG 命名空間 URI。

**Non-Goals:**
- 不改變非字型相關的視覺樣式。
- 不自行代管字型檔案。

## Decisions

### CSS 的具名字型直接刪除該段落＋逗號，不改寫整條宣告

例如 `font-family:"Noto Sans TC",-apple-system,"Segoe UI",sans-serif`
改為 `font-family:-apple-system,"Segoe UI",sans-serif`；
`font-family:"Noto Sans TC",sans-serif` 改為 `font-family:sans-serif`；
`font-family:"Noto Serif TC",serif` 改為 `font-family:serif`；
`font-family:"IBM Plex Mono",ui-monospace,monospace` 改為
`font-family:ui-monospace,monospace`；`font-family:"IBM Plex Mono",
monospace` 改為 `font-family:monospace`。逐一手動核對每個出現位置的
上下文字串後再替換，不用會影響到不相關程式碼的寬鬆正則表達式。

### JS 內嵌的 SVG `font-family` 屬性字串內部也拿掉具名字型

`"font-family":"IBM Plex Mono, monospace"` 改為
`"font-family":"monospace"`（`docs/index.html`、`docs/en/index.html`）；
`"font-family": "IBM Plex Mono, monospace"` 改為
`"font-family": "monospace"`（`docs/legislative.html`、
`docs/en/legislative.html`，保留原本冒號後的空白，維持該檔案既有的
格式風格、不引入不必要的格式差異）。

### 新檢查函式直接讀取 `docs/` 底下每個 `.html` 檔案的完整內容找外部參照

比對邏輯：對每個 `.html` 檔案的內容，用正則表達式找出所有
`https?://[^\s"'<>]+` 這種形式的子字串，逐一排除等於
`http://www.w3.org/2000/svg`（SVG 命名空間 URI，字串完全相等才排除，
不是子字串包含）的項目，剩下的任何一個都視為外部資源參照、觸發中止。
函式命名 `check_no_external_resources()`，比照既有 `check_*` 函式
無參數、找到問題就拋 `SiteDataError` 的慣例。

### 檢查放在 `main()` 既有的內容面檢查區塊，`--check` 與 `--write` 都跑

依循既有慣例（`check_static_qualifiers()`／`check_current_term_notice()`
所在的 `if args.write or args.check:` 區塊），因為這是驗證「已經存在的
靜態內容」不含外部參照，跟建置期算出的常數無關。

## Implementation Contract

**行為**：執行 `python scripts/build_site_data.py --check` 或 `--write`
時：
- 讀取 `docs/` 目錄下（含 `docs/en/`）每一個 `.html` 檔案，若任一檔案
  含有 `http://` 或 `https://` 開頭、且不等於
  `http://www.w3.org/2000/svg` 的字串，流程中止並拋出 `SiteDataError`，
  訊息指名是哪個檔案、找到的外部參照字串是什麼。
- 若所有檔案都不含這類字串，檢查通過、流程正常繼續。
- 五個既有頁面（`docs/index.html`、`docs/roster.html`、
  `docs/legislative.html`、`docs/en/index.html`、
  `docs/en/legislative.html`）本身，套用這個檢查後應該通過（因為
  Google Fonts 連結已經移除）。

**介面**：`scripts/build_site_data.py` 新增
`check_no_external_resources() -> None`，無參數、無回傳值，比照既有
`check_*` 函式失敗時拋 `SiteDataError` 的慣例。加進 `main()` 既有的
`if args.write or args.check:` 區塊。

**失敗模式**：任一 `.html` 檔案含非 SVG 命名空間 URI 的 `http(s)://`
字串 → `SiteDataError`，訊息含檔名與該字串。

**驗收標準**：
- `scripts/test_build_site_data.py` 新增測試，構造一個含合法外部資源
  參照（例如假的 `<script src="https://example.com/x.js">`）的暫存
  HTML 檔案，斷言 `check_no_external_resources()` 對它拋出
  `SiteDataError`；再構造一個只含 SVG 命名空間 URI（`http://www.w3.org
  /2000/svg`）而沒有其他外部參照的暫存 HTML 檔案，斷言不拋例外——證明
  這個檢查真的會分辨兩者，不是「看到 http 就一律中止」這種寬鬆到連
  SVG 命名空間都擋下來的誤判版本。
- 對真實的 `docs/` 執行 `python scripts/build_site_data.py --check`，
  新檢查通過，且既有的所有檢查都不受影響。
- 用瀏覽器實際開啟五個頁面，`Network` 面板確認沒有對
  `fonts.googleapis.com`／`fonts.gstatic.com` 的請求。

**範圍邊界**：只動五個頁面裡跟 Google Fonts／`font-family` 具名字型
有關的部分，以及新增的外部資源檢查本身。不動任何其他視覺樣式、不動
非字型的 JS 邏輯。
