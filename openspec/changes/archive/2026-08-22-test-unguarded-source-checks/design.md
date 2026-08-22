## Context

`scripts/mutate_build_local_election.py` 有 59 項變異，其中 **10 項一直漏網**。2026-08-22 以插樁量測九個判斷式（第 43 項不是判斷式，另計）在完整建置中的到達與成立次數：

| 變異 | 守什麼 | 到達 | 成立 | 所在函式 |
| --- | --- | ---: | ---: | --- |
| 30 | 投票數 > 選舉人數，非具名者中止 | 1 | 0 | `cross_validate` |
| 31 | 配錯選舉區時鄉鎮市區多重集合須相同 | 3 | 0 | `cross_validate` |
| 33 | 具名異常單位的上層級必須正常 | 3 | 0 | `cross_validate` |
| 34 | 鄉鎮市區代碼集合差異須可解釋 | 9 | 0 | `cross_validate` |
| 40 | 選舉區欄只能出現宣告的值 | 20 | 0 | `process_one` |
| 41 | 孤兒層級向上加總 = 父層級有效票 | 4 | 0 | `cross_validate` |
| 42 | 孤兒單位的父單位必須存在 | 4 | 0 | `cross_validate` |
| 44 | 忽略選舉區欄後候選人身分仍唯一 | 5 | 0 | `derive_elected_authoritative` |
| 45 | 孤兒層級須嚴格深於 elprof 最深層級 | 2 | 0 | `cross_validate` |

**沒有一項是死碼**——全部執行過，只是這批資料的條件沒成立。

⚠️ 量測本身踩過一次：第一版插樁腳本因 `if up is None:` 在檔內不唯一而改錯位置，建置失敗、九項全部顯示 0。若未印退出碼，全 0 會被讀成「都沒觸發」而推出「全是死碼、可以刪」的**相反結論**。這也是同一天修掉「變異字串必須唯一」的由來。

第 43 項形態不同：它不是「拿掉檢查」而是**移除鍵的選舉區正規化**，使四個直轄市檔的每一列都變唯一、唯一性檢查恆為真。屬於「斷言變空轉」而非「檢查被移除」。

## Goals / Non-Goals

**Goals:**

- 10 項守衛各有一份會觸發它的輸入，變異漏網數降為 0
- 既有三張長表與 `validation-report.json` 的 SHA-256 不變
- 每一條新測試都能指出「是哪一條檢查中止的」，而非只驗「有中止」

**Non-Goals:**

- 不刪除任何守衛（量測已證明無死碼）
- 不新建合成壓縮檔
- 不重構建置腳本以遷就測試
- 不動站台端與立委端的變異測試（兩者皆已全數偵測到）

## Decisions

### 合成方式：取真實 parts 深拷貝後改一格

`process_one` 回傳的 part 是純 dict（`summary`／`candidates`／`votes`／`file_total` 等皆為 list of dict），可 `copy.deepcopy` 後就地修改再餵給 `cross_validate`。

**已實測可行**：把 1998 T3 一個未具名鄉鎮市區的 `投票數` 設為 `選舉人數 + 1`，`cross_validate` 如期中止並指名該單位。

替代方案「合成整個 zip」被否決：成本高一個量級（要造 elbase／elcand／elctks／elprof 四個互相一致的檔），而辨識力相同——被測的是 `cross_validate` 的判斷式，不是讀檔層。讀檔層已有 `test_read_csv` 等既有測試涵蓋。

⚠️ 每個 probe **必須先確認基準通過**：未改動的 parts 餵進 `cross_validate` 要不中止。少了這一步，「中止」可能來自 parts 本身有問題而非合成的缺陷。

### 三個入口，不是一個

八項在 `cross_validate` 上，另兩項不是：

- **第 40 項在 `process_one` 內**（選舉區欄允許值的檢查在讀檔後、組裝前）。要驅動它得直接呼叫 `process_one`，或把該檢查的輸入（四個來源檔的第 3 欄取值集合）合成後呼叫其所在的檢查片段。
- **第 44 項在 `derive_elected_authoritative` 內**，且只在 `ignore_district=True` 時執行。要驅動它得直接呼叫該函式並傳入兩位「忽略選舉區欄後身分相同」的候選人。

