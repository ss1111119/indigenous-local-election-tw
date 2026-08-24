## 1. 鍵盤可達性（`bind()`）

- [x] 1.1 修改 `docs/index.html` 的 `bind(el, text)`：`pointerenter` 與 `focus` 共用顯示邏輯、`pointerleave` 與 `blur` 共用隱藏邏輯，`pointermove` 只在指標裝置生效（focus 時 tooltip 定位在該元素旁，不需要滑鼠座標）。所有既有的透明 hit target 補上 `tabindex="0"` 使其可 Tab 到達。落實需求 `Hover-Only Content Is Also Reachable By Keyboard` 的兩個情境，以及「決策 1：`bind()` 同時處理 hover 與 focus，不是另外寫一套」。⚠️ 不可寫成兩套邏輯（一套給滑鼠、一套給鍵盤）——本專案已經因為「同一規則兩處實作」出過兩次 bug。驗證方式：以指令確認 `bind()` 函式體同時監聽 `focus`／`blur`；瀏覽器手動測試——不用滑鼠、純鍵盤 Tab 能到達投票率圖與政黨席次圖的每個資料點，且 Enter/Tab 觸發的 tooltip 內容與滑鼠 hover 顯示的逐字相同。

- [x] 1.2 對 `docs/legislative.html` 套用同一份 `bind()` 改動（依「決策 3：立委頁只做鍵盤可達性，不做導航」，**不**加導航連結）。落實同一條需求，範圍限於立委頁既有的 tooltip 觸發元素（投票率、政黨得票率折線、政黨席次堆疊條）。驗證方式：瀏覽器手動測試 Tab 能到達立委頁每個資料點並顯示 tooltip；以指令確認 `legislative.html` 的圖表元素沒有被包進 `<a href="roster.html...">`（決策 3 的邊界）。

## 2. 巨觀連結微觀（僅 `index.html`）

- [x] 2.1 修改 `docs/index.html` 的 01 投票率折線圖：每個資料點的透明 hit target 改用 `svgEl("a", {href: \`roster.html#${year}/${t.code}\`, "aria-label": ...})` 包住，讓滑鼠點擊、鍵盤 Enter、觸控點按三種輸入都導向 `roster.html` 對應的屆別與選舉種類。落實需求 `A Chart Point Representing A Term And Category May Link To Its Detail Page` 的情境 `A turnout or seat chart point is activated` 與 `The link target is native, not scripted`，以及「決策 2：可導航的 hit target 用 `<a>` 包 SVG 元素，不是 JS 監聽 click 再手動導頁」。⚠️ 只對 `MAIN`（進主序列）的資料點加連結，`CUSTOM`（自訂代碼）那組不在本節範圍內（04 節，見任務 1 的 Non-Goals）。驗證方式：以指令確認新增的 `<a>` 元素的 `href` 值涵蓋 `YS` 與 `MAIN` 的每一個實際存在的 `(year, type)` 組合；瀏覽器手動測試點擊任一資料點，確認導向的 `roster.html#屆別/代碼` 頁面顯示的是同一屆同一選舉種類的名錄。

- [x] 2.2 修改 `docs/index.html` 的 02 政黨席次堆疊條：每個政黨區段同樣包 `<a href="roster.html#${year}/${t.code}">`（區段本身不分政黨導向不同頁面——政黨層級的名錄篩選超出 `roster.html` 既有雜湊格式，導向整個屆別＋選舉種類即可）。落實同一條需求。驗證方式：以指令確認每個政黨區段的 `<g>` 或其 hit target 被 `<a>` 包住；瀏覽器手動測試點擊任一區段能到達對應屆別的名錄。

- [x] 2.3 把 1.1、2.1、2.2 對 `docs/index.html` 做的改動，逐位元組同步到 `docs/en/index.html`，唯一差異是連結目標改為 `../roster.html#${year}/${code}`（「決策 4：英文頁的連結目標固定指向中文版 `roster.html`」：名錄沒有英文版）。落實 `site-translation` 既有的「兩版 JS 完全相同」規則。⚠️ 這不是新規則，是既有規則的延伸應用——检查沿用 `test_english_pages_share_the_same_data` 的精神。驗證方式：以指令比對兩份檔案的 `<script>` 內容，除了連結路徑的 `../` 前綴與 `T`／`L`／`DATA` 常數之外，其餘程式碼逐行相同；瀏覽器手動測試英文頁的資料點點擊後導向中文版 `roster.html`。

## 3. 測試與變異

- [x] 3.1 擴充 `scripts/test_build_site_data.py`：斷言 `bind()` 監聽 `focus`／`blur`；斷言 `index.html` 與 `en/index.html` 的可導航連結涵蓋 `DATA` 裡 `MAIN` 每一個實際存在的 `(year, type)`（用「兩邊 (year, type) 集合相等」驗證，不逐一測連結，依 Implementation Contract 的 Failure modes）；斷言 `legislative.html` 沒有任何 `<a href="roster.html`。⚠️ 每一條 Failure mode 都要有一組會觸發它的輸入，且斷言錯誤訊息含只有該檢查會輸出的字串。驗證方式：`pytest scripts/test_build_site_data.py` 通過，且該檔的檢查項數比變更前增加不少於 6 項。

- [ ] 3.2 擴充 `scripts/mutate_build_site_data.py`，新增三項變異並確認全部被偵測：（1）拿掉 `bind()` 的 focus 監聽（只留 pointerenter，模擬「鍵盤使用者拿不到 tooltip」的迴歸）；（2）可點擊的 hit target 改回不含 `<a>` 包裝的普通元素（模擬「導航消失」的迴歸）；（3）立委頁被誤加上導航連結（模擬決策 3 被違反）。驗證方式：執行後輸出「全部通過」，三項皆被偵測到，基準對照通過，無測試被跳過。

## 4. 文件

- [ ] 4.1 `README.md` 或 `docs/發布判定紀錄.md` 視需要註記本次改動不影響任何頁面的判定分類（純導航與可及性，未改變任何資料或算式）；`HANDOFF.md` 地雷區新增一條：`bind()` 的 focus／blur 與 pointerenter／pointerleave 是同一段邏輯，未來加新圖表要沿用它、不要另寫一套。驗證方式：以指令確認 `HANDOFF.md` 含「focus」與「bind()」。
