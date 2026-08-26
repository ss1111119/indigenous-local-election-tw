## Summary

把立委頁在導覽列與 `<h1>` 裡用到的「政黨傾向」「政黨版圖」這兩種說法，
改成跟頁面實際資料能力相符、更中性的用詞。

## Motivation

延續上一輪 Codex 對整體架構的審查：`docs/legislative.html` 的導覽標籤是
「立委與政黨傾向」、`<h1>` 是「立委九屆的政黨版圖」，但頁面本身在第 01 節
與 `.qual` 限定語裡明確承認候選人得票率不是政黨認同、不分區政黨票只涵蓋
一小部分原住民選舉人。「政黨傾向」「政黨版圖」這兩種說法暗示的解讀強度
超過資料實際能撐起的範圍，跟這個網站一貫的方法論誠實互相矛盾。

已查證受影響範圍：
- 導覽標籤「立委與政黨傾向」（英文對應 `Legislators & party leaning`）
  出現在五個頁面的 `<nav>` 裡：`docs/index.html`、`docs/roster.html`、
  `docs/legislative.html`、`docs/en/index.html`、`docs/en/legislative.html`。
- `<h1>` 的「···的政黨版圖」（英文對應 `Nine Terms of Party Politics`）
  只出現在 `docs/legislative.html` 與 `docs/en/legislative.html`。
- `<title>` 標籤本身已經是中性的（「原住民立委九屆」／
  `Indigenous Legislators, Nine Terms`），不需要改。

## Proposed Solution

- 把五個頁面 `<nav>` 裡的導覽標籤「立委與政黨傾向」改成「立委選舉」，
  英文版對應改成 `Legislative elections`。
- 把 `docs/legislative.html` 的 `<h1>` 從「···的政黨版圖」改成
  「···的政黨得票率」，呼應頁面內第 01 節既有的「立委選舉的政黨得票率」
  這個說法，用詞跟站台其他地方一致；`docs/en/legislative.html` 的
  `<h1>` 對應從 `Nine Terms of Party Politics` 改成
  `Nine Terms of Party Vote Share`。
- 新增一項自動化檢查，驗證這兩個舊說法（「政黨傾向」「政黨版圖」／
  `party leaning`／`Party Politics`）不再出現在導覽列或 `<h1>` 裡，
  防止之後又不小心改回去卻沒人發現。

## Non-Goals

- 不改版面結構、不改資料內容、不改 `.qual` 限定語文字本身（那些文字
  已經正確描述了資料限制，這次只改導覽標籤與標題這兩個「入口文案」）。
- 不改 `<title>` 標籤（已經是中性的）。
- 不處理 Codex 這次審查提出的其他項目（首頁分層、`<main>` 語意標籤、
  共用 CSS 整理等）——那些留給使用者確認後再另開 change。
- 不禁止「政黨傾向」這個詞出現在頁面**內文**的限定討論裡——這次要擋的
  只是把它當**主要導覽標籤或標題**使用，內文裡出現是正常且必要的。

## Alternatives Considered

- 保留「政黨傾向」但在旁邊加註解釋——Codex 與這次評估都認為，導覽標籤
  跟標題的篇幅本來就短，加註解釋的空間有限，效果不如直接換一個不需要
  額外解釋的中性說法。
- 完全比照 Codex 建議的「立委：政黨、席次與投票率」——考慮到導覽列
  空間有限（五個連結要並排），選擇較短的「立委選舉」，完整的內容範圍
  已經由 `<title>`「原住民立委九屆」與頁面第 01-04 節標題涵蓋。

## Impact

- Affected specs: `site-editorial-neutrality`（新增）
- Affected code:
  - New: (none)
  - Modified: `docs/index.html`, `docs/roster.html`, `docs/legislative.html`,
    `docs/en/index.html`, `docs/en/legislative.html`,
    `scripts/build_site_data.py`, `scripts/test_build_site_data.py`
  - Removed: (none)
