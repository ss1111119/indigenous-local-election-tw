#!/usr/bin/env python3
"""產生 1998／2002／2005 六個原住民檔的鄉鎮市區代碼對照表。

這六個檔的鄉鎮市區代碼是**檔內重新編號**的：同一個鄉鎮在原住民檔是 007、
在同屆「縣市議員（區域）」檔是 012。實測 1,290 個鄉鎮中有 829 個（64%）
兩邊代碼不同——直接拿原始碼跨檔 join 會**成功執行但對錯行政區**。

配對鍵是（縣市名稱, 鄉鎮市區名稱），不是代碼：1998 與 2002 的**縣市代碼
本身也是檔內重編的**，用代碼當鍵會在第一步就錯。名稱是兩邊唯一共通的東西。

⚠️ 區域檔是**同屆的 canonical target**，不是外部真實性的證明。兩邊一致
只證明它們能對得上，不證明區域檔的代碼就是真實的行政區代碼。

⚠️ 產出的 CSV 是建置的**輸入**，放 `data/reference/` 不是 `data/processed/`。
放進輸出目錄的話，「清空輸出再重跑」會把它一起刪掉。

⚠️ 這支腳本產生的對照表**不是建置時的權威**。建置每次都會重新驗證每一列
（名稱三方一致、一對一、逐檔數量）——對照表若與來源脫節，建置中止而非沿用舊值。

用法：
    python scripts/build_town_crosswalk.py
"""
from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_local_election as B  # noqa: E402

OUT_PATH = ROOT / "data" / "reference" / "cec-town-code-crosswalk-1998-2005.csv"

HEADER = [
    "屆別", "選舉種類", "縣市名稱",
    "本地鄉鎮代碼", "本地鄉鎮名稱",
    "目標鄉鎮代碼", "目標鄉鎮名稱",
]

# 六個待正規化的檔，與同屆的正規化目標。
# 目標一律是「縣市議員（區域）」——它涵蓋全部 23 縣市。
# 「鄉鎮市長」檔只涵蓋 18 個縣市（缺直轄市與省轄市），三個平原檔會落空。
PAIRS = [
    ("1998", "T2", "1998縣市議員/平原", "1998縣市議員/區域"),
    ("1998", "T3", "1998縣市議員/山原", "1998縣市議員/區域"),
    ("2002", "T2", "2002縣市議員/平原", "2002縣市議員/區域"),
    ("2002", "T3", "2002縣市議員/山原", "2002縣市議員/區域"),
    ("2005", "T2", "2005縣市議員/平原", "2005縣市議員/區域"),
    ("2005", "T3", "2005縣市議員/山原", "2005縣市議員/區域"),
]

# 每個檔的鄉鎮市區單位數：唯一真相在 build_local_election，這裡匯入。
# 兩邊各存一份的話，只改一邊時建置與產生器會對不同的數字達成一致。
EXPECTED_TOWNS = B.EXPECTED_TOWN_COUNTS

EXPECTED_TOTAL = 1290
EXPECTED_DIFFERENT = 829


def load_elbase(zf: zipfile.ZipFile, names: dict[str, str],
                folder: str) -> dict[tuple[str, ...], str]:
    """讀一個資料夾的 elbase，回傳 {5 碼 tuple: 名稱}。

    引號旗標由實際內容判定，不依屆別猜——舊屆有帶引號的檔。
    """
    path = f"votedata/votedata/voteData/{folder}/elbase.csv"
    if path not in names:
        raise SystemExit(f"壓縮檔內找不到 {path}")
    quoted = zf.read(names[path])[:200].lstrip().startswith(b'"')
    rows = B.read_csv(zf, names, path, B.COLS["elbase"], quoted,
                      B.KEY_COLS["elbase"])
    return B.build_area_names(rows)


def split_levels(
    mapping: dict[tuple[str, ...], str],
) -> tuple[dict[tuple[str, str, str], str], dict[tuple[str, str], str]]:
    """把 elbase 的對照拆成鄉鎮市區層級與縣市層級。

    ⚠️ elbase 的 5 碼是（省市, 縣市, **選舉區**, 鄉鎮市區, 村里）。
    第 3 碼是選舉區不是鄉鎮市區——索引弄錯會讀出選區名稱。
    """
    towns: dict[tuple[str, str, str], str] = {}
    counties: dict[tuple[str, str], str] = {}
    for (prv, cty, dist, town, vil), name in mapping.items():
        if vil.strip("0"):
            continue
        if cty.strip("0") and town.strip("0"):
            # 同一鄉鎮可能分屬多個選舉區而出現多次，取首見即可——
            # 代碼相同，名稱相同。
            towns.setdefault((prv, cty, town), name)
        elif cty.strip("0") and not dist.strip("0") and not town.strip("0"):
            counties[(prv, cty)] = name
    return towns, counties


