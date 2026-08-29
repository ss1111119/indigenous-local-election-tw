## 1. 改寫兩個頁面的涵蓋宣稱

本節實作 spec Requirement `A Coverage Claim Separates What The Data Lacks From What The Site Withholds`。

- [x] 1.1 （spec Requirement `A Coverage Claim Separates What The Data Lacks From What The Site Withholds`）改寫 `docs/index.html` 的涵蓋宣稱，分開交代兩件事：**資料層未涵蓋**（平地原住民鄉及一般鄉鎮市的鄉鎮市長、鄉鎮市民代表的區域席次、村里長、縣市長）與**資料層已涵蓋但站台未呈現**（山地鄉鄉長 `D1-MT`，七屆 187 個單位）。完成後：讀者不會把「鄉鎮市長」整類讀成未涵蓋。
- [x] 1.2 在同一段寫出站台未呈現 `D1-MT` 的**兩個**理由：`D1-MT` 沒有檔別合計列（依 `site-multi-dataset` 的 `A presented type's national figures come from the source's own aggregate row`，沒有該列者不可呈現且不得自行加總明細列），以及 `SITE_EXCLUDED_TYPES` 宣告的「待 2026-12-04 公告當選人名單後決定」。⚠️ 只寫後者會讓讀者以為解除延後就能呈現。
- [x] 1.3 改寫 `docs/en/index.html` 的對應句，語意與中文版逐項一致——兩項缺席、`D1-MT` 具名、兩個理由都要在。⚠️ 不可只照字面翻中文而遺漏其中一項。
- [x] 1.4 確認改寫後的句子中，修飾語「區域席次」／`regional seats` 的作用範圍明確，不會被讀成同時修飾鄉鎮市長。

## 2. 驗證

- [x] 2.1 執行 `python scripts/build_site_data.py --write`，離開碼為 0。**必須加 `--write`**：不加時只做檢查與報告，離開碼一樣是 0 但不會寫入。
- [x] 2.2 以 `git diff --stat docs/` 確認只有 `docs/index.html` 與 `docs/en/index.html` 變動，其餘頁面與 `docs/sitemap.xml` 位元組不變。
- [x] 2.3 比對兩頁的資料常數（`const DATA`／`const T`／`const L`）在改寫前後**逐鍵相同**——本次只應有散文變動，任何常數差異都代表改到了不該改的東西。
- [x] 2.4 執行 `python -m pytest scripts/test_build_site_data.py -q`，全數通過。
- [x] 2.5 執行 `python scripts/mutate_build_site_data.py`，全部變異皆被偵測、漏網為 0，且**未驗證項為 0**。⚠️ **必須先把 `docs/index.html` 的改動提交**：有 8 項變異要改真檔再以 git 還原，該檔不乾淨時它們會被跳過，總數顯示 77／85 但工具會印「未驗證不等於通過」。實測第一次跑就是這樣。⚠️ 必須在 2.1 重新產生頁面**之後**才跑：頁面過期時 `test_existing_pages_still_reproduce` 會讓每個變異都「被偵測」，結果全是假陽性。

## 3. 文件

- [x] 3.1 在 `docs/發布判定紀錄.md` 的 `index.html` 一列補記這次的涵蓋宣稱更正；判定結論維持「已凍結的歷史數據」（只改散文、未新增任何數字或推估）。
- [x] 3.2 在 `HANDOFF.md` 記錄：涵蓋宣稱**沒有機械檢查**在驗，相鄰的「選舉種類必須呈現或具名排除」那條有執行點、這條沒有；以及這次過期的成因是一句話同時承載「資料層未涵蓋」與「站台未呈現」兩種意思。
- [x] 3.3 執行 `spectra validate coverage-claim-data-vs-site --strict`，離開碼為 0。
