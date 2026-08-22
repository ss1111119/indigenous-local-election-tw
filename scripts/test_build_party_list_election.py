#!/usr/bin/env python3
"""`build_party_list_election.py` 的測試。

用法：
    python scripts/test_build_party_list_election.py
    pytest scripts/test_build_party_list_election.py

⚠️ **每一條 Failure mode 都要有一組會觸發它的輸入，且斷言錯誤訊息含
   只有那條檢查會輸出的字串。** 只斷言「有中止」不算——中止的路徑不只
   一條時，專責檢查會被別的檢查掩護而假通過。這個專案在那上面出過事。

⚠️ 迴歸值全部來自 `--census` 產生的常數或實際執行，不手抄。
   手抄宣告值在這個 change 造成過八次錯誤。
"""
from __future__ import annotations

import copy
import gzip
import csv
import sys
import zipfile
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_party_list_election as P  # noqa: E402
from build_local_election import ValidationError, zip_names  # noqa: E402
from oracles import (  # noqa: E402
    PARTY_LIST_MANIFEST,
    SEMANTIC_LEVELS,
    check_manifest_against,
)

OUT = ROOT / "data" / "processed"
failures: list[str] = []
skipped: list[str] = []


def check(label: str, got, want) -> None:
    if got == want:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}\n          得到 {got!r}\n          預期 {want!r}")
        failures.append(label)


def check_raises_msg(label: str, fn, phrase: str) -> None:
    """斷言 fn 丟出 ValidationError 且訊息含 phrase。

    ⚠️ phrase 必須是**只有目標檢查會輸出的字串**。
    """
    try:
        fn()
    except ValidationError as exc:
        if phrase in str(exc):
            print(f"  PASS  {label}")
        else:
            print(f"  FAIL  {label}（中止了，但訊息不含 {phrase!r}）"
                  f"\n          實際：{str(exc)[:120]}")
            failures.append(label)
        return
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL  {label}（丟出 {type(exc).__name__}）")
        failures.append(label)
        return
    print(f"  FAIL  {label}（沒有中止）")
    failures.append(label)


def reports(fn):
    """跑完一組後若有失敗就丟 AssertionError，讓 pytest 逐組報。

    ⚠️ 少了這一層，失敗只會被記進清單而 pytest 仍報 passed——
       本專案在那上面出過事（76 項測試在 pytest 下永遠通過）。
    """
    def wrapper():
        before = len(failures)
        fn()
        new = failures[before:]
        assert not new, f"{fn.__name__} 有 {len(new)} 項失敗：{new}"
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


# ══════════════════════════════════════════════════════════════════
# 實跑管線的快取（找不到壓縮檔時整組跳過而不是假通過）
# ══════════════════════════════════════════════════════════════════
_CACHE: dict = {}


def pipeline(year: str = "2024"):
    """跑一屆的完整前段，回傳 (src, shares, gaps, ind_total)。"""
    if year in _CACHE:
        return _CACHE[year]
    if not P.ZIP_PATH.exists():
        return None
    with zipfile.ZipFile(P.ZIP_PATH) as zf:
        names = zip_names(zf)
        src = P.load_term(zf, names, year)
        ind, ind_total = P.indigenous_station_totals(zf, names, year)
        shares, gaps = P.indigenous_shares(year, src["elprof"], ind, ind_total)
    _CACHE[year] = (src, shares, gaps, ind_total)
    return _CACHE[year]


def party_of_number(src) -> dict:
    paty = {r[0]: r[1] for r in src["elpaty"]}
    return {c[5]: P.party_key(c[7], paty.get(c[7], c[7]))
            for c in src["elcand"]}


