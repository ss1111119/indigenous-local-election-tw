## Context

`@trace` 是 `spectra archive` 自動注入 spec 檔的溯源 metadata。實測顯示它已嚴重腐化：5,863 條路徑中 4,736 條（81%）指向未入庫的檔案。

腐化有兩層，**必須分開處理**，因為可判定性完全不同：

| 層 | 症狀 | 可否客觀判定 |
| --- | --- | --- |
| **死鏈** | 路徑指向不存在或未入庫的檔案 | **可以**——`git ls-files` 是明確的判準 |
| **雜訊** | 路徑存在，但與該條 Requirement 無關（樣板檔出現在 88% 的區塊） | **不行**——需要判斷「這個檔是不是這條 Requirement 的實作」，而該判斷無法驗證 |

本 change 只處理第一層。第二層記錄為已知限制。

⚠️ 量測時 `git ls-files` 預設會把非 ASCII 路徑輸出成跳脫字串，直接比對中文檔名會全部誤判為死鏈。必須加 `-c core.quotepath=false`。本專案第一次量測就是這樣錯的。

## Goals / Non-Goals

**Goals:**

- 剝除所有指向未入庫路徑的 `@trace` 條目，判準客觀可重現
- 修正路徑移動造成的過期條目，而不是刪除它們
- 讓清理**不會腐化**——加一個會失敗的檢查，且它有執行點
- 把「剩下的 trace 仍不可靠」與「13 條 Requirement 沒有 trace」記錄下來，而不是隱藏

**Non-Goals:**

- 不逐 Requirement 重建 trace（判斷無法驗證，且 `@trace` 目前沒有消費者）
- 不刪除跨區塊重複的樣板檔條目（閾值沒有依據）
- 不為缺 trace 的 Requirement 補 trace
- 不停用 `@trace` 機制
- 不改 `data/processed/`、不改 `docs/` 下任何 HTML

## Decisions

### 決策 1：判準是「是否在 `git ls-files` 內」，不是「檔案是否存在」

**選擇**：以 `git -c core.quotepath=false ls-files` 的輸出為準。

**理由**：「存在」不足以判定——`scratch/` 下的檔案在開發者本機**確實存在**，但不在版控內，任何人 clone 都拿不到。溯源的用途是讓別人找得到，判準必須是「別人拿得到嗎」。

⚠️ 這也意味著檢查在**沒有 git 的環境**下無法執行。該情況下腳本必須**中止並具名原因**，不可回退成「用檔案是否存在判斷」——那會讓 `scratch/` 條目在該環境下靜默通過。

### 決策 2：過期路徑修正而非刪除

**選擇**：13 條 `data/processed/cec-county-code-crosswalk-1998-2002.csv` 改為 `data/reference/…`。

**理由**：該檔確實存在且已入庫，只是移動過。刪除會失去真實的溯源關聯——那 13 條是「這條 Requirement 確實與縣市代碼對照表有關」的正確資訊，錯的只有路徑。

⚠️ 這一項是**逐案判斷**，不是通則。修正的前提是「同名檔案在別處且確為同一個檔」，本案由檔名與內容用途確認。若日後出現無法確認同一性的死鏈，一律剝除而非猜測新路徑。

### 決策 3：檢查必須有執行點，且放在既有的執行點檔案

**選擇**：新增 `scripts/check_spec_traces.py`，並由 `scripts/test_site_invariants.py` 呼叫。

**理由**：`test_site_invariants.py` 的 docstring 明文寫著它存在的理由是「缺的不是規則，是執行點」——`build_site_data.py --check` 早就抓得到問題，但沒有流程會跑它。新檢查若只是一支獨立腳本，會落入同一個坑。

**否決的替代方案**：只寫成獨立腳本、在 README 說明用法。否決理由同上——本專案已經為此付過代價。

### 決策 4：剩餘的不可靠性**寫下來**，不靜默留著

