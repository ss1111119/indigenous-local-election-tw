## 1. 算繪邏輯可重用化

- [x] 1.1 在 `scripts/oracles.py` 抽出內部輔助函式 `_render_manifest_sections(manifest, names)`，回傳指定 manifest 的 Markdown 行清單，讓 `render_markdown()` 改為呼叫這個輔助函式處理 `MANIFEST`，依循設計決定「`render_markdown()` 改為可重用的雙 manifest 算繪，不是新增第二支算繪函式」。實作 Requirement「Every declared column manifest is rendered into the shared oracle document」的「The local-election sections are unaffected」情境。驗證：對 `data/processed/` 現有的本地選舉長表執行 `python scripts/build_local_election.py`（或該腳本既有的執行方式），用 `git diff docs/schema/oracles.md` 確認本地選舉三個既有區塊的內容與變更前逐位元組相同。
- [x] 1.2 讓 `render_markdown()` 在既有的本地選舉三區塊之後，額外呼叫 `_render_manifest_sections(LEGISLATIVE_MANIFEST, {"legislative_summary": "立委選舉概況 summary", "legislative_candidates": "立委候選人 candidates", "legislative_votes": "立委候選人得票 votes"})` 並把輸出接在同一份文件裡，實作 Requirement「Every declared column manifest is rendered into the shared oracle document」的「The legislative manifest gains a rendered section」情境。驗證：新增測試呼叫 `render_markdown()`，斷言輸出字串同時含三個立委區塊標題，且每個區塊列出的欄位名稱集合與 `LEGISLATIVE_MANIFEST` 對應鍵的欄位名稱集合完全相同（不多不少）。
- [x] 1.3 新增測試驗證 manifest 新增欄位時算繪結果會跟著變，實作 Requirement「Every declared column manifest is rendered into the shared oracle document」的「A manifest gains a new column」情境。驗證：測試裡構造一份臨時的 manifest 字典（在既有 `LEGISLATIVE_MANIFEST` 基礎上多加一個假欄位），呼叫 `_render_manifest_sections` 或等效的公開介面，斷言輸出含這個假欄位名稱。

## 2. 立委腳本接上算繪與寫檔

- [x] 2.1 在 `scripts/build_legislative_election.py` 的 `main()` 收尾（`write_outputs(...)` 呼叫之後），依循設計決定「兩支腳本都呼叫同一個 `render_markdown()`，不做「誰該負責寫入」的協調機制」，加入 `(ROOT / "docs" / "schema" / "oracles.md").write_text(render_markdown(), encoding="utf-8")`，並比照 `build_local_election.py` 既有的同一行加上「oracle 文件由 manifest 生成，手寫會脫節」註解。驗證：執行 `python scripts/build_legislative_election.py`，確認 `docs/schema/oracles.md` 檔案內容更新且含立委三個新區塊；再接著執行一次 `python scripts/build_local_election.py`，確認兩次執行後該檔案的位元組完全相同（互相覆寫不改變結果）。

## 3. 人口數輸入驗證

- [x] 3.1 在 `scripts/build_legislative_election.py` 新增函式 `check_population_is_valid_decimal(rows, label)`，比照 `build_local_election.py` 對 `人口數` 的既有驗證邏輯（`Decimal()` 可解析性、非負值），驗證失敗時拋出 `ValidationError` 並指名該筆資料的行政區識別，依循設計決定「`人口數` 驗證獨立成新函式，不塞進既有的 `check_manifest_against` 呼叫」，實作 Requirement「Population column has parity in self-verification across datasets」的三個情境（可解析性失敗、非負值失敗、合法值通過）。驗證：新增合成測試，構造一列 `人口數` 為 `"abc"`（非數字）的摘要資料與一列為 `"-5"`（負值）的摘要資料，分別餵給該函式，斷言兩者都拋出 `ValidationError` 且錯誤訊息可分辨是哪一種失敗（不同的訊息文字或例外屬性）；再構造一列 `"0"` 與一列含小數的字串（例如 `"1234.5"`），斷言兩者都不拋例外。
- [x] 3.2 在 `scripts/build_legislative_election.py` 的 `main()` 裡，於既有的 `check_manifest_against(LEGISLATIVE_MANIFEST, ...)` 呼叫之後加入對 `check_population_is_valid_decimal` 的呼叫，把三張表裡含 `人口數` 欄的摘要表傳入。驗證：對 `data/processed/` 現有的立委長表執行 `python scripts/build_legislative_election.py`，確認流程正常完成、不中止（證明現有真實資料本身合法，這個新驗證沒有誤殺）。
