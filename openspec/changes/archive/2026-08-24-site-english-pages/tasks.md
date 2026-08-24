## 1. 文案與標籤的單一來源

- [x] 1.1 在 `scripts/build_site_data.py` 加入 `STRINGS: dict[str, dict[str, str]]`（`{key: {"zh":…, "en":…}}`），把兩頁的**限定語與圖表標籤**收進去，並加入 `check_strings_complete()`：任一 key 缺 `zh` 或 `en` 即中止並列出該 key。落實「決策 1：限定語是**資料**，由產生器輸出，不是頁面裡的靜態文字」與需求 `A Translation Does Not Weaken A Qualifier` 的情境 `A qualifier string is missing in one language`。⚠️ 收進 `STRINGS` 的是**限定語**，不是全部文案——涵蓋率句、「不是全體原住民」、「這不等於政黨認同」、「三個資料集不可互相比較」、`CURRENT_TERM_NOTICE`。散文段落留在各自的 HTML。驗證方式：拿掉某個 key 的 `en` 值，斷言中止且訊息含該 key；還原後通過。

- [x] 1.2 加入 `LABELS_EN: dict[str, tuple[str, str]]`（`{中文名: (英文名, 出處)}`），涵蓋 11 個選舉種類名稱、7 個政黨桶名、界限面板實際顯示的 8 個政黨；出處限 `cec`／`common`／`project` 三值之一。加入 `check_labels_have_provenance()`：缺出處或出處不在允許值內即中止並列出該項。落實「決策 2：標籤英譯逐項宣告，且**每一項都要標出處**」與需求 `Display Labels Are Declared With Their Provenance` 的情境 `A declared label lacks provenance`。⚠️ 中選會英文站是 JS 渲染的、`WebFetch` 讀不到本文，能查證的只有搜尋摘要（"Lowland and Highland Indigene Legislator"）——**查不到官方用法的一律標 `project`，不可標 `cec` 充數**。驗證方式：把某一項的出處改成 `official`（不在允許值內），斷言中止且訊息含該標籤名；統計三種出處各幾項並印出，`project` 的項數要與實際查證結果相符。

- [x] 1.3 界限面板只翻譯實際顯示的 8 個政黨，展開表格裡的其餘 37 個**保留中文原名**，並在表格上方以 `STRINGS` 的一個 key 說明「沒有官方英文名者保留原文」。落實「決策 3：界限面板只翻**顯示得到**的 8 個政黨，其餘保留原文並說明」與需求 `Display Labels Are Declared With Their Provenance` 的情境 `A label has no established English name`。驗證方式：以指令統計界限表 45 個政黨中未列入 `LABELS_EN` 者，斷言其等於 **36**；並斷言兩頁都有「保留原文」的說明文字。⚠️ 提案時寫 37（45 減去面板顯示的 8 個），實測是 36——`無黨團結聯盟` 同時是政黨桶名，本來就在 `LABELS_EN` 裡，所以有英譯的是 9 個不是 8 個。以實測為準。⚠️ 完整表格只渲染**選定的那一屆**，所以 DOM 裡看到的中文名只有該屆的數量（2024 屆為 9 個），不是 36——這一條要驗宣告面，不是驗 DOM。

## 2. 兩個英文頁

- [x] 2.1 新增 `docs/en/legislative.html`：章節與中文版對應（範圍、政黨得票率、席次、投票率、界限），資料常數標記為 `const LEG = ` 與 `const BOUNDS = `、文案常數標記為 `const T = `，全部由 1.1／1.2 產生。落實 `Site Data Is Generated From The Long Tables` 的情境 `The same dataset is presented in two languages`。⚠️ 界限區塊必須同時滿足三條既有需求：涵蓋率與 "mountain indigenous townships" 早於任何百分比、限定語與數字在同一個 `.bnd` 區塊內、三個門檻並列。驗證方式：渲染後比對字元位置，斷言第一個百分比是 `11.0%`、"mountain indigenous" 的位置早於它；三個 `.bnd` 區塊各自都含本屆限定語的英文版；英文頁與中文頁的 `LEG`／`BOUNDS` 兩個常數**逐鍵完全相同**。

- [x] 2.2 新增 `docs/en/index.html`：章節與中文版對應（範圍、投票率、政黨、性別、規模、附錄、另計）。⚠️ 圖表標題寫 "vote share in legislative elections" 一類的敘述，**不可寫 "party support"**——與中文版不寫「政黨支持度」是同一條理由（候選人是誰、現任優勢、複數席次選區都會改變這個數字）。驗證方式：英文頁與中文頁的 `DATA` 常數逐鍵完全相同；以指令確認頁面不含 `party support` 字樣（不分大小寫）。