# ══════════════════════════════════════════════════════════════════
# 單元：極限法的公式本身
# ══════════════════════════════════════════════════════════════════
@reports
def test_bounds_formula() -> None:
    """Duncan-Davis 極限法。不碰檔案，純算術。"""
    print("\n[單元] 極限法公式")
    F = Fraction

    # q = 1 時界限退化成觀察值本身——沒有非原住民可混入
    lo, hi = P.duncan_davis_bounds(F(68, 100), F(1))
    check("q=1 時上下界等於觀察值", (lo, hi), (F(68, 100), F(68, 100)))

    # 未截斷時寬度恰為 (1-q)/q
    y, q = F(1, 2), F(9, 10)
    lo, hi = P.duncan_davis_bounds(y, q)
    check("未截斷時寬度恰為 (1-q)/q", hi - lo, (1 - q) / q)

    # 下界截斷：y 很小時下界為 0
    lo, hi = P.duncan_davis_bounds(F(1, 100), F(9, 10))
    check("y 遠小於 (1-q) 時下界截斷為 0", lo, F(0))
    check("下界截斷時寬度小於 (1-q)/q", hi - lo < (1 - F(9, 10)) / F(9, 10), True)

    # 上界截斷：y 大於 q 時上界為 1
    lo, hi = P.duncan_davis_bounds(F(98, 100), F(9, 10))
    check("y 大於 q 時上界截斷為 1", hi, F(1))

    # 界限必然含住觀察值
    for yi in (1, 25, 50, 75, 99):
        y = F(yi, 100)
        lo, hi = P.duncan_davis_bounds(y, F(97, 100))
        check(f"y={yi}% 時界限含住觀察值", lo <= y <= hi, True)

    # 定義域
    check_raises_msg("q=0 即中止",
                     lambda: P.duncan_davis_bounds(F(1, 2), F(0)),
                     "q 必須落在")
    check_raises_msg("y>1 即中止",
                     lambda: P.duncan_davis_bounds(F(2), F(1, 2)),
                     "觀察得票率必須落在")


@reports
def test_bounds_guard() -> None:
    """守門員：含住觀察值 ＋ 寬度不超過 (1-q)/q。

    ⚠️ 只驗「含住」擋不住把界限【放鬆】的錯誤——(1-q) 寫成 (1+q) 時
       下界被 clamp 成 0，含住關係照樣成立。實測那個變異確實漏掉，
       所以另加寬度恆等式。這一組就是在守那個發現。
    """
    print("\n[單元] 界限守門員")
    F = Fraction
    y, q = F(681, 1000), F(97, 100)
    lo, hi = P.duncan_davis_bounds(y, q)
    P.check_bounds_contain("基準", y, q, lo, hi)
    print("  PASS  基準：正確的界限通過")

    check_raises_msg("上下界對調即中止",
                     lambda: P.check_bounds_contain("x", y, q, hi, lo),
                     "界限不含觀察值")
    check_raises_msg("下界高於觀察值即中止",
                     lambda: P.check_bounds_contain("x", y, q, y + F(1, 100), hi),
                     "界限不含觀察值")
    check_raises_msg("上界低於觀察值即中止",
                     lambda: P.check_bounds_contain("x", y, q, lo, y - F(1, 100)),
                     "界限不含觀察值")
    # ⚠️ 這一項是關鍵：界限含住觀察值，但被放寬
    check_raises_msg("界限被放寬（仍含住觀察值）即中止",
                     lambda: P.check_bounds_contain("x", y, q, F(0), F(1)),
                     "超過 (1-q)/q")
    check_raises_msg("上界超過 1 即中止",
                     lambda: P.check_bounds_contain("x", y, q, lo, F(2)),
                     "界限不含觀察值")


