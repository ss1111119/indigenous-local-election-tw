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
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"

SUMMARY_FILE = "cec-local-election-summary-long.csv.gz"
CANDIDATES_FILE = "cec-local-election-candidates-long.csv"

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
# ⚠️ 缺欄即中止，不套用預設值也不跳過該欄。最要緊的是 elected_authoritative：
#    少了它會退回用 `當選`，而 `當選` 忠實反映來源錯誤——2005 縣市議員山原以
#    `當選` 只算出 18 席（正確 30）、平原 20（正確 27）。那種錯誤不會報錯，
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
        "當選註記", "elected_authoritative",
        "admin_code_system",
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
    return (
        read_long_table(data_dir / SUMMARY_FILE, REQUIRED_COLUMNS[SUMMARY_FILE]),
        read_long_table(data_dir / CANDIDATES_FILE,
                        REQUIRED_COLUMNS[CANDIDATES_FILE]),
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

    ⚠️ 所有與當選有關的數字一律取自 `elected_authoritative`，不用 `當選`。
    `當選` 忠實反映來源錯誤——2005 縣市議員山原以 `當選` 只算出 18 席
    （正確 30）、平原 20（正確 27）。用錯欄位站台會安靜地少 19 席。
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
            won = [c for c in rows if c["elected_authoritative"] == "true"]
            uses_town = any(not is_blank(c["鄉鎮市區"]) for c in rows)
            dists: dict[tuple, dict[str, int]] = {}
            for c in rows:
                d = dists.setdefault(district_key(c, uses_town),
                                     {"cands": 0, "seats": 0})
                d["cands"] += 1
                if c["elected_authoritative"] == "true":
                    d["seats"] += 1
            # 同額競選：該選舉區的候選人數等於當選人數
            unc = [d for d in dists.values() if d["cands"] == d["seats"]]

            party: dict[str, list[int]] = {b: [0, 0] for b in PARTY_BUCKETS}
            party[OTHER_BUCKET] = [0, 0]
            for c in rows:
                b = party_bucket(c)
                party[b][1] += 1
                if c["elected_authoritative"] == "true":
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


def site_mark(row: dict) -> str:
    """名錄顯示的當選註記。

    ⚠️ 當選與否取自 `elected_authoritative`，**不是** `當選註記`——後者忠實反映
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
    return "*" if row["elected_authoritative"] == "true" else ""


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
            int(c["年齡"]),
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
            (ROOT / "docs" / "index.html", [(DATA_MARKER, build_index_data)]),
            (ROOT / "docs" / "roster.html", [(ROSTER_MARKER, build_roster_data),
                                             (ROSTER_MAIN_MARKER, None)]),
        ):
            data = html.read_bytes()
            for marker, builder in replacements:
                if builder is None:      # MAIN 不吃長表，只由對照表投影
                    value = build_roster_main()
                else:
                    only = (read_embedded_constant(html, marker)["years"]
                            if args.only_existing_terms else None)
                    value = builder(summary, cands, only_terms=only)
                data = replace_constant_bytes(data, marker, value, html.name)
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
        if rc:
            raise SystemExit(rc)

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
