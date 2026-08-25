#!/usr/bin/env python3
"""build_site_data.py 的合成資料測試。

**這個檔案存在的理由是：有些行為用真實資料改壞了也不會被發現。**

`build_site_data.py --check` 已經能用九屆真實資料驗「重建的常數 == HTML 現況」，
而且對七種變異都會非零退出。但 `--check` 的辨識力全部來自「現有資料剛好會觸發
那條分支」。凡是現有資料觸發不到的分支——防禦性的 raise、零分母、剛好落在
四捨五入半數上的值——把它刪掉或改壞，`--check` 一樣通過。

這個檔案只放那類東西，不重複 `--check` 已經在做的事。唯一刻意重疊的是
「席次取自權威值」：`--check` 今天抓得到（實測改成讀 `當選` 會 rc=1），
但那個辨識力來自「來源目前是壞的」——2005 兩檔的 `當選` 少算 19 席。
來源哪天被上游修好，`--check` 就失去辨識力，合成測試不會。

用法：
    python scripts/test_build_site_data.py
    pytest scripts/test_build_site_data.py

⚠️ 每個 test_* 都用 @reports 包起來。沒有這一層，check() 的失敗只會記進全域
   清單而函式正常返回，**pytest 會判定通過**——這個專案已經因此產生過
   76 項永遠通過的測試。
"""

from __future__ import annotations

import ast
import csv
import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_site_data  # noqa: E402
from build_site_data import (  # noqa: E402
    BOUNDS_FILE,
    BOUNDS_MARKER,
    CANDIDATES_FILE,
    LEG_MARKER,
    LEG_SUMMARY_FILE,
    REQUIRED_COLUMNS,
    SUMMARY_FILE,
    SiteDataError,
    build_bounds_data,
    build_index_data,
    build_legislative_data,
    build_roster_data,
    election_types,
    load_legislative_tables,
    load_long_tables,
    read_embedded_constant,
    segment_headings,
    site_mark,
)

ROOT = Path(__file__).resolve().parent.parent

# ⚠️ 由**匯入的模組**推導，不要寫死 ROOT/"scripts"/"build_site_data.py"。
#    變異測試把原始碼與本檔複製到別的資料夾再改壞副本；寫死路徑的話
#    test_required_columns_matches_actual_reads 會回頭去讀真正那份沒被改壞的檔，
#    於是變異永遠不會被偵測到——那正是「永遠通過的測試」的長相。
SRC = Path(build_site_data.__file__).resolve()

DATA_DIR = ROOT / "data" / "processed"

failures: list[str] = []
skipped: list[str] = []


def reports(fn):
    """讓 check() 的失敗真的使 pytest 失敗。見模組 docstring 的警告。"""
    def wrapper():
        start = len(failures)
        fn()
        new = failures[start:]
        assert not new, f"{fn.__name__} 有 {len(new)} 項失敗：{new}"
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


def check(name: str, got, want) -> None:
    if got == want:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}\n          得到 {got!r}\n          預期 {want!r}")
        failures.append(name)


def check_raises(name: str, fn) -> None:
    try:
        fn()
    except SiteDataError:
        print(f"  PASS  {name}")
        return
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL  {name}（丟出 {type(exc).__name__}: {exc} 而非 SiteDataError）")
        failures.append(name)
        return
    print(f"  FAIL  {name}（沒有丟出例外）")
    failures.append(name)


# ------------------------------------------------------------ 合成資料建構

def summary_row(**kw) -> dict:
    """一列 summary。未指定的欄位一律給空字串，確保欄位集合完整。"""
    row = {c: "" for c in REQUIRED_COLUMNS[SUMMARY_FILE]}
    row.update(kw)
    return row


def cand_row(**kw) -> dict:
    """一列 candidates。未指定的欄位一律給空字串。"""
    row = {c: "" for c in REQUIRED_COLUMNS[CANDIDATES_FILE]}
    row.update(kw)
    return row


# 合成情境：一屆（"2000"）、一種選舉（"TX"）、兩個選舉區、四位候選人。
#
# 刻意讓 `當選註記`（來源怎麼寫）與 `當選`（權威值）**不一致**，方向與 2005
# 縣市議員原住民兩檔相同——來源少標了當選人。四個人的設計使每一項席次相關
# 指標在兩種取法下都得到不同的數字；只要有一項改用 `當選`，就會被抓到。
#
#   候選人  選舉區  當選(來源)  權威值  性別  現任  政黨       當選註記
#   甲      01      true        true    男    N     中國國民黨  *
#   乙      01      false       true    女    Y     民主進步黨  （空）← 來源漏標
#   丙      02      false       false   女    N     中國國民黨  （空）
#   丁      02      false       false   男    Y     其他黨      （空）
#
# 選舉區 01：2 位候選人、權威值 2 席 → 同額競選；以 `當選` 算只有 1 席 → 不是。
_TERM, _TYPE = "2000", "TX"


def _mixed_summary() -> list[dict]:
    return [
        summary_row(年度=_TERM, 選舉種類=_TYPE, 選舉種類名稱="測試選舉",
                    層級="檔別合計", 檔別="city",
                    選舉人數="1000", 投票數="505",
                    is_main_sequence="true", admin_code_system="test"),
    ]


def _mixed_cands() -> list[dict]:
    base = dict(年度=_TERM, 選舉種類=_TYPE, 省市="10", 縣市="001",
                admin_code_system="test", 檔別="city", 鄉鎮市區="000")
    return [
        cand_row(**base, 選舉區="01", 號次="1", 姓名="甲", 政黨代號="1", 政黨名稱="中國國民黨",
                 性別="男", 年齡="50", 現任="N",
                 當選註記="*", 當選="Y",
                 行政區名稱="測試縣第01選舉區"),
        cand_row(**base, 選舉區="01", 號次="2", 姓名="乙", 政黨代號="16", 政黨名稱="民主進步黨",
                 性別="女", 年齡="40", 現任="Y",
                 當選註記="", 當選="Y",
                 行政區名稱="測試縣第01選舉區"),
        cand_row(**base, 選舉區="02", 號次="1", 姓名="丙", 政黨代號="1", 政黨名稱="中國國民黨",
                 性別="女", 年齡="45", 現任="N",
                 當選註記="", 當選="N",
                 行政區名稱="測試縣第02選舉區"),
        cand_row(**base, 選舉區="02", 號次="2", 姓名="丁", 政黨代號="777", 政黨名稱="某小黨",
                 性別="男", 年齡="60", 現任="Y",
                 當選註記="", 當選="N",
                 行政區名稱="測試縣第02選舉區"),
    ]


# -------------------------------------------------- 一、席次取自權威值而非 當選

@reports
def test_seats_from_authoritative() -> None:
    print("\n[合成] 席次相關指標一律取自 `當選`（權威值），不是 `當選註記`")
    print("       來源漏標一位當選人（與 2005 兩檔同一方向），"
          "每一項指標在兩種取法下都不同")
    d = build_index_data(_mixed_summary(), _mixed_cands())
    y = d["types"][0]["years"][_TERM]

    # 左為權威值下的正確答案，右為改用 `當選` 會得到的錯誤答案（註解中）
    check("seats（以 `當選` 算會是 1）", y["seats"], 2)
    check("femaleSeats（以 `當選` 算會是 0）", y["femaleSeats"], 1)
    check("incWon（以 `當選` 算會是 0）", y["incWon"], 1)
    check("民進黨當選數（以 `當選` 算會是 0）", y["party"]["民主進步黨"][0], 1)
    check("國民黨當選數", y["party"]["中國國民黨"][0], 1)
    check("uncontestedDist（以 `當選` 算會是 0）", y["uncontestedDist"], 1)
    check("uncontestedSeats（以 `當選` 算會是 0）", y["uncontestedSeats"], 2)
    check("perSeat = 1000/2（以 `當選` 算會是 1000）", y["perSeat"], 500)

    # 候選人側的數字不受權威值影響，一併釘住以免把「當選」與「候選」搞混
    check("cands 不受影響", y["cands"], 4)
    check("femaleCands 不受影響", y["femaleCands"], 2)
    check("incCands 不受影響", y["incCands"], 2)
    check("districts 不受影響", y["districts"], 2)

    print("\n       名錄側的當選標記同樣取自權威值")
    r = build_roster_data(_mixed_summary(), _mixed_cands())
    marks = {c[1]: c[6] for grp in r["rows"][_TERM][_TYPE] for c in grp[2]}
    check("乙（來源漏標）在名錄顯示 *", marks["乙"], "*")
    check("甲（來源有標）在名錄顯示 *", marks["甲"], "*")
    check("丙（兩者皆否）在名錄無標記", marks["丙"], "")


@reports
def test_no_winners_does_not_divide_by_zero() -> None:
    print("\n[合成] 有候選人但權威值零當選：perSeat 為 None 而非 0 或例外")
    print("       真實資料沒有這種組合，--check 永遠走不到這條分支")
    cands = [dict(c, 當選="N", 當選註記="")
             for c in _mixed_cands()]
    y = build_index_data(_mixed_summary(), cands)["types"][0]["years"][_TERM]
    check("seats", y["seats"], 0)
    check("perSeat 為 None", y["perSeat"], None)
    check("cands 仍為 4（不是整組消失）", y["cands"], 4)


@reports
def test_zero_electors_turnout_is_none() -> None:
    print("\n[合成] 選舉人數為 0：turnout 為 None 而非 0 或 ZeroDivisionError")
    summ = [summary_row(年度=_TERM, 選舉種類=_TYPE, 選舉種類名稱="測試選舉",
                        層級="檔別合計", 檔別="city",
                        選舉人數="0", 投票數="0",
                        is_main_sequence="true", admin_code_system="test")]
    y = build_index_data(summ, _mixed_cands())["types"][0]["years"][_TERM]
    check("turnout 為 None", y["turnout"], None)


# ---------------------------------------------------- 二、當選標記的六個分支

@reports
def test_site_mark_branches() -> None:
    print("\n[合成] site_mark：`!` 與 `-` 原樣保留，其餘由權威值決定")
    print("       健康屆別下這條規則與 `當選註記` 完全一致，"
          "所以真實資料改壞也測不出來")

    def mark(note: str, auth: str) -> str:
        return site_mark({"當選註記": note, "當選": auth})

    check("`!` 婦女保障當選 → 保留 !", mark("!", "Y"), "!")
    check("`-` 因婦女保障被排擠 → 保留 -", mark("-", "N"), "-")
    check("`*` 且權威值當選 → *", mark("*", "Y"), "*")
    check("空白且權威值未當選 → 空白", mark("", "N"), "")
    check("空白但權威值當選 → *（2005 兩檔的修復方向）",
          mark("", "Y"), "*")
    check("`*` 但權威值未當選 → 空白（1994 高雄市的修復方向）",
          mark("*", "N"), "")
    # ⚠️ 編碼是 `Y`／`N`。舊值 `true`／`false` 必須被當成「未當選」，
    #    不可因為 "true" 是非空字串就誤判為當選——那會讓一個過期的
    #    呼叫端安靜地全部算成當選。
    check("舊編碼 'true' 不再被當成當選", mark("", "true"), "")