# ══════════════════════════════════════════════════════════════════
# 單元：宣告與個資
# ══════════════════════════════════════════════════════════════════
@reports
def test_declarations() -> None:
    """逐檔宣告的形狀。不碰檔案。"""
    print("\n[單元] 宣告")
    check("七個來源檔皆宣告欄數", sorted(P.SOURCE_COLS),
          ["elbase", "elcand", "elctks", "elpaty", "elprof", "elrepm",
           "elretks"])
    check("欄數與官方格式文件相符",
          [P.SOURCE_COLS[s] for s in
           ("elbase", "elcand", "elpaty", "elprof", "elctks", "elrepm",
            "elretks")],
          [6, 16, 2, 20, 10, 10, 5])
    check("五屆皆具名", sorted(P.TERMS),
          ["2008", "2012", "2016", "2020", "2024"])
    # ⚠️ 帶前置單引號的是【值內】的引號，不是 CSV 雙引號。
    check("帶前置單引號的 7 個檔", sorted(P.QUOTED_FILES),
          [("2008", "elcand"), ("2008", "elrepm"),
           ("2012", "elbase"), ("2012", "elcand"), ("2012", "elctks"),
           ("2012", "elprof"), ("2012", "elrepm")])
    check("2016 起沒有任何檔帶前置單引號",
          [k for k in P.QUOTED_FILES if k[0] in ("2016", "2020", "2024")], [])
    check("elpaty 不帶檔名後綴", sorted(P.FILES_WITHOUT_SUFFIX), ["elpaty"])
    check("2016 的路徑帶 _T4、elpaty 不帶",
          (P.source_path("2016", "elprof").endswith("elprof_T4.csv"),
           P.source_path("2016", "elpaty").endswith("elpaty.csv")),
          (True, True))
    # 選區欄：2008 與 2012 起不同
    check("2008 的 elprof 選區欄只允許 00",
          sorted(P.district_allowed("2008", "elprof")), ["00"])
    check("2024 的 elprof 選區欄允許 00 與 01",
          sorted(P.district_allowed("2024", "elprof")), ["00", "01"])
    # 配對鍵忽略選區欄
    row = ["63", "000", "01", "010", "0002", "0597"]
    check("unit_key 忽略選區欄", P.unit_key(row),
          ("63", "000", "010", "0002", "0597"))
    check("選區欄改變不影響鍵",
          P.unit_key(row) == P.unit_key(["63", "000", "00"] + row[3:]), True)
    # 席次是制度事實
    check("不分區應選席次為 34", P.AT_LARGE_SEATS, 34)
    # 政黨鍵含名稱
    check("party_key 是（代號, 名稱）配對",
          P.party_key("1", "中國國民黨"), ("1", "中國國民黨"))
    check("漂移代號 9 個且與宣告數一致",
          (len(P.KNOWN_PARTY_CODE_DRIFT), P.EXPECTED_DRIFT_COUNT), (9, 9))
    check("門檻宣告", [str(t) for t in P.THRESHOLDS], ["0.95", "0.90", "0.80"])


@reports
def test_personal_data_excluded() -> None:
    """elrepm 的個資欄一律不進輸出。

    ⚠️ 守的不是「這次沒寫進去」，是「以後也不會被加進去」——
       elrepm 就在同一支腳本裡，欄位取用只差一個索引。
    """
    print("\n[單元] 個資排除")
    check("宣告的個資欄索引", sorted(P.PERSONAL_DATA_COLS),
          [4, 6, 7])
    for word in ("出生日期", "出生地", "學歷", "生日"):
        check_raises_msg(f"輸出欄名含「{word}」即中止",
                         lambda w=word: P.check_no_personal_data(
                             {"t": [{"屆別": "2024", w: "x"}]}),
                         "含個資字樣")
    P.check_no_personal_data({"t": [{"屆別": "2024", "得票數": "1"}]})
    print("  PASS  基準：正常欄名通過")

    # 已發布的四份輸出，逐欄確認
    for name, gz in (("cec-party-list-summary-long.csv.gz", True),
                     ("cec-party-list-votes-long.csv.gz", True),
                     ("cec-party-list-seats.csv", False),
                     ("indigenous-party-preference-bounds.csv", False)):
        path = OUT / name
        if not path.exists():
            skipped.append(f"{name} 尚未產生")
            continue
        op = (gzip.open(path, "rt", encoding="utf-8") if gz
              else open(path, encoding="utf-8"))
        with op as fh:
            cols = [c.lstrip("﻿") for c in next(csv.reader(fh))]
        bad = [c for c in cols
               if any(w in c for w in P.FORBIDDEN_COLUMN_WORDS)]
        check(f"{name} 無個資欄", bad, [])


