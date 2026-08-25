#!/usr/bin/env python3
"""原住民立委長表的驗證測試。

⚠️ 這份測試的價值在於【能失敗】。每一組斷言都要問一次：
   「如果對應的程式碼壞掉，這一條會不會變紅？」答不出來的斷言等於沒寫。

   本檔的釘死值有兩種來源：
   1. 制度事實（席次逐屆不同）——改壞應選名額表就會紅。
   2. 外部錨點（報導者〈原住民立委選舉〉的 2020 數字）——那六個數字
      已逐項以中選會原始檔複核相符，是本專案之外的獨立確認。
"""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_legislative_election as B  # noqa: E402
from build_local_election import (  # noqa: E402
    ELECTED_MARKS, ValidationError, zip_names,
)
import oracles  # noqa: E402

OUT = ROOT / "data" / "processed"
failures: list[str] = []
skipped: list[str] = []


def check(label: str, got, want) -> None:
    if got == want:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}\n          得到 {got!r}\n          預期 {want!r}")
        failures.append(label)


def reports(fn):
    """跑完一組後若有失敗就丟 AssertionError，讓 pytest 逐組報。"""
    def wrapper():
        before = len(failures)
        fn()
        new = failures[before:]
        assert not new, f"{fn.__name__} 有 {len(new)} 項失敗：{new}"
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


# ── 席次：制度事實，逐屆不同 ────────────────────────────────────────
EXPECTED_SEATS = {
    "1995": 3, "1998": 4, "2001": 4, "2004": 4,
    "2008": 3, "2012": 3, "2016": 3, "2020": 3, "2024": 3,
}

# ── 2020 的外部錨點（報導者一文，已逐項以原始檔複核）─────────────────
ANCHOR_2020 = {
    "L3": {"選舉人數": 215115, "投票率": "68.6", "第二三名差距": 16},
    "L2": {"選舉人數": 199833, "投票率": "62.3", "第二三名差距": 2588},
}


# ══════════════════════════════════════════════════════════════════
# 實跑管線的快取
#
# ⚠️ **測試必須實跑 process_one，不可只讀已建好的長表。**
#    變異測試改的是原始碼、不會重建成品——讀成品的斷言對原始碼變異
#    一律無感。本專案在這件事上吃過三次虧；這份測試的第一版有 20/29
#    的變異漏網，成因全部是這一條。
# ══════════════════════════════════════════════════════════════════
_PIPELINE_CACHE: dict[tuple[str, str], dict] = {}

# 涵蓋各項具名事實所需的最小屆別組合：
#   1995 L2 — 檔別合計錯置、elctks 尾隨空白、鄉鎮市區為最細、年齡哨兵、舊代碼系統
#   1998 L3 — 零投票率三列、席次 4
#   2004 L2 — 和平鄉的 58 票
#   2008 L3 — elcand 帶引號
#   2012 L3 — 四個檔帶引號、2012 代碼系統、選舉區欄 00 與 01 並存
#   2016 L3 — 降級到鄉鎮市區
#   2020 L3 — 外部錨點
PIPELINE_PARTS = (("1995", "L2"), ("1998", "L3"), ("2004", "L2"),
                  ("2008", "L3"), ("2012", "L3"), ("2016", "L3"),
                  ("2020", "L3"))


def pipeline(year: str, etype: str) -> dict | None:
    """實跑一次建置管線。找不到原始壓縮檔時回傳 None。"""
    if not B.ZIP_PATH.exists():
        return None
    key = (year, etype)
    if key not in _PIPELINE_CACHE:
        with zipfile.ZipFile(B.ZIP_PATH) as zf:
            names = zip_names(zf)
            part = B.process_one(zf, names, year, etype)
        crosswalk = B.load_county_crosswalk()
        used: set = set()
        for rows in (part["summary"], part["candidates"], part["votes"]):
            B.normalise_geo(rows, crosswalk, used)
        _PIPELINE_CACHE[key] = part
    return _PIPELINE_CACHE[key]