# ------------------------------------------------------ 三、主序列旗標的傳遞

@reports
def test_main_sequence_flag_passthrough() -> None:
    """⚠️ 名稱刻意不叫「主序列過濾」。

    `build_site_data.py` **不做過濾**——它只把 `is_main_sequence` 轉成
    `mainSequence` 放進常數，實際的過濾是 docs/index.html 的
    `DATA.types.filter(t => t.mainSequence)`。若把這個測試叫做「過濾」，
    有人刪掉前端那一行時 Python 測試全綠，但站台已經把自訂選舉種類
    畫進跨屆折線了。前端那一側由 test_index_html_filters_custom_types 守。
    """
    print("\n[合成] mainSequence 旗標由長表傳遞至常數，不在站台端重新判定")
    summ = _mixed_summary() + [
        summary_row(年度=_TERM, 選舉種類="T-CUSTOM", 選舉種類名稱="自訂選舉",
                    層級="檔別合計", 檔別="city",
                    選舉人數="500", 投票數="250",
                    is_main_sequence="false", admin_code_system="test"),
    ]
    cands = _mixed_cands() + [
        cand_row(年度=_TERM, 選舉種類="T-CUSTOM", 省市="10", 縣市="001",
                 選舉區="01", 鄉鎮市區="000", 號次="1", 姓名="戊",
                 政黨代號="1", 政黨名稱="中國國民黨", 性別="男", 年齡="55", 現任="N",
                 當選註記="*", 當選="Y",
                 行政區名稱="測試縣第01選舉區",
                 admin_code_system="test", 檔別="city"),
    ]
    d = build_index_data(summ, cands)
    flags = {t["code"]: t["mainSequence"] for t in d["types"]}
    check("TX 的 mainSequence 為 True", flags.get("TX"), True)
    check("T-CUSTOM 的 mainSequence 為 False", flags.get("T-CUSTOM"), False)

    # 兩個方向都要測。只測 False 那一項的話，把整欄寫死成 False 會通過；
    # 只測 True 的話，寫死成 True 會通過。
    check("兩種值都出現（寫死成單一值即失敗）",
          sorted(set(flags.values())), [False, True])

    print("\n       非主序列的選舉種類**必須留在常數裡**（站台以獨立區塊呈現），"
          "過濾不在 Python 端")
    check("T-CUSTOM 仍在 types 中", "T-CUSTOM" in flags, True)

    print("\n       同一選舉種類的旗標在長表中互相矛盾 → 中止，不猜")
    bad = [
        summary_row(年度=_TERM, 選舉種類="TZ", 選舉種類名稱="矛盾",
                    is_main_sequence="true"),
        summary_row(年度=_TERM, 選舉種類="TZ", 選舉種類名稱="矛盾",
                    is_main_sequence="false"),
    ]
    check_raises("is_main_sequence 不一致時中止", lambda: election_types(bad))


@reports
def test_index_html_filters_custom_types() -> None:
    """真正的主序列過濾在前端 JS，這裡用 node 直接執行那兩行。

    沒有這一項，「主序列過濾」就處在兩邊都沒測到的真空區：
    Python 測試只到旗標為止，`--check` 只比對常數本身。
    """
    print("\n[前端] docs/index.html 的 DATA.types.filter 真的排除了非主序列")
    node = _node_or_none()
    if node is None:
        print("  SKIP  找不到 node，跳過前端過濾測試")
        skipped.append("test_index_html_filters_custom_types")
        return

    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    wanted = ("const DATA = ", "const MAIN = ", "const CUSTOM = ")
    lines = []
    for prefix in wanted:
        hit = [ln for ln in html.splitlines() if ln.startswith(prefix)]
        if len(hit) != 1:
            check(f"index.html 中 {prefix!r} 恰好一行", len(hit), 1)
            return
        lines.append(hit[0])

    script = "\n".join(lines) + """
const out = {
  main: MAIN.map(t => t.code),
  custom: CUSTOM.map(t => t.code),
  flagTrue: DATA.types.filter(t => t.mainSequence).map(t => t.code),
  flagFalse: DATA.types.filter(t => !t.mainSequence).map(t => t.code),
};
console.log(JSON.stringify(out));
"""
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "check_filter.mjs"
        f.write_text(script, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    if r.returncode != 0:
        check("node 執行成功", r.stderr.strip()[-200:], "")
        return
    got = json.loads(r.stdout)

    # 預期值由 DATA 自身推導，不寫死代碼清單——寫死的話，日後新增一種
    # 選舉種類就得改測試，而改測試的人很可能順手把它改成通過。
    check("MAIN 恰為 mainSequence 為真者", got["main"], got["flagTrue"])
    check("CUSTOM 恰為 mainSequence 為假者", got["custom"], got["flagFalse"])

    # 若 CUSTOM 是空的，上面兩項在「過濾被刪掉」時也會通過。
    check("CUSTOM 非空（否則上面兩項失去辨識力）",
          len(got["custom"]) > 0, True)
    check("MAIN 不含任何自訂選舉種類",
          [c for c in got["main"] if c.startswith("T-")], [])


# ---------------------------------------------------------- 四、四捨五入

@reports
def test_turnout_round_half_up() -> None:
    """⚠️ 這一項真實資料抓不到，實測九屆 33 組投票率，浮點與精確十進位結果相同。"""
    print("\n[合成] 投票率用四捨五入（ROUND_HALF_UP），不是 Python round() 的銀行家捨入")
    # 100 * 421 / 800 = 52.625，在二進位中可精確表示（52 + 5/8），
    # 因此 round() 的差異純粹來自銀行家捨入，不是浮點誤差。
    check("前提：Python round(52.625, 2) 確實捨去成 52.62",
          round(52.625, 2), 52.62)
    summ = [summary_row(年度=_TERM, 選舉種類=_TYPE, 選舉種類名稱="測試選舉",
                        層級="檔別合計", 檔別="city",
                        選舉人數="800", 投票數="421",
                        is_main_sequence="true", admin_code_system="test")]
    y = build_index_data(summ, _mixed_cands())["types"][0]["years"][_TERM]
    check("52.625 進位成 52.63", y["turnout"], 52.63)

    # ⚠️ 只測 52.625 不夠：ROUND_CEILING 在這個值上與 HALF_UP 同解（都得 52.63），
    #    把捨入模式改成一律進位不會被抓到——實測漏網過。
    #    要卡住「一律進位」與「一律捨去」，需要第三位小數分別低於與高於半數的值。
    def turnout(electors: str, votes: str) -> float:
        summ = [summary_row(年度=_TERM, 選舉種類=_TYPE, 選舉種類名稱="測試選舉",
                            層級="檔別合計", 檔別="city",
                            選舉人數=electors, 投票數=votes,
                            is_main_sequence="true", admin_code_system="test")]
        return build_index_data(summ, _mixed_cands())["types"][0]["years"][_TERM]["turnout"]

    check("33.333… 捨去成 33.33（一律進位即失敗）", turnout("3", "1"), 33.33)
    check("66.666… 進位成 66.67（一律捨去即失敗）", turnout("3", "2"), 66.67)


# ------------------------------------------------ 五、輸入欄位契約（兩個方向）

def _column_keys_in_source() -> set[str]:
    """原始碼中以字面字串索引取用的所有鍵。

    ⚠️ 抓不到以變數索引的取用（如 `c[f] for f in (...)`）。本腳本目前只有
       一處那樣寫，且那四欄在別處都有字面取用，故不影響。日後若新增這類寫法
       必須手動確認——這個限制寫在這裡，不要假裝它不存在。
    """
    keys: set[str] = set()
    for node in ast.walk(ast.parse(SRC.read_text(encoding="utf-8"))):
        if (isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)):
            keys.add(node.slice.value)
    return keys


@reports
def test_required_columns_matches_actual_reads() -> None:
    """REQUIRED_COLUMNS 必須恰好等於程式讀到的欄位集合，兩個方向都要對。

    改壞任一方向都會失敗：
      - 把 `鄉鎮市區` 從清單移除 → 「讀了卻沒宣告」失敗
      - 把 `候選人數` 加回清單   → 「宣告了卻沒讀」失敗
    """
    print("\n[契約] REQUIRED_COLUMNS 與原始碼實際讀取的欄位互相對照")
    if not (DATA_DIR / CANDIDATES_FILE).exists():
        print("  SKIP  找不到長表，無法界定「哪些鍵是欄位名」")
        skipped.append("test_required_columns_matches_actual_reads")
        return

    with gzip.open(DATA_DIR / SUMMARY_FILE, "rt", encoding="utf-8-sig") as fh:
        headers = set(next(csv.reader(fh)))
    with open(DATA_DIR / CANDIDATES_FILE, encoding="utf-8-sig") as fh:
        headers |= set(next(csv.reader(fh)))

    declared = set(REQUIRED_COLUMNS[SUMMARY_FILE]) | set(REQUIRED_COLUMNS[CANDIDATES_FILE])
    # 只看真的是長表欄位的鍵，排除 electors／seats 這類內部字典鍵
    read = _column_keys_in_source() & headers

    check("讀了卻沒宣告的欄位", sorted(read - declared), [])
    check("宣告了卻沒讀的欄位", sorted(declared - read), [])
    check("宣告的欄位都真的存在於長表", sorted(declared - headers), [])


def _write_synthetic_tables(d: Path, drop_from_cands: str = "",
                            drop_from_summary: str = "") -> None:
    """把合成資料寫成真正的檔案，供 load_long_tables 讀取。"""
    scols = [c for c in REQUIRED_COLUMNS[SUMMARY_FILE] if c != drop_from_summary]
    ccols = [c for c in REQUIRED_COLUMNS[CANDIDATES_FILE] if c != drop_from_cands]
    with gzip.open(d / SUMMARY_FILE, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=scols, extrasaction="ignore")
        w.writeheader()
        for r in _mixed_summary():
            w.writerow(r)
    with open(d / CANDIDATES_FILE, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ccols, extrasaction="ignore")
        w.writeheader()
        for r in _mixed_cands():
            w.writerow(r)


