## Problem

`election-period-publication` 的規則面（spec）與紀錄面（`docs/發布判定紀錄.md`）之間有三處不一致，全部在 2026-08-27 與外部覆核討論「總統票與政黨票的落差算不算解讀性指標」時浮現：

**1. `index.html` 的判定理由與頁面內容不符。**
紀錄寫的理由是「逐票全查，值由已公告的官方結果與版控中的計算式決定；**無方向性的量**。兩問皆否。」但該頁實際文字包含：

- 「T2 與 T3 從 2009-2010 一路上升到 2018（分別 +3.08／+1.00 與 +4.98／+0.56 個百分點）」
- 「2018→2022 才全部下降」
- 「參考組 T1 同期亦下降 5.83 個百分點」

那些是帶方向的量。**判定結論可能仍然正確**（可由完整官方計數與固定算式重算，無推估），但**理由是錯的**——而理由正是下一個人判斷同類案例時會拿來對照的東西。

**2. 兩段式測試的條件 (1) 文字有歧義。**
原文是「It cannot be obtained by summing officially published counts — it requires estimation, extrapolation, or **division across populations that were not counted together**」。

外部覆核（Codex）第一次讀時把破折號後的三項當成**獨立觸發條件**，因而把「總統票率減政黨票率」判為解讀性指標；經對照後改判為窄讀法（那三項是在說明什麼情況會導致「無法由加總取得」）。**兩種讀法在同一段文字上都說得通，就是歧義的證據。**

**3. `README.md` 不在機器檢查的涵蓋範圍內。**
`check_publication_record()` 掃的是 `docs/**/*.html`。但 `README.md` 也是公開的（GitHub repo 首頁），且含有跨屆投票率變化欄（`14→18`、`18→22`）——與 `index.html` 上那些百分點變化同一性質。

該檢查的 docstring 明寫它要擋的是「**多了一頁，沒有人想起要判定**」。README 正是「沒有人想起要判定」的那一類，只是它不是 `.html`。

## Root Cause

三者的共同成因是：規則寫成之後，**只有 `docs/` 下的 HTML 進入了機器驗證的迴圈**，而規則本身的文字與判定理由沒有任何東西在驗。

`check_publication_record()` 的 docstring 已經誠實地寫著「要擋的不是『判定寫錯』（那需要人看）」——那是刻意的取捨，不是疏漏。但「判定理由與頁面內容矛盾」這一類，其實**是機器驗得到的**：頁面若含方向性字樣而理由說「無方向性的量」，兩者必有一錯。

## Proposed Solution

- 修正 `index.html` 的判定理由，改以「完整官方計數、固定算式、無推估」為依據，並明文記載該頁**含有**方向性敘述、以及為什麼那不使它成為解讀性指標
- 在 spec 的兩段式測試補一個 Scenario，釘住「兩個各自在單一計數母體內取得的比率相減，仍是凍結歷史數據」——**這是補判例，不是改判準**
- 把 `README.md` 納入發布判定紀錄與 `check_publication_record()` 的涵蓋範圍
- 新增檢查：判定理由若聲稱「無方向性的量」，而該頁含有方向性字樣，即中止並具名

## Non-Goals

- **不改兩段式測試的判準本身**：外部覆核建議改寫條件 (1) 並加排除條款；本 change 認為現行文字已支持正確結論，問題是套用時不夠仔細與缺少判例。加排除條款會讓測試變複雜
- **不重新判定其他頁面**：只修 `index.html` 那一列的理由。其餘五列的理由未發現與內容矛盾
- **不改任何頁面內容**：`index.html` 上那些百分點敘述**維持原樣**——它們是可發布的凍結歷史數據，要改的是紀錄裡的理由
- **不把「兩個凍結數字相減」一律開放**：補的判例限於「各自在單一完整計數母體內取得的比率」；涉及推估或代理母體者不在其中
- **不處理站台是否呈現 `D1-MT`**：那是待 2026-12-04 後的決定，與本 change 無關

## Success Criteria

- `docs/發布判定紀錄.md` 的 `index.html` 一列不再出現與頁面內容矛盾的理由
- spec 的兩段式測試多一個 Scenario，明確涵蓋「兩個單一母體內的比率相減」
- `README.md` 在發布判定紀錄中有一列，且 `check_publication_record()` 涵蓋它
- 新增的「理由與內容一致」檢查在現況下通過；把某頁的理由改成「無方向性的量」而該頁含方向性字樣時，該檢查中止並具名
- `docs/` 下 HTML 逐位元組未變；`data/processed/` 未變

## Impact

- Affected specs: `election-period-publication`（修改）
- Affected code:
  - Modified: `docs/發布判定紀錄.md`, `scripts/build_site_data.py`, `scripts/test_build_site_data.py`, `scripts/mutate_build_site_data.py`
  - New: (none)
  - Removed: (none)
