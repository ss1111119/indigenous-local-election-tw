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
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_site_data  # noqa: E402
from build_site_data import (  # noqa: E402
    CANDIDATES_FILE,
    REQUIRED_COLUMNS,
    SUMMARY_FILE,
    SiteDataError,
    build_index_data,
    build_roster_data,
    election_types,
    load_long_tables,
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
# 刻意讓 `當選` 與 `elected_authoritative` **不一致**，且不一致的方向與 2005
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
                 當選註記="*", elected_authoritative="true",
                 行政區名稱="測試縣第01選舉區"),
        cand_row(**base, 選舉區="01", 號次="2", 姓名="乙", 政黨代號="16", 政黨名稱="民主進步黨",
                 性別="女", 年齡="40", 現任="Y",
                 當選註記="", elected_authoritative="true",
                 行政區名稱="測試縣第01選舉區"),
        cand_row(**base, 選舉區="02", 號次="1", 姓名="丙", 政黨代號="1", 政黨名稱="中國國民黨",
                 性別="女", 年齡="45", 現任="N",
                 當選註記="", elected_authoritative="false",
                 行政區名稱="測試縣第02選舉區"),
        cand_row(**base, 選舉區="02", 號次="2", 姓名="丁", 政黨代號="777", 政黨名稱="某小黨",
                 性別="男", 年齡="60", 現任="Y",
                 當選註記="", elected_authoritative="false",
                 行政區名稱="測試縣第02選舉區"),
    ]


# -------------------------------------------------- 一、席次取自權威值而非 當選

@reports
def test_seats_from_authoritative() -> None:
    print("\n[合成] 席次相關指標一律取自 elected_authoritative，不是 `當選`")
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
    cands = [dict(c, elected_authoritative="false", 當選註記="")
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
        return site_mark({"當選註記": note, "elected_authoritative": auth})

    check("`!` 婦女保障當選 → 保留 !", mark("!", "true"), "!")
    check("`-` 因婦女保障被排擠 → 保留 -", mark("-", "false"), "-")
    check("`*` 且權威值當選 → *", mark("*", "true"), "*")
    check("空白且權威值未當選 → 空白", mark("", "false"), "")
    check("空白但權威值當選 → *（2005 兩檔的修復方向）",
          mark("", "true"), "*")
    check("`*` 但權威值未當選 → 空白（1994 高雄市的修復方向）",
          mark("*", "false"), "")


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
                 當選註記="*", elected_authoritative="true",
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

    for col in ("鄉鎮市區", "admin_code_system", "elected_authoritative",
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


# -------------------------------- 六b、年齡直接取自長表的 `年齡_有效`（合成）

@reports
def test_age_read_from_derived_column() -> None:
    """站台**讀取** `年齡_有效`，不自行推導未記載的判準。

    ⚠️ 判準（哪些屆別的 99 算未記載）與守住它的兩條斷言都在長表建置端，
    見 scripts/build_local_election.py 的 valid_age 與 check_age_sentinel，
    測試在 scripts/test_build_local_election.py。

    同一個規則若在兩處各有一份實作，其中一份必然漂移——這個專案已經因此
    出過兩個 bug（名錄的 MAIN 手寫一份、政黨分桶只認一種名稱）。所以這裡
    要守的不是判準本身，而是「站台沒有第二份判準」。
    """
    print("\n[合成] 名錄的年齡取自長表的 `年齡_有效`，站台不重算判準")

    def roster_age(valid: str):
        cands = [dict(c, **{"年齡_有效": valid}) for c in _mixed_cands()]
        d = build_roster_data(_mixed_summary(), cands)
        return d["rows"][_TERM][_TYPE][0][2][0][4]

    check("有值時原樣帶入", roster_age("45"), 45)
    check("留空時為 None（常數裡是 null）", roster_age(""), None)

    print("\n       站台原始碼不得再出現自己的哨兵判準實作")
    src = SRC.read_text(encoding="utf-8")
    for token in ("AGE_UNRECORDED_TERMS", "AGE_ALWAYS_NO_DATA",
                  "AGE_UNRECORDED_VALUE", "def display_age",
                  "def check_age_sentinel"):
        check(f"未出現 {token}", token in src, False)


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
               test_independent_bucket_non_empty_every_term):
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
