## Why

本專案有三個資料集，但**站台只呈現其中一個**。`docs/index.html` 與
`docs/roster.html` 提到「立委」的次數是 **0**，`build_site_data.py` 只讀
`cec-local-election-*` 兩張表。原住民立委（九屆，2026-08-21 完成）與
不分區政黨票（五屆，2026-08-23 完成）都已建置、驗證、歸檔，卻沒有出口。

**讀者設定為一般讀者與媒體**，這個設定改變了設計的重心。

⚠️ **最大的風險不是讀者看不懂 `p` 與 `q`，是記者拿走「原住民 68% 投國民黨」
就發稿。** 那句話講的是佔比 ≥95% 的 90 個投開票所、涵蓋 11.0% 的原住民
選舉人、全在原住民族地區的山地鄉，不含都市裡的平地原住民（約三成）。

所以主軸**不能**是政黨票的界限。本專案手上有一組**涵蓋全體原住民選民、
零推論**的資料可以當主軸：原住民立委選舉的政黨得票率——那張票只有
原住民能投，分母就是全體原住民選民。

| 屆別 | 國民黨 | 第二名 | 第三名 |
| --- | ---: | --- | --- |
| 1995 | 77.0% | 無黨 13.3% | 中國台灣原住民黨 4.4% |
| 2001 | 47.7% | 親民黨 27.7% | 民進黨 6.5% |
| 2016 | 49.0% | 民進黨 16.2% | 無黨團結聯盟 13.3% |
| 2024 | 41.4% | 無黨籍 32.9% | 民進黨 22.5% |

席次同向：國民黨 1995 年 6/6 → 2020／2024 剩 3/6，民進黨 0 → 2。

## What Changes

站台由「一個資料集」擴充為「三個資料集，明確分開」。

**新增立委頁**（主軸）：九屆的政黨得票率與席次、投票率、山地／平地分列。
全部是零推論的完整事實，任何引用方式都不會錯。

**新增政黨傾向區塊**（次要，明確隔開）：不分區政黨票的觀察值與界限。
標題寫「原住民族地區的 N 個投開票所」而非「原住民」，
且**涵蓋率與地理集中出現在任何百分比之前**。

`build_site_data.py` 擴充為讀三個資料集，並沿用既有的
「就地替換標記行 ＋ `--check` 驗重建等於現況」機制。

## Non-Goals

- **不把立委與地方公職畫在同一條折線上。** 兩者不是同一個母體——
  一個是全國單一選區的中央職位、一個是各縣市的地方職位。
  這與 `is_main_sequence` 擋的是同一類錯誤，但需要更強的分隔：
  不同頁面／區塊，不是同一份清單裡的一個旗標。
- **不改動地方公職既有的呈現。** 既有屆別的資料常數必須逐鍵重現。
- **不改倉庫名稱。** 名實是否相符等站台確定涵蓋範圍後再議，現在改是猜。
- **不做總統票、區域立委票、公投。**
- **不在站台上做任何新的統計推論。** 站台只呈現已在資料層算好並驗證過的
  數字；界限由 `indigenous-party-preference-bounds.csv` 讀入，不在前端重算。

## Capabilities

### New Capabilities

- `site-multi-dataset`: 站台同時呈現三個不同母體的資料集而不讓它們被誤讀為可比

### Modified Capabilities

- `site-data-generation`: 資料常數的來源由一個資料集擴充為三個
- `bounded-estimates`: 界限的呈現規則由「文件」擴及「站台」

## Impact

- Affected specs: site-multi-dataset、site-data-generation、bounded-estimates
- Affected code:
  - New: docs/legislative.html
  - Modified: scripts/build_site_data.py
  - Modified: scripts/test_build_site_data.py
  - Modified: scripts/mutate_build_site_data.py
  - Modified: scripts/palette_metrics.py
  - Modified: docs/index.html
  - Modified: docs/roster.html
  - Modified: README.md
  - Modified: HANDOFF.md
