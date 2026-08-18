#!/usr/bin/env python3
"""從中選會 votedata.zip 建立原住民族地方選舉長表。

MVP 範圍：2022（民國 111 年）T2 議員（平地原住民）選舉，city 與 prv 兩份檔案。

欄位語意一律以壓縮檔內的官方格式文件 voteData/選舉資料庫格式.odt 為準，
不從既有腳本反推、不從資料猜。已知踩過的坑見 README「已查證的事實」。

用法：
    python scripts/build_local_election.py

不連網。讀 data/raw/cec-votedata.zip，寫 data/processed/ 與 docs/schema/。
任何自我驗證未通過即中止並回報，絕不套用預設值。
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = ROOT / "data" / "raw" / "cec-votedata.zip"
OUT_DIR = ROOT / "data" / "processed"

# 本次建置範圍。擴充屆別或選舉種類時改這裡。
YEAR = 2022
YEAR_FOLDER = "2022-111年地方公職人員選舉"
ELECTION_TYPES = {
    "T2": "議員（平地原住民）",
}
# 2022 年僅 C1/T1/T2/T3 有 city／prv 子資料夾，其餘選舉種類為扁平單一份。
SPLIT_TYPES = {"C1", "T1", "T2", "T3"}

# 官方格式文件 elcand／elctks 的當選註記
WIN_MARKS = {
    "*": "當選",
    " ": "未當選",
    "": "未當選",
    "!": "婦女保障當選",
    "-": "因婦女保障被排擠未當選",
}
# 計入席次的註記。只數 '*' 會系統性少算當選人且不報錯。
ELECTED_MARKS = {"*", "!"}

GENDER = {"1": "男", "2": "女"}


class ValidationError(Exception):
    """自我驗證未通過。中止而不是套用預設值。"""


def zip_names(zf: zipfile.ZipFile) -> dict[str, str]:
    """還原 Big5 檔名。

    壓縮檔未設 UTF-8 旗標，zipfile 以 cp437 解碼，須轉回 cp950。
    回傳 {還原後的名稱: 原始 namelist 名稱}。
    """
    out = {}
    for raw in zf.namelist():
        try:
            fixed = raw.encode("cp437").decode("cp950")
        except (UnicodeEncodeError, UnicodeDecodeError):
            fixed = raw
        out[fixed] = raw
    return out


def read_csv(zf: zipfile.ZipFile, names: dict[str, str], path: str) -> list[list[str]]:
    """讀壓縮檔內一個 CSV。所有欄位一律保留為字串。

    行政區代碼絕不可轉成數字：官方格式文件說明跨村里投開票所的村里代碼
    首碼為英文（如 A001），且補零形式（'0' 與 '0000'）本身帶有層級語意。
    """
    if path not in names:
        raise ValidationError(f"壓縮檔內找不到 {path}")
    data = zf.read(names[path]).decode("utf-8", errors="strict")
    rows = []
    for line in data.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.strip() == "":
            continue
        rows.append(line.split(","))
    return rows


def is_blank(code: str) -> bool:
    """該層級是否為「以上層級彙總」。

    官方格式文件：縣市以上彙總時縣市別為 000、選區以上為 00、
    鄉鎮市區以上為 000、村里以上為 0000、投開票所以上為 0。
    補零位數跨檔不一致（'0' 與 '0000' 都出現過），故一律用「全為 0」判斷。
    """
    return code == "" or set(code) == {"0"}


def admin_level(codes: list[str]) -> str:
    """由 6 個行政區代碼判定該列的層級。

    這是最容易出錯的一步：彙總列與明細列混在同一個檔案裡，
    沒有先判層級就加總，得票會暴增數倍。
    """
    prov, county, district, town, village, station = codes[:6]
    if not is_blank(station):
        return "投開票所"
    if not is_blank(village):
        return "村里"
    if not is_blank(town):
        return "鄉鎮市區"
    if not is_blank(district):
        return "選舉區"
    if not is_blank(county) or not is_blank(prov):
        return "直轄市縣市"
    return "檔別合計"


def detect_layout(n: list[int]) -> tuple[str, int, int]:
    """偵測 elprof idx11-16 的欄位版面，回傳（版面名, 候選人數, 當選人數）。

    官方格式文件（民國 101 年）記為「候選合計, 當選合計, 候選男, 候選女,
    當選男, 當選女」，但 2022 年實際資料為「候選男, 候選女, 候選合計,
    當選男, 當選女, 當選合計」。兩種各自算術自洽，只能靠「男+女=合計」分辨。

    兩種皆不通過即中止：依錯誤版面解讀會得到看起來合理但完全錯誤的席次，
    而且不會報錯。
    """
    a, b, c, d, e, f = n[11], n[12], n[13], n[14], n[15], n[16]
    if a + b == c and d + e == f:
        return "男女合計", c, f
    if c + d == a and e + f == b:
        return "合計在前", a, b
    raise ValidationError(
        f"elprof idx11-16 兩種版面皆未通過「男+女=合計」自我驗證："
        f"{a},{b},{c},{d},{e},{f}。來源欄位順序可能再次變更，須人工確認。"
    )


def build_area_names(base_rows: list[list[str]]) -> dict[tuple[str, ...], str]:
    """elbase 的行政區代碼→名稱對照。鍵為 5 碼 tuple。"""
    return {tuple(r[:5]): r[5] for r in base_rows if len(r) >= 6}


def process_one(zf, names, etype: str, variant: str | None) -> dict:
    """處理單一選舉種類的單一檔別（city／prv／扁平）。"""
    sub = f"{etype}/{variant}" if variant else etype
    prefix = f"votedata/votedata/voteData/{YEAR_FOLDER}/{sub}"

    base = read_csv(zf, names, f"{prefix}/elbase.csv")
    cand = read_csv(zf, names, f"{prefix}/elcand.csv")
    paty = read_csv(zf, names, f"{prefix}/elpaty.csv")
    prof = read_csv(zf, names, f"{prefix}/elprof.csv")
    ctks = read_csv(zf, names, f"{prefix}/elctks.csv")

    area = build_area_names(base)
    parties = {r[0]: r[1] for r in paty if len(r) >= 2}

    label = variant or "單一"

    # ---- elprof：選舉概況 ----
    summary = []
    file_total = None
    for r in prof:
        if len(r) < 20:
            raise ValidationError(f"{sub} elprof 有 {len(r)} 欄，預期 20 欄")
        n = {i: int(r[i]) for i in range(6, 17)}
        level = admin_level(r)
        layout, n_cand, n_seat = detect_layout(n)

        valid, invalid, voted = n[6], n[7], n[8]
        if valid + invalid != voted:
            raise ValidationError(
                f"{sub} 有效票+無效票≠投票數：{valid}+{invalid}≠{voted}（{r[:6]}）"
            )
        electors = n[9]
        row = {
            "年度": YEAR,
            "選舉種類": etype,
            "選舉種類名稱": ELECTION_TYPES[etype],
            "檔別": label,
            "層級": level,
            "省市": r[0], "縣市": r[1], "選舉區": r[2],
            "鄉鎮市區": r[3], "村里": r[4], "投開票所": r[5],
            "行政區名稱": area.get(tuple(r[:5]), ""),
            "有效票": valid, "無效票": invalid, "投票數": voted,
            "選舉人數": electors, "人口數": n[10],
            "候選人數": n_cand, "當選人數": n_seat,
            "投票率": r[18], "版面": layout,
        }
        summary.append(row)
        if level == "檔別合計":
            if file_total is not None:
                raise ValidationError(f"{sub} elprof 出現多列檔別合計")
            file_total = row

    if file_total is None:
        raise ValidationError(f"{sub} elprof 找不到檔別合計列（前 6 欄皆為 0）")

    # ---- elcand：候選人 ----
    # 不輸出出生日期、出生地、學歷（個資最小化，見 docs/schema）。
    candidates = []
    for r in cand:
        if len(r) < 15:
            raise ValidationError(f"{sub} elcand 有 {len(r)} 欄，預期至少 15 欄")
        mark = r[14]
        if mark not in WIN_MARKS:
            raise ValidationError(
                f"{sub} elcand 出現未知的當選註記 {mark!r}。"
                f"官方格式文件僅定義 '*'、' '、'!'、'-' 四種。"
            )
        candidates.append({
            "年度": YEAR,
            "選舉種類": etype,
            "選舉種類名稱": ELECTION_TYPES[etype],
            "檔別": label,
            "省市": r[0], "縣市": r[1], "選舉區": r[2],
            "鄉鎮市區": r[3], "村里": r[4],
            "行政區名稱": area.get(tuple(r[:5]), ""),
            "號次": r[5],
            "姓名": r[6],
            "政黨代號": r[7],
            "政黨名稱": parties.get(r[7], ""),
            "性別": GENDER.get(r[8], r[8]),
            "年齡": r[10],
            "現任": r[13],
            "當選註記": mark.strip(),
            "當選註記語意": WIN_MARKS[mark],
            "當選": "Y" if mark in ELECTED_MARKS else "N",
        })

    # ---- elctks：候選人得票 ----
    votes = []
    for r in ctks:
        if len(r) < 9:
            raise ValidationError(f"{sub} elctks 有 {len(r)} 欄，預期至少 9 欄")
        mark = r[9] if len(r) > 9 else ""
        if mark not in WIN_MARKS:
            raise ValidationError(f"{sub} elctks 出現未知的當選註記 {mark!r}")
        votes.append({
            "年度": YEAR,
            "選舉種類": etype,
            "選舉種類名稱": ELECTION_TYPES[etype],
            "檔別": label,
            "層級": admin_level(r),
            "省市": r[0], "縣市": r[1], "選舉區": r[2],
            "鄉鎮市區": r[3], "村里": r[4], "投開票所": r[5],
            "行政區名稱": area.get(tuple(r[:5]), ""),
            "號次": r[6],
            "得票數": int(r[7]),
            "得票率": r[8],
            "當選註記": mark.strip(),
        })

    return {
        "summary": summary, "candidates": candidates, "votes": votes,
        "file_total": file_total, "label": label,
    }


def cross_validate(parts: list[dict], report: list[dict]) -> None:
    """交叉驗證。任何一項不通過即中止。"""
    for p in parts:
        ft = p["file_total"]
        label = p["label"]

        # 1. elprof 的候選人數／當選人數 對得上 elcand 的實際列數？
        n_cand = len(p["candidates"])
        n_win = sum(1 for c in p["candidates"] if c["當選"] == "Y")
        if n_cand != ft["候選人數"]:
            raise ValidationError(
                f"{label} 候選人數不符：elprof={ft['候選人數']}、elcand={n_cand}"
            )
        if n_win != ft["當選人數"]:
            raise ValidationError(
                f"{label} 當選人數不符：elprof={ft['當選人數']}、elcand={n_win}。"
                f"（只數 '*' 而漏掉 '!' 婦女保障是最常見原因）"
            )

        # 2. 投票率能不能從投票數／選舉人數重算出來？
        recomputed = round(100.0 * ft["投票數"] / ft["選舉人數"], 2)
        stated = round(float(ft["投票率"]), 2)
        if abs(recomputed - stated) > 0.01:
            raise ValidationError(
                f"{label} 投票率不符：重算={recomputed}、檔案={stated}"
            )

        # 3. elctks 各選舉區的得票加總，是否等於該區明細列的有效票？
        #    這是「彙總列混在明細列」陷阱的直接測試：
        #    若誤把彙總列一起加總，數字會暴增數倍。
        station_sum = sum(
            v["得票數"] for v in p["votes"] if v["層級"] == "投開票所"
        )
        valid_detail = sum(
            s["有效票"] for s in p["summary"] if s["層級"] == "投開票所"
        )
        if station_sum != valid_detail:
            raise ValidationError(
                f"{label} 投開票所層級得票加總={station_sum}，"
                f"但 elprof 同層級有效票加總={valid_detail}"
            )

        report.append({
            "檔別": label,
            "候選人數": n_cand,
            "當選人數": n_win,
            "選舉人數": ft["選舉人數"],
            "投票數": ft["投票數"],
            "投票率_檔案": ft["投票率"],
            "投票率_重算": recomputed,
            "投開票所層級得票加總": station_sum,
            "版面": ft["版面"],
        })

    # 4. city 與 prv 是互斥的行政區劃分——兩者的縣市代碼不得重疊。
    if len(parts) > 1:
        sets = []
        for p in parts:
            sets.append({
                (s["省市"], s["縣市"])
                for s in p["summary"] if s["層級"] == "直轄市縣市"
            })
        overlap = sets[0] & sets[1]
        if overlap:
            raise ValidationError(
                f"city 與 prv 的縣市代碼重疊：{sorted(overlap)}。"
                f"兩者應為互斥的行政區劃分，相加才是全國數字。"
            )


def write_csv(path: Path, rows: list[dict], gzip_it: bool = False) -> None:
    """寫出長表。大檔以 gzip 壓縮，沿用相鄰專案的慣例。

    gzip 標頭預設會寫入當下時間，導致每次建置的位元組都不同。
    這裡固定 mtime=0，讓相同輸入產生相同輸出（可重現、git diff 乾淨）。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValidationError(f"{path.name} 沒有任何資料列")

    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    payload = buf.getvalue().encode("utf-8-sig")

    if gzip_it:
        with io.open(path, "wb") as fh:
            with gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
                gz.write(payload)
    else:
        path.write_bytes(payload)


