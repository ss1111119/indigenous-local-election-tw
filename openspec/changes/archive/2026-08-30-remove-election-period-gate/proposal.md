## Why

`election-period-publication` 這個能力把發布時機掛在選舉期程上：2026-08-20 至 12-04 之間，
不得新增任何「解讀性指標」。它擋著兩件本來可以做的事——地方層級代表性指標的定義、
以及不分區政黨票界限估計的解凍。

**它不是法律要求。** `README.md` 自己就把三條限制分開標示：不輸出出生日期／學歷那條
寫明「這是法律要求，不是本專案的價值判斷」，而分階段發布這條沒有這個標記。
它是本專案自訂的編輯立場，而自訂的立場擋不住實際工作時，應該撤掉而不是繞過。

## What Changes

- **BREAKING**：移除 `election-period-publication` 能力全部 7 條 Requirement。
- 刪除發布判定紀錄檔，以及建置期兩支強制它的檢查函式
  `check_publication_record` 與 `check_record_reason_consistency`。
- `README.md` 移除「發布依選舉期程分階段」那條限制。
- `site-translation` 與 `mountain-township-chief-census` 兩處引用改寫，
  不再以「選舉期間」為條件。

## Non-Goals

- **不刪除四個 HTML 的現屆聲明文案**（「本節為 2008–2024 年的歷史數字，
  不代表 2026 年本屆選舉結果」）。那句話陳述的是事實，不依賴本規則成立；
  它由獨立的 `check_current_term_notice` 執行，該函式與發布判定紀錄無關，
  刪掉發布閘不會讓它失去執行者。
- **不刪除 README 第 2 條限制**（不產出 2026 這屆的預測或選情指標）。
  該條管的是專案定位，不是發布時機。
- **本 change 不解凍界限估計、也不定義代表性指標。** 移除閘門只是讓那兩件事
  不再被本能力擋著；它們各自是獨立的判斷，需要各自的 change。
- **不查證公職人員選舉罷免法對民意調查發布的限制是否涵蓋界限估計。**
  該查證與本 change 無關——本 change 不發布任何新數字。但它是解凍界限估計
  之前必須先做的事，記在 `HANDOFF.md` 待辦。

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `election-period-publication`: 全部 7 條 Requirement 移除，能力整個刪除。
- `site-translation`: 現屆聲明的 Scenario 不再以「選舉期間」為前提條件。
- `mountain-township-chief-census`: 移除「納入判斷受選舉期間發布規則約束」的敘述。

## Impact

- Affected specs: `election-period-publication`（移除）、`site-translation`、
  `mountain-township-chief-census`
- Affected code:
  - Modified:
    - scripts/build_site_data.py
    - scripts/test_build_site_data.py
    - scripts/mutate_build_site_data.py
    - README.md
    - HANDOFF.md
    - AGENTS.md
    - CLAUDE.md
    - GEMINI.md
    - .spectra.yaml
    - docs/規劃-2026地方選舉.md
    - openspec/specs/site-translation/spec.md
    - openspec/specs/mountain-township-chief-census/spec.md
    - openspec/specs/site-district-geography/spec.md
    - openspec/specs/site-data-generation/spec.md
    - docs/legislative.html
    - docs/en/legislative.html
    - docs/schema/山地鄉鄉長資料清點.md
  - Removed:
    - docs/發布判定紀錄.md
    - openspec/specs/election-period-publication/spec.md