@reports
def test_missing_column_aborts_at_header() -> None:
    """缺欄必須在讀完標頭時就中止，而不是算到一半才 KeyError。

    `鄉鎮市區` 是 district_key 決定粒度的那一欄，`admin_code_system` 是名錄
    回填鄉鎮市區名稱的鍵。這兩欄先前都沒有宣告——缺了會在計算途中
    KeyError，錯誤訊息離真正的原因很遠。

    `政黨代號` 是 party_bucket 的鍵之一。少了它，分桶會退回只認名稱，
    而那正是「舊屆無黨籍全是 0」的成因——所以缺這一欄必須中止，不可容忍。
    """
    print("\n[契約] 缺少實際會讀的欄位 → SiteDataError（不是 KeyError）")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_synthetic_tables(d)
        # 對照組：完整的合成表必須能讀進來
        summ, cands = load_long_tables(d)
        check("完整的合成表可讀取（summary 列數）", len(summ), 1)
        check("完整的合成表可讀取（candidates 列數）", len(cands), 4)

    for col in ("鄉鎮市區", "admin_code_system", "當選",
                "政黨代號"):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            _write_synthetic_tables(d, drop_from_cands=col)
            check_raises(f"candidates 缺 {col} → 中止",
                         lambda d=d: load_long_tables(d))

    for col in ("鄉鎮市區", "admin_code_system", "is_main_sequence"):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            _write_synthetic_tables(d, drop_from_summary=col)
            check_raises(f"summary 缺 {col} → 中止",
                         lambda d=d: load_long_tables(d))


# ------------------------------------------------------------------ 執行

def _node_or_none() -> str | None:
    exe = "node.exe" if os.name == "nt" else "node"
    for p in os.environ.get("PATH", "").split(os.pathsep):
        cand = Path(p) / exe
        if cand.exists():
            return str(cand)
    return None


# ------------------------------------------------ 六、分桶鍵的語意（合成）

@reports
def test_party_bucket_key_semantics() -> None:
    """鍵是 (代號, 名稱) 配對，兩個欄位都必須吻合。

    ⚠️ **這幾條非用合成資料不可。** 實測真實資料：對照表內的五個代號
    （1／2／16／99／999）**各自只對到一個名稱**，而全資料五組「同代號多名稱」
    （166／199／254／290／303）**全部落在表外**、兩個名稱本來都歸「其他」。

    後果是：把鍵改成**只用代號**，或加上「代號相同就沿用該桶」的回退，
    在現有真實資料上算出的結果**與正確實作完全相同**——任何只斷言真實資料
    最終輸出的測試都不可能亮紅燈。是這份資料的分布剛好掩蓋了那個漏洞。

    這裡守的是**設計意圖**（代號會被回收再發給另一個政黨），不是現有資料。
    """
    print("\n[合成] 分桶鍵是 (代號, 名稱) 配對，兩者都要吻合")
    def b(code: str, name: str) -> str:
        return build_site_data.party_bucket({"政黨代號": code, "政黨名稱": name})

    print("       正向對照：對照表列出的五筆必須各歸其位")
    check("1／中國國民黨", b("1", "中國國民黨"), "中國國民黨")
    check("2／民主進步黨（舊屆代號）", b("2", "民主進步黨"), "民主進步黨")
    check("16／民主進步黨（新屆代號）", b("16", "民主進步黨"), "民主進步黨")
    check("99／無（舊屆無黨籍）", b("99", "無"), "無黨籍及未經政黨推薦")
    check("999／無黨籍及未經政黨推薦", b("999", "無黨籍及未經政黨推薦"),
          "無黨籍及未經政黨推薦")

    print("\n       代號相符但名稱不符 → 其他（擋下「只用代號」與「代號回退」）")
    check("2／某未知黨（代號被回收的情境）", b("2", "某未知黨"), "其他")
    check("999／某未知黨", b("999", "某未知黨"), "其他")

    print("\n       名稱相符但代號不符 → 其他（擋下「只用名稱」）")
    check("777／無", b("777", "無"), "其他")
    check("777／中國國民黨", b("777", "中國國民黨"), "其他")

    print("\n       兩欄各自都在表內、但不成配對 → 其他")
    print("       （擋下「代號在表內 and 名稱在表內」這種鬆散寫法）")
    check("1／民主進步黨", b("1", "民主進步黨"), "其他")
    check("16／中國國民黨", b("16", "中國國民黨"), "其他")
    check("99／無黨籍及未經政黨推薦", b("99", "無黨籍及未經政黨推薦"), "其他")

    print("\n       同代號多名稱：兩者都歸其他，且不因共用代號互相牽連")
    print("       ⚠️ 這一組【不是】辨識用的案例——兩個名稱都不在表內，")
    print("          沒有桶可以外洩，合併與不合併的結果相同。列出是為了記錄意圖。")
    check("303／基進黨", b("303", "基進黨"), "其他")
    check("303／台灣基進", b("303", "台灣基進"), "其他")


@reports
def test_party_code_and_name_hygiene() -> None:
    """代號與名稱在真實資料裡沒有空白、補零或空值的變體。

    ⚠️ **量到例外集合是空的，所以【不加】清洗機制。** 在 party_bucket 裡塞
    `str(...).strip()` 會蓋出一段永遠不會執行的程式碼，而且會讓後來的人以為
    這裡本來就有髒資料因此放寬警覺。改為斷言它繼續是空的——真的出現變體時
    這條會失敗，屆時再決定怎麼處置。
    """
    print("\n[真實] 政黨代號與名稱的乾淨度（空集合以斷言守，不以清洗守）")
    if not (DATA_DIR / CANDIDATES_FILE).exists():
        print("  SKIP  找不到長表")
        skipped.append("test_party_code_and_name_hygiene")
        return
    _, cands = load_long_tables()
    codes = {c["政黨代號"] for c in cands}
    names = {c["政黨名稱"] for c in cands}
    check("代號全為數字字串", sorted(c for c in codes if not c.isdigit()), [])
    check("代號無前後空白", sorted(c for c in codes if c != c.strip()), [])
    check("名稱無前後空白", sorted(n for n in names if n != n.strip()), [])
    check("無空字串代號", "" in codes, False)
    # 只差前導零的代號會讓 ("1", X) 與 ("01", X) 變成兩個鍵
    by_int: dict[str, list[str]] = {}
    for c in codes:
        by_int.setdefault(str(int(c)), []).append(c)
    check("無只差前導零的代號組",
          {k: sorted(v) for k, v in by_int.items() if len(v) > 1}, {})


# ------------------------ 六b、年齡取自長表已是乾淨值的 `年齡` 欄（合成）

@reports
def test_age_read_from_derived_column() -> None:
    """站台**讀取** `年齡`（長表已將它清乾淨），不自行推導未記載的判準。

    ⚠️ 判準（哪些屆別的 99 算未記載）與守住它的兩條斷言都在長表建置端，
    見 scripts/build_local_election.py 的 valid_age 與 check_age_sentinel，
    測試在 scripts/test_build_local_election.py。
    來源原值在長表的 `年齡_原始`，站台**不讀那一欄**——讀了就等於有第二份判準。

    同一個規則若在兩處各有一份實作，其中一份必然漂移——這個專案已經因此
    出過兩個 bug（名錄的 MAIN 手寫一份、政黨分桶只認一種名稱）。所以這裡
    要守的不是判準本身，而是「站台沒有第二份判準」。
    """
    print("\n[合成] 名錄的年齡取自長表的 `年齡`（已是乾淨值），站台不重算判準")

    def roster_age(clean: str):
        cands = [dict(c, **{"年齡": clean}) for c in _mixed_cands()]
        d = build_roster_data(_mixed_summary(), cands)
        return d["rows"][_TERM][_TYPE][0][2][0][4]

    check("有值時原樣帶入", roster_age("45"), 45)
    check("留空時為 None（常數裡是 null）", roster_age(""), None)

    print("\n       判別測試：兩欄刻意衝突，只有一種實作能通過")
    print("       屆別=1998（在建置端的具名清單內）、年齡_原始=99、年齡=45")
    print("       讀 年齡 → 45；改讀 年齡_原始 再自己重算 → None。")
    print("       兩者不可能同時成立。")
    conflict = [dict(c, **{"年度": "1998", "年齡_原始": "99", "年齡": "45"})
                for c in _mixed_cands()]
    summ = [dict(r, **{"年度": "1998"}) for r in _mixed_summary()]
    got = build_roster_data(summ, conflict)["rows"]["1998"][_TYPE][0][2][0][4]
    check("站台取 年齡（45），不是自己從 年齡_原始 算出的 None", got, 45)


# ---------------------------------------------- 七、名錄的 MAIN 由對照表投影

@reports
def test_roster_main_projection() -> None:
    """名錄的 `MAIN` 是「名稱 → 色槽」，由 (代號, 名稱) 對照表投影而來。

    ⚠️ 名錄前端只有政黨名稱可用（候選人 tuple 存的是 `D.parties` 的索引），
    所以這一份只能以名稱為鍵。因此投影**可能是歧義的**：若對照表讓同一個名稱
    在不同代號下歸到不同的桶，名稱就不足以決定色槽。那條防護在真實資料上
    **永遠不會觸發**，只能用合成資料測。
    """
    print("\n[合成] 名錄的 MAIN 投影：同名同槽，歧義即中止")
    main = build_site_data.build_roster_main()
    check("「無」與「無黨籍及未經政黨推薦」同一個色槽",
          main.get("無") == main.get("無黨籍及未經政黨推薦") is not None, True)
    check("兩者的色槽是 1（對應 --s2）", main.get("無"), 1)
    check("中國國民黨在色槽 0", main.get("中國國民黨"), 0)
    check("民主進步黨在色槽 2（兩個代號投影到同一槽）",
          main.get("民主進步黨"), 2)
    check("投影後恰四個名稱", len(main), 4)

    print("\n       同名對到不同桶 → 中止，不猜")
    orig = dict(build_site_data.PARTY_IDENTITY_BUCKETS)
    try:
        build_site_data.PARTY_IDENTITY_BUCKETS[("888", "無")] = "中國國民黨"
        check_raises("同一名稱兩個桶時中止",
                     build_site_data.build_roster_main)
    finally:
        build_site_data.PARTY_IDENTITY_BUCKETS.clear()
        build_site_data.PARTY_IDENTITY_BUCKETS.update(orig)
    check("還原後投影仍正常", len(build_site_data.build_roster_main()), 4)


# ------------------------------------ 八、無黨籍逐屆非零（具名的領域斷言）

# 實測的逐屆無黨籍候選人數。舊五屆是本次修正的直接產物——修正前全部是 0，
# 因為分桶只認新屆的名稱「無黨籍及未經政黨推薦」，舊屆的代號 99／名稱「無」
# 整批落進「其他」。
EXPECTED_INDEPENDENT_CANDS = {
    "1994": 14, "1998": 44, "2002": 50, "2005": 42, "2006": 1,
}

INDEPENDENT_BUCKET = "無黨籍及未經政黨推薦"