**選擇**：在 `HANDOFF.md` 新增一條地雷，記載：剝除後仍有 1,127 條，其中六個樣板檔各出現在 53–73 個區塊（共 83 個）；13 條 Requirement 完全沒有 trace。

**理由**：清理完之後，`@trace` 會**看起來**比清理前可信——路徑都指得到了。那正是它最危險的時候：下一個人可能把 `CLAUDE.md` 出現在某條 Requirement 的 trace 裡當成「這條 Requirement 與 CLAUDE.md 有關」。已知限制不寫下來，等於用清理製造了一個新的誤導。

## Implementation Contract

**Behavior**：執行 `python scripts/check_spec_traces.py` 時，逐一檢查 `openspec/specs/*/spec.md` 內所有 `@trace` 區塊的 `code:` 與 `tests:` 條目。全部指向已入庫檔案時 exit 0 並印出統計；否則 exit 1 並**逐條具名**（能力名稱、Requirement 名稱、違規路徑）。

**Interface / data shape**：
- 新增 `scripts/check_spec_traces.py`，可獨立執行
- 該腳本匯出 `collect_trace_entries()` 回傳 `list[tuple[能力, Requirement 名稱, 路徑]]`，與 `check_traces()` 回傳違規清單，供測試以合成輸入呼叫
- `scripts/test_site_invariants.py` 新增一項呼叫它的檢查

**Failure modes**：
- 任一 `@trace` 路徑不在 `git ls-files` 內 → exit 1，具名能力、Requirement 與路徑
- git 不可用（不在 repo 內、或 git 指令不存在）→ **exit 1 並具名原因**，不可回退為「用檔案存在判斷」
- `openspec/specs/` 下找不到任何 spec 檔 → exit 1（避免「零違規」來自零輸入）

**Acceptance criteria**：
- 清理後執行該腳本 exit 0
- 在任一 spec 的 `@trace` 內插入一條 `scratch/x.py` 後執行，exit 1 且訊息含該路徑與所屬能力
- `python scripts/test_site_invariants.py` 通過，且該檢查確實被執行到（輸出中可見）
- `openspec/specs/` 下 `grep -c "  - scratch/"` 為 0
- 13 條過期路徑已全部指向 `data/reference/`
- `git status` 確認 `data/processed/` 與 `docs/` 下 HTML 皆未修改

**Scope boundaries**：
- **In scope**：12 個 spec 檔的 `@trace` 區塊、`scripts/check_spec_traces.py`、`scripts/test_site_invariants.py`、`HANDOFF.md`
- **Out of scope**：spec 的 Requirement 本文與 Scenario、`data/processed/`、`docs/` 下任何 HTML、`spectra` CLI 本身的行為、逐 Requirement 重建 trace

## Risks / Trade-offs

- **[清理後 `@trace` 看起來比實際可信]** → 決策 4：把剩餘的不可靠性寫進 HANDOFF 地雷，並在檢查腳本的 docstring 明文說明它驗的是「路徑指得到」而**不是**「溯源正確」
- **[檢查在無 git 環境下退化]** → 決策 1 的 ⚠️：明文禁止回退，該情況中止並具名
- **[「零違規」可能來自零輸入]** → 腳本在找不到任何 spec 檔或任何 `@trace` 區塊時中止；測試另以合成輸入驗證它會失敗
- **[13 條路徑修正是逐案判斷，可能被當成通則]** → 決策 2 的 ⚠️ 明文限定前提；日後無法確認同一性者一律剝除

## Migration Plan

1. 先寫檢查腳本並確認它在**現況**下失敗（4,736 條違規）——先有會失敗的檢查，再去修
2. 剝除死鏈、修正過期路徑
3. 確認檢查轉為通過
4. 接上執行點並補測試
5. 記錄已知限制

⚠️ 第 1 步的順序不可調換。先清理再寫檢查的話，無法確認檢查真的抓得到——那正是本 change 要防的那類問題。
