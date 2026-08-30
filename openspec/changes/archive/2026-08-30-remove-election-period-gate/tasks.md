## 1. 移除規範與紀錄

實作 design 決策「移除整個能力，而不是放寬其中的 Requirement」
與「刪除發布判定紀錄檔，而不是保留為純文件」
與「兩處跨能力引用改寫為不以選舉期間為條件」。

- [x] 1.1 刪除 openspec/specs/election-period-publication/spec.md 整個目錄。
      完成條件：openspec/specs/ 下剩 18 個能力目錄。
- [x] 1.2 刪除 docs/發布判定紀錄.md。
      完成條件：該檔不存在，且專案內除已歸檔 change 與 .spectra/snapshots/ 外
      沒有任何檔案讀取它。
- [x] 1.3 改寫 Requirement: A Translation Does Not Weaken A Qualifier。依 specs/site-translation/spec.md 的 delta 修改
      openspec/specs/site-translation/spec.md 的
      Requirement: A Translation Does Not Weaken A Qualifier。現屆聲明的 Scenario 移除
      「during an election period」前提，並新增一條 Scenario 明訂「沒有選舉在進行中」
      不是移除該聲明的正當理由。
- [x] 1.4 改寫 Requirement: The census does not decide inclusion and produces no derived figures。依 specs/mountain-township-chief-census/spec.md 的 delta 修改
      openspec/specs/mountain-township-chief-census/spec.md 的
      Requirement: The census does not decide inclusion and produces no derived figures。
      移除「including the publication rules that apply during an election period」
      子句，保留「納入與否是另一個判斷」的主張，並新增一條 Scenario 明訂
      清點結果乾淨不等於授權發布。

## 2. 移除建置期的強制機制

實作 design 決策「保留現屆聲明，因為它的真值不依賴這條規則」。

- [x] 2.1 從 scripts/build_site_data.py 移除 check_publication_record 與
      check_record_reason_consistency 兩個函式、PUBLICATION_RECORD 與
      ROOT_LEVEL_PUBLISHED 兩個常數，以及主流程中對 check_publication_record
      與 check_record_reason_consistency 的呼叫。連帶移除只服務這兩支的
      canonical_published_key、NO_DIRECTION_CLAIMS、DIRECTIONAL_MARKERS。
      並移除 check_frozen_indicator_shape 與 FROZEN_BOUNDS_SHAPE 及其呼叫——
      它是被移除的 Requirement: A Frozen Indicator Is Not Extended 的執行者，
      且其錯誤訊息指向已刪除的紀錄檔。
      ⚠️ 移除該檢查【不】改變任何已發布數字：界限估計的形狀仍是 5 屆 × 3 門檻，
      本 change 不動資料。移除的是「未來擴充會被擋下」這個保證。
      完成條件：模組匯入成功，且上述名稱在該檔零命中。
- [x] 2.2 確認 check_current_term_notice 函式、其主流程呼叫、STRINGS 中
      current_term_notice 的中英文字串**皆未被動到**。
      完成條件：該函式簽章與呼叫點與改動前逐字相同。
      ⚠️ 這是本 change 最容易被順手清掉的東西——它與被刪的兩支函式相鄰。
- [x] 2.3 從 scripts/test_build_site_data.py 移除
      test_publication_record_covers_every_page、
      test_publication_record_key_namespaces、test_record_reason_matches_page
      三個測試函式。
      完成條件：pytest 收集階段不再出現這三個名稱，且無 AttributeError。
- [x] 2.4 從 scripts/mutate_build_site_data.py 移除「發布判定紀錄的涵蓋與理由一致性」
      那一組變異項；**保留**所有針對 current_term_notice 的變異項。
      同時修正該檔中提及 check_publication_record 的過期註解——那些註解解釋的是
      限定語檢查為何從該函式拆出來，函式刪除後敘述已無對象。

## 3. 更新文件

實作 design 決策「文件中的能力數與 Requirement 數需同步」。

