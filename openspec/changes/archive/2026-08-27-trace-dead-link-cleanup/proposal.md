## Why

`openspec/specs/*/spec.md` 的每條 Requirement 底下有 `spectra archive` 自動注入的 `@trace` 區塊，記錄「這條 Requirement 涉及哪些檔案」。實測（2026-08-27）：

- 全部 83 個 `@trace` 區塊共 **5,863 條路徑**
- 其中 **4,736 條指向未入庫的檔案**（81%）
- 死鏈組成：**4,723 條指向 `scratch/`**（該目錄在 `.gitignore` 內，`git ls-files scratch` 為 0 筆）、**13 條指向 `data/processed/cec-county-code-crosswalk-1998-2002.csv`**（該檔實際位於 `data/reference/`，路徑移動後 metadata 未同步）

任何人 clone 這個 repo，八成的溯源指向不存在的檔案。

成因記於 `HANDOFF.md` 地雷 1i：`spectra task done` 記的 touched files 是掃當下整個 git status。`scratch/` 於 2026-08-25 加進 `.gitignore`（commit `eee5ac0`）後，該類污染在結構上停止——實測 `@trace` 依 `updated` 日期的分布，08-20 至 08-24 共 66 個區塊 **100% 含 `scratch/`**，08-25 為 7/11，**08-26 為 0/6**。

⚠️ 但根因**沒有**被修掉：`spectra task done` 仍是掃整個 git status，只是 `scratch/` 不再出現在其中。同型污染仍會發生——剝除死鏈後剩下的 1,127 條裡，`CLAUDE.md`／`AGENTS.md`／`GEMINI.md`／`.spectra.yaml` 各出現在 **73/83** 個區塊、`README.md` 63 次、`HANDOFF.md` 53 次。出現在 88% 的 Requirement 上的檔案，沒有指出任何東西。

因此本 change 做兩件事：清掉客觀可判定的死鏈，並加上**會失敗的檢查**讓它不再腐化。

## What Changes

- 剝除所有 `@trace` 條目中指向未入庫路徑的項目（4,723 條 `scratch/`）
- 將 13 條過期路徑由 `data/processed/cec-county-code-crosswalk-1998-2002.csv` 修正為 `data/reference/cec-county-code-crosswalk-1998-2002.csv`（**修正而非刪除**——那是路徑移動，刪掉會失去真實關聯）
- 新增檢查腳本：所有 `@trace` 路徑必須存在且已入庫，且不得出現在 `.gitignore` 涵蓋的目錄下；違反即以非零退出並逐條具名
- 該檢查納入 `scripts/test_site_invariants.py` 的執行範圍，使其在既有測試流程中被跑到
- 在 `HANDOFF.md` 記錄剩餘的已知限制：1,127 條中含大量跨區塊重複的樣板檔、13 條 Requirement 完全沒有 `@trace`

## Non-Goals

- **不逐 Requirement 重建 trace**：83 個區塊各需讀該 change 的完整 diff 再判斷「哪個檔實作了這條 Requirement」。那個判斷是主觀的且**沒有 oracle 可以驗證對錯**，而 `@trace` 在本 repo 目前沒有任何消費者。拿不可驗證的判斷覆蓋現有資料，等於把「已知不可靠」換成「看起來可靠但仍不可靠」
- **不刪除跨區塊重複的樣板檔條目**：判準會是「出現在超過 N% 區塊就刪」，而 N 由本專案自訂、沒有依據。`README.md` 出現 63 次裡可能真有幾次是該條 Requirement 的實作位置，無法分辨
- **不為 13 條沒有 trace 的 Requirement 補 trace**：沒有 trace 本身就是「未建立溯源」的標記，假造會讓它看起來已完成
- **不停用 `@trace` 機制**：08-26 之後產生的 trace 是乾淨且有用的（每區塊平均 7.3 條，對比先前約 80 條）
- **不修改 `spectra task done` 的行為**：那是外部 CLI，不在本 repo 內
- **不改任何資料或站台**：不動 `data/processed/`、不動 `docs/` 下任何 HTML

## Capabilities

### New Capabilities

- `spec-trace-integrity`: `@trace` 溯源條目的完整性——路徑必須指向實際存在且已入庫的檔案，路徑移動時修正而非刪除，以及「未建立溯源」與「溯源不可靠」兩種狀態必須被記錄而非隱藏

### Modified Capabilities

（無）

## Impact

- Affected specs: `spec-trace-integrity`（新）
- Affected code:
  - New: `scripts/check_spec_traces.py`
  - Modified: `openspec/specs/bounded-estimates/spec.md`, `openspec/specs/column-oracle-documentation/spec.md`, `openspec/specs/election-period-publication/spec.md`, `openspec/specs/historical-terms-1994-2006/spec.md`, `openspec/specs/indigenous-legislative-elections/spec.md`, `openspec/specs/legacy-source-quirks/spec.md`, `openspec/specs/party-list-votes/spec.md`, `openspec/specs/site-chart-accessibility/spec.md`, `openspec/specs/site-data-generation/spec.md`, `openspec/specs/site-heading-segmentation/spec.md`, `openspec/specs/site-multi-dataset/spec.md`, `openspec/specs/site-translation/spec.md`, `scripts/test_site_invariants.py`, `HANDOFF.md`
  - Removed: (none)
