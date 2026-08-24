## Context

站台的圖表互動全部依賴滑鼠：`bind()` 只綁 `pointerenter`／`pointermove`／
`pointerleave`，隱形的 hit target（`<circle r="14" fill="transparent">`
一類的元素）沒有 `tabindex`，鍵盤使用者 Tab 不到、螢幕閱讀器也讀不到內容。
`roster.html` 早已支援 `#屆別/代碼` 的網址雜湊定位（`readHash()`／
`writeHash()`），但 `index.html` 的圖表沒有任何元素連過去。

2026-08-24 與 Codex、Antigravity 分別討論後的共同結論：互動性的安全邊界是
「篩選、定位、可及性」，跨過去變成「讀者自選欄位算比值」就是在前端產生
新的解讀性指標，違反 `election-period-publication`。

## Goals / Non-Goals

**Goals:**

- 01 投票率折線圖與 02 政黨席次堆疊條的每個資料點／區段，鍵盤與滑鼠都能觸發
  同一件事：導向 `roster.html` 對應的屆別與選舉種類
- 既有的 hover tooltip 內容，鍵盤使用者也能取得（不是「另外做一份」，
  是同一個 `bind()` 機制對 focus 也生效）
- 中英兩版的 JS 保持逐位元組相同（`site-translation` 既有規則）

**Non-Goals:**

- 不做圖例與資料點互相高亮
- 不做 03 性別方格圖、04 規模表的點擊導航
- 不做任何新計算、新比值、新指標
- 不修改 `roster.html`——它的雜湊定位能力已經存在

## Decisions

### 決策 1：`bind()` 同時處理 hover 與 focus，不是另外寫一套

`bind()` 目前只認 `pointerenter`／`pointermove`／`pointerleave`。改為：
`pointerenter`／`focus` 共用顯示邏輯，`pointerleave`／`blur` 共用隱藏邏輯，
`pointermove` 只在指標裝置上跟著游標、focus 時 tooltip 固定在該元素旁。

**替代方案**：獨立寫一套鍵盤專用的資訊面板。否決——那是「同一個規則兩處
實作」的翻版，本專案已經因為這個模式出過兩次 bug（名錄 `MAIN` 手寫、
政黨分桶只認一種名稱），這次直接讓同一段程式碼服務兩種輸入。

### 決策 2：可導航的 hit target 用 `<a>` 包 SVG 元素，不是 JS 監聽 click 再手動導頁

投票率的 hit target 與政黨席次的區段，改成 `<a href="roster.html#{year}/{code}">`
包住原本的圖形元素。瀏覽器原生就會讓它可 Tab、可 Enter 觸發、可跳出分頁
另開、可長按複製連結。

**替代方案**：保留 `<circle>`／`<rect>`，加 `tabindex="0"` 與
`addEventListener("keydown", ...)` 手動判斷 Enter/Space 再用
`location.href` 導頁。否決——那要自己重新實作瀏覽器對 `<a>` 免費提供的
一整組行為（新分頁開啟、複製連結、螢幕閱讀器的「連結」語意），
且容易漏掉某個鍵盤事件分支。

### 決策 3：立委頁只做鍵盤可達性，不做導航

`legislative.html` 的 tooltip 觸發元素同樣改用 `bind()` 的 focus 支援，
但**不包 `<a>`**——立委資料（`L2`／`L3`）沒有對應的名錄頁可以連過去，
硬要導航會導向一個不存在或語意不符的頁面。

**替代方案**：導向 `index.html` 或 `legislative.html` 自己的表格區塊
（錨點連結）。否決——那不是「巨觀連結微觀」，只是原地跳轉，價值有限，
且會讓「圖表可點擊」這件事在兩個頁面上代表不同意思，讀者無法預期。

### 決策 4：英文頁的連結目標固定指向中文版 `roster.html`

`en/index.html` 的圖表連到 `../roster.html#{year}/{code}`——名錄沒有
英文版（`site-translation` 已定案），這與頁首導覽「Roster (Chinese only)」
是同一個既有決定，不是本變更新開的先例。

## Implementation Contract

**Behavior**

- `index.html`／`en/index.html` 的投票率資料點與政黨席次區段，滑鼠點擊、
  Tab 後按 Enter，或觸控點按，三種輸入都導向 `roster.html#{year}/{code}`
  （英文頁固定 `../roster.html#{year}/{code}`）。
- 同一個元素 hover 或 focus 時都顯示原本的 tooltip 文字，內容不變。
- `legislative.html`／`en/legislative.html` 的 tooltip 觸發元素可用 Tab
  到達並顯示內容，但不導航到任何頁面。

**Interface / data shape**

- `bind(el, text)` 簽名不變，內部改為監聽
  `["pointerenter", "focus"]` 與 `["pointerleave", "blur"]` 兩組事件。
- 可導航的 hit target 改用 `svgEl("a", {href: ..., "aria-label": ...})`
  包住原本的透明 hit 元素，`<a>` 需要 `xlink:href` 相容性只在 SVG 1.1
  情境需要——本專案的 SVG 內嵌於 HTML5，用 `href` 屬性即可，不需要
  `xlink` 命名空間。

**Failure modes**

- 若某個資料點對應的 `(year, code)` 組合在 `roster.html` 的 `D.years`
  或 `D.types` 找不到（理論上不會發生，因為兩份長表同源），連結仍會
  產生但導向一個 `readHash()` 讀不到值、退回預設畫面的雜湊——
  不視為需要中止建置的錯誤，但驗收條件要求兩份資料源本來就必須同源，
  所以測試改為斷言「兩邊的 (year, type) 集合相等」，而不是逐一驗證連結。

**Acceptance criteria**

- `pytest scripts/test_build_site_data.py` 通過，新增檢查不少於 6 項
- 變異測試新增至少 3 項並全數偵測：
  1. 拿掉 `bind()` 的 focus 監聽（只留 pointerenter）
  2. 可點擊的 hit target 改回普通 `<circle>`（拿掉 `<a>` 包裝）
  3. 立委頁被誤加上導航連結（違反決策 3）
- 手動以鍵盤（不用滑鼠）在瀏覽器中操作：Tab 能到達每個資料點、Enter
  能跳轉、跳轉後的雜湊與滑鼠點擊產生的一致
- `python scripts/build_site_data.py --check` 五頁仍全綠、既有屆別
  逐鍵重現、位元組未變（本變更不改資料常數，只改靜態 JS／HTML）

**Scope boundaries**

- 在範圍內：`index.html`／`en/index.html` 的 01、02 兩個圖表；
  `legislative.html`／`en/legislative.html` 的既有 tooltip 觸發元素的
  鍵盤可達性
- 不在範圍內：03、04 兩節；`roster.html` 本身；任何新資料或新計算

## Risks / Trade-offs

**風險一：`<a>` 包 SVG 圖形元素的瀏覽器相容性。** 現代瀏覽器（含行動裝置）
支援良好，但需要手動驗證：包在 `<a>` 內的透明 `<circle>` 是否仍能正確接收
pointer 事件並觸發 `bind()` 的 tooltip，而不是被 `<a>` 的預設樣式或事件
攔截。若有問題，退回決策 2 的替代方案。

**風險二：可點擊的圖表元素若無視覺提示，讀者不會發現可以點。** 本變更
不含新增 hover 樣式（如游標變手指、底線）的任務——`<a>` 標籤預設就會
改變游標樣式，暫時視為足夠；若使用者回饋看不出來，再另立變更加強視覺提示。
