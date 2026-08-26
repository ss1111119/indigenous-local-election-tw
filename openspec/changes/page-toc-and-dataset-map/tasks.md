## 1. build_site_data.py：新增資料集地圖字串與兩個一致性檢查

- [x] 1.1 在 `STRINGS` 新增 `dataset_map` 鍵（zh/en 各一段文字，說明地方公職／原住民立委／不分區政黨票界限估計三個資料集彼此不可比較），對應設計決策「資料集地圖是新的 `STRINGS["dataset_map"]` 鍵，跨五個頁面共用同一段文字」。驗證：`check_strings_complete()` 通過，新鍵兩語言皆非空。
- [x] 1.2 新增 `DATASET_MAP_PAGES: dict[str, str]`（五個已發布頁面 → 語言碼）與 `check_dataset_map_present()`，比對邏輯沿用 `check_static_qualifiers()` 排除 `<script>` 區塊的既有寫法，實現規格「Every published page states where the site's other datasets can be found」。驗證：對缺少該段文字的合成頁面呼叫會拋出 `SiteDataError` 並具名頁面。
- [x] 1.3 新增 `TOC_PAGES: dict[str, tuple[str, ...]]`（四個多節頁面 → 期望的 section id 順序）與 `check_section_ids_match_toc()`，解析頁面 `<section id="...">` 序列與 `<nav class="toc">` 內 `href="#..."` 序列並比對是否一致，實現規格「Multi-section pages provide an in-page table of contents whose entries match the page's actual sections」，對應設計決策「頁內目錄是手寫的 `<nav class="toc">`，用一致性檢查而非生成保證正確」。驗證：對 section id 與目錄不一致的合成頁面呼叫會拋出 `SiteDataError` 並具名差異。
- [x] 1.4 把 `check_dataset_map_present()`、`check_section_ids_match_toc()` 接進 `main()` 的 `if args.write or args.check:` 區塊，各自印出對應的 `✓` 確認訊息。驗證：`python scripts/build_site_data.py --check` 在尚未改頁面前會因缺少 section id／目錄／資料集地圖文字而中止（預期失敗），確認新檢查真的被執行到。

## 2. HTML：加 section id、頁內目錄、資料集地圖文字

- [x] 2.1 為 `docs/index.html` 的七個 `<section>` 加上 id（`scope`／`turnout`／`party`／`gender`／`scale`／`perseat`／`custom`），依設計決策「Section id 直接手寫在 HTML 原始碼裡，不由 build_site_data.py 動態產生」手寫而非生成，並在 `<nav class="nav">` 之後手寫 `<nav class="toc">` 列出對應七個 `<a href="#id">`。驗證：`check_section_ids_match_toc()` 對 `docs/index.html` 通過。
- [x] 2.2 為 `docs/legislative.html` 的五個 `<section>` 加上 id（`scope`／`partyvote`／`seats`／`turnout`／`bounds`，`bounds` 沿用既有值不改），並加上對應的 `<nav class="toc">`。驗證：`check_section_ids_match_toc()` 對 `docs/legislative.html` 通過。
- [x] 2.3 為 `docs/en/index.html`、`docs/en/legislative.html` 加上與中文版逐一對應的 section id 與 `<nav class="toc">`（英文標籤文字）。驗證：`check_section_ids_match_toc()` 對兩個英文頁通過。
- [x] 2.4 在 `docs/index.html`／`docs/roster.html`／`docs/legislative.html`／`docs/en/index.html`／`docs/en/legislative.html` 的導覽附近各自加入與 `STRINGS["dataset_map"]` 逐字相同的資料集地圖段落（中文頁用 zh、英文頁用 en）。驗證：`check_dataset_map_present()` 對五個頁面全數通過。

## 3. 測試：合成案例與真實 docs/ 驗證

- [x] 3.1 在 `scripts/test_build_site_data.py` 新增 `test_dataset_map_present`：合成一個缺少資料集地圖文字的頁面驗證 `check_dataset_map_present()` 會中止，並對真實 `docs/` 驗證五個頁面全數通過。驗證：`python scripts/test_build_site_data.py` 該測試組別全數 PASS。
- [x] 3.2 在 `scripts/test_build_site_data.py` 新增 `test_section_ids_match_toc`：合成一個目錄與 section id 不一致的頁面驗證 `check_section_ids_match_toc()` 會中止（含目錄多連、目錄少列兩種變體），並對真實 `docs/` 的四個多節頁面驗證全數通過。驗證：`python scripts/test_build_site_data.py` 該測試組別全數 PASS。
- [x] 3.3 執行 `python scripts/build_site_data.py --write` 兩次並比對輸出位元是否相同（冪等），確認 HTML 手改內容不影響既有生成內容。驗證：兩次輸出的 `docs/index.html`／`docs/legislative.html`（含英文版）逐位元相同。

## 4. 變異測試覆蓋

- [x] 4.1 在 `scripts/mutate_build_site_data.py` 的 `MUTATIONS` 為 `check_dataset_map_present()` 補至少一則真實檔案變異（例如刪除某頁的資料集地圖段落），確認會被 3.1 新增的測試抓到。驗證：`python scripts/mutate_build_site_data.py` 該則變異回報「有測試抓到」。
- [x] 4.2 在 `scripts/mutate_build_site_data.py` 的 `MUTATIONS` 為 `check_section_ids_match_toc()` 補至少一則真實檔案變異（例如把某個 `<nav class="toc">` 裡的一個 `href` 改成不存在的 id），確認會被 3.2 新增的測試抓到。驗證：`python scripts/mutate_build_site_data.py` 該則變異回報「有測試抓到」。

## 5. 手動驗證

- [x] 5.1 用 Playwright 開啟 `docs/index.html`／`docs/legislative.html`，點擊頁內目錄任一項確認畫面跳轉到對應節、無破版；截圖確認資料集地圖文字可見。驗證：截圖顯示跳轉後對應 `<section>` 位於可視範圍內，且沒有版面重疊。
