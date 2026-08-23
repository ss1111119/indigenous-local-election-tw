## 1. 判定紀錄

- [x] 1.1 新增 `docs/發布判定紀錄.md`：宣告 `投票日`（含來源；查不到就明文標為「未查證」）與目前階段，並以固定欄位的表格逐頁列出 `docs/` 下每一個 HTML 的判定（欄位：頁面、內容類別、判定、理由、判定日期）。三頁的判定依「決策 2 的兩問」逐頁寫出理由：`index.html` 與 `roster.html` 為逐票全查、無方向 → 已凍結的歷史數據；`legislative.html` 前三節同；第四節需推估且帶方向 → 解讀性指標，處置為保留＋標示＋凍結（使用者 2026-08-23 判定）。落實需求 `Every Published Page Carries A Recorded Classification` 與 `An Interpretive Indicator Is Distinguished From Frozen Historical Data`，以及「決策 2：「解讀性指標」的判準是兩問，兩問皆是才算」與「決策 4：判定紀錄是一份表，且**每一頁都必須在表裡**」。⚠️ 投票日**不可寫一個沒查證的日期**——本專案在 `EXPECTED_INDIGENOUS_ELECTORS` 上犯過「未量測就標成普查值」的同一類錯。查證來源限中選會公告；查不到就標未查證，並依「決策 1：階段界線由**宣告值**決定，且未查證時從嚴」把階段設為選舉期間。驗證方式：檔案存在且表格恰有三列，欄位名與上列五個完全相同；投票日欄位非空；若投票日為「未查證」則階段欄必須是「選舉期間」。

- [x] 1.2 在 `scripts/build_site_data.py` 加入 `CURRENT_TERM_NOTICE` 模組層常數（本節為歷史數字、不代表 2026 年本屆選舉結果的具名措辭）與 `check_publication_record()`：兩個方向驗涵蓋（`docs/*.html` 每一個都在表裡、表裡每一列的檔案都存在），並對判定為含歷史選舉數字的頁面驗其含 `CURRENT_TERM_NOTICE`。落實 `Every Published Page Carries A Recorded Classification` 的三個情境，以及「決策 4：判定紀錄是一份表，且**每一頁都必須在表裡**」——要守的不變量是涵蓋，不是判定內容。⚠️ 標示的檢查**必須比對 `CURRENT_TERM_NOTICE` 這個具名字串**，不可比對「2026」——頁尾的 `更新：2026-08` 本來就含 2026，用年份當判準的檢查在標示被刪掉後照樣通過（「決策 5：標示的檢查比對**具名字串**，不是「有沒有提到 2026」」）。驗證方式：三種失敗各造一次並斷言中止且訊息含該檔名——（a）表裡刪掉 `legislative.html` 那一列、（b）表裡加一列指向不存在的 `docs/nosuch.html`、（c）判定為歷史數字的頁面移除標示。

- [x] 1.3 在 `docs/發布判定紀錄.md` 宣告被凍結的指標及其**形狀**（政黨傾向界限：5 屆 × 3 門檻），並在 `scripts/build_site_data.py` 加入 `check_frozen_indicator_shape()`：`BOUNDS` 的屆別數與門檻數必須等於宣告值，不符即中止。落實需求 `A Frozen Indicator Is Not Extended`，以及「決策 3：已判定為解讀性指標者，選前的處置是「保留＋標示＋凍結」」。⚠️ 凍結的意思是**形狀不長大**，不只是數字不更新——多一屆、多一個門檻、多一個政黨分類都算擴充，即使既有的每個數字都沒變。這條檢查把「不得擴充」變成會失敗的東西，而不是一句叮嚀。驗證方式：把宣告值改成 6 屆，斷言中止且訊息含「凍結」與實際屆數；還原後通過。

## 2. 站台標示

- [x] 2.1 在 `docs/legislative.html` 的政黨傾向區塊加入 `CURRENT_TERM_NOTICE`，且與界限數字在**同一個可複製的區塊**（`.bnd`）內，與既有的涵蓋率限定語同一處理方式。落實 `Publication Is Phased Around The Election` 的情境 `Historical material is retained during the election period`。⚠️ 不可放在頁尾或 `<footer>`——限定語與數字分開，讀者複製一段貼到別處時限定語不會跟著走，那正是 `bounded-estimates` 已經處理過的失效形態。驗證方式：以指令確認三個 `.bnd` 區塊各自都含該字串；並斷言該字串出現在區塊內而非只出現在頁面其他位置（比對字元位置落在 `.bnd` 的起訖之間）。

