<!-- SPECTRA:START v1.0.2 -->

# Spectra Instructions

This project uses Spectra for Spec-Driven Development(SDD). Specs live in `openspec/specs/`, change proposals in `openspec/changes/`.

## Use `/spectra-*` skills when:

- A discussion needs structure before coding → `/spectra-discuss`
- User wants to plan, propose, or design a change → `/spectra-propose`
- Tasks are ready to implement → `/spectra-apply`
- There's an in-progress change to continue → `/spectra-ingest`
- User asks about specs or how something works → `/spectra-ask`
- Implementation is done → `/spectra-archive`
- Commit only files related to a specific change → `/spectra-commit`

## Workflow

discuss? → propose → apply ⇄ ingest → archive

- `discuss` is optional — skip if requirements are clear
- Requirements change mid-work? Plan mode → `ingest` → resume `apply`

## Parked Changes

Changes can be parked（暫存）— temporarily moved out of `openspec/changes/`. Parked changes won't appear in `spectra list` but can be found with `spectra list --parked`. To restore: `spectra unpark <name>`. The `/spectra-apply` and `/spectra-ingest` skills handle parked changes automatically.

<!-- SPECTRA:END -->

<!-- 以下內容在 SPECTRA 管理區塊之外，Spectra 重新產生指令檔時不會覆蓋。 -->

## 交接狀態

接手這個專案前先讀 `HANDOFF.md`（repo 根目錄）。它記的是「現在停在哪裡、下一步做什麼、
哪些地雷會靜默出錯」，包含：

- 進行中的 Spectra change `include-1994-2006-terms` 的產出物完成度與中斷點
- 尚未寫進產出物、只存在於對話裡的六個設計決策
- 五個**不會報錯但會產生錯誤數字**的來源地雷（代碼欄尾隨空白、縣市代碼逐檔重編、
  人口欄層級限制、2005 當選註記壞掉、站台資料是手動維護的內嵌常數）
- 四項先前文件寫錯過的事實更正

專案本身的說明在 `README.md`。`HANDOFF.md` 只寫交接資訊，不重複 README。
