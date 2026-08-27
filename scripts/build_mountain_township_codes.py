#!/usr/bin/env python3
"""產生山地鄉的逐屆行政區代碼對照表。

為什麼需要它：山地鄉名單（`data/reference/mountain-township-list.csv`）記的是
**名稱**，而名稱在這批來源上對不起來——直接拿公告原文比對只命中 24／30。
六個未命中全是名稱問題：霧台↔霧臺異體字、烏來等五個公告寫 2010 改制後的
「區」而該屆仍是「鄉」、那瑪夏在 2008 年前叫三民鄉。

更嚴重的是誤配：全國有十餘個三民里／村，只用名稱比對會撈到別的行政區。

因此建置期**一律用（省市, 縣市, 鄉鎮市區）代碼三元組**，名稱只出現在這支
產生器裡。產出的 CSV 是建置的**輸入**，放 `data/reference/` 不是
`data/processed/`——放進輸出目錄的話，「清空輸出再重跑」會把它一起刪掉。

⚠️ 名稱變體一律**具名宣告**，不用字串通則（例如全面把「台」換成「臺」）。
通則會讓第七個特例出現時靜默漏撈；具名宣告會在使用次數不符時中止。

⚠️ 逐屆記錄而非單一快照：省市碼 1998／2002＝`03`、2005＝`01`、
2009-2010＝`03`／`04`、2014 起＝`09`／`10`，且 2009 與 2014 起的缺額成因不同
（前者所屬縣正在改制而未參選，後者改制為直轄市原住民區改列 D2）。

用法：
    python scripts/build_mountain_township_codes.py
"""
from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_local_election as B  # noqa: E402

LIST_PATH = ROOT / "data" / "reference" / "mountain-township-list.csv"
OUT_PATH = ROOT / "data" / "reference" / "mountain-township-codes.csv"

HEADER = ["屆別", "省市", "縣市", "鄉鎮市區", "山地鄉名", "來源屆名稱", "備註"]

# 屆別 → 壓縮檔內的 D1（鄉鎮市長）資料夾。
# ⚠️ 資料夾名逐屆不同且不可由命名慣例推導，此處為實際開啟壓縮檔確認的結果。
#    2022 起子資料夾改用選舉種類代碼（D1），2014／2018 為中文名，
#    2009-2010 在合併檔內，1998／2002／2005 無子目錄。
D1_FOLDERS = {
    "1998": "1998鄉鎮市長",
    "2002": "2002鄉鎮市長選舉",
    "2005": "2005鄉鎮市長",
    "2009-2010": "20091205-縣市長縣市議員及鄉鎮長/鄉鎮市長",
    "2014": "2014-103年地方公職人員選舉/縣市鄉鎮市長",
    "2018": "2018-107年地方公職人員選舉/縣市鄉鎮市長",
    "2022": "2022-111年地方公職人員選舉/D1",
}

# 逐屆預期命中數。來源：`docs/schema/山地鄉鄉長資料清點.md` 第七之二節，
# 2026-08-26 第二輪重新實測，與第一輪記載一致。
EXPECTED_HITS = {
    "1998": 30, "2002": 30, "2005": 30,
    "2009-2010": 25, "2014": 24, "2018": 24, "2022": 24,
}

# 名稱變體：(屆別, 名單上的公告原文名) → 該屆來源實際使用的名稱。
# 每一筆都必須被用到恰好一次，否則中止——「有被用到」不足以證明它套在該套的
# 地方，多套一次代表某個合法名稱被誤判，少套代表宣告過期。
NAME_ALIASES = {
    # 異體字：公告寫霧台鄉，中選會七屆皆寫霧臺鄉。
    ("1998", "霧台鄉"): "霧臺鄉",
    ("2002", "霧台鄉"): "霧臺鄉",
    ("2005", "霧台鄉"): "霧臺鄉",
    ("2009-2010", "霧台鄉"): "霧臺鄉",
    ("2014", "霧台鄉"): "霧臺鄉",
    ("2018", "霧台鄉"): "霧臺鄉",
    ("2022", "霧台鄉"): "霧臺鄉",
    # 公告用 2010 五都改制後的「區」名，但這三屆該地仍是「鄉」。
    ("1998", "烏來區"): "烏來鄉", ("2002", "烏來區"): "烏來鄉",
    ("2005", "烏來區"): "烏來鄉",
    ("1998", "和平區"): "和平鄉", ("2002", "和平區"): "和平鄉",
    ("2005", "和平區"): "和平鄉",
    ("1998", "桃源區"): "桃源鄉", ("2002", "桃源區"): "桃源鄉",
    ("2005", "桃源區"): "桃源鄉",
    ("1998", "茂林區"): "茂林鄉", ("2002", "茂林區"): "茂林鄉",
    ("2005", "茂林區"): "茂林鄉",
    # 那瑪夏在 2008 年才由三民鄉改名，這三屆的來源寫三民鄉。
    ("1998", "那瑪夏區"): "三民鄉", ("2002", "那瑪夏區"): "三民鄉",
    ("2005", "那瑪夏區"): "三民鄉",
}