def main() -> None:
    if not ZIP_PATH.exists():
        raise SystemExit(
            f"找不到 {ZIP_PATH}。該檔不入庫，請自 https://data.cec.gov.tw/ 下載。"
        )

    digest = hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()

    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zip_names(zf)
        all_summary, all_cand, all_votes, parts = [], [], [], []
        for etype in ELECTION_TYPES:
            variants = ["city", "prv"] if etype in SPLIT_TYPES else [None]
            for v in variants:
                p = process_one(zf, names, etype, v)
                parts.append(p)
                all_summary += p["summary"]
                all_cand += p["candidates"]
                all_votes += p["votes"]

    report: list[dict] = []
    cross_validate(parts, report)

    write_csv(OUT_DIR / "cec-local-election-summary-long.csv.gz", all_summary, gzip_it=True)
    write_csv(OUT_DIR / "cec-local-election-candidates-long.csv", all_cand)
    write_csv(OUT_DIR / "cec-local-election-votes-long.csv.gz", all_votes, gzip_it=True)

    national = {
        "選舉人數": sum(r["選舉人數"] for r in report),
        "投票數": sum(r["投票數"] for r in report),
        "候選人數": sum(r["候選人數"] for r in report),
        "當選人數": sum(r["當選人數"] for r in report),
    }
    national["投票率_本專案計算"] = round(
        100.0 * national["投票數"] / national["選舉人數"], 2
    )

    (OUT_DIR / "validation-report.json").write_text(
        json.dumps({
            "來源檔": ZIP_PATH.name,
            "來源檔sha256": digest,
            "年度": YEAR,
            "選舉種類": ELECTION_TYPES,
            "各檔別": report,
            "全國合計": national,
            "全國合計說明": (
                "city 與 prv 為互斥行政區劃分，兩份 elprof 的首列各為該檔範圍小計，"
                "須相加才是全國數字。全國投票率為本專案計算值，檔案中不存在此數。"
            ),
            "列數": {
                "summary": len(all_summary),
                "candidates": len(all_cand),
                "votes": len(all_votes),
            },
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"來源 sha256: {digest}")
    for r in report:
        print(
            f"  {r['檔別']:<5} 選舉人 {r['選舉人數']:>7,} "
            f"投票 {r['投票數']:>7,} 投票率 {r['投票率_重算']:>5}% "
            f"候選 {r['候選人數']:>3} 當選 {r['當選人數']:>3} 版面 {r['版面']}"
        )
    print(
        f"  全國   選舉人 {national['選舉人數']:>7,} "
        f"投票 {national['投票數']:>7,} 投票率 {national['投票率_本專案計算']:>5}% "
        f"候選 {national['候選人數']:>3} 當選 {national['當選人數']:>3}"
    )
    print(
        f"輸出 {len(all_summary):,} / {len(all_cand):,} / {len(all_votes):,} 列"
        f"（summary / candidates / votes）"
    )
    print("所有自我驗證通過。")


if __name__ == "__main__":
    main()
