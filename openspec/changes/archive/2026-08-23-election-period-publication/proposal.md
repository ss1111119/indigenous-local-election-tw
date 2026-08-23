## Why

2026 年地方公職人員選舉在 2026-11 舉行，現在是 2026-08。本專案的規劃文件
`docs/規劃-2026地方選舉.md` 於 2026-08-18 經兩輪外部覆核，定案了一套
**選前／選舉期間／結果確認後**的分階段發布規則，兩個覆核者的共識之一是
「選前只做歷史比較安全」的推論站不住——歷史落差在選戰期間同樣會被當成攻防工具。

**那套規則從未寫進本 repo。** 主 spec 八個能力、60 條 Requirement 中，
與發布有關的只有兩條（個資不輸出、立委與地方資料分開發布），
沒有任何一條約束「什麼時候可以發布什麼」。規則只存在於一份狀態標示為
「構想，未進入 Spectra」的文件裡，而該文件描述的「本站」其實是相鄰的
`indigenous-constitution-tw`，本 repo 的讀者不會把它當成自己的約束。

其後果已經發生：2026-08-23 發布的 `docs/legislative.html` 帶有政黨傾向區塊，
呈現原住民族地區高密度投開票所的不分區政黨票界限（2008-2024）。
那正是選戰中最容易被截取為攻防素材的數字形態，而發布時沒有任何書面規則
可供對照判斷它該不該在選前上線。

## What Changes

- 新增能力 `election-period-publication`，把分階段規則寫成 Requirement：
  選前只發布方法、資料字典、已凍結的歷史數據與固定計算規則；
  選舉期間凍結新增的解讀性指標；正式結果確認後才發布本屆彙總。
- 定義「解讀性指標」與「已凍結的歷史數據」的判準，使一個新產出可以被逐條判定，
  而不是靠當下的直覺。
- **對既有三頁逐頁做一次判定並留下紀錄**，包含判定理由與判定日期。
  已發布的東西不因新規則自動下架，但必須有一次明文判定。
- 依判定結果，在呈現歷史數字的頁面加上「不代表本屆結果」的標示。
- 更新 `README.md` 的「發布上的限制」，把兩條擴充為含時序的規則。
- 更新 `docs/規劃-2026地方選舉.md` 的狀態：它的「下一步」第 1-3 項
  在本 repo 已完成，且文中的「本站」指相鄰 repo，不加註會誤導下一個讀者。

## Capabilities

### New Capabilities

- `election-period-publication`: 選舉期間的發布規則——什麼時候可以發布什麼、
  既有產出如何逐項判定、判定紀錄如何留存

### Modified Capabilities

(none)

## Impact

- Affected specs: `election-period-publication`（新增）
- Affected code:
  - New: `openspec/specs/election-period-publication/spec.md`
  - Modified: `README.md`、`HANDOFF.md`、`docs/規劃-2026地方選舉.md`、
    `docs/legislative.html`、`scripts/test_build_site_data.py`、
    `scripts/mutate_build_site_data.py`
  - Removed: （無）