def main() -> None:
    if not B.ZIP_PATH.exists():
        raise SystemExit(
            f"找不到 {B.ZIP_PATH}。該檔不入庫，請自 https://data.cec.gov.tw/ 下載。"
        )

    out_rows: list[list[str]] = []
    n_diff = 0
    alias_used: dict[tuple[str, str, str, str], int] = {}

    with zipfile.ZipFile(B.ZIP_PATH) as zf:
        names = B.zip_names(zf)
        for year, etype, folder, ref_folder in PAIRS:
            src_towns, src_counties = split_levels(
                load_elbase(zf, names, folder))
            ref_towns, ref_counties = split_levels(
                load_elbase(zf, names, ref_folder))

            # 目標端以（縣市名稱, 鄉鎮名稱）建索引。同一鍵出現多次即中止——
            # 「恰好一個候選」不可以是靠運氣得到的。
            by_name: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
            for key, town_name in ref_towns.items():
                county_name = ref_counties.get((key[0], key[1]))
                if county_name is None:
                    continue
                by_name.setdefault((county_name, town_name), []).append(key)
            dupes = {k: v for k, v in by_name.items() if len(v) > 1}
            if dupes:
                raise SystemExit(
                    f"{year} {etype} 的目標檔 {ref_folder} 同一縣市內有同名鄉鎮："
                    f"{sorted(dupes)[:5]}"
                )

            seen_targets: dict[tuple[str, str, str], tuple[str, str, str]] = {}
            count = 0
            for key, town_name in sorted(src_towns.items()):
                county_name = src_counties.get((key[0], key[1]))
                if county_name is None:
                    raise SystemExit(
                        f"{year} {etype} 找不到 {key[:2]} 的縣市名稱")
                # 名稱被截斷者走具名 alias。alias 的唯一真相在
                # build_local_election.TOWN_NAME_ALIASES——這裡匯入，不另存一份。
                alias = B.TOWN_NAME_ALIASES.get(
                    (year, etype, county_name, town_name))
                lookup_name = alias[0] if alias else town_name
                lookup = (county_name, lookup_name)
                cands = by_name.get(lookup, [])
                if not cands:
                    raise SystemExit(
                        f"{year} {etype} {county_name}-{town_name} "
                        f"在 {ref_folder} 查無同名鄉鎮。"
                        f"若是名稱被截斷，須加入具名 alias，不可用字串通則推斷。"
                    )
                target = cands[0]
                if alias and target[2] != alias[1]:
                    raise SystemExit(
                        f"{year} {etype} {county_name}-{town_name} 的 alias 宣告"
                        f"目標代碼 {alias[1]}，但 {alias[0]} 在 {ref_folder} "
                        f"的代碼是 {target[2]}"
                    )
                if alias:
                    alias_used[(year, etype, county_name, town_name)] = (
                        alias_used.get(
                            (year, etype, county_name, town_name), 0) + 1)
                if target in seen_targets:
                    raise SystemExit(
                        f"{year} {etype} 兩個本地鄉鎮對到同一個目標 {target}："
                        f"{seen_targets[target]} 與 {key}"
                    )
                seen_targets[target] = key

                if target[2] != key[2]:
                    n_diff += 1
                out_rows.append([
                    year, etype, county_name,
                    key[2], town_name,
                    target[2], ref_towns[target],
                ])
                count += 1

            expected = EXPECTED_TOWNS[(year, etype)]
            if count != expected:
                raise SystemExit(
                    f"{year} {etype} 的鄉鎮市區數為 {count}，宣告值為 {expected}。"
                    f"來源可能換版——請重新普查後更新 EXPECTED_TOWNS。"
                )
            print(f"  {year} {etype}: {count} 個鄉鎮")

    # alias 的使用次數必須恰好等於宣告值。「有被用到」不足以證明它套在
    # 該套的地方——多套一次代表某個合法名稱被誤判，少套代表宣告過期。
    for key, (_, _, expect_n) in B.TOWN_NAME_ALIASES.items():
        got_n = alias_used.get(key, 0)
        if got_n != expect_n:
            raise SystemExit(
                f"alias {key} 的實際使用次數 {got_n} 不等於宣告的 {expect_n}")

    if len(out_rows) != EXPECTED_TOTAL:
        raise SystemExit(
            f"總列數為 {len(out_rows)}，宣告值為 {EXPECTED_TOTAL}")
    if n_diff != EXPECTED_DIFFERENT:
        raise SystemExit(
            f"代碼不同者為 {n_diff}，宣告值為 {EXPECTED_DIFFERENT}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(out_rows)

    print(f"\n寫出 {OUT_PATH.relative_to(ROOT)}")
    print(f"  共 {len(out_rows)} 列，其中 {n_diff} 列的本地代碼與目標代碼不同")


if __name__ == "__main__":
    main()