⚠️ 實測探測時，第 44 項的第一版合成輸入**被另一條檢查先擋下**（錯誤訊息是「候選人複合鍵重複」而非身分唯一）。這是本專案已記錄的第三種假通過形態——**斷言必須比對只有專責檢查會說的話**，不能只驗有沒有中止。

### 第 43 項要斷言「正規化真的有發生」

它使唯一性檢查恆為真而非移除檢查，所以「中止／不中止」測不到。決定：斷言**四個直轄市檔在正規化前後的鍵集合大小不同**——正規化把選舉區欄壓成 `00`，若不做，鍵會因選舉區欄不同而多出若干個。這是可觀察且會因變異而改變的量。

### 測試放在既有檔案，不另立新檔

補進 `scripts/test_build_local_election.py`，理由是變異腳本的 `SEL` 已涵蓋該檔的測試選擇器，另立新檔要同步改 `SEL`、`prepare()` 的複製清單與基準對照，多三處可能不同步的地方。

## Implementation Contract

**行為**：執行 `python scripts/mutate_build_local_election.py` 後，59 項變異全部顯示「偵測到 ✓」，基準對照通過且無測試被跳過。執行 `pytest scripts/` 全數通過。重新建置後 `data/processed/` 既有四份輸出的 SHA-256 與本變更前相同。

**介面**：新增的測試為 `scripts/test_build_local_election.py` 內的函式，命名以 `test_` 開頭並納入該檔 `main()` 的執行清單；變異腳本的 `SEL` 選擇器必須涵蓋新函式名，否則變異跑不到它們。

**失敗模式**：每一條 probe 在合成缺陷後必須 `raise ValidationError`，且錯誤訊息必須包含**只有該條檢查會輸出的字串**（例如指名的單位鍵、或該檢查特有的措辭）。只斷言「有拋出例外」不算滿足契約。

**驗收**：
- `python scripts/mutate_build_local_election.py` 輸出「變異測試全部被偵測到」
- 每一條新測試在對應守衛被改成 `if False:` 時變紅——由變異腳本本身證明，不需另外人工確認
- 基準對照（未變異副本）通過且 `SKIP` 行數為 0
- `data/processed/cec-local-election-*` 三檔與 `validation-report.json` 的 SHA-256 不變

**範圍邊界**：**在範圍內**——`scripts/test_build_local_election.py` 的新測試、`HANDOFF.md` 的狀態更新、`legacy-source-quirks` 的一條新 Requirement。**在範圍外**——建置邏輯、站台端、立委端、合成壓縮檔、刪除任何守衛。

## Risks / Trade-offs

- **合成輸入被更早的檢查攔截** → 已實測發生於第 44 項。處置：斷言錯誤訊息中只有專責檢查會輸出的字串；若仍被攔截，調整合成輸入使其只違反目標檢查。
- **深拷貝真實 parts 使測試依賴原始壓縮檔** → 該檔不入版控。處置：比照既有 `test_legacy_terms`，找不到壓縮檔時記入 `skipped` 並在變異腳本的基準對照中要求 `SKIP` 為 0——跳過的測試不算通過。
- **10 條 probe 使該測試檔變長** → 集中在單一測試函式內，以小工具函式（`aborts_with`）收斂重複，並在檔頭說明這一組存在的理由。
- **第 40 項可能需要直接呼叫 `process_one`，執行時間較長** → 只跑一個最小的檔別（1998 T-COMBO 僅 10 名候選人），不跑既有四屆。

## Migration Plan

只新增測試，不改建置邏輯與輸出。回退方式為還原 `scripts/test_build_local_election.py`。既有的建置、站台產生、立委建置流程皆不受影響。

## Open Questions

- 第 40 項的最終驅動方式（直接呼叫 `process_one` 於既有小檔，或抽出該檢查片段單獨呼叫）待實作時依實測決定。兩者皆能滿足契約，差別在執行時間。
