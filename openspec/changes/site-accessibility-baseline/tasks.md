<!--
Each task description MUST state:
- the behavior or contract being delivered (what is observably true when the
  task is complete), and
- the verification target that proves completion (test, CLI invocation,
  analyzer check, manual assertion, or content review).
-->

## 1. 量測與配色

- [x] 1.1 量出既有配色的實際問題，落實 Categorical Colors Are Measured Against Each Other 的「量測」一端：以 OKLab ΔE×100 與色盲模擬計算兩個主題下相鄰系列的距離。驗證方式：民進黨綠↔其他灰在淺色為常人 14.5／色盲 5.5、暗色 12.9／4.5，皆低於門檻（15／8），數字為執行驗證器所得而非估計。
- [x] 1.2 依設計決策「語意色不動，動的是「其他」桶與文字」只調整語意無約束的系列，落實 Categorical Colors Are Measured Against Each Other 的「慣例色不動」一端：淺色 `--s4` `#9BA0A5`→`#ADB3B9`、暗色 `--s4` `#7C838A`→`#6A7178`、暗色 `--s3` `#199e70`→`#1da77a`。驗證方式：重跑驗證器，兩個主題的常人 ΔE 為 16.9／16.6、色盲 9.0／9.7，且四個政黨色相未改變（`git diff` 中 `--s1`／`--s2` 淺色值不變）。

## 2. 段內文字

- [x] 2.1 依設計決策「每系列一個墨色變數」新增 `--lab1`~`--lab4`，並讓 `PARTIES` 每項同時帶填色與墨色變數名，實現 Labels Drawn Inside A Mark Meet 4.5:1 Against That Mark。驗證方式：八個「系列×主題」組合的 WCAG 對比全部 ≥4.5（4.76／5.56／6.32／8.41／4.89／4.58／5.82／4.95）。
- [x] 2.2 退回一項錯誤修改，對應設計決策「對比不足時改文字墨色，不改語意色 —— 本輪一度做錯」，落實 requirement 中「慣例色相遇對比不足時先窮盡黑白」的條件：曾把淺色 `--s1` 改為 `#2670cc` 以遷就白字，實際上原色 `#2a78d6` 配純黑即 4.76:1。驗證方式：`--s1` 回到 `#2a78d6`、`--lab1` 為 `#000`，且 2.1 的八項全數仍達標。
- [x] 2.3 `docs/roster.html` 的政黨徽章同步（原為 `li.won .pty{color:#fff}` 一律白字，11px 小字）。驗證方式：徽章改為依 `data-p` 取 `--lab1`~`--lab4`，且兩頁的 `--s1`~`--s4` 值完全一致（同一組圖例不得跨頁不同色）。

## 3. 替代內容

- [x] 3.1 依設計決策「替代內容用可展開表格，不是視覺隱藏表格」新增可展開表格並由同一份 `DATA` 產生，實現 Color-Encoded Data Has A Tabular Equivalent。驗證方式：`#t-party` 產生 27 列，抽樣 T2 2005＝16／7／0／4 合計 27、T3 2005＝20／8／0／2 合計 30，與 HANDOFF 的權威席次序列一致；圖表帶 `aria-describedby="t-party"`。
- [x] 3.2 修正兩處與現況不符的敘述：figcaption 仍寫「三條由上而下為 2014／2018／2022」（實際七條），政黨代碼說明只提 `999`（舊屆為 `99`／「無」）。驗證方式：內容複核，並確認新敘述與 3.1 的表格、以及 `fix-party-bucket-drift` 的分桶修正互不矛盾。

## 4. 列印與高對比

- [x] 4.1 依設計決策「列印一律套淺色」以 `@media print` 覆寫變數並保住色塊，實現 Print And Forced Colors Do Not Erase The Encoding 的列印情境。驗證方式：把該區塊改為 `@media screen` 的暫時副本、強制 `data-theme="dark"` 後渲染，實測 `--paper` 為 `#fff`、段內數字 `rgb(0,0,0)`；暫時副本已刪除。
- [x] 4.2 依設計決策「高對比模式保留圖表原色」，對 `svg`／`.sw`／`.pty` 設 `forced-color-adjust:none`。驗證方式：確認該 media rule 有正確解析進 stylesheet（`document.styleSheets` 列出 `(forced-colors: active)`）。**未在真實 Windows 高對比模式下確認**，這條的驗證強度低於其他項。

## 5. 文件層宣告

- [x] 5.1 補 `doctype`、`html lang="zh-Hant"`、`head`／`body`、`meta charset`、`viewport`，實現 Pages Declare Encoding, Language, And Viewport。驗證方式：瀏覽器實測 `document.doctype` 為真、`documentElement.lang` 為 `zh-Hant`、viewport meta 存在；補 charset 前經由本機 server 開啟確實是亂碼，補後正常。

## 6. 安全網

- [x] 6.1 依設計決策「一致性要有東西在守，不是有指令可查」新增 `scripts/test_site_invariants.py::test_embedded_constants_match_long_tables`，實現 Constant-To-Long-Table Consistency Is Enforced, Not Merely Checkable：由測試套件執行 `--check` 並在退出碼非零時列出差異的鍵。驗證方式：變異測試——把 `docs/index.html` 常數中 T2 1998 的 `seats` 由 23 改為 24，該測試失敗；還原後通過。
- [x] 6.2 新增 `test_in_mark_label_contrast`，把 4.5:1 這條下限釘住，防止四個墨色變數被當成冗餘移除。驗證方式：變異測試——把淺色 `--lab4` 改回 `#fff`（對比 2.12），該測試失敗並指出是哪個系列與主題。
- [x] 6.3 新增 `test_pages_declare_encoding_language_and_viewport`。驗證方式：變異測試——移除 `viewport` meta，該測試失敗。
- [x] 6.4 確認新測試不是「永遠通過的測試」。驗證方式：三項變異同時植入時三個測試同時失敗（`3 failed`），還原後全套 `pytest scripts/ -q` 為 `30 passed`。
