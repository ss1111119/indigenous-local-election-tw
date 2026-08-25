## Problem

`README.md` 第 488 行明確宣稱 `docs/index.html`、`docs/roster.html`「不連外部
資源」，`scripts/build_site_data.py` 的檔頭註解重申這個設計原則（理由是
`fetch()` 會讓離線開啟與單檔分享失效，`file://` 下還會被 CORS 擋掉）。但
實際查證：五個站台頁面（`docs/index.html`、`docs/roster.html`、
`docs/legislative.html`、`docs/en/index.html`、`docs/en/legislative.html`）
全部都有 `<link rel="preconnect" href="https://fonts.googleapis.com">` 與
`<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=...">`
連到 Google Fonts（`IBM Plex Mono`、`Noto Sans TC`、`Noto Serif TC` 三個
字型家族）。這是文件承諾與實際行為的真實矛盾，不是誤報。

## Root Cause

字型選型階段直接採用 Google Fonts 提供的 CDN 連結，沒有人對照
`README.md` 既有的「不連外部資源」承諾做一致性檢查；且這件事沒有任何
自動化檢查會擋下，純粹是這次由 Codex 做整體架構審查時人工讀出來的。

## Proposed Solution

- 移除五個頁面 `<head>` 裡的兩個 Google Fonts `<link>`（`preconnect` 與
  `stylesheet`）。
- 把 CSS 與內嵌 JS 裡所有 `font-family` 宣告中引用的
  `"IBM Plex Mono"`、`"Noto Sans TC"`、`"Noto Serif TC"` 這三個具名字型
  拿掉，只留下原本就存在於同一條宣告裡的通用字型關鍵字（`monospace`、
  `sans-serif`、`serif`）或系統字型關鍵字（例如既有的 `ui-monospace`）。
  不拿掉整條 `font-family` 宣告本身，只拿掉具名字型那一段。
- 在 `scripts/build_site_data.py` 新增一項自動化檢查，驗證
  `docs/` 底下每一個 `.html` 檔案都不含指向外部主機的資源參照
  （`http://` 或 `https://` 開頭、且不是 SVG 命名空間 URI
  `http://www.w3.org/2000/svg` 的字串），在 `--check` 與 `--write` 都會跑。

## Non-Goals

- 不改變任何非字型相關的視覺樣式（配色、間距、版面結構）。
- 不新增字型檔案到 repo 裡（不做自行代管字型檔這件事）——這次選擇的是
  改用系統字型，不是「離線內建自訂字型」這個替代方案。
- 不處理 Codex 這次審查提出的其他項目（導覽命名、首頁分層、`<main>`
  語意標籤等）——那些留給使用者確認後再另開 change。

## Success Criteria

- 五個頁面的 `<head>` 都不再含任何 `fonts.googleapis.com`／
  `fonts.gstatic.com` 的 `<link>`。
- 執行 `python scripts/build_site_data.py --check`，新增的外部資源檢查
  通過，且既有的所有檢查（欄位重現、限定語、oracle 曝光等）都不受影響。
- 新增的外部資源檢查在人為插入一個外部資源參照（例如一個假的
  `<script src="https://example.com/x.js">`）時會中止，證明它真的有
  辨識力，不是形式上存在。
- 用瀏覽器實際開啟五個頁面，標題與內文顯示為瀏覽器/作業系統的預設
  serif／sans-serif／monospace 字型，版面沒有明顯跑版或重疊。

## Impact

- Affected specs: `site-offline-resource-policy`（新增）
- Affected code:
  - New: (none)
  - Modified: `docs/index.html`, `docs/roster.html`, `docs/legislative.html`,
    `docs/en/index.html`, `docs/en/legislative.html`,
    `scripts/build_site_data.py`, `scripts/test_build_site_data.py`
  - Removed: (none)