@reports
def test_manifest() -> None:
    """欄位 oracle 宣告與實際輸出逐欄相符。"""
    print("\n[單元] 欄位 oracle")
    check("三張官方表皆宣告", sorted(PARTY_LIST_MANIFEST),
          ["party_list_seats", "party_list_summary", "party_list_votes"])
    for table, cols in PARTY_LIST_MANIFEST.items():
        bad = [c for c, d in cols.items()
               if d["semantic"] not in SEMANTIC_LEVELS]
        check(f"{table} 的 semantic 值皆合法", bad, [])

    actual = {}
    for table, name, gz in (
        ("party_list_summary", "cec-party-list-summary-long.csv.gz", True),
        ("party_list_votes", "cec-party-list-votes-long.csv.gz", True),
        ("party_list_seats", "cec-party-list-seats.csv", False),
    ):
        path = OUT / name
        if not path.exists():
            skipped.append(f"{name} 尚未產生")
            continue
        op = (gzip.open(path, "rt", encoding="utf-8") if gz
              else open(path, encoding="utf-8"))
        with op as fh:
            actual[table] = [c.lstrip("﻿") for c in next(csv.reader(fh))]
    if actual:
        check("manifest 與輸出逐欄相符",
              check_manifest_against(PARTY_LIST_MANIFEST, actual), [])
    # 多一欄要被抓到
    if "party_list_seats" in actual:
        problems = check_manifest_against(
            PARTY_LIST_MANIFEST,
            {"party_list_seats": actual["party_list_seats"] + ["多餘欄"]})
        check("輸出多一欄即回報", len(problems), 1)


# ══════════════════════════════════════════════════════════════════
# 整合：對真實來源跑檢查，並以合成缺陷確認每一條都會失敗
# ══════════════════════════════════════════════════════════════════
@reports
def test_source_guards() -> None:
    """讀檔層的四條檢查各配一組會觸發它的輸入。"""
    print("\n[整合] 讀檔層的守衛")
    if not P.ZIP_PATH.exists():
        skipped.append("test_source_guards")
        print("  SKIP  找不到原始壓縮檔")
        return
    with zipfile.ZipFile(P.ZIP_PATH) as zf:
        names = zip_names(zf)

        # 基準：五屆七檔皆通過
        for year in P.TERMS:
            P.load_term(zf, names, year)
        print("  PASS  基準：五屆七檔皆通過")

        def probe(label, mutate, phrase, year="2024", stem="elprof"):
            restore = mutate()
            try:
                check_raises_msg(
                    label,
                    lambda: P.load_source(zf, names, year, stem), phrase)
            finally:
                restore()

        def m_cols():
            old = P.SOURCE_COLS["elprof"]
            P.SOURCE_COLS["elprof"] = old + 1
            return lambda: P.SOURCE_COLS.__setitem__("elprof", old)

        def m_rows():
            key = ("2024", "elprof")
            old = P.EXPECTED_ROWS[key]
            P.EXPECTED_ROWS[key] = old + 1
            return lambda: P.EXPECTED_ROWS.__setitem__(key, old)

        def m_district():
            old = P.DISTRICT_ALLOWED_ELPROF["2024"]
            P.DISTRICT_ALLOWED_ELPROF["2024"] = {"01"}
            return lambda: P.DISTRICT_ALLOWED_ELPROF.__setitem__("2024", old)

        def m_quote_declared():
            old = P.QUOTED_FILES
            P.QUOTED_FILES = frozenset(old | {("2024", "elprof")})
            return lambda: setattr(P, "QUOTED_FILES", old)

        def m_quote_missing():
            old = P.QUOTED_FILES
            P.QUOTED_FILES = frozenset(old - {("2008", "elcand")})
            return lambda: setattr(P, "QUOTED_FILES", old)

        probe("欄數宣告改錯即中止", m_cols, "欄")
        probe("列數宣告改錯即中止", m_rows, "宣告值為")
        probe("選區欄宣告改錯即中止", m_district, "宣告允許")
        probe("宣告有引號但來源沒有即中止", m_quote_declared, "宣告已過期")
        probe("來源有引號但未宣告即中止", m_quote_missing, "未具名宣告",
              year="2008", stem="elcand")
        check_raises_msg(
            "路徑落在 old/ 即中止",
            lambda: P.check_no_excluded_path(
                "votedata/votedata/voteData/2016總統立委/old/不分區政黨/elprof.csv"),
            "具名排除的目錄")