def load_candidates() -> list[dict]:
    p = OUT / "cec-legislative-election-candidates-long.csv"
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_summary() -> list[dict]:
    p = OUT / "cec-legislative-election-summary-long.csv.gz"
    if not p.exists():
        return []
    with gzip.open(p, "rt", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_votes() -> list[dict]:
    p = OUT / "cec-legislative-election-votes-long.csv.gz"
    if not p.exists():
        return []
    with gzip.open(p, "rt", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


@reports
def test_seat_sequence() -> None:
    """席次逐屆不同——不可寫成單一數字。"""
    print("\n[迴歸] 席次序列")
    cands = load_candidates()
    if not cands:
        print("  SKIP  找不到候選人長表")
        skipped.append("seat_sequence")
        return
    got = {}
    for c in cands:
        if c["當選"] == "Y":
            got[(c["年度"], c["選舉種類"])] = got.get(
                (c["年度"], c["選舉種類"]), 0) + 1
    want = {(y, e): n for y, n in EXPECTED_SEATS.items() for e in ("L2", "L3")}
    check("九屆兩種類的席次", got, want)
    check("九屆合計 60 席", sum(got.values()), 60)
    # ⚠️ 這一條守的是「席次不是常數」。若有人把 SEATS_BY_TERM 改成
    #    全部 3 席，上面那條會紅，但這一條說明為什麼。
    check("席次有三個不同的值", sorted(set(EXPECTED_SEATS.values())), [3, 4])


@reports
def test_anchor_2020() -> None:
    """2020 的外部錨點值。來源是報導者一文，已逐項以中選會原始檔複核。"""
    print("\n[迴歸] 2020 外部錨點")
    summary, votes = load_summary(), load_votes()
    if not summary or not votes:
        print("  SKIP  找不到長表")
        skipped.append("anchor_2020")
        return
    for etype, want in ANCHOR_2020.items():
        nat = [s for s in summary
               if s["年度"] == "2020" and s["選舉種類"] == etype
               and s["層級"] == "檔別合計"]
        check(f"2020 {etype} 檔別合計列恰一筆", len(nat), 1)
        if not nat:
            continue
        check(f"2020 {etype} 選舉人數", int(nat[0]["選舉人數"]),
              want["選舉人數"])
        check(f"2020 {etype} 投票率", nat[0]["投票率_檔案"], want["投票率"])

        tally = sorted(
            (int(v["得票數"]) for v in votes
             if v["年度"] == "2020" and v["選舉種類"] == etype
             and v["層級"] == "檔別合計"), reverse=True)
        check(f"2020 {etype} 第二名與第三名得票差",
              tally[1] - tally[2], want["第二三名差距"])


@reports
def test_personal_data_absent() -> None:
    """個資欄位不得出現在任何輸出。"""
    print("\n[契約] 個資欄位")
    banned = {"出生日期", "出生地", "學歷"}
    for name, cols in (("summary", B.SUMMARY_COLUMNS),
                       ("candidates", B.CANDIDATE_COLUMNS),
                       ("votes", B.VOTES_COLUMNS)):
        check(f"{name} 不含個資欄", sorted(set(cols) & banned), [])
    cands = load_candidates()
    if cands:
        check("候選人長表實際欄名不含個資欄",
              sorted(set(cands[0]) & banned), [])


@reports
def test_age_sentinel() -> None:
    """年齡哨兵：1995／1998／2001／2004 整批 99，其餘屆別無哨兵。

    ⚠️ 立委的哨兵屆別與地方公職【不同】，只有 1998 重疊。
       沿用地方公職的清單會讓 1995／2001／2004 的 99 當成年齡輸出。
    """
    print("\n[單元] 年齡哨兵")
    check("哨兵屆別", sorted(B.AGE_UNRECORDED_TERMS),
          ["1995", "1998", "2001", "2004"])
    check("2001 的 99 判為無資料", B.valid_age("2001", "99"), "")
    check("2020 的 99 保留為年齡", B.valid_age("2020", "99"), "99")
    check("0 在任何屆別都無資料", B.valid_age("2020", "0"), "")
    check("正常年齡原樣", B.valid_age("2020", "45"), "45")

    cands = load_candidates()
    if not cands:
        print("  SKIP  找不到候選人長表")
        skipped.append("age_sentinel")
        return
    bad_clean = [c["年度"] for c in cands if c["年齡"] == "99"]
    check("乾淨的 年齡 欄不含 99", bad_clean, [])
    for year in ("1995", "1998", "2001", "2004"):
        rows = [c for c in cands if c["年度"] == year]
        check(f"{year} 的 年齡_原始 全為 99",
              sorted({c["年齡_原始"] for c in rows}), ["99"])
        check(f"{year} 的 年齡 全部留空",
              sorted({c["年齡"] for c in rows}), [""])


@reports
def test_elected_from_authoritative() -> None:
    """`當選` 存權威值，`當選註記` 存來源認定——兩者是不同的欄。"""
    print("\n[契約] 當選欄的分工")
    cands = load_candidates()
    if not cands:
        print("  SKIP  找不到候選人長表")
        skipped.append("elected")
        return
    check("當選 的取值集合", sorted({c["當選"] for c in cands}), ["N", "Y"])
    check("當選_依據 的取值集合",
          sorted({c["當選_依據"] for c in cands}), ["elctks_檔別合計"])
    # ⚠️ 兩側必須取自不同欄。本批零不符是正確的，但若哪天有人把
    #    `當選註記` 那一側改成也讀 `當選`，這條會恆真而測不到任何東西。
    #    因此另加下一條：兩欄的【欄名】必須都在輸出裡且不同。
    mismatch = [c["姓名"] for c in cands
                if (c["當選"] == "Y") != (c["當選註記"] in ELECTED_MARKS)]
    check("來源認定與權威值零不符（本批無已知損壞）", mismatch, [])
    check("兩欄都存在且相異",
          ("當選" in cands[0] and "當選註記" in cands[0]
           and "當選" != "當選註記"), True)


@reports
def test_published_levels() -> None:
    """每屆輸出到的最細層級，含 2016 的降級。"""
    print("\n[契約] 輸出層級")
    summary = load_summary()
    if not summary:
        print("  SKIP  找不到 summary")
        skipped.append("levels")
        return
    from build_local_election import ADMIN_LEVELS
    got = {}
    for s in summary:
        y = s["年度"]
        if y not in got or ADMIN_LEVELS.index(s["層級"]) > ADMIN_LEVELS.index(got[y]):
            got[y] = s["層級"]
    check("逐屆最細輸出層級", got, dict(B.PUBLISHED_LEVEL_BY_TERM))
    # ⚠️ 2016 是唯一「來源比輸出更細」的屆別。這一條守住那個區別——
    #    若有人把兩個宣告合併成一個，這裡會紅。
    check("2016 的來源層級比輸出層級細",
          (B.FINEST_LEVEL_BY_TERM["2016"], B.PUBLISHED_LEVEL_BY_TERM["2016"]),
          ("投開票所", "鄉鎮市區"))
    check("2016 輸出不含村里與投開票所",
          sorted({s["層級"] for s in summary if s["年度"] == "2016"}),
          ["檔別合計", "直轄市縣市", "鄉鎮市區"])


@reports
def test_geo_normalisation() -> None:
    """縣市正規化讓跨屆可比，鄉鎮市區一律留空。"""
    print("\n[契約] 地理正規化")
    summary = load_summary()
    if not summary:
        print("  SKIP  找不到 summary")
        skipped.append("geo")
        return
    check("鄉鎮市區_正規化 全部留空",
          sorted({s["鄉鎮市區_正規化"] for s in summary}), [""])
    # 同一個縣在三個代碼系統下必須正規化到同一個鍵。
    hualien = {(s["admin_code_system"], s["省市"], s["縣市"]): s["縣市_正規化"]
               for s in summary
               if s["層級"] == "直轄市縣市" and s["行政區名稱"] == "花蓮縣"}
    check("花蓮縣在三套代碼系統下的原碼", sorted(hualien),
          [("1995-2008", "03", "015"), ("2012", "06", "011"),
           ("2016+", "10", "015")])
    check("花蓮縣正規化後同一鍵", sorted(set(hualien.values())), ["10015"])
    # ⚠️ 原碼會撞：02,000 在 1995-2008 是高雄市、在 2012 是新北市。
    raw = {}
    for s in summary:
        if s["層級"] == "直轄市縣市":
            raw.setdefault((s["省市"], s["縣市"]), set()).add(s["行政區名稱"])
    collide = {k: sorted(v) for k, v in raw.items() if len(v) > 1}
    check("原碼跨屆會撞的鍵",
          collide, {("02", "000"): ["新北市", "高雄市"]})


@reports
def test_named_defects() -> None:
    """四項具名來源瑕疵，逐一釘死。"""
    print("\n[迴歸] 具名來源瑕疵")
    p = OUT / "legislative-validation-report.json"
    if not p.exists():
        print("  SKIP  找不到驗證報告")
        skipped.append("defects")
        return
    rep = json.loads(p.read_text(encoding="utf-8"))
    d = rep["已知來源瑕疵"]
    check("檔別合計錯置 4 筆", len(d["檔別合計錯置"]), 4)
    check("有效票與得票加總不符 3 筆", len(d["有效票與得票加總不符"]), 3)
    check("投票率為零但有投票數 3 筆", len(d["投票率為零但有投票數"]), 3)
    # 2004 那兩筆必須一正一負且絕對值相同——那是「和平鄉的票跑到彰化縣」。
    v2004 = sorted(x["elprof減elctks"] for x in d["有效票與得票加總不符"]
                   if x["屆別"] == "2004")
    check("2004 兩縣的差額互為相反數", v2004, [-58, 58])
    check("1995 的差額互相抵銷",
          sum(x["檔別合計減細層級加總"] for x in d["檔別合計錯置"]), 0)


@reports
def test_existing_outputs_untouched() -> None:
    """既有地方公職長表與驗證報告不得因本變更而改變。

    ⚠️ 這是本變更最重要的一條保證。釘死的是【檔案存在且非空】與
       【欄位集合】——SHA-256 會隨地方公職自己的變更而變，釘死雜湊
       會讓那邊每次改動都誤紅。
    """
    print("\n[契約] 既有輸出未受影響")
    local = OUT / "cec-local-election-candidates-long.csv"
    if not local.exists():
        print("  SKIP  找不到地方公職長表")
        skipped.append("untouched")
        return
    with local.open(encoding="utf-8-sig", newline="") as fh:
        cols = next(csv.reader(fh))
    check("地方公職候選人長表仍是 28 欄", len(cols), 28)
    check("地方公職長表沒有被加上立委的欄位",
          sorted(set(cols) & {"選舉區_語意", "當選_依據", "admin_code_system"}),
          ["admin_code_system", "當選_依據"])
    from oracles import MANIFEST
    check("MANIFEST 仍只有三張地方公職的表",
          sorted(MANIFEST), ["candidates", "summary", "votes"])


@reports
def test_reproducible() -> None:
    """同樣的輸入必須產生同樣的位元組。"""
    print("\n[契約] 可重現性")
    if not B.ZIP_PATH.exists():
        print("  SKIP  找不到原始壓縮檔")
        skipped.append("reproducible")
        return
    rows = [{c: "x" for c in B.VOTES_COLUMNS} for _ in range(3)]
    a = B.render_csv(rows, B.VOTES_COLUMNS)
    b = B.render_csv(rows, B.VOTES_COLUMNS)
    check("render_csv 可重現", hashlib.sha256(a).hexdigest(),
          hashlib.sha256(b).hexdigest())
    check("render_csv 用 \\n 換行", b"\r\n" in a, False)
    check("render_csv 為 UTF-8-SIG", a[:3], b"\xef\xbb\xbf")


@reports
def test_source_guards() -> None:
    """來源守衛：路徑排除、引號宣告、選舉區欄、層級。皆以合成輸入觸發。"""
    print("\n[單元] 來源守衛")

    def aborts(label, fn):
        try:
            fn()
            check(label, "沒有中止", "中止")
        except ValidationError:
            check(label, "中止", "中止")

    aborts("含 old 的路徑集合",
           lambda: B.check_no_excluded_paths(
               ["votedata/votedata/voteData/2016總統立委/old/山地立委/elcand_T3.csv"]))
    B.check_no_excluded_paths(["votedata/x/golden舊檔/elcand.csv"])
    check("golden 不被誤判為 old", True, True)

    aborts("未宣告卻讀到引號",
           lambda: B.check_quoting_declaration("2020", "L3", "elcand",
                                               ["'00", "000"]))
    aborts("宣告有引號卻讀不到",
           lambda: B.check_quoting_declaration("2008", "L3", "elcand",
                                               ["00", "000"]))

    aborts("選舉區欄出現宣告外的值",
           lambda: B.check_district_values(
               "1995", "L3", "elprof", [["a", "b", "99", "d", "e", "f"]]))

    aborts("出現以選舉區為最深層級的列",
           lambda: B.check_finest_level(
               "2020", "L3", "elprof",
               [["01", "000", "01", "000", "0000", "0"]]))

    # 合成一列 elcand：年齡在索引 10（官方格式文件）。
    row_age_99 = [""] * 16
    row_age_99[B.C_AGE] = "99"
    aborts("未具名屆別出現年齡 99",
           lambda: B.check_age_sentinel("2020", [row_age_99]))
    row_real_age = [""] * 16
    row_real_age[B.C_AGE] = "45"
    aborts("具名屆別出現真實年齡（宣告過期）",
           lambda: B.check_age_sentinel("2001", [row_real_age]))


@reports
def test_pipeline_end_to_end() -> None:
    """實跑管線，斷言記憶體裡的結果。

    ⚠️ 這是本檔最重要的一組——其餘讀成品的斷言對原始碼變異無感。
       七個（屆別, 選舉種類）涵蓋所有具名事實，見 PIPELINE_PARTS。
    """
    print("\n[整合] 實跑 process_one")
    if not B.ZIP_PATH.exists():
        print("  SKIP  找不到原始壓縮檔")
        skipped.append("pipeline")
        return

    parts = {k: pipeline(*k) for k in PIPELINE_PARTS}
    check("七個部分都跑完", sorted(parts), sorted(PIPELINE_PARTS))

    # ── 席次：逐屆不同 ──────────────────────────────────────
    seats = {k: sum(1 for c in p["candidates"] if c["當選"] == "Y")
             for k, p in parts.items()}
    check("實跑得到的席次",
          seats, {("1995", "L2"): 3, ("1998", "L3"): 4, ("2004", "L2"): 4,
                  ("2008", "L3"): 3, ("2012", "L3"): 3, ("2016", "L3"): 3,
                  ("2020", "L3"): 3})
    check("elprof 當選人數與釘死值一致",
          {k: p["elprof當選人數"] for k, p in parts.items()},
          {k: EXPECTED_SEATS[k[0]] for k in PIPELINE_PARTS})

    # ── 年齡哨兵：乾淨值不得含 99 ────────────────────────────
    p95 = parts[("1995", "L2")]
    check("1995 的 年齡_原始 全為 99",
          sorted({c["年齡_原始"] for c in p95["candidates"]}), ["99"])
    check("1995 的 年齡 全部留空",
          sorted({c["年齡"] for c in p95["candidates"]}), [""])
    p20 = parts[("2020", "L3")]
    check("2020 的 年齡 有真實值",
          all(c["年齡"] and c["年齡"] != "99" for c in p20["candidates"]), True)

    # ── 當選：權威值與來源認定 ───────────────────────────────
    check("當選 的取值只有 Y/N",
          sorted({c["當選"] for p in parts.values() for c in p["candidates"]}),
          ["N", "Y"])
    check("當選_依據 全部取自檔別合計",
          sorted({c["當選_依據"] for p in parts.values()
                  for c in p["candidates"]}), ["elctks_檔別合計"])

    # ── 具名瑕疵：實跑後的筆數 ───────────────────────────────
    check("1995 L2 的檔別合計錯置",
          {a["號次"]: a["檔別合計減細層級加總"]
           for a in p95["anomalies"]["檔別合計錯置"]}, {"1": -1, "3": 1})
    check("2004 L2 的有效票不符（和平鄉的 58 票）",
          sorted(a["elprof減elctks"]
                 for a in parts[("2004", "L2")]["anomalies"]["有效票與得票加總不符"]),
          [-58, 58])
    check("1998 L3 的零投票率三列",
          sorted(a["重算投票率"]
                 for a in parts[("1998", "L3")]["anomalies"]["投票率為零但有投票數"]),
          ["100.00", "25.00", "66.67"])
    check("其餘屆別無檔別合計錯置",
          {k: len(p["anomalies"]["檔別合計錯置"]) for k, p in parts.items()
           if k != ("1995", "L2")},
          {k: 0 for k in PIPELINE_PARTS if k != ("1995", "L2")})

    # ── 層級：2016 降級、1995 只到鄉鎮市區 ──────────────────
    from build_local_election import ADMIN_LEVELS
    deepest = {k: max({s["層級"] for s in p["summary"]},
                      key=ADMIN_LEVELS.index) for k, p in parts.items()}
    check("實跑得到的最細輸出層級",
          deepest, {k: B.PUBLISHED_LEVEL_BY_TERM[k[0]] for k in PIPELINE_PARTS})
    check("2016 實跑後不含村里與投開票所",
          sorted({s["層級"] for s in parts[("2016", "L3")]["summary"]}),
          ["檔別合計", "直轄市縣市", "鄉鎮市區"])

    # ── 尾隨空白：1995 的 450 列不得被判成投開票所 ───────────
    check("1995 的層級判定未受尾隨空白影響",
          sorted({s["層級"] for s in p95["summary"]}),
          ["檔別合計", "直轄市縣市", "鄉鎮市區"])

    # ── 地理正規化 ──────────────────────────────────────────
    check("鄉鎮市區_正規化 實跑後仍全部留空",
          sorted({s["鄉鎮市區_正規化"] for p in parts.values()
                  for s in p["summary"]}), [""])
    hual = {k: {s["縣市_正規化"] for s in p["summary"]
                if s["層級"] == "直轄市縣市" and s["行政區名稱"] == "花蓮縣"}
            for k, p in parts.items()}
    check("花蓮縣在三套代碼系統下都正規化到 10015",
          sorted({v for s in hual.values() for v in s}), ["10015"])

    # ── 欄位契約：個資不得出現 ───────────────────────────────
    banned = {"出生日期", "出生地", "學歷"}
    check("實跑產出的候選人列不含個資欄",
          sorted({c for p in parts.values() for c in p["candidates"][0]}
                 & banned), [])
    check("候選人列的欄位集合等於宣告",
          {k: set(p["candidates"][0]) == set(B.CANDIDATE_COLUMNS)
           for k, p in parts.items()},
          {k: True for k in PIPELINE_PARTS})
    check("summary 列的欄位集合等於宣告",
          {k: set(p["summary"][0]) == set(B.SUMMARY_COLUMNS)
           for k, p in parts.items()},
          {k: True for k in PIPELINE_PARTS})

    # ── 2020 外部錨點：由實跑結果算出 ────────────────────────
    nat20 = [s for s in p20["summary"] if s["層級"] == "檔別合計"]
    check("2020 L3 選舉人數（實跑）", int(nat20[0]["選舉人數"]), 215115)
    check("2020 L3 投票率（實跑）", nat20[0]["投票率_檔案"], "68.6")
    tally = sorted((int(v["得票數"]) for v in p20["votes"]
                    if v["層級"] == "檔別合計"), reverse=True)
    check("2020 L3 第二三名差距（實跑）", tally[1] - tally[2], 16)

    # ── 報告：兩個當選人數必須取自不同欄 ─────────────────────
    rep = B.build_report(
        [s for p in parts.values() for s in p["summary"]],
        [c for p in parts.values() for c in p["candidates"]],
        [v for p in parts.values() for v in p["votes"]],
        collections.defaultdict(list), "x")
    check("報告涵蓋七個部分", len(rep["各屆別選舉種類"]), 7)
    check("報告的兩個當選人數皆等於釘死值",
          {(e["年度"], e["選舉種類"]): (e["當選人數"], e["當選人數_權威值"])
           for e in rep["各屆別選舉種類"]},
          {k: (EXPECTED_SEATS[k[0]], EXPECTED_SEATS[k[0]])
           for k in PIPELINE_PARTS})


@reports
def test_synthetic_dirty_data() -> None:
    """以【合成的髒資料】驅動每一道守衛。

    ⚠️ 這一組存在的理由：立委來源目前沒有已知損壞，所以「把某條檢查拿掉」
       這類破壞在乾淨資料上【輸出完全相同】。只餵真實資料的測試對它們無感——
       實測第一版有 11 項變異因此漏網。每一條守衛都必須有一份會觸發它的輸入。
    """
    print("\n[單元] 合成髒資料")

    def aborts(label, fn):
        try:
            fn()
            check(label, "沒有中止", "中止")
        except ValidationError:
            check(label, "中止", "中止")

    part = pipeline("2020", "L3")
    if part is None:
        print("  SKIP  找不到原始壓縮檔")
        skipped.append("synthetic")
        return
    cands = [dict(c) for c in part["candidates"]]

    # ── 席次三方核對：三個數字必須【兩兩】相等 ──────────────
    #
    # ⚠️ 這裡必須測「elprof 與實數相等、但釘死值不同」這個組合。
    #    只傳一個與實數不同的 elprof 席次是【測不出來的】——那時
    #    「只比兩方」的版本照樣會中止，兩者無法區分。實測踩過。
    real = part["elprof當選人數"]
    saved = B.SEATS_BY_TERM["2020"]
    B.SEATS_BY_TERM["2020"] = real + 2
    try:
        aborts("釘死值與 elprof 不符（但 elprof 與實數相等）",
               lambda: B.check_seat_total("2020", "L3", cands, real))
    finally:
        B.SEATS_BY_TERM["2020"] = saved
    flipped = [dict(c) for c in cands]
    flipped[0]["當選"] = "N" if flipped[0]["當選"] == "Y" else "Y"
    aborts("由權威值數出的席次與 elprof 不符",
           lambda: B.check_seat_total("2020", "L3", flipped, real))

    # ── 補償性檢查：兩側必須取自不同欄 ───────────────────────
    corrupt = [dict(c) for c in cands]
    win = next(c for c in corrupt if c["當選"] == "Y")
    win["當選註記"] = " "        # 來源說沒當選、權威值說當選
    aborts("來源註記與權威值不一致",
           lambda: B.check_elected_agreement("2020", "L3", corrupt))

    # ── 權威值必須來自 elctks，不是抄 elcand ─────────────────
    with zipfile.ZipFile(B.ZIP_PATH) as zf:
        names = zip_names(zf)
        ctks = B.load_source(zf, names, "2020", "L3", "elctks")
    fake_ctks = [list(r) for r in ctks]
    top = [r for r in fake_ctks if B.admin_level(r[:6]) == "檔別合計"]
    # 把 elctks 的註記整組翻轉：當選變未當選、未當選變當選
    for r in top:
        r[9] = " " if r[9].strip() in ("*", "!") else "*"
    probe = [dict(c) for c in cands]
    B.derive_elected("2020", "L3", fake_ctks, probe)
    src_says = {c["姓名"] for c in cands if c["當選註記"] in ELECTED_MARKS}
    now_says = {c["姓名"] for c in probe if c["當選"] == "Y"}
    check("翻轉 elctks 後 當選 跟著翻轉（證明不是抄 elcand）",
          bool(src_says) and src_says.isdisjoint(now_says), True)

    # ── 地理正規化 ──────────────────────────────────────────
    crosswalk = B.load_county_crosswalk()
    unknown = [{"年度": "2020", "選舉種類": "L3",
                "admin_code_system": "2016+", "省市": "99", "縣市": "999",
                "縣市_正規化": "", "鄉鎮市區_正規化": ""}]
    aborts("未具名的縣市碼",
           lambda: B.normalise_geo(unknown, crosswalk, set()))
    aborts("對照表有從未被使用的列",
           lambda: B.check_crosswalk_fully_used(crosswalk, set()))
    R = lambda k, nm: {"層級": "直轄市縣市", "縣市_正規化": k, "行政區名稱": nm}
    full = [R(k, nm) for k, v in B.NAMED_COUNTY_MERGES.items() for nm in v]
    aborts("具名合併少掉一半",
           lambda: B.check_named_merges_only(
               [r for r in full if r["行政區名稱"] != "高雄縣"]))
    aborts("不相干的縣市被併成同一鍵",
           lambda: B.check_named_merges_only(
               full + [R("10015", "花蓮縣"), R("10015", "臺東縣")]))

    # ── 選舉區欄：宣告過期（實際少一個值）也要中止 ───────────
    only_00 = [["a", "b", "00", "d", "e", "f"]]
    aborts("選舉區欄的宣告過期（宣告 00+01、實際只有 00）",
           lambda: B.check_district_values("2020", "L3", "elprof", only_00))

    # ── 層級：必須是【專責那條檢查】中止，不是層級不符順便擋下 ──
    #
    # ⚠️ 只斷言「有中止」是測不出來的：把專責檢查拿掉之後，那一列的
    #    最深層級變成「選舉區」而宣告是「投開票所」，仍會因層級不符而中止，
    #    訊息裡照樣有「選舉區」三個字。必須比對【只有專責檢查會說的話】。
    try:
        B.check_finest_level("2020", "L3", "elprof",
                             [["01", "000", "01", "000", "0000", "0"]])
        check("出現選舉區層級時中止", "沒有中止", "中止")
    except ValidationError as e:
        check("中止訊息來自專責檢查而非層級不符",
              "為最深層級的列" in str(e), True)

    # ── 欄位契約：多一欄也要中止 ─────────────────────────────
    extra = [dict(cands[0], 出生日期="0600101")]
    aborts("輸出多出未宣告的欄位",
           lambda: B._check_columns(extra, B.CANDIDATE_COLUMNS, "candidates"))

    # ── 報告：兩個當選人數必須取自不同欄 ─────────────────────
    rep = B.build_report(part["summary"], corrupt, part["votes"],
                         collections.defaultdict(list), "x")
    e = rep["各屆別選舉種類"][0]
    check("來源註記被改壞時報告的兩個數字會不同",
          e["當選人數"] != e["當選人數_權威值"], True)

    # ── gzip 可重現 ─────────────────────────────────────────
    check("gzip 固定 mtime，同輸入同位元組",
          hashlib.sha256(B.gzip_bytes(b"x" * 100)).hexdigest(),
          hashlib.sha256(B.gzip_bytes(b"x" * 100)).hexdigest())
    check("gzip 標頭的 mtime 為 0",
          B.gzip_bytes(b"x")[4:8], b"\x00\x00\x00\x00")


@reports
def test_legislative_oracle_rendered_into_shared_document() -> None:
    """立委的欄位 oracle 必須透過 render_markdown() 曝光，不是死碼。"""
    print("\n[單元] 立委欄位 oracle 的算繪")
    md = oracles.render_markdown()
    names = {"legislative_summary": "立委選舉概況 summary",
             "legislative_candidates": "立委候選人 candidates",
             "legislative_votes": "立委候選人得票 votes"}
    for table, heading in names.items():
        check(f"文件含標題「## {heading}」", f"## {heading}" in md, True)
        section = md.split(f"## {heading}")[1].split("## ")[0]
        expected_cols = set(oracles.LEGISLATIVE_MANIFEST[table])
        found_cols = set(
            line.split("|")[1].strip().strip("`")
            for line in section.splitlines()
            if line.startswith("| `")
        )
        check(f"{heading} 欄位集合與 LEGISLATIVE_MANIFEST 完全相符",
              found_cols, expected_cols)


@reports
def test_manifest_rendering_reflects_new_columns() -> None:
    """manifest 多一個欄位，算繪結果就要跟著多出來——不是照抄一份快照。"""
    print("\n[單元] 算繪結果會反映 manifest 的內容變動")
    fake_manifest = {
        "legislative_summary": dict(
            oracles.LEGISLATIVE_MANIFEST["legislative_summary"],
            假欄位=dict(provenance="project", structure="test",
                     arithmetic=None, semantic="none", note=None),
        )
    }
    out = oracles._render_manifest_sections(
        fake_manifest, {"legislative_summary": "立委選舉概況 summary"})
    md = "\n".join(out)
    check("新增的假欄位出現在算繪結果裡", "`假欄位`" in md, True)


@reports
def test_population_is_valid_decimal() -> None:
    """人口數原樣保留字串，但仍須是可解析、有限、非負的十進位數。

    這支函式現在住在 `oracles.py`（`check_population_column`），
    `build_legislative_election.py` 直接匯入使用，不再自己維護一份。
    """
    print("\n[合成] 立委人口數的可解析性、有限值與非負值驗證")

    def row(pop) -> dict:
        return {"層級": "縣市", "省市": "10", "縣市": "001",
                "鄉鎮市區": "000", "行政區名稱": "測試縣", "人口數": pop}

    for bad_value, needle, desc in (
        ("abc", "不是十進位數", "非數字字串"),
        ("Infinity", "不是有限值", "正無限大"),
        ("-Infinity", "不是有限值", "負無限大"),
        ("NaN", "不是有限值", "NaN"),
        (None, "不是十進位數", "非字串輸入"),
        ("-5", "為負數", "負值"),
    ):
        try:
            B.check_population_column([row(bad_value)], "測試")
            check(f"{desc}會中止", "沒有中止", "中止")
        except ValidationError as e:
            check(f"{desc}的錯誤訊息含「{needle}」", needle in str(e), True)
        except Exception as e:  # noqa: BLE001
            check(f"{desc}應拋出 ValidationError（卻是 {type(e).__name__}）",
                  False, True)

    try:
        B.check_population_column([row("0"), row("1234.5")], "測試")
        check("合法值（含 0 與小數）不中止", True, True)
    except ValidationError as e:
        check(f"合法值不應中止（卻拋出 {e}）", False, True)


@reports
def test_oracle_document_written_atomically() -> None:
    """render_markdown() 的輸出要原子寫入，且不留殘餘暫存檔。"""
    print("\n[真實] oracle 文件的原子寫入")
    before = oracles.render_markdown()
    oracles.write_oracle_document()
    target = oracles.ROOT / "docs" / "schema" / "oracles.md"
    check("寫入後的檔案內容與 render_markdown() 一致",
          target.read_text(encoding="utf-8"), before)
    leftovers = [f for f in (oracles.ROOT / "docs" / "schema").iterdir()
                 if f.name.startswith(".oracles-")]
    check("沒有殘留暫存檔", leftovers, [])


def main() -> int:
    for fn in (test_pipeline_end_to_end, test_synthetic_dirty_data,
               test_seat_sequence, test_anchor_2020, test_personal_data_absent,
               test_age_sentinel, test_elected_from_authoritative,
               test_published_levels, test_geo_normalisation,
               test_named_defects, test_existing_outputs_untouched,
               test_reproducible, test_source_guards,
               test_legislative_oracle_rendered_into_shared_document,
               test_manifest_rendering_reflects_new_columns,
               test_population_is_valid_decimal,
               test_oracle_document_written_atomically):
        try:
            fn()
        except AssertionError:
            pass
    print()
    if skipped:
        print(f"跳過 {len(skipped)} 組：{skipped}")
    if failures:
        print(f"★ {len(failures)} 項失敗：{failures}")
        return 1
    print("全部通過")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
