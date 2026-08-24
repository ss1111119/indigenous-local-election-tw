#!/usr/bin/env python3
"""build_site_data.py 與其測試的變異測試。

**驗證通過不代表驗證有效。** 每一項變異都必須讓 pytest 非零退出；
還原後必須回到通過。有一項漏網就是那條檢查沒有辨識力。

用法：
    python scripts/mutate_build_site_data.py

⚠️ 檔名不可用 `*_test.py` 或 `test_*.py` 結尾，執行的部分也必須包在 `main()` 裡，
   否則 pytest 會把它當測試檔收集並在收集階段執行整套變異。
   姊妹檔 `mutate_build_local_election.py` 原名 `mutation_test.py`，
   實測就是這樣被跑了 52 秒後以 INTERNALERROR 收場。

⚠️ 兩件事是踩過坑才這樣寫的：

1. **在 pytest 下驗，不是直接執行測試檔。** 這個專案出過「直接執行 exit 1、
   pytest 卻報 passed」的事（見測試檔 @reports 的註解）。變異測試若只用直接
   執行來驗，那個坑會原封不動地回來。

2. **變異做在副本上，副本放在 repo 根目錄【正下方一層】（`_mut/`）。**
   測試檔以 `__file__.parent.parent` 推導 ROOT 去找 `docs/` 與 `data/`。
   深度錯了不會報錯，只會讓需要那些檔案的測試**靜默跳過而 pytest 仍報 passed**——
   於是變異看起來「被偵測到」或「測試通過」，其實那些斷言根本沒跑。
   放到系統暫存目錄會整組失效；放在 `scratch/mut/`（兩層）也一樣，
   姊妹檔 `mutate_build_local_election.py` 就曾因此讓迴歸測試全程未執行。

⚠️ 例外：`docs/index.html` 的變異**只能改真檔**。測試是用 node 執行 HTML 裡
   那兩行來驗前端過濾，而它讀的是 `ROOT/docs/index.html`；改副本測不到。
   那一項因此有額外的防護，見 mutate_index_html()。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUT = ROOT / "_mut"
HTML = ROOT / "docs" / "index.html"
COPIED = ("build_site_data.py", "test_build_site_data.py")

# (說明, 檔名, 原字串, 變異字串)
MUTATIONS = [
    # ---- 席次取自權威值 ----
    ("index：當選與否改用來源註記 `當選註記 == '*'`",
     'won = [c for c in rows if c["當選"] == "Y"]',
     'won = [c for c in rows if c["當選註記"] == "*"]'),
    ("index：選舉區內的席次改用來源註記（同額競選會算錯）",
     '                if c["當選"] == "Y":\n'
     '                    d["seats"] += 1',
     '                if c["當選註記"] == "*":\n'
     '                    d["seats"] += 1'),
    ("index：政黨當選數改用來源註記",
     '                if c["當選"] == "Y":\n'
     '                    party[b][0] += 1',
     '                if c["當選註記"] == "*":\n'
     '                    party[b][0] += 1'),
    ("roster：名錄標記整個改用來源註記",
     '    mark = row["當選註記"]\n'
     '    if mark in ("!", "-"):\n'
     '        return mark\n'
     '    return "*" if row["當選"] == "Y" else ""',
     '    return row["當選註記"]'),
    ("roster：`!` 不再原樣保留（婦女保障當選被寫成一般當選）",
     '    if mark in ("!", "-"):',
     '    if mark in ("-",):'),

    # ---- 分桶鍵 ----
    #
    # ⚠️ 下面三項裡，只有第一項在真實資料上會失敗。實測：對照表內的五個代號
    #    各自只對到一個名稱，全資料五組「同代號多名稱」全部落在表外。
    #    所以「只用代號」與「代號回退」在現有資料上的輸出與正確實作**完全相同**。
    #    它們之所以會被偵測到，靠的是 test_party_bucket_key_semantics 的合成斷言。
    #    把那個測試刪掉，這兩項就會變成漏網——這正是它存在的理由。
    ("分桶鍵改成只用名稱（舊屆的代號 99／無 會掉回其他）",
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    return {n: b for (c, n), b in PARTY_IDENTITY_BUCKETS.items()}.get(\n'
     '        row["政黨名稱"], OTHER_BUCKET)'),
    ("分桶鍵改成只用代號（真實資料看不出差別）",
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    return {c: b for (c, n), b in PARTY_IDENTITY_BUCKETS.items()}.get(\n'
     '        row["政黨代號"], OTHER_BUCKET)'),
    ("配對查不到時以代號回退（等同同代號自動合併）",
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    hit = PARTY_IDENTITY_BUCKETS.get((row["政黨代號"], row["政黨名稱"]))\n'
     '    if hit is not None:\n'
     '        return hit\n'
     '    for (c, n), b in PARTY_IDENTITY_BUCKETS.items():\n'
     '        if c == row["政黨代號"]:\n'
     '            return b\n'
     '    return OTHER_BUCKET'),
    ("分桶鍵改成鬆散的「代號在表內 and 名稱在表內」",
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    codes = {c for c, n in PARTY_IDENTITY_BUCKETS}\n'
     '    for (c, n), b in PARTY_IDENTITY_BUCKETS.items():\n'
     '        if row["政黨代號"] in codes and row["政黨名稱"] == n:\n'
     '            return b\n'
     '    return OTHER_BUCKET'),
    ("無黨籍改用子字串比對（會吸收無黨團結聯盟）",
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    if "無" in row["政黨名稱"]:\n'
     '        return "無黨籍及未經政黨推薦"\n'
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)'),
    ("把舊屆無黨籍那一筆從對照表移除（本次修正的本體）",
     '    ("99", "無"): "無黨籍及未經政黨推薦",\n',
     ''),

    # ---- 年齡：站台不得有第二份判準 ----
    ("站台改讀 年齡_原始 並自己重算判準（不讀已清乾淨的 年齡）",
     '            int(c["年齡"]) if c["年齡"] else None,',
     '            (None if (c["年度"] in {"1994","1998","2002","2005","2006"}\n'
     '                      and c["年齡_原始"] == "99") else int(c["年齡_原始"])),'),

    # ⚠️ 年齡判準本身的變異【不在這裡】。它已移到長表建置端，
    #    對應的變異在 scripts/mutate_build_local_election.py。
    #    站台端只剩「有沒有第二份判準」那條測試，見
    #    test_age_read_from_derived_column。

    # ---- 名錄的 MAIN 投影 ----
    ("MAIN 投影回到只認新屆的名稱（舊屆無黨籍在名錄拿到其他的顏色）",
     '    slot_of = {b: i for i, b in enumerate(PARTY_BUCKETS)}',
     '    slot_of = {b: i for i, b in enumerate(PARTY_BUCKETS)}\n'
     '    return {n: i for i, n in enumerate(PARTY_BUCKETS)}'),
    ("MAIN 的歧義防護被拿掉（同名對到兩個桶時安靜取後者）",
     '        if name in out and out[name] != slot:',
     '        if False:'),

    # ---- 主序列旗標 ----
    ("旗標寫死為 true（前端會把自訂選舉種類畫進跨屆折線）",
     '        ms = r["is_main_sequence"] == "true"',
     '        ms = True'),
    ("旗標寫死為 false",
     '        ms = r["is_main_sequence"] == "true"',
     '        ms = False'),
    ("旗標不一致時不再中止，改為沿用先出現的值",
     '            if out[code]["mainSequence"] != ms:\n'
     '                raise SiteDataError(',
     '            if False:\n'
     '                raise SiteDataError('),

    # ---- 四捨五入 ----
    ("投票率改用 Python round()（銀行家捨入）",
     '            turnout = (float(_round_half_up(\n'
     '                Decimal(100 * tot["votes"]) / Decimal(tot["electors"]), "0.01"))\n'
     '                if tot["electors"] else None)',
     '            turnout = (round(100 * tot["votes"] / tot["electors"], 2)\n'
     '                if tot["electors"] else None)'),
    ("四捨五入方向改為一律進位",
     '    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)',
     '    return value.quantize(Decimal(places), rounding=ROUND_CEILING)'),
    ("四捨五入方向改為一律捨去",
     '    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)',
     '    return value.quantize(Decimal(places), rounding=ROUND_FLOOR)'),

    # ---- 邊界防護 ----
    ("零當選時不再回傳 None，直接相除",
     '            per_seat = (int(_round_half_up(\n'
     '                Decimal(tot["electors"]) / Decimal(len(won)), "1"))\n'
     '                if won else None)',
     '            per_seat = int(_round_half_up(\n'
     '                Decimal(tot["electors"]) / Decimal(len(won)), "1"))'),
    ("選舉人數為零時不再回傳 None",
     '                Decimal(100 * tot["votes"]) / Decimal(tot["electors"]), "0.01"))\n'
     '                if tot["electors"] else None)',
     '                Decimal(100 * tot["votes"]) / Decimal(tot["electors"]), "0.01")))'),

    # ---- 輸入欄位契約（兩個方向）----
    ("契約：把實際會讀的 `鄉鎮市區` 從 candidates 清單移除",
     '        "省市", "縣市", "選舉區", "鄉鎮市區", "行政區名稱",\n'
     '        "號次", "姓名", "政黨代號", "政黨名稱", "性別", "年齡", "現任",',
     '        "省市", "縣市", "選舉區", "行政區名稱",\n'
     '        "號次", "姓名", "政黨代號", "政黨名稱", "性別", "年齡", "現任",'),
    ("契約：把實際會讀的 `政黨代號` 從 candidates 清單移除",
     '        "號次", "姓名", "政黨代號", "政黨名稱", "性別", "年齡", "現任",',
     '        "號次", "姓名", "政黨名稱", "性別", "年齡", "現任",'),
    ("契約：把實際會讀的 `年齡` 從 candidates 清單移除",
     '"性別", "年齡", "現任",',
     '"性別", "現任",'),
    ("契約：把不讀的 `候選人數`／`當選人數` 加回 summary 清單",
     '        "選舉人數", "投票數",\n'
     '        "admin_code_system", "is_main_sequence",',
     '        "選舉人數", "投票數", "候選人數", "當選人數",\n'
     '        "admin_code_system", "is_main_sequence",'),
    ("契約：拿掉缺欄檢查本身",
     '        if missing:',
     '        if False:'),

    # ---- 立委頁：分桶 ----
    ("立委：分桶鍵改成只比名稱（代號 9 的兩個政黨會被合併）",
     '    return LEGISLATIVE_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    return {n: b for (_c, n), b in LEGISLATIVE_IDENTITY_BUCKETS.items()}'
     '.get(row["政黨名稱"], OTHER_BUCKET)'),
    ("立委：分桶鍵改成只比代號",
     '    return LEGISLATIVE_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    return {c: b for (c, _n), b in LEGISLATIVE_IDENTITY_BUCKETS.items()}'
     '.get(row["政黨代號"], OTHER_BUCKET)'),
    ("立委：漏掉舊屆的無黨籍編碼 ('99','無')",
     '    ("99", "無"): "無黨籍",\n',
     ''),
    ("立委：分桶集合改成沿用地方公職那三桶",
     'LEGISLATIVE_PARTY_BUCKETS = (\n'
     '    "中國國民黨", "民主進步黨", "親民黨", "無黨團結聯盟", "無黨籍",\n'
     ')',
     'LEGISLATIVE_PARTY_BUCKETS = PARTY_BUCKETS'),
    ("立委：拿掉「兩個分桶集合不得相同」的檢查",
     '    if set(LEGISLATIVE_PARTY_BUCKETS) == set(PARTY_BUCKETS):',
     '    if False:'),
    ("立委：拿掉「無黨籍桶九屆皆非零」的檢查",
     '    empty = [y for y in years if party_votes[y].get("無黨籍", 0) == 0]',
     '    empty = []'),

    # ---- 立委頁：席次與投票率 ----
    ("立委：席次改用來源的當選註記",
     '        if c["當選"] == "Y":\n'
     '            party_seats[c["年度"]][legislative_bucket(c)] += 1',
     '        if c["當選註記"] == "*":\n'
     '            party_seats[c["年度"]][legislative_bucket(c)] += 1'),
    ("立委：政黨席次改用地方公職的分桶函式",
     '            party_seats[c["年度"]][legislative_bucket(c)] += 1',
     '            party_seats[c["年度"]][party_bucket(c)] += 1'),
    ("立委：合計投票率改成兩個投票率取平均",
     '        turnout[y] = float(_round_half_up(\n'
     '            Decimal(n) * 100 / Decimal(e), "0.01"))',
     '        rs = [t["years"][y]["votes"] / t["years"][y]["electors"]\n'
     '              for t in types.values() if y in t["years"]]\n'
     '        turnout[y] = float(_round_half_up(\n'
     '            Decimal(sum(rs) / len(rs)) * 100, "0.01"))'),

    # ---- 界限 ----
    ("界限：涵蓋率改成無條件捨去到整數",
     '            "coverage": float(_round_half_up(\n'
     '                Decimal(r["涵蓋率"]) * 100, "0.1")),',
     '            "coverage": float(int(Decimal(r["涵蓋率"]) * 100)),'),
    ("界限：上界誤寫成下界（區間會塌成一點）",
     '            float(_round_half_up(Decimal(r["上界_原住民得票率"]) * 100, "0.01")),',
     '            float(_round_half_up(Decimal(r["下界_原住民得票率"]) * 100, "0.01")),'),
    ("界限：只留一個門檻（替讀者挑掉取捨）",
     'BOUNDS_THRESHOLDS = ("0.95", "0.90", "0.80")',
     'BOUNDS_THRESHOLDS = ("0.95",)'),
    ("界限：所數與涵蓋人數對調",
     '            "stations": int(r["所數"]),\n'
     '            "electors": int(r["涵蓋原住民選舉人"]),',
     '            "stations": int(r["涵蓋原住民選舉人"]),\n'
     '            "electors": int(r["所數"]),'),

    # ---- 選舉期間的發布規則 ----
    ("發布：拿掉「紀錄漏列頁面」的檢查（多一頁沒人判定也不會被發現）",
     '    missing = sorted(on_disk - listed)',
     '    missing = []'),
    ("發布：拿掉「紀錄列了不存在頁面」的檢查（單向驗等於沒驗）",
     '    phantom = sorted(listed - on_disk)',
     '    phantom = []'),
    ("發布：本屆限定語的檢查改成比對「2026」（頁尾本來就有，永遠通過）",
     '        if STRINGS["current_term_notice"][lang] not in html:',
     '        if "2026" not in html:'),
    ("發布：凍結形狀的檢查被拿掉（指標可以無聲長大）",
     '    if got != FROZEN_BOUNDS_SHAPE:',
     '    if False:'),
    ("發布：未查證時的從嚴預設被拿掉",
     '    if "未查證" in text.split("## 逐頁判定")[0]:',
     '    if False:'),

    # ---- 多語（英文版）----
    ("多語：STRINGS 少一個 en 值（那一版的限定語整句消失）",
     '        "en": ("These figures describe {stations} polling stations covering "\n'
     '               "{coverage}% of indigenous electors. They are not the party "\n'
     '               "leaning of indigenous people as a whole. For the remaining "\n'
     '               "{rest}%, the same arithmetic yields no useful bound. {notice}"),',
     '        "en": "",'),
    ("多語：STRINGS 完整性檢查被拿掉",
     '    missing = [f"{k}.{lang}" for k, v in STRINGS.items()\n'
     '               for lang in LANGUAGES if not v.get(lang, "").strip()]',
     '    missing = []'),
    ("多語：代入欄位一致性檢查被拿掉（頁面會留下未替換的大括號）",
     '        if len({frozenset(f) for f in fields.values()}) != 1:',
     '        if False:'),
    ("多語：LABELS_EN 的出處檢查被拿掉",
     '    bad = [(k, v) for k, v in LABELS_EN.items()\n'
     '           if not (isinstance(v, tuple) and len(v) == 2\n'
     '                   and v[0].strip() and v[1] in LABEL_SOURCES)]',
     '    bad = []'),
    ("多語：涵蓋列舉改回非遞迴（docs/en/ 的兩頁被靜默跳過）",
     '    on_disk = {p.relative_to(docs).as_posix() for p in docs.rglob("*.html")}',
     '    on_disk = {p.relative_to(docs).as_posix() for p in docs.glob("*.html")}'),
    ("多語：靜態限定語的檢查改回 grep 整個檔案（const T 會掩護它）",
     '        html = re.sub(r"<script>.*?</script>", "",\n'
     '                      page.read_text(encoding="utf-8"), flags=re.S)',
     '        html = page.read_text(encoding="utf-8")'),
    ("多語：本屆限定語只驗 T 有、不驗 JS 用到（讀者看不到的限定語等於沒有）",
     '        if "T.current_term_notice" not in html:',
     '        if False:'),
]

# 立委頁的變異：與 index.html 同樣只能改真檔，因為斷言讀的是 ROOT/docs/。
LEG_HTML = ROOT / "docs" / "legislative.html"
LEG_HTML_MUTATION = (
    "立委頁：涵蓋率被擠到「山地鄉」之前（限定語順序反了）",
    '這樣的所<strong>全部位於原住民族地區的山地鄉</strong>',
    '這樣的所涵蓋 11.0% 的原住民選舉人，'
    '且<strong>全部位於原住民族地區的山地鄉</strong>')

# 立委頁的第二個真檔變異：拿掉本屆限定語。
LEG_NOTICE_MUTATION = (
    "立委頁：拿掉本屆限定語（選舉期間保留歷史資料卻不標示）",
    "        notice: T.current_term_notice });",
    "        notice: \"\" });")


# 英文頁的真檔變異：把限定語「翻順」——這正是翻譯時最容易發生的弱化。
EN_HTML = ROOT / "docs" / "en" / "legislative.html"
EN_WEAKEN_MUTATION = (
    "英文頁：限定語被翻弱（拿掉 not the whole 那一句）",
    # ⚠️ 前綴的 &#9888; 是必要的：這段限定語同時存在於頁面的 const T 裡，
    #    不帶前綴會出現兩次，變異腳本會拒絕執行（字串須恰好一次）。
    #    要變異的是**讀者看得到的那一份**。
    "&#9888; Figures on these pages cover different populations. They cannot be compared with each other, and they cannot be added.",
    "&#9888; Figures on these pages differ.")

# 成對驗證專用的破壞：把 T 裡的限定語字串換掉，**保留 JS 的用法**。
#
# ⚠️ 必須只觸發條件一。拿掉 JS 的用法會觸發條件二，那樣不論條件一拿什麼比
#    都會中止，這一對就證明不了任何事（實測 RAISED/RAISED）。
LEG_T_STRING_MUTATION = (
    "成對驗證用：T 裡的限定語字串被換掉（JS 的用法保留）",
    "本節為 2008–2024 年的歷史數字，不代表 2026 年本屆選舉結果。",
    "（此處原為本屆限定語）")

# 每個被變異的檔各一個 canary。
#
# ⚠️ **這是必要的，不是保險。** 本專案在政黨票那個 change 遇過「36 個變異
#    全部漏網而基準通過」——成因是副本沒被載入（`sys.path` 指回真正的
#    `scripts/`）。當時只有一個 canary，看不出另一個檔沒生效。
#    canary 是「明顯壞掉、一定要被抓到」的改動：它沒被抓到，代表
#    那個檔根本不是被執行的那一份，這一輪的所有結果都不算數。
CANARIES = [
    ("build_site_data.py", 'OTHER_BUCKET = "其他"',
     'OTHER_BUCKET = "CANARY 這個桶名不存在"'),
    ("test_build_site_data.py",
     '    print("\\n[合成] 席次相關指標一律取自 `當選`（權威值），不是 `當選註記`")',
     '    print("\\n[合成] CANARY")\n    check("canary 必須失敗", 1, 2)'),
]
HTML_CANARIES = [
    # ⚠️ canary 要打在**有斷言看著**的地方。改 <title> 沒有任何測試在看，
    #    它「沒被抓到」不代表副本沒生效，那個 canary 自己就是壞的。
    (HTML, "docs/index.html",
     '"note2009":"2009-2010 是同一輪任期分兩次投票',
     '"note2009":"CANARY 這不是原本的註記'),
    (LEG_HTML, "docs/legislative.html",
     '最嚴的一組是 11.0%',
     '最嚴的一組是 99.9%'),
    (EN_HTML, "docs/en/legislative.html",
     'indigenous electors &mdash; 11.0% at',
     'indigenous electors &mdash; 99.9% at'),
]

# 只能改真檔的那一項。見模組 docstring。
HTML_MUTATION = ("前端：MAIN 不再過濾（Python 端全綠、站台卻畫錯）",
                 'const MAIN = DATA.types.filter(t => t.mainSequence);',
                 'const MAIN = DATA.types;')

# @reports 是否承重，不能用一般變異的方式驗——單獨拿掉它時程式是好的，
# 測試本來就會通過，會被誤判成「漏網」。要驗的是：
#   壞掉的程式 + 有 @reports → pytest 失敗（由上面的變異清單涵蓋）
#   壞掉的程式 + 無 @reports → pytest 通過  ← 證明少了它失敗就看不見
REPORTS_ASSERT = '        assert not new, f"{fn.__name__} 有 {len(new)} 項失敗：{new}"'
BREAK_CODE = ('        ms = r["is_main_sequence"] == "true"', '        ms = True')


def run_pytest(test_path: Path) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_path), "-q", "--no-header"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, r.stdout + r.stderr


def fresh_copies() -> Path:
    """把原始碼與測試檔複製到 scratch/mut/，回傳測試檔路徑。"""
    if MUT.exists():
        shutil.rmtree(MUT)
    MUT.mkdir(parents=True)
    for f in COPIED:
        shutil.copy(ROOT / "scripts" / f, MUT / f)
    return MUT / "test_build_site_data.py"


def apply_to_copy(fname: str, old: str, new: str) -> bool:
    target = MUT / fname
    src = target.read_text(encoding="utf-8")
    if src.count(old) != 1:
        return False
    mutated = src.replace(old, new, 1)
    if "ROUND_CEILING" in new or "ROUND_FLOOR" in new:
        mutated = mutated.replace(
            "from decimal import Decimal, ROUND_HALF_UP",
            "from decimal import (Decimal, ROUND_CEILING, "
            "ROUND_FLOOR, ROUND_HALF_UP)")
    target.write_text(mutated, encoding="utf-8")
    return True


def git_is_clean(path: Path) -> bool:
    """該檔的內容是否與 HEAD 相同（因此 git checkout -- 不會丟掉任何東西）。

    ⚠️ **不可用 `git status --porcelain` 判斷。** 在 core.autocrlf 生效的環境下，
       只有換行不同的檔案也會被報成 ` M`，於是這個防護會把「內容其實一模一樣」
       誤判為「有未提交的工作」，白白跳過一項變異驗證——實測 docs/index.html
       就是這樣被跳過的（全檔 641 個換行都是 CRLF，而 blob 存的是 LF）。

    要問的是「內容有沒有差」，所以用 `git diff --quiet`，
    而且工作區與索引兩層都要問：只查工作區的話，
    已 staged 但未 commit 的改動會被 `git checkout --` 一併還原掉。
    """
    for extra in ([], ["--cached"]):
        r = subprocess.run(["git", "diff", "--quiet", *extra, "--", str(path)],
                           capture_output=True, cwd=ROOT)
        if r.returncode != 0:
            return False
    return True


def mutate_real_html(path: Path, desc: str, old: str, new: str
                     ) -> tuple[bool, str]:
    """在真檔上做一次變異並驗，之後以 git 還原。回傳（是否偵測到, 說明）。

    ⚠️ 還原用 `git checkout --` 而不是把備份寫回去：若這支腳本在改完之後、
       寫回之前被中斷，記憶體裡的備份就沒了，而 git 的版本還在。
       前提是執行前該檔必須乾淨，否則會連使用者未提交的改動一起還原掉——
       所以不乾淨就直接拒絕執行，不做「應該沒差」的判斷。
    """
    rel = path.relative_to(ROOT).as_posix()
    if not git_is_clean(path):
        return False, (f"★ 跳過「{desc}」：{rel} 有未提交的改動。"
                       "這項變異需要改真檔並以 git 還原，會連你的改動一起還原掉。"
                       "請先提交或暫存後再跑。")
    src = path.read_text(encoding="utf-8")
    if src.count(old) != 1:
        return False, f"★ 變異字串在 {rel} 出現 {src.count(old)} 次（需恰好 1 次）"
    test_path = fresh_copies()
    try:
        path.write_text(src.replace(old, new, 1), encoding="utf-8")
        rc, out = run_pytest(test_path)
        caught = rc != 0 and "INTERNALERROR" not in out
    finally:
        subprocess.run(["git", "checkout", "--", str(path)], cwd=ROOT,
                       capture_output=True)
    return caught, f"  {desc} → {'偵測到 ✓' if caught else '★沒被偵測到'}"


def mutate_index_html() -> tuple[bool, str]:
    """index.html 的變異。它只能改真檔——測試是用 node 執行 HTML 裡那兩行
    來驗前端過濾，而它讀的是 ROOT/docs/index.html，改副本測不到。
    """
    return mutate_real_html(HTML, *HTML_MUTATION)


def prove_named_string_beats_year() -> tuple[bool, str]:
    """證明「比對具名字串」比「比對 2026」有辨識力。

    ⚠️ 這一項**不能用一般變異的方式驗**。把檢查改成比對「2026」之後，
       基準是**通過**的（頁面本來就有 `更新：2026-08`），所以它看起來
       像「沒被偵測到的變異」，實際上是那個寫法本身沒有辨識力。

    ⚠️ **也不能用 pytest 的退出碼來量。** 測試檔另有一條獨立斷言直接比對
       限定語，限定語一被拿掉它就紅——不論 check_publication_record 拿什麼比。
       實測第一版就是這樣得到 (1, 1) 而看不出差別。
       所以這裡**直接呼叫那個函式**，只問它有沒有丟出 SiteDataError。

    要驗的是一對，在同一份被拿掉限定語的頁面上：
      具名字串的檢查 → 丟出 SiteDataError
      比對 2026 的檢查 → 不丟   ← 這正是不能那樣寫的理由

    與 @reports 承重驗證是同一種形狀。
    """
    if not git_is_clean(LEG_HTML):
        return False, "★ 跳過「具名字串 vs 年份」：docs/legislative.html 有未提交的改動"

    desc, old, new = LEG_T_STRING_MUTATION
    src = LEG_HTML.read_text(encoding="utf-8")
    if src.count(old) != 1:
        return False, (f"★ 限定語字串在 legislative.html 出現 "
                       f"{src.count(old)} 次（需恰好 1 次）")

    year_check = (
        '        if STRINGS["current_term_notice"][lang] not in html:',
        '        if "2026" not in html:')

    # ⚠️ 只呼叫**限定語的那一支**，不跑測試套件。
    #    限定語的檢查已從 check_publication_record 拆到
    #    check_current_term_notice；呼叫舊的那支永遠是 OK——
    #    探針量錯函式，輸出看起來像「檢查沒抓到」。
    # 印出 RAISED / OK，讓「工具自己壞掉」與「檢查沒抓到」分得開。
    snippet = (
        "import sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "import build_site_data as B\n"
        "try:\n"
        "    B.check_current_term_notice()\n"
        "    print('OK')\n"
        "except B.SiteDataError:\n"
        "    print('RAISED')\n"
    )

    def probe() -> str:
        r = subprocess.run([sys.executable, "-c", snippet, str(MUT)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=ROOT,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        out = (r.stdout or "").strip().splitlines()
        return out[-1] if out else f"ERROR rc={r.returncode} {r.stderr[-200:]}"

    try:
        LEG_HTML.write_text(src.replace(old, new, 1), encoding="utf-8")

        fresh_copies()
        named = probe()                      # 具名字串的檢查

        fresh_copies()
        apply_to_copy("build_site_data.py", *year_check)
        year = probe()                       # 改成比對年份
    finally:
        subprocess.run(["git", "checkout", "--", str(LEG_HTML)], cwd=ROOT,
                       capture_output=True)

    ok = named == "RAISED" and year == "OK"
    msg = (f"  限定語被拿掉 + 具名字串檢查 → {named}"
           f"（應 RAISED）{'✓' if named == 'RAISED' else ' ★'}\n"
           f"  限定語被拿掉 + 比對『2026』 → {year}"
           f"（應 OK，證明年份判準沒有辨識力）{'✓' if year == 'OK' else ' ★'}")
    return ok, msg


def main() -> int:
    rc = 0

    test_path = fresh_copies()
    base_rc, base_out = run_pytest(test_path)
    print(f"未變異的副本 → {'通過 ✓' if base_rc == 0 else '★失敗'}")
    if base_rc != 0:
        print(base_out[-1500:])
        shutil.rmtree(MUT, ignore_errors=True)
        return 1

    for desc, old, new in MUTATIONS:
        test_path = fresh_copies()
        if not apply_to_copy("build_site_data.py", old, new):
            print(f"  ★ 變異字串未恰好出現一次，變異測試本身壞了：{desc}")
            rc = 1
            continue
        mrc, mout = run_pytest(test_path)
        caught = mrc != 0 and "INTERNALERROR" not in mout
        print(f"  {desc} → {'偵測到 ✓' if caught else '★沒被偵測到'}")
        if not caught:
            rc = 1
            print("      ", mout.strip()[-300:].replace("\n", " | "))

    # ⚠️ 「因前置條件未驗證」與「驗證後漏網」是兩件不同的事，分開計數。
    #    但兩者都不算通過——把未驗證的項目算成通過，就是「靜默縮減涵蓋範圍」。
    skipped_msgs: list[str] = []
    for caught, msg in (mutate_index_html(),
                        mutate_real_html(LEG_HTML, *LEG_HTML_MUTATION),
                        mutate_real_html(LEG_HTML, *LEG_NOTICE_MUTATION),
                        mutate_real_html(EN_HTML, *EN_WEAKEN_MUTATION)):
        print(msg)
        if not caught:
            if msg.lstrip().startswith("★ 跳過"):
                skipped_msgs.append(msg.strip())
            else:
                rc = 1

    # ---- canary：每個被變異的檔各一個 ----
    print("\n[canary] 每個被變異的檔都必須真的是被執行的那一份")
    for fname, old, new in CANARIES:
        test_path = fresh_copies()
        if not apply_to_copy(fname, old, new):
            print(f"  ★ canary 字串未恰好出現一次：{fname}")
            rc = 1
            continue
        crc, cout = run_pytest(test_path)
        caught = crc != 0 and "INTERNALERROR" not in cout
        print(f"  {fname} 的 canary → {'被抓到 ✓' if caught else '★沒被抓到'}")
        if not caught:
            rc = 1
            print("       這一輪的所有結果都不算數：副本沒有被載入。")
    for path, label, old, new in HTML_CANARIES:
        caught, msg = mutate_real_html(path, f"{label} 的 canary", old, new)
        print(msg)
        if not caught:
            if msg.lstrip().startswith("★ 跳過"):
                skipped_msgs.append(msg.strip())
            else:
                rc = 1
                print("       這一輪的所有結果都不算數：該檔沒有被讀到。")

    # ---- 決策 5：具名字串 vs 年份（成對驗證，不是一般變異）----
    print("\n[成對] 本屆限定語的檢查：具名字串 vs 比對「2026」")
    ok_pair, msg_pair = prove_named_string_beats_year()
    print(msg_pair)
    if not ok_pair:
        if msg_pair.lstrip().startswith("★ 跳過"):
            skipped_msgs.append(msg_pair.strip())
        else:
            rc = 1

    # ---- @reports 承重驗證 ----
    print("\n[骨架] 驗證 @reports 是承重的，不是裝飾")
    test_path = fresh_copies()
    apply_to_copy("build_site_data.py", *BREAK_CODE)
    with_rc, _ = run_pytest(test_path)
    tf = MUT / "test_build_site_data.py"
    tf.write_text(tf.read_text(encoding="utf-8")
                  .replace(REPORTS_ASSERT, "        pass", 1), encoding="utf-8")
    without_rc, _ = run_pytest(test_path)
    print(f"  壞掉的程式 + 有 @reports → pytest rc={with_rc}"
          f"（應非零）{'✓' if with_rc != 0 else ' ★'}")
    print(f"  壞掉的程式 + 無 @reports → pytest rc={without_rc}"
          f"（應為零，證明少了它失敗就看不見）{'✓' if without_rc == 0 else ' ★'}")
    if not (with_rc != 0 and without_rc == 0):
        rc = 1

    shutil.rmtree(MUT, ignore_errors=True)

    # 真檔必須完好如初：副本法動不到它，但 index.html 那一項改過真檔
    final_rc, final_out = run_pytest(ROOT / "scripts" / "test_build_site_data.py")
    print(f"\n真正的 scripts/ 與 docs/ → {'通過 ✓' if final_rc == 0 else '★失敗（還原不完全）'}")
    if final_rc != 0:
        print(final_out[-1500:])
        rc = 1

    print()
    if rc:
        print("★ 有變異漏網——那些檢查沒有辨識力，必須補斷言")
    elif skipped_msgs:
        print(f"★ 全部已驗證的變異都被偵測到，但有 {len(skipped_msgs)} 項"
              f"因前置條件【未驗證】：")
        for m in skipped_msgs:
            print("   ", m)
        print("    未驗證不等於通過。處理前置條件後請重跑。")
    else:
        print("全部通過")
    # 未驗證的項目一樣不算通過——把它算成通過就是靜默縮減涵蓋範圍。
    return rc or (1 if skipped_msgs else 0)


if __name__ == "__main__":
    raise SystemExit(main())
