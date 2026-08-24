## Why

站台的圖表互動目前只有滑鼠 hover 的 tooltip，鍵盤與觸控裝置都拿不到那些數字。
與 Codex、Antigravity 於 2026-08-24 分別獨立討論後，兩邊的結論收斂：
「圖表資料點可點擊、連到名錄對應的屆別與選舉種類」與「hover 改為鍵盤可達」
是投報率最高、且不觸碰選舉期間發布規則的兩件事——`roster.html` 早已支援
網址雜湊定位（`#屆別/代碼`），純粹是巨觀圖表沒有接上這個既有能力。

兩邊也一致警告：**互動性不可用來讓讀者在前端自選欄位算比值**——那等於
在客戶端產生新的解讀性指標，即使算式沒有寫死進 HTML，一樣違反
`election-period-publication` 的規則。本變更的範圍嚴格限於「篩選、
定位、可及性」，不新增任何計算。

## What Changes

- `docs/index.html` 的投票率折線圖（01）與政黨席次堆疊條（02）的資料點／
  區段可點擊，導向 `roster.html#屆別/代碼`（既有的雜湊定位能力）。
- 所有既有 tooltip 的觸發元素（`bind()` 綁定的隱形 hit target）補上
  `tabindex="0"`、`role="link"` 或對應語意，並用 `focus`／`blur`
  取代（不是取消）`pointerenter`／`pointerleave`，使 Tab 鍵可達、
  Enter／Space 可觸發導航。
- 同步套用到 `docs/en/index.html`（依 `site-translation` 的既有規則，
  兩版的 JS 必須完全相同，只有 `T`／`L` 不同）。
- `docs/legislative.html` 與 `docs/en/legislative.html` 的 tooltip
  觸發元素同樣補上鍵盤可達性，但**不新增點擊導航**——立委資料沒有對應的
  名錄頁可以連過去。

## Non-Goals

- 不新增任何比值、排名、差距或其他解讀性指標，不論算在前端還是後端。
- 不做讀者自選欄位、自訂分組、自訂篩選條件的分析器。
- 不做圖例與資料點互相高亮（Codex 提過，但這次范圍先收斂到導航與可及性）。
- 不做 03 性別方格圖與 04 規模表的點擊導航——保留給下一輪，避免範圍蔓延。
- 不引入前端框架、圖表套件或 build pipeline。
- 不修改 `roster.html` 本身——它的雜湊定位能力已經存在，不需要改。

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `site-chart-accessibility`: 加入鍵盤可達性與導航的要求

## Impact

- Affected specs: `site-chart-accessibility`（修改）
- Affected code:
  - Modified: `docs/index.html`、`docs/en/index.html`、`docs/legislative.html`、
    `docs/en/legislative.html`、`scripts/test_build_site_data.py`、
    `scripts/mutate_build_site_data.py`
  - New: （無）
  - Removed: （無）