@reports
def test_independent_bucket_non_empty_every_term() -> None:
    """無黨籍在每一屆都必須有候選人。

    ⚠️ **這是具名的領域斷言，不是「每個桶在每屆都非零」的通則。**
    某個桶在某屆確實可能真的沒有候選人（例如民進黨在 1994 只有 3 人、
    某些選舉種類是 0）。無黨籍不同：九屆每一屆都有人以無黨籍身分參選，
    這是可查證的事實，因此可以拿來當不變量。

    ⚠️ **為什麼用真實資料而不是合成資料**（本檔其餘測試都是合成的）：
    這條要守的是「對照表涵蓋了資料裡實際出現的每一種無黨籍編碼」。
    合成資料只能證明我列出的那幾筆有效，證明不了沒有第三種編碼被漏掉。
    只有真實資料能。

    ⚠️ **為什麼 `--check` 不能取代它**：`--check` 比對「重建的常數 == 檔案現況」，
    它的辨識力來自「已提交的常數目前是對的」。若對照表漏了一筆而常數
    也是用漏了那筆的程式產生的，兩邊會一致而 `--check` 通過。
    這條斷言不依賴檔案，所以擋得住。
    """
    print("\n[真實] 無黨籍在九屆每一屆都必須有候選人")
    if not (DATA_DIR / CANDIDATES_FILE).exists():
        print("  SKIP  找不到長表")
        skipped.append("test_independent_bucket_non_empty_every_term")
        return

    summ, cands = load_long_tables()
    d = build_index_data(summ, cands)
    per_term: dict[str, int] = {}
    for t in d["types"]:
        for year, v in t["years"].items():
            if v is None:
                continue
            per_term[year] = per_term.get(year, 0) + v["party"][INDEPENDENT_BUCKET][1]

    check("涵蓋九屆", len(per_term), 9)
    for year in sorted(per_term):
        # 屆別寫進斷言名稱裡，失敗訊息才指得出是哪一屆
        check(f"{year} 的無黨籍候選人數 > 0", per_term[year] > 0, True)

    print("\n       舊五屆的實測值（修正前全部是 0）")
    for year, want in EXPECTED_INDEPENDENT_CANDS.items():
        check(f"{year} 的無黨籍候選人數", per_term.get(year), want)


# ------------------------------------------------------- 立委頁（本變更新增）

# 九屆的迴歸值。**由 build_legislative_data 實測後寫入，不是手抄**，
# 且與 design 的普查表逐格對過（1995 國民黨 77.0、2024 國民黨 41.4／
# 無黨籍 32.9／民進黨 22.5、投票率 57.9…61.4、國民黨席次 6/6/4…3）。
LEG_YEARS = ["1995", "1998", "2001", "2004", "2008", "2012", "2016", "2020", "2024"]
LEG_KMT_SHARE = [76.97, 71.54, 47.71, 40.64, 54.89, 51.52, 48.95, 48.1, 41.37]
LEG_KMT_SEATS = [6, 6, 4, 4, 4, 4, 4, 3, 3]
LEG_DPP_SEATS = [0, 0, 0, 1, 0, 0, 1, 2, 2]
LEG_TURNOUT = [57.87, 55.58, 57.84, 48.77, 47.36, 61.99, 54.79, 65.57, 61.41]
# 只在某幾屆重要的兩個桶。**這兩個數字就是立委頁不能沿用地方公職三桶的理由**：
# 那三桶會讓它們掉進「其他」，而站台照樣畫得出來。
LEG_PFP_2001 = 27.67
LEG_NPSU_2004 = 26.03


def check_raises_msg(name: str, fn, needle: str) -> None:
    """必須中止，且錯誤訊息含 `needle`。

    ⚠️ needle 要挑**只有這條檢查會輸出**的字串。挑一個到處都有的詞
       （「中止」「欄位」），另一條檢查失敗時這裡照樣綠燈。
    """
    try:
        fn()
    except SiteDataError as exc:
        if needle in str(exc):
            print(f"  PASS  {name}")
        else:
            print(f"  FAIL  {name}（訊息不含 {needle!r}：{exc}）")
            failures.append(name)
        return
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL  {name}（丟出 {type(exc).__name__}: {exc}）")
        failures.append(name)
        return
    print(f"  FAIL  {name}（沒有丟出例外）")
    failures.append(name)


def _leg_tables():
    """讀立委四張表；缺檔回 None 讓呼叫端 SKIP。"""
    if not (DATA_DIR / BOUNDS_FILE).exists():
        return None
    return load_legislative_tables()


@reports
def test_legislative_constants_regression() -> None:
    """立委常數的迴歸值：九屆得票率、席次、投票率。"""
    print("\n[真實] 立委常數的九屆迴歸值")
    tables = _leg_tables()
    if tables is None:
        print("  SKIP  找不到立委長表")
        skipped.append("test_legislative_constants_regression")
        return
    summ, cands, votes, _ = tables
    leg = build_legislative_data(summ, cands, votes)

    check("屆別九屆", leg["years"], LEG_YEARS)
    for i, y in enumerate(LEG_YEARS):
        check(f"{y} 國民黨得票率", leg["parties"][y]["中國國民黨"], LEG_KMT_SHARE[i])
        check(f"{y} 國民黨席次", leg["partySeats"][y]["中國國民黨"], LEG_KMT_SEATS[i])
        check(f"{y} 民進黨席次", leg["partySeats"][y]["民主進步黨"], LEG_DPP_SEATS[i])
        check(f"{y} 合計投票率", leg["turnout"][y], LEG_TURNOUT[i])
    check("2001 親民黨得票率（沿用三桶會消失）",
          leg["parties"]["2001"]["親民黨"], LEG_PFP_2001)
    check("2004 無黨團結聯盟得票率（沿用三桶會消失）",
          leg["parties"]["2004"]["無黨團結聯盟"], LEG_NPSU_2004)


def _leg_synth() -> tuple[list[dict], list[dict], list[dict]]:
    """一屆、一個選舉種類、三位候選人的合成立委資料。

    刻意讓 `當選註記`（來源怎麼寫）與 `當選`（權威值）**不一致**：
    乙當選了但來源沒標。方向與 2005 縣市議員兩檔相同。
    """
    term, kind = "2999", "L3"
    summ = [{c: "" for c in REQUIRED_COLUMNS[build_site_data.LEG_SUMMARY_FILE]}]
    summ[0].update(年度=term, 選舉種類=kind, 選舉種類名稱="合成選舉",
                   層級="檔別合計", 選舉人數="400", 投票數="200")

    def cand(no, name, code, party, won, mark):
        r = {c: "" for c in REQUIRED_COLUMNS[
            build_site_data.LEG_CANDIDATES_FILE]}
        r.update(年度=term, 選舉種類=kind, 號次=no, 姓名=name,
                 政黨代號=code, 政黨名稱=party, 當選=won, 當選註記=mark)
        return r

    cands = [
        cand("1", "甲", "1", "中國國民黨", "Y", "*"),
        cand("2", "乙", "16", "民主進步黨", "Y", ""),   # ← 來源漏標
        cand("3", "丙", "99", "無", "N", ""),
    ]

    def vote(no, n):
        r = {c: "" for c in REQUIRED_COLUMNS[build_site_data.LEG_VOTES_FILE]}
        r.update(年度=term, 選舉種類=kind, 層級="檔別合計", 號次=no, 得票數=n)
        return r

    votes = [vote("1", "100"), vote("2", "60"), vote("3", "40")]
    return summ, cands, votes


@reports
def test_legislative_seats_from_authoritative() -> None:
    """立委席次一律取自 `當選`（權威值），不是 `當選註記`。

    ⚠️ **這條非用合成資料不可。** 實測立委三張長表：`當選 == "Y"` 與
    `當選註記 == "*"` 各 60 筆、**逐筆一致，零筆不符**。所以把席次改讀
    `當選註記`，在現有真實資料上算出的結果**與正確實作完全相同**——
    任何只斷言真實資料輸出的測試都不可能亮紅燈（實測那項變異就是這樣漏網的）。

    地方公職那邊今天抓得到，靠的是「來源目前是壞的」（2005 兩檔少標 19 席）。
    立委的來源目前是好的，所以那份辨識力這裡根本不存在。
    """
    print("\n[合成] 立委席次取自權威值 `當選`，不是來源註記")
    print("       實測立委真實資料兩者零筆不符——這條的辨識力只能來自合成資料")
    summ, cands, votes = _leg_synth()
    leg = build_legislative_data(summ, cands, votes)
    seats = leg["partySeats"]["2999"]
    check("國民黨席次", seats["中國國民黨"], 1)
    check("民進黨席次（來源漏標，以註記算會是 0）", seats["民主進步黨"], 1)
    check("無黨籍席次", seats["無黨籍"], 0)
    check("總席次（以註記算會是 1）",
          sum(seats.values()), 2)
    check("投票率 200/400", leg["turnout"]["2999"], 50.0)
    check("國民黨得票率 100/200", leg["parties"]["2999"]["中國國民黨"], 50.0)
    check("無黨籍得票率 40/200", leg["parties"]["2999"]["無黨籍"], 20.0)


@reports
def test_bucket_sets_are_not_shared() -> None:
    """兩個分桶集合必須不相等，合併成一套要中止。"""
    print("\n[合成] 立委與地方公職的分桶集合不共用")
    check("兩個集合不相等",
          set(build_site_data.LEGISLATIVE_PARTY_BUCKETS)
          != set(build_site_data.PARTY_BUCKETS), True)
    check("立委有五個政黨桶", len(build_site_data.LEGISLATIVE_PARTY_BUCKETS), 5)
    for b in ("親民黨", "無黨團結聯盟"):
        check(f"{b} 是獨立的桶", b in build_site_data.LEGISLATIVE_PARTY_BUCKETS, True)

    old = build_site_data.LEGISLATIVE_PARTY_BUCKETS
    build_site_data.LEGISLATIVE_PARTY_BUCKETS = build_site_data.PARTY_BUCKETS
    try:
        check_raises_msg("合併成一套即中止",
                         build_site_data.check_bucket_sets_differ,
                         "合併成一套")
    finally:
        build_site_data.LEGISLATIVE_PARTY_BUCKETS = old
    check("還原後基準通過",
          build_site_data.check_bucket_sets_differ() is None, True)