@reports
def test_cross_file_guards() -> None:
    """跨檔對帳的檢查各配一組會觸發它的輸入。"""
    print("\n[整合] 跨檔對帳的守衛")
    got = pipeline("2024")
    if got is None:
        skipped.append("test_cross_file_guards")
        print("  SKIP  找不到原始壓縮檔")
        return
    src, shares, gaps, ind_total = got

    units = P.check_votes_reconcile("2024", src["elprof"], src["elctks"])
    check("2024 逐所對帳的單位數", units, P.EXPECTED_ROWS[("2024", "elprof")])

    # 政黨票加總改一票
    ctks = [list(r) for r in src["elctks"]]
    ctks[0][P.T_VOTES] = str(int(ctks[0][P.T_VOTES]) + 1)
    check_raises_msg("某所的政黨票加總不等於有效票即中止",
                     lambda: P.check_votes_reconcile(
                         "2024", src["elprof"], ctks),
                     "政黨票加總不等於有效票")

    # 鍵含選區欄 → 2008 幾乎全部對不上
    got8 = pipeline("2008")
    if got8 is not None:
        src8 = got8[0]
        orig = P.unit_key
        P.unit_key = lambda r: (r[0], r[1], r[2], r[3], r[4], r[5])
        try:
            check_raises_msg(
                "配對鍵含選區欄時 2008 即中止",
                lambda: P.check_votes_reconcile(
                    "2008", src8["elprof"], src8["elctks"]),
                "不存在於 elprof")
        finally:
            P.unit_key = orig

    # elprof 的鍵重複
    prof = [list(r) for r in src["elprof"]]
    dup = next(r for r in prof if r[5].strip("0"))
    check_raises_msg("elprof 的單位鍵重複即中止",
                     lambda: P.check_votes_reconcile(
                         "2024", prof + [list(dup)], src["elctks"]),
                     "重複")


@reports
def test_party_and_seats() -> None:
    """政黨鍵與席次不變量。"""
    print("\n[整合] 政黨與席次")
    if not P.ZIP_PATH.exists():
        skipped.append("test_party_and_seats")
        print("  SKIP  找不到原始壓縮檔")
        return
    with zipfile.ZipFile(P.ZIP_PATH) as zf:
        names = zip_names(zf)
        sources = {y: P.load_term(zf, names, y) for y in P.TERMS}

    tables = P.party_names_by_term(sources)
    drift = P.check_party_code_drift(tables)
    check("跨屆漂移的代號", sorted(drift, key=int),
          sorted(P.KNOWN_PARTY_CODE_DRIFT, key=int))
    check("代號 1 與 16 五屆穩定",
          [{t[c] for t in tables.values() if c in t} for c in ("1", "16")],
          [{"中國國民黨"}, {"民主進步黨"}])

    bad = copy.deepcopy(sources)
    bad["2024"]["elpaty"] = list(sources["2024"]["elpaty"]) + [["1", "偽政黨"]]
    check_raises_msg("同屆同代號兩名稱即中止",
                     lambda: P.party_names_by_term(bad),
                     "對到兩個名稱")

    old_list = P.KNOWN_PARTY_CODE_DRIFT
    P.KNOWN_PARTY_CODE_DRIFT = frozenset(old_list - {"79"})
    try:
        check_raises_msg("漂移清單少一筆即中止",
                         lambda: P.check_party_code_drift(tables),
                         "清單過期")
    finally:
        P.KNOWN_PARTY_CODE_DRIFT = old_list

    for year in P.TERMS:
        stats = P.check_seat_allocation(year, sources[year]["elretks"])
        check(f"{year} 當選人數合計為 34", stats["當選人數"], 34)

    retks = [list(r) for r in sources["2024"]["elretks"]]
    retks[0][P.R_SEATS] = str(int(retks[0][P.R_SEATS]) + 1)
    check_raises_msg("席次合計不是 34 即中止",
                     lambda: P.check_seat_allocation("2024", retks),
                     "不分區應選席次")

    # ⚠️ 得票率合計不是恆為 100.0000
    check("得票率合計逐屆的具名值",
          {y: (P.EXPECTED_RATE_SUMS[y]["stage1"],
               P.EXPECTED_RATE_SUMS[y]["stage2"]) for y in P.TERMS},
          {"2008": ("100.0000", "100.0000"),
           "2012": ("99.9998", "100.0000"),
           "2016": ("100.0002", "100.0000"),
           "2020": ("100.0003", "100.0000"),
           "2024": ("100.0000", "100.0001")})

    # 殘差超過捨入上界：宣告與來源一致，只有上界那條能擋
    rows = [list(r) for r in sources["2024"]["elretks"]]
    rows[0][P.R_STAGE2] = str(Decimal(rows[0][P.R_STAGE2]) + Decimal("0.4999"))
    total = sum(Decimal(r[P.R_STAGE2]) for r in rows)
    old_sum = P.EXPECTED_RATE_SUMS["2024"]["stage2"]
    P.EXPECTED_RATE_SUMS["2024"]["stage2"] = str(total)
    try:
        check_raises_msg("殘差超過捨入上界即中止",
                         lambda: P.check_seat_allocation("2024", rows),
                         "超過捨入上界")
    finally:
        P.EXPECTED_RATE_SUMS["2024"]["stage2"] = old_sum