- [x] 2.2 `python scripts/build_site_data.py --check` 仍三頁全綠：`index.html` 與 `roster.html` 的既有屆別逐鍵重現，`legislative.html` 的 `LEG` 與 `BOUNDS` 與長表一致。⚠️ 2.1 動到 `legislative.html` 的位元組，而 `--check` 對該頁的斷言是「資料未變 → 檔案未變」；標示是靜態 HTML、不在標記行上，所以應當仍然通過——若不通過表示改到了常數行，必須查明而不是重跑 `--write` 蓋過去。驗證方式：`--check` 退出碼為 0 且輸出三個 ✓；並以 `git diff --stat` 確認本次對 `legislative.html` 的改動不含 `const LEG = ` 或 `const BOUNDS = ` 開頭的行。

## 3. 文件

- [x] 3.1 `README.md`「發布上的限制」由兩條擴為三條，新增的第三條是時序規則（選前／選舉期間／結果確認後各准許什麼），並指向 `docs/發布判定紀錄.md`。落實 `Publication Is Phased Around The Election`。驗證方式：以指令確認該節含「選舉期間」與 `發布判定紀錄` 兩個字串，且既有兩條（個資、不預測）仍在。

- [x] 3.2 在 `docs/規劃-2026地方選舉.md` 頂端加一段狀態說明：文中的「本站」指相鄰的 `indigenous-constitution-tw` 而非本 repo；其「建議的下一步」第 1-3 項（對齊 elprof 欄位語意、確認 city 與 prv 的關係、確認三屆欄位語意一致）在本 repo 已完成；其分階段規則已於本變更寫入本 repo 的 spec。⚠️ **不要改寫該文件的本文**——它是 2026-08-18 那次覆核的紀錄，改掉本文等於竄改當時的判斷依據；只在頂端加狀態說明。驗證方式：以指令確認頂端新增段落含「本站」與「已完成」，且文件的既有行數未減少。

- [x] 3.3 `HANDOFF.md` 地雷區新增一條：選舉期間的發布規則存在、預設從嚴、且判定紀錄的涵蓋是機器驗的。並更新第一節的 change 數與 Requirement 數。驗證方式：以指令確認 `HANDOFF.md` 含「發布判定紀錄」，且第一節的 Requirement 數與 `openspec/specs/` 實際計數相符。

## 4. 測試與變異

- [x] 4.1 擴充 `scripts/test_build_site_data.py`：涵蓋兩個方向、標示存在、標示位置在 `.bnd` 內、投票日未查證時階段須為選舉期間。⚠️ 每一條 Failure mode 都要有一組會觸發它的輸入，且斷言錯誤訊息含**只有該檢查會輸出的字串**。驗證方式：`pytest scripts/test_build_site_data.py` 通過，且該檔的檢查項數比變更前增加不少於 8 項。

- [x] 4.2 擴充 `scripts/mutate_build_site_data.py`，新增四項變異並確認全部被偵測：（1）紀錄表刪掉 `legislative.html` 那一列；（2）`docs/legislative.html` 移除 `CURRENT_TERM_NOTICE`；（3）把標示檢查改成比對字串 `2026`；（4）投票日為未查證時把階段寫成「選前」。⚠️ 第 3 項是「決策 5：標示的檢查比對**具名字串**，不是「有沒有提到 2026」」的證明：它必須**通過基準**（因為頁面本來就含 2026），且在第 2 項變異下**漏網**——所以它不能用一般變異的方式驗，要像 `@reports` 承重那樣成對驗：有具名字串的檢查抓得到第 2 項、改成比對 `2026` 之後抓不到。⚠️ 變異若要動到 `docs/` 下的真檔，該檔必須先提交乾淨，且每個被變異的檔各需一個 canary。驗證方式：執行後輸出「全部通過」，每個 canary 皆被抓到，基準對照通過。
