## Why

站台的圖表**以顏色承載資料**，但配色與段內文字從未被量測過。實測（OKLab ΔE×100、WCAG 對比）發現三類缺陷，共同特徵是**不會讓任何測試失敗、也不會在畫面上看起來壞掉**：

1. 政黨圖的民進黨綠與「其他各政黨」灰，**連正常色覺的讀者都難以分辨**（淺色 ΔE 14.5、暗色 12.9，門檻 15；色盲模擬 5.5／4.5，門檻 8）。在政黨席次圖上，這是把一個政黨的席次看成另一類。
2. 段內席次數字一律白字，八個「系列×主題」組合中**七個低於 4.5:1**，最差的是淺色「其他」上的白字，只有 2.12:1。名錄頁的政黨徽章同樣問題，且字級只有 11px。
3. 兩個頁面都缺 `<meta charset>`、`viewport`、`doctype` 與 `lang`。線上靠 GitHub Pages 送出的 header 才正常，**存下來離線開啟就是滿畫面亂碼**——而「單檔分享、離線可開」正是 `build_site_data.py` 明訂的設計前提。手機則以桌機寬度渲染後整頁縮小。

另外在同一輪覆核中，`build_site_data.py --check` 回報 36 項未預期差異、退出碼 1。**這些差異不是站台漂移，而是同時進行的 `fix-party-bucket-drift` 改動了產生器的分桶規則所暴露的**——HEAD 的產生器只比對政黨名稱字串，站台常數與它一致；把規則改成 (政黨代號, 政黨名稱) 配對後，舊屆的無黨籍（代號 `99`／名稱「無」）才從「其他各政黨」歸位。本 change 因此**不負責那項資料修正**，只從中得到一個結論：這種「產生邏輯改了但站台沒跟上」的狀態，目前**沒有任何自動化會回報**，只能靠有人想起要跑 `--check`。缺的是執行點。

## What Changes

- **配色**：淺色「其他」灰 `#9BA0A5`→`#ADB3B9`、暗色 `#7C838A`→`#6A7178`，暗色民進黨綠 `#199e70`→`#1da77a`。**政黨色相一律不動**——調整只發生在語意無約束的「其他」桶，以及暗色綠的同色相微調。
- **段內文字**：新增 `--lab1`～`--lab4`，每個系列依自身填色算出的對比選黑或白，八組全部 ≥4.5:1。`roster.html` 的徽章同步（原本 `li.won .pty{color:#fff}` 一律白字）。
- **替代內容**：政黨圖表新增可展開表格（`<details>` + `#t-party`），由同一份 `DATA` 產生。窄段不標數字，這是唯一能取得那些數值的地方——tooltip 對鍵盤、螢幕閱讀器、列印與高對比模式都不存在。圖表加 `aria-describedby`。
- **列印**：`@media print` 強制套淺色變數並 `print-color-adjust:exact`。原本在暗色主題列印會得到白紙白字，且長條圖可能被省墨規則整片吃掉。
- **高對比**：`@media (forced-colors: active)` 對 `svg`／`.sw`／`.pty` 設 `forced-color-adjust:none`，因為那些顏色是資料本身。
- **文件基本結構**：補 `doctype`、`html lang="zh-Hant"`、`head`／`body`、`meta charset`、`viewport`。
- **不含資料修正**：1994–2005 的無黨籍歸屬由 `fix-party-bucket-drift` 負責（該 change 修的是產生器的分桶規則，並會自行重新產生常數）。本 change 進行期間曾誤跑 `--write`，把該 change 進行中的結果寫入 `docs/index.html`；那一行 `const DATA` 的改動應歸入該 change 的提交，不屬於本 change。頁面上「舊屆用代碼 `99`／名稱「無」」的說明則留在本 change，因為它是讀者敘述而非資料。
- **安全網**：新增三項測試——常數與長表的一致性（執行 `--check` 的比對邏輯）、段內文字對比度的下限，以及頁面的文件層宣告。沒有這兩項，上述決定會在下一次重構時被無聲地改掉。
- 修正兩處過時敘述：政黨圖 figcaption 仍寫「三條由上而下為 2014／2018／2022」（實際已七條）、政黨代碼說明只提 `999`。

## Capabilities

### New Capabilities

- `site-chart-accessibility` — 圖表的顏色、文字對比、替代內容，以及列印與高對比模式下不依賴顏色的可讀性；另含頁面的文件層宣告（編碼、語言、viewport）。

### Modified Capabilities

- `site-data-generation` — 既有 requirement 要求「重現既有屆別、差異須具名」，但沒有任何自動化在執行它。新增一條 requirement，把一致性從「有指令可查」變成「有東西在守」。

## Impact

- `docs/index.html`、`docs/roster.html`
- `scripts/test_site_invariants.py`（新增，三項測試）
- 不影響 `data/processed/`、不影響任何長表產生邏輯、不改變任何數字（數字的變動屬 `fix-party-bucket-drift`）
- **提交順序相依**：本 change 的 `test_embedded_constants_match_long_tables` 會執行產生器再比對站台常數，因此必須在 `fix-party-bucket-drift` 之後提交；否則乾淨 checkout 上會是「舊產生器 vs 新常數」而失敗
