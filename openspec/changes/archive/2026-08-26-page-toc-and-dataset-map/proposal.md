## Why

`docs/index.html`（7 節）與 `docs/legislative.html`（5 節）都是只能靠捲動閱讀的長頁面，沒有任何頁內錨點或目錄可以跳段落。導覽列（`<nav class="nav">`）只列出頁面連結，沒有說明三個頁面／三個資料集（地方公職、原住民立委、不分區政黨票界限估計）彼此的範圍差異——讀者要自己讀完 README 或每頁的「範圍」節才知道還有哪些資料集、分別在哪一頁。這是 2026-08-25 Codex 整體架構審查優先序清單第 3 項。

## What Changes

- 在 `docs/index.html`、`docs/legislative.html`（及其英文版 `docs/en/index.html`、`docs/en/legislative.html`）的每個 `<section>` 加上穩定的 `id`
- 在每頁 `<h1>`／`<nav>` 附近加一段頁內目錄，列出本頁所有節、可點擊跳轉錨點連結，純 HTML/CSS 實作（不寫額外 JS）
- 在導覽列附近加一段簡短的資料集地圖文字，說明三個資料集／頁面各自涵蓋什麼、彼此不可比較；`docs/roster.html` 只加資料集地圖、不加頁內目錄（單頁無多節結構）
- 中英文兩版文案透過 `scripts/build_site_data.py` 的 `STRINGS`／`LABELS_EN` 產生，不手寫兩份
- 新增自動化檢查：每個 `<section>` 的 `id` 與頁內目錄連結一致（目錄連去不存在的 id、或有 section 沒被目錄列到都要中止）；三個頁面（index／roster／legislative）都含資料集地圖文字

## Non-Goals (optional)

## Capabilities

### New Capabilities

- `site-navigation`: 頁內目錄（section id 與目錄連結一致）與資料集地圖（讓讀者在任一頁都能看到三個資料集彼此的範圍差異）

### Modified Capabilities

## Impact

- Affected specs: `site-navigation`（新）
- Affected code:
  - Modified: `docs/index.html`, `docs/legislative.html`, `docs/roster.html`, `docs/en/index.html`, `docs/en/legislative.html`, `scripts/build_site_data.py`, `scripts/test_build_site_data.py`, `scripts/mutate_build_site_data.py`
