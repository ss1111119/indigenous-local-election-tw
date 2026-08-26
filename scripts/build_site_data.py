#!/usr/bin/env python3
"""由長表產生站台內嵌的資料常數。

## 為什麼需要這支腳本

`docs/index.html` 的 `DATA` 與 `docs/roster.html` 的 `D` 原本是**人工維護**的
內嵌 JSON——`scripts/` 內沒有任何檔案參照那兩個頁面。所以資料集更新後站台不會
跟上，而且已經發生過不只一次（commit `aade72f` 修的是同一種不一致）。

內嵌常數這個**形式**沒有問題：站台是 GitHub Pages 的靜態頁，既有設計明訂
「不連外部資源」，改成 `fetch()` 會讓離線開啟與單檔分享失效，在 `file://` 下
還會被 CORS 擋掉。有問題的是「由人手維護」。所以這支腳本算出常數後
**就地替換 HTML 中的那一行**，其餘位元組不動。

⚠️ 只需要 summary 與 candidates 兩張長表。站台完全沒有用到 votes 表——
名錄的候選人 tuple 是「號次, 姓名, 政黨, 性別, 年齡, 現任, 註記」，不含得票數。
votes 表有 175 萬列／12MB，載入它純屬浪費。

用法：
    python scripts/build_site_data.py

不連網。任何自我驗證未通過即中止，不產出半套結果。
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import budoux

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"

SUMMARY_FILE = "cec-local-election-summary-long.csv.gz"
CANDIDATES_FILE = "cec-local-election-candidates-long.csv"

# 原住民立委（九屆）。⚠️ 與地方公職是【不同母體】——中央職位、全國單一選區。
# 站台上兩者必須分頁呈現，不可出現在同一份 types 清單或同一條折線。
LEG_SUMMARY_FILE = "cec-legislative-election-summary-long.csv.gz"
LEG_CANDIDATES_FILE = "cec-legislative-election-candidates-long.csv"
LEG_VOTES_FILE = "cec-legislative-election-votes-long.csv.gz"

# 不分區政黨票的界限表。⚠️ 這一份是【估計值】不是開票結果，
# 且只涵蓋原住民族地區的高佔比投開票所——引用時必須帶涵蓋率。
BOUNDS_FILE = "indigenous-party-preference-bounds.csv"

# 本腳本實際會讀到的欄位，逐張表宣告。
#
# ⚠️ 這份清單必須**恰好等於**程式讀到的欄位集合，兩個方向都要對：
#    - 少列了實際會讀的欄位（例如 `鄉鎮市區`）→ 缺欄時不會在讀完標頭時中止，
#      而是算到一半才 KeyError，錯誤訊息離真正的原因很遠。
#    - 多列了不讀的欄位 → 對本可處理的長表無謂中止。
#    這一項由 scripts/test_build_site_data.py 以合成 CSV 從行為端釘住
#    （拔掉會讀的欄位須得到 SiteDataError；缺少不讀的欄位須能正常算完），
#    不是用「清單裡有沒有某個字串」這種跟著程式一起改的斷言。
#
# ⚠️ 缺欄即中止，不套用預設值也不跳過該欄。最要緊的是 `當選`：
#    少了它會退回用 `當選註記`，而註記忠實反映來源錯誤——2005 縣市議員山原以
#    註記只算出 18 席（正確 30）、平原 20（正確 27）。那種錯誤不會報錯，
#    只會讓站台安靜地少 19 席。
REQUIRED_COLUMNS = {
    SUMMARY_FILE: (
        "年度", "選舉種類", "選舉種類名稱", "檔別", "層級",
        "省市", "縣市", "選舉區", "鄉鎮市區", "行政區名稱",
        "選舉人數", "投票數",
        "admin_code_system", "is_main_sequence",
    ),
    CANDIDATES_FILE: (
        "年度", "選舉種類", "檔別",
        "省市", "縣市", "選舉區", "鄉鎮市區", "行政區名稱",
        "號次", "姓名", "政黨代號", "政黨名稱", "性別", "年齡", "現任",
        "當選註記", "當選",
        "admin_code_system",
    ),
    LEG_SUMMARY_FILE: (
        "年度", "選舉種類", "選舉種類名稱", "層級",
        "選舉人數", "投票數",
    ),
    LEG_CANDIDATES_FILE: (
        "年度", "選舉種類", "號次", "姓名",
        "政黨代號", "政黨名稱", "當選",
    ),
    LEG_VOTES_FILE: (
        "年度", "選舉種類", "層級", "號次", "得票數",
    ),
    BOUNDS_FILE: (
        "屆別", "門檻", "政黨代號", "政黨名稱", "所數",
        "涵蓋原住民選舉人", "涵蓋率", "p_加權", "q_加權", "有效政黨票",
        "觀察_得票數", "觀察_得票率",
        "下界_原住民得票率", "上界_原住民得票率",
    ),
}


class SiteDataError(Exception):
    """自我驗證未通過。中止而不是套用預設值。"""


def read_long_table(path: Path, required: tuple[str, ...]) -> list[dict]:
    """讀一張長表並檢查必要欄位。

    欄位檢查在讀完標頭後【立即】做，不等到用到那一欄才失敗——
    後者會在算了一半之後才中止，而且錯誤訊息會離真正的原因很遠。
    """
    if not path.exists():
        raise SiteDataError(f"找不到長表 {path}")
    opener = gzip.open if path.suffix == ".gz" else io.open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        missing = [c for c in required if c not in header]
        if missing:
            raise SiteDataError(
                f"{path.name} 缺少必要欄位 {missing}。"
                f"實際欄位共 {len(header)} 個。"
                f"請先執行 scripts/build_local_election.py 重新產生長表。"
            )
        rows = list(reader)
    if not rows:
        raise SiteDataError(f"{path.name} 沒有任何資料列")
    return rows


def load_long_tables(data_dir: Path = DATA_DIR) -> tuple[list[dict], list[dict]]:
    """讀入 summary 與 candidates 兩張長表。回傳（summary, candidates）。"""
    summary = read_long_table(data_dir / SUMMARY_FILE,
                              REQUIRED_COLUMNS[SUMMARY_FILE])
    cands = read_long_table(data_dir / CANDIDATES_FILE,
                            REQUIRED_COLUMNS[CANDIDATES_FILE])
    return summary, cands


def load_legislative_tables(
    data_dir: Path = DATA_DIR,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """讀入立委三張長表與界限表。

    回傳（summary, candidates, votes, bounds）。

    ⚠️ 立委與地方公職是不同母體，這裡刻意用另一個載入函式而不是把檔名
       加進 load_long_tables——同一個入口回傳兩個資料集，會讓後續程式
       很容易把它們接在一起。
    """
    return (
        read_long_table(data_dir / LEG_SUMMARY_FILE,
                        REQUIRED_COLUMNS[LEG_SUMMARY_FILE]),
        read_long_table(data_dir / LEG_CANDIDATES_FILE,
                        REQUIRED_COLUMNS[LEG_CANDIDATES_FILE]),
        read_long_table(data_dir / LEG_VOTES_FILE,
                        REQUIRED_COLUMNS[LEG_VOTES_FILE]),
        read_long_table(data_dir / BOUNDS_FILE,
                        REQUIRED_COLUMNS[BOUNDS_FILE]),
    )


def terms(summary: list[dict]) -> list[str]:
    """長表涵蓋的屆別，由早到晚。

    字串排序即為時序：所有屆別鍵都以四位數西元年開頭，
    而 "2009-2010" 排在 "2006" 之後、"2014" 之前。
    """
    return sorted({r["年度"] for r in summary})


def election_types(summary: list[dict]) -> dict[str, dict]:
    """長表涵蓋的選舉種類，回傳 {代碼: {name, indigenous, mainSequence}}。

    ⚠️ `mainSequence` 直接取自長表的 `is_main_sequence` 欄，不在此重新判定——
    那一欄是資料層的權威來源（見 scripts/oracles.py 的 is_main_sequence）。
    同一個選舉種類在不同列若出現不一致的值，代表資料層出了問題，中止。
    """
    out: dict[str, dict] = {}
    for r in summary:
        code = r["選舉種類"]
        ms = r["is_main_sequence"] == "true"
        if code in out:
            if out[code]["mainSequence"] != ms:
                raise SiteDataError(
                    f"選舉種類 {code} 的 is_main_sequence 在長表中不一致——"
                    f"資料層有問題，不可由站台端猜測"
                )
            continue
        out[code] = {
            # 站台的顯示名稱去掉尾綴「選舉」，沿用現有常數的寫法
            "name": r["選舉種類名稱"].removesuffix("選舉"),
            "mainSequence": ms,
        }
    return out


# 站台圖表的政黨分組。三個具名桶，其餘一律歸「其他」。
#
# ⚠️ **鍵是 (政黨代號, 政黨名稱) 配對，不是名稱、也不是代號。**
#    兩種單一鍵都被實測證明不成立：
#
#    - 只用名稱 → **無黨籍破掉**。無黨籍在來源有兩套完全不重疊的編碼：
#      舊屆是代號 99／名稱「無」（1994-2006 共 151 列），
#      新屆是代號 999／名稱「無黨籍及未經政黨推薦」（2009-2022 共 2,894 列）。
#      只認後者的話，站台上五個舊屆的無黨籍全是 0，那 151 位候選人被歸進「其他」。
#      這就是本對照表要修的錯。
#    - 只用代號 → **民進黨破掉**。舊屆是 2、新屆是 16，但名稱一致，
#      所以名稱比對對民進黨反而是對的。國民黨兩個時代都是 1。
#
#    其他同名多代號者（不影響本表，但說明為何不能只用代號）：
#    新黨 5／74、親民黨 3／90、台灣團結聯盟 4／95、無黨團結聯盟 7／106、勞動黨 15／33。
#
# ⚠️ **同代號多名稱不自動合併。** 代號 303 有「基進黨」與「台灣基進」兩個名稱
#    （另有 290、166、199、254 亦然）。它們是兩個不同的鍵，各自查表，
#    都查不到就都歸「其他」。代號被回收再發給另一個政黨時，
#    自動合併會把一個政黨的成績無聲地算到另一個頭上。
#
# ⚠️ **不可改用子字串或前綴比對。** 「含『無』」或「以『無黨』開頭」會把
#    **無黨團結聯盟**（一個獨立登記的政黨，25 位候選人、14 席）錯誤吸收進無黨籍。
PARTY_IDENTITY_BUCKETS: dict[tuple[str, str], str] = {
    ("1", "中國國民黨"): "中國國民黨",
    ("2", "民主進步黨"): "民主進步黨",
    ("16", "民主進步黨"): "民主進步黨",
    ("99", "無"): "無黨籍及未經政黨推薦",
    ("999", "無黨籍及未經政黨推薦"): "無黨籍及未經政黨推薦",
}

# 桶名。顯示用字沿用新屆的官方名稱「無黨籍及未經政黨推薦」——
# 它不等同一般語意的「無黨籍」，站台端另有縮寫顯示。
PARTY_BUCKETS = ("中國國民黨", "無黨籍及未經政黨推薦", "民主進步黨")
OTHER_BUCKET = "其他"


# ⚠️ 年齡的「未記載」判準【不在這裡】。它在長表建置端，長表的 `年齡` 欄
#    因此已經是乾淨值（有記載放值、未記載留空），本檔直接讀取。
#    來源原值在 `年齡_原始`，站台【不讀那一欄】——讀了就等於有第二份判準。
#    同一個規則若在兩處各有一份實作，其中一份必然漂移——這個專案已經因此
#    出過兩個 bug（名錄的 MAIN 手寫一份、政黨分桶只認一種名稱）。
#    守住具名清單前提的兩條斷言也隨判準一起移到建置端，不是刪掉。


def party_bucket(row: dict) -> str:
    """該候選人所屬的圖表分組。查不到就是「其他」，不猜。"""
    return PARTY_IDENTITY_BUCKETS.get(
        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)


def is_blank(code: str) -> bool:
    """該層級是否為「以上層級彙總」。與 build_local_election 同一判準。"""
    return code == "" or set(code) == {"0"}


def district_key(row: dict, uses_town: bool) -> tuple:
    """該列所屬的「選舉區」鍵。

    ⚠️ 粒度**由資料推導**，不寫死選舉種類：T1／T2／T3 的候選人記在選舉區層級
    （鄉鎮市區為 0），D2／R3／R2 記在鄉鎮市區層級——因為那些選舉本身就以
    鄉鎮市／區為單位（D2 的選舉區欄全是 00）。
    這與 build_local_election.py 第 6b 項驗證用的是同一個判準。
    實測 22 組（選舉種類 × 屆別）的區數與站台現有常數完全相符。
    """
    base = (row["省市"], row["縣市"], row["選舉區"])
    return base + ((row["鄉鎮市區"],) if uses_town else ())


def _round_half_up(value: Decimal, places: str) -> Decimal:
    """四捨五入。中選會用的是四捨五入而非 Python round() 的銀行家捨入。

    ⚠️ **`--check` 的重現比對抓不到這一條。** 實測九屆 33 組的投票率，
    改用浮點的 `round()` 與精確十進位的結果**完全一致**——所以把這裡改壞，
    任何以真實資料為基礎的檢查都會通過。這一條只能靠合成資料的單元測試守
    （見 scripts/test_build_site_data.py）。
    這與長表那邊「2022 T2 沒有 `!` 列，所以拿掉 `!` 也全過」是同一類問題。
    """
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def build_index_data(summary: list[dict], cands: list[dict],
                     only_terms: list[str] | None = None) -> dict:
    """算出 `docs/index.html` 的 `DATA` 常數。

    ⚠️ 所有與當選有關的數字一律取自 `當選`——**它現在存放的是跨檔比對後的
    權威值**，不是來源怎麼寫。來源的認定在 `當選註記`，用它計席次會少算：
    2005 縣市議員山原只有 18 席（正確 30）、平原 20（正確 27）。
    """
    all_terms = terms(summary)
    keep = set(only_terms) if only_terms else set(all_terms)
    years = [y for y in all_terms if y in keep]
    types_meta = election_types(summary)

    # 檔別合計列：每個（屆別, 選舉種類, 檔別）一列。T2／T3 的 city 與 prv
    # 是互斥的行政區劃分，全國數字須相加——不能只取其中一份。
    totals: dict[tuple[str, str], dict[str, int]] = {}
    for r in summary:
        if r["層級"] != "檔別合計":
            continue
        k = (r["選舉種類"], r["年度"])
        acc = totals.setdefault(k, {"electors": 0, "votes": 0})
        acc["electors"] += int(r["選舉人數"])
        acc["votes"] += int(r["投票數"])

    by_key: dict[tuple[str, str], list[dict]] = {}
    for c in cands:
        by_key.setdefault((c["選舉種類"], c["年度"]), []).append(c)

    out_types = []
    for code, meta in types_meta.items():
        per_year: dict[str, dict | None] = {}
        for year in years:
            k = (code, year)
            rows = by_key.get(k)
            if not rows:
                # 該屆沒有這種選舉。以 null 表示「不存在」，站台顯示 ×——
                # 用 0 填補會讓「沒有這種選舉」與「這種選舉 0 席」無法分辨。
                per_year[year] = None
                continue
            tot = totals[k]
            won = [c for c in rows if c["當選"] == "Y"]
            uses_town = any(not is_blank(c["鄉鎮市區"]) for c in rows)
            dists: dict[tuple, dict[str, int]] = {}
            for c in rows:
                d = dists.setdefault(district_key(c, uses_town),
                                     {"cands": 0, "seats": 0})
                d["cands"] += 1
                if c["當選"] == "Y":
                    d["seats"] += 1
            # 同額競選：該選舉區的候選人數等於當選人數
            unc = [d for d in dists.values() if d["cands"] == d["seats"]]

            party: dict[str, list[int]] = {b: [0, 0] for b in PARTY_BUCKETS}
            party[OTHER_BUCKET] = [0, 0]
            for c in rows:
                b = party_bucket(c)
                party[b][1] += 1
                if c["當選"] == "Y":
                    party[b][0] += 1

            turnout = (float(_round_half_up(
                Decimal(100 * tot["votes"]) / Decimal(tot["electors"]), "0.01"))
                if tot["electors"] else None)
            per_seat = (int(_round_half_up(
                Decimal(tot["electors"]) / Decimal(len(won)), "1"))
                if won else None)

            per_year[year] = {
                "electors": tot["electors"],
                "votes": tot["votes"],
                "turnout": turnout,
                "seats": len(won),
                "cands": len(rows),
                "districts": len(dists),
                "party": party,
                "femaleSeats": sum(1 for c in won if c["性別"] == "女"),
                "femaleCands": sum(1 for c in rows if c["性別"] == "女"),
                "quota": sum(1 for c in rows if c["當選註記"] == "!"),
                "displaced": sum(1 for c in rows if c["當選註記"] == "-"),
                "incCands": sum(1 for c in rows if c["現任"] == "Y"),
                "incWon": sum(1 for c in won if c["現任"] == "Y"),
                "uncontestedDist": len(unc),
                "uncontestedSeats": sum(d["seats"] for d in unc),
                "perSeat": per_seat,
            }
        if all(v is None for v in per_year.values()):
            continue
        out_types.append({
            "code": code,
            "name": meta["name"],
            "indigenous": code != "T1",
            "mainSequence": meta["mainSequence"],
            "years": per_year,
        })

    return {
        "types": out_types,
        "years": years,
        "note2009": "2009-2010 是同一輪任期分兩次投票"
                    "（縣市 2009-12-05、直轄市 2010-11-27）",
    }



# ── 立委的政黨分桶 ──────────────────────────────────────────────────
#
# ⚠️ **與地方公職的 PARTY_BUCKETS 是兩套，不可共用。** 直接沿用那三桶會讓
#    親民黨 2001 年的 27.7%、無黨團結聯盟 2004 年的 26.0% 掉進「其他」——
#    而那正是那兩屆的主要故事。
#
# ⚠️ 分桶鍵仍是（政黨代號, 政黨名稱）配對，不是只比名稱。
#    無黨籍在來源有兩套不重疊的編碼（舊屆「無」、新屆「無黨籍及未經政黨推薦」），
#    站台既有的分桶就是為此建立的。
LEGISLATIVE_PARTY_BUCKETS = (
    "中國國民黨", "民主進步黨", "親民黨", "無黨團結聯盟", "無黨籍",
)

# 來源的（政黨代號, 政黨名稱）→ 桶。九屆實測涵蓋 35 種配對，具名 9 種。
#
# ⚠️ **鍵是配對，不是名稱也不是代號**，與既有的 PARTY_IDENTITY_BUCKETS 同一個
#    慣例。這批資料自己就有兩個反例：
#
#    - **代號 9 對到兩個不同政黨**：("9", "全國民主非政黨聯盟") 與
#      ("9", "台灣吾黨")。只用代號會把兩者合併。
#    - **同一政黨有兩個代號**：親民黨 3／90、無黨團結聯盟 7／106、
#      民主進步黨 2／16。只用代號會把同一政黨拆成兩個。
#
# ⚠️ 無黨籍的兩套編碼（99／「無」與 999／「無黨籍及未經政黨推薦」）
#    都歸同一桶。少了任何一個，某些屆的無黨籍會變成 0 而站台照樣畫得出來。
LEGISLATIVE_IDENTITY_BUCKETS: dict[tuple[str, str], str] = {
    ("1", "中國國民黨"): "中國國民黨",
    ("2", "民主進步黨"): "民主進步黨",
    ("16", "民主進步黨"): "民主進步黨",
    ("3", "親民黨"): "親民黨",
    ("90", "親民黨"): "親民黨",
    ("7", "無黨團結聯盟"): "無黨團結聯盟",
    ("106", "無黨團結聯盟"): "無黨團結聯盟",
    ("99", "無"): "無黨籍",
    ("999", "無黨籍及未經政黨推薦"): "無黨籍",
}


def legislative_bucket(row: dict) -> str:
    """立委候選人的政黨桶。查不到就是『其他』，不猜。"""
    return LEGISLATIVE_IDENTITY_BUCKETS.get(
        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)


def check_bucket_sets_differ() -> None:
    """兩個分桶集合必須不相等。

    ⚠️ 這條守的是「哪天有人把兩套合併成一套」。合併之後親民黨與
       無黨團結聯盟會靜默地掉進『其他』，而站台照樣畫得出來。
    """
    if set(LEGISLATIVE_PARTY_BUCKETS) == set(PARTY_BUCKETS):
        raise SiteDataError(
            "立委與地方公職的分桶集合相同。兩者的政黨版圖不同——"
            "合併成一套會讓只在其中一邊重要的政黨掉進『其他』"
            "（親民黨 2001 年 27.7%、無黨團結聯盟 2004 年 26.0%）。"
        )


def build_legislative_data(summary: list[dict], cands: list[dict],
                           votes: list[dict]) -> dict:
    """立委頁的資料常數。

    ⚠️ 席次一律取自 `當選`（跨檔推導的權威值），**不數 `當選註記`**。
       註記忠實反映來源錯誤，而權威值是對帳過的。
    """
    check_bucket_sets_differ()

    party_of = {(c["年度"], c["選舉種類"], c["號次"]): legislative_bucket(c)
                for c in cands}

    years = sorted({r["年度"] for r in summary})
    types: dict[str, dict] = {}
    for r in summary:
        if r["層級"] != "檔別合計":
            continue
        t = types.setdefault(r["選舉種類"], {
            "code": r["選舉種類"], "name": r["選舉種類名稱"], "years": {}})
        y = t["years"].setdefault(r["年度"], {"electors": 0, "votes": 0})
        y["electors"] += int(r["選舉人數"])
        y["votes"] += int(r["投票數"])

    # 席次與候選人數（由權威值 `當選` 計）
    for c in cands:
        y = types[c["選舉種類"]]["years"].setdefault(
            c["年度"], {"electors": 0, "votes": 0})
        y["cands"] = y.get("cands", 0) + 1
        if c["當選"] == "Y":
            y["seats"] = y.get("seats", 0) + 1

    # 逐屆逐桶的得票（檔別合計層級，兩種類相加）
    party_votes: dict[str, dict[str, int]] = {y: {} for y in years}
    party_total: dict[str, int] = {y: 0 for y in years}
    for v in votes:
        if v["層級"] != "檔別合計":
            continue
        bucket = party_of.get((v["年度"], v["選舉種類"], v["號次"]))
        if bucket is None:
            raise SiteDataError(
                f"{v['年度']} {v['選舉種類']} 號次 {v['號次']} "
                f"在候選人長表找不到對應的政黨"
            )
        n = int(v["得票數"])
        party_votes[v["年度"]][bucket] = \
            party_votes[v["年度"]].get(bucket, 0) + n
        party_total[v["年度"]] += n

    buckets = list(LEGISLATIVE_PARTY_BUCKETS) + [OTHER_BUCKET]
    parties = {
        y: {b: _round_half_up(
            Decimal(party_votes[y].get(b, 0)) * 100 / Decimal(party_total[y]),
            "0.01") for b in buckets}
        for y in years
    }

    # ⚠️ 無黨籍桶在每一屆都必須非零——來源有兩套編碼，漏掉任一個
    #    會讓某些屆變成 0 而站台照樣畫得出來。
    empty = [y for y in years if party_votes[y].get("無黨籍", 0) == 0]
    if empty:
        raise SiteDataError(
            f"無黨籍桶在這些屆為 0：{empty}。"
            f"來源有『無』與『無黨籍及未經政黨推薦』兩套不重疊的編碼，"
            f"漏掉任一個都會讓某些屆歸零。"
        )

    for t in types.values():
        for y, d in t["years"].items():
            d["turnout"] = float(_round_half_up(
                Decimal(d["votes"]) * 100 / Decimal(d["electors"]), "0.01"))

    # 逐屆逐桶的席次。
    #
    # ⚠️ 一律由權威值 `當選` 計，與上面的席次同一個來源。
    party_seats = {y: {b: 0 for b in buckets} for y in years}
    for c in cands:
        if c["當選"] == "Y":
            party_seats[c["年度"]][legislative_bucket(c)] += 1

    # 兩種類合計的投票率。山地與平地是兩個不重疊的選舉人母體，
    # 相加得到的是「原住民立委選舉」整體，不是平均值——不可用兩個
    # 投票率取平均，那會忽略兩邊選舉人數不同。
    turnout = {}
    for y in years:
        e = sum(t["years"][y]["electors"] for t in types.values()
                if y in t["years"])
        n = sum(t["years"][y]["votes"] for t in types.values()
                if y in t["years"])
        turnout[y] = float(_round_half_up(
            Decimal(n) * 100 / Decimal(e), "0.01"))

    return {
        "years": years,
        "buckets": buckets,
        "types": [types[k] for k in sorted(types)],
        "parties": {y: {b: float(v) for b, v in parties[y].items()}
                    for y in years},
        "partySeats": party_seats,
        "turnout": turnout,
    }


# 界限表的三個門檻，由寬到窄的涵蓋率。
#
# ⚠️ **三個都要出現在頁面上，不挑一個。** 挑一個等於替讀者決定
#    「涵蓋率換精度」這個取捨要怎麼取——而那正是決定這個數字能不能
#    外推到全體的東西。0.95 只涵蓋 11.0% 的原住民選舉人、0.80 涵蓋 28.4%。
# ── 選舉期間的發布規則 ──────────────────────────────────────────────
#
# 規則在 openspec/specs/election-period-publication/spec.md，
# 逐頁判定在 docs/發布判定紀錄.md。

# ── 多語文案：限定語只有一份來源 ──────────────────────────────────
#
# ⚠️ **限定語是資料，不是頁面裡的靜態文字。** 這是本專案最容易在翻譯時
#    被弱化的東西——譯者（包括我自己）會下意識把「這不是全體原住民的
#    政黨傾向」翻得比較順、比較短，順帶把限定拿掉。做成產生的資料，
#    兩個語言版本就不可能各自漂移。
#
# ⚠️ 這裡只放**限定語與圖表標籤**，不放散文段落。散文留在各自的 HTML：
#    它們可以有不同的寫法，限定語不可以。
#
# `{...}` 是執行期由 JS 代入的欄位，兩種語言必須有**相同的欄位集合**——
# 少一個欄位會在頁面上留下未替換的 `{coverage}`。
STRINGS: dict[str, dict[str, str]] = {
    "current_term_notice": {
        "zh": "本節為 2008–2024 年的歷史數字，不代表 2026 年本屆選舉結果。",
        "en": ("These are historical figures from 2008–2024. They do not "
               "represent the 2026 election now under way."),
    },
    "bounds_qual": {
        # ⚠️ 本屆限定語以 {notice} 併進來，**不是在 JS 裡用 + 接**——
        #    中文不需要空格、英文需要，接法交給各語言自己決定。
        "zh": ("以上是這 {stations} 個投開票所的數字，涵蓋 {coverage}% 的"
               "原住民選舉人，不是全體原住民的政黨傾向。"
               "其餘 {rest}% 的原住民選舉人，同樣的算術給不出有用的界限。"
               "{notice}"),
        "en": ("These figures describe {stations} polling stations covering "
               "{coverage}% of indigenous electors. They are not the party "
               "leaning of indigenous people as a whole. For the remaining "
               "{rest}%, the same arithmetic yields no useful bound. {notice}"),
    },
    "bounds_coverage_label": {
        "zh": "全體原住民選舉人的涵蓋率　{electors} 人",
        "en": "share of all indigenous electors covered　{electors} people",
    },
    "bounds_station_heading": {
        "zh": "原住民選舉人佔比 ≥{pct}% 的 {stations} 個投開票所",
        "en": ("{stations} polling stations where indigenous electors are "
               "≥{pct}% of the roll"),
    },
    "bounds_caption": {
        "zh": "{term} 年不分區政黨票，這 {stations} 個所的觀察值與原住民得票率的界限",
        "en": ("{term} party-list vote: observed shares at these {stations} "
               "stations, and the bounds on the indigenous vote share"),
    },
    "bounds_retained_original": {
        "zh": "沒有官方英文名的政黨保留原文。",
        "en": ("Parties with no established English name are shown under "
               "their original Chinese name."),
    },
    "not_party_identification": {
        "zh": "這不等於政黨認同",
        "en": "This is not party identification",
    },
    "datasets_not_comparable": {
        "zh": "兩頁的數字不可互相比較，也不可相加。",
        "en": ("Figures on these pages cover different populations. They "
               "cannot be compared with each other, and they cannot be added."),
    },
    "dataset_map": {
        "zh": ("本站呈現三個資料集：地方公職（見「概況」與「名錄」）、原住民立法委員"
               "（見「立委選舉」）、不分區政黨票的界限估計（見「立委選舉」頁第 04 節）——"
               "三者選舉人範圍不同，數字不可互相比較，也不可相加。"),
        "en": ("This site presents three datasets: local public offices (see "
               "Overview and Roster), indigenous legislators (see Legislative "
               "elections), and a bounded estimate of party-list preference "
               "(within the Legislative elections page, section 04). Their "
               "electorates differ; figures cannot be compared with each "
               "other, and they cannot be added."),
    },
    # ── 圖表與表格的 UI 文字 ─────────────────────────────────
    #
    # ⚠️ 這些收進來之後，**兩版頁面的 JS 完全相同、只有 T 與 L 不同**。
    #    原本只打算收限定語，但那樣會產生兩份各自演化的繪圖程式碼——
    #    本專案在名錄的 MAIN 上踩過那個坑。
    "chart_party_aria": {
        "zh": "九屆政黨得票率折線圖，數值見下方表格",
        "en": "Party vote share across nine terms; values in the table below",
    },
    "chart_seat_aria": {
        "zh": "逐屆政黨席次堆疊條，數值見下方表格",
        "en": "Seats by party and term, stacked; values in the table below",
    },
    "chart_turnout_aria": {
        "zh": "{code} 投票率 {series}",
        "en": "{code} turnout {series}",
    },
    "tip_party": {
        "zh": "{year}　{party}\n得票率 {share}%\n席次 {seats}",
        "en": "{year}　{party}\nvote share {share}%\nseats {seats}",
    },
    "tip_seat": {
        "zh": "{year}　{party}\n席次 {n} / {total}\n得票率 {share}%",
        "en": "{year}　{party}\nseats {n} / {total}\nvote share {share}%",
    },
    "tip_turnout": {
        "zh": "{year}　{name}\n投票率 {turnout}%\n選舉人 {electors}\n投票數 {votes}",
        "en": ("{year}　{name}\nturnout {turnout}%\nelectors {electors}\n"
               "votes cast {votes}"),
    },
    "th_party": {"zh": "政黨", "en": "Party"},
    "th_term": {"zh": "屆別", "en": "Term"},
    "th_total": {"zh": "合計", "en": "Total"},
    "th_turnout_total": {"zh": "合計投票率", "en": "Combined turnout"},
    "th_turnout_suffix": {"zh": "{name} 投票率", "en": "{name} turnout"},
    "th_electors_suffix": {"zh": "{name} 選舉人", "en": "{name} electors"},
    "th_threshold": {"zh": "門檻", "en": "Threshold"},
    "th_stations": {"zh": "所數", "en": "Stations"},
    "th_coverage": {"zh": "涵蓋率", "en": "Coverage"},
    "th_observed": {"zh": "觀察", "en": "Observed"},
    "th_observed_full": {"zh": "觀察得票率", "en": "Observed vote share"},
    "th_bounds": {"zh": "界限", "en": "Bounds"},
    "th_lower": {"zh": "界限下界", "en": "Lower bound"},
    "th_upper": {"zh": "界限上界", "en": "Upper bound"},
    "term_option": {"zh": "{term} 年", "en": "{term}"},
    "covbar_aria": {
        "zh": "涵蓋 {coverage}%，未涵蓋 {rest}%",
        "en": "{coverage}% covered, {rest}% not covered",
    },
    # ── index 頁的 UI 文字 ───────────────────────────────────
    "ref_group": {"zh": "參考組", "en": "Reference"},
    "ref_group_paren": {"zh": "（參考組）", "en": " (reference)"},
    "scope_election_name": {"zh": "{name}選舉", "en": "{name}"},
    "scope_indigenous_only": {"zh": "原住民專屬", "en": "Indigenous-only"},
    "scope_r2_seats": {"zh": "平地原住民代表席次",
                       "en": "Plain indigenous seats only"},
    "scope_reference": {"zh": "參考組，非原住民資料",
                        "en": "Reference group, not indigenous data"},
    "tip_turnout_typed": {
        "zh": "{year}　{code} {name}\n投票率 {turnout}%\n選舉人 {electors}\n投票數 {votes}",
        "en": ("{year}　{code} {name}\nturnout {turnout}%\nelectors {electors}\n"
               "votes cast {votes}"),
    },
    "chart_party_seats_aria": {
        "zh": "{code} 各屆政黨席次組成",
        "en": "{code}: composition of seats by party, each term",
    },
    "tip_party_seats": {
        "zh": "{year}　{code}\n{label}\n當選 {seats} 席 / 共 {total} 席\n候選人紀錄 {cands} 筆",
        "en": ("{year}　{code}\n{label}\nelected {seats} of {total} seats\n"
               "{cands} candidate records"),
    },
    "tip_gender": {
        "zh": "{year}　{code} {name}\n女性當選 {fseats} / {seats} 席\n女性候選人紀錄 {fcands} / {cands} 筆",
        "en": ("{year}　{code} {name}\nwomen elected {fseats} of {seats} seats\n"
               "women candidate records {fcands} of {cands}"),
    },
    "note_candidates_prefix": {"zh": "候選人 ", "en": "candidates "},
    "th_election_type": {"zh": "選舉種類", "en": "Election type"},
    "th_total_seats": {"zh": "總席次", "en": "Total seats"},
    "th_electors": {"zh": "選舉人數", "en": "Electors"},
    "th_votes": {"zh": "投票數", "en": "Votes cast"},
    "th_turnout": {"zh": "投票率", "en": "Turnout"},
    "th_seats": {"zh": "席次", "en": "Seats"},
    "th_cand_records": {"zh": "候選人紀錄", "en": "Candidate records"},
    "th_districts": {"zh": "選舉區", "en": "Districts"},
    "th_incumbent": {"zh": "現任當選/參選", "en": "Incumbents won/ran"},
    "th_uncontested": {"zh": "同額選區/席次", "en": "Uncontested districts/seats"},
    "no_such_election": {"zh": "無此選舉", "en": "no such election"},
    "no_incumbent": {"zh": "無現任", "en": "no incumbent"},
    "zero_women_note": {
        "zh": "T3、D2 各屆皆為 0（已確認，非漏算）",
        "en": "T3 and D2 are 0 in every term (confirmed, not a gap in the data)",
    },
    "party_label_kmt": {"zh": "中國國民黨", "en": "Kuomintang (KMT)"},
    "party_label_independent": {
        "zh": "999 無黨籍及未經政黨推薦",
        "en": "999 Independent / not party-nominated",
    },
    "party_label_dpp": {"zh": "民主進步黨", "en": "Democratic Progressive Party (DPP)"},
    "party_label_other": {"zh": "其他各政黨", "en": "All other parties"},
    "self_translated": {
        "zh": "本頁為專案自譯。",
        "en": ("This page is translated by the project and has not been "
               "reviewed by a native speaker. The Chinese version governs."),
    },
}

LANGUAGES = ("zh", "en")


def check_strings_complete() -> None:
    """每個 key 在每種語言都要有值，且代入欄位的集合要一致。

    ⚠️ 少一個語言 → 那一版的限定語會整句消失，而頁面照樣畫得出來。
    ⚠️ 欄位集合不一致 → 頁面上會留下未替換的 `{coverage}` 這種字樣。
    """
    missing = [f"{k}.{lang}" for k, v in STRINGS.items()
               for lang in LANGUAGES if not v.get(lang, "").strip()]
    if missing:
        raise SiteDataError(
            f"STRINGS 缺少這些語言的值：{missing}。"
            f"限定語少一種語言，那一版就會整句消失而頁面照樣畫得出來。"
        )
    bad_fields = []
    for k, v in STRINGS.items():
        fields = {lang: set(re.findall(r"\{(\w+)\}", v[lang]))
                  for lang in LANGUAGES}
        if len({frozenset(f) for f in fields.values()}) != 1:
            bad_fields.append((k, {lang: sorted(f) for lang, f in fields.items()}))
    if bad_fields:
        raise SiteDataError(
            f"STRINGS 的代入欄位在不同語言間不一致：{bad_fields}。"
            f"欄位少一個，頁面上會留下未替換的大括號。"
        )


# ── 顯示標籤的英譯：逐項宣告，且每一項都要標出處 ───────────────────
#
# ⚠️ **出處不是裝飾。** 這個專案對「數字的出處」要求到寫進 spec，
#    對「名稱的出處」不該用另一套標準。造出來的譯名如果不標明，
#    讀者會當成官方譯名。
#
# 出處三值：
#   cec     —— 中選會英文站可查證的用法
#   common  —— 該組織自己公布的英文名
#   project —— **本專案自訂**，找不到官方或通行英文名
#
# ⚠️ 中選會英文站是 JS 渲染的，`WebFetch` 讀不到本文（與查政府資料開放
#    授權條款時同一個限制）。能查證到的只有搜尋摘要顯示的
#    "Lowland and Highland Indigene Legislator" 一類用法，所以
#    **選舉種類多數是 `project`**。查不到就標 project，不可標 cec 充數。
LABEL_SOURCES = ("cec", "common", "project")

LABELS_EN: dict[str, tuple[str, str]] = {
    # 選舉種類（地方公職）
    "議員(平地原住民)": ("City/County Councilor (Plain Indigenous)", "project"),
    "議員(山地原住民)": ("City/County Councilor (Mountain Indigenous)", "project"),
    "議員(區域)": ("City/County Councilor (Regional)", "project"),
    "直轄市原住民區長": ("Indigenous District Chief (Special Municipality)", "project"),
    "直轄市原住民區民代表": ("Indigenous District Representative (Special Municipality)", "project"),
    "鄉(鎮、市)民代表(平原)": ("Township Representative (Plain Indigenous)", "project"),
    "直轄市議員(原住民，未分平地／山地)": (
        "Special Municipality Councilor (Indigenous, plain/mountain not split)", "project"),
    "臺灣省議員(山地原住民)": ("Taiwan Provincial Assembly Member (Mountain Indigenous)", "project"),
    "臺灣省議員(平地原住民)": ("Taiwan Provincial Assembly Member (Plain Indigenous)", "project"),
    # 選舉種類（立委）——中選會英文站用 "Lowland/Highland Indigene Legislator"
    "立法委員(平地原住民)選舉": ("Legislator (Lowland Indigenous)", "cec"),
    "立法委員(山地原住民)選舉": ("Legislator (Highland Indigenous)", "cec"),
    # 政黨桶名
    "中國國民黨": ("Kuomintang (KMT)", "common"),
    "民主進步黨": ("Democratic Progressive Party (DPP)", "common"),
    "親民黨": ("People First Party (PFP)", "common"),
    "無黨團結聯盟": ("Non-Partisan Solidarity Union (NPSU)", "common"),
    "無黨籍": ("Independent", "project"),
    "無黨籍及未經政黨推薦": ("Independent / not party-nominated", "project"),
    "其他": ("Other", "project"),
    # 界限面板實際顯示得到的政黨（各屆各門檻前四名）
    "台灣民眾黨": ("Taiwan People's Party (TPP)", "common"),
    "時代力量": ("New Power Party (NPP)", "common"),
    "台灣團結聯盟": ("Taiwan Solidarity Union (TSU)", "common"),
    "新黨": ("New Party", "common"),
    "信心希望聯盟": ("Faith and Hope League", "common"),
}


def check_labels_have_provenance() -> None:
    """每個英譯標籤都要有合法的出處。"""
    bad = [(k, v) for k, v in LABELS_EN.items()
           if not (isinstance(v, tuple) and len(v) == 2
                   and v[0].strip() and v[1] in LABEL_SOURCES)]
    if bad:
        raise SiteDataError(
            f"這些標籤的英譯缺出處或出處不在 {LABEL_SOURCES}：{bad}。"
            f"造出來的譯名不標明出處，讀者會當成官方譯名。"
        )


def label_en(zh: str) -> str:
    """中文標籤的英譯。未宣告者**保留原文**，不猜。

    ⚠️ 保留原文是刻意的：界限的完整表格裡有 37 個沒有通行英文名的小黨，
       造 37 個英文名，讀者無從判斷哪些是真的。
    """
    hit = LABELS_EN.get(zh)
    return hit[0] if hit else zh


PUBLICATION_RECORD = ROOT / "docs" / "發布判定紀錄.md"

# 保留的歷史資料必須明文說它不代表本屆。
#
# ⚠️ **檢查一律比對這個具名字串，不可比對「2026」。** 頁尾本來就有
#    `更新：2026-08`，用年份當判準的檢查在標示被刪掉之後【照樣通過】——
#    那正是本專案在變異測試上反覆踩到的「斷言的是別的東西」。
#
# ⚠️ 值由 STRINGS 導出，**不在這裡再寫一份**——中英兩版的限定語必須
#    出自同一個來源，否則翻譯時會各自漂移。
CURRENT_TERM_NOTICE = STRINGS["current_term_notice"]["zh"]

# 判定為「含歷史選舉數字」而必須帶上本屆限定語的頁面 → 該頁的語言。
#
# ⚠️ 這份清單不是判定本身——判定在紀錄檔裡。這裡只列出「判定的後果是
#    要標示」的那些頁面，讓檢查有東西可比。兩邊不一致時以紀錄檔為準。
# ⚠️ 英文頁要比對**英文版**的限定語。比對中文版會讓英文頁永遠失敗，
#    比對「有沒有這個 key」則等於沒驗。
PAGES_REQUIRING_NOTICE = {
    "legislative.html": "zh",
    "en/legislative.html": "en",
}

# 被凍結的指標及其形狀。凍結的意思是**形狀不長大**，不只是數字不更新。
FROZEN_BOUNDS_SHAPE = {"terms": 5, "thresholds": 3}


def check_publication_record(record: Path = PUBLICATION_RECORD) -> None:
    """發布判定紀錄必須涵蓋 docs/ 下每一個 HTML，兩個方向都驗。

    ⚠️ 要擋的不是「判定寫錯」（那需要人看），而是**「多了一頁，
       沒有人想起要判定」**。後者是靜默的，而且會隨時間必然發生。
    """
    if not record.exists():
        raise SiteDataError(f"找不到發布判定紀錄 {record}")
    text = record.read_text(encoding="utf-8")

    # ⚠️ **必須遞迴。** `glob("*.html")` 不含子目錄——加了 docs/en/ 之後
    #    那兩頁會被安靜地跳過而不報錯，而「多了一頁沒人判定」正是這條
    #    檢查存在的理由。鍵用**相對路徑**而不是檔名：docs/index.html 與
    #    docs/en/index.html 的檔名相同，用檔名兩者會互相掩護。
    listed = set(re.findall(r"^\| `([^`]+\.html)` \|", text, re.M))
    docs = ROOT / "docs"
    on_disk = {p.relative_to(docs).as_posix() for p in docs.rglob("*.html")}

    missing = sorted(on_disk - listed)
    if missing:
        raise SiteDataError(
            f"這些已發布的頁面不在發布判定紀錄裡：{missing}。"
            f"每一頁都必須有一次明文判定——見 {record.name}。"
        )
    phantom = sorted(listed - on_disk)
    if phantom:
        raise SiteDataError(
            f"發布判定紀錄列了不存在的頁面：{phantom}。"
            f"紀錄與 docs/ 必須兩個方向都對得上。"
        )

    if "| 投票日 |" not in text:
        raise SiteDataError(f"{record.name} 缺少「投票日」欄位")
    if "未查證" in text.split("## 逐頁判定")[0]:
        phase = re.search(r"\| \*\*目前階段\*\* \| \*\*(.+?)\*\* \|", text)
        if not phase or phase.group(1) != "選舉期間":
            raise SiteDataError(
                "投票日標為未查證時，目前階段必須是「選舉期間」（較嚴的一段）。"
                "查證前不會誤放行，只會誤攔截。"
            )


# SVG 規格要求的固定命名空間 URI，`document.createElementNS()` 用它建立
# SVG 元素——瀏覽器不會對這個字串發出任何網路請求，不算外部資源。
SVG_NAMESPACE_URI = "http://www.w3.org/2000/svg"


def check_no_external_resources(docs: Path | None = None) -> None:
    """`docs/` 底下的頁面不得含任何外部資源參照。

    ⚠️ 站台明訂「不連外部資源」（離線開啟、單檔分享、file:// 下不被 CORS
       擋住）——曾經悄悄違反過這個承諾（Google Fonts 的 <link>），沒有
       任何檢查會擋下，直到人工審查才發現。這條檢查把承諾變成會失敗的斷言。

    `docs` 參數只供測試餵合成目錄用，正式流程一律用預設值（真正的 docs/）。
    """
    docs = docs or (ROOT / "docs")
    pattern = re.compile(r'https?://[^\s"\'<>]+')
    for path in sorted(docs.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        found = [m for m in pattern.findall(text) if m != SVG_NAMESPACE_URI]
        if found:
            try:
                label = path.relative_to(ROOT).as_posix()
            except ValueError:
                label = str(path)
            raise SiteDataError(
                f"{label} 含外部資源參照："
                f"{found}。站台明訂不連外部資源（離線開啟、單檔分享）。"
            )


# 導覽標籤與 <h1> 不得使用的說法——暗示比資料實際能撐起的解讀更強。
# 內文限定語裡出現這些詞是合法的（用來劃清界線），這份清單只管
# check_no_overclaiming_labels() 掃描的兩個區塊，不是整份檔案。
OVERCLAIMING_TERMS = ("政黨傾向", "政黨版圖", "party leaning", "Party Politics")

_NAV_RE = re.compile(r"<nav\b[^>]*>.*?</nav>", re.DOTALL)
_H1_RE = re.compile(r"<h1\b[^>]*>.*?</h1>", re.DOTALL)


def check_no_overclaiming_labels(docs: Path | None = None) -> None:
    """導覽標籤與 <h1> 不得暗示比資料能撐起的更強的解讀。

    ⚠️ 只掃描 <nav>／<h1> 這兩個區塊，不是整份檔案——「政黨傾向」在內文
       限定語裡是合法用法（用來說「這才是政黨傾向、其他數字不是」），
       整份檔案級的比對會把那種正確用法也擋下來。

    `docs` 參數只供測試餵合成目錄用，正式流程一律用預設值（真正的 docs/）。
    """
    docs = docs or (ROOT / "docs")
    for path in sorted(docs.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        try:
            label = path.relative_to(ROOT).as_posix()
        except ValueError:
            label = str(path)
        for block_name, block_re in (("nav", _NAV_RE), ("h1", _H1_RE)):
            m = block_re.search(text)
            if not m:
                continue
            block = m.group(0)
            for term in OVERCLAIMING_TERMS:
                if term in block:
                    raise SiteDataError(
                        f"{label} 的 <{block_name}> 含過強的說法「{term}」——"
                        f"暗示比資料實際能撐起的解讀更強。"
                    )


# 資料集地圖必須出現的頁面 → 語言碼。五個已發布頁面全部列在這裡——
# roster.html 沒有頁內目錄（見 check_section_ids_match_toc()），但仍要有
# 資料集地圖，讓讀者不管從哪一頁進站都知道還有哪些資料集。
DATASET_MAP_PAGES: dict[str, str] = {
    "index.html": "zh",
    "roster.html": "zh",
    "legislative.html": "zh",
    "en/index.html": "en",
    "en/legislative.html": "en",
}


def check_dataset_map_present(docs: Path | None = None) -> None:
    """`DATASET_MAP_PAGES` 列出的每個頁面都要含與 `STRINGS["dataset_map"]`
    逐字相同的資料集地圖說明。

    ⚠️ 比對邏輯與 `check_static_qualifiers()` 相同：排除 `<script>` 區塊，
       量到的是讀者看得到的那份文字，不是頁面的 `T` 常數。

    `docs` 參數只供測試餵合成目錄用，正式流程一律用預設值（真正的 docs/）。
    """
    check_strings_complete()
    docs = docs or (ROOT / "docs")
    for name, lang in DATASET_MAP_PAGES.items():
        page = docs / name
        if not page.exists():
            continue
        html = re.sub(r"<script>.*?</script>", "",
                       page.read_text(encoding="utf-8"), flags=re.S)
        want = STRINGS["dataset_map"][lang]
        if want not in html:
            raise SiteDataError(
                f"{name} 缺少資料集地圖說明（{lang}）：{want!r}。"
                f"每個已發布頁面都必須讓讀者知道還有哪些資料集、彼此不可比較。"
            )


# 多節頁面 → 該頁 <section id="..."> 的期望順序。roster.html 不在這裡：
# 它是單頁名錄，沒有多個 <section>，不需要頁內目錄。
TOC_PAGES: dict[str, tuple[str, ...]] = {
    "index.html": ("scope", "turnout", "party", "gender", "scale",
                    "perseat", "custom"),
    "legislative.html": ("scope", "partyvote", "seats", "turnout", "bounds"),
    "en/index.html": ("scope", "turnout", "party", "gender", "scale",
                        "perseat", "custom"),
    "en/legislative.html": ("scope", "partyvote", "seats", "turnout", "bounds"),
}

_SECTION_ID_RE = re.compile(r'<section\b[^>]*\bid="([^"]+)"')
_TOC_RE = re.compile(r'<nav class="toc"[^>]*>(.*?)</nav>', re.DOTALL)
_TOC_HREF_RE = re.compile(r'<a\s+href="#([^"]+)"')


def check_section_ids_match_toc(docs: Path | None = None) -> None:
    """`TOC_PAGES` 列出的每個頁面，其 `<section id>` 序列必須與
    `<nav class="toc">` 內的 `href="#id"` 序列完全一致（相同集合、相同順序）。

    ⚠️ 目錄是手寫的（見 design.md「頁內目錄是手寫的 `<nav class="toc">`，
       用一致性檢查而非生成保證正確」），這條檢查擋的是目錄與實際 section
       之間的脫節——新增／刪除／搬動一節卻忘了同步改目錄，兩邊都不會
       各自報錯，只有比對過才看得出來。

    `docs` 參數只供測試餵合成目錄用，正式流程一律用預設值（真正的 docs/）。
    """
    docs = docs or (ROOT / "docs")
    for name, expected in TOC_PAGES.items():
        page = docs / name
        if not page.exists():
            continue
        html = page.read_text(encoding="utf-8")
        section_ids = tuple(_SECTION_ID_RE.findall(html))
        toc_match = _TOC_RE.search(html)
        toc_ids = tuple(_TOC_HREF_RE.findall(toc_match.group(1))) if toc_match else ()

        if not toc_match:
            raise SiteDataError(f"{name} 沒有 <nav class=\"toc\">，但列在 TOC_PAGES 裡。")
        if section_ids != expected:
            raise SiteDataError(
                f"{name} 的 <section id> 序列 {section_ids} 與期望的 {expected} 不同。"
            )
        if toc_ids != expected:
            missing = set(expected) - set(toc_ids)
            extra = set(toc_ids) - set(expected)
            raise SiteDataError(
                f"{name} 的頁內目錄與 section id 不一致："
                f"目錄序列 {toc_ids}，期望 {expected}"
                f"（目錄少列 {sorted(missing)}，目錄多連 {sorted(extra)}）。"
            )


# 頁面上以**靜態 HTML** 呈現的限定語：頁面 → (語言, 必須逐字出現的 key)。
#
# ⚠️ **為什麼不把這些也交給 JS 從 `T` 注入**：那會讓「沒有 JS 就沒有限定語」。
#    限定語是這個專案的主要價值，不能依賴腳本執行成功。
#    所以文字留在 HTML 裡，改用檢查釘住它與 STRINGS 逐字相同——
#    單一來源的效果一樣達到，而且限定語在原始碼裡看得到。
STATIC_QUALIFIERS: dict[str, tuple[str, tuple[str, ...]]] = {
    "legislative.html": ("zh", ("not_party_identification",
                                "datasets_not_comparable")),
    "en/legislative.html": ("en", ("not_party_identification",
                                   "datasets_not_comparable",
                                   "self_translated")),
}


def check_static_qualifiers() -> None:
    """靜態限定語必須與 STRINGS 逐字相同。

    ⚠️ 這條擋的是**翻譯時把限定語改順、順帶改弱**。文字在 HTML 裡，
       所以有人可以直接改它而不動 STRINGS——那正是兩份來源會漂移的路徑。
    """
    check_strings_complete()
    for name, (lang, keys) in STATIC_QUALIFIERS.items():
        page = ROOT / "docs" / name
        if not page.exists():
            continue
        # ⚠️ **排除 script 區塊。** 限定語同時存在於頁面的 `const T` 常數裡，
        #    grep 整個檔案的話，把讀者看得到的那份刪掉也照樣通過——
        #    量到的是 T，不是頁面上的字。實測就是這樣漏掉的。
        html = re.sub(r"<script>.*?</script>", "",
                      page.read_text(encoding="utf-8"), flags=re.S)
        for key in keys:
            want = STRINGS[key][lang]
            if want not in html:
                raise SiteDataError(
                    f"{name} 缺少限定語 {key}（{lang}）：{want!r}。"
                    f"頁面上的限定語必須與 STRINGS 逐字相同——"
                    f"改頁面不改 STRINGS，兩份來源就開始漂移。"
                )


def check_current_term_notice() -> None:
    """判定為含歷史選舉數字的頁面，必須帶該語言的本屆限定語。

    ⚠️ **這支必須在 `--write` 之後跑。** 限定語由 STRINGS 產生、寫進頁面的
       `T` 常數，寫入之前它不在檔案裡——放在寫入前會讓每次 `--write` 都被
       自己還沒寫入的東西擋下。涵蓋檢查沒有這個問題（它只看檔案集合），
       所以那一支留在最前面。

    ⚠️ 英文頁比對**英文版**的限定語。比對中文版會讓英文頁永遠失敗；
       只檢查「有沒有這個 key」則等於沒驗。
    """
    check_strings_complete()
    for name, lang in PAGES_REQUIRING_NOTICE.items():
        page = ROOT / "docs" / name
        if not page.exists():
            continue
        html = page.read_text(encoding="utf-8")
        # ⚠️ 兩個條件都要，缺一個都沒有辨識力：
        #    (1) 該語言的限定語在頁面的 T 常數裡
        #    (2) JS 真的把它畫出來
        #    只驗 (1) → 把 JS 裡用它的那行刪掉照樣通過。
        #    只驗 (2) → T 是空的也照樣通過。
        if STRINGS["current_term_notice"][lang] not in html:
            raise SiteDataError(
                f"{name} 判定為含歷史選舉數字，但頁面沒有 {lang} 版的本屆限定語。"
                f"選舉期間保留的歷史資料必須明文標示不代表本屆。"
            )
        if "T.current_term_notice" not in html:
            raise SiteDataError(
                f"{name} 的 T 常數裡有本屆限定語，但頁面沒有任何地方用到它——"
                f"讀者看不到的限定語等於沒有。"
            )

def check_frozen_indicator_shape(bounds: dict) -> None:
    """被凍結的指標，形狀不得長大。

    ⚠️ 多一屆、多一個門檻都算擴充，**即使既有的每個數字都沒變**——
       它擴大了這個指標所主張的範圍。
    """
    got = {"terms": len(bounds["terms"]), "thresholds": len(bounds["thresholds"])}
    if got != FROZEN_BOUNDS_SHAPE:
        raise SiteDataError(
            f"政黨傾向界限已凍結，形狀不得改變："
            f"宣告 {FROZEN_BOUNDS_SHAPE}、實際 {got}。"
            f"解凍條件見 docs/發布判定紀錄.md（2026-12-04 公告當選人名單後）。"
        )


_ZH_HEADING_PARSER: budoux.Parser | None = None


def _zh_heading_parser() -> budoux.Parser:
    global _ZH_HEADING_PARSER
    if _ZH_HEADING_PARSER is None:
        _ZH_HEADING_PARSER = budoux.load_default_traditional_chinese_parser()
    return _ZH_HEADING_PARSER


_HEADING_RE = re.compile(r"<(h[12])>(.*?)</\1>")


def segment_headings(html: str, label: str = "") -> str:
    """替中文頁面 `<h1>`／`<h2>` 的純文字插入 BudouX 語意斷詞的 `<wbr>`。

    ⚠️ 冪等：先剝除既有的 `<wbr>`（或舊式手動 `<br>`）還原純文字，
       再重新斷詞組回——連續執行兩次輸出不變，而不是靠「看到 <wbr> 就跳過」
       這種粗略判斷（那樣會漏掉新增的標題）。

    只接受純文字或純文字加 `<br>` 這兩種既有樣式；標題內若含其他子標籤，
    直接中止並在錯誤訊息帶上檔名與原始文字，不可靜默略過。
    """
    parser = _zh_heading_parser()

    def replace(match: re.Match) -> str:
        tag = match.group(1)
        inner = match.group(2)
        text = inner.replace("<wbr>", "").replace("<br>", "")
        if "<" in text:
            raise SiteDataError(
                f"{label}：<{tag}> 內含不支援的子標籤，segment_headings 只接受"
                f"純文字或既有 <br>，實際內容為 {inner!r}"
            )
        chunks = parser.parse(text)
        return f"<{tag}>{'<wbr>'.join(chunks)}</{tag}>"

    return _HEADING_RE.sub(replace, html)


def build_strings(lang: str) -> dict:
    """該語言的限定語與圖表文案。

    ⚠️ 中英兩版都從 STRINGS 取值，**頁面裡不再寫第二份**。
    """
    check_strings_complete()
    if lang not in LANGUAGES:
        raise SiteDataError(f"未知的語言 {lang!r}（已宣告 {LANGUAGES}）")
    return {k: v[lang] for k, v in STRINGS.items()}


def build_labels(lang: str) -> dict:
    """資料裡的中文標籤 → 該語言的顯示字。

    中文版是恆等對映（讓兩版的 JS 走同一條路），英文版查 LABELS_EN，
    **查不到就保留原文**。
    """
    check_labels_have_provenance()
    if lang == "zh":
        return {}
    return {zh: en for zh, (en, _src) in LABELS_EN.items()}


BOUNDS_THRESHOLDS = ("0.95", "0.90", "0.80")


def build_bounds_data(bounds: list[dict]) -> dict:
    """政黨傾向界限的頁面常數。

    ⚠️ **涵蓋率是主資料，不是註腳。** 每個（屆別, 門檻）的涵蓋率與所數與
       界限放在同一層，頁面才有辦法把它排在任何百分比之前。
    """
    thresholds = list(BOUNDS_THRESHOLDS)
    terms = sorted({r["屆別"] for r in bounds})
    meta: dict[str, dict] = {y: {} for y in terms}
    rows: dict[str, dict] = {y: {t: [] for t in thresholds} for y in terms}
    for r in bounds:
        y, t = r["屆別"], r["門檻"]
        if t not in thresholds:
            raise SiteDataError(
                f"界限表出現未宣告的門檻 {t!r}（已宣告 {thresholds}）"
            )
        meta[y][t] = {
            "stations": int(r["所數"]),
            "electors": int(r["涵蓋原住民選舉人"]),
            "coverage": float(_round_half_up(
                Decimal(r["涵蓋率"]) * 100, "0.1")),
        }
        rows[y][t].append([
            r["政黨名稱"],
            float(_round_half_up(Decimal(r["觀察_得票率"]) * 100, "0.01")),
            float(_round_half_up(Decimal(r["下界_原住民得票率"]) * 100, "0.01")),
            float(_round_half_up(Decimal(r["上界_原住民得票率"]) * 100, "0.01")),
        ])

    missing = [(y, t) for y in terms for t in thresholds if not rows[y][t]]
    if missing:
        raise SiteDataError(
            f"界限表缺少這些（屆別, 門檻）組合：{missing}。"
            f"三個門檻必須並列——少一個等於替讀者挑了一個。"
        )
    for y in terms:
        for t in thresholds:
            rows[y][t].sort(key=lambda x: -x[1])
    out = {"terms": terms, "thresholds": thresholds,
           "meta": meta, "rows": rows}
    # ⚠️ 在這裡呼叫，不是在 main()——任何取得 BOUNDS 的路徑都要經過凍結檢查。
    #    只在 main() 檢查的話，測試與其他呼叫端拿到的是沒被檢查過的東西。
    check_frozen_indicator_shape(out)
    return out


def site_mark(row: dict) -> str:
    """名錄顯示的當選註記。

    ⚠️ 當選與否取自 `當選`（權威值），**不是** `當選註記`——後者忠實反映
    來源錯誤（2005 兩檔與 1994 高雄市）。但婦女保障 `!` 與被排擠 `-` 這兩個
    區別只存在於 `當選註記`，權威值欄無法表達，故那兩個值原樣保留：
      - `!` 婦女保障當選 —— 是當選，保留 `!` 以便站台區別呈現
      - `-` 因婦女保障被排擠未當選 —— 不是當選，保留 `-`
    其餘一律由權威值決定：當選為 `*`、未當選為空字串。
    健康屆別下這條規則與原本的 `當選註記` 完全一致。
    """
    mark = row["當選註記"]
    if mark in ("!", "-"):
        return mark
    return "*" if row["當選"] == "Y" else ""


def build_roster_data(summary: list[dict], cands: list[dict],
                      only_terms: list[str] | None = None) -> dict:
    """算出 `docs/roster.html` 的 `D` 常數。

    形狀：`parties` 為政黨名稱清單（候選人 tuple 以索引參照）、`years` 為屆別、
    `rows` 為 {屆別: {選舉種類: [[縣市名, 區名, [候選人 tuple, ...]], ...]}}。
    候選人 tuple 為 `[號次, 姓名, 政黨索引, 女性, 年齡, 現任, 註記]`。
    """
    all_terms = terms(summary)
    keep = set(only_terms) if only_terms else set(all_terms)
    years = [y for y in all_terms if y in keep]
    kept = [c for c in cands if c["年度"] in keep]

    # 政黨清單的順序＝在長表中**首次出現**的順序。
    #
    # ⚠️ 這不是任意選的：實測與站台現有常數的 59 個政黨順序完全相同
    #    （另外試過「候選人數由多到少」、「席次由多到少」、「政黨代號排序」
    #    三種，都不符）。沿用它才能讓「資料未變則輸出位元組不變」成立——
    #    政黨索引在名錄中出現數千次，換一個排序會讓一位數／兩位數索引重新分配，
    #    檔案長度就變了（實測差 84 bytes），真正的差異會被埋在長度變化裡。
    #
    # 長表本身的列順序是穩定的（由 build_local_election.py 的屆別與種類迴圈
    # 決定），所以這個規則是可重現的，不依賴字典的插入順序以外的任何東西。
    parties: list[str] = []
    seen_parties: set[str] = set()
    for c in kept:
        name = c["政黨名稱"]
        if name not in seen_parties:
            seen_parties.add(name)
            parties.append(name)
    p_index = {n: i for i, n in enumerate(parties)}

    # 候選人記在鄉鎮市區層級的選舉種類。粒度**由資料推導**，不寫死種類——
    # 與 build_index_data 的 uses_town 同一判準，但這裡要逐種類算一次，
    # 因為分組必須在整個屆別範圍內一致（同一種類不可有些組含鄉鎮市區、有些不含）。
    town_level_types = {
        code for code in {c["選舉種類"] for c in kept}
        if any(not is_blank(c["鄉鎮市區"]) for c in kept
               if c["選舉種類"] == code)
    }

    # 縣市名稱取自 summary 的縣市層級列——候選人列的 `行政區名稱` 是選舉區或
    # 鄉鎮市區的名稱，不是縣市名。
    county_name: dict[tuple[str, str, str], str] = {}
    for r in summary:
        if r["層級"] == "直轄市縣市":
            county_name[(r["年度"], r["省市"], r["縣市"])] = r["行政區名稱"]

    # 鄉鎮市區名稱的回填來源。
    #
    # ⚠️ 為什麼需要：2014 年 D2（直轄市原住民區長）的 20 位候選人，`行政區名稱`
    #    **全部為空**——該屆 elbase 的選舉區欄與 elprof 不一致，名稱查表必然落空
    #    （這是長表 validation report 記錄的 417 次「行政區名稱查無」）。
    #    若用名稱當分組鍵，高雄市的三個原住民區會被併成一組。
    #
    # ⚠️ 只取【選舉區欄為空白】的鄉鎮市區層級列。非空白者的名稱含選舉區後綴
    #    （如「茂林區第01選舉區」，來自 R3），那不是鄉鎮市區的名稱。
    # ⚠️ 只在同一個行政區代碼系統內回填。跨代碼系統的同一組代碼指的是不同地方。
    town_name: dict[tuple[str, str, str, str], str] = {}
    for r in summary:
        if r["層級"] != "鄉鎮市區" or not is_blank(r["選舉區"]):
            continue
        if not r["行政區名稱"]:
            continue
        k = (r["admin_code_system"], r["省市"], r["縣市"], r["鄉鎮市區"])
        prev = town_name.setdefault(k, r["行政區名稱"])
        if prev != r["行政區名稱"]:
            raise SiteDataError(
                f"鄉鎮市區 {k} 在同一代碼系統內出現兩個名稱："
                f"{prev!r} 與 {r['行政區名稱']!r}——無法安全回填"
            )

    # 檔別合計列的行政區名稱。1994 台灣省議員的 elbase 只有「臺灣省」一列，
    # 沒有縣市層級，所以縣市標籤只能退到這裡取。
    file_total_name: dict[tuple[str, str, str], str] = {}
    for r in summary:
        if r["層級"] == "檔別合計" and r["行政區名稱"]:
            file_total_name[(r["年度"], r["選舉種類"], r["檔別"])] = r["行政區名稱"]

    BACKFILL_SUFFIX = "（名稱由鄉鎮市區回填）"
    NO_NAME_SUFFIX = "（來源無選舉區名稱）"

    def county_label(c: dict) -> str:
        """縣市標籤。1994 省議員沒有縣市層級，退到檔別合計列的「臺灣省」。"""
        name = county_name.get((c["年度"], c["省市"], c["縣市"]))
        if name:
            return name
        return file_total_name.get((c["年度"], c["選舉種類"], c["檔別"]), "")

    def district_label(c: dict) -> str:
        """該候選人所屬選舉區的顯示名稱。三層依序，每層退讓都留下痕跡。

        ⚠️ 第三層（以檔別標示）目前只用於 **1994 台灣省議員的「平原2」**：
           該檔的 elbase 沒有選舉區層級的列，來源真的沒有這個選舉區的名稱。
           而「平原」與「平原2」是**兩個不同的選舉區**（候選人完全不同），
           不可併成一組，所以必須有個能區分它們的標籤——檔別是唯一可用的。
        """
        # ⚠️ 代碼全為零時，`行政區名稱` 查到的其實是【檔別合計列】的名稱，
        #    不是選舉區的名稱。1994 台灣省議員的「平原」就是這種情形：它拿到
        #    「臺灣省」，而同一種類的「平原2」什麼都拿不到——兩個都沒有來源
        #    名稱，卻會得到不一致的標籤。這裡把它一併視為「來源無名稱」。
        ft = file_total_name.get((c["年度"], c["選舉種類"], c["檔別"]))
        all_blank = all(is_blank(c[f]) for f in ("省市", "縣市", "選舉區", "鄉鎮市區"))
        if c["行政區名稱"] and not (all_blank and c["行政區名稱"] == ft):
            return c["行政區名稱"]
        k = (c["admin_code_system"], c["省市"], c["縣市"], c["鄉鎮市區"])
        name = town_name.get(k)
        if name:
            return name + BACKFILL_SUFFIX
        if c["檔別"]:
            return c["檔別"] + NO_NAME_SUFFIX
        raise SiteDataError(
            f"{c['年度']} {c['選舉種類']} 的候選人 {c['姓名']} 找不到選舉區名稱，"
            f"鄉鎮市區代碼 {k} 無法回填，檔別也是空的——不輸出無標籤的分組"
        )

    # ⚠️ 分組鍵用【代碼】而不是名稱。名稱可能為空（見上），用它當鍵會把
    #    不同的行政區靜默併成一組。
    rows: dict[str, dict[str, dict[tuple, dict]]] = {}
    for c in kept:
        y, code = c["年度"], c["選舉種類"]
        uses_town = c["選舉種類"] in town_level_types
        gkey = district_key(c, uses_town)
        grp = rows.setdefault(y, {}).setdefault(code, {}).setdefault(
            gkey,
            {"county": county_label(c),
             "label": district_label(c), "cands": []},
        )
        grp["cands"].append([
            int(c["號次"]),
            c["姓名"],
            p_index[c["政黨名稱"]],
            1 if c["性別"] == "女" else 0,
            int(c["年齡"]) if c["年齡"] else None,
            1 if c["現任"] == "Y" else 0,
            site_mark(c),
        ])

    out_rows: dict[str, dict[str, list]] = {}
    for y in years:
        if y not in rows:
            continue
        out_rows[y] = {}
        for code, groups in rows[y].items():
            out_rows[y][code] = [
                # 組內：當選者在前，其次依號次
                [g["county"], g["label"],
                 sorted(g["cands"], key=lambda t: (t[6] not in ("*", "!"), t[0]))]
                for g in sorted(groups.values(),
                                key=lambda g: (g["county"], g["label"]))
            ]
    # ⚠️ 選舉種類清單由資料產生，不讓前端寫死。
    #    roster.html 原本有一份手寫的 TYPES 常數，只列官方六種——資料擴充到
    #    九屆之後，1994／1998／2002／2006 這四屆只有自訂代碼的資料，
    #    按鈕列不出來就等於那四屆完全點不到。這正是本次要消滅的漂移來源。
    meta = election_types(summary)
    types = [[code, meta[code]["name"], 0 if code == "T1" else 1]
             for code in meta
             if any(code in by_type for by_type in out_rows.values())]

    return {"types": types, "parties": parties, "years": years, "rows": out_rows}


def normalise_roster(d: dict) -> dict:
    """把名錄常數轉成可語意比對的形式：政黨索引還原為名稱。

    ⚠️ 為什麼需要這一步：`parties` 的排序是**偶然的編碼細節**，不是語意——
    `docs/roster.html` 只用它做索引→名稱的查表（單一處 `D.parties[pi]`），
    排序對畫面毫無影響。若直接比對索引，換一個排序就會產生數千項假差異，
    真正的差異會被埋掉。本專案的重現比對要驗的是**意義**，不是編碼。
    """
    parties = d["parties"]
    return {
        # 不含 types：那是本次刻意新增的鍵，見 INTENTIONAL_NEW_KEYS
        "years": d["years"],
        "rows": {
            y: {code: [[cty, dist,
                        [[t[0], t[1], parties[t[2]], t[3], t[4], t[5], t[6]]
                         for t in cs]]
                       for cty, dist, cs in groups]
                for code, groups in by_type.items()}
            for y, by_type in d["rows"].items()
        },
    }


DATA_MARKER = "const DATA = "
ROSTER_MARKER = "const D = "
ROSTER_MAIN_MARKER = "const MAIN = "
LEG_MARKER = "const LEG = "
BOUNDS_MARKER = "const BOUNDS = "
STRINGS_MARKER = "const T = "
LABELS_MARKER = "const L = "

# 只有這兩個中文頁面的靜態 <h1>/<h2> 套用 BudouX 斷詞。英文頁原生依空白斷行；
# roster.html 的 <h2> 是 JS 在瀏覽器端用縣市名稱動態產生，不是建置期靜態文字。
ZH_HEADING_PAGES = (ROOT / "docs" / "index.html", ROOT / "docs" / "legislative.html")


def build_roster_main() -> dict[str, int]:
    """名錄頁的 `MAIN`：政黨名稱 → 色槽索引。由同一份對照表投影而來。

    這一份先前是**手寫死在 HTML 裡的**（不在產生的 `D` 常數內），因此只認新屆的
    「無黨籍及未經政黨推薦」——舊屆的「無」在名錄裡拿到「其他」的顏色。
    同一個分類決策有兩份來源，其中一份必然會漂移。

    ⚠️ **這裡只能用名稱當鍵，因為名錄前端拿不到政黨代號。** 候選人 tuple 存的是
    `D.parties` 的索引，`pslot(name)` 只有名稱。這與圖表端以 (代號, 名稱) 配對
    分桶不同——是前端資料形狀的限制，不是判準放寬。

    ⚠️ 因此這個投影**可能是歧義的**：若對照表哪天讓同一個名稱在不同代號下歸到
    不同的桶，名稱就不足以決定色槽。那種情況下中止，不猜——要嘛把代號帶進
    名錄的資料形狀，要嘛承認這個名稱無法在名錄上正確著色。
    """
    slot_of = {b: i for i, b in enumerate(PARTY_BUCKETS)}
    out: dict[str, int] = {}
    for (code, name), bucket in PARTY_IDENTITY_BUCKETS.items():
        slot = slot_of[bucket]
        if name in out and out[name] != slot:
            raise SiteDataError(
                f"政黨名稱「{name}」在對照表中對應到兩個不同的桶"
                f"（色槽 {out[name]} 與 {slot}）。名錄端只有名稱可用，"
                f"無法決定色槽——不猜。需把政黨代號帶進名錄的資料形狀。"
            )
        out[name] = slot
    return out


def read_embedded_constant(path: Path, marker: str) -> dict:
    """讀出 HTML 中內嵌的資料常數。

    以固定的標記行界定，不做模糊比對——找不到標記行即中止。
    """
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(marker):
            return json.loads(line[len(marker):].rstrip().rstrip(";"))
    raise SiteDataError(
        f"{path.name} 找不到以 {marker!r} 開頭的標記行。"
        f"不做模糊比對——請確認該行未被改寫。"
    )


def diff_nested(new, old, path: str = "") -> list[str]:
    """逐鍵比對兩份巢狀結構，回傳差異描述。"""
    out: list[str] = []
    if isinstance(new, dict) and isinstance(old, dict):
        for k in sorted(set(new) | set(old)):
            p = f"{path}.{k}" if path else str(k)
            if k not in new:
                out.append(f"{p}: 新版缺少（舊值 {old[k]!r}）")
            elif k not in old:
                out.append(f"{p}: 舊版缺少（新值 {new[k]!r}）")
            else:
                out += diff_nested(new[k], old[k], p)
    elif isinstance(new, list) and isinstance(old, list):
        if len(new) != len(old):
            out.append(f"{path}: 長度 {len(new)} vs {len(old)}")
        else:
            for i, (a, b) in enumerate(zip(new, old)):
                out += diff_nested(a, b, f"{path}[{i}]")
    elif new != old:
        out.append(f"{path}: {new!r} vs 舊值 {old!r}")
    return out


# 重現比對時「刻意新增」而非「算錯」的差異。
#
# ⚠️ 這份清單刻意只有一項。1.2／1.4 的重現比對結果是 index 509 個葉節點、
#    roster 全部逐鍵相同——站台現有四屆的數字**沒有任何偏差**。
#    所以這裡不建「站台舊值錯」的登錄機制：那個集合是空的，
#    為空集合建登錄機制只會在真的出事時提供一個放行的地方
#    （同一個理由讓 include-1994-2006-terms 拿掉了未被使用的 elprof 回退規則）。
INTENTIONAL_NEW_KEYS = ("mainSequence", "types")


def unexpected_diffs(diffs: list[str]) -> list[str]:
    """濾掉刻意新增的欄位，回傳真正未預期的差異。"""
    return [d for d in diffs
            if not any(d.startswith(f"{k}: 舊版缺少") or f".{k}: 舊版缺少" in d
                       for k in INTENTIONAL_NEW_KEYS)]


def replace_constant_bytes(raw_bytes: bytes, marker: str, value: dict,
                           label: str) -> bytes:
    """把位元組中的資料常數換成 `value`，回傳完整位元組。

    ⚠️ 只替換以標記開頭的那一行，其餘位元組（含換行形式）原封不動。
       找不到標記行即中止，**不做模糊比對**——正則誤傷會安靜地改壞頁面。

    吃位元組而非路徑，是為了讓同一個檔案的**多處替換可以串接**
    （名錄頁有 `D` 與 `MAIN` 兩個常數）。若每次都從路徑重讀，
    第二次替換會讀到還沒寫入的舊內容，於是前一次的結果被安靜丟掉。
    """
    raw = raw_bytes.decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.split(newline)
    hits = [i for i, ln in enumerate(lines) if ln.startswith(marker)]
    if len(hits) != 1:
        raise SiteDataError(
            f"{label} 中以 {marker!r} 開頭的行有 {len(hits)} 個，預期恰為 1 個。"
            f"不做模糊比對。"
        )
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    lines[hits[0]] = f"{marker}{payload};"
    return newline.join(lines).encode("utf-8")


def replace_constant(path: Path, marker: str, value: dict) -> bytes:
    """算出把 HTML 的資料常數換成 `value` 之後的完整位元組。"""
    return replace_constant_bytes(path.read_bytes(), marker, value, path.name)


def report_other_bucket(cands: list[dict]) -> None:
    """列出「其他」桶逐屆的組成，由候選人數多到少。

    ⚠️ **這是給人看的，不是自動檢查。** 本專案刻意不對「其他」桶設任何自動門檻——
    已實測兩種被提議的門檻都不可用：

    - 「單一政黨佔該屆總候選人數 < 5%」：在修正舊屆無黨籍編碼之後**仍然會失敗**
      （2002 年「其他」由親民黨 28 人領先，28/164 = 17.1%）。舊屆規模太小
      （1994 全屆只有 23 位候選人），固定比例在那裡沒有意義。
    - 「其他桶成員必須小於具名桶」：舊屆的民進黨只有 3 至 7 人，比親民黨少，會誤報。

    所以偵測「下一個被錯誤歸戶的大政黨」這件事，靠的是**有人看這份輸出**。
    自動守得住的部分由 test_independent_bucket_non_empty_every_term 負責
    （無黨籍逐屆非零），那是具名的領域斷言而非統計門檻。
    """
    # ⚠️ 每一屆都要列出，包括「其他」為空的那些屆。靜默省略會讓讀者
    #    分不出「該屆沒有其他政黨」與「該屆的資料沒被算到」。
    totals: dict[str, int] = {}
    by_term: dict[str, dict[tuple[str, str], int]] = {}
    for c in cands:
        y = c["年度"]
        totals[y] = totals.get(y, 0) + 1
        by_term.setdefault(y, {})
        if party_bucket(c) == OTHER_BUCKET:
            k = (c["政黨代號"], c["政黨名稱"])
            by_term[y][k] = by_term[y].get(k, 0) + 1

    print()
    print("=== 「其他」桶逐屆組成（候選人數由多到少）===")
    print("⚠️ 沒有自動門檻在守這裡。若某一屆的首位佔比異常，"
          "可能是又一種跨屆編碼漂移——見 report_other_bucket 的 docstring。")
    for y in sorted(by_term):
        members = sorted(by_term[y].items(), key=lambda kv: (-kv[1], kv[0][0]))
        n = sum(v for _, v in members)
        if not members:
            print(f"  {y:<11} 共    0 人／該屆 {totals[y]:>4} 人"
                  f"　（該屆所有候選人都在具名桶內）")
            continue
        (top_code, top_name), top_n = members[0]
        print(f"  {y:<11} 共 {n:>4} 人／該屆 {totals[y]:>4} 人"
              f"　首位 {top_name}（{top_n} 人，佔該屆 {top_n / totals[y]:.1%}）")
        for (code, name), cnt in members:
            print(f"      {cnt:>4} 人  代號 {code:<4} {name}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR,
                    help="長表所在目錄（預設 data/processed）")
    ap.add_argument("--only-existing-terms", action="store_true",
                    help="只輸出站台現有常數涵蓋的屆別，供逐鍵比對")
    ap.add_argument("--diff-index", action="store_true",
                    help="與 docs/index.html 現有的 DATA 常數逐鍵比對並列出差異")
    ap.add_argument("--diff-roster", action="store_true",
                    help="與 docs/roster.html 現有的 D 常數逐鍵比對並列出差異")
    ap.add_argument("--write", action="store_true",
                    help="把算出的常數就地寫回兩個 HTML")
    ap.add_argument("--check", action="store_true",
                    help="只檢查不寫檔：現有屆別的重現若出現未預期差異即非零退出")
    args = ap.parse_args()

    summary, cands = load_long_tables(args.data_dir)
    ts = terms(summary)
    types = election_types(summary)

    print(f"summary {len(summary):,} 列、candidates {len(cands):,} 列")
    print(f"屆別 {len(ts)} 個：{'、'.join(ts)}")
    print("選舉種類：")
    for code, meta in types.items():
        flag = "主序列" if meta["mainSequence"] else "**不進主序列**"
        print(f"  {code:8s} {meta['name']:<22s} {flag}")

    report_other_bucket(cands)

    # 發布判定紀錄的涵蓋檢查。⚠️ 放在最前面，且 --write 與 --check 都跑——
    # 新增一頁卻沒有判定，要在寫任何檔案之前就中止。
    check_publication_record()
    print("✓ 發布判定紀錄涵蓋 docs/ 下每一個頁面")

    # 立委頁的兩個常數。三張立委長表與界限表只在這裡讀一次。
    #
    # ⚠️ 這幾張表【不參與】既有兩頁的重現比對——它們是另一組母體。
    #    詳見 docs/legislative.html 頂端的「這個頁面是什麼、不是什麼」。
    _direct: dict[str, dict] = {}

    def direct_values() -> dict[str, dict]:
        if not _direct:
            leg_s, leg_c, leg_v, leg_b = load_legislative_tables(args.data_dir)
            _direct[LEG_MARKER] = build_legislative_data(leg_s, leg_c, leg_v)
            _direct[BOUNDS_MARKER] = build_bounds_data(leg_b)
        return _direct

    # ⚠️ 語言相關的常數依頁面而不同，所以不能放進 direct_values()
    #    那個共用快取——它是以標記行為鍵的。
    def lang_values(lang: str) -> dict[str, dict]:
        return {STRINGS_MARKER: build_strings(lang),
                LABELS_MARKER: build_labels(lang)}

    if args.diff_index:
        index_html = ROOT / "docs" / "index.html"
        old = read_embedded_constant(index_html, DATA_MARKER)
        only = old["years"] if args.only_existing_terms else None
        new_data = build_index_data(summary, cands, only_terms=only)
        diffs = diff_nested(new_data, old)
        print()
        print(f"=== 與 {index_html.name} 現有 DATA 逐鍵比對 ===")
        print(f"比對範圍：{'僅現有屆別 ' + '、'.join(old['years']) if only else '全部屆別'}")
        if not diffs:
            print("  完全相同——產生器重現了現有常數")
        else:
            print(f"  差異 {len(diffs)} 項：")
            for d in diffs:
                print(f"    {d}")

    if args.write:
        # 先算完兩份、都成功了才落地——不產出半套結果。
        #
        # ⚠️ 名錄頁有【兩個】常數要換（`D` 與 `MAIN`），所以逐檔串接替換，
        #    每一步都吃上一步的位元組。若每步都從路徑重讀，
        #    第二次替換會把第一次的結果安靜丟掉。
        outputs = []
        for html, replacements in (
            (ROOT / "docs" / "index.html", [(DATA_MARKER, build_index_data),
                                            (STRINGS_MARKER, "zh"),
                                            (LABELS_MARKER, "zh")]),
            # 英文 index：DATA 與中文版完全相同，只有文案與標籤不同。
            (ROOT / "docs" / "en" / "index.html",
             [(DATA_MARKER, build_index_data),
              (STRINGS_MARKER, "en"), (LABELS_MARKER, "en")]),
            (ROOT / "docs" / "roster.html", [(ROSTER_MARKER, build_roster_data),
                                             (ROSTER_MAIN_MARKER, None)]),
            # 立委頁的兩個常數都不吃地方公職長表，走 direct 分支。
            (ROOT / "docs" / "legislative.html", [(LEG_MARKER, "direct"),
                                                  (BOUNDS_MARKER, "direct"),
                                                  (STRINGS_MARKER, "zh"),
                                                  (LABELS_MARKER, "zh")]),
            # 英文頁：**資料常數與中文版完全相同**，只有文案與標籤不同。
            (ROOT / "docs" / "en" / "legislative.html",
             [(LEG_MARKER, "direct"), (BOUNDS_MARKER, "direct"),
              (STRINGS_MARKER, "en"), (LABELS_MARKER, "en")]),
        ):
            if not html.exists():
                continue
            data = html.read_bytes()
            for marker, builder in replacements:
                if builder in LANGUAGES:
                    value = lang_values(builder)[marker]
                elif builder == "direct":
                    value = direct_values()[marker]
                elif builder is None:    # MAIN 不吃長表，只由對照表投影
                    value = build_roster_main()
                else:
                    only = (read_embedded_constant(html, marker)["years"]
                            if args.only_existing_terms else None)
                    value = builder(summary, cands, only_terms=only)
                data = replace_constant_bytes(data, marker, value, html.name)
            if html in ZH_HEADING_PAGES:
                data = segment_headings(data.decode("utf-8"), html.name).encode("utf-8")
            outputs.append((html, data))
        print()
        for html, data in outputs:
            before = html.read_bytes()
            if before == data:
                print(f"  {html.name} 內容未變，不寫入")
                continue
            html.write_bytes(data)
            print(f"  {html.name} 已更新（{len(before):,} → {len(data):,} bytes）")

    if args.check:
        # 重現檢查：只比現有屆別，且只有「刻意新增的欄位」可以不同。
        rc = 0
        for html, marker, builder, norm in (
            (ROOT / "docs" / "index.html", DATA_MARKER, build_index_data,
             lambda x: x),
            (ROOT / "docs" / "roster.html", ROSTER_MARKER, build_roster_data,
             normalise_roster),
        ):
            old = read_embedded_constant(html, marker)
            new_data = builder(summary, cands, only_terms=old["years"])
            diffs = unexpected_diffs(diff_nested(norm(new_data), norm(old)))
            print()
            if diffs:
                rc = 1
                print(f"★ {html.name} 有 {len(diffs)} 項未預期差異：")
                for d in diffs[:20]:
                    print(f"    {d}")
            else:
                print(f"✓ {html.name} 的現有屆別完全重現"
                      f"（僅刻意新增 {'、'.join(INTENTIONAL_NEW_KEYS)}）")
            # 位元組層的斷言。
            #
            # ⚠️ 上面的語意比對【看不到編碼層的變動】：名錄的比對會把政黨索引
            #    還原成名稱，所以換一個政黨排序它完全無感——但那會讓一位數／
            #    兩位數索引重新分配，檔案長度就變了（實測差 84 bytes）。
            #    真正要守的不變量是「資料未變 → 檔案未變」，那必須在位元組層驗。
            # ⚠️ 這裡【不剝除】刻意新增的欄位。剝除只在一次性遷移（站台還是
            #    手動維護的舊常數）時有意義；站台改由本腳本產生之後，
            #    要守的就是「重建 == 現況」。
            # ⚠️ 名錄頁的 `MAIN` 也必須納入這個斷言。它不參與上面的語意比對
            #    （那只比 `D`），所以少了這一步，`MAIN` 過時會完全沒人發現——
            #    而 `MAIN` 過時正是本次修正的第二個現場。
            rebuilt = replace_constant(html, marker, new_data)
            if marker == ROSTER_MARKER:
                rebuilt = replace_constant_bytes(
                    rebuilt, ROSTER_MAIN_MARKER, build_roster_main(), html.name)
            if rebuilt != html.read_bytes():
                rc = 1
                print(f"★ {html.name} 的位元組與現況不同"
                      f"（{len(html.read_bytes()):,} vs {len(rebuilt):,} bytes）——"
                      f"語意相同但編碼變了，例如政黨清單的排序改變")
        # 立委頁：沒有「既有屆別」要重現（它是本變更新增的），
        # 但「資料未變 → 檔案未變」這個不變量一樣要守——LEG 或 BOUNDS
        # 過時了，頁面照樣畫得出來，沒有人會發現。
        for leg_html, lang in ((ROOT / "docs" / "legislative.html", "zh"),
                               (ROOT / "docs" / "en" / "legislative.html", "en")):
            if not leg_html.exists():
                continue
            label = leg_html.relative_to(ROOT / "docs").as_posix()
            rebuilt = leg_html.read_bytes()
            for marker in (LEG_MARKER, BOUNDS_MARKER):
                rebuilt = replace_constant_bytes(
                    rebuilt, marker, direct_values()[marker], label)
            for marker in (STRINGS_MARKER, LABELS_MARKER):
                if marker.encode() in rebuilt:
                    rebuilt = replace_constant_bytes(
                        rebuilt, marker, lang_values(lang)[marker], label)
            print()
            if rebuilt != leg_html.read_bytes():
                rc = 1
                print(f"★ {label} 的位元組與現況不同"
                      f"（{len(leg_html.read_bytes()):,} vs {len(rebuilt):,} bytes）——"
                      f"常數未跟著長表或 STRINGS 重建")
            else:
                print(f"✓ {label} 的資料常數與文案與來源一致")

        # 標題斷詞：只有 ZH_HEADING_PAGES 這兩個中文頁面的 <h1>/<h2> 套用
        # BudouX。若現況跟重新斷詞的結果不同，代表標題被手動改過、
        # 卻沒有重新跑 --write 讓斷詞點跟上。
        for zh_html in ZH_HEADING_PAGES:
            if not zh_html.exists():
                continue
            text = zh_html.read_text(encoding="utf-8")
            rebuilt_text = segment_headings(text, zh_html.name)
            print()
            if rebuilt_text != text:
                rc = 1
                print(f"★ {zh_html.name} 的標題斷詞與現況不同——"
                      f"跑 --write 讓 <h1>/<h2> 套用最新的 BudouX 斷詞")
            else:
                print(f"✓ {zh_html.name} 的標題斷詞與現況一致")

        if rc:
            raise SystemExit(rc)

    # 內容面的檢查放在最後：限定語由 STRINGS 產生並寫入頁面，
    # 在 --write 完成之前它不在檔案裡。
    if args.write or args.check:
        check_static_qualifiers()
        print("✓ 靜態限定語與 STRINGS 逐字相同")
        check_current_term_notice()
        print("✓ 該標示本屆限定語的頁面都帶了對應語言的版本")
        check_no_external_resources()
        print("✓ docs/ 下的頁面都不含外部資源參照")
        check_no_overclaiming_labels()
        print("✓ 導覽標籤與 h1 都沒有過強的說法")
        check_dataset_map_present()
        print("✓ 已發布頁面都含資料集地圖說明")
        check_section_ids_match_toc()
        print("✓ 多節頁面的 section id 與頁內目錄一致")

    if args.diff_roster:
        roster_html = ROOT / "docs" / "roster.html"
        old = read_embedded_constant(roster_html, ROSTER_MARKER)
        only = old["years"] if args.only_existing_terms else None
        new_data = build_roster_data(summary, cands, only_terms=only)
        # 語意比對：政黨索引還原成名稱，排序差異不算差異
        diffs = diff_nested(normalise_roster(new_data),
                            normalise_roster(old))
        print()
        print(f"=== 與 {roster_html.name} 現有 D 逐鍵比對 ===")
        print(f"比對範圍：{'僅現有屆別' if only else '全部屆別'}")
        if not diffs:
            print("  完全相同——產生器重現了現有常數")
        else:
            print(f"  差異 {len(diffs)} 項（最多列 25 項）：")
            for d in diffs[:25]:
                print(f"    {d}")


if __name__ == "__main__":
    main()
