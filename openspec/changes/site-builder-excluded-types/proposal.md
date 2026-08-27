## Problem

`python scripts/build_site_data.py` 目前**完全無法執行**，包含 `--check`：

```
File "scripts/build_site_data.py", line 318, in build_index_data
    tot = totals[k]
KeyError: ('D1-MT', '1998')
```

後果：**站台無法再重新產生**。`docs/` 下的 HTML 本身未受損、線上站台正常，但任何人 pull 下來都無法重建它。這個狀態已經在 `main` 上。

`scripts/test_site_invariants.py` 的 `test_embedded_constants_match_long_tables` 因此失敗——該檔存在的理由正是「缺的不是規則，是執行點」，而它抓到的第一件事就是這個。

## Root Cause

`include-mountain-township-chief`（2026-08-27 歸檔）把 `D1-MT` 加進三份長表，其 design 決策 8 明文規定 **`D1-MT` 不產生檔別合計列**——D1 的檔別合計涵蓋全部 319 個鄉鎮市，縣市層級更是混合母體，沿用會產出一個標成 `D1-MT` 卻描述全體鄉鎮市長的數字。

但 `build_site_data.py` 的 `build_index_data()` 假設每個選舉種類都有檔別合計列：

- `election_types(summary)` **從長表推導**種類清單 → `D1-MT` 自動出現
- `totals` **只由 `層級 == "檔別合計"` 的列建立** → `D1-MT` 不在其中
- `totals[k]` 直接索引 → `KeyError`

該 change 的 Non-Goals 寫著「不進 `scripts/build_site_data.py` 的呈現層」。**把呈現層排除在範圍外，不等於可以讓建置器壞掉**——這是當時未追到底的消費者。

驗證不足也是成因之一：該 change 只跑了 `scripts/test_build_local_election.py`，未跑 `scripts/test_site_invariants.py`，而後者才是會抓到這件事的地方。

## Proposed Solution

在 `scripts/build_site_data.py` 新增一份**具名的排除登記**，記錄「哪些選舉種類在資料層但不在站台，以及理由」。`D1-MT` 登記為「資料層已納入，站台呈現待 2026-12-04 公告當選人名單後決定」。

⚠️ **未登記且缺檔別合計的種類一律中止**，不靜默跳過。靜默跳過的話，日後任何種類因為別的原因掉了彙總列，會從站台安靜消失且無錯誤訊息——本專案已為同類問題付過代價（1994-2005 的無黨籍席次被算成「其他」，在站台上活了一整天）。

## Non-Goals

- **不讓 `D1-MT` 出現在站台上**：那會推翻「站台呈現另案、選舉期間不單方面發布」這個經兩輪外部覆核做成的決定，且是當成修 bug 的副作用悄悄推翻
- **不由鄉鎮市區列加總補出 `D1-MT` 的全國數字**：同上
- **不改 `D1-MT` 在長表中的結構**：決策 8 的理由（混合母體、不製造來源沒有的數字）仍然成立
- **不重新產生 `docs/` 下的 HTML**：站台內容是否更新是另一個決定；本 change 只讓建置器能跑
- **不改任何資料**：不動 `data/processed/`

## Success Criteria

- `python scripts/build_site_data.py --check` 可執行完成（不再 `KeyError`）
- `python scripts/test_site_invariants.py` 全數通過
- 在排除登記中移除 `D1-MT` 後執行建置器會**中止並具名該種類**，而非靜默跳過或崩潰
- `docs/` 下的 HTML **逐位元組未變**
- `data/processed/` 未變

## Impact

- Affected specs: `site-multi-dataset`（修改）
- Affected code:
  - Modified: `scripts/build_site_data.py`, `scripts/test_build_site_data.py`, `scripts/mutate_build_site_data.py`, `docs/schema/cec-local-election.md`
  - New: (none)
  - Removed: (none)