- [x] 3.1 README.md 移除「本專案自訂的限制」第 3 條（發布依選舉期程分階段），
      將原第 3 條之後的編號重排，並保留第 1 條（法律要求）與第 2 條（專案定位）。
- [x] 3.2 README.md「尚未解決」第 2 點移除「選舉期間不得定義這個指標」的整段限制，
      保留該指標在方法上為何困難的敘述（各縣市席次、選區、選舉人範圍不同）。
      完成條件：該點不再出現 2026-12-04 這個日期作為解禁條件。
- [x] 3.3 更新 README.md 與 HANDOFF.md 中的能力數與 Requirement 數：19 改為 18、
      110 改為 103。完成條件：執行 python scripts/check_doc_numbers.py，exit code 為 0，
      且輸出回報 18 個能力、103 條 Requirement。
- [x] 3.4 HANDOFF.md 移除 A′ 一節中「選舉期間不得定義」的阻擋敘述，改記
      本能力已於本次移除、該項現在可以做；能力表移除 election-period-publication 那列。
- [x] 3.5 HANDOFF.md 的「下一步」新增一條待辦：解凍不分區政黨票界限估計之前，
      須先查證公職人員選舉罷免法對民意調查發布的限制是否涵蓋由開票數推導的界限估計。
      明確記下本專案至今未查證過這一點。
- [x] 3.6 移除 AGENTS.md、CLAUDE.md、GEMINI.md、.spectra.yaml、
      docs/規劃-2026地方選舉.md 中對 election-period-publication 與發布判定紀錄的引用。
      完成條件：全文搜尋 election-period-publication 與「發布判定紀錄」，
      除 openspec/changes/archive/ 與 .spectra/snapshots/ 外零命中。

- [x] 3.7 清除指向已刪除的 docs/發布判定紀錄.md 的 @trace code 條目共 9 條：
      openspec/specs/site-district-geography/spec.md 4 條、
      openspec/specs/site-translation/spec.md 4 條、
      openspec/specs/site-data-generation/spec.md 1 條。
      ⚠️ 只刪 @trace 區塊裡那一行路徑，這三個 spec 的 Requirement 內容
      與發布閘無關，不得因此改動。
      完成條件：執行 python scripts/check_spec_traces.py，exit code 為 0。
- [x] 3.8 改寫 docs/legislative.html 與 docs/en/legislative.html 中解釋
      現屆聲明存在理由的 HTML 註解：現行說法是「本頁上線時已在選舉期間內」，
      改為說明該聲明陳述的是資料涵蓋到 2024 年這個事實。
      ⚠️ 只改註解。四頁的可見聲明文字一字不得更動。
- [x] 3.9 改寫 docs/schema/山地鄉鄉長資料清點.md 三處提及「涉及選舉期間發布規則」
      的敘述，保留「納入與否是另一個判斷」的主張，移除以選舉期間為由的部分。

## 4. 驗證

- [x] 4.1 執行 python scripts/build_site_data.py，直接檢查其 exit code 為 0。
      ⚠️ 不可將輸出接到 tail 或 head 再判斷成敗——管線的 exit code 是最後一個指令的，
      失敗的建置會回報 0。
- [x] 4.2 執行 python scripts/check_spec_traces.py，exit code 為 0，
      且回報涵蓋的能力數已由 17 降為 16。
- [x] 4.3 執行 pytest scripts/test_build_site_data.py，全數通過且無跳過項因
      找不到發布判定紀錄而產生。
- [x] 4.4 變異驗證：執行 scripts/mutate_build_site_data.py，確認針對
      current_term_notice 的變異項**仍然被抓到**。
      ⚠️ 這是保留現屆聲明有效的唯一證據——若該變異項在移除發布閘後變成通過，
      表示聲明已失去執行者，必須回頭修，不可視為變異項過期而刪除。
- [x] 4.5 人工檢視 docs/index.html、docs/legislative.html、docs/en/index.html、
      docs/en/legislative.html 四頁，確認現屆聲明文字仍在且與改動前逐字相同。