@reports
def test_legislative_bucket_key_semantics() -> None:
    """立委的分桶鍵一樣是 (代號, 名稱) 配對。

    ⚠️ **非用合成資料不可，理由與地方公職那條相同。** 實測九屆的 35 組
    （代號, 名稱）：唯一一個「同代號多名稱」是代號 `9`（全國民主非政黨聯盟／
    台灣吾黨），而兩者都在對照表外、本來都歸「其他」。所以把鍵改成只用代號，
    在現有真實資料上算出的結果**與正確實作完全相同**。
    """
    print("\n[合成] 立委分桶鍵是 (代號, 名稱) 配對")
    def b(code: str, name: str) -> str:
        return build_site_data.legislative_bucket(
            {"政黨代號": code, "政黨名稱": name})

    print("       正向：同一政黨的兩個代號都要歸位")
    check("3／親民黨", b("3", "親民黨"), "親民黨")
    check("90／親民黨（新屆代號）", b("90", "親民黨"), "親民黨")
    check("7／無黨團結聯盟", b("7", "無黨團結聯盟"), "無黨團結聯盟")
    check("106／無黨團結聯盟（新屆代號）", b("106", "無黨團結聯盟"), "無黨團結聯盟")
    check("99／無（舊屆無黨籍）", b("99", "無"), "無黨籍")
    check("999／無黨籍及未經政黨推薦", b("999", "無黨籍及未經政黨推薦"), "無黨籍")

    print("\n       名稱相符代號不符 → 其他（擋下「只用名稱」）")
    check("777／親民黨", b("777", "親民黨"), "其他")
    check("777／無", b("777", "無"), "其他")

    print("\n       代號相符名稱不符 → 其他（擋下「只用代號」與代號回退）")
    check("3／某未知黨", b("3", "某未知黨"), "其他")
    check("99／某未知黨", b("99", "某未知黨"), "其他")

    print("\n       真實資料裡唯一的同代號多名稱：代號 9 的兩個政黨")
    check("9／全國民主非政黨聯盟", b("9", "全國民主非政黨聯盟"), "其他")
    check("9／台灣吾黨", b("9", "台灣吾黨"), "其他")


@reports
def test_legislative_independent_bucket_every_term() -> None:
    """無黨籍桶九屆皆非零；漏掉舊編碼要中止。

    ⚠️ 這條用真實資料。合成資料證明不了「對照表涵蓋了資料裡出現的
       每一種無黨籍編碼」——那正是這條要守的。
    """
    print("\n[真實] 立委的無黨籍桶九屆皆非零")
    tables = _leg_tables()
    if tables is None:
        print("  SKIP  找不到立委長表")
        skipped.append("test_legislative_independent_bucket_every_term")
        return
    summ, cands, votes, _ = tables
    leg = build_legislative_data(summ, cands, votes)
    for y in LEG_YEARS:
        check(f"{y} 無黨籍得票率 > 0", leg["parties"][y]["無黨籍"] > 0, True)

    print("\n       拿掉舊編碼 ('99','無') → 1995–2004 歸零並中止")
    old = dict(build_site_data.LEGISLATIVE_IDENTITY_BUCKETS)
    del build_site_data.LEGISLATIVE_IDENTITY_BUCKETS[("99", "無")]
    try:
        check_raises_msg(
            "漏掉一種無黨籍編碼即中止",
            lambda: build_legislative_data(summ, cands, votes),
            "兩套不重疊的編碼")
    finally:
        build_site_data.LEGISLATIVE_IDENTITY_BUCKETS.clear()
        build_site_data.LEGISLATIVE_IDENTITY_BUCKETS.update(old)


@reports
def test_legislative_required_column_aborts() -> None:
    """立委長表缺欄要在讀完標頭時中止，訊息含該欄名。"""
    print("\n[真實] 立委長表的必要欄位檢查")
    if not (DATA_DIR / LEG_SUMMARY_FILE).exists():
        print("  SKIP  找不到立委長表")
        skipped.append("test_legislative_required_column_aborts")
        return
    bogus = "這個欄位不存在"
    old = REQUIRED_COLUMNS[LEG_SUMMARY_FILE]
    REQUIRED_COLUMNS[LEG_SUMMARY_FILE] = old + (bogus,)
    try:
        check_raises_msg("宣告一個不存在的欄名即中止",
                         load_legislative_tables, bogus)
    finally:
        REQUIRED_COLUMNS[LEG_SUMMARY_FILE] = old
    check("還原後讀得回來", _leg_tables() is not None, True)


