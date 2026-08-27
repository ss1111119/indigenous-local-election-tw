## 一、先寫會失敗的檢查

- [x] 1.1 （實作 spec requirement「A recorded classification states a reason that matches what the page contains」）在 `scripts/build_site_data.py` 新增 `check_record_reason_consistency()`：解析 `docs/發布判定紀錄.md` 逐頁判定表的「理由」欄，若某列的理由含「無方向性的量」而該頁 HTML 含方向性字樣（`個百分點`、`上升`、`下降`、`落差`、`差距`），即中止並具名該頁與矛盾處。⚠️ 措辭清單與字樣清單**以實作為準**，本任務描述須與 `NO_DIRECTION_CLAIMS`／`DIRECTIONAL_MARKERS` 逐項相符——2026-08-27 外部覆核抓到本任務原寫「`+` 開頭的數字」而實作沒有該項。
- [x] 1.2 執行該檢查，確認它在**修正理由之前**即失敗，且具名 `index.html`。⚠️ **順序不可調換**——先修理由再寫檢查的話，無法確認檢查真的抓得到。
- [x] 1.3 ⚠️ 在函式 docstring 明寫這條**只驗機械可判定的矛盾**（理由聲稱「無方向性」而頁面有方向性字樣），**不驗理由本身是否正確**——後者需要人看。不寫的話，下一個人會把「檢查通過」讀成「判定正確」。

## 二、修正判定理由

- [x] 2.1 修正 `docs/發布判定紀錄.md` 中 `index.html` 那一列的理由：改以「逐票全查，值由已公告的官方結果與版控中的計算式決定，**無推估**」為依據，並**明文記載該頁含有方向性敘述**（`+3.08／+1.00`、`+4.98／+0.56`、`下降 5.83 個百分點`），以及為什麼那不使它成為解讀性指標（兩問中的第一問不成立）。⚠️ **不改頁面內容**——那些敘述是可發布的凍結歷史數據。
- [x] 2.2 逐一檢視其餘五列的理由是否與各自頁面內容矛盾。發現矛盾者一併修正；未發現者在本任務記錄「已逐列檢視、未發現其他矛盾」，不得只改一列就宣稱全部一致。
- [x] 2.3 執行 1.1 的檢查，確認轉為通過。

## 三、README 納入涵蓋範圍

- [x] 3.1 （實作 spec requirement「The record covers what is published, not only what is HTML」）在 `docs/發布判定紀錄.md` 新增 `README.md` 一列，記載內容類別（含地方公職九屆投票率與跨屆變化欄）、判定、理由、判定日期。
- [x] 3.2 修改 `check_publication_record()`，把 `README.md` 納入涵蓋檢查。**紀錄表維持現狀的人類可讀鍵**（`index.html`、`en/index.html`），檢查內部轉成 repo-relative canonical path 再比對。實作要求：(a) 明確區分兩個命名空間——docs-relative（`index.html` → `docs/index.html`）與 root-relative allowlist（目前只有 `README.md`）；(b) 轉換後只比較 canonical path；(c) **拒絕含 `../`、絕對路徑、或不屬於任一命名空間的鍵**並具名。
  ⚠️ 不可把未分類的字串直接混進同一集合。外部覆核列出的五個具體失效：根目錄新增 `CHANGELOG.md` 被誤當成 `docs/CHANGELOG.md`；`README.md` 與 `docs/../README.md` 造成別名；把 `docs/index.html` 填進要求 docs-relative 的欄位而變成 `docs/docs/index.html`；`../` 或絕對路徑逃出預期根目錄；第二個根目錄公開檔案出現時特例逐漸散落。
- [x] 3.3 在該函式的 docstring 記錄**涵蓋範圍的邊界**：目前涵蓋 `docs/**/*.html` 與 `README.md`；其餘 `.md`（如 `docs/schema/` 下的說明文件）不納入，並寫下理由。⚠️ 依 spec 的 Scenario「A file type is deliberately left out of scope」，排除必須具名且有理由，不可靜默。

## 四、補判例

- [x] 4.1 （實作 spec requirement「Comparing two rates each taken within one counted population does not by itself require estimation」）本項由 delta spec 的三個 Scenario 完成，無程式碼變更。完成判準：`openspec/changes/publication-record-consistency/specs/election-period-publication/spec.md` 含該 Requirement 及其三個 Scenario，且 `spectra validate` 通過。
- [x] 4.2 在 `docs/發布判定紀錄.md` 的判準說明段落補一句指向該判例：「兩個各自在單一計數母體內取得的比率相減，仍屬凍結歷史數據；但若任一側是以某母體代理另一母體、或以界限法推估未計數的子群，則整個比較繼承該推估。」

## 五、測試與驗證

- [x] 5.1 在 `scripts/test_build_site_data.py` 新增測試，涵蓋五種情形：理由聲稱「無方向性的量」而頁面含方向性字樣時中止並具名該頁、**理由未作該聲稱時不因該檢查中止**、`README.md` 缺列時 `check_publication_record()` 中止、紀錄列了不存在的檔案時中止、紀錄鍵含 `../` 或絕對路徑時中止。每項以合成輸入呼叫，不依賴真實檔案內容。
  ⚠️ **不得寫「斷言同義措辭抓不到」的測試。** 那會把當前的不完整性釘死成契約——日後擴充 `NO_DIRECTION_CLAIMS` 時該測試會失敗，而失敗的理由是「檢查變強了」。限制寫在 docstring，不寫成行為斷言。
  ⚠️ 但「理由未作該聲稱時不中止」**要測**：它不是釘死漏洞，是防止檢查退化成「只要頁面有方向性字樣就失敗」。
- [x] 5.2 在 `scripts/mutate_build_site_data.py` 新增對應變異：理由一致性檢查空轉、README 被移出涵蓋範圍。⚠️ 會被變異的模組必須在測試檔的**模組層級** import（HANDOFF 地雷 1n 第 4 種：`sys.path` 污染會讓函式內的 import 載到未變異模組，症狀是單獨跑失敗、一起跑通過）。
- [x] 5.3 執行 `python scripts/mutate_build_site_data.py`，確認全部變異被偵測、基準對照通過、無測試被跳過。任一變異未被偵測時補測試，不調降判準。
- [x] 5.4 執行 `python scripts/build_site_data.py --check` 與 `python scripts/test_site_invariants.py`，兩者皆須通過。
- [x] 5.5 執行 `git status` 確認 `docs/` 下只有 `docs/發布判定紀錄.md` 變動、`docs/*.html` 與 `docs/en/` 逐位元組未變、`data/processed/` 未變動。