@reports
def test_shares_and_denominator() -> None:
    """p／q 的計算與分母核對。"""
    print("\n[整合] 原住民佔比與分母")
    got = pipeline("2024")
    if got is None:
        skipped.append("test_shares_and_denominator")
        print("  SKIP  找不到原始壓縮檔")
        return
    src, shares, gaps, ind_total = got
    check("2024 原住民選舉人總數", ind_total,
          P.EXPECTED_INDIGENOUS_ELECTORS["2024"])

    with zipfile.ZipFile(P.ZIP_PATH) as zf:
        names = zip_names(zf)
        ind, total = P.indigenous_station_totals(zf, names, "2024")
        pl = {P.unit_key(r) for r in src["elprof"] if r[5].strip("0")}

        # ⚠️ 我探索階段就是拿交集後的 422,774 當分母
        subset = {k: v for k, v in ind.items() if k in pl}
        check_raises_msg("只算交集當分母即中止",
                         lambda: P.indigenous_shares(
                             "2024", src["elprof"], subset, total),
                         "≠ 檔別合計")
        old = P.EXPECTED_INDIGENOUS_ELECTORS["2024"]
        P.EXPECTED_INDIGENOUS_ELECTORS["2024"] = 422_774
        try:
            check_raises_msg("原住民選舉人總數宣告改錯即中止",
                             lambda: P.indigenous_shares(
                                 "2024", src["elprof"], ind, total),
                             "宣告為 422,774")
        finally:
            P.EXPECTED_INDIGENOUS_ELECTORS["2024"] = old

        old_join = P.EXPECTED_JOIN["2024"]
        P.EXPECTED_JOIN["2024"] = (1, 1, 1)
        try:
            check_raises_msg("可接三整數改錯即中止",
                             lambda: P.indigenous_shares(
                                 "2024", src["elprof"], ind, total),
                             "宣告為 (1, 1, 1)")
        finally:
            P.EXPECTED_JOIN["2024"] = old_join

    # 三類缺席原因
    reasons = {v["缺席原因"] for v in shares.values()}
    check("2024 的缺席原因取值", sorted(reasons), ["", "所號兩檔對不上"])
    # p 與 q 都有值且落在 [0,1]
    bad = [k for k, v in shares.items() if v["p"] != ""
           and not (Decimal(0) <= Decimal(v["p"]) <= Decimal(1))]
    check("p 皆落在 [0,1]", bad, [])


@reports
def test_2020_special_stations() -> None:
    """2020 嘉義市的特設投票所——「缺席」是 p=0 不是未知。

    ⚠️ 第一版把這 189 所算成缺口，可接率因此少報成 98.90%。
       它們是量出來的零，不是未知。
    """
    print("\n[整合] 2020 嘉義市的特設所")
    got = pipeline("2020")
    if got is None:
        skipped.append("test_2020_special_stations")
        print("  SKIP  找不到原始壓縮檔")
        return
    src, shares, gaps, ind_total = got
    zero = [k for k, v in shares.items()
            if v["缺席原因"] == "該所無原住民選民"]
    check("2020 判為 p=0 的所數", len(zero), 189)
    check("全部在同一個縣市", {k[:2] for k in zero}, {("10", "020")})
    check("2020 沒有任何未知",
          [k for k, v in shares.items() if v["原住民可接"] == "false"], [])
    # 那兩個特設所的 p 恰為 1
    ones = [k for k, v in shares.items()
            if v["p"] not in ("", "0") and Decimal(v["p"]) == 1
            and k[:2] == ("10", "020")]
    check("嘉義市有兩個 p=1.0000 的特設所", len(ones), 2)
    check("特設所的村里碼為 0999", {k[3] for k in ones}, {"0999"})


