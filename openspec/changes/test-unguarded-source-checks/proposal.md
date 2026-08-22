## Why

地方公職建置的變異測試有 **10 項一直漏網**（59 項中 49 偵測）。實測插樁量測後確認：**那 9 個判斷式全部執行過**（到達 1–20 次），**條件成立次數全部為 0**。

它們不是死碼，是「這批資料剛好沒發生」。也就是說——**這 10 個守衛目前沒有任何測試在證明它們還有用**。把其中任何一個改成 `if False:`，`pytest` 全綠、建置照樣通過、輸出位元組不變。下次來源變壞時，沒有人會知道它們早就失效了。

⚠️ `HANDOFF.md` 原本記的判準（「上游已保證的防禦性檢查是冗餘死碼，該刪不該補」）已於 2026-08-22 由量測推翻並更正——**沒有一項該刪**。

技術已在 `scripts/test_build_legislative_election.py` 的 `test_synthetic_dirty_data` 驗證過：立委那支用同一套做法把 20 項漏網修到 0。

## What Changes

- 為那 10 項守衛各建立一份**會觸發它的合成輸入**，補進 `scripts/test_build_local_election.py`
- 合成方式為「取真實 parts 深拷貝後改一格」，不新建合成壓縮檔——已實測可行
- 三項守衛不在 `cross_validate` 流程上，各自從其所在函式驅動
- 變異測試腳本的漏網數由 10 降為 0

**不改任何建置邏輯**：長表三檔與 `validation-report.json` 的 SHA-256 必須不變。

## Non-Goals

- **不刪除任何守衛**。量測已證明沒有死碼。
- **不新建合成壓縮檔**。已實測「改真實 parts」足以驅動 `cross_validate` 上的八項；另兩項各自直接呼叫其所在函式。合成 zip 成本高一個量級且無額外辨識力。
- **不重構建置腳本**。若某個守衛難以從外部驅動，優先設計輸入而不是改動被測程式——改被測程式來遷就測試會讓測試失去獨立性。
- **不處理站台端**（`scripts/mutate_build_site_data.py` 已 27 項全數偵測到）。
- **不動立委那支**（已 28 項全數偵測到）。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `legacy-source-quirks`: 現有條文規範「具名記錄 ＋ 補償性檢查」，但未要求那些補償性檢查本身必須被證明有效。新增一條：守衛必須有一份會觸發它的輸入，否則等同未受測。

## Impact

- Affected specs: `legacy-source-quirks`（修改）
- Affected code:
  - Modified:
    - `scripts/test_build_local_election.py`
    - `HANDOFF.md`
  - New: 無
  - Removed: 無
