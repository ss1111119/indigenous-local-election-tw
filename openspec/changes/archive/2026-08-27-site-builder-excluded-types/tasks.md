## 一、先重現，再修

- [x] 1.1 執行 `python scripts/build_site_data.py --check`，確認它目前以 `KeyError: ('D1-MT', '1998')` 中止，並記下堆疊指向 `build_index_data()` 的哪一行行為（`totals[k]` 直接索引）。⚠️ **先確認重現再改**——沒有重現就無法確認修的是這件事。
- [x] 1.2 執行 `python scripts/test_site_invariants.py`，確認 `test_embedded_constants_match_long_tables` 目前失敗。⚠️ 同時確認該失敗**在 `git show HEAD~1` 的版本也存在**，以證明這是既有回歸而非本輪引入。

## 二、具名排除登記

- [x] 2.1 （實作 spec requirement「An election type present in the data is either presented or excluded by name」）在 `scripts/build_site_data.py` 新增常數 `SITE_EXCLUDED_TYPES`，鍵為選舉種類代碼、值為排除理由字串。登記 `"D1-MT"`，理由記明「資料層已納入（7 屆 187 個單位），站台呈現待 2026-12-04 公告當選人名單後決定；依 design 決策 8 該種類刻意不產生檔別合計列」。
- [x] 2.2 在 `build_index_data()` 的種類迴圈中，於取 `totals[k]` 之前判斷：該種類若在 `SITE_EXCLUDED_TYPES` 內則跳過並**不**列入輸出；若不在登記內且該屆缺檔別合計列，則**中止並具名該種類與屆別**。⚠️ 不可用 `totals.get(k)` 靜默略過——那正是本 change 要防的行為。完成判準：`python scripts/build_site_data.py --check` 可執行完成。
- [x] 2.2b （實作 spec requirement「A presented type's national figures come from the source's own aggregate row」）確認修正**沒有**引入「由明細列加總補出全國數字」的路徑：`build_index_data()` 取全國選舉人數與投票數時，仍只讀 `層級 == "檔別合計"` 的列並相加（T2／T3 的 `city` 與 `prv` 是互斥劃分，兩列都要加），缺該列的種類走排除或中止，**不得由鄉鎮市區列合成**。完成判準：在 `build_index_data()` 內 grep 不到任何對非檔別合計層級做選舉人數／投票數加總的程式碼。
- [x] 2.3 確認排除的種類**完全不出現在站台輸出**：`build_index_data()` 回傳的 `types` 清單不含 `D1-MT`，且重新產生的 `docs/` HTML 與現況逐位元組相同（本 change 不更新站台內容）。

## 三、驗證

- [x] 3.1 執行 `python scripts/test_site_invariants.py`，確認全數通過（含 `trace-dead-link-cleanup` 新增的 `test_spec_traces_point_to_tracked_files`）。
- [x] 3.2 在 `scripts/test_build_site_data.py` 新增測試，涵蓋三種情形：已登記的種類被排除且不出現在輸出、未登記且缺檔別合計的種類會中止並具名、已登記種類的理由字串非空。每項以合成 summary 資料呼叫，不依賴真實長表。
- [x] 3.3 在 `scripts/mutate_build_site_data.py` 新增對應變異：把中止改成靜默跳過、把排除登記清空。確認兩者皆被 3.2 的測試偵測到。⚠️ 若該腳本以 `pytest -k` 篩選測試，新增的測試必須加進篩選字串（HANDOFF 地雷 1j）。
- [x] 3.4 執行 `python scripts/mutate_build_site_data.py`，確認全部變異被偵測、基準對照通過、無測試被跳過。
- [x] 3.5 實測「移除登記會中止」：暫時把 `D1-MT` 從 `SITE_EXCLUDED_TYPES` 移除，執行建置器確認中止且訊息具名 `D1-MT`，然後還原。⚠️ 還原用 `try/finally` 或先備份——本 session 已有一次「腳本在還原前中止、把變異留在檔案裡」的紀錄。

## 四、文件與範圍

- [x] 4.1 在 `docs/schema/cec-local-election.md` 的 `D1-MT` 投影層一節補上一句：該種類已登記於站台建置器的排除清單，站台呈現待 2026-12-04 後決定。
- [x] 4.2 執行 `git status` 確認 `docs/` 下只有 `docs/schema/cec-local-election.md` 變動、`docs/*.html` 與 `docs/en/` 皆未變動、`data/processed/` 未變動。