@reports
def test_regression() -> None:
    """五屆的實際數字釘死。改動 parser 後這些若變了，必須是刻意的。"""
    print("\n[迴歸] 五屆的實際輸出")
    if not P.ZIP_PATH.exists():
        skipped.append("test_regression")
        print("  SKIP  找不到原始壓縮檔")
        return
    per_term = {}
    for year in P.TERMS:
        src, shares, gaps, ind_total = pipeline(year)
        usable = sum(1 for v in shares.values() if v["原住民可接"] == "true")
        per_term[year] = (len(shares), usable, ind_total)
    check("逐屆（投開票所, 可用, 原住民選舉人）", per_term,
          {"2008": (14377, 14377, 323072),
           "2012": (14806, 14806, 354946),
           "2016": (15582, 15582, 387105),
           "2020": (17226, 17226, 414948),
           "2024": (17795, 17685, 438200)})

    # 2024 的三個門檻
    src, shares, _, _ = pipeline("2024")
    rows = P.stratum_bounds("2024", src["elprof"], src["elctks"], shares,
                            party_of_number(src))
    by_threshold = {}
    for r in rows:
        by_threshold.setdefault(r["門檻"], (r["所數"], r["涵蓋原住民選舉人"]))
    check("2024 三個門檻的（所數, 涵蓋選舉人）", by_threshold,
          {"0.95": (90, 48091), "0.90": (172, 90837), "0.80": (237, 124365)})

    # ⚠️ 這三列是 spec 範例表的值，逐格釘死
    top = {r["政黨名稱"]: r for r in rows if r["門檻"] == "0.95"}
    for name, obs, lo, hi in (
        ("中國國民黨", "0.6810173127", "0.6713134260", "0.7017347845"),
        ("台灣民眾黨", "0.1408610388", "0.1147248644", "0.1451462229"),
        ("民主進步黨", "0.1209131301", "0.0941701132", "0.1245914718"),
    ):
        r = top[name]
        check(f"2024 ≥95% {name} 的觀察與界限",
              (r["觀察_得票率"], r["下界_原住民得票率"], r["上界_原住民得票率"]),
              (obs, lo, hi))
    check("2024 ≥95% 層的所數與有效票",
          (top["中國國民黨"]["所數"], top["中國國民黨"]["有效政黨票"]),
          (90, 32635))


@reports
def test_existing_outputs_untouched() -> None:
    """既有六張長表不得被這支腳本改動。"""
    print("\n[迴歸] 既有輸出未被動")
    existing = [
        "cec-local-election-summary-long.csv.gz",
        "cec-local-election-candidates-long.csv",
        "cec-local-election-votes-long.csv.gz",
        "cec-legislative-election-summary-long.csv.gz",
        "cec-legislative-election-candidates-long.csv",
        "cec-legislative-election-votes-long.csv.gz",
    ]
    missing = [n for n in existing if not (OUT / n).exists()]
    check("六張既有長表都在", missing, [])
    check("本腳本的輸出不與既有檔名衝突",
          [n for n in existing if n.startswith("cec-party-list")], [])


def main() -> int:
    for fn in (test_bounds_formula, test_bounds_guard, test_declarations,
               test_personal_data_excluded, test_manifest,
               test_source_guards, test_cross_file_guards,
               test_party_and_seats, test_shares_and_denominator,
               test_2020_special_stations, test_regression,
               test_existing_outputs_untouched):
        try:
            fn()
        except AssertionError:
            pass
    print()
    if skipped:
        print(f"跳過 {len(skipped)} 項：{skipped}")
    if failures:
        print(f"★ {len(failures)} 項失敗：{failures}")
        return 1
    print("全部通過")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
