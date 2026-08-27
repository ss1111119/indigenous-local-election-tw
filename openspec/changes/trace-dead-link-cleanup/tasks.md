## 一、先寫會失敗的檢查

- [x] 1.1 （實作 spec requirement「A trace entry points to something a reader can actually obtain」；design 決策 1：判準是「是否在 `git ls-files` 內」，不是「檔案是否存在」）新增 `scripts/check_spec_traces.py`，匯出 `collect_trace_entries()` 回傳 `list[tuple[能力, Requirement 名稱, 路徑]]` 與 `check_traces()` 回傳違規清單。判準為 `git -c core.quotepath=false ls-files` 的輸出。⚠️ 非 ASCII 路徑必須用該旗標，否則中文檔名會全部誤判為死鏈（本專案第一次量測就是這樣錯的）。
- [x] 1.2 （實作 spec requirement「The integrity check fails rather than degrades when it cannot do its job」；design 決策 1：判準是「是否在 `git ls-files` 內」，不是「檔案是否存在」的 ⚠️）在該腳本加入三個中止條件：取不到已入庫清單時中止並具名原因（**不可回退為「檔案是否存在」**）、找不到任何 spec 檔時中止、找不到任何 `@trace` 區塊時中止。錯誤訊息須逐條具名能力、Requirement 與路徑。
- [x] 1.3 執行 `python scripts/check_spec_traces.py`，確認它在**清理前**即失敗，且回報的違規數為 4,736（4,723 條 `scratch/` ＋ 13 條過期路徑）。⚠️ **這一步不可跳過也不可調換順序**——先清理再寫檢查的話，無法確認檢查真的抓得到東西。

## 二、清理

- [x] 2.1 剝除 12 個 spec 檔中所有指向 `scratch/` 的 `@trace` 條目（共 4,723 條）。只刪 `- scratch/…` 那些行，`@trace` 區塊本身、`source:`／`updated:`／`code:`／`tests:` 標頭與其餘條目一律保留。完成判準：`grep -rc "  - scratch/" openspec/specs/` 全部為 0。
- [x] 2.2 （實作 spec requirement 的 Scenario「A trace path names a file that has been moved」；design 決策 2：過期路徑修正而非刪除）將 13 條 `data/processed/cec-county-code-crosswalk-1998-2002.csv` 修正為 `data/reference/cec-county-code-crosswalk-1998-2002.csv`。**修正而非刪除**——該檔確實存在且已入庫，只是移動過。完成判準：`openspec/specs/` 下已無 `data/processed/cec-county-code-crosswalk` 字樣，且該 13 條指向的路徑在 `git ls-files` 內。
- [x] 2.3 執行 `python scripts/check_spec_traces.py` 確認轉為 exit 0，並記錄清理後的條目總數（**1,140**）。⚠️ 本任務原寫「預期 1,127」，那是**寫錯的**——1,127 是先前量到的「活著的條目數」，屬於**修正過期路徑之前**的數字，那 13 條當時指向 `data/processed/`、不在版控內而被算成死鏈。修正後它們變成活的：1,127＋13＝1,140，另一條路徑 5,863−4,723＝1,140，兩者一致，死鏈 0。**這個更正是逐項對帳後做的，不是為了讓數字對上而調整預期值。**

## 三、執行點與測試

- [ ] 3.1 （實作 spec requirement「The check has an execution point, and what it does not verify is written down」；design 決策 3：檢查必須有執行點，且放在既有的執行點檔案）在 `scripts/test_site_invariants.py` 新增一項呼叫 `check_spec_traces` 的檢查。完成判準：執行 `python scripts/test_site_invariants.py` 時輸出中可見該項，且在 spec 內插入一條 `scratch/x.py` 後該腳本會失敗。
- [ ] 3.2 為 `check_spec_traces.py` 補合成髒資料測試，涵蓋四種情形：指向未入庫路徑、取不到已入庫清單、找不到任何 spec 檔、找不到任何 `@trace` 區塊。每項須以合成輸入呼叫 `check_traces()` 或 `collect_trace_entries()`，且在該項防護被移除時失敗。
- [ ] 3.3 實測驗證檢查**能失敗**：暫時在任一 spec 的 `@trace` 內插入 `- scratch/x.py`，執行檢查確認 exit 1 且訊息含該路徑、所屬能力與 Requirement 名稱，然後還原。⚠️ 還原必須用 `try/finally` 或先備份，本 session 已有一次「變異腳本在還原前中止、把變異留在檔案裡」的紀錄。

## 四、記錄已知限制

- [ ] 4.1 （實作 spec requirement 的 Scenario「The cleanup makes the metadata look more reliable than it is」；design 決策 4：剩餘的不可靠性**寫下來**，不靜默留著）在 `HANDOFF.md` 新增一條地雷，記載三件事：(1) 清理只驗「路徑指得到」，**不驗溯源正確**；(2) 剩餘 1,127 條中，`CLAUDE.md`／`AGENTS.md`／`GEMINI.md`／`.spectra.yaml` 各出現在 73/83 個區塊、`README.md` 63、`HANDOFF.md` 53——出現在 88% 的 Requirement 上的檔案沒有指出任何東西；(3) 13 條 Requirement 完全沒有 `@trace`（`legacy-source-quirks` 4 條、`mountain-township-chief-census` 2 條、`mountain-township-chief-elections` 7 條），那是「未建立溯源」的標記，不補。
- [ ] 4.2 在 `HANDOFF.md` 同一條記下根因未解：`spectra task done` 仍是掃當下整個 git status（地雷 1i）。`scratch/` 於 2026-08-25 進 `.gitignore` 後該類污染在結構上停止（實測 `@trace` 依 `updated` 日期：08-20 至 08-24 共 66 個區塊 100% 含 `scratch/`，08-26 為 0/6），但**樣板檔那一類沒有結構性保證**——08-26 每區塊平均 7.3 條只是一天、六個區塊的資料。
- [ ] 4.3 執行 `git status` 確認 `data/processed/` 與 `docs/` 下 HTML 皆未修改，且變動範圍限於 12 個 spec 檔、兩支 `scripts/` 檔與 `HANDOFF.md`。