# 逐屆預期未命中的山地鄉，及其成因。成因不同的缺額不可混為一談——
# 把它們畫成同一條折線會被讀成「山地鄉鄉長席次逐屆減少」，那不是事實。
EXPECTED_MISSES = {
    "1998": {},
    "2002": {},
    "2005": {},
    "2009-2010": {
        "烏來區": "所屬臺北縣正併入直轄市，未參加 2009-12-05 這一輪",
        "和平區": "所屬臺中縣正併入直轄市，未參加 2009-12-05 這一輪",
        "桃源區": "所屬高雄縣正併入直轄市，未參加 2009-12-05 這一輪",
        "茂林區": "所屬高雄縣正併入直轄市，未參加 2009-12-05 這一輪",
        "那瑪夏區": "所屬高雄縣正併入直轄市，未參加 2009-12-05 這一輪",
    },
}
_REORGANISED = {
    "烏來區": "自本屆起為直轄市山地原住民區，改列 D2",
    "復興鄉": "自本屆起為直轄市山地原住民區，改列 D2",
    "和平區": "自本屆起為直轄市山地原住民區，改列 D2",
    "桃源區": "自本屆起為直轄市山地原住民區，改列 D2",
    "茂林區": "自本屆起為直轄市山地原住民區，改列 D2",
    "那瑪夏區": "自本屆起為直轄市山地原住民區，改列 D2",
}
for _t in ("2014", "2018", "2022"):
    EXPECTED_MISSES[_t] = dict(_REORGANISED)

EXPECTED_TOTAL = sum(EXPECTED_HITS.values())  # 187


def check_unique_name(term: str, lookup: str, cands: list) -> None:
    """同一名稱不得對到多個鄉鎮市區代碼。

    ⚠️ 「恰好一個候選」不可以是靠運氣得到的。全國有十餘個三民里／村，
    那瑪夏 2008 年前又叫三民鄉——這一條就是為那個誤配存在的。
    """
    if len(cands) > 1:
        raise SystemExit(
            f"{term} 的 {lookup} 在 elbase 對到 {len(cands)} 個"
            f"鄉鎮市區代碼：{cands}。名稱不足以識別，須改以具名代碼指定。")


def check_hit_count(term: str, hits: list, misses: list, expected: int) -> None:
    """逐屆命中數必須等於宣告值。"""
    if len(hits) != expected:
        raise SystemExit(
            f"{term} 命中 {len(hits)} 個山地鄉，宣告值為 {expected}。"
            f"未命中：{misses}。來源或名單可能換版——"
            f"請重新清點後更新 EXPECTED_HITS，不可調降判準。")


def check_miss_set(term: str, misses: list, expected: dict) -> None:
    """未命中的【集合】必須與宣告相符，不只是數量。

    ⚠️ 只對數量的話，「這一屆少了 A 鄉、卻多缺了 B 鄉」會靜默通過，
    而兩者的成因（改制未參選 vs 改列 D2）完全不同。
    """
    if set(misses) != set(expected):
        raise SystemExit(
            f"{term} 的未命中集合為 {sorted(misses)}，"
            f"宣告值為 {sorted(expected)}。"
            f"缺額成因必須逐項具名，不可只對數量。")


def check_total(rows: list, expected: int) -> None:
    """輸出總列數必須等於各屆宣告值之和。"""
    if len(rows) != expected:
        raise SystemExit(f"總列數為 {len(rows)}，宣告值為 {expected}")