@reports
def test_bounds_constant_matches_csv() -> None:
    """頁面的 BOUNDS 常數與界限 CSV 逐列相符。

    ⚠️ 這裡**不呼叫 build_bounds_data 來當預期值**——那會變成拿同一段程式
       比自己。CSV 在這條測試裡獨立重算一次。
    """
    print("\n[真實] BOUNDS 常數 vs 界限 CSV 逐列")
    page = ROOT / "docs" / "legislative.html"
    if not page.exists() or not (DATA_DIR / BOUNDS_FILE).exists():
        print("  SKIP  找不到界限表或立委頁")
        skipped.append("test_bounds_constant_matches_csv")
        return
    embedded = read_embedded_constant(page, BOUNDS_MARKER)

    with open(DATA_DIR / BOUNDS_FILE, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    want: dict[tuple[str, str], dict[str, tuple]] = {}
    meta: dict[tuple[str, str], tuple] = {}
    for r in rows:
        k = (r["屆別"], r["門檻"])
        want.setdefault(k, {})[r["政黨名稱"]] = (
            round(float(r["觀察_得票率"]) * 100, 2),
            round(float(r["下界_原住民得票率"]) * 100, 2),
            round(float(r["上界_原住民得票率"]) * 100, 2))
        meta[k] = (int(r["所數"]), int(r["涵蓋原住民選舉人"]),
                   round(float(r["涵蓋率"]) * 100, 1))

    check("屆別集合", sorted(embedded["terms"]),
          sorted({y for y, _ in want}))
    check("門檻集合", sorted(embedded["thresholds"]),
          sorted({t for _, t in want}))
    bad_meta, bad_rows, n_rows = [], [], 0
    for (y, t), parties in want.items():
        m = embedded["meta"][y][t]
        if (m["stations"], m["electors"], m["coverage"]) != meta[(y, t)]:
            bad_meta.append((y, t, m, meta[(y, t)]))
        got = {r[0]: (r[1], r[2], r[3]) for r in embedded["rows"][y][t]}
        if set(got) != set(parties):
            bad_rows.append((y, t, "政黨集合不同"))
        for p, v in parties.items():
            n_rows += 1
            if got.get(p) != v:
                bad_rows.append((y, t, p, got.get(p), v))
    check("所數／涵蓋人數／涵蓋率逐組相符", bad_meta, [])
    check("每一列的觀察值與上下界相符", bad_rows[:5], [])
    check("比對過的列數", n_rows, len(rows))

    # ⚠️ **上面只比了「檔案裡的常數」對不對，沒有比「產生器」對不對。**
    #    實測後果：把 build_bounds_data 的上界改讀下界、涵蓋率改成無條件捨去、
    #    所數與涵蓋人數對調、三個門檻砍成一個——四項變異**全部漏網**，
    #    因為 HTML 裡那行是變異前寫進去的，比對兩邊都沒動到被改壞的程式。
    #    產生器必須自己被呼叫一次。
    print("\n       同一批 CSV 餵給 build_bounds_data，逐鍵比對它的輸出")
    built = build_bounds_data(rows)
    check("產生器的門檻數（砍成一個就會少）", len(built["thresholds"]), 3)
    check("產生器的門檻集合", sorted(built["thresholds"]),
          sorted({t for _, t in want}))
    bad_built = []
    for (y, t), parties in want.items():
        m = built["meta"][y][t]
        if (m["stations"], m["electors"], m["coverage"]) != meta[(y, t)]:
            bad_built.append(("meta", y, t, m, meta[(y, t)]))
        got = {r[0]: (r[1], r[2], r[3]) for r in built["rows"][y][t]}
        for p, v in parties.items():
            if got.get(p) != v:
                bad_built.append((y, t, p, got.get(p), v))
    check("產生器輸出與 CSV 逐列相符", bad_built[:5], [])
    check("產生器輸出與頁面常數相同", built, embedded)

    print("\n       上界必須嚴格大於等於下界，且不得等於觀察值以外塌成一點")
    collapsed = [(y, t, r[0]) for y in built["terms"]
                 for t in built["thresholds"]
                 for r in built["rows"][y][t] if r[2] == r[3]]
    check("沒有任何一列的上下界完全相同", collapsed[:3], [])

    print("\n       改動一個界限值 → 比對要抓得到（量測本身能失敗）")
    mutated = {p: v for p, v in want[(embedded["terms"][-1],
                                      embedded["thresholds"][0])].items()}
    first = sorted(mutated)[0]
    mutated[first] = (mutated[first][0] + 1.0,) + mutated[first][1:]
    y0, t0 = embedded["terms"][-1], embedded["thresholds"][0]
    got0 = {r[0]: (r[1], r[2], r[3]) for r in embedded["rows"][y0][t0]}
    check("變異後的觀察值與常數不同", got0[first] != mutated[first], True)


@reports
def test_bounds_section_states_coverage_first() -> None:
    """界限區塊：涵蓋率與「山地鄉」在任何百分比之前，限定語與數字同區塊。

    ⚠️ 檢查的是 `docs/legislative.html` 的**靜態文字與產生區塊的樣板**。
       面板由 JS 產生，所以樣板裡的順序就是頁面上的順序。
    """
    print("\n[頁面] 界限區塊的涵蓋率優先於任何百分比")
    page = ROOT / "docs" / "legislative.html"
    if not page.exists():
        print("  SKIP  找不到立委頁")
        skipped.append("test_bounds_section_states_coverage_first")
        return
    raw = page.read_text(encoding="utf-8")
    body = raw.split('<section id="bounds">', 1)[1].split("</section>", 1)[0]
    text = re.sub(r"<[^>]+>", "\n", body)
    pcts = [m for m in re.finditer(r"[0-9]+(?:\.[0-9]+)?%", text)]
    check("靜態文字裡有百分比", bool(pcts), True)
    check("第一個百分比就是涵蓋率 11.0%", pcts[0].group(0), "11.0%")
    check("「山地鄉」早於第一個百分比",
          text.index("山地鄉") < pcts[0].start(), True)
    check("標題不含未限定的「原住民的政黨傾向」",
          "原住民的政黨傾向" in re.search(r"<h2>(.*?)</h2>", body, re.S).group(1),
          False)

    script = raw.split("/* 04 界限", 1)[1]
    i_cov = script.index("covnum")
    # ⚠️ 這個字串隨頁面在地化改過一次（原本是 `tableFrom(t, ["政黨"`）。
    #    斷言的是**順序**不是字面，所以字串變了要跟著改——但改的時候
    #    必須確認新字串一樣只出現在該處，否則量到的是別的位置。
    i_tbl = script.index("tableFrom(t, [T.th_party")
    i_qual = script.index("qual")
    check("涵蓋率的主視覺排在表格之前", i_cov < i_tbl, True)
    check("限定語排在同一個 .bnd 區塊內的表格之後", i_tbl < i_qual, True)
    check("限定語含「不是全體原住民」",
          "不是全體原住民的政黨傾向" in build_site_data.STRINGS["bounds_qual"]["zh"],
          True)
    check("限定語帶著涵蓋率一起走", "coverage.toFixed(1)" in
          script[i_qual:i_qual + 500], True)
    check("限定語與本屆註記在同一個字串裡（不是用 + 接）",
          "{notice}" in build_site_data.STRINGS["bounds_qual"]["zh"], True)
    check("三個門檻都畫，不挑一個",
          "BOUNDS.thresholds.forEach" in script, True)


@reports
def test_existing_pages_still_reproduce() -> None:
    """既有兩頁的現有屆別逐鍵重現。

    ⚠️ 這條與 `--check` 重疊是刻意的：本變更改動了兩頁的 `<head>` 與導覽，
       而那兩處就在資料常數的同一個檔案裡。
    """
    print("\n[真實] 既有兩頁的現有屆別逐鍵重現")
    if not (DATA_DIR / CANDIDATES_FILE).exists():
        print("  SKIP  找不到長表")
        skipped.append("test_existing_pages_still_reproduce")
        return
    summ, cands = load_long_tables()
    for name, marker, builder, norm in (
        ("index.html", build_site_data.DATA_MARKER, build_index_data,
         lambda x: x),
        ("roster.html", build_site_data.ROSTER_MARKER, build_roster_data,
         build_site_data.normalise_roster),
    ):
        page = ROOT / "docs" / name
        old = read_embedded_constant(page, marker)
        new = builder(summ, cands, only_terms=old["years"])
        diffs = build_site_data.unexpected_diffs(
            build_site_data.diff_nested(norm(new), norm(old)))
        check(f"{name} 未預期差異", diffs, [])
        check(f"{name} 的屆別數", len(old["years"]), 9)



# --------------------------------------------- 選舉期間的發布規則（本變更新增）

@reports
def test_publication_record_covers_every_page() -> None:
    """發布判定紀錄必須涵蓋 docs/ 下每一個 HTML，兩個方向都驗。

    ⚠️ 這條要擋的不是「判定寫錯」（那需要人看），而是
       **「多了一頁，沒有人想起要判定」**——那是靜默的，而且必然會發生。
    """
    print("\n[真實] 發布判定紀錄的涵蓋（兩個方向）")
    rec = ROOT / "docs" / "發布判定紀錄.md"
    if not rec.exists():
        print("  SKIP  找不到發布判定紀錄")
        skipped.append("test_publication_record_covers_every_page")
        return

    check("基準通過", build_site_data.check_publication_record() is None, True)

    orig = rec.read_text(encoding="utf-8")
    tmp = Path(tempfile.mkdtemp()) / "rec.md"

    print("\n       漏列一頁 → 中止並具名該檔")
    tmp.write_text(re.sub(r"^\| `legislative\.html`.*\n", "", orig, flags=re.M),
                   encoding="utf-8")
    check_raises_msg("漏列 legislative.html",
                     lambda: build_site_data.check_publication_record(tmp),
                     "legislative.html")

    print("\n       列了不存在的頁面 → 中止並具名該檔")
    tmp.write_text(orig.replace(
        "| `index.html` |",
        "| `nosuch.html` | x | x | x | 2026-08-23 |\n| `index.html` |", 1),
        encoding="utf-8")
    check_raises_msg("列了不存在的 nosuch.html",
                     lambda: build_site_data.check_publication_record(tmp),
                     "nosuch.html")

    print("\n       投票日未查證時，階段必須是較嚴的那一段")
    tmp.write_text(orig.replace("| 投票日 | 2026-11-28（星期六） |",
                                "| 投票日 | 未查證 |", 1)
                       .replace("| **目前階段** | **選舉期間** |",
                                "| **目前階段** | **選前** |", 1),
                   encoding="utf-8")
    check_raises_msg("未查證卻標成選前",
                     lambda: build_site_data.check_publication_record(tmp),
                     "較嚴的一段")

    check("還原後仍通過",
          build_site_data.check_publication_record() is None, True)


@reports
def test_current_term_notice_is_present_and_named() -> None:
    """含歷史選舉數字的頁面必須帶本屆限定語，且檢查比對的是具名字串。

    ⚠️ **這條的重點是「比對什麼」。** 頁尾本來就有 `更新：2026-08`，
       所以用「頁面有沒有提到 2026」當判準的檢查，在限定語被刪掉之後
       **照樣通過**。下面第二段就是把這件事寫成斷言。
    """
    print("\n[真實] 本屆限定語存在，且檢查比對的是具名字串")
    page = ROOT / "docs" / "legislative.html"
    if not page.exists():
        print("  SKIP  找不到立委頁")
        skipped.append("test_current_term_notice_is_present_and_named")
        return
    notice = build_site_data.CURRENT_TERM_NOTICE
    orig = page.read_text(encoding="utf-8")
    check("立委頁含 CURRENT_TERM_NOTICE", notice in orig, True)
    check("限定語不是只寫個年份", len(notice) > 20, True)

    print("\n       拿掉限定語 → 具名字串的檢查抓得到")
    try:
        page.write_text(orig.replace(notice, "", 1), encoding="utf-8")
        # ⚠️ 限定語的檢查已從 check_publication_record 拆出來——
        #    前者只驗涵蓋（檔案集合），後者驗內容。呼叫錯的那支會永遠通過。
        check_raises_msg("缺少限定語即中止",
                         build_site_data.check_current_term_notice,
                         "legislative.html")

        print("\n       同一份被改壞的頁面：改用「有沒有提到 2026」當判準就抓不到")
        broken = page.read_text(encoding="utf-8")
        check("被改壞的頁面仍含『2026』（頁尾的更新日期）", "2026" in broken, True)
        check("所以年份判準在此為真、具名字串判準為假——兩者不等價",
              ("2026" in broken, notice in broken), (True, False))
    finally:
        page.write_text(orig, encoding="utf-8")
    check("還原後通過",
          build_site_data.check_publication_record() is None, True)


@reports
def test_frozen_indicator_shape_does_not_grow() -> None:
    """被凍結的指標，形狀不得長大。

    ⚠️ 多一屆、多一個門檻都算擴充，**即使既有的每個數字都沒變**——
       它擴大了這個指標所主張的範圍。
    """
    print("\n[真實] 政黨傾向界限的凍結形狀")
    tables = _leg_tables()
    if tables is None:
        print("  SKIP  找不到界限表")
        skipped.append("test_frozen_indicator_shape_does_not_grow")
        return
    bounds = tables[3]
    built = build_bounds_data(bounds)
    check("宣告的形狀", build_site_data.FROZEN_BOUNDS_SHAPE,
          {"terms": 5, "thresholds": 3})
    check("實際屆數", len(built["terms"]), 5)
    check("實際門檻數", len(built["thresholds"]), 3)

    print("\n       宣告值改成 6 屆 → 中止（模擬有人加了一屆）")
    old = dict(build_site_data.FROZEN_BOUNDS_SHAPE)
    build_site_data.FROZEN_BOUNDS_SHAPE["terms"] = 6
    try:
        check_raises_msg(
            "形狀不符即中止",
            lambda: build_site_data.check_frozen_indicator_shape(built),
            "已凍結")
    finally:
        build_site_data.FROZEN_BOUNDS_SHAPE.clear()
        build_site_data.FROZEN_BOUNDS_SHAPE.update(old)
    check("還原後通過",
          build_site_data.check_frozen_indicator_shape(built) is None, True)



# ------------------------------------------------------- 英文版（本變更新增）

EN_PAGES = ("en/index.html", "en/legislative.html")


@reports
def test_strings_complete_and_fields_match() -> None:
    """STRINGS 每個 key 都要有 zh 與 en，且代入欄位集合一致。"""
    print("\n[真實] STRINGS 的完整性")
    check("兩種語言", build_site_data.LANGUAGES, ("zh", "en"))
    check("基準通過", build_site_data.check_strings_complete() is None, True)
    check("key 數 ≥ 50", len(build_site_data.STRINGS) >= 50, True)

    print("\n       拿掉一個 en 值 → 中止並具名該 key")
    orig = build_site_data.STRINGS["bounds_qual"]["en"]
    build_site_data.STRINGS["bounds_qual"]["en"] = ""
    try:
        check_raises_msg("缺 en 即中止",
                         build_site_data.check_strings_complete, "bounds_qual.en")
    finally:
        build_site_data.STRINGS["bounds_qual"]["en"] = orig

    print("\n       en 少一個代入欄位 → 中止（頁面上會留下未替換的大括號）")
    build_site_data.STRINGS["bounds_qual"]["en"] = orig.replace("{rest}", "REST")
    try:
        check_raises_msg("欄位集合不一致即中止",
                         build_site_data.check_strings_complete, "代入欄位")
    finally:
        build_site_data.STRINGS["bounds_qual"]["en"] = orig
    check("還原後通過",
          build_site_data.check_strings_complete() is None, True)


@reports
def test_labels_have_provenance() -> None:
    """每個英譯標籤都要有合法出處，且未宣告者保留原文。"""
    print("\n[真實] LABELS_EN 的出處")
    check("基準通過",
          build_site_data.check_labels_have_provenance() is None, True)
    srcs = {v[1] for v in build_site_data.LABELS_EN.values()}
    check("出處都在允許值內",
          srcs <= set(build_site_data.LABEL_SOURCES), True)
    check("未宣告者保留原文", build_site_data.label_en("台灣綠黨"), "台灣綠黨")
    check("已宣告者取英譯", build_site_data.label_en("中國國民黨"),
          "Kuomintang (KMT)")

    print("\n       出處改成不允許的值 → 中止並具名該標籤")
    old = build_site_data.LABELS_EN["新黨"]
    build_site_data.LABELS_EN["新黨"] = ("New Party", "official")
    try:
        check_raises_msg("非法出處即中止",
                         build_site_data.check_labels_have_provenance, "新黨")
    finally:
        build_site_data.LABELS_EN["新黨"] = old
    check("還原後通過",
          build_site_data.check_labels_have_provenance() is None, True)

    print("\n       界限表 45 個政黨中，未宣告英譯者保留原文")
    tables = _leg_tables()
    if tables is None:
        print("  SKIP  找不到界限表")
        return
    bounds = build_bounds_data(tables[3])
    allp = {r[0] for y in bounds["rows"] for t in bounds["rows"][y]
            for r in bounds["rows"][y][t]}
    retained = [p for p in allp if p not in build_site_data.LABELS_EN]
    check("政黨總數", len(allp), 45)
    check("保留原文者", len(retained), 36)


@reports
def test_english_pages_share_the_same_data() -> None:
    """英文頁與中文頁的資料常數**逐鍵完全相同**。

    ⚠️ 這條守的是「翻譯不得改動數字」。兩版若各自產生，某一版的資料
       過時了不會有任何東西報錯——頁面照樣畫得出來。
    """
    print("\n[真實] 中英兩版的資料常數逐鍵相同")
    for zh_name, en_name, markers in (
        ("index.html", "en/index.html", (build_site_data.DATA_MARKER,)),
        ("legislative.html", "en/legislative.html",
         (build_site_data.LEG_MARKER, build_site_data.BOUNDS_MARKER)),
    ):
        zh_page = ROOT / "docs" / zh_name
        en_page = ROOT / "docs" / en_name
        if not en_page.exists():
            print(f"  SKIP  找不到 {en_name}")
            skipped.append("test_english_pages_share_the_same_data")
            return
        for marker in markers:
            a = read_embedded_constant(zh_page, marker)
            b = read_embedded_constant(en_page, marker)
            check(f"{en_name} 的 {marker.strip()} 與中文版相同", a == b, True)
        t_zh = read_embedded_constant(zh_page, build_site_data.STRINGS_MARKER)
        t_en = read_embedded_constant(en_page, build_site_data.STRINGS_MARKER)
        check(f"{en_name} 的文案 key 集合與中文版相同",
              set(t_zh) == set(t_en), True)
        check(f"{en_name} 的文案實際是英文（與中文版不同值）",
              t_zh != t_en, True)


@reports
def test_english_bounds_states_coverage_first() -> None:
    """英文界限區塊：涵蓋率與 mountain indigenous 在任何百分比之前。"""
    print("\n[頁面] 英文界限區塊的涵蓋率優先於任何百分比")
    page = ROOT / "docs" / "en" / "legislative.html"
    if not page.exists():
        print("  SKIP  找不到英文立委頁")
        skipped.append("test_english_bounds_states_coverage_first")
        return
    raw = page.read_text(encoding="utf-8")
    body = raw.split('<section id="bounds">', 1)[1].split("</section>", 1)[0]
    text = re.sub(r"<[^>]+>", "\n", body)
    pcts = [m for m in re.finditer(r"[0-9]+(?:\.[0-9]+)?%", text)]
    check("靜態文字裡有百分比", bool(pcts), True)
    check("第一個百分比是涵蓋率 11.0%", pcts[0].group(0), "11.0%")
    check("mountain indigenous 早於第一個百分比",
          text.index("mountain indigenous") < pcts[0].start(), True)
    heading = re.search(r"<h2>(.*?)</h2>", body, re.S).group(1)
    check("標題不宣稱是全體原住民的政黨傾向",
          "party leaning of indigenous" in heading, False)


@reports
def test_recursive_enumeration_is_load_bearing() -> None:
    """涵蓋檢查必須遞迴，否則子目錄的頁面會被靜默跳過。

    ⚠️ 成對驗證：同一個破壞下，列入英文頁的檢查抓得到、未列入的抓不到。
       這證明「列舉涵蓋子目錄」不是可有可無。
    """
    print("\n[真實] 遞迴列舉是承重的")
    docs = ROOT / "docs"
    rg = {p.relative_to(docs).as_posix() for p in docs.rglob("*.html")}
    g = {p.relative_to(docs).as_posix() for p in docs.glob("*.html")}
    check("rglob 看到五頁", len(rg), 5)
    check("glob 只看到三頁", len(g), 3)
    check("差集正是兩個英文頁", rg - g,
          {"en/index.html", "en/legislative.html"})

    page = ROOT / "docs" / "en" / "legislative.html"
    if not page.exists():
        print("  SKIP  找不到英文立委頁")
        skipped.append("test_recursive_enumeration_is_load_bearing")
        return
    notice = build_site_data.STRINGS["current_term_notice"]["en"]
    orig = page.read_text(encoding="utf-8")
    try:
        page.write_text(orig.replace(notice, "", 1), encoding="utf-8")
        check_raises_msg("列入英文頁 → 抓得到",
                         build_site_data.check_current_term_notice,
                         "en/legislative.html")
        old = dict(build_site_data.PAGES_REQUIRING_NOTICE)
        del build_site_data.PAGES_REQUIRING_NOTICE["en/legislative.html"]
        try:
            build_site_data.check_current_term_notice()
            check("未列入英文頁 → 抓不到（所以列舉必須涵蓋子目錄）", True, True)
        except SiteDataError:
            check("未列入英文頁 → 抓不到（所以列舉必須涵蓋子目錄）", False, True)
        finally:
            build_site_data.PAGES_REQUIRING_NOTICE.clear()
            build_site_data.PAGES_REQUIRING_NOTICE.update(old)
    finally:
        page.write_text(orig, encoding="utf-8")
    check("還原後通過",
          build_site_data.check_current_term_notice() is None, True)


@reports
def test_notice_must_be_used_not_merely_declared() -> None:
    """限定語在 T 裡有，還不夠——JS 必須真的把它畫出來。

    ⚠️ 兩個條件缺一不可，而**只有這條測試會觸發第二個**：
       只驗「T 裡有」→ 把 JS 裡用到它的那行刪掉，限定語就從畫面上消失了，
       而檢查照樣通過。實測那項變異就是這樣漏網的。
    """
    print("\n[真實] 限定語必須被用到，不只是被宣告")
    page = ROOT / "docs" / "en" / "legislative.html"
    if not page.exists():
        print("  SKIP  找不到英文立委頁")
        skipped.append("test_notice_must_be_used_not_merely_declared")
        return
    orig = page.read_text(encoding="utf-8")
    check("基準：JS 有用到 T.current_term_notice",
          "T.current_term_notice" in orig, True)
    check("基準：T 裡也有那段字",
          build_site_data.STRINGS["current_term_notice"]["en"] in orig, True)

    print("\n       只拿掉 JS 的用法、T 保持不變 → 必須中止")
    try:
        page.write_text(orig.replace("notice: T.current_term_notice",
                                     'notice: ""', 1), encoding="utf-8")
        broken = page.read_text(encoding="utf-8")
        check("T 裡仍有那段字（所以只驗 T 的檢查會通過）",
              build_site_data.STRINGS["current_term_notice"]["en"] in broken, True)
        check("但 JS 已不再用它", "T.current_term_notice" in broken, False)
        check_raises_msg("沒有任何地方用到它即中止",
                         build_site_data.check_current_term_notice,
                         "沒有任何地方用到它")
    finally:
        page.write_text(orig, encoding="utf-8")
    check("還原後通過",
          build_site_data.check_current_term_notice() is None, True)


@reports
def test_static_qualifiers_match_strings() -> None:
    """靜態限定語必須與 STRINGS 逐字相同。"""
    print("\n[真實] 靜態限定語與 STRINGS 逐字相同")
    check("基準通過",
          build_site_data.check_static_qualifiers() is None, True)
    page = ROOT / "docs" / "en" / "legislative.html"
    if not page.exists():
        print("  SKIP  找不到英文立委頁")
        skipped.append("test_static_qualifiers_match_strings")
        return
    orig = page.read_text(encoding="utf-8")
    want = build_site_data.STRINGS["datasets_not_comparable"]["en"]
    try:
        # 把限定語「改順」——這正是翻譯時最容易發生的弱化
        page.write_text(orig.replace(want, "Figures differ between pages.", 1),
                        encoding="utf-8")
        check_raises_msg("限定語被改寫即中止",
                         build_site_data.check_static_qualifiers,
                         "datasets_not_comparable")
    finally:
        page.write_text(orig, encoding="utf-8")
    check("還原後通過",
          build_site_data.check_static_qualifiers() is None, True)



# --------------------------------------------- 圖表互動性（本變更新增）

@reports
def test_bind_listens_focus_and_blur() -> None:
    """`bind()` 必須同時處理 hover 與鍵盤 focus，不是兩套實作。

    ⚠️ 這條斷言的是**同一個函式體**同時監聽兩組事件，不是「有沒有某個
       關鍵字出現在檔案某處」——那樣改成兩套各自獨立的實作也會通過。
    """
    print("\n[真實] bind() 同時監聽 pointerenter/focus 與 pointerleave/blur")
    for name in ("docs/index.html", "docs/en/index.html",
                "docs/legislative.html", "docs/en/legislative.html"):
        page = ROOT / name
        if not page.exists():
            print(f"  SKIP  找不到 {name}")
            skipped.append("test_bind_listens_focus_and_blur")
            continue
        html = page.read_text(encoding="utf-8")
        m = re.search(r"function bind\(el, text\)\{(.*?)\n\}", html, re.S)
        check(f"{name} 有 bind() 函式", m is not None, True)
        if not m:
            continue
        body = m.group(1)
        check(f"{name}: bind() 監聽 focus", '"focus"' in body, True)
        check(f"{name}: bind() 監聽 blur", '"blur"' in body, True)
        check(f"{name}: bind() 監聽 pointerenter", '"pointerenter"' in body, True)
        check(f"{name}: bind() 監聽 pointerleave", '"pointerleave"' in body, True)


@reports
def test_index_charts_link_every_main_term_and_type() -> None:
    """`index.html` 與 `en/index.html` 的可導航連結涵蓋 MAIN 的每個 (year, type)。

    ⚠️ 這條是**靜態**檢查（樣板字串與迴圈範圍），不是渲染後的逐點比對——
       渲染後的完整驗證（27／79 個連結、點擊後導向正確的名錄頁）已在
       任務 2.1／2.2／2.3 用 playwright 手動跑過，見 tasks.md 的驗證紀錄。
       這裡要擋的是「樣板字串被改壞或整段被砍掉」這種靜態就看得出來的迴歸。
    """
    print("\n[真實] 圖表連結的樣板與涵蓋迴圈範圍")
    summ, cands = load_long_tables()
    data = build_index_data(summ, cands)
    types = election_types(summ)
    main_pairs = {(y, t["code"]) for t in data["types"] if types[t["code"]]["mainSequence"]
                  for y in data["years"] if t["years"].get(y)}
    check("MAIN 的 (year, type) 組合數 > 0", len(main_pairs) > 0, True)

    for name in ("docs/index.html", "docs/en/index.html"):
        page = ROOT / name
        if not page.exists():
            print(f"  SKIP  找不到 {name}")
            skipped.append("test_index_charts_link_every_main_term_and_type")
            continue
        html = page.read_text(encoding="utf-8")
        prefix = r"\.\./" if "en/" in name else ""
        turnout_tmpl = re.search(
            rf'href: `{prefix}roster\.html#\$\{{ys\[i\]\}}/\$\{{t\.code\}}`', html)
        party_tmpl = re.search(
            rf'href: `{prefix}roster\.html#\$\{{yr\}}/\$\{{t\.code\}}`', html)
        check(f"{name}: 01 投票率圖的連結樣板逐字正確",
              turnout_tmpl is not None, True)
        check(f"{name}: 02 政黨席次圖的連結樣板逐字正確",
              party_tmpl is not None, True)

        turnout_block = html[html.index("/* 01"):html.index("/* 02")]
        party_block = html[html.index("/* 02"):html.index("/* 03")]
        check(f"{name}: 01 的 <a> 在 MAIN.forEach 範圍內",
              "MAIN.forEach" in turnout_block and 'svgEl("a"' in turnout_block, True)
        check(f"{name}: 02 的 <a> 在 MAIN.forEach 範圍內",
              "MAIN.forEach" in party_block and 'svgEl("a"' in party_block, True)


@reports
def test_legislative_page_has_no_roster_navigation() -> None:
    """立委頁不得出現任何導向 `roster.html` 的圖表連結（決策 3 的邊界）。

    ⚠️ 導覽列本來就有連到 roster.html 的連結（名錄分頁），那是正常的、
       不該被這條檢查誤判——只查 SVG 圖表區塊內，不查整個檔案。
    """
    print("\n[真實] 立委頁的圖表區塊沒有導向 roster.html 的連結")
    for name in ("docs/legislative.html", "docs/en/legislative.html"):
        page = ROOT / name
        if not page.exists():
            print(f"  SKIP  找不到 {name}")
            skipped.append("test_legislative_page_has_no_roster_navigation")
            continue
        html = page.read_text(encoding="utf-8")
        script = html[html.index("<script>"):html.index("</script>")]
        check(f"{name}: script 區塊不含 roster.html 連結樣板",
              "roster.html" not in script, True)


# -------------------------------------------------- 標題語意斷詞（BudouX）

HEADING_RE = re.compile(r"<(h[12])>(.*?)</\1>")


@reports
def test_heading_segmentation_preserves_visible_text() -> None:
    """插入 <wbr> 不能改變、增減任何可見文字。"""
    print("\n[真實] 標題斷詞不改變可見文字")
    for name in ("docs/index.html", "docs/legislative.html"):
        page = ROOT / name
        if not page.exists():
            print(f"  SKIP  找不到 {name}")
            skipped.append("test_heading_segmentation_preserves_visible_text")
            continue
        html = page.read_text(encoding="utf-8")
        headings = HEADING_RE.findall(html)
        check(f"{name}: 至少有一個 h1/h2 標題可供測試", len(headings) > 0, True)
        for tag, inner in headings:
            original_text = inner.replace("<br>", "").replace("<wbr>", "")
            full = f"<{tag}>{inner}</{tag}>"
            segmented = segment_headings(full, name)
            segmented_text = re.sub(r"</?(?:wbr|br|h[12])>", "", segmented)
            check(f"{name}: <{tag}>{original_text}</{tag}> 純文字保留一致",
                  segmented_text, original_text)


@reports
def test_heading_segmentation_single_chunk_has_no_wbr() -> None:
    """BudouX 只判定出一段語意時，輸出不得含 <wbr>——這不是失敗，是正確行為。"""
    print("\n[合成] 單一語意段的標題不含 <wbr>")
    out = segment_headings("<h2>性別</h2>", "合成")
    check("單段標題輸出不含 <wbr>", "<wbr>" in out, False)
    check("單段標題可見文字不變", out, "<h2>性別</h2>")


@reports
def test_heading_segmentation_replaces_manual_br_with_wbr() -> None:
    """index.html 現有 h1 手動寫死的 <br> 已由 BudouX 產生的 <wbr> 取代。"""
    print("\n[真實] index.html 的 h1 手動 <br> 被 BudouX 斷詞取代")
    page = ROOT / "docs" / "index.html"
    if not page.exists():
        print("  SKIP  找不到 docs/index.html")
        skipped.append("test_heading_segmentation_replaces_manual_br_with_wbr")
        return
    html = page.read_text(encoding="utf-8")
    m = re.search(r"<h1>.*?</h1>", html)
    check("index.html 找得到 <h1>", m is not None, True)
    if m is None:
        return
    current_h1 = m.group(0)
    # 這是對「跑過 --write 之後的檔案現況」做的靜態斷言，不是重跑
    # segment_headings 再驗證——現況已經沒有手動 <br> 可供重新取代，
    # 直接重跑只會得到「本來就沒有」這種恆真的弱驗證。
    check("目前檔案的 h1 不含手動 <br>", "<br>" in current_h1, False)
    check("目前檔案的 h1 含至少一個 BudouX 產生的 <wbr>",
          "<wbr>" in current_h1, True)


@reports
def test_heading_segmentation_rejects_unsupported_markup() -> None:
    """標題內含 <br> 以外的子標籤必須中止，不可靜默略過或照原文字通過去。"""
    print("\n[合成] 標題含不支援的子標籤時中止")
    check_raises_msg(
        "含 <span> 的標題會中止",
        lambda: segment_headings("<h2>前<span>中</span>後</h2>", "合成頁面"),
        "不支援的子標籤")


@reports
def test_heading_css_enforces_semantic_break_points() -> None:
    """h1/h2 的 CSS 規則要有 word-break:keep-all 與 overflow-wrap:anywhere。

    少了這兩個屬性，<wbr> 只是多一個斷行選項，瀏覽器對 CJK 文字預設的
    逐字斷行規則照樣可能蓋過它，在窄螢幕把 BudouX 判定的同一語意片段
    從中間切開。
    """
    print("\n[真實] 中文頁面的 h1/h2 CSS 含斷行控制屬性")
    for name in ("docs/index.html", "docs/legislative.html"):
        page = ROOT / name
        if not page.exists():
            print(f"  SKIP  找不到 {name}")
            skipped.append("test_heading_css_enforces_semantic_break_points")
            continue
        html = page.read_text(encoding="utf-8")
        style = html[html.index("<style>"):html.index("</style>")]
        for tag in ("h1", "h2"):
            m = re.search(rf"^{tag}\{{[^}}]*\}}", style, re.MULTILINE)
            check(f"{name}: 找得到裸的 {tag}{{...}} 規則", m is not None, True)
            if m is None:
                continue
            rule = m.group(0)
            check(f"{name}: {tag}{{...}} 含 word-break:keep-all",
                  "word-break:keep-all" in rule, True)
            check(f"{name}: {tag}{{...}} 含 overflow-wrap:anywhere",
                  "overflow-wrap:anywhere" in rule, True)


@reports
def test_heading_segmentation_scope_excludes_en_and_roster() -> None:
    """只有 docs/index.html、docs/legislative.html 套用標題斷詞。"""
    print("\n[真實] 標題斷詞的範圍不含英文頁與 roster.html")
    zh_pages = {p.name for p in build_site_data.ZH_HEADING_PAGES}
    check("ZH_HEADING_PAGES 只含 index.html 與 legislative.html",
          zh_pages, {"index.html", "legislative.html"})
    for name in ("docs/en/index.html", "docs/en/legislative.html"):
        page = ROOT / name
        if not page.exists():
            print(f"  SKIP  找不到 {name}")
            skipped.append("test_heading_segmentation_scope_excludes_en_and_roster")
            continue
        html = page.read_text(encoding="utf-8")
        headings = HEADING_RE.findall(html)
        check(f"{name}: 至少有一個 h1/h2 標題可供測試", len(headings) > 0, True)
        check(f"{name}: 標題不含 <wbr>（英文頁不套用中文斷詞）",
              "<wbr>" in html, False)
    roster = ROOT / "docs" / "roster.html"
    if roster.exists():
        html = roster.read_text(encoding="utf-8")
        check("roster.html 仍含 JS 動態產生縣市標題的樣板",
              '<h2>${county}</h2>' in html, True)
    else:
        print("  SKIP  找不到 docs/roster.html")
        skipped.append("test_heading_segmentation_scope_excludes_en_and_roster")


@reports
def test_heading_segmentation_is_idempotent() -> None:
    """連續斷詞兩次，第二次相對第一次的輸出沒有任何差異。"""
    print("\n[真實] 標題斷詞冪等")
    for name in ("docs/index.html", "docs/legislative.html"):
        page = ROOT / name
        if not page.exists():
            print(f"  SKIP  找不到 {name}")
            skipped.append("test_heading_segmentation_is_idempotent")
            continue
        html = page.read_text(encoding="utf-8")
        for tag, inner in HEADING_RE.findall(html):
            full = f"<{tag}>{inner}</{tag}>"
            once = segment_headings(full, name)
            twice = segment_headings(once, name)
            check(f"{name}: <{tag}> 重跑斷詞第二次與第一次相同", twice, once)


def main() -> int:
    for fn in (test_seats_from_authoritative,
               test_no_winners_does_not_divide_by_zero,
               test_zero_electors_turnout_is_none,
               test_site_mark_branches,
               test_main_sequence_flag_passthrough,
               test_index_html_filters_custom_types,
               test_turnout_round_half_up,
               test_required_columns_matches_actual_reads,
               test_missing_column_aborts_at_header,
               test_party_bucket_key_semantics,
               test_party_code_and_name_hygiene,
               test_age_read_from_derived_column,
               test_roster_main_projection,
               test_independent_bucket_non_empty_every_term,
               test_legislative_constants_regression,
               test_legislative_seats_from_authoritative,
               test_bucket_sets_are_not_shared,
               test_legislative_bucket_key_semantics,
               test_legislative_independent_bucket_every_term,
               test_legislative_required_column_aborts,
               test_bounds_constant_matches_csv,
               test_bounds_section_states_coverage_first,
               test_existing_pages_still_reproduce,
               test_publication_record_covers_every_page,
               test_current_term_notice_is_present_and_named,
               test_frozen_indicator_shape_does_not_grow,
               test_strings_complete_and_fields_match,
               test_labels_have_provenance,
               test_english_pages_share_the_same_data,
               test_english_bounds_states_coverage_first,
               test_recursive_enumeration_is_load_bearing,
               test_notice_must_be_used_not_merely_declared,
               test_static_qualifiers_match_strings,
               test_bind_listens_focus_and_blur,
               test_index_charts_link_every_main_term_and_type,
               test_legislative_page_has_no_roster_navigation,
               test_heading_segmentation_preserves_visible_text,
               test_heading_segmentation_single_chunk_has_no_wbr,
               test_heading_segmentation_replaces_manual_br_with_wbr,
               test_heading_segmentation_rejects_unsupported_markup,
               test_heading_css_enforces_semantic_break_points,
               test_heading_segmentation_scope_excludes_en_and_roster,
               test_heading_segmentation_is_idempotent):
        try:
            fn()
        except AssertionError:
            pass

    print("\n" + "=" * 60)
    if failures:
        print(f"失敗 {len(failures)} 項：")
        for f in failures:
            print(f"  - {f}")
        return 1
    msg = "全數通過"
    if skipped:
        msg += f"（跳過 {len(skipped)} 項：{', '.join(skipped)}）"
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