- [x] 2.3 兩版互相連結：四個頁面（中文兩頁、英文兩頁）的 `<head>` 各加 `<link rel="alternate" hreflang>` 指向對應語言版本，頁首導覽加語言切換連結。落實「決策 4：語言切換是**明確的連結**，不是自動偵測」。⚠️ **不做 `navigator.language` 轉址**——靜態站沒有內容協商，JS 轉址會讓分享出去的連結指向讀者未必想要的語言，且會在返回鍵上打架。驗證方式：以指令確認四頁各有兩個 `hreflang` 值（`zh-Hant` 與 `en`）且 URL 互相對應；以指令確認四頁的 `<script>` 中不含 `navigator.language`。

- [x] 2.4 兩個英文頁各加一段「本頁為專案自譯」的聲明，指明以中文版為準。落實需求 `A Self-Translated Page States That It Is Self-Translated`。⚠️ 這不是免責客套——沒有母語者覆核，英文限定語可能讀起來比中文弱而我看不出來，讀者有權知道。驗證方式：以指令確認兩個英文頁都含該聲明，且聲明中含指向中文版的連結。

## 3. 檢查改為遞迴

- [x] 3.1 `check_publication_record()` 的頁面列舉由 `glob("*.html")` 改為 `rglob("*.html")`，並把兩個英文頁加入 `docs/發布判定紀錄.md` 的逐頁判定表與 `PAGES_REQUIRING_NOTICE`。落實需求 `Coverage Checks Traverse Every Published Page` 與「決策 5：英文頁一樣要通過既有的四條需求，且**用同一組檢查**」。⚠️ **這是本變更最容易靜默失效的一處**：不改成遞迴的話，`docs/en/` 下兩頁會被安靜地跳過而不報錯——而「多了一頁沒人判定」正是那條檢查存在的理由。驗證方式：把 `rglob` 改回 `glob`，斷言英文頁**未被檢查到**（即：移除英文頁的限定語後仍然通過）——這一項證明遞迴是必要的，形狀同 `@reports` 承重驗證。

- [x] 3.2 `docs/sitemap.xml` 補上兩個英文網址（共五個）。驗證方式：XML 可解析且 `loc` 恰為五個，其中兩個以 `/en/` 開頭。

## 4. 測試與變異

- [x] 4.1 擴充 `scripts/test_build_site_data.py`：`STRINGS` 完整性、`LABELS_EN` 出處合法、中英資料常數逐鍵相同、英文界限區塊的涵蓋率順序、英文頁帶本屆限定語、遞迴列舉涵蓋 `docs/en/`。⚠️ 每一條 Failure mode 都要有一組會觸發它的輸入，且斷言錯誤訊息含**只有該檢查會輸出的字串**。驗證方式：`pytest scripts/test_build_site_data.py` 通過，且該檔的檢查項數比變更前增加不少於 12 項。

- [x] 4.2 擴充 `scripts/mutate_build_site_data.py`，新增四項變異並確認全部被偵測：（1）`STRINGS` 某 key 少掉 `en`；（2）`LABELS_EN` 某項出處改成不允許的值；（3）`rglob` 改回 `glob`；（4）英文限定語被翻弱（拿掉 "not the whole"）。⚠️ 第 3 項要用**成對驗證**而非一般變異：把 `rglob` 改回 `glob` 之後，若同時拿掉英文頁的限定語，檢查應該**抓不到**——那正是遞迴必要的證明。⚠️ 成對驗證要**直接呼叫被測函式**、只問它有沒有丟例外，不可看 pytest 退出碼——測試檔另有獨立斷言會一起紅，量不出差別（本專案已犯過一次）。⚠️ 變異若動到 `docs/` 下的真檔，該檔須先提交乾淨，且每個被變異的檔各需一個 canary。驗證方式：執行後輸出「全部通過」，每個 canary 皆被抓到，基準對照通過。

## 5. 文件

- [x] 5.1 `README.md` 的線上瀏覽區塊加入兩個英文網址，並說明名錄沒有英文版及其理由（4,607 個人名的音譯沒有權威來源）。`HANDOFF.md` 地雷區新增一條：限定語由 `STRINGS` 產生、兩版不可各自手寫，以及涵蓋檢查必須遞迴。驗證方式：以指令確認 `README.md` 含 `/en/` 連結與「音譯」二字；`HANDOFF.md` 含 `STRINGS` 與 `rglob`。
