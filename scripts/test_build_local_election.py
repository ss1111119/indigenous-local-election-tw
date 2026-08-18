#!/usr/bin/env python3
"""build_local_election.py 的迴歸測試。

分兩類：

1. **單元測試**——直接測 parser 的判斷邏輯（層級判定、版面偵測、CSV 讀取），
   用手寫的最小案例，不需要原始壓縮檔。這些一定會跑。

2. **迴歸測試**——把 2022 年六種選舉的實際輸出數字釘死。需要
   `data/processed/` 已存在（即已跑過建置）；不存在就跳過而非失敗，
   因為原始壓縮檔不入庫，clone 下來的人不一定有。

用法：
    python scripts/test_build_local_election.py
    pytest scripts/test_build_local_election.py     # 兩者皆可
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_local_election import (  # noqa: E402
    COLS,
    ELECTED_MARKS,
    WIN_MARKS,
    ValidationError,
    admin_level,
    detect_layout,
    is_blank,
    read_csv,
    render_csv,
    zip_names,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed"

# 2022 年六種選舉的實際數字。改動 parser 後這些若變了，必須是**刻意**的。
EXPECTED = {
    "rows": {"summary": 71734, "candidates": 1923, "votes": 477589},
    "levels_summary": {
        "檔別合計": 9, "直轄市縣市": 64, "選舉區": 215,
        "鄉鎮市區": 1055, "村里": 21113, "投開票所": 49278,
    },
    "levels_votes": {
        "選舉區": 1677, "鄉鎮市區": 5595, "村里": 134950, "投開票所": 335367,
    },
    "candidates_by_type": {
        "T2": 73, "T3": 80, "D2": 20, "R3": 92, "R2": 134, "T1": 1524,
    },
    # 每個選舉種類的全國數字（city + prv，若有）。
    # ⚠️ 這些【不可跨種類相加】——D2 與 R3 是同一批選民。
    "national": {
        "T2": {"選舉人數": 202477, "投票數": 106573, "候選人數": 73,
               "當選人數": 34, "婦女保障當選人數": 0, "投票率": 52.63},
        "T3": {"選舉人數": 216262, "投票數": 144164, "候選人數": 80,
               "當選人數": 35, "婦女保障當選人數": 0, "投票率": 66.66},
        "D2": {"選舉人數": 31807, "投票數": 23712, "候選人數": 20,
               "當選人數": 6, "婦女保障當選人數": 0, "投票率": 74.55},
        "R3": {"選舉人數": 31803, "投票數": 23712, "候選人數": 92,
               "當選人數": 50, "婦女保障當選人數": 0, "投票率": 74.56},
        # R2 是唯一有婦女保障當選的原住民選舉種類
        "R2": {"選舉人數": 91627, "投票數": 55614, "候選人數": 134,
               "當選人數": 72, "婦女保障當選人數": 2, "投票率": 60.7},
        # T1 為對照組（區域議員），非原住民資料
        "T1": {"選舉人數": 18710006, "投票數": 11445404, "候選人數": 1524,
               "當選人數": 841, "婦女保障當選人數": 4, "投票率": 61.17},
    },
    # 婦女保障當選共 6 席（R2 兩席、T1 四席）。這是 '!' 邏輯的真實資料覆蓋：
    # 只數 '*' 會少算這 6 席，而且建置驗證會抓到（已用變異測試確認）。
    "women_quota_total": 6,
    # 全零列：只出現在 T2／T3，各約 38%。使用者若不排除，
    # 「平均每投開票所多少選舉人」這類問題會低估一半。
    "zero_rows": {"total": 17131, "T2": 8932, "T3": 8199},
    # 投票率逐列精確驗證的列數（中選會用四捨五入，非銀行家捨入）
    "turnout_rows_checked": 54603,
    "sha256": "84740535b1f4a9a8fec8ebfe8f7577889837b7639cd7f5e40ef8826c6ab2f69a",
}

failures: list[str] = []
skipped: list[str] = []


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

def test_is_blank() -> None:
    print("\n[單元] is_blank——補零位數跨檔不一致，'0' 與 '0000' 都代表彙總")
    check("空字串", is_blank(""), True)
    check("'0'", is_blank("0"), True)
    check("'000'", is_blank("000"), True)
    check("'0000'", is_blank("0000"), True)
    check("'0001' 不是彙總", is_blank("0001"), False)
    check("'A001' 不是彙總（跨村里投開票所）", is_blank("A001"), False)


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


# ---------------------------------------------------------------- 迴歸測試

def load(name: str) -> list[dict]:
    path = OUT / name
    opener = gzip.open if name.endswith(".gz") else io.open
    with opener(path, "rt", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def test_regression() -> None:
    print("\n[迴歸] 2022 年六種選舉的實際輸出")
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

    by_type: dict[str, int] = {}
    for c in C:
        by_type[c["選舉種類"]] = by_type.get(c["選舉種類"], 0) + 1
    check("各選舉種類候選人數", by_type, EXPECTED["candidates_by_type"])

    # 逐一選舉種類重算全國數字（city + prv 相加），不跨種類相加
    for etype, want in EXPECTED["national"].items():
        totals = [
            r for r in S
            if r["層級"] == "檔別合計" and r["選舉種類"] == etype
        ]
        e = sum(int(r["選舉人數"]) for r in totals)
        v = sum(int(r["投票數"]) for r in totals)
        check(f"{etype} 全國選舉人數", e, want["選舉人數"])
        check(f"{etype} 全國投票數", v, want["投票數"])
        check(f"{etype} 全國投票率", round(100.0 * v / e, 2), want["投票率"])
        cands = [c for c in C if c["選舉種類"] == etype]
        check(f"{etype} 當選人數（含婦女保障）",
              sum(1 for c in cands if c["當選"] == "Y"), want["當選人數"])
        check(f"{etype} 婦女保障當選人數",
              sum(1 for c in cands if c["當選註記"] == "!"),
              want["婦女保障當選人數"])

    # '!' 邏輯的真實資料覆蓋——2022 T2 單獨一種選舉時無法測到這條
    check("婦女保障當選總數",
          sum(1 for c in C if c["當選註記"] == "!"),
          EXPECTED["women_quota_total"])

    # 全零列——T2／T3 特有，佔各該種類約 38%
    zero = [r for r in S if int(r["選舉人數"]) == 0
            and int(r["投票數"]) == 0 and int(r["人口數"]) == 0]
    check("全零列總數", len(zero), EXPECTED["zero_rows"]["total"])
    zt: dict[str, int] = {}
    for r in zero:
        zt[r["選舉種類"]] = zt.get(r["選舉種類"], 0) + 1
    check("全零列只出現在 T2/T3", set(zt), {"T2", "T3"})
    for et in ("T2", "T3"):
        check(f"{et} 全零列數", zt[et], EXPECTED["zero_rows"][et])
    check("沒有『選舉人數 0 卻有票』的列",
          [r for r in zero if int(r["有效票"]) or int(r["無效票"])], [])

    # 投票率：中選會用四捨五入，逐列精確相等
    from decimal import Decimal, ROUND_HALF_UP
    checked = mism = 0
    for r in S:
        e = int(r["選舉人數"])
        if e == 0 or not r["投票率"]:
            continue
        checked += 1
        got = (Decimal(100 * int(r["投票數"])) / Decimal(e)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        if got != Decimal(r["投票率"]):
            mism += 1
    check("投票率可重算列數", checked, EXPECTED["turnout_rows_checked"])
    check("投票率不符列數（四捨五入）", mism, 0)

    # 個資最小化：這三欄不得出現
    leaked = {"出生日期", "出生地", "學歷"} & set(C[0].keys())
    check("個資欄位未輸出", leaked, set())

    # 當選註記只能是官方定義的四種語意
    check("當選註記值域",
          set(c["當選註記語意"] for c in C) <= {
              "當選", "未當選", "婦女保障當選", "因婦女保障被排擠未當選"},
          True)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    check("報告來源 sha256", report["來源檔sha256"], EXPECTED["sha256"])
    check("報告涵蓋選舉種類",
          set(report["各選舉種類全國合計"]), set(EXPECTED["national"]))


def main() -> int:
    test_is_blank()
    test_admin_level()
    test_detect_layout()
    test_win_marks()
    test_read_csv()
    test_render_csv_deterministic()
    test_regression()

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


if __name__ == "__main__":
    raise SystemExit(main())
