## Why

本專案目前能回答「原住民在原住民立委那張票上投給誰」，但不能回答
「原住民的政黨傾向」——原住民立委多為無黨籍或地方勢力，與政黨標籤不是同一回事。
要回答後者需要政黨票（不分區），而政黨票是全體選民一起投的，沒有按族別分開計票。

⚠️ **這個問題先前只在對話裡被回答過，檔案裡沒有任何產物。** 那些數字（國民黨在
原住民選區得票率遠高於全國）無法重現、沒有任何檢查在守、也沒有寫明方法與範圍。
本變更的目的是讓它變成可重現、可審查、且**範圍被明確限定**的產出。

實作前的完整普查（五屆逐檔，非抽樣）確認資料就在既有的
`data/raw/cec-votedata.zip` 內，不需要新來源：

- `不分區政黨` 五屆（2008／2012／2016／2020／2024），**投開票所層級**
- 與原住民立委的投開票所鍵可接：2008／2012／2016／2020 為 100%，2024 為 99.3%
- 政黨票逐所加總 **＝** 該所有效票，五屆皆 0 筆不符
- 新增兩個本專案未處理過的檔：`elrepm`（不分區政黨代表人）與
  `elretks`（不分區政黨得票），語意取自壓縮檔內的官方格式文件

⚠️ **`elrepm` 帶出生日期／出生地／學歷**，與 `elcand` 同類個資，一律不輸出。

## What Changes

新增第三個資料集：政黨票長表。並在其上建立**受範圍限定的**原住民政黨傾向指標。

指標**不是單一估計值**，而是「觀察值 ＋ 數學上必然的區間」。區間用
Duncan-Davis 極限法：給定該層觀察到的得票率 y 與投票者中原住民佔比 q，
原住民的支持率必然落在 `[max(0,(y-(1-q))/q), min(1, y/q)]`。這個區間
**不依賴任何統計假設**，只依賴算術，因此可以拿來當建置時的守門員。

分三個門檻輸出（實測 2024）：

| 門檻 | 所數 | 涵蓋原住民選舉人 | 國民黨區間寬 |
| --- | ---: | ---: | ---: |
| ≥95% | 90 | 11.0% | 3.0pp |
| ≥90% | 172 | 20.7% | 4.8pp |
| ≥80% | 237 | 28.4% | 7.5pp |

## Non-Goals

- **不做生態迴歸外推到佔比 = 1。** 八成以上的投開票所原住民佔比低於 20%，
  迴歸斜率會被非原住民與都市原住民定錨，外推到 1 落在樣本支援之外。
  它的失效是靜默的：數字看起來精確，可能已經毫無意義。
- **不宣稱涵蓋全體原住民。** 三個門檻都只涵蓋原住民族地區，
  都市裡的平地原住民（佔 31.8%）全在門檻外，極限法對他們給不出有用的界限。
- **不把估計值與官方數字放在同一個資料表或同一組欄名。**
- **不輸出 `elrepm` 的出生日期／出生地／學歷。**
- **不處理 2016 的 `old/` 重複目錄。** 專案已有具名排除。
- 不處理總統票、區域立委票、公投——本變更只做不分區政黨票。

## Capabilities

### New Capabilities

- `party-list-votes`: 不分區政黨票五屆的建置與驗證
- `bounded-estimates`: 估計值與官方數字的分層、以及可失敗的界限守門員

### Modified Capabilities

(none)

## Impact

- Affected specs: party-list-votes、bounded-estimates
- Affected code:
  - New: scripts/build_party_list_election.py
  - New: scripts/test_build_party_list_election.py
  - New: scripts/mutate_build_party_list_election.py
  - New: docs/schema/cec-party-list-election.md
  - New: data/processed/cec-party-list-summary-long.csv.gz
  - New: data/processed/cec-party-list-votes-long.csv.gz
  - New: data/processed/cec-party-list-seats.csv
  - New: data/processed/indigenous-party-preference-bounds.csv
  - New: data/processed/party-list-validation-report.json
  - Modified: scripts/oracles.py
  - Modified: data/sources.json
  - Modified: README.md
  - Modified: HANDOFF.md
