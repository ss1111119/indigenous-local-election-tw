#!/usr/bin/env python3
"""建立中選會行政區代碼與內政部標準代碼的對照表（crosswalk）。

回答一個具體問題：**拿本專案的選舉資料，能不能 join 到內政部的圖資與人口統計？**

結論（2022 年資料實測）：能，但**必須用代碼 join，不能用名稱 join**。
- 鄉鎮市區層級：368 / 368 完全對上（100%）
- 村里層級：7,725 / 7,735 對上（99.87%）
- 名稱則有 265 列含私用區（PUA）字元，用名稱比對會失敗

對應規則（官方格式文件已明載，本專案實測確認）：

    鄉鎮市區  CEC 省市 + 縣市 + 鄉鎮市區          = MOI TOWNCODE（8 碼）
    村里      上述 + CEC 村里碼去掉第 1 碼        = MOI 村里代碼（11 碼）

村里碼「第 1 碼為 0、其後 3 碼採內政部戶役政村里代碼」是格式文件的原文；
跨多村里的投開票所由中選會另行自訂代碼，那些不存在於內政部（實測 8 筆，皆在連江縣）。

用法：
    python scripts/build_crosswalk.py [內政部界圖目錄]

預設讀相鄰專案 indigenous-constitution-tw/data/raw/ 的界圖壓縮檔。
那兩個檔約 16MB 且非本專案下載，故不納入本版本庫；本腳本的**產出**才入庫。
"""

from __future__ import annotations

import csv
import io
import json
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "processed"

# 內政部界圖與人口資料的預設位置（相鄰專案）。可用第一個命令列參數覆寫。
DEFAULT_MOI_DIR = ROOT.parent / "indigenous-constitution-tw" / "data" / "raw"
TOWN_ZIP = "moi-township-boundary-1140318.zip"
COUNTY_ZIP = "moi-county-boundary-1140318.zip"
POP_JSON = "moi-odrp013-population-by-indigenous-status-11506.json"


class CrosswalkError(Exception):
    """對照失敗。中止而不是輸出半套對照表。"""


def read_dbf(zip_path: Path, member: str) -> list[dict]:
    """讀 shapefile 的 .dbf 屬性表。編碼依同名 .CPG 宣告。"""
    with zipfile.ZipFile(zip_path) as z:
        raw = z.read(member)
        cpg_name = member.rsplit(".", 1)[0] + ".CPG"
        enc = "cp950"
        if cpg_name in z.namelist():
            cpg = z.read(cpg_name).decode("ascii", errors="replace").strip()
            if "utf" in cpg.lower():
                enc = "utf-8"

    n_rec, hdr_len, rec_len = struct.unpack("<IHH", raw[4:12])
    fields, off = [], 32
    while raw[off] != 0x0D:
        fd = raw[off:off + 32]
        fields.append((fd[:11].split(b"\0")[0].decode("ascii"), fd[16]))
        off += 32

    rows = []
    for i in range(n_rec):
        q = hdr_len + i * rec_len + 1
        rec = {}
        for name, length in fields:
            rec[name] = raw[q:q + length].decode(enc, errors="replace").strip()
            q += length
        rows.append(rec)
    return rows


def has_pua(text: str) -> bool:
    """是否含 Unicode 私用區字元。

    中選會的行政區名稱與候選人姓名含 Big5 遺留的 PUA 碼位（如 U+E02D 即「廍」），
    多數字型沒有字形，看起來像少了一個字。內政部的資料也有（如 U+FFFA8）。
    這是**名稱比對必然失敗**的原因，也是必須用代碼 join 的原因。
    """
    return any(0xE000 <= ord(c) <= 0xF8FF or 0xF0000 <= ord(c) <= 0x10FFFD
               for c in text)


