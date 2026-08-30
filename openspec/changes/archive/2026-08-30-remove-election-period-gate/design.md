## Context

`election-period-publication` 是本專案 19 個能力中唯一管「發布時機」的，其餘 18 個管正確性。
它定義三階段（選前／選舉期間／結果確認後）與一組兩問測試，判定一個數字是
「解讀性指標」還是「已凍結的歷史數據」，並要求每一個已發布頁面都在
發布判定紀錄裡有一筆判定。

它由建置期兩支函式強制：`check_publication_record` 驗涵蓋（缺頁中止、記錄指到
不存在的頁也中止）、`check_record_reason_consistency` 驗判定理由與頁面內容不矛盾。
兩者都會讓建置中止。

移除它的理由不是它寫得不好，而是**它不是法律要求**。`README.md` 把不輸出出生日期／
學歷那條明確標為「這是法律要求」，分階段發布那條沒有這個標記——它是自訂的編輯立場。
而它正在擋著地方層級代表性指標與界限估計解凍。

## Goals / Non-Goals

**Goals:**

- 移除三階段發布閘與兩問測試，使「現在是選舉期間」不再是任何工作的阻擋理由。
- 移除發布判定紀錄，以及強制它的兩支建置檢查。
- 讓現屆聲明文案在閘門移除後**仍有執行者**，不變成一條沒人驗的規定。
- 清乾淨跨能力引用，不留下指涉已刪除能力的散文。

**Non-Goals:**

- 不刪除四個 HTML 的現屆聲明文案。
- 不刪除 README 第 2 條（不產出本屆預測或選情指標）——那條管定位不管時機。
- 不解凍界限估計、不定義代表性指標。移除閘門讓它們不再被擋，但各自是獨立判斷。
- 不修改已歸檔 change 的散文內容。歸檔件是歷史紀錄，不隨現況改寫。

## Decisions

### 移除整個能力，而不是放寬其中的 Requirement

替代方案是保留能力、把「選舉期間不得新增解讀性指標」改成建議而非強制。
不採用：兩問測試、三階段、判定紀錄三者互相定義，拆掉強制力之後剩下的是一組
沒有效力的分類詞彙，讀者會以為它還有約束力。半留比全刪更容易誤導。

### 保留現屆聲明，因為它的真值不依賴這條規則

「本節為 2008–2024 年的歷史數字，不代表 2026 年本屆選舉結果」是一句**事實陳述**：
資料確實只到 2024。刪掉這條規則不會讓它變成假的。刪掉它只會讓頁面少一句真話，
且不解鎖任何東西。

⚠️ 關鍵查證：它由 `check_current_term_notice` 執行，該函式獨立於發布判定紀錄、
由主流程獨立呼叫。因此保留文案在閘門移除後仍是可執行的規定，不會靜默失效。

### 刪除發布判定紀錄檔，而不是保留為純文件

替代方案是留著該檔當歷史紀錄。不採用：它的每一列都是依兩問測試做的判定，
測試移除後那些判定沒有判準可依歸；留著會讓下一個人以為判準還在。
它的內容仍可由 git 歷史取得。

### 兩處跨能力引用改寫為不以選舉期間為條件

`site-translation` 有一條 Scenario 要求翻譯頁在選舉期間呈現歷史數字時必須帶現屆聲明。
既然聲明要保留，該 Scenario 也保留，但移除「選舉期間」這個前提條件——
否則條件所指的階段定義已不存在。

`mountain-township-chief-census` 有一句散文說納入判斷受選舉期間發布規則約束，
移除該子句，保留「納入與否是另一個判斷」這個主張本身。

### 文件中的能力數與 Requirement 數需同步

`check_doc_numbers.py` 驗證文件裡的能力數與 Requirement 數與實際相符，
移除 7 條 Requirement 與 1 個能力後該檢查會中止，`README.md` 與 `HANDOFF.md`
的對應數字須一併更新。這是刻意設計的攔截點，不是要繞過的障礙。

## Implementation Contract

**Behavior**：建置在移除後**不再因發布判定紀錄而中止**。不存在發布判定紀錄檔、
不存在階段判定，任何新數字的發布不再需要通過兩問測試。四個已發布 HTML 的
現屆聲明文字**不變**，且移除聲明仍會使建置中止。

**Interface**：`build_site_data.py` 不再匯出 `check_publication_record`、
`check_record_reason_consistency`、`PUBLICATION_RECORD`、`ROOT_LEVEL_PUBLISHED`。
`check_current_term_notice` 的名稱、簽章與呼叫點不變。

**Failure modes**：移除任一 HTML 的現屆聲明 → 建置中止並指名該頁（既有行為，須保持）。
文件數字與實際不符 → `check_doc_numbers.py` 中止（既有行為，須保持）。
`@trace` 指向不存在路徑 → `check_spec_traces.py` 中止（既有行為，須保持）。

**Acceptance criteria**：

1. `python scripts/build_site_data.py` 成功且 exit code 為 0
   （⚠️ 不可用管線接 tail 判斷成敗，管線的 rc 是最後一個指令的）。
2. `python scripts/check_doc_numbers.py` exit code 0，回報 18 個能力、103 條 Requirement。
3. `python scripts/check_spec_traces.py` exit code 0。
4. `pytest scripts/test_build_site_data.py` 全數通過，且測試檔中針對已刪除函式的
   測試案例一併移除（保留它們會 import 失敗，而不是靜默通過）。
5. 變異測試：`mutate_build_site_data.py` 中針對已刪除函式的變異項一併移除；
   針對 `check_current_term_notice` 的變異項**必須保留且仍會被抓到**——
   這是證明保留文案仍受保護的唯一證據。
6. 專案內全文搜尋 `election-period-publication` 與「發布判定紀錄」，
   除已歸檔 change 與 `.spectra/snapshots/` 外零命中。

**Scope boundaries**：

- In scope：spec 移除、判定紀錄刪除、兩支檢查與其測試／變異項移除、
  README 第 3 條移除、跨能力引用改寫、文件數字更新、`@trace` 清理。
- Out of scope：任何 HTML 文案改動、界限估計解凍、代表性指標定義、
  `D1-MT` 站台呈現（它被 `site-multi-dataset` 的合計列規定擋著，與本 change 無關）。

## Risks / Trade-offs

[移除後失去唯一管發布時機的機制，日後若想恢復需重寫] → 內容可由 git 歷史取回；
本 change 的 proposal 記下了移除理由，恢復時可據以判斷理由是否仍成立。

[保留的現屆聲明失去所屬能力，變成孤立規定] → 它仍屬 `site-translation`
（翻譯頁那條 Scenario）與 `check_current_term_notice`，兩者都保留，不是孤立的。

[界限估計解凍後可能觸及公職人員選舉罷免法對民意調查發布的限制] → 本 change
不解凍任何東西，該風險不由本 change 引入。但解凍是移除閘門後才變得可能的動作，
因此在 `HANDOFF.md` 留下待辦：解凍前須先查證該法是否涵蓋由開票數推導的界限估計。
本專案至今**未查證過**這一點。

[已歸檔 change 的散文仍提及本能力，讀者可能以為它還在] → 歸檔件本就是歷史紀錄，
不隨現況改寫；`HANDOFF.md` 記下本能力已於本次移除，作為索引。