def load_mountain_list() -> list[str]:
    """讀山地鄉名單，回傳 30 個公告原文名。"""
    names = []
    with LIST_PATH.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["類別"].strip() == "山地鄉":
                names.append(row["鄉鎮市區_公告原文"].strip())
    if len(names) != 30:
        raise SystemExit(
            f"{LIST_PATH.name} 的山地鄉數為 {len(names)}，預期 30。"
            f"名單換版須重新普查後更新本腳本的宣告值。")
    if len(set(names)) != len(names):
        raise SystemExit(f"{LIST_PATH.name} 的山地鄉名有重複")
    return names


def town_index(zf, names, folder):
    """回傳（{(省市,縣市,鄉鎮市區): 名稱}, {縣市名稱→該縣市代碼}）。

    ⚠️ elbase 的 5 碼是（省市, 縣市, **選舉區**, 鄉鎮市區, 村里）。
    第 3 碼是選舉區不是鄉鎮市區——索引弄錯會讀出選區名稱。
    """
    path = f"votedata/votedata/voteData/{folder}/elbase.csv"
    if path not in names:
        raise SystemExit(f"壓縮檔內找不到 {path}")
    quoted = zf.read(names[path])[:200].lstrip().startswith(b'"')
    rows = B.read_csv(zf, names, path, B.COLS["elbase"], quoted,
                      B.KEY_COLS["elbase"])
    mapping = B.build_area_names(rows)
    towns, counties = {}, {}
    for (prv, cty, dist, town, vil), name in mapping.items():
        if vil.strip("0"):
            continue
        if cty.strip("0") and town.strip("0"):
            towns.setdefault((prv, cty, town), name)
        elif cty.strip("0") and not dist.strip("0") and not town.strip("0"):
            counties[(prv, cty)] = name
    return towns, counties


def main() -> None:
    if not B.ZIP_PATH.exists():
        raise SystemExit(
            f"找不到 {B.ZIP_PATH}。該檔不入庫，"
            f"請自 https://data.cec.gov.tw/ 下載。")

    listed = load_mountain_list()
    out_rows: list[list[str]] = []
    alias_used: dict[tuple[str, str], int] = {}

    with zipfile.ZipFile(B.ZIP_PATH) as zf:
        names = B.zip_names(zf)
        for term, folder in D1_FOLDERS.items():
            towns, _counties = town_index(zf, names, folder)

            # 以名稱建反向索引。同名出現多次即中止——「恰好一個候選」
            # 不可以是靠運氣得到的。全國有十餘個三民里／村，正是這個風險。
            by_name: dict[str, list[tuple[str, str, str]]] = {}
            for key, name in towns.items():
                by_name.setdefault(name, []).append(key)

            hits, misses = [], []
            for listed_name in listed:
                alias = NAME_ALIASES.get((term, listed_name))
                lookup = alias if alias else listed_name
                cands = by_name.get(lookup, [])
                check_unique_name(term, lookup, cands)
                if not cands:
                    misses.append(listed_name)
                    continue
                if alias:
                    alias_used[(term, listed_name)] = (
                        alias_used.get((term, listed_name), 0) + 1)
                key = cands[0]
                note = f"公告原文作「{listed_name}」" if alias else ""
                hits.append([term, key[0], key[1], key[2],
                             listed_name, lookup, note])

            check_hit_count(term, hits, misses, EXPECTED_HITS[term])
            check_miss_set(term, misses, EXPECTED_MISSES[term])
            # ⚠️ 未參選者【不】寫進對照表。這張表是建置期的代碼查詢輸入，
            #    代碼欄為空的列不是查詢對象，混進去只會讓空字串變成看似合法的鍵。
            #    缺額的成因由上面的 EXPECTED_MISSES 強制，並記於
            #    docs/schema/山地鄉鄉長資料清點.md。
            out_rows.extend(hits)
            print(f"  {term}: 命中 {len(hits)}，未參選 {len(misses)}")

    # alias 的使用次數必須恰好等於宣告的屆別數。少用代表宣告過期，
    # 多用代表某個合法名稱被誤判成變體。
    for key in NAME_ALIASES:
        if alias_used.get(key, 0) != 1:
            raise SystemExit(
                f"名稱變體 {key} 的使用次數為 {alias_used.get(key, 0)}，預期 1。"
                f"宣告可能過期或誤套。")

    check_total(out_rows, EXPECTED_TOTAL)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(out_rows)

    print(f"\n寫出 {OUT_PATH.relative_to(ROOT)}")
    print(f"  共 {len(out_rows)} 列")


if __name__ == "__main__":
    main()
