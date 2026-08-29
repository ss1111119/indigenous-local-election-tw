#!/usr/bin/env python3
"""build_local_election.py 的迴歸測試。

分兩類：

1. **單元測試**——直接測 parser 的判斷邏輯（層級判定、版面偵測、CSV 讀取），
   用手寫的最小案例，不需要原始壓縮檔。這些一定會跑。

2. **迴歸測試**——把 2014／2018／2022 三屆、六種選舉的實際輸出數字釘死。需要
   `data/processed/` 已存在（即已跑過建置）；不存在就跳過而非失敗，
   因為原始壓縮檔不入庫，clone 下來的人不一定有。

用法：
    python scripts/test_build_local_election.py
    pytest scripts/test_build_local_election.py     # 兩者皆可（已驗證 pytest 會失敗）
"""

from __future__ import annotations

import collections
import contextlib
import copy
import csv
import gzip
import io
import json
import pathlib
import sys
import tempfile
import tempfile
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from oracles import (  # noqa: E402
    ADMIN_CODE_SYSTEMS,
    CUSTOM_ELECTION_TYPES,
    ELECTION_TYPE_GRANULARITY,
    FILE_SCOPE,
    MANIFEST,
    SEMANTIC_LEVELS,
    OracleError,
    check_manifest,
    comparability_flags,
    is_main_sequence,
    office_type,
    POPULATION_APPLICABLE,
    POPULATION_APPLICABLE_LEVELS,
    POPULATION_NOT_APPLICABLE,
    population_applicability,
)
import build_local_election  # noqa: E402
# ⚠️ 這一行必須在【模組層級】，不可放進測試函式內。
#    `build_mountain_township_codes` 在 import 時會執行
#    `sys.path.insert(0, ROOT / "scripts")`，而在變異副本裡 ROOT 解析成 repo
#    根目錄——它把【真正的】scripts/ 插到 sys.path[0]。任何在那之後才做的
#    import 都會載到未變異的原始模組：變異測試報「偵測不到」，
#    而單獨跑同一個測試卻會失敗。2026-08-27 實測踩到三次。
import check_doc_numbers  # noqa: E402
import check_spec_traces  # noqa: E402
from build_local_election import (  # noqa: E402
    COLS,
    COUNTY_CROSSWALK_YEARS,
    DISTRICT_COLUMN_INCONSISTENT,
    TOWN_CODES_FILE_LOCAL,
    KEY_COLS,
    ELECTED_MARKS,
    ELECTION_TYPES,
    KNOWN_ELECTOR_ANOMALIES,
    KNOWN_TOWN_ASSIGNMENT_ANOMALIES,
    YEARS,
    WIN_MARKS,
    COUNTY_CROSSWALK_PATH,
    TOWN_CROSSWALK_PATH,
    TOWN_CROSSWALK_TARGETS,
    TOWN_NAME_ALIASES,
    EXPECTED_TOWN_COUNTS,
    AGE_UNRECORDED_EXTRA,
    MOUNTAIN_CODES_PATH,
    check_age_sentinel as _check_age_sentinel_imported,
    check_mountain_township_level,
    check_mountain_township_selection,
    load_mountain_township_codes,
    project_mountain_townships,
    ValidationError,
    load_town_crosswalk,
    regional_town_names,
    verify_town_crosswalk,
    check_age_sentinel,
    valid_age,
    ZIP_PATH,
    admin_level,
    area_key,
    cross_validate,
    derive_elected_authoritative,
    detect_layout,
    is_blank,
    load_county_crosswalk,
    process_one,
    resolve_county_code,
    read_csv,
    render_csv,
    zip_names,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed"

# 2009-2010／2014／2018／2022 四屆的實際數字。改動 parser 後這些若變了，必須是**刻意**的。
# 九屆（1994／1998／2002／2005／2006／2009-2010／2014／2018／2022）的實際輸出。
# 改動 parser 後這些若變了，必須是**刻意**的。
#
# ⚠️ 複合鍵一律用 `|` 分隔而【不是】連字號。本專案自訂的選舉種類代碼含連字號
#    （T-COMBO／T-PRV2／T-PRV3），屆別鍵也含連字號（2009-2010），
#    用連字號當分隔會讓 "1994-T-COMBO" 無法正確切開——原本的
#    `k.rsplit("-", 1)` 會切成 ("1994-T", "COMBO")。
# ⚠️ 這份數字由 scratch/gen_expected.py 從實際輸出產生，不手抄。
EXPECTED = {
    # 2026-08-27 D1-MT 納入後的增量：summary +187、candidates +476、votes +476。
    # 既有九種選舉種類的列經 SHA-256 驗證逐位元組未變，故差值必然恰為新增列數。
    "rows": {"summary": 268063, "candidates": 8294, "votes": 1751666},
    # ⚠️ 只有『鄉鎮市區』一項變動（5429→5616）。D1-MT 不產生任何彙總列，
    #    也不納入村里／投開票所層級——其餘五個層級一列都不該變。
    "levels_summary": {'檔別合計': 46, '直轄市縣市': 318, '選舉區': 997, '鄉鎮市區': 5616, '投開票所': 176811, '村里': 84275},
    "levels_votes": {'選舉區': 7081, '鄉鎮市區': 27067, '投開票所': 1183724, '村里': 533784, '檔別合計': 10},
    "candidates_by_year_type": {'2022|T2': 73, '2022|T3': 80, '2022|D2': 20, '2022|R3': 92, '2022|R2': 134, '2022|T1': 1524, '2018|T2': 84, '2018|T3': 98, '2018|D2': 19, '2018|R3': 98, '2018|R2': 131, '2018|T1': 1569, '2014|T2': 77, '2014|T3': 79, '2014|D2': 20, '2014|R3': 94, '2014|R2': 118, '2014|T1': 1444, '2009-2010|T2': 69, '2009-2010|T3': 79, '2009-2010|T1': 1433, '2006|T-COMBO': 6, '2005|T2': 65, '2005|T3': 66, '2002|T2': 67, '2002|T3': 85, '2002|T-COMBO': 12, '1998|T2': 69, '1998|T3': 80, '1998|T-COMBO': 10, '1994|T-PRV3': 5, '1994|T-PRV2': 5, '1994|T-COMBO': 13, '2022|D1-MT': 61, '2018|D1-MT': 71, '2014|D1-MT': 59, '2009-2010|D1-MT': 48, '2005|D1-MT': 80, '2002|D1-MT': 72, '1998|D1-MT': 85},
    # ⚠️ D1-MT 【沒有】檔別合計列（design 決策 8：衍生彙總只作驗證用的內部值，
    #    不寫進長表），故不可放進 "national"——那一段是加總「檔別合計」列的，
    #    對 D1-MT 會得到 0 並在算投票率時除以零。改由下面 MOUNTAIN_NATIONAL
    #    以鄉鎮市區列加總，數字仍然被釘死。
    "national": {
        "1994|T-COMBO": {"選舉人數": 5965, "投票數": 4115, "候選人數": 13, "當選人數": 2, "當選人數_權威值": 2, "婦女保障當選人數": 0, "投票率": 68.99},
        "1994|T-PRV2": {"選舉人數": 102156, "投票數": 54616, "候選人數": 5, "當選人數": 2, "當選人數_權威值": 2, "婦女保障當選人數": 0, "投票率": 53.46},
        "1994|T-PRV3": {"選舉人數": 116398, "投票數": 73619, "候選人數": 5, "當選人數": 2, "當選人數_權威值": 2, "婦女保障當選人數": 0, "投票率": 63.25},
        "1998|T-COMBO": {"選舉人數": 8146, "投票數": 6049, "候選人數": 10, "當選人數": 2, "當選人數_權威值": 2, "婦女保障當選人數": 0, "投票率": 74.26},
        "1998|T2": {"選舉人數": 106061, "投票數": 57609, "候選人數": 69, "當選人數": 23, "當選人數_權威值": 23, "婦女保障當選人數": 0, "投票率": 54.32},
        "1998|T3": {"選舉人數": 121727, "投票數": 86261, "候選人數": 80, "當選人數": 30, "當選人數_權威值": 30, "婦女保障當選人數": 0, "投票率": 70.86},
        "2002|T-COMBO": {"選舉人數": 11417, "投票數": 7263, "候選人數": 12, "當選人數": 2, "當選人數_權威值": 2, "婦女保障當選人數": 0, "投票率": 63.62},
        "2002|T2": {"選舉人數": 118940, "投票數": 60706, "候選人數": 67, "當選人數": 26, "當選人數_權威值": 26, "婦女保障當選人數": 0, "投票率": 51.04},
        "2002|T3": {"選舉人數": 133338, "投票數": 91031, "候選人數": 85, "當選人數": 30, "當選人數_權威值": 30, "婦女保障當選人數": 0, "投票率": 68.27},
        "2005|T2": {"選舉人數": 133766, "投票數": 72501, "候選人數": 65, "當選人數": 20, "當選人數_權威值": 27, "婦女保障當選人數": 0, "投票率": 54.2},
        "2005|T3": {"選舉人數": 147145, "投票數": 101690, "候選人數": 66, "當選人數": 18, "當選人數_權威值": 30, "婦女保障當選人數": 0, "投票率": 69.11},
        "2006|T-COMBO": {"選舉人數": 13758, "投票數": 7210, "候選人數": 6, "當選人數": 2, "當選人數_權威值": 2, "婦女保障當選人數": 0, "投票率": 52.41},
        "2009-2010|T1": {"選舉人數": 17335124, "投票數": 11883466, "候選人數": 1433, "當選人數": 843, "當選人數_權威值": 843, "婦女保障當選人數": 15, "投票率": 68.55},
        "2009-2010|T2": {"選舉人數": 160576, "投票數": 89731, "候選人數": 69, "當選人數": 31, "當選人數_權威值": 31, "婦女保障當選人數": 1, "投票率": 55.88},
        "2009-2010|T3": {"選舉人數": 170513, "投票數": 115572, "候選人數": 79, "當選人數": 32, "當選人數_權威值": 32, "婦女保障當選人數": 0, "投票率": 67.78},
        "2014|D2": {"選舉人數": 28850, "投票數": 23348, "候選人數": 20, "當選人數": 6, "當選人數_權威值": 6, "婦女保障當選人數": 0, "投票率": 80.93},
        "2014|R2": {"選舉人數": 88079, "投票數": 55604, "候選人數": 118, "當選人數": 68, "當選人數_權威值": 68, "婦女保障當選人數": 3, "投票率": 63.13},
        "2014|R3": {"選舉人數": 28842, "投票數": 23346, "候選人數": 94, "當選人數": 50, "當選人數_權威值": 50, "婦女保障當選人數": 0, "投票率": 80.94},
        "2014|T1": {"選舉人數": 18084841, "投票數": 12241793, "候選人數": 1444, "當選人數": 841, "當選人數_權威值": 841, "婦女保障當選人數": 9, "投票率": 67.69},
        "2014|T2": {"選舉人數": 179268, "投票數": 105688, "候選人數": 77, "當選人數": 33, "當選人數_權威值": 33, "婦女保障當選人數": 0, "投票率": 58.96},
        "2014|T3": {"選舉人數": 189042, "投票數": 137544, "候選人數": 79, "當選人數": 33, "當選人數_權威值": 33, "婦女保障當選人數": 0, "投票率": 72.76},
        "2018|D2": {"選舉人數": 30904, "投票數": 24862, "候選人數": 19, "當選人數": 6, "當選人數_權威值": 6, "婦女保障當選人數": 0, "投票率": 80.45},
        "2018|R2": {"選舉人數": 90281, "投票數": 58870, "候選人數": 131, "當選人數": 71, "當選人數_權威值": 71, "婦女保障當選人數": 3, "投票率": 65.21},
        "2018|R3": {"選舉人數": 30895, "投票數": 24856, "候選人數": 98, "當選人數": 50, "當選人數_權威值": 50, "婦女保障當選人數": 1, "投票率": 80.45},
        "2018|T1": {"選舉人數": 18656541, "投票數": 12499109, "候選人數": 1569, "當選人數": 843, "當選人數_權威值": 843, "婦女保障當選人數": 4, "投票率": 67.0},
        "2018|T2": {"選舉人數": 192460, "投票數": 115407, "候選人數": 84, "當選人數": 34, "當選人數_權威值": 34, "婦女保障當選人數": 0, "投票率": 59.96},
        "2018|T3": {"選舉人數": 204127, "投票數": 149675, "候選人數": 98, "當選人數": 35, "當選人數_權威值": 35, "婦女保障當選人數": 0, "投票率": 73.32},
        "2022|D2": {"選舉人數": 31807, "投票數": 23712, "候選人數": 20, "當選人數": 6, "當選人數_權威值": 6, "婦女保障當選人數": 0, "投票率": 74.55},
        "2022|R2": {"選舉人數": 91627, "投票數": 55614, "候選人數": 134, "當選人數": 72, "當選人數_權威值": 72, "婦女保障當選人數": 2, "投票率": 60.7},
        "2022|R3": {"選舉人數": 31803, "投票數": 23712, "候選人數": 92, "當選人數": 50, "當選人數_權威值": 50, "婦女保障當選人數": 0, "投票率": 74.56},
        "2022|T1": {"選舉人數": 18710006, "投票數": 11445404, "候選人數": 1524, "當選人數": 841, "當選人數_權威值": 841, "婦女保障當選人數": 4, "投票率": 61.17},
        "2022|T2": {"選舉人數": 202477, "投票數": 106573, "候選人數": 73, "當選人數": 34, "當選人數_權威值": 34, "婦女保障當選人數": 0, "投票率": 52.63},
        "2022|T3": {"選舉人數": 216262, "投票數": 144164, "候選人數": 80, "當選人數": 35, "當選人數_權威值": 35, "婦女保障當選人數": 0, "投票率": 66.66},
    },
    "layout_by_year": {'2022|男女合計': 71758, '2018|合計在前': 66767, '2014|合計在前': 66164, '2009-2010|合計在前': 61744, '2006|合計在前': 26, '2005|合計在前': 553, '2002|合計在前': 541, '1998|合計在前': 503, '1994|合計在前': 7},
    "marks": {'*': 4318, ' ': 3898, '!': 42, '-': 36},
    "women_quota": {'2022|R2': 2, '2022|T1': 4, '2018|R3': 1, '2018|R2': 3, '2018|T1': 4, '2014|R2': 3, '2014|T1': 9, '2009-2010|T2': 1, '2009-2010|T1': 15},
    "displaced": {'2018|R3': 1, '2018|R2': 3, '2018|T1': 4, '2014|R2': 3, '2014|T1': 9, '2009-2010|T2': 1, '2009-2010|T1': 15},
    "zero_rows": {"total": 60914, **{'2022|T2': 8932, '2022|T3': 8199, '2018|T2': 7848, '2018|T3': 7045, '2018|R2': 1, '2014|T2': 8140, '2014|T3': 7370, '2014|R2': 1, '2009-2010|T2': 6646, '2009-2010|T3': 6731, '2009-2010|T1': 1}},
    "known_turnout_anomalies": 7,
    "vote_sum_anomaly_kinds": {"elctks 比 elprof 細": 2,
                               "得票加總錯置": 2, "鄉鎮市區配錯選舉區": 3},
    "known_elected_mark_anomalies": 63,
    "known_elector_anomalies": 1,
    "turnout_rows_checked": 207146,
    "main_sequence": {'true': 267837, 'false': 39},
    "admin_code_systems": {'2014+': 204617, '2009': 61719, '2005+': 549, '2002': 511, '1998': 473, '1994': 7},
    "auth_basis": {'elctks_選舉區': 7081, 'elctks_鄉鎮市區': 727, 'elctks_檔別合計': 10},
    "pop_applicability": {'縣市以上': 364, '低於縣市_不適用': 267512},
    "sha256": "84740535b1f4a9a8fec8ebfe8f7577889837b7639cd7f5e40ef8826c6ab2f69a",
}

failures: list[str] = []
skipped: list[str] = []


def reports(fn):
    """讓測試函式在有 check() 失敗時真的丟出 AssertionError。

    ⚠️ 這個包裝是必要的，不是裝飾。原本每個 test_* 只把失敗記進全域
    `failures`，函式本身正常返回——**在 pytest 下會被判定為通過**。
    實測：故意改壞一個預期值後，`pytest` 報 7 passed / exit 0，
    直接執行卻正確 exit 1。而 docstring 當時還寫著「兩者皆可」。

    測試數量再多，若失敗不會讓 runner 失敗，數量就沒有意義。
    """
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
        print(f"  FAIL  {name}\n          得到 {got}\n          預期 {want}")
        failures.append(name)


def check_raises(name: str, fn) -> None:
    try:
        fn()
    except ValidationError:
        print(f"  PASS  {name}")
        return
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL  {name}（丟出 {type(exc).__name__} 而非 ValidationError）")
        failures.append(name)
        return
    print(f"  FAIL  {name}（沒有丟出例外）")
    failures.append(name)


# ---------------------------------------------------------------- 單元測試

@reports
def test_is_blank() -> None:
    print("\n[單元] is_blank——補零位數跨檔不一致，'0' 與 '0000' 都代表彙總")
    check("空字串", is_blank(""), True)
    check("'0'", is_blank("0"), True)
    check("'000'", is_blank("000"), True)
    check("'0000'", is_blank("0000"), True)
    check("'0001' 不是彙總", is_blank("0001"), False)
    check("'A001' 不是彙總（跨村里投開票所）", is_blank("A001"), False)


@reports
def test_admin_level() -> None:
    print("\n[單元] admin_level——彙總列與明細列混在同一檔，判錯就會重複加總")
    cases = [
        (["00", "000", "00", "000", "0000", "0000"], "檔別合計"),
        (["10", "002", "00", "000", "0000", "0000"], "直轄市縣市"),
        (["63", "000", "00", "000", "0000", "0000"], "直轄市縣市"),
        (["10", "002", "11", "000", "0000", "0000"], "選舉區"),
        (["10", "002", "11", "010", "0000", "0000"], "鄉鎮市區"),
        (["10", "002", "11", "010", "0001", "0000"], "村里"),
        (["10", "002", "11", "010", "0036", "0001"], "投開票所"),
        # D2 原住民區長不分選舉區，第 3 欄為 00 但第 4 欄有值
        (["64", "000", "00", "360", "0000", "0000"], "鄉鎮市區"),
        # 跨村里投開票所的村里代碼首碼為英文
        (["10", "002", "11", "010", "A001", "0000"], "村里"),
    ]
    for codes, want in cases:
        check(f"{','.join(codes)}", admin_level(codes), want)


@reports
def test_detect_layout() -> None:
    print("\n[單元] detect_layout——套錯版面會得到看似合理的錯誤席次且不報錯")
    # 2022 實際版面：候選男,候選女,候選合計,當選男,當選女,當選合計
    n = {11: 31, 12: 15, 13: 46, 14: 13, 15: 10, 16: 23}
    check("2022 版面", detect_layout(n), ("男女合計", 46, 23))
    # 官方格式文件版面：候選合計,當選合計,候選男,候選女,當選男,當選女
    n = {11: 3, 12: 1, 13: 2, 14: 1, 15: 1, 16: 0}
    check("格式文件版面", detect_layout(n), ("合計在前", 3, 1))
    # 兩種皆不成立 → 中止
    check_raises(
        "皆不成立即中止",
        lambda: detect_layout({11: 5, 12: 5, 13: 99, 14: 1, 15: 1, 16: 99}),
    )
    # 兩種同時成立（全為 0）→ 也必須中止，不可靜默取第一種
    check_raises(
        "同時成立即中止（不可靜默取第一種）",
        lambda: detect_layout({11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0}),
    )


@reports
def test_win_marks() -> None:
    """當選註記的分類邏輯。

    ⚠️ 這個測試必須是單元測試，不能靠資料驗證：
    2022 年 T2 **完全沒有 `!` 列**，所以把 `!` 從 ELECTED_MARKS 拿掉，
    建置與所有迴歸測試都會照樣通過（已用變異測試確認）。
    真正會踩到的是 R2（少 2 席）與 T1（少 4 席），但那些還不在建置範圍內。
    """
    print("\n[單元] 當選註記——2022 T2 無 '!' 列，只能靠單元測試守住")
    check("四種註記都有定義", set(WIN_MARKS) - {""},
          {"*", " ", "!", "-"})
    check("'*' 計入席次", "*" in ELECTED_MARKS, True)
    check("'!' 婦女保障【計入席次】", "!" in ELECTED_MARKS, True)
    check("'-' 被排擠者【不計入】", "-" in ELECTED_MARKS, False)
    check("空白不計入", " " in ELECTED_MARKS, False)
    check("'!' 的語意", WIN_MARKS["!"], "婦女保障當選")
    check("'-' 的語意", WIN_MARKS["-"], "因婦女保障被排擠未當選")


@reports
def test_read_csv() -> None:
    print("\n[單元] read_csv——欄數逐列嚴格檢查，且用 csv.reader 而非 split")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("ok.csv", "1,中國國民黨\n16,民主進步黨\n")
        zf.writestr("short.csv", "1,中國國民黨\n16\n")
        zf.writestr("long.csv", "1,中國國民黨\n16,民主進步黨,多餘\n")
        zf.writestr("quoted.csv", '1,"含,逗號的黨名"\n16,民主進步黨\n')
        zf.writestr("empty.csv", "\n\n")
    zf = zipfile.ZipFile(buf)
    names = zip_names(zf)

    check("正常讀取", read_csv(zf, names, "ok.csv", 2),
          [["1", "中國國民黨"], ["16", "民主進步黨"]])
    check_raises("欄數不足即中止", lambda: read_csv(zf, names, "short.csv", 2))
    check_raises("欄數過多即中止", lambda: read_csv(zf, names, "long.csv", 2))
    check_raises("空檔即中止", lambda: read_csv(zf, names, "empty.csv", 2))
    check_raises("找不到檔即中止", lambda: read_csv(zf, names, "nope.csv", 2))
    # 這一項是 split(",") 會錯、csv.reader 才對的關鍵差異
    check("引號包住的逗號不會被拆開",
          read_csv(zf, names, "quoted.csv", 2)[0],
          ["1", "含,逗號的黨名"])


@reports
def test_read_csv_keys() -> None:
    """關聯鍵欄位的尾隨空白正規化——白名單，不是全面 strip。

    ⚠️ 這一組必須是單元測試。1994-2006 尚未進入 BUILD_YEARS，而既有四屆
    無論 strip 與否輸出都【逐位元組相同】（已實測三張表 SHA-256 一致，
    因為 2009-2018 的 quoted 路徑本來就整列 strip，2022 唯一受影響的
    當選註記在 process_one() 也已經 .strip()）。也就是說：把 KEY_COLS
    整組拿掉，建置與全部迴歸測試都會照樣通過。

    兩條會被擋下的失效路徑，兩條都不報錯：
      1. elprof／elctks 投開票所欄 '0 ' → 每一列都被判成投開票所
      2. 2005 elctks 號次 '1 ' vs elcand '1' → 雙向參照全數對不上
    """
    print("\n[單元] read_csv 關聯鍵正規化——舊屆未進建置範圍，只能靠單元測試守住")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # 模擬 1998／2002／2005 的形式：無引號，投開票所欄 '0 '，
        # 號次 '1 '，得票率與註記帶尾隨空白
        zf.writestr("legacy.csv", "01,005,07,010,0000,0 ,1 ,123,30.61 , \n")
        zf.writestr("q.csv", '"\'10","\'002","\'11","\'010","\'0001","\'0036"\n')
    zf = zipfile.ZipFile(buf)
    names = zip_names(zf)

    # 不給 keys → 原樣保留（證明正規化確實由 keys 驅動，不是別處順手做掉的）
    check("不給 keys 時原樣保留",
          read_csv(zf, names, "legacy.csv", 10)[0],
          ["01", "005", "07", "010", "0000", "0 ", "1 ", "123", "30.61 ", " "])
    # 給 keys → 只有白名單內的欄位被正規化
    got = read_csv(zf, names, "legacy.csv", 10, False, KEY_COLS["elctks"])[0]
    check("投開票所欄（關聯鍵）已正規化", got[5], "0")
    check("號次欄（關聯鍵）已正規化", got[6], "1")
    check("得票率（非關聯鍵）原樣保留", got[8], "30.61 ")
    check("當選註記（非關聯鍵）原樣保留——' ' 是官方四值之一", got[9], " ")
    check("非關聯鍵的得票數未被改動", got[7], "123")
    # quoted 路徑不變：去撇號＋整列 strip 是已驗證過的既有行為
    check("quoted 路徑照舊去撇號",
          read_csv(zf, names, "q.csv", 6, True, KEY_COLS["elprof"])[0],
          ["10", "002", "11", "010", "0001", "0036"])

    # 白名單本身的完整性
    check("每個來源檔都宣告了關聯鍵", set(KEY_COLS), set(COLS))
    check("號次欄在 elcand 的白名單內", 5 in KEY_COLS["elcand"], True)
    check("號次欄在 elctks 的白名單內", 6 in KEY_COLS["elctks"], True)
    check("政黨代號在 elcand 的白名單內（對照 elpaty 的鍵）",
          7 in KEY_COLS["elcand"], True)
    # 白名單索引不得超出該檔欄數——寫錯會靜默不生效
    check("白名單索引都在欄數範圍內",
          [(f, i) for f, ks in KEY_COLS.items() for i in ks if i >= COLS[f]], [])
    # 行政區代碼欄【每一欄】都必須在白名單內。
    # ⚠️ 這裡刻意把欄數獨立寫一遍（而非從 build 模組匯入）——測試要當獨立的
    # oracle，若兩邊共用同一個常數，改壞常數會讓兩邊一起變而測不出來。
    # 這一條是變異測試逼出來的：把 elprof 的 idx5 從白名單拿掉，
    # 上面所有測試照樣通過（quoted 路徑本來就整列 strip，既有四屆看不出差異），
    # 但 1998／2002 的每一列都會被判成投開票所。
    N_CODE_COLS = {"elbase": 5, "elcand": 5, "elpaty": 0, "elprof": 6, "elctks": 6}
    check("代碼欄數宣告涵蓋全部來源檔", set(N_CODE_COLS), set(COLS))
    for f, n in N_CODE_COLS.items():
        check(f"{f} 的 {n} 個行政區代碼欄都在白名單內",
              [i for i in range(n) if i not in KEY_COLS[f]], [])
    # 非關聯鍵【不得】被列入白名單。這幾欄的既有處置是原樣保留來源值。
    check("得票率欄未被列入白名單", 8 in KEY_COLS["elctks"], False)
    check("當選註記欄未被列入白名單（elctks idx9）",
          9 in KEY_COLS["elctks"], False)
    check("當選註記欄未被列入白名單（elcand idx14）",
          14 in KEY_COLS["elcand"], False)
    check("人口數欄未被列入白名單", 10 in KEY_COLS["elprof"], False)
    check("投票率欄未被列入白名單", 18 in KEY_COLS["elprof"], False)


@reports
def test_render_csv_deterministic() -> None:
    print("\n[單元] render_csv——gzip 需可重現（mtime 固定、標頭不含檔名）")
    rows = [{"a": 1, "b": "甲"}, {"a": 2, "b": "乙"}]
    check("gzip 兩次結果相同",
          render_csv(rows, "x", gzip_it=True) == render_csv(rows, "x", gzip_it=True),
          True)
    check("gzip 內容正確",
          gzip.decompress(render_csv(rows, "x", gzip_it=True)).decode("utf-8-sig"),
          render_csv(rows, "x").decode("utf-8-sig"))
    check_raises("空資料即中止", lambda: render_csv([], "x"))


def check_raises_oracle(name: str, fn) -> None:
    try:
        fn()
    except OracleError:
        print(f"  PASS  {name}")
        return
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL  {name}（丟出 {type(exc).__name__} 而非 OracleError）")
        failures.append(name)
        return
    print(f"  FAIL  {name}（沒有丟出例外）")
    failures.append(name)


@reports
def test_custom_election_types() -> None:
    """本專案自訂的選舉種類代碼。

    ⚠️ 這一組必須是單元測試。1994-2006 尚未進入 BUILD_YEARS，所以把自訂代碼
    整組刪掉，建置與所有迴歸測試都會照樣通過——沒有任何真實資料會踩到它。
    """
    print("\n[單元] 自訂選舉種類代碼——舊屆未進建置範圍，只能靠單元測試守住")
    check("四個自訂代碼都在", set(CUSTOM_ELECTION_TYPES),
          {"T-PRV2", "T-PRV3", "T-COMBO", "D1-MT"})
    # 連字號是「非官方代碼」的辨識標記。官方代碼一律兩字元英數，
    # 若哪天有人把自訂代碼改成兩字元，就會與官方代碼混淆且無法分辨。
    check("自訂代碼皆含連字號（官方代碼一律無）",
          [c for c in CUSTOM_ELECTION_TYPES if "-" not in c], [])
    check("自訂代碼不與官方代碼重疊",
          set(CUSTOM_ELECTION_TYPES) & set(ELECTION_TYPES), set())
    # 兩份對照表的一致性：任一邊新增種類而另一邊沒跟上都會被擋下
    check("粒度表涵蓋官方＋自訂的全部種類",
          set(ELECTION_TYPE_GRANULARITY),
          set(ELECTION_TYPES) | set(CUSTOM_ELECTION_TYPES))
    check("合併類別的粒度標為合併",
          ELECTION_TYPE_GRANULARITY["T-COMBO"], "合併未分平地山地")
    check("省議員是與 T2／T3 不同的職位",
          {office_type("T-PRV2", "單一"), office_type("T-PRV3", "單一")},
          {"臺灣省議員"})
    check("合併類別的職位是直轄市議員",
          office_type("T-COMBO", "單一"), "直轄市議員")
    check_raises_oracle("未登記的選舉種類即中止",
                        lambda: is_main_sequence("T9"))


@reports
def test_comparability_flags() -> None:
    """可比性標記欄位。

    這四欄是下游判斷「哪些列可以畫進同一條折線」的唯一依據，
    來源一欄都沒有，所以錯了不會有任何算術驗證抓得到。
    """
    print("\n[單元] 可比性標記——來源沒有這四欄，算術 oracle 一項都沒有")
    got = comparability_flags("2022", "T2", "city")
    check("四個標記欄位齊備", set(got),
          {"office_type", "category_granularity",
           "is_main_sequence", "admin_code_system"})
    check("2022 T2 city 職位為縣市議員", got["office_type"], "縣市議員")
    check("2022 T2 city 進主序列", got["is_main_sequence"], "true")
    check("2022 代碼系統", got["admin_code_system"], "2014+")

    # 同一選舉種類、不同檔別 → 不同職位。猜錯會把直轄市數字記成縣市的。
    check("T2 prv 職位為直轄市議員",
          comparability_flags("2022", "T2", "prv")["office_type"], "直轄市議員")
    check("2009-2010 五都腿為直轄市議員",
          comparability_flags("2009-2010", "T3", "五都 2010-11-27")["office_type"],
          "直轄市議員")
    check("2009-2010 縣市腿為縣市議員",
          comparability_flags("2009-2010", "T3", "縣市 2009-12-05")["office_type"],
          "縣市議員")

    # 主序列：這是 1994 與直轄市合併類別【不進折線】的機制
    check("1994 省議員不進主序列",
          comparability_flags("1994", "T-PRV3", "單一")["is_main_sequence"], "false")
    check("直轄市合併類別不進主序列",
          comparability_flags("1998", "T-COMBO", "單一")["is_main_sequence"], "false")
    check("官方種類皆進主序列",
          {is_main_sequence(t) for t in ELECTION_TYPES}, {True})
    check("自訂種類皆不進主序列",
          {is_main_sequence(t) for t in CUSTOM_ELECTION_TYPES}, {False})

    # 行政區代碼系統：至少六套互不相通，跨屆比對行政區前必須先確認此欄相同
    check("六套代碼系統", set(ADMIN_CODE_SYSTEMS.values()),
          {"1994", "1998", "2002", "2005+", "2009", "2014+"})
    check("1998 與 2002 不是同一套",
          ADMIN_CODE_SYSTEMS["1998"] == ADMIN_CODE_SYSTEMS["2002"], False)
    check("2009-2010 與 2014+ 不是同一套",
          ADMIN_CODE_SYSTEMS["2009-2010"] == ADMIN_CODE_SYSTEMS["2022"], False)
    check("2014／2018／2022 同一套",
          {ADMIN_CODE_SYSTEMS[y] for y in ("2014", "2018", "2022")}, {"2014+"})
    check("2005 與 2006 同一套",
          {ADMIN_CODE_SYSTEMS[y] for y in ("2005", "2006")}, {"2005+"})

    # 未登記即中止——這三條是防「靜默套用預設值」的
    check_raises_oracle("未登記的屆別即中止",
                        lambda: comparability_flags("2026", "T2", "city"))
    check_raises_oracle("未登記的檔別即中止",
                        lambda: comparability_flags("2022", "T2", "縣市"))
    check_raises_oracle("議員種類遇全國單一檔即中止（無法判定縣市或直轄市）",
                        lambda: comparability_flags("2022", "T2", "單一"))
    # ⚠️ 只有 T1／T2／T3 的職位取決於檔別，才需要 FILE_SCOPE 登記；
    #    其餘種類（含三個自訂代碼）的職位由選舉種類本身決定。
    #    種類清單在測試裡獨立寫一遍——與 build 模組共用常數會讓改壞時兩邊一起變。
    NEEDS_SCOPE = ("T1", "T2", "T3")
    check("職位取決於檔別的種類，其檔別都已登記於 FILE_SCOPE",
          [(y, et, lbl) for y, cfg in YEARS.items()
           for et, parts in cfg["parts"].items() if et in NEEDS_SCOPE
           for lbl in parts if lbl not in FILE_SCOPE], [])

    # manifest 的欄名必須與 comparability_flags() 實際產出的鍵同名。
    # ⚠️ 這一條是變異測試逼出來的：把 MANIFEST 裡的 "is_main_sequence" 改名，
    # 上面所有測試照樣通過（「沒有算術 oracle 的欄位數」是計數，改名不變）。
    # 唯一會抓到的是建置時的 check_manifest——但那要跑完整建置才發現。
    for t in ("summary", "candidates", "votes"):
        check(f"{t} 已宣告全部四個可比性標記欄位",
              [k for k in got if k not in MANIFEST[t]], [])


@reports
def test_population_applicability() -> None:
    """人口數欄的適用層級標記。

    ⚠️ 這一組必須是單元測試。既有四屆的資料【不會】踩到小數（小數只出現在
    1998-2006），所以把 idx10 改回 int() 轉型，建置與全部迴歸測試都會照樣通過。

    ⚠️「適用」不等於「已驗證」：縣市層級也有帶小數的值（2002 山原全國
    206740.121634792），而戶籍人口是離散的人頭計數，不可能有小數。
    """
    print("\n[單元] 人口數適用層級——小數只在舊屆出現，只能靠單元測試守住")
    # 只有檔別合計與縣市層級適用。選舉區【不】適用——它在縣市之下，
    # 且 1/607 的違反率是弱證據，不足以支持放寬（spec 明定 county and above）。
    LEVELS = ["檔別合計", "直轄市縣市", "選舉區", "鄉鎮市區", "村里", "投開票所"]
    check("適用的層級恰為兩個",
          [lv for lv in LEVELS if population_applicability(lv) == "縣市以上"],
          ["檔別合計", "直轄市縣市"])
    check("選舉區不適用", population_applicability("選舉區"), "低於縣市_不適用")
    check("鄉鎮市區不適用", population_applicability("鄉鎮市區"), "低於縣市_不適用")
    check("投開票所不適用", population_applicability("投開票所"), "低於縣市_不適用")
    # 常數宣告與 admin_level 的實際輸出必須對得上。
    # ⚠️ 這裡的層級名稱刻意獨立寫一遍——共用同一個常數，改壞時兩邊會一起變。
    check("適用層級的名稱都是 admin_level 產得出來的",
          [lv for lv in POPULATION_APPLICABLE_LEVELS if lv not in LEVELS], [])
    check("兩個標記值不相同",
          POPULATION_APPLICABLE != POPULATION_NOT_APPLICABLE, True)
    # 欄名必須與 manifest 宣告一致（summary 才有人口數，另兩張表沒有）
    check("summary 宣告了人口數適用層級", "人口數適用層級" in MANIFEST["summary"], True)
    check("candidates 沒有人口數欄",
          "人口數" in MANIFEST["candidates"], False)
    check("votes 沒有人口數欄", "人口數" in MANIFEST["votes"], False)
    # 「適用」而非「可用／有效」：後兩者會被讀成數值已驗證
    check("標記用詞不宣稱數值已驗證",
          [w for w in ("可用", "有效", "正確", "已驗證")
           if w in POPULATION_APPLICABLE or w in POPULATION_NOT_APPLICABLE], [])


_PRE = "votedata/votedata/voteData/t/"


def _synthetic_zip(pop_total: str, pop_county: str, pop_town: str,
                   age: str = "45"):
    """造一份最小的合成來源檔，形式仿 1994-2006（無引號、合計列在首列）。

    elprof 的 idx11-16 用「合計在前」版面：候選合計 3、當選合計 1、
    候選男 2、候選女 1、當選男 1、當選女 0（2+1=3、1+0=1 成立，
    而「男女合計」式 3+1≠2 不成立，故版面判定不會模稜兩可）。
    """
    def prof(codes, pop):
        return (",".join(codes) + f",80,20,100,200,{pop}"
                + ",3,1,2,1,1,0,50.00,50.00,33.33")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # 本地檔用【2002 山原對照表裡的】南投縣本地碼 01007。
        # 同屆區域檔的南投縣是 01008——換算後 縣市_正規化 應為 008。
        zf.writestr(_PRE + "elbase.csv",
                    "00,000,00,000,0000,合計\n"
                    "01,007,00,000,0000,南投縣\n"
                    "01,007,01,010,0000,測試鄉\n")
        zf.writestr(_PRE + "elprof.csv", "\n".join([
            prof(["00", "000", "00", "000", "0000", "0"], pop_total),
            prof(["01", "007", "00", "000", "0000", "0"], pop_county),
            # 投開票所欄刻意寫成 '0 '——順便覆蓋關聯鍵正規化
            prof(["01", "007", "01", "010", "0000", "0 "], pop_town),
        ]) + "\n")
        zf.writestr(_PRE + "elcand.csv",
                    "01,007,01,000,0000,1,測試候選人,999,1,0700101," + age
                    + ",臺東縣,大學,N,*,0\n")
        zf.writestr(_PRE + "elctks.csv",
                    "01,007,01,010,0000,0 ,1 ,80,100.00 ,*\n")
        zf.writestr(_PRE + "elpaty.csv", "999,無黨籍及未經政黨推薦\n")
        # 同屆「區域」檔——換算的權威清單。刻意只放縣市層級需要的那一列，
        # 外加一個不相關的縣市，證明查的是代碼而不是「唯一那一列」。
        # 同屆「區域」檔——縣市與鄉鎮兩個層級的權威清單。
        # 鄉鎮列的代碼刻意與本地檔不同（本地 010 → 區域 020），
        # 這樣「有沒有真的換算」才看得出來。
        zf.writestr("votedata/votedata/voteData/r/elbase.csv",
                    "00,000,00,000,0000,合計\n"
                    "01,008,00,000,0000,南投縣\n"
                    "01,008,01,020,0000,測試鄉\n"
                    "01,010,00,000,0000,嘉義縣\n")
    return zipfile.ZipFile(buf)


# 合成壓縮檔用的鄉鎮對照列：(縣市名稱, 本地碼, 鄉鎮名稱, 目標碼)
_SYN_TOWNS_DEFAULT = [("南投縣", "010", "測試鄉", "020")]


@contextlib.contextmanager
def _synthetic_town_env(year: str, rows=None):
    """把鄉鎮市區正規化的三項輸入指向合成資料。

    ⚠️ process_one 對 TOWN_CODES_FILE_LOCAL 內的檔會由來源重新推導對照表，
    所以合成壓縮檔也必須提供區域檔的鄉鎮列、一份對應的對照表、
    以及相符的宣告數。少任何一項建置都會（正確地）中止——
    那是刻意的：對照表與來源脫節時不可沿用舊值。
    """
    rows = _SYN_TOWNS_DEFAULT if rows is None else rows
    tmp = Path(tempfile.mkdtemp()) / "town.csv"
    tmp.write_text(
        "屆別,選舉種類,縣市名稱,本地鄉鎮代碼,本地鄉鎮名稱,目標鄉鎮代碼,目標鄉鎮名稱\n"
        + "".join(f"{year},T3,{c},{lc},{n},{tc},{n}\n"
                 for c, lc, n, tc in rows),
        encoding="utf-8")
    real_target = TOWN_CROSSWALK_TARGETS.get(year)
    real_path = build_local_election.TOWN_CROSSWALK_PATH
    real_count = EXPECTED_TOWN_COUNTS.get((year, "T3"))
    # 合成檔沒有那些被截斷的鄉鎮，故該屆的 alias 宣告要一併移開——
    # 留著的話「宣告 1 次、實際 0 次」會（正確地）中止。
    real_aliases = {k: v for k, v in TOWN_NAME_ALIASES.items()
                    if k[0] == year and k[1] == "T3"}
    for k in real_aliases:
        del TOWN_NAME_ALIASES[k]
    TOWN_CROSSWALK_TARGETS[year] = "r"
    build_local_election.TOWN_CROSSWALK_PATH = tmp
    EXPECTED_TOWN_COUNTS[(year, "T3")] = len(rows)
    try:
        yield
    finally:
        if real_target is None:
            TOWN_CROSSWALK_TARGETS.pop(year, None)
        else:
            TOWN_CROSSWALK_TARGETS[year] = real_target
        build_local_election.TOWN_CROSSWALK_PATH = real_path
        if real_count is None:
            EXPECTED_TOWN_COUNTS.pop((year, "T3"), None)
        else:
            EXPECTED_TOWN_COUNTS[(year, "T3")] = real_count
        TOWN_NAME_ALIASES.update(real_aliases)


@reports
def test_process_one_legacy_decimals() -> None:
    """用合成的舊屆資料跑 process_one——人口數必須原樣保留、不轉型。

    ⚠️ 這一組必須用合成資料。既有四屆的人口數【全部是整數】，所以把
    idx10 改回 int() 轉型，建置與全部迴歸測試都會照樣通過（已用變異測試確認）。
    真正會踩到的是 2002 山原／平原的 9 個小數值，而那一屆還沒進 BUILD_YEARS。
    """
    print("\n[單元] process_one 的人口數處理——既有四屆全是整數，踩不到這條")
    zf = _synthetic_zip("206740.121634792", "49115.2145361076", "1888")
    names = zip_names(zf)
    # process_one 由 YEARS 取得該屆的編碼形式。2002 還沒進 YEARS（Task 3.2 才加），
    # 此處臨時登記；用 try/finally 確保不污染其他測試。
    # 2002 已在 YEARS（Task 3.2 納入），但它帶 folder；合成的壓縮檔沒有那層目錄，
    # 故暫時換成無 folder 的等價設定，並把區域檔指向合成的那一份。
    assert YEARS["2002"]["quoted"] is False, "2002 的編碼形式應為無引號"
    real_year, real_regional = YEARS["2002"], COUNTY_CROSSWALK_YEARS["2002"]
    YEARS["2002"] = {"quoted": False, "parts": {}}
    COUNTY_CROSSWALK_YEARS["2002"] = "r"       # 指向合成的區域檔
    try:
        with _synthetic_town_env("2002"):
            p = process_one(zf, names, "2002", "T3", "city", "t")
    finally:
        YEARS["2002"] = real_year
        COUNTY_CROSSWALK_YEARS["2002"] = real_regional

    S = p["summary"]
    check("三列都讀進來了", len(S), 3)
    # 端到端驗證 crosswalk 接線：本地碼 01007（南投縣）→ 區域檔碼 008
    check("縣市代碼已換算成區域檔代碼",
          [r["縣市_正規化"] for r in S], ["000", "008", "008"])
    check("原始縣市代碼原樣保留", [r["縣市"] for r in S], ["000", "007", "007"])
    check("用過的對照表鍵被記錄",
          sorted(p["crosswalk_used"]), [("2002", "T3", "01007")])
    # 端到端驗證鄉鎮市區 crosswalk 接線：合成的區域檔把 測試鄉 放在 020，
    # 本地檔放在 010。若換算沒發生，這裡會是 {'000', '010'}。
    check("鄉鎮市區代碼已換算成區域檔代碼",
          {r["鄉鎮市區_正規化"] for r in S}, {"000", "020"})
    check("鄉鎮列的原碼未被覆寫（來源值原樣保留）",
          {r["鄉鎮市區"] for r in S if not is_blank(r["鄉鎮市區"])}, {"010"})
    check("人口數是字串未轉型", isinstance(S[0]["人口數"], str), True)
    check("檔別合計的小數原樣保留", S[0]["人口數"], "206740.121634792")
    check("縣市層級的小數原樣保留", S[1]["人口數"], "49115.2145361076")
    check("鄉鎮市區的常數原樣保留", S[2]["人口數"], "1888")
    check("層級判定正確（'0 ' 已正規化，否則三列都會是投開票所）",
          [r["層級"] for r in S], ["檔別合計", "直轄市縣市", "鄉鎮市區"])
    check("適用層級標記",
          [r["人口數適用層級"] for r in S],
          ["縣市以上", "縣市以上", "低於縣市_不適用"])
    check("可比性標記帶進來了", S[0]["admin_code_system"], "2002")
    check("號次跨檔對得上（elctks '1 ' vs elcand '1'）",
          {c["號次"] for c in p["candidates"]} == {v["號次"] for v in p["votes"]},
          True)


@reports
def test_elected_authoritative() -> None:
    """2005 當選權威值的推導。用模擬的 2005 資料，斷言原欄位不變。

    ⚠️ 這一組必須用合成資料。既有四屆的 elcand 註記與權威值【完全一致】
    （7,335 筆實測零不一致），所以把整條推導改成直接抄 elcand，
    建置與全部迴歸測試都會照樣通過。

    合成的兩種情境都取自 2005 山原的實測樣貌：
      1. 一般：elctks 有選舉區層級的彙總列，註記為 '*'，但 elcand 寫 ' '（損壞）
      2. 屏東 16 區：elctks【只有鄉鎮市區層級】的列，elcand 的鄉鎮市區欄是 000
    """
    print("\n[單元] 當選權威值——既有四屆與 elcand 全一致，只能靠合成資料守住")

    def ctks_row(codes, no, votes, mark):
        return ",".join(codes) + f",{no},{votes},50.00,{mark}"

    def cand_row(codes, no, name, mark):
        return (",".join(codes) + f",{no},{name},999,1,0700101,45,"
                f"臺東縣,大學,N,{mark},0")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(_PRE + "elbase.csv",
                    "00,000,00,000,0000,合計\n"
                    "01,013,00,000,0000,屏東縣\n"
                    "01,013,11,000,0000,第11選舉區\n"
                    "01,013,16,000,0000,第16選舉區\n"
                    # elctks 用到的鄉鎮必須也在 elbase——真實資料實測
                    # 六個檔的 elprof／elctks 鄉鎮碼皆不超出 elbase。
                    "01,013,11,001,0000,甲鄉\n"
                    "01,013,16,033,0000,乙鄉\n")
        # 選舉區 11：兩位候選人，1 席；選舉區 16：一位候選人，1 席
        def prof(codes, nc, nw):
            return (",".join(codes) + ",1794,133,1927,2259,50000"
                    + f",{nc},{nw},{nc},0,{nw},0,50.00,85.30,50.00")
        zf.writestr(_PRE + "elprof.csv", "\n".join([
            prof(["00", "000", "00", "000", "0000", "0"], 3, 2),
            prof(["01", "013", "00", "000", "0000", "0"], 3, 2),
            prof(["01", "013", "11", "000", "0000", "0"], 2, 1),
            prof(["01", "013", "16", "000", "0000", "0"], 1, 1),
        ]) + "\n")
        # elcand：兩區共 3 人。⚠️ 註記【全部寫成未當選】，模擬 2005 的損壞
        zf.writestr(_PRE + "elcand.csv", "\n".join([
            cand_row(["01", "013", "11", "000", "0000"], "1", "甲", " "),
            cand_row(["01", "013", "11", "000", "0000"], "2", "乙", " "),
            cand_row(["01", "013", "16", "000", "0000"], "1", "杜春生", " "),
        ]) + "\n")
        # elctks：11 區有選舉區層級彙總列；16 區【只有鄉鎮市區層級】
        zf.writestr(_PRE + "elctks.csv", "\n".join([
            ctks_row(["01", "013", "11", "000", "0000", "0"], "1", "1000", "*"),
            ctks_row(["01", "013", "11", "000", "0000", "0"], "2", "794", " "),
            ctks_row(["01", "013", "11", "001", "0000", "0"], "1", "1000", " "),
            ctks_row(["01", "013", "16", "033", "0000", "0"], "1", "1794", "*"),
        ]) + "\n")
        zf.writestr(_PRE + "elpaty.csv", "999,無黨籍及未經政黨推薦\n")
        # 同屆「區域」檔：鄉鎮市區正規化的目標。本地的 001／033 在這裡是
        # 002／034——換算若沒發生，下面的斷言會看到原碼。
        zf.writestr("votedata/votedata/voteData/r/elbase.csv",
                    "00,000,00,000,0000,合計\n"
                    "01,013,00,000,0000,屏東縣\n"
                    "01,013,11,002,0000,甲鄉\n"
                    "01,013,16,034,0000,乙鄉\n")
    zf = zipfile.ZipFile(buf)
    names = zip_names(zf)

    # 2005 已在 YEARS（Task 3.2 納入）。該屆不需 crosswalk（縣市碼已是全域碼），
    # 但帶 folder，故同樣暫時換成無 folder 的等價設定。
    assert "2005" not in COUNTY_CROSSWALK_YEARS, "2005 不應需要 crosswalk"
    real_year = YEARS["2005"]
    YEARS["2005"] = {"quoted": False, "parts": {}}
    try:
        with _synthetic_town_env("2005",
                                 [("屏東縣", "001", "甲鄉", "002"),
                                  ("屏東縣", "033", "乙鄉", "034")]):
            p = process_one(zf, names, "2005", "T3", "city", "t")
    finally:
        YEARS["2005"] = real_year

    C = {c["姓名"]: c for c in p["candidates"]}
    check("三位候選人都在", sorted(C), ["乙", "杜春生", "甲"])
    # 來源原樣【完整保留】——這是「不覆寫來源數字」的紀律。
    # ⚠️ `當選` 現在存的是權威值，不是來源認定；來源認定看 `當選註記`。
    check("elcand 註記原樣保留（三人皆空白）",
          {c["當選註記"] for c in C.values()}, {""})
    check("來源認定（由註記推導）三人皆未當選",
          {c["當選註記"] in ELECTED_MARKS for c in C.values()}, {False})
    # 權威值由 elctks 推導
    check("甲：elctks 選舉區層級 '*' → 權威值當選",
          C["甲"]["當選"], "Y")
    check("乙：elctks 選舉區層級 ' ' → 權威值未當選",
          C["乙"]["當選"], "N")
    check("甲的依據是選舉區層級",
          C["甲"]["當選_依據"], "elctks_選舉區")
    # ⚠️ 這一項是本組的核心：elcand 鄉鎮市區欄為 000，elctks 只有 033 那一列。
    #    若把鄉鎮市區欄也當成必須相等的鍵，這位候選人會完全對不上而中止。
    check("杜春生：elctks 只有鄉鎮市區層級的列 → 仍能推導出當選",
          C["杜春生"]["當選"], "Y")
    check("杜春生的依據是鄉鎮市區層級",
          C["杜春生"]["當選_依據"], "elctks_鄉鎮市區")
    # 乙在 11 區的鄉鎮市區層級也有一列（註記 ' '），但選舉區層級才是依據
    check("甲有多層級列時取最高層級（選舉區優先於鄉鎮市區）",
          C["甲"]["當選_依據"], "elctks_選舉區")
    check("權威值當選人數 = 2（elprof 檔別合計也是 2）",
          sum(1 for c in C.values() if c["當選"] == "Y"), 2)


@reports
def test_elected_authoritative_aborts() -> None:
    """推導不出來時必須中止，不可猜測。

    刻意【沒有】「elctks 無列就由 elprof 同額競選補齊」的回退——
    實測 6 個舊檔與既有四屆共 7,335 位候選人沒有任何一位缺 elctks 列，
    而該回退會在 elctks 整區遺失時把整區靜默標成當選。
    """
    print("\n[單元] 當選權威值推導失敗時中止")
    C5 = ["01", "013", "16", "000", "0000"]

    def cand(no, mark=" "):
        return [*C5, no, "某人", "999", "1", "0700101", "45",
                "臺東縣", "大學", "N", mark, "0"]

    def ctks(codes, no, mark):
        return [*codes, no, "100", "50.00", mark]

    # elctks 完全沒有該候選人的列 → 中止（不由 elprof 補）
    check_raises("elctks 無對應列即中止",
                 lambda: derive_elected_authoritative([cand("1")], [], "T"))
    # 同一層級註記自相矛盾 → 中止（不取多數、不取「任一為星號」）
    check_raises(
        "同層級註記矛盾即中止",
        lambda: derive_elected_authoritative(
            [cand("1")],
            [ctks(["01", "013", "16", "033", "0000", "0"], "1", "*"),
             ctks(["01", "013", "16", "034", "0000", "0"], "1", " ")], "T"))
    # 號次不同的人不會被混在一起
    got = derive_elected_authoritative(
        [cand("1"), cand("2")],
        [ctks(["01", "013", "16", "000", "0000", "0"], "1", "*"),
         ctks(["01", "013", "16", "000", "0000", "0"], "2", " ")], "T")
    check("號次區分不同候選人",
          [got[tuple(C5) + (n,)][0] for n in ("1", "2")], [True, False])
    # ⚠️ D2／R3 的情境：候選人的選舉區欄為空白，真正的單位在鄉鎮市區欄。
    #    選舉區欄空白時不約束該欄，但鄉鎮市區欄必須相等，否則不同區的
    #    同號次候選人會被併成一個（既有四屆實測 332 筆會受影響）。
    d2 = ["64", "000", "00", "360", "0000"]
    d2b = ["64", "000", "00", "370", "0000"]
    got = derive_elected_authoritative(
        [[*d2, "1", "茂林甲", "999", "1", "0700101", "45", "高雄市", "大學",
          "N", " ", "0"],
         [*d2b, "1", "桃源甲", "999", "1", "0700101", "45", "高雄市", "大學",
          "N", " ", "0"]],
        [ctks(["64", "000", "01", "360", "0000", "0"], "1", "*"),
         ctks(["64", "000", "01", "370", "0000", "0"], "1", " ")], "D2")
    check("選舉區欄空白時仍以鄉鎮市區欄區分候選人",
          [got[tuple(d2) + ("1",)][0], got[tuple(d2b) + ("1",)][0]],
          [True, False])


@reports
def test_county_crosswalk() -> None:
    """縣市代碼的三段式換算。

    ⚠️ 這一組必須是單元測試。1998／2002 尚未進 BUILD_YEARS，而既有四屆
    完全不走換算路徑（`縣市_正規化` 等於 `縣市`），所以把三段式規則
    整個拆掉，建置與全部迴歸測試都會照樣通過。
    """
    print("\n[單元] 縣市代碼三段式換算——既有四屆不走這條路徑")
    # 對照表【只收代碼不同者】。01001 臺北縣兩邊同碼，刻意不收。
    cw = {("1998", "T2", "01005"): ("嘉義縣", "01010")}
    reg = {"01010": "嘉義縣", "01001": "臺北縣"}
    used: set = set()

    check("第1段：列於對照表 → 用區域檔代碼",
          resolve_county_code("1998", "T2", "01", "005", "嘉義縣",
                              cw, reg, "T", used), "010")
    check("用過的鍵被記錄（供『不得有未使用列』檢查）",
          sorted(used), [("1998", "T2", "01005")])
    check("第2段：未列於對照表但同碼同名 → identity",
          resolve_county_code("1998", "T2", "01", "001", "臺北縣",
                              cw, reg, "T", used), "001")
    check("identity 不記入用過的鍵", len(used), 1)
    # 第 3 段：identity 【不是】無條件退回——這是差異表沒有削弱 fail-fast 的關鍵
    check_raises(
        "未知代碼即中止（identity 不是無條件退回）",
        lambda: resolve_county_code("1998", "T2", "01", "999", "火星縣",
                                    cw, reg, "T", used))
    check_raises(
        "同碼但名稱不符即中止",
        lambda: resolve_county_code("1998", "T2", "01", "001", "桃園縣",
                                    cw, reg, "T", used))
    # 第 1 段的三方名稱驗證：本地檔、對照表、區域檔
    check_raises(
        "三方名稱不一致即中止（本地檔與對照表不符）",
        lambda: resolve_county_code("1998", "T2", "01", "005", "嘉義市",
                                    cw, reg, "T", used))
    check_raises(
        "三方名稱不一致即中止（對照表指向的區域檔代碼不存在）",
        lambda: resolve_county_code("1998", "T2", "01", "005", "嘉義縣",
                                    cw, {"01001": "臺北縣"}, "T", used))
    # 不同選舉種類的同一代碼是不同縣市——鍵必須含選舉種類
    check_raises(
        "對照表的鍵含選舉種類（T3 查不到 T2 的列）",
        lambda: resolve_county_code("1998", "T3", "01", "005", "嘉義縣",
                                    cw, reg, "T", used))

    # 對照表是【輸入】不是產物，不得放在輸出目錄底下。
    # ⚠️ 這一條守的不是資料正確性，是「清空輸出目錄再重跑」不會把輸入刪掉。
    #    放回 OUT_DIR 時建置與其餘測試全部照樣通過——這裡不擋就沒人擋。
    check("對照表不在輸出目錄底下",
          OUT in COUNTY_CROSSWALK_PATH.parents, False)
    check("對照表放在 data/reference/",
          COUNTY_CROSSWALK_PATH.parent.name, "reference")

    # 實際的對照表：只收代碼不同者，且鍵不重複
    real = load_county_crosswalk()
    # 2026-08-27 加入 D1-MT 後由 31 列增為 67：1998／2002 的鄉鎮市長檔省市碼
    # 為 03、同屆區域檔為 01，18 個縣市的 identity 一個都對不上，故各補 18 列。
    check("對照表 67 列", len(real), 67)
    check("涵蓋的屆別與選舉種類",
          sorted({(k[0], k[1]) for k in real}),
          [("1998", "D1-MT"), ("1998", "T2"), ("1998", "T3"),
           ("2002", "D1-MT"), ("2002", "T2"), ("2002", "T3")])
    check("D1-MT 各屆 18 個縣市",
          sorted(collections.Counter(
              k[0] for k in real if k[1] == "D1-MT").items()),
          [("1998", 18), ("2002", 18)])
    check("每一列的本地代碼與區域碼確實不同（identity 列不入表）",
          [k for k, (_, rc) in real.items() if k[2] == rc], [])
    check("2005 不在對照表內（該屆縣市碼已是全域碼）",
          [k for k in real if k[0] == "2005"], [])

    # 鄉鎮市區代碼：宣告為檔內重編者必須留空
    # ⚠️ D1-MT 只有 1998／2002 需要換算。2005 的 D1 實測與同屆區域檔 319 個
    #    代碼逐一相符，而同屆的 T2／T3 卻需要——同屆不同選舉種類的重編情形
    #    不同，不可互相推論。這一項守住那個區別。
    check("宣告為檔內重編的（屆別, 選舉種類）",
          sorted(TOWN_CODES_FILE_LOCAL),
          [("1998", "D1-MT"), ("1998", "T2"), ("1998", "T3"),
           ("2002", "D1-MT"), ("2002", "T2"), ("2002", "T3"),
           ("2005", "T2"), ("2005", "T3")])
    check("2005 的 D1-MT 不需要鄉鎮市區換算",
          ("2005", "D1-MT") in TOWN_CODES_FILE_LOCAL, False)
    # ⚠️ 2005 的縣市碼已是全域碼但鄉鎮市區碼【仍是檔內重編】——
    #    「2005 起才是全域代碼」只在縣市層級成立。這一項守住這個區別。
    check("2005 需要留空鄉鎮市區碼，但不需要縣市換算",
          [("2005", "T2") in TOWN_CODES_FILE_LOCAL,
           "2005" in COUNTY_CROSSWALK_YEARS], [True, False])
    check("1998／2002 兩者都需要",
          [("1998", "T3") in TOWN_CODES_FILE_LOCAL,
           "1998" in COUNTY_CROSSWALK_YEARS,
           "2002" in COUNTY_CROSSWALK_YEARS], [True, True, True])
    check("兩個正規化欄在三張表都宣告了 oracle",
          [t for t in ("summary", "candidates", "votes")
           for c in ("縣市_正規化", "鄉鎮市區_正規化") if c not in MANIFEST[t]], [])


@reports
def test_legacy_terms() -> None:
    """1998／2002／2005 六個舊屆檔的整合驗證。

    需要原始壓縮檔；沒有就跳過（該檔不入庫）。只跑這 6 個檔——它們都很小
    （elprof 各 201-269 列），秒級完成，不像既有四屆要跑一分多鐘。

    ⚠️ 這一組守的是【具名異常清單】。那些清單只在舊屆建置時才會被用到，
    所以純單元測試咬不到——把清單改壞、或把補償性檢查拿掉，
    其他測試都會照樣通過（已用變異測試確認）。
    """
    print("\n[整合] 1998／2002／2005 六個舊屆檔")
    if not ZIP_PATH.exists():
        print("  SKIP  找不到原始壓縮檔")
        skipped.append("legacy_terms")
        return

    LEGACY = ["2005", "2002", "1998"]
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zip_names(zf)
        parts = []
        for year in LEGACY:
            for etype, mapping in YEARS[year]["parts"].items():
                # 只跑縣市議員那一支；1998／2002 的 T-COMBO 由
                # test_custom_type_terms 負責。
                if etype not in ("T2", "T3"):
                    continue
                for label, sub in mapping.items():
                    parts.append(process_one(zf, names, year, etype, label, sub))

    check("六個檔都解析出來", len(parts), 6)
    rows = {f"{p['year']}-{p['etype']}": len(p["summary"]) for p in parts}
    check("各檔 elprof 列數", rows,
          {"2005-T2": 254, "2005-T3": 269, "2002-T2": 239, "2002-T3": 269,
           "1998-T2": 201, "1998-T3": 269})

    # cross_validate 必須通過——所有具名異常都要通過補償性檢查
    rep, an, ta, ema, ela = [], [], [], [], []
    cross_validate(parts, rep, an, ta, ema, ela)
    check("六個檔的交叉驗證通過", True, True)

    # 已具名的異常筆數。改動任一份清單都會在這裡被抓到。
    check("得票加總／配錯選舉區異常筆數", len(an), 4)
    check("投票率異常筆數（1998 兩檔的合計列＋2005 山原的進位臨界）", len(ta), 3)
    check("當選註記異常筆數（2005 山原 28＋平原 33）", len(ema), 61)
    check("投票數超過選舉人數異常筆數（1998 山原寶山鄉）", len(ela), 1)

    # ⚠️ 只數筆數不夠：兩側若取自同一欄，筆數仍是 61、這一項照樣通過，
    #    但每一筆的兩個值會恆等，報告失去它唯一的資訊。
    #    依定義能進這份清單就是因為兩邊不一致，故每一筆都必須相異。
    check("異常紀錄的兩側取自不同來源",
          [a["由註記推導"] == a["權威值"] for a in ema], [False] * len(ema))
    check("由註記推導 與 elcand當選註記 相符",
          [a["由註記推導"] == ("Y" if a["elcand當選註記"] in ELECTED_MARKS else "N")
           for a in ema], [True] * len(ema))

    # ⚠️ 報告的 `當選人數` 必須數【來源註記】、`當選人數_權威值` 數權威值。
    #    若前者改讀 `當選`（現為權威值），它會恆等於 elprof 的當選人數，
    #    第 4 項驗證的當選人數那一半就永遠不觸發——不會報錯，只會靜靜地
    #    再也偵測不到 elcand 損壞。2005 兩檔的 20/27 與 18/30 是唯一能
    #    分辨這兩者的真實資料。
    by_key: dict[str, list[int]] = {}
    for r in rep:
        acc = by_key.setdefault(f"{r['年度']}-{r['選舉種類']}", [0, 0])
        acc[0] += r["當選人數"]
        acc[1] += r["當選人數_權威值"]
    check("報告的來源席次與權威席次",
          {k: tuple(v) for k, v in by_key.items()},
          {"1998-T2": (23, 23), "1998-T3": (30, 30),
           "2002-T2": (26, 26), "2002-T3": (30, 30),
           "2005-T2": (20, 27), "2005-T3": (18, 30)})

    # 席次：2005 的 elcand 損壞，權威值才是正確席次
    seats = {}
    for p in parts:
        k = f"{p['year']}-{p['etype']}"
        # ⚠️ 左為【來源認定】（由 elcand 註記推導）、右為【權威值】。
        #    兩者必須取自不同的欄位——`當選` 現在存的是權威值，
        #    左右都讀它會恆等，這一項就再也看不出 2005 兩檔的差異。
        seats[k] = (
            sum(1 for c in p["candidates"] if c["當選註記"] in ELECTED_MARKS),
            sum(1 for c in p["candidates"] if c["當選"] == "Y"),
        )
    check("來源認定席次與權威值席次", seats,
          {"1998-T2": (23, 23), "1998-T3": (30, 30),
           "2002-T2": (26, 26), "2002-T3": (30, 30),
           "2005-T2": (20, 27), "2005-T3": (18, 30)})

    # 可比性標記
    flags = {f"{p['year']}-{p['etype']}":
             (p["summary"][0]["is_main_sequence"],
              p["summary"][0]["admin_code_system"],
              p["summary"][0]["office_type"]) for p in parts}
    check("三屆皆進主序列、代碼系統各自不同",
          sorted({(v[0], v[1], v[2]) for v in flags.values()}),
          [("true", "1998", "縣市議員"), ("true", "2002", "縣市議員"),
           ("true", "2005+", "縣市議員")])
    # 縣市代碼正規化：1998／2002 有換算、2005 沒有
    changed = {f"{p['year']}-{p['etype']}":
               sum(1 for s in p["summary"]
                   if not is_blank(s["縣市"]) and s["縣市_正規化"] != s["縣市"])
               for p in parts}
    check("被換算的列數（2005 應為 0）", changed,
          {"2005-T2": 0, "2005-T3": 0, "2002-T2": 207, "2002-T3": 148,
           "1998-T2": 169, "1998-T3": 148})
    # 鄉鎮市區代碼正規化。這一欄在 2026-08-22 之前對這六個檔一律留空；
    # 現在改為換算成同屆區域檔的代碼，留空即代表建置沒有做該做的事。
    check("六個檔的鄉鎮市區_正規化都不留空",
          sum(1 for p in parts for s in p["summary"]
              if s["鄉鎮市區_正規化"] == ""), 0)
    check("鄉鎮以上的列填 000（與其他檔一致，不是空字串）",
          {s["鄉鎮市區_正規化"] for p in parts for s in p["summary"]
           if is_blank(s["鄉鎮市區"])}, {"000"})
    town_units = {f"{p['year']}-{p['etype']}":
                  len({(s["省市"], s["縣市"], s["鄉鎮市區"])
                       for s in p["summary"] if not is_blank(s["鄉鎮市區"])})
                  for p in parts}
    check("逐檔的鄉鎮市區單位數", town_units,
          {"1998-T2": 177, "1998-T3": 226, "2002-T2": 211,
           "2002-T3": 226, "2005-T2": 224, "2005-T3": 226})
    # ⚠️ 只驗「有值」不夠——把換算改成直接放原碼也會有值。
    #    這一條釘死【真的被換掉】的單位數，總計 829。
    town_changed = {f"{p['year']}-{p['etype']}":
                    len({(s["省市"], s["縣市"], s["鄉鎮市區"])
                         for s in p["summary"]
                         if not is_blank(s["鄉鎮市區"])
                         and s["鄉鎮市區_正規化"] != s["鄉鎮市區"]})
                    for p in parts}
    check("代碼確實被換掉的單位數", town_changed,
          {"1998-T2": 139, "1998-T3": 195, "2002-T2": 99,
           "2002-T3": 167, "2005-T2": 76, "2005-T3": 153})
    check("換掉的單位合計 829", sum(town_changed.values()), 829)


@reports
def test_custom_type_terms() -> None:
    """1994 省議員與各屆直轄市合併類別的整合驗證（自訂代碼、降級標記）。

    需要原始壓縮檔；沒有就跳過。七個檔都很小（最大的 elctks 148 列）。

    ⚠️ 這一組守的是【降級標記】與這七個檔特有的來源瑕疵處置。
    把 is_main_sequence 改成一律 true、或把選舉區欄不一致的宣告拿掉，
    純單元測試都咬不到（那些檔的解析路徑只有在建置時才會走到）。
    """
    print("\n[整合] 1994 省議員與各屆直轄市合併類別")
    if not ZIP_PATH.exists():
        print("  SKIP  找不到原始壓縮檔")
        skipped.append("custom_type_terms")
        return

    CUSTOM = set(CUSTOM_ELECTION_TYPES)
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zip_names(zf)
        parts = []
        for year in ("1994", "1998", "2002", "2006"):
            for etype, mapping in YEARS[year]["parts"].items():
                if etype not in CUSTOM:
                    continue
                for label, sub in mapping.items():
                    parts.append(process_one(zf, names, year, etype, label, sub))

    # 2026-08-27 D1-MT 加入後由 7 增為 9（1998／2002 各一個檔）。
    # 選法刻意維持「這幾屆的【全部】自訂代碼」，不逐一列名——
    # 列名的話，日後新增自訂代碼會靜默不被這一組涵蓋。
    check("九個自訂代碼的檔都解析出來", len(parts), 9)
    check("涵蓋的（屆別, 選舉種類, 檔別）",
          sorted((p["year"], p["etype"], p["label"]) for p in parts),
          [("1994", "T-COMBO", "直轄市"), ("1994", "T-PRV2", "平原"),
           ("1994", "T-PRV2", "平原2"), ("1994", "T-PRV3", "山原"),
           ("1998", "D1-MT", "單一"), ("1998", "T-COMBO", "直轄市"),
           ("2002", "D1-MT", "單一"), ("2002", "T-COMBO", "直轄市"),
           ("2006", "T-COMBO", "直轄市")])

    rep, an, ta, ema, ela = [], [], [], [], []
    cross_validate(parts, rep, an, ta, ema, ela)
    check("九個檔的交叉驗證通過", True, True)
    # 具名異常：1994 兩檔＋2006 一列的彙總層級投票率、1994 直轄市的當選註記 2 筆、
    # 1998／2002 的「elctks 比 elprof 細」2 筆
    check("彙總層級投票率異常筆數", len(ta), 3)
    check("當選註記異常筆數（1994 高雄市 高玉生／吳福祥）", len(ema), 2)
    check("elctks 比 elprof 細的具名筆數", len(an), 2)

    # ⚠️ 降級標記——這是 1994 與合併類別【不進任何折線】的機制
    ms = {s["is_main_sequence"] for p in parts for s in p["summary"]}
    check("自訂代碼的 is_main_sequence 全為 false", ms, {"false"})
    check("職位類型",
          sorted({s["office_type"] for p in parts for s in p["summary"]}),
          ["山地鄉鄉長", "直轄市議員", "臺灣省議員"])
    check("合併類別的粒度標為合併",
          sorted({s["category_granularity"] for p in parts
                  for s in p["summary"] if p["etype"] == "T-COMBO"}),
          ["合併未分平地山地"])
    check("省議員的粒度為分平地山地",
          sorted({s["category_granularity"] for p in parts
                  for s in p["summary"] if p["etype"].startswith("T-PRV")}),
          ["分平地山地"])

    # 席次：1994 共 6 席（省議員 4＋直轄市合併 2），直轄市合併每屆固定 2 席
    seats = {}
    for p in parts:
        k = (p["year"], p["etype"])
        seats[k] = seats.get(k, 0) + sum(
            1 for c in p["candidates"] if c["當選"] == "Y")
    check("各（屆別, 選舉種類）的權威值席次", seats,
          {("1994", "T-PRV3"): 2, ("1994", "T-PRV2"): 2,
           ("1994", "T-COMBO"): 2, ("1998", "T-COMBO"): 2,
           ("2002", "T-COMBO"): 2, ("2006", "T-COMBO"): 2,
           # 山地鄉鄉長每鄉 1 席，1998／2002 皆為 30 個山地鄉
           ("1998", "D1-MT"): 30, ("2002", "D1-MT"): 30})
    check("1994 共 6 席",
          sum(v for (y, _), v in seats.items() if y == "1994"), 6)

    # 1994 直轄市高雄市：elcand 標錯人，權威值標的是最高票者
    kh = [c for p in parts if (p["year"], p["etype"]) == ("1994", "T-COMBO")
          for c in p["candidates"] if c["省市"] == "02"]
    # ⚠️ 比對的是【來源註記】與【權威值】。`當選` 現在存的是權威值，
    #    拿它跟自己比會恆真——那正是 elected-column-swap 要防的靜默失效。
    got = {c["姓名"]: (c["當選註記"], c["當選"]) for c in kh}
    check("高玉生：elcand 未標當選、權威值當選", got["高玉生"], ("", "Y"))
    check("吳福祥：elcand 標當選、權威值未當選", got["吳福祥"], ("*", "N"))

    # 選舉區欄不一致的宣告必須涵蓋這些檔
    check("選舉區欄不一致的宣告",
          sorted(DISTRICT_COLUMN_INCONSISTENT),
          [("1994", "T-COMBO", "直轄市"), ("1994", "T-PRV2", "平原2"),
           ("1998", "D1-MT", "單一"), ("1998", "T-COMBO", "直轄市"),
           ("2002", "D1-MT", "單一"), ("2002", "T-COMBO", "直轄市"),
           ("2005", "D1-MT", "單一"), ("2006", "T-COMBO", "直轄市"),
           ("2009-2010", "D1-MT", "單一"), ("2014", "D1-MT", "單一")])
    check("1994 平原（不是平原2）不在該宣告內",
          ("1994", "T-PRV2", "平原") in DISTRICT_COLUMN_INCONSISTENT, False)
    # ⚠️ 2018／2022 的 D1-MT【不】登記——四個來源檔的選舉區欄一致。
    #    多餘的條目等於預先赦免日後真的出現的分歧：它會被靜默正規化掉
    #    而不是中止。這一項守住「只為實測不一致者登記」。
    check("2018／2022 的 D1-MT 不在該宣告內",
          [("2018", "D1-MT", "單一") in DISTRICT_COLUMN_INCONSISTENT,
           ("2022", "D1-MT", "單一") in DISTRICT_COLUMN_INCONSISTENT],
          [False, False])


@reports
def test_valid_age() -> None:
    """輸出的 `年齡`（乾淨值）：有記載放值、未記載留空；判準具名到屆別。

    ⚠️ **這一組必須用合成資料。** 真實資料正好滿足前提——五個舊屆整批是 99、
    新四屆從未出現 99、全資料的 0 出現 0 次——所以兩條中止**永遠不會觸發**，
    而「99 一律當未記載」這種改壞在真實資料上也看不出差別。
    這正是它們最容易被無聲拿掉的原因。

    語意來自壓縮檔內的官方格式文件：
    「年齡 Num(3) (部分選舉未必有資料，可能 0 或 99)」。
    """
    print("\n[單元] 年齡（乾淨值）——0 與 99 的處置不對稱")
    print("       0 不可能是真實年齡 → 任何屆別都留空")
    check("1998 的 0", valid_age("1998", "T2", "0"), "")
    check("2022 的 0", valid_age("2022", "T2", "0"), "")
    # 空白比 0 與 99 更明確地就是無資料，且不可能是年齡。
    # 列入不是為了處理現況（實測 0 筆），是為了移除一個錯誤行為：
    # 不列入的話，具名的五屆出現空白時 check_age_sentinel 會誤中止。
    check("1998 的空白", valid_age("1998", "T2", ""), "")
    check("2022 的空白", valid_age("2022", "T2", ""), "")

    print("\n       99 落在合法年齡值域內 → 只在具名的五屆留空")
    for term in ("1994", "1998", "2002", "2005", "2006"):
        check(f"{term} 的 99", valid_age(term, "T2", "99"), "")
    # 若判準寫成無條件，將來真有 99 歲候選人時他的年齡會被默默吃掉
    check("2022 的 99 原樣保留", valid_age("2022", "T2", "99"), "99")
    check("2014 的 99 原樣保留", valid_age("2014", "T2", "99"), "99")

    print("\n       其餘一律原樣")
    check("1998 的 52", valid_age("1998", "T2", "52"), "52")
    check("2022 的 45", valid_age("2022", "T2", "45"), "45")

    print("\n       兩條前提斷言：不成立即中止")
    # ⚠️ 必須含 1998 D1-MT 的 100：check_age_sentinel 會在
    #    AGE_UNRECORDED_EXTRA 的登記從未被用到時中止，合成資料缺了
    #    那個範圍就會誤中止（而那正是該檢查存在的理由）。
    base = [{"年度": "1998", "選舉種類": "T2", "年齡_原始": "99"},
            {"年度": "1998", "選舉種類": "D1-MT", "年齡_原始": "100"},
            {"年度": "2022", "選舉種類": "T2", "年齡_原始": "45"}]
    check_age_sentinel(base)
    check("前提成立時不中止", True, True)
    # 格式文件把 0 與 99 並列，所以舊屆出現 0 不是異常，不得誤中止
    check_age_sentinel(base + [{"年度": "1998", "選舉種類": "T2", "年齡_原始": "0"}])
    check("列入清單的屆別出現 0 → 不中止", True, True)
    check_age_sentinel(base + [{"年度": "1998", "選舉種類": "T2", "年齡_原始": ""}])
    check("列入清單的屆別出現空白 → 不中止", True, True)

    def with_row(term, raw):
        return lambda: check_age_sentinel(
            base + [{"年度": term, "選舉種類": "T2", "年齡_原始": raw}])

    check_raises("列入清單的屆別出現非無資料值 → 中止", with_row("1998", "52"))
    check_raises("清單外的屆別出現 99 → 中止", with_row("2022", "99"))

    for term, raw in (("1998", "52"), ("2022", "99")):
        try:
            with_row(term, raw)()
            check(f"{term} 應中止", "沒有中止", "中止")
        except ValidationError as exc:
            check(f"{term} 的中止訊息指出屆別", term in str(exc), True)


@reports
def test_age_valid_column_in_output() -> None:
    """乾淨值的規則**有被套用到列組裝**，不只是函式本身正確。

    ⚠️ 這一條是變異測試逼出來的，而且逼了兩次：

    1. 原本只測 `valid_age()`。把列組裝處改成讓 `年齡` 直接抄 `r[10]` 時，
       函式沒被動過所以測試照樣通過——
       **測了規則，沒測規則有沒有被套用。**
    2. 第一次補救是去讀**已建好的**長表。那也抓不到：變異改的是原始碼，
       不會重建長表，讀成品的測試對原始碼變異一律無感。
       這與本檔其他十項「驗證被拿掉」型變異漏網是同一個結構問題。

    所以這裡實際跑一次 `process_one`——合成來源、真的走過列組裝。
    """
    print("\n[單元] process_one 的 年齡／年齡_原始——實際跑列組裝，不是讀成品")

    def one(year: str, age: str) -> dict:
        zf = _synthetic_zip("1000", "1000", "1000", age=age)
        # 與 test_process_one_legacy_decimals 同一套處置：合成檔沒有 folder 那層，
        # 且區域檔指向合成的那一份。用 try/finally 確保不污染其他測試。
        real_year = YEARS[year]
        real_regional = COUNTY_CROSSWALK_YEARS.get(year)
        YEARS[year] = {"quoted": False, "parts": {}}
        COUNTY_CROSSWALK_YEARS[year] = "r"
        try:
            with _synthetic_town_env(year):
                p = process_one(zf, zip_names(zf), year, "T3", "city", "t")
        finally:
            YEARS[year] = real_year
            if real_regional is None:
                COUNTY_CROSSWALK_YEARS.pop(year, None)
            else:
                COUNTY_CROSSWALK_YEARS[year] = real_regional
        return p["candidates"][0]

    print("       舊屆的 99 → 年齡_原始 保留 99、年齡 留空")
    c = one("2002", "99")
    check("2002 的 年齡_原始", c["年齡_原始"], "99")
    check("2002 的 年齡（乾淨）", c["年齡"], "")

    print("\n       舊屆的真實年齡 → 兩欄相同")
    c = one("2002", "45")
    check("2002 的 年齡_原始", c["年齡_原始"], "45")
    check("2002 的 年齡（乾淨）", c["年齡"], "45")

    print("\n       0 在任何屆別都留空")
    c = one("2002", "0")
    check("2002 的 0 → 年齡 留空", c["年齡"], "")
    check("2002 的 0 → 年齡_原始 保留 0", c["年齡_原始"], "0")


@reports
def test_oracles() -> None:
    """每個輸出欄位都必須宣告 oracle，且語意層的值必須合法。

    這組測試守的是「manifest 不腐爛」：新增欄位而未宣告、或把
    project-inferred 偷改成 official-doc，都會在這裡被擋下。
    """
    print("\n[單元] 欄位 oracle 宣告")
    check("三張表都有宣告", set(MANIFEST), {"summary", "candidates", "votes"})
    for t, fields in MANIFEST.items():
        bad = [c for c, d in fields.items() if d["semantic"] not in SEMANTIC_LEVELS]
        check(f"{t} 語意層值域合法", bad, [])
        missing = [c for c, d in fields.items()
                   if not d.get("structure") or "provenance" not in d]
        check(f"{t} 每欄都有 structure 與 provenance", missing, [])
    # 沒有算術 oracle 的欄位數——這個數字本身是專案的已知弱點，釘死它
    n = sum(1 for f in MANIFEST.values() for d in f.values() if not d["arithmetic"])
    # 新增可比性標記 4 欄 × 3 張表 = 12 欄，全部沒有算術 oracle（43 → 55）
    # candidates 新增 `年齡_原始`（來源原值欄，無算術 oracle）：60 → 61
    check("沒有算術 oracle 的欄位數", n, 61)


# ---------------------------------------------------------------- 迴歸測試

# D1-MT 的全國數字。它沒有檔別合計列，故由 187 個鄉鎮市區列加總後釘死。
# 當選人數等於各屆山地鄉數（每鄉選 1 位鄉長）；候選人數與 2026-08-26 清點
# 逐屆記錄的山地鄉候選人列數相同。
MOUNTAIN_NATIONAL = {
    "1998": {"選舉人數": 134728, "投票數": 98611, "投票率": 73.19,
             "候選人數": 85, "當選人數": 30},
    "2002": {"選舉人數": 139445, "投票數": 98142, "投票率": 70.38,
             "候選人數": 72, "當選人數": 30},
    "2005": {"選舉人數": 143597, "投票數": 103588, "投票率": 72.14,
             "候選人數": 80, "當選人數": 30},
    "2009-2010": {"選舉人數": 127275, "投票數": 89681, "投票率": 70.46,
                  "候選人數": 48, "當選人數": 25},
    "2014": {"選舉人數": 125940, "投票數": 101766, "投票率": 80.81,
             "候選人數": 59, "當選人數": 24},
    "2018": {"選舉人數": 128950, "投票數": 103780, "投票率": 80.48,
             "候選人數": 71, "當選人數": 24},
    "2022": {"選舉人數": 130142, "投票數": 100611, "投票率": 77.31,
             "候選人數": 61, "當選人數": 24},
}


def load(name: str) -> list[dict]:
    path = OUT / name
    opener = gzip.open if name.endswith(".gz") else io.open
    with opener(path, "rt", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


@reports
def test_regression() -> None:
    print("\n[迴歸] 2009-2010／2014／2018／2022 四屆的實際輸出")
    report_path = OUT / "validation-report.json"
    if not report_path.exists():
        print("  SKIP  data/processed/ 不存在，請先執行 build_local_election.py")
        skipped.append("regression")
        return

    S = load("cec-local-election-summary-long.csv.gz")
    C = load("cec-local-election-candidates-long.csv")
    V = load("cec-local-election-votes-long.csv.gz")

    check("summary 列數", len(S), EXPECTED["rows"]["summary"])
    check("candidates 列數", len(C), EXPECTED["rows"]["candidates"])
    check("votes 列數", len(V), EXPECTED["rows"]["votes"])

    for name, rows in (("summary", S), ("votes", V)):
        got: dict[str, int] = {}
        for r in rows:
            got[r["層級"]] = got.get(r["層級"], 0) + 1
        check(f"{name} 層級分布", got, EXPECTED[f"levels_{name}"])

    by_yt: dict[str, int] = {}
    for c in C:
        k = f"{c['年度']}|{c['選舉種類']}"
        by_yt[k] = by_yt.get(k, 0) + 1
    check("各屆別選舉種類候選人數", by_yt, EXPECTED["candidates_by_year_type"])

    # 逐屆逐種類重算全國數字（city + prv 相加），不跨種類、不跨屆相加
    for key, want in EXPECTED["national"].items():
        # 屆別與選舉種類【都】可能含連字號（2009-2010、T-COMBO），故用 | 分隔
        year, etype = key.split("|")
        totals = [r for r in S if r["層級"] == "檔別合計"
                  and r["選舉種類"] == etype and r["年度"] == year]
        e = sum(int(r["選舉人數"]) for r in totals)
        v = sum(int(r["投票數"]) for r in totals)
        check(f"{key} 全國選舉人數", e, want["選舉人數"])
        check(f"{key} 全國投票數", v, want["投票數"])
        check(f"{key} 全國投票率", round(100.0 * v / e, 2), want["投票率"])
        cands = [c for c in C
                 if c["選舉種類"] == etype and c["年度"] == year]
        # ⚠️ 兩個釘死值分別對應**不同的欄位**，不可都讀 `當選`：
        #    `當選人數`      = 來源認定（由 elcand 註記推導）
        #    `當選人數_權威值` = 由 elctks 跨檔推導，現存於 `當選`
        #    2005 兩檔正是這兩個數字不同的地方（20 vs 27、18 vs 30）。
        #    若兩項都讀 `當選`，前者會恆等於後者，那個差異就再也看不見。
        check(f"{key} 來源認定的當選人數（含婦女保障）",
              sum(1 for c in cands if c["當選註記"] in ELECTED_MARKS),
              want["當選人數"])
        check(f"{key} 權威值當選人數（含婦女保障）",
              sum(1 for c in cands if c["當選"] == "Y"),
              want["當選人數_權威值"])

    # 版面：2022 與 2018 不同，靠自我驗證分辨。套錯會得到看似合理的錯誤席次。
    got_layout: dict[str, int] = {}
    for r in S:
        k = f"{r['年度']}|{r['版面']}"
        got_layout[k] = got_layout.get(k, 0) + 1
    check("各屆版面分布", got_layout, EXPECTED["layout_by_year"])

    # 婦女保障：'!' 邏輯的真實資料覆蓋
    wq: dict[str, int] = {}
    for c in C:
        if c["當選註記"] == "!":
            k = f"{c['年度']}|{c['選舉種類']}"
            wq[k] = wq.get(k, 0) + 1
    check("婦女保障當選分布", wq, EXPECTED["women_quota"])
    check("婦女保障當選總數", sum(wq.values()), EXPECTED["marks"]["!"])

    # '-'（因婦女保障被排擠未當選）——本專案曾誤稱未出現
    dq: dict[str, int] = {}
    for c in C:
        if c["當選註記"] == "-":
            k = f"{c['年度']}|{c['選舉種類']}"
            dq[k] = dq.get(k, 0) + 1
    check("被排擠未當選分布", dq, EXPECTED["displaced"])
    check("被排擠未當選總數", sum(dq.values()), EXPECTED["marks"]["-"])
    check("被排擠者皆計為未當選",
          {c["當選"] for c in C if c["當選註記"] == "-"}, {"N"})

    marks: dict[str, int] = {}
    for c in C:
        m = c["當選註記"] or " "
        marks[m] = marks.get(m, 0) + 1
    check("當選註記分布", marks, EXPECTED["marks"])

    # 全零列
    # ⚠️ 人口數已改為原樣保留的字串（舊屆含小數），不能用 int()
    zero = [r for r in S if int(r["選舉人數"]) == 0
            and int(r["投票數"]) == 0 and Decimal(r["人口數"]) == 0]
    check("全零列總數", len(zero), EXPECTED["zero_rows"]["total"])
    zt: dict[str, int] = {}
    for r in zero:
        k = f"{r['年度']}|{r['選舉種類']}"
        zt[k] = zt.get(k, 0) + 1
    check("全零列分布", zt,
          {k: v for k, v in EXPECTED["zero_rows"].items() if k != "total"})
    check("沒有『選舉人數 0 卻有票』的列",
          [r for r in zero if int(r["有效票"]) or int(r["無效票"])], [])

    # 投票率：中選會用四捨五入，逐列精確相等
    checked = mism = 0
    for r in S:
        e = int(r["選舉人數"])
        if e == 0 or not r["投票率"]:
            continue
        checked += 1
        got_t = (Decimal(100 * int(r["投票數"])) / Decimal(e)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        if got_t != Decimal(r["投票率"]):
            mism += 1
    check("投票率可重算列數", checked, EXPECTED["turnout_rows_checked"])
    # 不硬寫 0 也不硬寫 1：不符的列數必須【恰好等於】驗證報告中具名記錄的
    # 已知來源異常數。多一列代表出現未記錄的新異常，少一列代表記錄過期。
    report0 = json.loads((OUT / "validation-report.json").read_text(encoding="utf-8"))
    known_turnout = len(report0["已知來源異常_投票率"])
    check("投票率不符列數 = 已具名的來源異常數", mism, known_turnout)
    check("已知投票率異常數", known_turnout, EXPECTED["known_turnout_anomalies"])

    # 個資最小化：這三欄不得出現
    leaked = {"出生日期", "出生地", "學歷"} & set(C[0].keys())
    check("個資欄位未輸出", leaked, set())

    check("當選註記值域",
          set(c["當選註記語意"] for c in C) <= {
              "當選", "未當選", "婦女保障當選", "因婦女保障被排擠未當選"},
          True)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    # 這個清單混了三種形態，逐類型檢查而不是混在一起數
    by_kind: dict[str, list] = {}
    for a in report["已知來源異常_得票加總"]:
        by_kind.setdefault(a["類型"], []).append(a)
    check("已知得票加總類異常的類型與筆數",
          {k: len(v) for k, v in sorted(by_kind.items())},
          EXPECTED["vote_sum_anomaly_kinds"])
    check("「得票加總錯置」的差額必為 0",
          [a["差額合計"] for a in by_kind.get("得票加總錯置", [])],
          [0] * EXPECTED["vote_sum_anomaly_kinds"]["得票加總錯置"])
    check("「鄉鎮市區配錯選舉區」的多重集合必須相同",
          [a["多重集合相同"] for a in by_kind.get("鄉鎮市區配錯選舉區", [])],
          [True] * EXPECTED["vote_sum_anomaly_kinds"]["鄉鎮市區配錯選舉區"])
    check("「elctks 比 elprof 細」都做過向上加總比對",
          [a["向上加總比對的父單位數"] for a in
           by_kind.get("elctks 比 elprof 細", [])],
          [2, 2])
    check("已知當選註記異常數", len(report["已知來源異常_當選註記"]),
          EXPECTED["known_elected_mark_anomalies"])
    # 這份紀錄的全部價值在於「兩邊分別怎麼認定」。若兩個欄位取自同一來源，
    # 它們會恆等，報告仍有 63 筆、長度檢查照樣通過，但已不含任何資訊。
    # 依定義：能進到這份清單就是因為兩邊不一致，所以每一筆都必須相異。
    ema = report["已知來源異常_當選註記"]
    check("異常紀錄的兩側取自不同來源（由註記推導 ≠ 權威值）",
          [a["由註記推導"] == a["權威值"] for a in ema], [False] * len(ema))
    # 再從註記端獨立重算一次：紀錄裡的 `由註記推導` 必須真的等於註記的解讀，
    # 而不是隨便一個與權威值相反的值。
    check("由註記推導 與 elcand當選註記 相符",
          [a["由註記推導"] == ("Y" if a["elcand當選註記"] in ("*", "!") else "N")
           for a in ema], [True] * len(ema))
    check("已知投票數超過選舉人數異常數",
          len(report["已知來源異常_投票數超過選舉人數"]),
          EXPECTED["known_elector_anomalies"])
    check("報告來源 sha256", report["來源檔sha256"], EXPECTED["sha256"])
    check("報告涵蓋屆別選舉種類",
          set(report["各屆別選舉種類全國合計"]),
          set(EXPECTED["national"])
          | {f"{t}|D1-MT" for t in MOUNTAIN_NATIONAL})

    # ---- D1-MT：沒有檔別合計列，數字由鄉鎮市區列加總後釘死 ----
    # ⚠️ 兩邊都要驗：長表加總（實際發布的資料）與報告的衍生彙總
    #    （驗證用的內部值）。只驗一邊的話，兩者脫節時不會有人發現。
    for term, want in sorted(MOUNTAIN_NATIONAL.items()):
        rows = [r for r in S if r["選舉種類"] == "D1-MT" and r["年度"] == term]
        check(f"{term} D1-MT 長表只有鄉鎮市區層級",
              {r["層級"] for r in rows}, {"鄉鎮市區"})
        e = sum(int(r["選舉人數"]) for r in rows)
        v = sum(int(r["投票數"]) for r in rows)
        check(f"{term} D1-MT 選舉人數", e, want["選舉人數"])
        check(f"{term} D1-MT 投票數", v, want["投票數"])
        check(f"{term} D1-MT 投票率", round(100.0 * v / e, 2), want["投票率"])
        cands = [c for c in C
                 if c["選舉種類"] == "D1-MT" and c["年度"] == term]
        check(f"{term} D1-MT 候選人數", len(cands), want["候選人數"])
        check(f"{term} D1-MT 當選人數（每鄉 1 席）",
              sum(1 for c in cands if c["當選"] == "Y"), want["當選人數"])
        check(f"{term} D1-MT 當選人數等於山地鄉數",
              len(rows), want["當選人數"])
        nat = report["各屆別選舉種類全國合計"][f"{term}|D1-MT"]
        check(f"{term} D1-MT 報告與長表加總一致",
              [nat["選舉人數"], nat["投票數"], nat["候選人數"]],
              [e, v, want["候選人數"]])
        check(f"{term} D1-MT 報告記錄了彙總血緣",
              [nat.get("彙總口徑") is not None,
               nat.get("來源完整類型"),
               nat.get("來源原始彙總是否寫入長表"),
               nat.get("長表最細層級")],
              [True, "D1", False, "鄉鎮市區"])



# ═══════════════════════════════════════════════════════════════════
# 無測試守衛的合成髒資料
#
# ⚠️ 這一組存在的理由，用一句話講：**那些守衛在乾淨資料上永遠不觸發，
#    所以把它們改成 `if False:` 之後 pytest 全綠、建置通過、輸出位元組不變。**
#
#    2026-08-22 插樁量測九個判斷式在完整建置中的行為：到達 1–20 次、
#    條件成立 0 次。它們不是死碼（全部執行過），是「這批資料剛好沒發生」。
#    刪掉任何一個，下次來源變壞時就沒人擋。
#
# ⚠️ **只斷言「有拋出 ValidationError」不夠。** 中止的路徑不只一條，
#    專責檢查會被別的檢查掩護——實測第 44 項的第一版合成輸入就是被更早的
#    「候選人複合鍵重複」擋下的。所以 aborts_with() 一律要比對
#    **只有目標檢查會輸出的字串**。
# ═══════════════════════════════════════════════════════════════════
_PARTS_CACHE: dict[tuple, list] = {}

# 探測用的屆別。刻意挑小檔，秒級完成。
#
# 1998／2005 的 T2／T3：涵蓋寶山鄉（投票數 > 選舉人數）與配錯選舉區、跨區移動。
# 1998 的 T-COMBO：**孤兒單位那三條檢查只在 CTKS_DEEPER_THAN_PROF 內的檔跑**，
#   而那個集合只有 1998／2002 的 T-COMBO 直轄市檔。不加它，41／42／45
#   三條的合成輸入會靜默地什麼都沒觸發——因為整段程式根本不執行。
# 1994 的 T-COMBO：第 43 項唯一能觀察到「正規化有沒有生效」的檔——
#   它同時在 DISTRICT_COLUMN_INCONSISTENT 與 KNOWN_ELECTED_MARK_ANOMALIES
#   內，有 2 筆具名的註記不一致。不做正規化時那 2 筆會看不見。
PROBE_PARTS = (("1994", "T-COMBO"),
               ("1998", "T2"), ("1998", "T3"), ("1998", "T-COMBO"),
               ("2005", "T2"), ("2005", "T3"))


def probe_parts() -> list | None:
    """取得探測用的真實 parts。找不到原始壓縮檔時回傳 None。"""
    if not ZIP_PATH.exists():
        return None
    key = PROBE_PARTS
    if key not in _PARTS_CACHE:
        out = []
        with zipfile.ZipFile(ZIP_PATH) as zf:
            names = zip_names(zf)
            for year, etype in PROBE_PARTS:
                for label, sub in YEARS[year]["parts"][etype].items():
                    out.append(process_one(zf, names, year, etype, label, sub))
        _PARTS_CACHE[key] = out
    return _PARTS_CACHE[key]


def part_of(parts: list, year: str, etype: str) -> dict:
    """取出指定（屆別, 選舉種類）的 part。"""
    return next(p for p in parts if (p["year"], p["etype"]) == (year, etype))


def check_raises_msg(label: str, fn, phrase: str) -> None:
    """斷言 fn 丟出 ValidationError 且訊息含 phrase。

    ⚠️ 與既有的 check_raises 不同：那個只驗型別。中止的路徑不只一條時，
       只驗型別會讓專責檢查被別的檢查掩護而假通過。
    """
    try:
        fn()
    except ValidationError as exc:
        if phrase in str(exc):
            print(f"  PASS  {label}")
        else:
            print(f"  FAIL  {label}（中止了，但訊息不含 {phrase!r}）"
                  f"\n          實際：{str(exc)[:110]}")
            failures.append(label)
        return
    print(f"  FAIL  {label}（沒有中止）")
    failures.append(label)


def aborts_with(label: str, mutate, phrase: str) -> None:
    """深拷貝 parts、套用 mutate、跑 cross_validate，斷言中止且訊息含 phrase。

    `phrase` 必須是**只有目標檢查會輸出的字串**——只驗有沒有中止，
    會讓專責檢查被別的檢查掩護而假通過。
    """
    parts = probe_parts()
    if parts is None:
        return
    ps = copy.deepcopy(parts)
    if mutate(ps) is None:
        check(label, "找不到可改的位置", "已套用合成缺陷")
        return
    try:
        cross_validate(ps, [], [], [], [], [])
    except ValidationError as exc:
        if phrase in str(exc):
            print(f"  PASS  {label}")
        else:
            print(f"  FAIL  {label}（中止了，但訊息不含 {phrase!r}）"
                  f"\n          實際：{str(exc)[:110]}")
            failures.append(label)
        return
    print(f"  FAIL  {label}（沒有中止）")
    failures.append(label)


TOWN_PROBE = ("2002", "T3", "city", "2002縣市議員/山原")


def _town_fixture(zf, names):
    """取 2002 山原的 base、對照表與縣市名稱對照，供各項探測共用。

    用 2002 T3 是因為它是四筆 alias 中的三筆所在，且整份檔的鄉鎮名稱
    都被截到 3 字——名稱配對的最壞情況。
    """
    year, etype, _, sub = TOWN_PROBE
    path = f"votedata/votedata/voteData/{sub}/elbase.csv"
    quoted = zf.read(names[path])[:200].lstrip().startswith(b'"')
    base = read_csv(zf, names, path, COLS["elbase"], quoted,
                    KEY_COLS["elbase"])
    crosswalk = load_town_crosswalk()
    county_names = {}
    for b in base:
        if admin_level(list(b[:5]) + [""]) == "直轄市縣市":
            county_names[b[0] + b[1]] = b[5]
    return base, crosswalk, county_names


@reports
def test_town_crosswalk() -> None:
    """鄉鎮市區代碼的跨檔正規化。

    ⚠️ 這一組必須能在乾淨資料上失敗。對照表已把 alias 解開了，
    若建置只查表，alias 的兩條檢查會是永遠不會失敗的程式碼——
    所以建置每次都由來源重新推導，這裡逐一確認那些推導檢查真的擋得住。
    """
    print("\n[單元] 鄉鎮市區代碼跨檔正規化")

    # ---- 對照表本身 ----
    real = load_town_crosswalk()
    # 2026-08-27 加入 1998／2002 的 D1-MT（各 319 列）後由 1,290 增為 1,928；
    # 代碼不同者由 829 增為 1,182（增量 1998 為 230、2002 為 123）。
    check("對照表 1,928 列", len(real), 1928)
    check("代碼與本地不同者 1,182 列",
          sum(1 for k, v in real.items() if k[3] != v), 1182)
    by_file = collections.Counter((k[0], k[1]) for k in real)
    check("逐檔的鄉鎮市區數",
          dict(sorted(by_file.items())),
          {("1998", "T2"): 177, ("1998", "T3"): 226,
           ("2002", "T2"): 211, ("2002", "T3"): 226,
           ("2005", "T2"): 224, ("2005", "T3"): 226,
           ("1998", "D1-MT"): 319, ("2002", "D1-MT"): 319})
    check("宣告值與對照表一致",
          dict(sorted(EXPECTED_TOWN_COUNTS.items())), dict(sorted(by_file.items())))
    check("對照表放在 data/reference/",
          TOWN_CROSSWALK_PATH.parent.name, "reference")
    check("對照表不在輸出目錄底下",
          OUT in TOWN_CROSSWALK_PATH.parents, False)

    # spec 的範例表：兩列可直接當測試值
    check("範例：2002 T3 屏東縣 霧臺鄉 033 → 027",
          real.get(("2002", "T3", "屏東縣", "033")), "027")
    check("範例：2005 T2 花蓮縣 吉安鄉 004 → 004",
          real.get(("2005", "T2", "花蓮縣", "004")), "004")

    # ---- alias 常數 ----
    check("alias 四筆", len(TOWN_NAME_ALIASES), 4)
    check("alias 的鍵",
          sorted(TOWN_NAME_ALIASES),
          [("2002", "T3", "嘉義縣", "里山鄉"),
           ("2002", "T3", "屏東縣", "地門鄉"),
           ("2002", "T3", "臺東縣", "麻里鄉"),
           ("2005", "T3", "臺東縣", "麻里鄉")])
    # ⚠️ 2002 T3 與 2005 T3 都有「麻里鄉」。鍵若不含屆別與選舉種類，
    #    一筆 alias 會同時套用到兩屆。
    check("麻里鄉在兩屆各有一筆",
          sum(1 for k in TOWN_NAME_ALIASES if k[3] == "麻里鄉"), 2)

    # ---- 載入時的四種中止 ----
    def with_csv(text):
        tmp = Path(tempfile.mkdtemp()) / "cw.csv"
        tmp.write_text(text, encoding="utf-8")
        return tmp

    head = ("屆別,選舉種類,縣市名稱,本地鄉鎮代碼,本地鄉鎮名稱,"
            "目標鄉鎮代碼,目標鄉鎮名稱\n")
    row_a = "2002,T3,屏東縣,033,霧臺鄉,027,霧臺鄉\n"
    orig_path = build_local_election.TOWN_CROSSWALK_PATH
    for label, text, phrase in (
        ("載入：無資料列即中止", head, "沒有任何資料列"),
        ("載入：本地鍵重複即中止",
         head + row_a + "2002,T3,屏東縣,033,霧臺鄉,028,瑪家鄉\n", "重複"),
        ("載入：目標鍵重複即中止",
         head + row_a + "2002,T3,屏東縣,034,瑪家鄉,027,霧臺鄉\n",
         "不得對到同一個目標"),
    ):
        build_local_election.TOWN_CROSSWALK_PATH = with_csv(text)
        check_raises_msg(label, load_town_crosswalk, phrase)
    build_local_election.TOWN_CROSSWALK_PATH = (
        Path(tempfile.mkdtemp()) / "不存在.csv")
    check_raises_msg("載入：檔案不存在即中止", load_town_crosswalk,
                     "找不到鄉鎮市區代碼對照表")
    build_local_election.TOWN_CROSSWALK_PATH = orig_path

    # ---- 由來源重新推導時的五條檢查 ----
    if not ZIP_PATH.exists():
        skipped.append("test_town_crosswalk 的來源推導部分")
        print("  SKIP  找不到原始壓縮檔，略過來源推導的探測")
        return

    year, etype, label_, sub = TOWN_PROBE
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zip_names(zf)
        base, crosswalk, county_names = _town_fixture(zf, names)

        def run(mutate, phrase, label):
            b = copy.deepcopy(base)
            cw = dict(crosswalk)
            restore = mutate(b, cw)
            try:
                check_raises_msg(
                    label,
                    lambda: verify_town_crosswalk(
                        zf, names, year, etype, label_, b, cw, county_names),
                    phrase)
            finally:
                if restore is not None:
                    restore()

        # 基準：未變異的輸入必須【不】中止，否則後面的「中止」不能歸因
        got = verify_town_crosswalk(zf, names, year, etype, label_,
                                    base, crosswalk, county_names)
        check("基準：未變異的 2002 T3 通過且回傳（226, 3）", got, (226, 3))

        def m_dupe_target(b, cw):
            orig = build_local_election.regional_town_names

            def patched(zf_, names_, folder):
                out = orig(zf_, names_, folder)
                keys = [k for k in out if (k[0], k[1]) == ("01", "010")]
                if len(keys) >= 2:
                    out[keys[1]] = out[keys[0]]
                return out
            build_local_election.regional_town_names = patched
            return lambda: setattr(
                build_local_election, "regional_town_names", orig)

        run(m_dupe_target, "有兩個名為", "目標端同一縣市內同名即中止")

        def m_one_to_one(b, cw):
            seen = {}
            for r in b:
                if r[4].strip("0") or not (r[1].strip("0") and r[3].strip("0")):
                    continue
                k = (r[0], r[1])
                if k in seen:
                    r[5] = seen[k]
                    return None
                seen[k] = r[5]
            return None

        run(m_one_to_one, "對到同一個目標", "兩個本地鄉鎮對到同一目標即中止")

        def m_unknown_name(b, cw):
            for r in b:
                if r[4].strip("0") or not (r[1].strip("0") and r[3].strip("0")):
                    continue
                r[5] = "火星鄉"
                return None
            return None

        run(m_unknown_name, "查無同名", "目標端查無同名即中止")

        def m_alias_count(b, cw):
            key = ("2002", "T3", "嘉義縣", "里山鄉")
            old = TOWN_NAME_ALIASES[key]
            TOWN_NAME_ALIASES[key] = (old[0], old[1], 2)
            return lambda: TOWN_NAME_ALIASES.__setitem__(key, old)

        run(m_alias_count, "宣告 2 次", "alias 使用次數不符即中止")

        def m_alias_target(b, cw):
            key = ("2002", "T3", "嘉義縣", "里山鄉")
            old = TOWN_NAME_ALIASES[key]
            TOWN_NAME_ALIASES[key] = (old[0], "999", old[2])
            return lambda: TOWN_NAME_ALIASES.__setitem__(key, old)

        run(m_alias_target, "alias 宣告目標代碼", "alias 目標代碼不一致即中止")

        def m_count(b, cw):
            key = ("2002", "T3")
            old = EXPECTED_TOWN_COUNTS[key]
            EXPECTED_TOWN_COUNTS[key] = old + 1
            return lambda: EXPECTED_TOWN_COUNTS.__setitem__(key, old)

        run(m_count, "宣告值為", "鄉鎮市區數與宣告不符即中止")

        def m_stale(b, cw):
            cw[("2002", "T3", "嘉義縣", "018")] = "777"
            return None

        run(m_stale, "已與來源脫節", "對照表與來源脫節即中止")

        # ---- 六個檔在鄉鎮市區以下沒有任何資料 ----
        # 這一條若失敗，代表來源新增了更細的層級，鄉鎮層級的正規化不再足夠：
        # 村里代碼若也是檔內重編的，正規化鄉鎮反而造出「看似能 join 實則錯置」。
        for y, e, s in (("1998", "T2", "1998縣市議員/平原"),
                        ("1998", "T3", "1998縣市議員/山原"),
                        ("2002", "T2", "2002縣市議員/平原"),
                        ("2002", "T3", "2002縣市議員/山原"),
                        ("2005", "T2", "2005縣市議員/平原"),
                        ("2005", "T3", "2005縣市議員/山原")):
            deeper = 0
            for stem in ("elbase", "elprof", "elctks"):
                pth = f"votedata/votedata/voteData/{s}/{stem}.csv"
                q = zf.read(names[pth])[:200].lstrip().startswith(b'"')
                rows = read_csv(zf, names, pth, COLS[stem], q, KEY_COLS[stem])
                deeper += sum(1 for r in rows if r[4].strip("0"))
                if stem != "elbase":
                    deeper += sum(1 for r in rows if r[5].strip("0"))
            check(f"{y} {e} 在鄉鎮市區以下沒有資料", deeper, 0)


@reports
def test_unguarded_source_checks() -> None:
    """為那些在乾淨資料上永不觸發的守衛，各餵一份會觸發它的輸入。"""
    print("\n[單元] 無測試守衛的合成髒資料")
    parts = probe_parts()
    if parts is None:
        print("  SKIP  找不到原始壓縮檔")
        skipped.append("unguarded_source_checks")
        return

    # ⚠️ 基準：未改動的 parts 必須【不】中止。少了這一步，後續每一個
    #    「中止」都可能來自 parts 本身有問題，而不是我們合成的缺陷。
    try:
        cross_validate(copy.deepcopy(parts), [], [], [], [], [])
        print("  PASS  基準：未改動的 parts 通過 cross_validate")
    except ValidationError as exc:
        check("基準：未改動的 parts 通過 cross_validate",
              f"中止：{str(exc)[:80]}", "通過")
        return

    def m_elector(ps):
        """30：未具名的單位投票數 > 選舉人數。"""
        p = part_of(ps, "1998", "T3")
        allow = KNOWN_ELECTOR_ANOMALIES.get(
            (p["year"], p["etype"], p["label"]), set())
        for s in p["summary"]:
            if (admin_level(area_key(s)) == "鄉鎮市區"
                    and area_key(s) not in allow and s["選舉人數"]):
                s["投票數"] = s["選舉人數"] + 1
                return s
        return None

    aborts_with("30 未具名單位的投票數 > 選舉人數", m_elector, "投票數")

    # ── 33：具名單位的上層級也異常 ─────────────────────────────────
    #
    # ⚠️ 第一版合成輸入【被第 30 項攔截】：我把縣市層級列改成投票數超過
    #    選舉人數，但那一列不在具名清單內，所以 #30 先中止，訊息是
    #    「投票數 N > 選舉人數 M」而不是「其上層級」。#33 根本沒執行到。
    #
    #    要到達 #33，那一列必須【也】是具名的——否則 #30 一定先擋下。
    #    所以這裡臨時把上層級加進具名清單。語意上這正是 #33 要守的情況：
    #    「即使該單位已具名放行，它的彙總值也不准被污染」。
    key98 = ("1998", "T3", "city")
    named = KNOWN_ELECTOR_ANOMALIES.get(key98, set())
    upper_key = None
    if named:
        k = next(iter(named))
        upper_key = (k[0], k[1], "00", "000", "0000", "0")

    def m_elector_upper(ps):
        p = part_of(ps, "1998", "T3")
        for s in p["summary"]:
            if area_key(s) == upper_key and s["選舉人數"]:
                s["投票數"] = s["選舉人數"] + 1
                return s
        return None

    if upper_key is None:
        check("33 具名異常單位的上層級也異常", "具名清單是空的", "有具名單位")
    else:
        KNOWN_ELECTOR_ANOMALIES[key98] = named | {upper_key}
        try:
            aborts_with("33 具名異常單位的上層級也異常",
                        m_elector_upper, "其上層級")
        finally:
            KNOWN_ELECTOR_ANOMALIES[key98] = named

    # ── 31 / 34：鄉鎮市區配錯選舉區的兩條相鄰檢查 ─────────────────
    #
    # 兩條都在具名的錯置選舉區上跑，且 31 先執行。要到達 34，合成輸入
    # 必須【改代碼但不改值】——那正是 34 的註解所描述的情況：
    # 「多的那一個若剛好與少的那一個同值，多重集合仍相同」。
    def _misplaced_part(ps):
        """回傳（part, 具名的錯置選舉區集合）。"""
        for p in ps:
            anom = KNOWN_TOWN_ASSIGNMENT_ANOMALIES.get(
                (p["year"], p["etype"], p["label"]))
            if anom and anom.get("districts"):
                return p, anom["districts"]
        return None, None

    def m_multiset(ps):
        """31：把具名選舉區內某個鄉鎮市區的有效票改掉，使多重集合不同。"""
        p, dists = _misplaced_part(ps)
        if p is None:
            return None
        for s in p["summary"]:
            if (s["層級"] == "鄉鎮市區"
                    and area_key(s, with_station=False)[:3] in dists):
                s["有效票"] = s["有效票"] + 1
                return s
        return None

    def m_town_set(ps):
        """34：把某個鄉鎮市區的【代碼】改掉但保留其值，多重集合因此不變。"""
        p, dists = _misplaced_part(ps)
        if p is None:
            return None
        for s in p["summary"]:
            if (s["層級"] == "鄉鎮市區"
                    and area_key(s, with_station=False)[:3] in dists):
                s["鄉鎮市區"] = "999"      # 一個 elctks 不會有的代碼
                return s
        return None

    aborts_with("31 具名選舉區的鄉鎮市區有效票多重集合不同",
                m_multiset, "多重集合不相同")
    aborts_with("34 鄉鎮市區代碼集合差異未具名",
                m_town_set, "代碼集合差異未具名")

    # ── 41 / 42 / 45：孤兒單位的三條檢查 ─────────────────────────
    #
    # ⚠️ 這三條【只在 CTKS_DEEPER_THAN_PROF 內的檔執行】（1998／2002 的
    #    T-COMBO 直轄市）。若探測 parts 不含那個檔，合成輸入會靜默地
    #    什麼都不觸發——整段程式根本不跑，而測試會顯示「沒有中止」。
    ORPHAN = ("1998", "T-COMBO")

    def _orphan_ctx(ps):
        """回傳（part, 孤兒單位鍵清單）。

        ⚠️ 必須【重現】cross_validate 的算法，不能近似：真實程式建鍵前會
           先套 unit()——把 DISTRICT_COLUMN_INCONSISTENT 內的檔的選舉區欄
           壓成 '00'。1998 T-COMBO 正在那個集合裡。第一版用原始 area_key，
           算出來的「孤兒」其實是縣市層級列，三條探測全部打到別的檢查。
        """
        p = part_of(ps, *ORPHAN)
        drop = (p["year"], p["etype"], p["label"]) in DISTRICT_COLUMN_INCONSISTENT

        def unit(k):
            return (k[0], k[1], "00") + tuple(k[3:]) if drop else k

        prof = {unit(area_key(s)) for s in p["summary"]}
        seen: dict[tuple, int] = {}
        for v in p["votes"]:
            k = unit(area_key(v))
            seen[k] = seen.get(k, 0) + v["得票數"]
        return p, [k for k in seen if k not in prof], unit

    def m_orphan_sum(ps):
        """41：孤兒層級的向上加總 ≠ 父單位有效票。"""
        p, orphans, unit = _orphan_ctx(ps)
        if not orphans:
            return None
        target = orphans[0]
        for v in p["votes"]:
            if unit(area_key(v)) == target:
                v["得票數"] = v["得票數"] + 1
                return v
        return None

    def m_orphan_parent(ps):
        """42：孤兒單位的父單位從 elprof 消失。

        ⚠️ 只從 elprof 移除父列【不夠】：那個鍵在 elctks 仍有列，於是父列
           自己變成一個【淺層】孤兒，先觸發第 45 條（層級未深於 elprof）。
           實測踩過。所以 elprof 與 elctks 兩邊都要移除該鍵，
           讓真正的深層孤兒找不到父單位。
        """
        p, orphans, unit = _orphan_ctx(ps)
        if not orphans:
            return None
        k = orphans[0]
        pk = (k[0], k[1], "00", "000", "0000", "0")
        before = len(p["summary"])
        p["summary"] = [s for s in p["summary"] if unit(area_key(s)) != pk]
        p["votes"] = [v for v in p["votes"] if unit(area_key(v)) != pk]
        return None if len(p["summary"]) == before else pk

    def m_orphan_shallow(ps):
        """45：孤兒單位的層級不比 elprof 最深層級更深。

        把 elprof 的最深層級往下推（補一列更深的），孤兒單位就不再更深。
        """
        p, orphans, _u = _orphan_ctx(ps)
        if not orphans:
            return None
        k = orphans[0]
        deeper = dict(p["summary"][0])
        for col, val in zip(("省市", "縣市", "選舉區", "鄉鎮市區", "村里", "投開票所"), k):
            deeper[col] = val
        deeper["層級"] = admin_level(list(k))
        deeper["有效票"] = 0
        deeper["無效票"] = 0
        deeper["投票數"] = 0
        deeper["選舉人數"] = 0
        p["summary"].append(deeper)
        return deeper

    aborts_with("41 孤兒層級的加總 ≠ 父單位有效票",
                m_orphan_sum, "的得票加總")
    aborts_with("42 孤兒單位的父單位不存在於 elprof",
                m_orphan_parent, "不存在於 elprof")
    aborts_with("45 孤兒單位的層級並未深於 elprof 最深層級",
                m_orphan_shallow, "並未深於")

    # ── 43：驗證 7 的鍵必須套用選舉區正規化 ───────────────────────
    #
    # ⚠️ 這一項與其他九項【形態不同】：它不是「拿掉檢查」，是讓檢查
    #    **恆為空轉**。不做正規化時，elcand 的鍵（選舉區 00）與 elctks 的鍵
    #    （選舉區 01）永遠對不上，`ctks_mark.get()` 全部回 None，
    #    那一整段比對一次都不執行——【不會中止，所以「有沒有中止」測不到】。
    #
    # ⚠️ 這一項逼了三次才寫對，兩次都是【測到別的東西】：
    #
    #    第一版：在測試裡自己重寫了一遍 mark_key，斷言「套用正規化對得上 > 0、
    #      不套用 = 0」。那測的是我自己的副本，改建置腳本對它毫無影響。
    #      **測試不可重新實作被測邏輯。**
    #    第二版：斷言 1994 T-COMBO 的 2 筆具名註記異常出現在 cross_validate
    #      收集的清單裡。但那份清單是【驗證 4d（權威值比對）】產出的，
    #      不是驗證 7——改 mark_key 一樣影響不到。
    #
    #    正解：合成一筆【不在具名清單內】的註記不一致，放進一個 drop_district
    #    的檔。正確程式的 mark_key 會對上、發現不一致、因未具名而中止；
    #    變異版的鍵對不上，marks 為 None，那一筆看不見，不會中止。
    #    選 1998 T-COMBO——它是 drop_district 檔且【沒有】具名的註記異常，
    #    所以任何不一致都必須立刻中止，不會被具名清單吸收。
    def m_mark_key(ps):
        """把 elctks 的當選註記由 `*` 換成 `!`——兩者都算當選。

        ⚠️ 這個輸入逼了四次才寫對，前三次都被更早的檢查攔截：
           1. 翻一筆 elcand 註記 → 改變當選人數，撞驗證 4（當選人數不符）。
           2. 對調兩筆 elcand 註記 → 當選人數不變，但撞驗證 4d
              （elcand 註記與權威值不一致）。
           3. 兩者都是「當選與否」層次的改動，而 4d 就是比那個。
           要到達驗證 7，改動必須【不影響當選與否】——4d 只看 Y/N，
           驗證 7 比的是【註記字串本身】。`*` 與 `!` 都是當選，
           所以 4d 通過、驗證 7 看到 {'!'} != {'*'} 而中止。

        ⚠️ 這也說明驗證 7 的辨識範圍比看起來窄：它唯一獨有的能力，
           是分辨兩個都代表當選的不同註記。
        """
        p = part_of(ps, "1998", "T-COMBO")
        for c in p["candidates"]:
            if c["當選註記"] != "*":
                continue
            ck = area_key(c, with_station=False)
            for v in p["votes"]:
                vk = area_key(v, with_station=False)
                same = (vk[0], vk[1]) + tuple(vk[3:]) == (ck[0], ck[1]) + tuple(ck[3:])
                if same and v["號次"] == c["號次"] and v["當選註記"] == "*":
                    v["當選註記"] = "!"
                    return v
        return None

    aborts_with("43 drop_district 檔的註記不一致必須被看見",
                m_mark_key, "當選註記不一致")

    # ── 44：忽略選舉區欄後候選人身分仍須唯一 ─────────────────────
    #
    # ⚠️ 這一條在 derive_elected_authoritative() 內，【不在 cross_validate 上】，
    #    且只在 ignore_district=True 時執行，所以直接呼叫該函式。
    #    它吃的是原始 CSV 列（list）而不是長表的 dict。
    #
    # ⚠️ 第一版合成輸入是「把兩位候選人的五個欄位設成相同」，結果被
    #    cross_validate 更早的「候選人複合鍵重複」擋下——那條看的是含選舉區
    #    的完整鍵。這裡改成直接呼叫，並讓兩人【只有選舉區欄不同】：
    #    含選舉區時兩人不同（不會被複合鍵檢查抓到），去掉選舉區才重複。
    dup_cand = [
        ["01", "000", "01", "000", "0000", "1"] + [""] * 10,
        ["01", "000", "02", "000", "0000", "1"] + [""] * 10,
    ]
    check_raises_msg(
        "44 忽略選舉區欄後候選人身分不唯一",
        lambda: derive_elected_authoritative(dup_cand, [], "合成檔",
                                             ignore_district=True),
        "候選人身分不唯一")
    # 反向：含選舉區欄時兩人是不同的人，不得誤中止。
    try:
        derive_elected_authoritative(dup_cand, [], "合成檔",
                                     ignore_district=False)
        print("  FAIL  44 反向：不忽略選舉區時不該因身分重複中止"
              "（應改為在 elctks 找不到列而中止）")
        failures.append("44 反向")
    except ValidationError as exc:
        check("44 反向：不忽略選舉區時不因身分重複中止",
              "候選人身分不唯一" in str(exc), False)

    # ── 40：選舉區欄只能出現宣告的值 ─────────────────────────────
    #
    # ⚠️ 這一條在 process_one() 內（讀檔後、組裝前），也不在 cross_validate 上。
    #
    #    合成方式不是造假檔，而是【把宣告集合改錯】再對真實檔跑一次——
    #    語意相同（宣告與實際不符即中止），但不必造四個互相一致的來源檔。
    #    選 1998 T-COMBO 直轄市：只有 10 名候選人，秒級完成。
    #
    #    design 的 Open Questions 列了兩個選項（合成 zip／抽出檢查片段），
    #    這是第三個：兩者都不必，且不動被測程式。
    dist_key = ("1998", "T-COMBO", "直轄市")
    saved_decl = DISTRICT_COLUMN_INCONSISTENT.get(dist_key)
    if saved_decl is None:
        check("40 選舉區欄出現未宣告的值", "找不到具名宣告", "有具名宣告")
    else:
        bogus = dict(saved_decl)
        bogus["elctks"] = frozenset({"99"})     # 真實檔是 01，宣告成 99
        DISTRICT_COLUMN_INCONSISTENT[dist_key] = bogus
        try:
            sub = YEARS["1998"]["parts"]["T-COMBO"]["直轄市"]
            with zipfile.ZipFile(ZIP_PATH) as zf:
                check_raises_msg(
                    "40 選舉區欄出現未宣告的值",
                    lambda: process_one(zf, zip_names(zf), "1998",
                                        "T-COMBO", "直轄市", sub),
                    "選舉區欄出現未宣告的值")
        finally:
            DISTRICT_COLUMN_INCONSISTENT[dist_key] = saved_decl


@reports
def test_doc_numbers_match_reality() -> None:
    """文件裡的高風險數字與實際相符，且該檢查本身會失敗。

    ⚠️ **只斷言「目前相符」不夠。** 那樣把 `check_claims()` 整個改成
       `return []` 也會通過——檢查變成一段永遠說 OK 的程式碼。
       所以同時餵一份改壞的文件，斷言它抓得到。

    ⚠️ 這支只驗**數字**，不驗散文是否正確。文件說了什麼、說得對不對，
       仍然只能靠人看——見 HANDOFF 地雷 1u。
    """
    C = check_doc_numbers
    print("\n[真實] 文件數字與實際相符")
    check("目前沒有漂移", C.check_claims(), [])

    # 改壞一份副本，確認抓得到。用副本而不是動真檔——真檔被改壞而
    # 測試中途失敗的話，會留下污染。
    import re as _re
    import shutil as _shutil
    with tempfile.TemporaryDirectory() as d:
        work = pathlib.Path(d)
        (work / "scripts").mkdir()
        _shutil.copy(C.__file__, work / "scripts" / "check_doc_numbers.py")
        for f in ("HANDOFF.md", "README.md"):
            _shutil.copy(C.ROOT / f, work / f)
        _shutil.copytree(C.ROOT / "openspec" / "specs", work / "openspec" / "specs")
        (work / "data" / "processed").mkdir(parents=True)
        _shutil.copy(
            C.ROOT / "data" / "processed" / "cec-local-election-summary-long.csv.gz",
            work / "data" / "processed" / "cec-local-election-summary-long.csv.gz")

        h = work / "HANDOFF.md"
        text = h.read_text(encoding="utf-8")
        broken = _re.sub(r"個能力、\*\*(\d+) 條 Requirement",
                         "個能力、**1 條 Requirement", text, count=1)
        check("變異字串確實有改到", broken != text, True)
        h.write_text(broken, encoding="utf-8")

        # 讓檢查對著改壞的副本跑
        real_root = C.ROOT
        try:
            C.ROOT = work
            problems = C.check_claims()
        finally:
            C.ROOT = real_root
        check("Requirement 數被改壞 → 抓得到",
              any("Requirement 數" in p for p in problems), True)

        # ⚠️ 日期戳「整個不見」這一支要另外餵。只改 Requirement 數的話，
        #    `if not stamps:` 永遠不會被走到——把它改成 `if False:` 完全
        #    看不出差別（變異測試實測到這個漏網）。
        h.write_text(text.replace("**最後更新：2026-08-29。**",
                                  "（本節沒有日期）", 1), encoding="utf-8")
        check("日期戳確實被拿掉", "最後更新：2026-08-29"
              not in h.read_text(encoding="utf-8"), True)
        try:
            C.ROOT = work
            problems = C.check_claims()
        finally:
            C.ROOT = real_root
        check("日期戳整個不見 → 抓得到",
              any("找不到帶日期的「最後更新」" in p for p in problems), True)


def main() -> int:
    # 逐一執行；@reports 會在該組有失敗時丟 AssertionError，
    # 這裡吞掉以便跑完全部並一次列出所有失敗（pytest 則會逐組報失敗）。
    for fn in (test_is_blank, test_admin_level, test_detect_layout,
               test_win_marks, test_read_csv, test_read_csv_keys,
               test_render_csv_deterministic,
               test_custom_election_types, test_comparability_flags,
               test_population_applicability,
               test_process_one_legacy_decimals,
               test_elected_authoritative,
               test_elected_authoritative_aborts,
               test_county_crosswalk, test_town_crosswalk,
               test_legacy_terms,
               test_custom_type_terms,
               test_valid_age, test_age_valid_column_in_output,
               test_oracles, test_regression,
               test_unguarded_source_checks,
               test_mountain_township_selection,
               test_mountain_township_projection,
               test_mountain_age_sentinel_scope,
               test_mountain_not_in_main_sequence,
               test_mountain_codes_table,
               test_mountain_township_level_postcondition,
               test_mountain_codes_generator_guards,
               test_spec_trace_integrity_guards,
               test_doc_numbers_match_reality):
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
        msg += f"（跳過 {len(skipped)} 組迴歸測試）"
    print(msg)
    return 0


# ⚠️ 進入點在檔案【最末】。新增測試函式時一律加在它【之前】——
#    加在後面的話，pytest 照樣通過（它獨立收集模組層級函式），但直接執行
#    會在 main() 參照到尚未定義的名稱時 NameError。兩種執行方式都必須有效。


@reports
def test_mountain_township_selection() -> None:
    """山地鄉篩選的守衛：比對【集合】而不只是數量。

    ⚠️ 這一組必須用合成資料。真實資料正好滿足前提（七屆逐屆吻合），
    所以每一條中止在真實建置上**永遠不會觸發**——那正是它們最容易被
    無聲拿掉的原因。

    ⚠️ 只比對數量會讓三種失效靜默通過，這裡逐一餵一份會觸發的輸入。
    """
    print("\n[單元] 山地鄉篩選——集合相等，不只是數量")
    want = {("09", "007", "010"): "甲鄉",
            ("09", "007", "011"): "乙鄉",
            ("09", "007", "012"): "丙鄉"}
    src = [["09", "007", "00", t, "0000", "0"] + ["0"] * 14
           for t in ("010", "011", "012", "013")]

    check_mountain_township_selection("2022", "L", set(want), want, src)
    check("集合相同 → 不中止", True, True)

    check_raises(
        "少選一個 → 中止",
        lambda: check_mountain_township_selection(
            "2022", "L", {("09", "007", "010"), ("09", "007", "011")},
            want, src))

    # 【數量相同】但成員不同——len() 比對會完全看不到這一種
    swapped = {("09", "007", "010"), ("09", "007", "011"), ("09", "007", "013")}
    check_raises(
        "少選 A 鄉、誤選 B 鄉（數量不變）→ 中止",
        lambda: check_mountain_township_selection("2022", "L", swapped, want, src))
    try:
        check_mountain_township_selection("2022", "L", swapped, want, src)
    except ValidationError as exc:
        check("訊息同時具名多選與少選",
              "013" in str(exc) and "012" in str(exc), True)

    check_raises(
        "對照表缺該屆 → 中止",
        lambda: check_mountain_township_selection("1994", "L", set(), {}, src))

    # 對照表列到、但該屆來源沒有那一列（對照表過期）
    ghost_want = dict(want)
    ghost_want[("09", "007", "099")] = "幽靈鄉"
    check_raises(
        "對照表列到但來源沒有 → 中止",
        lambda: check_mountain_township_selection(
            "2022", "L", set(ghost_want), ghost_want, src))


@reports
def test_mountain_township_projection() -> None:
    """投影層只保留鄉鎮市區層級，且 elcand 的欄數與 elprof/elctks 不同。

    ⚠️ 層級限制不是效能考量。2002／2005 的 elctks 當選註記在村里／投開票所
    層級 100% 帶星號——落選人會被算成當選，而且**不會報錯**。
    """
    print("\n[單元] 山地鄉投影——層級限制與欄數差異")
    keys = {("09", "007", "010")}

    def prof_row(town, vil, sta):
        return ["09", "007", "00", town, vil, sta] + ["0"] * 14

    prof = [prof_row("010", "0000", "0"),      # 鄉鎮市區 → 保留
            prof_row("010", "0001", "0"),      # 村里     → 剔除
            prof_row("010", "0001", "0001"),   # 投開票所 → 剔除
            prof_row("011", "0000", "0")]      # 非山地鄉 → 剔除
    ctks = [r[:6] + ["1", "100", "50.00", "*"] for r in prof]
    # elcand 只有 5 個代碼欄，第 6 欄是【號次】不是投開票所
    cand = [["09", "007", "00", "010", "0000"] + ["1"] + ["x"] * 10,
            ["09", "007", "00", "010", "0001"] + ["2"] + ["x"] * 10,
            ["09", "007", "00", "011", "0000"] + ["3"] + ["x"] * 10]

    np_, nc, nk = project_mountain_townships("2022", "L", prof, cand, ctks, keys)
    check("elprof 只留鄉鎮市區層級的山地鄉", len(np_), 1)
    check("elctks 只留鄉鎮市區層級的山地鄉", len(nk), 1)
    check("elcand 只留鄉鎮市區層級的山地鄉", len(nc), 1)
    check("保留的是正確的鄉", np_[0][3], "010")

    # ⚠️ elcand 用 6 欄判層級會把號次當成投開票所代碼，鄉鎮市區列會被誤剔除。
    #    這一條釘住「兩種欄數分開處理」這件事。
    check("elcand 的號次沒有被當成投開票所代碼", nc[0][5], "1")


@reports
def test_mountain_age_sentinel_scope() -> None:
    """年齡哨兵的具名粒度是（屆別, 選舉種類），不是屆別。

    實測依據：1998 鄉鎮市長檔 827 位候選人中 751 位為 100、76 位為 99
    （整檔無真實年齡）；同屆其他五個檔 100% 用 99。
    """
    print("\n[單元] 年齡哨兵——具名到（屆別, 選舉種類）")
    check("1998 D1-MT 的 100 判為未記載",
          build_local_election.valid_age("1998", "D1-MT", "100"), "")
    check("1998 D1-MT 的 99 仍判為未記載",
          build_local_election.valid_age("1998", "D1-MT", "99"), "")
    # 同屆其他選舉種類不受影響——否則真實的 100 歲會被靜默吃掉
    check("1998 T2 的 100 原樣保留",
          build_local_election.valid_age("1998", "T2", "100"), "100")
    check("2022 D1-MT 的 100 原樣保留",
          build_local_election.valid_age("2022", "D1-MT", "100"), "100")

    ok = [{"年度": "1998", "選舉種類": "D1-MT", "年齡_原始": "100"},
          {"年度": "1998", "選舉種類": "T2", "年齡_原始": "99"}]
    build_local_election.check_age_sentinel(ok)
    check("基準：登記範圍內只有無資料值 → 不中止", True, True)

    check_raises(
        "已登記範圍出現宣告外的值 → 中止",
        lambda: build_local_election.check_age_sentinel(
            ok + [{"年度": "1998", "選舉種類": "D1-MT", "年齡_原始": "52"}]))

    check_raises(
        "登記從未被用到 → 中止",
        lambda: build_local_election.check_age_sentinel(
            [{"年度": "1998", "選舉種類": "T2", "年齡_原始": "99"}]))

    # ⚠️ 「哨兵擴散」那一項以目前的登記會被上面第一項先攔下（1998 在
    #    AGE_UNRECORDED_TERMS 內）。要驗到它自己，必須把登記改到一個
    #    【不屬於】AGE_UNRECORDED_TERMS 的屆別。
    saved = dict(AGE_UNRECORDED_EXTRA)
    try:
        AGE_UNRECORDED_EXTRA.clear()
        AGE_UNRECORDED_EXTRA[("2022", "D1-MT")] = frozenset({"100"})
        base = [{"年度": "2022", "選舉種類": "D1-MT", "年齡_原始": "100"}]
        build_local_election.check_age_sentinel(base)
        check("基準：窄化登記在未列屆別 → 不中止", True, True)
        check_raises(
            "窄化哨兵擴散到同屆其他選舉種類 → 中止",
            lambda: build_local_election.check_age_sentinel(
                base + [{"年度": "2022", "選舉種類": "T2", "年齡_原始": "100"}]))
    finally:
        AGE_UNRECORDED_EXTRA.clear()
        AGE_UNRECORDED_EXTRA.update(saved)


@reports
def test_mountain_not_in_main_sequence() -> None:
    """D1-MT 與 D2 不得接為同一序列，且該保護要【能失敗】。

    ⚠️ 原設計要新增一個「斷言兩者不同序列」的執行期檢查。實際上
    is_main_sequence() 是 `etype not in CUSTOM_ELECTION_TYPES`，
    D1-MT 登記為自訂代碼後那種檢查恆為真、永遠不會失敗。
    這裡改為斷言分類本身——有人把 D1-MT 改列官方代碼時會當場失敗。
    """
    print("\n[單元] D1-MT 不進主序列")
    check("D1-MT 不進主序列", is_main_sequence("D1-MT"), False)
    check("D2 進主序列", is_main_sequence("D2"), True)
    check("D1-MT 登記為自訂代碼", "D1-MT" in CUSTOM_ELECTION_TYPES, True)
    check("D1-MT 不在官方代碼表", "D1-MT" in ELECTION_TYPES, False)
    check("D1-MT 的職位", office_type("D1-MT", "單一"), "山地鄉鄉長")


@reports
def test_mountain_codes_table() -> None:
    """山地鄉代碼對照表的形狀：逐屆列數與鍵唯一。"""
    print("\n[單元] 山地鄉代碼對照表")
    if not MOUNTAIN_CODES_PATH.exists():
        print("  SKIP  找不到對照表")
        skipped.append("mountain_codes_table")
        return
    codes = load_mountain_township_codes()
    expect = {"1998": 30, "2002": 30, "2005": 30,
              "2009-2010": 25, "2014": 24, "2018": 24, "2022": 24}
    check("屆別集合", sorted(codes), sorted(expect))
    for term, n in sorted(expect.items()):
        check(f"{term} 的山地鄉數", len(codes[term]), n)
    check("總列數", sum(len(v) for v in codes.values()), 187)


@reports
def test_mountain_township_level_postcondition() -> None:
    """後置斷言：進入長表的 D1-MT 不得低於鄉鎮市區層級。

    ⚠️ 這一組必須用合成資料。真實輸出全在鄉鎮市區層級，所以中止
    **永遠不會觸發**——那正是它最容易被無聲拿掉的原因。

    ⚠️ 它擋的不是篩選函式（那由 test_mountain_township_projection 驗），
    是「日後有別的路徑把明細列加進長表」。
    """
    print("\n[單元] D1-MT 的層級後置斷言")
    ok_s = [{"選舉種類": "D1-MT", "層級": "鄉鎮市區", "年度": "2022"}]
    ok_c = [{"選舉種類": "D1-MT", "村里": "0000", "年度": "2022"}]
    ok_v = [{"選舉種類": "D1-MT", "層級": "鄉鎮市區", "年度": "2022"}]
    check_mountain_township_level(ok_s, ok_c, ok_v)
    check("基準：全在鄉鎮市區層級 → 不中止", True, True)

    check_raises(
        "summary 出現村里層級 → 中止",
        lambda: check_mountain_township_level(
            ok_s + [{"選舉種類": "D1-MT", "層級": "村里", "年度": "2005"}],
            ok_c, ok_v))
    check_raises(
        "votes 出現投開票所層級 → 中止",
        lambda: check_mountain_township_level(
            ok_s, ok_c,
            ok_v + [{"選舉種類": "D1-MT", "層級": "投開票所", "年度": "2002"}]))
    check_raises(
        "candidates 的村里欄非彙總碼 → 中止",
        lambda: check_mountain_township_level(
            ok_s,
            ok_c + [{"選舉種類": "D1-MT", "村里": "0001", "年度": "2002"}],
            ok_v))

    # ⚠️ 其餘九種選舉種類本來就有村里／投開票所層級，不可被這條誤擋
    check_mountain_township_level(
        ok_s + [{"選舉種類": "T2", "層級": "村里", "年度": "2022"}], ok_c, ok_v)
    check("其他選舉種類的村里列不受影響", True, True)


@reports
def test_mountain_codes_generator_guards() -> None:
    """對照表產生器的四個守衛，各餵一份會觸發它的合成輸入。

    ⚠️ 2026-08-27 實測：其中三個（未命中集合、同名歧義、總列數）在目前的
    真實資料上**拿掉也不會失敗**——條件從未成立。依 HANDOFF 第六節的處置，
    一項都不刪，逐項補合成髒資料。

    ⚠️ 產生器本身不在建置流程內（對照表是建置的輸入），所以它的守衛
    只有這一組測試會咬到。
    """
    import build_mountain_township_codes as G

    print("\n[單元] 山地鄉代碼產生器的守衛")
    G.check_unique_name("2022", "甲鄉", [("09", "007", "010")])
    G.check_hit_count("2022", [1] * 24, [], 24)
    G.check_miss_set("2022", ["烏來區"], {"烏來區": "理由"})
    G.check_total([1] * 187, 187)
    check("基準：四個守衛都不誤中止", True, True)

    def raises_exit(name, fn):
        try:
            fn()
        except SystemExit:
            print(f"  PASS  {name}")
            return
        print(f"  FAIL  {name}（沒有中止）")
        failures.append(name)

    # 全國有十餘個三民里／村，那瑪夏 2008 年前又叫三民鄉——這一條為誤配而存在
    raises_exit("同一名稱對到多個鄉鎮市區代碼 → 中止",
                lambda: G.check_unique_name(
                    "2022", "三民鄉",
                    [("09", "007", "010"), ("10", "003", "022")]))
    raises_exit("逐屆命中數不符 → 中止",
                lambda: G.check_hit_count("2022", [1] * 23, ["x"], 24))
    # ⚠️ 【數量相同】但成員不同——只對數量會完全看不到
    raises_exit("未命中集合不同但數量相同 → 中止",
                lambda: G.check_miss_set(
                    "2022", ["復興鄉"], {"烏來區": "理由"}))
    raises_exit("輸出總列數不符 → 中止",
                lambda: G.check_total([1] * 186, 187))


@reports
def test_spec_trace_integrity_guards() -> None:
    """`@trace` 完整性檢查的四個守衛，各餵一份會觸發它的合成輸入。

    ⚠️ 這一組必須用合成資料。清理後真實資料零死鏈，所以「有死鏈就失敗」
    那條**永遠不會觸發**——把判準從「是否在版控內」改成「檔案是否存在」，
    真實資料上完全看不出差別，而 `scratch/` 下的路徑會全部靜默通過。

    ⚠️ 這支檢查驗的是【路徑指得到】，不是【溯源正確】。剝除死鏈後仍有
    六個檔案各出現在 53–73 個區塊（共 83 個）——見 HANDOFF 地雷。
    """
    C = check_spec_traces

    print("\n[單元] @trace 完整性檢查的守衛")
    entries = [("capA", "Req 1", "scripts/oracles.py"),
               ("capB", "Req 2", "scratch/x.py")]
    tracked = {"scripts/oracles.py"}
    check("只回報未入庫的那一條",
          C.check_traces(entries, tracked),
          [("capB", "Req 2", "scratch/x.py")])
    check("全部入庫時回報空清單",
          C.check_traces(entries[:1], tracked), [])

    # ⚠️ 上面兩條【分辨不出】判準是「是否入庫」還是「檔案是否存在」——
    #    `scratch/x.py` 在磁碟上也不存在，兩種判準給同一個答案。
    #    要分辨，必須用一個【存在但未入庫】的檔案，那正是 scratch/ 的本質。
    probe = C.ROOT / "_trace_probe_tmp.txt"
    try:
        probe.write_text("x", encoding="utf-8")
        rel = probe.name
        check("存在但未入庫 → 仍算違規（判準是版控，不是磁碟）",
              C.check_traces([("capC", "Req 3", rel)], tracked),
              [("capC", "Req 3", rel)])
    finally:
        probe.unlink(missing_ok=True)

    def raises_check(name, fn):
        try:
            fn()
        except C.TraceCheckError:
            print(f"  PASS  {name}")
            return
        print(f"  FAIL  {name}（沒有中止）")
        failures.append(name)

    with tempfile.TemporaryDirectory() as d:
        empty = pathlib.Path(d)
        # ⚠️ 零違規若來自零輸入，與「全部通過」無法分辨——故兩者都要中止。
        #    ⚠️ 而且必須驗【是哪一個守衛】中止的：兩個守衛都丟同一個例外，
        #    只驗「有沒有中止」的話，拿掉前一個守衛時後一個會接住，
        #    測試照樣通過（2026-08-27 變異測試實測到這個漏網）。
        raises_check("找不到任何 spec 檔 → 中止",
                     lambda: C.collect_trace_entries(empty))
        try:
            C.collect_trace_entries(empty)
        except C.TraceCheckError as exc:
            check("中止訊息來自『找不到 spec 檔』那一條",
                  "找不到任何 spec 檔" in str(exc), True)

        spec = empty / "cap" / "spec.md"
        spec.parent.mkdir()
        spec.write_text("# x\n\n### Requirement: A\n內容\n", encoding="utf-8")
        raises_check("有 spec 但無 @trace 區塊 → 中止",
                     lambda: C.collect_trace_entries(empty))
        try:
            C.collect_trace_entries(empty)
        except C.TraceCheckError as exc:
            check("中止訊息來自『找不到 @trace 條目』那一條",
                  "找不到 @trace 條目" in str(exc), True)

    # ⚠️ 取不到版控清單時必須中止，【不可】回退成「檔案是否存在」——
    #    那會讓未入庫的路徑在沒有 git 的環境下靜默通過。
    saved_root = C.ROOT
    try:
        C.ROOT = pathlib.Path("/nonexistent-dir-for-trace-check-test")
        raises_check("取不到版控清單 → 中止", C.tracked_files)
    finally:
        C.ROOT = saved_root


if __name__ == "__main__":
    raise SystemExit(main())
