## 1. 修過期的測試篩選器

- [x] 1.1 把 `test_legislative_oracle_rendered_into_shared_document`、`test_manifest_rendering_reflects_new_columns`、`test_population_is_valid_decimal`、`test_oracle_document_written_atomically` 加進 `mutate_build_legislative_election.py` 的 `SEL` 字串，實作 Requirement「Shared verification helpers carry mutation-test proof of discriminating power」的「A mutation-test script's selection filter is not silently stale」情境。驗證：在 `mutate_build_legislative_election.py` 裡臨時印出 `SEL` 篩選後、對 `test_build_legislative_election.py` 執行 `pytest -k SEL -q --collect-only`，確認這四個測試函式名稱出現在收集到的清單裡。
- [x] 1.2 把 `test_party_list_oracle_rendered_into_shared_document` 加進 `mutate_build_party_list_election.py` 的 `SEL` 字串，實作同一個情境。驗證：對 `test_build_party_list_election.py` 執行 `pytest -k SEL -q --collect-only`，確認這個測試函式名稱出現在收集到的清單裡。

## 2. 立委腳本的真檔變異

- [x] 2.1 在 `mutate_build_legislative_election.py` 新增一項真檔變異：把 `scripts/oracles.py` 的 `check_population_column` 裡 `if not pop.is_finite():` 那個判斷拿掉，實作 Requirement「Shared verification helpers carry mutation-test proof of discriminating power」的「check_population_column has a real-file mutation」情境。驗證：用該腳本既有的變異測試機制（`prepare()` 加 `run()` 或等效流程）手動套用此變異，確認 `test_population_is_valid_decimal` 由通過變成失敗（`Infinity`／`NaN` 那幾個情境不再拋出例外），再撤銷變異、確認測試恢復通過。
- [x] 2.2 在 `mutate_build_legislative_election.py` 新增一項真檔變異：把 `scripts/oracles.py` 的 `write_oracle_document` 改成在寫入前直接 `return`，跳過寫入本身，實作「write_oracle_document has a real-file mutation」情境。驗證：手動套用此變異，確認 `test_oracle_document_written_atomically` 由通過變成失敗（檔案內容與 `render_markdown()` 當下輸出不一致），再撤銷變異、確認測試恢復通過。
- [x] 2.3 把任務 2.1、2.2 的兩項變異併入 `mutate_build_legislative_election.py` 的 `main()` 變異迴圈中。驗證：執行 `python scripts/mutate_build_legislative_election.py`，確認這兩項新變異與既有全部變異項目皆回報偵測到，沒有漏網。

## 3. 政黨票腳本的真檔變異

- [x] 3.1 在 `mutate_build_party_list_election.py` 新增一項真檔變異：把 `scripts/oracles.py` 的 `render_markdown()` 裡呼叫 `_render_manifest_sections(PARTY_LIST_MANIFEST, ...)` 那一行拿掉，實作「_render_manifest_sections has a real-file mutation covering the party-list call site」情境。驗證：用該腳本既有的變異測試機制（`fresh_copies()` 加 `run()` 或等效流程）手動套用此變異，確認 `test_party_list_oracle_rendered_into_shared_document` 由通過變成失敗（政黨票三個區塊標題消失），再撤銷變異、確認測試恢復通過。
- [x] 3.2 把任務 3.1 的變異併入 `mutate_build_party_list_election.py` 的 `main()` 變異迴圈中。驗證：執行 `python scripts/mutate_build_party_list_election.py`，確認這項新變異與既有全部變異項目皆回報偵測到，沒有漏網。