def load_cec() -> tuple[dict, dict]:
    """從本專案輸出取出鄉鎮市區與村里層級的行政區代碼。"""
    path = OUT_DIR / "cec-local-election-summary-long.csv.gz"
    if not path.exists():
        raise CrosswalkError(
            f"找不到 {path}。請先執行 scripts/build_local_election.py。"
        )
    import gzip
    with gzip.open(path, "rt", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    towns, villages = {}, {}
    for r in rows:
        code = r["省市"] + r["縣市"] + r["鄉鎮市區"]
        if r["層級"] == "鄉鎮市區":
            towns.setdefault(code, r["行政區名稱"])
        elif r["層級"] == "村里":
            villages.setdefault((code, r["村里"]), r["行政區名稱"])
    return towns, villages


def main() -> None:
    moi_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MOI_DIR
    for f in (TOWN_ZIP, COUNTY_ZIP, POP_JSON):
        if not (moi_dir / f).exists():
            raise SystemExit(
                f"找不到 {moi_dir / f}。\n"
                f"內政部界圖與人口資料非本專案下載，不納入本版本庫。\n"
                f"請指定其所在目錄：python scripts/build_crosswalk.py <目錄>"
            )

    town = read_dbf(moi_dir / TOWN_ZIP, "TOWN_MOI_1140318.dbf")
    county = read_dbf(moi_dir / COUNTY_ZIP, "COUNTY_MOI_1140318.dbf")
    pop = json.loads((moi_dir / POP_JSON).read_text(encoding="utf-8"))
    moi_town = {t["TOWNCODE"]: (t["COUNTYNAME"], t["TOWNNAME"]) for t in town}
    moi_county = {c["COUNTYCODE"]: c["COUNTYNAME"] for c in county}
    moi_village = {r["district_code"]: (r["site_id"], r["village"])
                   for r in pop["data"]}

    cec_towns, cec_villages = load_cec()

    rows: list[dict] = []
    stats: dict[str, int] = {}

    def bump(k: str) -> None:
        stats[k] = stats.get(k, 0) + 1

    for code, name in sorted(cec_towns.items()):
        moi = moi_town.get(code)
        if moi is None:
            status, moi_name = "查無對應", ""
        elif moi[1] != name:
            status, moi_name = "代碼相符但名稱不同", moi[1]
        else:
            status, moi_name = "完全相符", moi[1]
        bump(f"鄉鎮市區/{status}")
        rows.append({
            "層級": "鄉鎮市區",
            "cec_省市": code[:2], "cec_縣市": code[2:5],
            "cec_鄉鎮市區": code[5:8], "cec_村里": "",
            "cec_名稱": name,
            "moi_代碼": code if moi else "",
            "moi_名稱": moi_name,
            "moi_縣市": moi_county.get(code[:5], ""),
            "比對狀態": status,
            "名稱含私用區字元": "Y" if has_pua(name) or has_pua(moi_name) else "N",
        })

    for (town_code, vil), name in sorted(cec_villages.items()):
        # 跨多村里的投開票所由中選會自訂代碼，不存在於內政部
        self_defined = not vil[1:].isdigit()
        code = town_code + vil[1:]
        moi = moi_village.get(code)
        if self_defined:
            status, moi_name = "中選會自訂（跨村里投開票所）", ""
        elif moi is None:
            status, moi_name = "查無對應", ""
        elif moi[1] != name:
            status, moi_name = "代碼相符但名稱不同", moi[1]
        else:
            status, moi_name = "完全相符", moi[1]
        bump(f"村里/{status}")
        rows.append({
            "層級": "村里",
            "cec_省市": town_code[:2], "cec_縣市": town_code[2:5],
            "cec_鄉鎮市區": town_code[5:8], "cec_村里": vil,
            "cec_名稱": name,
            "moi_代碼": code if moi else "",
            "moi_名稱": moi_name,
            "moi_縣市": moi_county.get(town_code[:5], ""),
            "比對狀態": status,
            "名稱含私用區字元": "Y" if has_pua(name) or has_pua(moi_name) else "N",
        })

    # 鄉鎮市區層級必須 100% 對上——若不成立，代表對應規則的前提已改變
    if stats.get("鄉鎮市區/查無對應", 0):
        raise CrosswalkError(
            f"有 {stats['鄉鎮市區/查無對應']} 個鄉鎮市區代碼在內政部界圖中查無對應。"
            f"「CEC 省市+縣市+鄉鎮市區 = MOI TOWNCODE」這條規則可能已不成立。"
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    (OUT_DIR / "cec-moi-crosswalk.csv").write_bytes(
        buf.getvalue().encode("utf-8-sig")
    )

    report = {
        "說明": (
            "中選會行政區代碼與內政部標準代碼的對照。"
            "對應規則：鄉鎮市區為 CEC 省市+縣市+鄉鎮市區 = MOI TOWNCODE(8碼)；"
            "村里為前述再接 CEC 村里碼去掉第 1 碼 = MOI 村里代碼(11碼)。"
        ),
        "⚠️ 必須用代碼 join": (
            "CEC 與 MOI 的名稱都含 Unicode 私用區字元（Big5 遺留，如 U+E02D 即「廍」），"
            "多數字型無字形。用名稱比對必然失敗，用代碼則 99.87% 對上。"
        ),
        "⚠️ 時間基準不同": (
            "內政部界圖為 1140318、人口為 11506（2026-06），"
            "選舉為 2022-11。期間的行政區改制會造成少數對不上。"
        ),
        "內政部來源": {
            "鄉鎮市區界圖": TOWN_ZIP, "縣市界圖": COUNTY_ZIP,
            "村里人口": POP_JSON,
            "取得方式": "非本專案下載，來自相鄰專案 indigenous-constitution-tw",
        },
        "比對結果": stats,
        "總列數": len(rows),
    }
    (OUT_DIR / "crosswalk-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"對照表 {len(rows):,} 列")
    for k in sorted(stats):
        print(f"  {k:<38} {stats[k]:>6,}")
    pua = sum(1 for r in rows if r["名稱含私用區字元"] == "Y")
    print(f"  名稱含私用區字元（不可用名稱 join）      {pua:>6,}")


if __name__ == "__main__":
    main()
