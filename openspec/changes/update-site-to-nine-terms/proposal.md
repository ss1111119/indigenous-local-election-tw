## Why

資料集已於 2026-08-20 擴充至九屆（1994、1998、2002、2005、2006、2009-2010、2014、2018、2022），但站台仍停在四屆——`docs/index.html` 與 `docs/roster.html` 各自內嵌一份**手動維護**的資料常數，沒有任何腳本產生它們，所以資料集更新後站台不會跟上。這次不只要補上五屆，更要把「手動維護」這個結構性原因移除，否則下一次擴充還會再落後一輪。

## What Changes

- 新增 `scripts/build_site_data.py`：由 `data/processed/` 的三張長表產生兩份站台資料常數，**不連網、不手抄**。
- **先重現、再擴充**：腳本必須先產出與現有四屆常數**逐項相同**的數字；任何差異都要具名記錄後才可接受。這一步同時是驗證腳本、也是驗證站台現有數字是否正確。
- `docs/index.html` 的 `DATA` 常數改由腳本產生，涵蓋九屆。
- `docs/roster.html` 的 `D` 常數改由腳本產生，涵蓋九屆。
- **BREAKING（對站台讀者）**：名錄的當選標記改採 `elected_authoritative` 而非 `當選`。2005 縣市議員若沿用 `當選`，山原會少 12 席、平原少 7 席。
- 站台遵守 `is_main_sequence`：三個自訂選舉種類代碼（`T-PRV2`、`T-PRV3`、`T-COMBO`）不得進入任何跨屆折線，改以獨立區塊呈現。
- 該屆不存在的選舉種類維持以 `×` 標示，不以 `0` 填補（沿用既有慣例）。

## Capabilities

### New Capabilities

- `site-data-generation`: 由長表產生站台內嵌資料常數的規則與驗證——涵蓋數字重現、主序列過濾、當選權威值的採用，以及缺屆的表示方式。

### Modified Capabilities

(none)

## Impact

- Affected specs: `site-data-generation`（新增）；遵守 `historical-terms-1994-2006` 既有的 Comparability Flags 需求
- Affected code:
  - New:
    - `scripts/build_site_data.py`
    - `scripts/test_build_site_data.py`
  - Modified:
    - `docs/index.html`
    - `docs/roster.html`
    - `README.md`
  - Removed: （無）
