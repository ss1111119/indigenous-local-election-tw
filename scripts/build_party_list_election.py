#!/usr/bin/env python3
"""建置不分區政黨票（立委）五屆的長表，並算出原住民政黨傾向的界限。

資料來源與其他兩個資料集相同：`data/raw/cec-votedata.zip`。
涵蓋 2008／2012／2016／2020／2024 五屆的 `不分區政黨`，投開票所層級。

⚠️ **這個資料集回答的問題與另兩個不同。** 政黨票是全體選民一起投的，
   沒有按族別分開計票。要從它讀出原住民的政黨傾向，必須處理識別問題——
   本腳本的作法是輸出「觀察值 ＋ 數學上必然的區間」，
   **不做**生態迴歸外推。理由見 design 決策 1。

⚠️ **界限只約束「非原住民混入」，不約束「地理選擇偏誤」。**
   高原住民佔比的投開票所全在原住民族地區；都市裡的平地原住民（約三成）
   在門檻外，極限法對他們給不出有用的界限。任何引用這些數字的地方
   都必須先講涵蓋率與地理集中，不是當註腳。

用法：
    python scripts/build_party_list_election.py            # 建置
    python scripts/build_party_list_election.py --census    # 產生宣告常數
"""
from __future__ import annotations

import csv
import sys
import zipfile
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# ⚠️ 必須是【本檔所在的目錄】，不是 ROOT/"scripts"。
#    變異測試把副本放在 _mut/ 執行；寫成 ROOT/"scripts" 會把【真正的】
#    scripts/ 插到 sys.path 最前面，於是本檔之後 import 的 oracles 與
#    build_local_election 全部載入原版——針對它們的變異永遠不會生效。
#    既有的 build_local_election.py 與 build_legislative_election.py
#    都用這一行，我沒照抄。
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_local_election import (  # noqa: E402
    ValidationError,
    commit_outputs,
    read_csv,
    render_csv,
    zip_names,
)
import build_legislative_election as LEG  # noqa: E402
from oracles import (  # noqa: E402
    PARTY_LIST_MANIFEST,
    check_manifest_against,
    write_oracle_document,
)

ZIP_PATH = ROOT / "data" / "raw" / "cec-votedata.zip"
OUT_DIR = ROOT / "data" / "processed"
PREFIX = "votedata/votedata/voteData"

# 各檔的欄數。取自壓縮檔內的官方格式文件（選舉資料庫格式.odt），
# 不是由既有腳本或欄位位置推測。逐列檢查——只驗「至少幾欄」會讓
# 多出來的欄位靜默通過。
SOURCE_COLS = {
    "elbase": 6, "elcand": 16, "elpaty": 2, "elprof": 20,
    "elctks": 10, "elrepm": 10, "elretks": 5,
}

# 關聯鍵欄位（尾隨空白只在這些欄正規化，其餘原樣保留）。
# elrepm 的鍵是（政黨代號, 排名）；elretks 的鍵是政黨代號。
KEY_COLS = {
    "elbase": (0, 1, 2, 3, 4),
    "elcand": (0, 1, 2, 3, 4, 5, 7),
    "elpaty": (0,),
    "elprof": (0, 1, 2, 3, 4, 5),
    "elctks": (0, 1, 2, 3, 4, 5, 6),
    "elrepm": (0, 1),
    "elretks": (0,),
}

SOURCE_FILES = tuple(SOURCE_COLS)

# 五屆的資料夾。頂層名稱不規則（2008 是「2008立委」、2012 帶日期前綴），
# 逐屆具名而不用樣式推導。
TERM_FOLDERS = {
    "2008": "2008立委",
    "2012": "20120114-總統及立委",
    "2016": "2016總統立委",
    "2020": "2020總統立委",
    "2024": "2024總統立委",
}
SUBFOLDER = "不分區政黨"
TERMS = tuple(TERM_FOLDERS)

# 2016 的檔名帶類別後綴。
FILENAME_SUFFIX = {"2016": "_T4"}

# ⚠️ 後綴的例外：2016 的 elpaty 不帶後綴，與該屆其他六檔不同。
#    既有的 build_legislative_election 也記了同一件事。
FILES_WITHOUT_SUFFIX = frozenset({"elpaty"})

# 2016 有一份 old/ 重複目錄。既有腳本已具名排除，此處沿用同一個判準。
EXCLUDED_PATH_SEGMENT = "old"

# ⚠️ 「引號」有兩種，不要混為一談：
#    - CSV 雙引號包覆（"63","000"）由 csv.reader 透明處理，【不需宣告】。
#    - 值內的前置單引號（'0300317，Excel 強制文字）【必須具名宣告】，
#      因為它要被剝除，而剝除與否會改變鍵。
#    下面宣告的是後者。實測 7 個檔，2016 起完全沒有。
QUOTED_FILES: frozenset[tuple[str, str]] = frozenset({
    ("2008", "elcand"), ("2008", "elrepm"),
    ("2012", "elbase"), ("2012", "elcand"), ("2012", "elprof"),
    ("2012", "elctks"), ("2012", "elrepm"),
})

# 逐檔的列數。**由 `--census` 產生後貼上，不手抄。**
# 數量不符代表來源換版——中止而不是繼續。
#
# ⚠️ 手抄宣告值本身就是錯誤來源。這個 change 在宣告值上錯過八次，
#    其中四次的根因是「跑了普查、印出摘要、把摘要當成資料」——截斷、
#    四捨五入、只印一個分母各自銷毀了資訊，而摘要看起來永遠是完整的；
#    另一次是根本沒量就寫，還標成「普查值」。
#    來源換版後的正確流程是跑 `--census` 再貼上，不是逐個改。
EXPECTED_ROWS = {
    ("2008", "elbase"): 8204, ("2008", "elcand"): 12,
    ("2008", "elpaty"): 18, ("2008", "elprof"): 22581,
    ("2008", "elctks"): 270972, ("2008", "elrepm"): 128,
    ("2008", "elretks"): 18,
    ("2012", "elbase"): 8198, ("2012", "elcand"): 11,
    ("2012", "elpaty"): 16, ("2012", "elprof"): 23004,
    ("2012", "elctks"): 253044, ("2012", "elrepm"): 127,
    ("2012", "elretks"): 16,
    ("2016", "elbase"): 8216, ("2016", "elcand"): 18,
    ("2016", "elpaty"): 29, ("2016", "elprof"): 23798,
    ("2016", "elctks"): 428364, ("2016", "elrepm"): 179,
    ("2016", "elretks"): 29,
    ("2020", "elbase"): 8130, ("2020", "elcand"): 19,
    ("2020", "elpaty"): 46, ("2020", "elprof"): 25354,
    ("2020", "elctks"): 481726, ("2020", "elrepm"): 216,
    ("2020", "elretks"): 19,
    ("2024", "elbase"): 8270, ("2024", "elcand"): 16,
    ("2024", "elpaty"): 390, ("2024", "elprof"): 25924,
    ("2024", "elctks"): 414784, ("2024", "elrepm"): 177,
    ("2024", "elretks"): 16,
}


# 選區欄（第 3 碼）的允許值，逐屆逐檔宣告。
#
# ⚠️ 四個帶行政區代碼的檔對這一欄的用法各不相同，而且 2008 與 2012 起不同：
#    2012 起的規則是「彙總列 00、明細列 01」（那 23 列彙總列正好是鄉鎮市區
#    以上的層級：全國 1 ＋ 省市 6 ＋ 縣市 16）；**2008 連明細列都是 00**。
#
# ⚠️ 配對時必須【忽略】這一欄。不忽略的話，2008 的 elctks 有 22,555 個單位
#    對不上 elprof（22,581 中只有 26 對上）——而那會表現成「2008 幾乎全部
#    對不上」，不是報錯。
#
# 忽略一個欄位不等於放棄驗證它：這份宣告才是「可以忽略」的依據。
DISTRICT_ALLOWED = {
    "elbase": {"00"},
    "elcand": {"01"},
    "elctks": {"00", "01"},
    # elprof 逐屆不同，見 district_allowed()
}
DISTRICT_ALLOWED_ELPROF = {
    "2008": {"00"},
    "2012": {"00", "01"},
    "2016": {"00", "01"},
    "2020": {"00", "01"},
    "2024": {"00", "01"},
}

# 有行政區代碼、需要驗選區欄的檔。elpaty／elrepm／elretks 沒有代碼欄。
GEO_FILES = ("elbase", "elcand", "elprof", "elctks")


def district_allowed(year: str, stem: str) -> set[str]:
    """該屆該檔的選區欄允許值。"""
    if stem == "elprof":
        return DISTRICT_ALLOWED_ELPROF[year]
    return DISTRICT_ALLOWED[stem]


def check_district_values(year: str, stem: str,
                          rows: list[list[str]]) -> None:
    """選區欄不得出現宣告外的值。"""
    if stem not in GEO_FILES:
        return
    got = {r[2] for r in rows}
    want = district_allowed(year, stem)
    if got != want:
        raise ValidationError(
            f"{year} {stem} 的選區欄實得 {sorted(got)}、宣告允許 {sorted(want)}。"
            f"配對時忽略這一欄的前提是它只有已查明的用法；"
            f"取值改變代表來源結構變了，不可自動接受。"
        )


def unit_key(row: list[str]) -> tuple[str, ...]:
    """行政單位鍵，**忽略選區欄**。

    ⚠️ 不忽略的話 2008 的 elctks 與 elprof 幾乎完全對不上。
    """
    return (row[0], row[1], row[3], row[4], row[5])


def source_path(year: str, stem: str) -> str:
    """該屆該檔在壓縮檔內的路徑（還原後的名稱）。"""
    suffix = "" if stem in FILES_WITHOUT_SUFFIX else FILENAME_SUFFIX.get(year, "")
    return f"{PREFIX}/{TERM_FOLDERS[year]}/{SUBFOLDER}/{stem}{suffix}.csv"


def is_quoted(year: str, stem: str) -> bool:
    """該檔是否宣告為【值內帶前置單引號】。"""
    return (year, stem) in QUOTED_FILES


def check_quoting_declaration(year: str, stem: str,
                              first_row: list[str]) -> None:
    """雙向核對引號宣告與來源實況。任一方向不符即中止。

    ⚠️ 這裡刻意【不】用嗅探。嗅探會自動適應任何來源變化，
       因此永遠不會失敗——那就不是檢查。宣告與來源脫節時要有人知道：
       來源新增引號而未剝除，跨檔 join 會一列都對不上且不報錯；
       宣告過期而來源已無引號，下次真的有檔新增引號時這條也不會響。

    傳入的 first_row 必須是**未經剝除**的原始列。
    """
    found = any(cell.startswith("'") for cell in first_row)
    declared = is_quoted(year, stem)
    if found and not declared:
        raise ValidationError(
            f"{year} {stem}：來源的欄位值帶前置單引號，但未具名宣告。"
            f"未宣告即不剝除，跨檔 join 會一列都對不上且不報錯。"
            f"首列={first_row[:6]}"
        )
    if declared and not found:
        raise ValidationError(
            f"{year} {stem}：已具名宣告為帶前置單引號，但來源實際沒有。"
            f"宣告已過期——放著不管，下次真的有檔新增引號時這項檢查也不會響。"
            f"首列={first_row[:6]}"
        )


def check_no_excluded_path(path: str) -> None:
    """路徑不得落在具名排除的目錄內。"""
    parts = path.split("/")
    if EXCLUDED_PATH_SEGMENT in parts:
        raise ValidationError(
            f"路徑落在具名排除的目錄內：{path}。"
            f"2016 的 {EXCLUDED_PATH_SEGMENT}/ 是舊版重複資料，不可混入。"
        )


def raw_first_row(zf: zipfile.ZipFile, names: dict[str, str],
                  path: str) -> list[str]:
    """讀未經剝除的首列，供引號宣告核對。"""
    with zf.open(names[path]) as fh:
        text = fh.read().decode("utf-8-sig", errors="strict")
    for row in csv.reader(text.splitlines()):
        if row:
            return row
    raise ValidationError(f"{path} 沒有任何資料列")


def load_source(zf: zipfile.ZipFile, names: dict[str, str],
                year: str, stem: str,
                check_counts: bool = True) -> list[list[str]]:
    """讀一個來源檔，並在讀入時完成檢查。

    1. 路徑不落在具名排除的目錄內
    2. 引號宣告與來源實況雙向相符
    3. 欄數逐列恰好符合官方格式文件
    4. 列數與宣告相符、選區欄取值與宣告相符（`check_counts=False` 時略過）

    ⚠️ `check_counts=False` 只給 `--census` 模式用。census 不得讀取
       被它量測的宣告值，否則檢查變成自我證明。
       第 1–3 項仍然執行：它們是對來源自我驗證的，不循環。
    """
    path = source_path(year, stem)
    check_no_excluded_path(path)
    if path not in names:
        raise ValidationError(
            f"壓縮檔內找不到 {path}。該檔不入庫，"
            f"請自 https://data.cec.gov.tw/ 下載後放在 {ZIP_PATH.name}。"
        )
    check_quoting_declaration(year, stem, raw_first_row(zf, names, path))
    rows = read_csv(zf, names, path, SOURCE_COLS[stem],
                    is_quoted(year, stem), KEY_COLS[stem])
    if check_counts:
        expected = EXPECTED_ROWS[(year, stem)]
        if len(rows) != expected:
            raise ValidationError(
                f"{year} {stem} 的列數為 {len(rows)}，宣告值為 {expected}。"
                f"來源可能換版——請重新普查後更新 EXPECTED_ROWS，"
                f"不可自動接受。"
            )
        check_district_values(year, stem, rows)
    return rows


def load_term(zf: zipfile.ZipFile, names: dict[str, str],
              year: str) -> dict[str, list[list[str]]]:
    """讀一屆的七個來源檔。"""
    return {stem: load_source(zf, names, year, stem)
            for stem in SOURCE_FILES}


# 政黨代號跨屆語意漂移的具名清單。實測 elpaty 五屆合計 390 個代號，
# 其中 9 個在不同屆對到不同名稱：
#
#   79  綠黨 → 台灣綠黨                     189 健保免費連線 → 健保免費
#   102 洪運忠義黨 → 全民忠義黨              195 中華民國臺灣基本法連線 → 制度救世島
#   133 紅黨 → 台灣國民會議 → 台灣人權聯盟   199 人民民主陣線 → 人民民主黨
#   134 制憲聯盟 → 大愛憲改聯盟 → 大愛憲改   278 泛盟黨 → 臺灣前進黨
#   166 台灣主義黨 → 全民生活政策黨
#
# ⚠️ 這些漂移有兩種機制——同一政黨改名，或代號被另一個政黨重用——
#    而**從這批資料無法判定是哪一種**（要知道政黨登記史）。
#    這正是鍵必須含名稱的理由：兩種解讀下（代號, 名稱）都安全，
#    只用代號會把重用的情形誤併，只用名稱會把改名的情形誤拆。
#
# ⚠️ 代號 1（中國國民黨）與 16（民主進步黨）五屆穩定，
#    但那【不是】代號穩定的證據。
#
# 清單少一筆或多一筆都中止——清單過期本身就是錯誤，
# 而「來源修好了」與「檢查失效了」在數字上長得一樣。
KNOWN_PARTY_CODE_DRIFT = frozenset({
    "79", "102", "133", "134", "166", "189", "195", "199", "278",
})
EXPECTED_DRIFT_COUNT = 9


def party_names_by_term(
    sources: dict[str, dict[str, list[list[str]]]],
) -> dict[str, dict[str, str]]:
    """逐屆的政黨代號→名稱。同屆內一個代號對到兩個名稱即中止。"""
    out: dict[str, dict[str, str]] = {}
    for year, src in sources.items():
        table: dict[str, str] = {}
        for row in src["elpaty"]:
            code, name = row[0], row[1]
            if code in table and table[code] != name:
                raise ValidationError(
                    f"{year} elpaty 的政黨代號 {code} 對到兩個名稱："
                    f"{table[code]!r} 與 {name!r}。"
                    f"（代號, 名稱）配對鍵無法再識別政黨。"
                )
            table[code] = name
        out[year] = table
    return out


def check_party_code_drift(
    names_by_term: dict[str, dict[str, str]],
) -> set[str]:
    """清點跨屆語意漂移的代號，並與具名清單核對。

    回傳實際漂移的代號集合。
    """
    seen: dict[str, set[str]] = {}
    for year, table in names_by_term.items():
        for code, name in table.items():
            seen.setdefault(code, set()).add(name)
    drift = {c for c, v in seen.items() if len(v) > 1}
    if len(drift) != EXPECTED_DRIFT_COUNT:
        raise ValidationError(
            f"跨屆語意漂移的政黨代號有 {len(drift)} 個，宣告 "
            f"{EXPECTED_DRIFT_COUNT} 個：實得 {sorted(drift)}。"
            f"來源可能換版——請重新普查後更新宣告。"
        )
    extra = drift - KNOWN_PARTY_CODE_DRIFT
    stale = KNOWN_PARTY_CODE_DRIFT - drift
    if extra or stale:
        raise ValidationError(
            f"漂移代號的具名清單與實況不符：多出 {sorted(extra)}、"
            f"清單過期 {sorted(stale)}。"
        )
    return drift


def party_key(code: str, name: str) -> tuple[str, str]:
    """政黨的分桶鍵。

    ⚠️ 必須是（代號, 名稱）配對。只用代號會把漂移的代號誤併成同一個政黨；
       只用名稱會在改名時把同一個政黨拆成兩個。
    """
    return (code, name)


# elprof 的欄位索引（依官方格式文件）
P_VALID = 6      # 有效票
P_INVALID = 7    # 無效票
P_VOTED = 8      # 投票數
P_ELECTORS = 9   # 選舉人數

# elctks 的欄位索引
T_NUM = 6        # 號次（此處即政黨在該屆的號次）
T_VOTES = 7      # 得票數


# elretks 的欄位索引（依官方格式文件）
R_CODE = 0        # 政黨代號
R_STAGE1 = 1      # 第一階段得票率（占全部有效政黨票）
R_STAGE2 = 2      # 第二階段得票率（排除未達門檻政黨後重算，席次分配依據）
R_CANDIDATES = 3  # 候選人數（該黨名單長度）——⚠️【不是】應選席次
R_SEATS = 4       # 當選人數

# 不分區應選席次。五屆皆 34，由法律定而非由來源決定。
AT_LARGE_SEATS = 34

# 兩階段得票率的逐屆精確合計。
#
# ⚠️ **合計不是恆為 100.0000。** 各黨的比率是四捨五入到小數 4 位的值，
#    加總會有捨入殘差：實測 2012 第一階段 99.9998、2016 100.0002、
#    2020 100.0003、2024 第二階段 100.0001。
#
# ⚠️ 我普查時用 float 印到小數 2 位，四捨五入把這些差全部藏起來，
#    因而在 design 裡寫成「五屆合計皆 100.00%」。用 Decimal 才看得到。
EXPECTED_RATE_SUMS = {
    "2008": {"stage1": "100.0000", "stage2": "100.0000"},
    "2012": {"stage1": "99.9998", "stage2": "100.0000"},
    "2016": {"stage1": "100.0002", "stage2": "100.0000"},
    "2020": {"stage1": "100.0003", "stage2": "100.0000"},
    "2024": {"stage1": "100.0000", "stage2": "100.0001"},
}

# 逐屆的政黨數與候選人數。實作前的完整普查值。
EXPECTED_RETKS = {
    "2008": {"parties": 18, "candidates": 128, "passed": 2},
    "2012": {"parties": 16, "candidates": 127, "passed": 4},
    "2016": {"parties": 29, "candidates": 179, "passed": 4},
    "2020": {"parties": 19, "candidates": 216, "passed": 4},
    "2024": {"parties": 16, "candidates": 177, "passed": 3},
}


def check_seat_allocation(year: str, retks: list[list[str]]) -> dict:
    """elretks 的不變量。兩個比率一律【原樣保留】，不重算。

    ⚠️ 第 4 欄是候選人數（該黨名單長度），不是應選席次。
       我一度把 2024 的「34」讀成應選席次——它剛好與應選席次同值，
       是查官方格式文件才發現讀錯。同值使這個誤讀不會有任何跡象。

    回傳該屆的統計，供報告使用。
    """
    codes = [r[R_CODE] for r in retks]
    if len(set(codes)) != len(codes):
        raise ValidationError(f"{year} elretks 的政黨代號重複")

    seats = sum(int(r[R_SEATS]) for r in retks)
    if seats != AT_LARGE_SEATS:
        raise ValidationError(
            f"{year} elretks 的當選人數合計為 {seats}，"
            f"不分區應選席次為 {AT_LARGE_SEATS}。"
            f"席次由法律定，不可由來源決定。"
        )

    # 比率以字串原樣保留，比對用 Decimal——用 float 會讓 0.0002 的差
    # 在印出時被四捨五入藏起來（我普查時就是這樣漏掉的）。
    for idx, label, key in ((R_STAGE1, "第一階段", "stage1"),
                            (R_STAGE2, "第二階段", "stage2")):
        total = sum(Decimal(r[idx]) for r in retks)
        want = Decimal(EXPECTED_RATE_SUMS[year][key])
        if total != want:
            raise ValidationError(
                f"{year} elretks 的{label}得票率合計為 {total}，"
                f"宣告為 {want}。合計不是恆為 100.0000——各黨的比率是"
                f"四捨五入到小數 4 位的值，加總會有捨入殘差。"
                f"殘差改變代表來源換版，不可自動接受。"
            )
        # 補償檢查：宣告的殘差必須小於捨入本身能造成的上界。
        # 上界 = 政黨數 × 0.00005（每個比率的最大捨入誤差）。
        residual = abs(want - Decimal("100"))
        bound = Decimal(len(retks)) * Decimal("0.00005")
        if residual > bound:
            raise ValidationError(
                f"{year} elretks 的{label}殘差 {residual} 超過捨入上界 "
                f"{bound}（{len(retks)} 個政黨 × 0.00005）。"
                f"這個差不可能只是捨入造成的。"
            )

    want = EXPECTED_RETKS[year]
    parties = len(retks)
    candidates = sum(int(r[R_CANDIDATES]) for r in retks)
    passed = sum(1 for r in retks if Decimal(r[R_STAGE2]) > 0)
    got = {"parties": parties, "candidates": candidates, "passed": passed}
    if got != want:
        raise ValidationError(
            f"{year} elretks 的統計為 {got}，宣告為 {want}。"
            f"來源可能換版——請重新普查後更新 EXPECTED_RETKS。"
        )
    return {"政黨數": parties, "候選人數": candidates,
            "當選人數": seats, "達門檻政黨數": passed}


# 原住民立委的選舉種類代碼。L3 山地、L2 平地——由既有的
# build_legislative_election 定義，此處只引用不重新宣告。
INDIGENOUS_TYPES = ("L3", "L2")

# 逐屆的投開票所數與交集，三個整數皆具名。
#
# ⚠️ **可接率有兩個方向，分母不同。** 我普查時只算了「原住民所有多少對得上」
#    （交集／原住民所），因而以為 2020 是 100%——但這裡需要的是
#    「政黨票所有多少對得上」（交集／政黨票所），2020 實際是 98.90%：
#    有 189 個政黨票所沒有原住民立委的對應列。兩個方向都有缺口而我只看了一邊。
#
# ⚠️ 用整數計數而非比率下限：三個數任一改變都中止。
#    「低於下限就中止」放得過鬆——分母與缺口同步變大時比率可能不動。
EXPECTED_JOIN = {
    #        政黨票所, 原住民所, 交集
    "2008": (14_377, 14_377, 14_377),
    "2012": (14_806, 14_806, 14_806),
    "2016": (15_582, 15_582, 15_582),
    "2020": (17_226, 17_037, 17_037),
    "2024": (17_795, 17_810, 17_685),
}

# 原住民選舉人總數（山原 ＋ 平原的檔別合計）。逐屆實測值。
#
# ⚠️ 這一條抓的是【分母算錯】。我在探索階段拿「交集後」的 422,774 當 2024 的
#    分母，比正確的 438,200 少 3.5%——涵蓋率因此被高估。
#
# ⚠️ 這五個數字第一版有四個是我【憑空寫的】：只量過 2024，其餘四屆填了
#    看起來合理的遞增值，而註解卻寫著「普查值」。是這條檢查擋下來的。
#    看起來合理的數字沒有任何跡象顯示它沒被量過——註解說是普查值也不算證據。
EXPECTED_INDIGENOUS_ELECTORS = {
    "2008": 323_072, "2012": 354_946, "2016": 387_105,
    "2020": 414_948, "2024": 438_200,
}


def indigenous_station_totals(
    zf: zipfile.ZipFile, names: dict[str, str], year: str,
) -> tuple[dict[tuple[str, ...], tuple[int, int]], int]:
    """讀該屆山原＋平原的投開票所層級（選舉人數, 投票數）。

    回傳（逐所字典, 檔別合計的選舉人數加總）。

    ⚠️ 沿用 build_legislative_election 的載入器與 SOURCE_DIRS——
       那邊已經驗過引號宣告、欄數與選區欄，不在這裡重寫一份。
    """
    per_station: dict[tuple[str, ...], tuple[int, int]] = {}
    file_total = 0
    for etype in INDIGENOUS_TYPES:
        rows = LEG.load_source(zf, names, year, etype, "elprof")
        for r in rows:
            electors, voted = int(r[P_ELECTORS]), int(r[P_VOTED])
            if not any(x.strip("0") for x in r[:6]):
                file_total += electors      # 檔別合計列
                continue
            if not r[5].strip("0"):
                continue                    # 非投開票所層級
            key = unit_key(r)
            prev_e, prev_v = per_station.get(key, (0, 0))
            per_station[key] = (prev_e + electors, prev_v + voted)
    return per_station, file_total


def indigenous_shares(
    year: str, prof: list[list[str]],
    indigenous: dict[tuple[str, ...], tuple[int, int]],
    file_total: int,
) -> tuple[dict[tuple[str, ...], dict], dict[str, dict[str, int]]]:
    """逐投開票所算原住民選民佔比 p 與投票者佔比 q。

    ⚠️ p 與 q 不是同一件事。分解式 y = q·y_I + (1-q)·y_N 裡的權重是
       【投票者】佔比 q，不是選舉人佔比 p——兩者的差來自兩張票的投票率不同。
       兩個都輸出，讓讀者能自己看差距，而不是被告知「兩者很接近」。

    對不上原住民檔的所，p／q 留空並標記 原住民可接 = false。
    """
    # 分母核對：投開票所層級加總必須等於檔別合計
    station_sum = sum(e for e, _ in indigenous.values())
    if station_sum != file_total:
        raise ValidationError(
            f"{year} 原住民立委的投開票所層級選舉人加總 {station_sum:,} "
            f"≠ 檔別合計 {file_total:,}。分母算錯會讓涵蓋率整組偏掉。"
        )
    declared = EXPECTED_INDIGENOUS_ELECTORS[year]
    if file_total != declared:
        raise ValidationError(
            f"{year} 原住民選舉人總數為 {file_total:,}，宣告為 {declared:,}。"
            f"來源可能換版——請重新普查後更新 EXPECTED_INDIGENOUS_ELECTORS。"
        )

    # ⚠️ 「該所不在原住民檔內」有兩種意思，必須分開：
    #
    #   (a) 該所【沒有原住民選民】——p = 0 是量出來的事實。
    #   (b) 兩個檔的所號對不上——p 是【未知】，不是 0。
    #
    # 判準是**反向缺口**：若該縣市的每一個原住民所都在政黨票檔內
    # （反向缺口 = 0），那麼政黨票檔多出來的所必然沒有原住民選民；
    # 反之兩向都有缺口時，代表所號本身對不上，不能斷言 p = 0。
    #
    # 實測 2020 只有嘉義市有缺口且反向為 0——該市的原住民投票集中在
    # 兩個特設所（村里碼 0999、p 恰為 1.0000），其餘 189 個一般所
    # 確實沒有原住民選民。2024 有七個縣市兩向皆有缺口，屬 (b)。
    #
    # 這個判準由資料算出而非宣告，安全性來自 EXPECTED_JOIN：
    # 缺口數一改變就中止，不會靜默地在 (a) 與 (b) 之間切換。
    pl_keys = {unit_key(r) for r in prof if r[5].strip("0")}
    reverse_gap_by_county: dict[tuple[str, str], int] = {}
    for key in set(indigenous) - pl_keys:
        c = (key[0], key[1])
        reverse_gap_by_county[c] = reverse_gap_by_county.get(c, 0) + 1

    out: dict[tuple[str, ...], dict] = {}
    for r in prof:
        if not r[5].strip("0"):
            continue
        key = unit_key(r)
        total_e, total_v = int(r[P_ELECTORS]), int(r[P_VOTED])
        got = indigenous.get(key)
        if got is not None and total_e > 0 and total_v > 0:
            ind_e, ind_v = got
            out[key] = {
                "原住民可接": "true",
                "缺席原因": "",
                "p": str(Decimal(ind_e) / Decimal(total_e)),
                "q": str(Decimal(ind_v) / Decimal(total_v)),
                "原住民選舉人": str(ind_e),
                "原住民投票數": str(ind_v),
            }
        elif got is None and not reverse_gap_by_county.get((key[0], key[1])):
            # (a) 該縣市的原住民所全部有對應 → 這一所沒有原住民選民
            out[key] = {
                "原住民可接": "true",
                "缺席原因": "該所無原住民選民",
                "p": "0", "q": "0",
                "原住民選舉人": "0", "原住民投票數": "0",
            }
        else:
            # (b) 所號對不上，或該所選舉人／投票數為 0
            out[key] = {
                "原住民可接": "false",
                "缺席原因": ("所號兩檔對不上" if got is None
                             else "該所選舉人或投票數為 0"),
                "p": "", "q": "",
                "原住民選舉人": "", "原住民投票數": "",
            }

    # EXPECTED_JOIN 記的是【交集】——兩檔都有該所的數量。
    # 它不受上面 (a)／(b) 判準的影響，所以判準若因來源變化而改變分類，
    # 這條仍然會先中止。
    # 具名缺口清單：兩個方向逐縣市。放進報告而不只是計數——
    # 「這次影響小」不是不記的理由，來源換版後分布可能改變。
    gaps: dict[str, dict[str, int]] = {"政黨票側": {}, "原住民側": {}}
    for key in sorted(pl_keys - set(indigenous)):
        c = f"{key[0]}-{key[1]}"
        gaps["政黨票側"][c] = gaps["政黨票側"].get(c, 0) + 1
    for key in sorted(set(indigenous) - pl_keys):
        c = f"{key[0]}-{key[1]}"
        gaps["原住民側"][c] = gaps["原住民側"].get(c, 0) + 1
    matched = len(pl_keys & set(indigenous))
    want = EXPECTED_JOIN[year]
    got = (len(pl_keys), len(indigenous), matched)
    if got != want:
        raise ValidationError(
            f"{year} 的（政黨票所, 原住民所, 交集）為 {got}，宣告為 {want}。"
            f"⚠️ 可接率有兩個方向、分母不同——"
            f"政黨票側 {matched}/{len(pl_keys)}、原住民側 {matched}/{len(indigenous)}。"
            f"三個整數任一改變都代表來源換版，不可自動接受。"
        )
    return out, gaps


def check_votes_reconcile(year: str, prof: list[list[str]],
                          ctks: list[list[str]]) -> int:
    """政黨票逐所加總必須【精確等於】該所有效票。

    ⚠️ 配對鍵忽略選區欄。不忽略的話 2008 的 22,581 個單位只有 26 個
       對得上——而那會表現成「幾乎全部對不上」，不是報錯。

    回傳比對的單位數。
    """
    valid = {}
    for r in prof:
        key = unit_key(r)
        if key in valid:
            raise ValidationError(
                f"{year} elprof 的行政單位鍵（忽略選區欄後）重複：{key}。"
                f"重複列會讓後續所有加總驗證失去意義。"
            )
        valid[key] = int(r[P_VALID])

    summed: dict[tuple[str, ...], int] = {}
    for r in ctks:
        key = unit_key(r)
        summed[key] = summed.get(key, 0) + int(r[T_VOTES])

    orphan = sorted(set(summed) - set(valid))
    if orphan:
        raise ValidationError(
            f"{year} elctks 有 {len(orphan)} 個行政單位不存在於 elprof，"
            f"例如 {orphan[:3]}。參照完整性不成立。"
        )
    missing = sorted(set(valid) - set(summed))
    if missing:
        raise ValidationError(
            f"{year} elprof 有 {len(missing)} 個行政單位在 elctks 沒有任何"
            f"得票列，例如 {missing[:3]}。"
        )
    bad = [(k, valid[k], summed[k]) for k in valid if valid[k] != summed[k]]
    if bad:
        k, a, b = bad[0]
        raise ValidationError(
            f"{year} 有 {len(bad)} 個行政單位的政黨票加總不等於有效票，"
            f"例如 {k}：有效票 {a} vs 政黨票加總 {b}。"
        )
    return len(valid)


# 分層門檻，以【選舉人佔比 p】篩投開票所。
#
# ⚠️ 三個都輸出，不挑一個。涵蓋率與精度是直接的取捨——挑一個等於替讀者
#    做決定，而 11% 與 28% 的涵蓋率差別足以改變結論的可信範圍。
THRESHOLDS = (Decimal("0.95"), Decimal("0.90"), Decimal("0.80"))


def duncan_davis_bounds(y: Fraction, q: Fraction) -> tuple[Fraction, Fraction]:
    """Duncan-Davis 極限法。回傳（下界, 上界），皆為**精確有理數**。

    給定該層觀察到的得票率 y 與**投票者**中原住民佔比 q，
    原住民的支持率必然落在：

        [ max(0, (y - (1 - q)) / q),  min(1, y / q) ]

    ⚠️ 這個區間**不依賴任何統計假設**，只依賴算術：分子最多是全部觀察到的
       票都來自原住民，最少是非原住民先投滿自己的份額。因此它可以拿來當
       建置時的守門員——公式或權重寫錯時，界限會與觀察值矛盾。

    ⚠️ 權重必須是 q（投票者佔比）而不是 p（選舉人佔比）。用錯的那個算出的
       界限**仍然長得像界限**，不會有任何跡象。

    ⚠️ 全程用 Fraction 而非 Decimal。分子分母本來就是整數票數，
       用有理數不會有捨入；改用 Decimal 的話，寬度恆等式會因為
       各自捨入而差 1 ulp，逼人去設容差——而容差會把「界限被放鬆」
       一起放過，那正是下面那條要抓的東西。
    """
    if not (0 < q <= 1):
        raise ValidationError(f"q 必須落在 (0, 1]，實得 {q}")
    if not (0 <= y <= 1):
        raise ValidationError(f"觀察得票率必須落在 [0, 1]，實得 {y}")
    lower = max(Fraction(0), (y - (1 - q)) / q)
    upper = min(Fraction(1), y / q)
    return lower, upper


def check_bounds_contain(party: str, y: Fraction, q: Fraction,
                         lower: Fraction, upper: Fraction) -> None:
    """界限必須含住觀察值、落在 [0, 1]，且寬度不超過 (1-q)/q。

    ⚠️ 這是估計值唯一能寫出「會失敗」的檢查。

    ⚠️ 只驗「含住觀察值」**擋不住把界限放鬆的錯誤**：把 (1-q) 寫成 (1+q)，
       下界會變負而被 clamp 成 0，含住關係照樣成立。實測那個變異確實
       沒被含住檢查抓到。所以另加寬度恆等式——極限法的寬度由 q 唯一決定，
       未截斷時【恰為】(1-q)/q，截斷時只會更小。
    """
    if not (Fraction(0) <= lower <= y <= upper <= Fraction(1)):
        raise ValidationError(
            f"{party} 的界限不含觀察值："
            f"下界 {float(lower):.6g}、觀察 {float(y):.6g}、"
            f"上界 {float(upper):.6g}。"
            f"必須滿足 0 ≤ 下界 ≤ 觀察 ≤ 上界 ≤ 1——"
            f"不成立代表權重或公式寫錯了。"
        )
    max_width = (1 - q) / q
    width = upper - lower
    if width > max_width:
        raise ValidationError(
            f"{party} 的區間寬 {float(width):.6g} 超過 (1-q)/q = "
            f"{float(max_width):.6g}。"
            f"極限法的寬度由 q 唯一決定，超過代表公式被放鬆了——"
            f"而放鬆的界限仍然含得住觀察值，只驗含住是抓不到的。"
        )


def as_ratio(value: Fraction, places: int = 10) -> str:
    """有理數轉成輸出用的十進位字串。只在輸出時捨入，計算全程精確。"""
    return format(
        Decimal(value.numerator) / Decimal(value.denominator), f".{places}f")


def stratum_bounds(
    year: str, prof: list[list[str]], ctks: list[list[str]],
    shares: dict[tuple[str, ...], dict],
    party_of_number: dict[str, tuple[str, str]],
) -> list[dict]:
    """逐門檻算出各政黨的觀察值與極限。

    ⚠️ 篩所用 p（選舉人佔比），算界限用 q（投票者佔比）——兩者不同。
    """
    valid_by_key = {unit_key(r): int(r[P_VALID]) for r in prof}
    rows: list[dict] = []
    for threshold in THRESHOLDS:
        selected = {
            k for k, v in shares.items()
            if v["原住民可接"] == "true" and v["p"] != ""
            and Decimal(v["p"]) >= threshold
        }
        if not selected:
            raise ValidationError(
                f"{year} 門檻 {threshold} 沒有任何投開票所——"
                f"門檻宣告與資料脫節。"
            )
        ind_electors = sum(int(shares[k]["原住民選舉人"]) for k in selected)
        ind_votes = sum(int(shares[k]["原住民投票數"]) for k in selected)
        total_votes = 0
        for r in prof:
            if unit_key(r) in selected:
                total_votes += int(r[P_VOTED])
        valid = sum(valid_by_key[k] for k in selected)
        q = Fraction(ind_votes, total_votes)

        votes: dict[tuple[str, str], int] = {}
        for r in ctks:
            k = unit_key(r)
            if k not in selected:
                continue
            key = party_of_number.get(r[T_NUM])
            if key is None:
                raise ValidationError(
                    f"{year} elctks 的號次 {r[T_NUM]} 在 elcand 找不到政黨"
                )
            votes[key] = votes.get(key, 0) + int(r[T_VOTES])

        for (code, name), v in sorted(votes.items(), key=lambda x: -x[1]):
            y = Fraction(v, valid)
            lower, upper = duncan_davis_bounds(y, q)
            check_bounds_contain(
                f"{year} {threshold} {name}", y, q, lower, upper)
            rows.append({
                "屆別": year,
                "門檻": str(threshold),
                "政黨代號": code,
                "政黨名稱": name,
                "所數": len(selected),
                "涵蓋原住民選舉人": ind_electors,
                "涵蓋率": as_ratio(
                    Fraction(ind_electors,
                             EXPECTED_INDIGENOUS_ELECTORS[year])),
                "p_加權": as_ratio(Fraction(
                    ind_electors,
                    sum(int(r[P_ELECTORS]) for r in prof
                        if unit_key(r) in selected))),
                "q_加權": as_ratio(q),
                "有效政黨票": valid,
                "觀察_得票數": v,
                "觀察_得票率": as_ratio(y),
                "下界_原住民得票率": as_ratio(lower),
                "上界_原住民得票率": as_ratio(upper),
            })
    return rows



# elrepm 中【絕不輸出】的欄位索引：出生日期、出生地、學歷。
#
# ⚠️ 實測五屆這三欄都有值，不是空欄。與 elcand 同類個資，
#    本專案對 elcand 已有同樣的排除，此處沿用同一條紀律。
PERSONAL_DATA_COLS = {4: "出生日期", 6: "出生地", 7: "學歷"}

# 任何輸出的欄名都不得包含這些字樣。
FORBIDDEN_COLUMN_WORDS = ("出生日期", "出生地", "學歷", "生日")


def check_no_personal_data(tables: dict[str, list[dict]]) -> None:
    """任何輸出的欄名集合都不得含個資衍生欄。

    ⚠️ 這條守的不是「我這次沒寫進去」，是「以後也不會被加進去」。
       elrepm 只讀不輸出，但它就在同一支腳本裡，欄位取用只差一個索引。
    """
    for name, rows in tables.items():
        if not rows:
            continue
        for col in rows[0]:
            for word in FORBIDDEN_COLUMN_WORDS:
                if word in col:
                    raise ValidationError(
                        f"{name} 的欄位 {col!r} 含個資字樣 {word!r}。"
                        f"elrepm 的出生日期／出生地／學歷一律不輸出——"
                        f"與 elcand 同一條紀律。"
                    )


def check_output_manifests(tables: dict[str, list[dict]]) -> None:
    """三張官方表的欄位必須與 PARTY_LIST_MANIFEST 逐欄相符。

    ⚠️ 抽成函式而不寫在 main() 裡：寫在 main() 的話測試碰不到它，
       把它拿掉的變異會漏網——實測就是這樣漏的。
    """
    problems = check_manifest_against(
        PARTY_LIST_MANIFEST,
        {name: list(rows[0].keys())
         for name, rows in tables.items()
         if name != "indigenous_party_preference_bounds" and rows},
    )
    if problems:
        raise ValidationError(
            "欄位 oracle 宣告與實際輸出不符：\n  " + "\n  ".join(problems))


def build_summary_rows(year: str, prof: list[list[str]],
                       shares: dict[tuple[str, ...], dict]) -> list[dict]:
    """政黨票的選舉概況長表。投開票所層級的列另帶 p／q。"""
    rows = []
    for r in prof:
        key = unit_key(r)
        s = shares.get(key, {})
        rows.append({
            "屆別": year,
            "省市": r[0], "縣市": r[1], "選舉區": r[2],
            "鄉鎮市區": r[3], "村里": r[4], "投開票所": r[5],
            "層級": LEG.admin_level(list(r[:6])),
            "有效票": r[P_VALID], "無效票": r[P_INVALID],
            "投票數": r[P_VOTED], "選舉人數": r[P_ELECTORS],
            "原住民可接": s.get("原住民可接", ""),
            "缺席原因": s.get("缺席原因", ""),
            "p": s.get("p", ""), "q": s.get("q", ""),
            "原住民選舉人": s.get("原住民選舉人", ""),
            "原住民投票數": s.get("原住民投票數", ""),
        })
    return rows


def build_votes_rows(year: str, ctks: list[list[str]],
                     party_of_number: dict[str, tuple[str, str]]) -> list[dict]:
    """逐所逐政黨的得票長表。"""
    rows = []
    for r in ctks:
        key = party_of_number.get(r[T_NUM])
        if key is None:
            raise ValidationError(
                f"{year} elctks 的號次 {r[T_NUM]} 在 elcand 找不到政黨")
        code, name = key
        rows.append({
            "屆別": year,
            "省市": r[0], "縣市": r[1], "選舉區": r[2],
            "鄉鎮市區": r[3], "村里": r[4], "投開票所": r[5],
            "層級": LEG.admin_level(list(r[:6])),
            "政黨代號": code, "政黨名稱": name,
            "號次": r[T_NUM], "得票數": r[T_VOTES], "得票率": r[8],
        })
    return rows


def build_seats_rows(year: str, retks: list[list[str]],
                     paty: dict[str, str]) -> list[dict]:
    """逐屆逐政黨的席次表。兩個比率【原樣保留】，不重算。"""
    rows = []
    for r in retks:
        rows.append({
            "屆別": year,
            "政黨代號": r[R_CODE],
            "政黨名稱": paty.get(r[R_CODE], r[R_CODE]),
            "第一階段得票率": r[R_STAGE1],
            "第二階段得票率": r[R_STAGE2],
            "候選人數": r[R_CANDIDATES],
            "當選人數": r[R_SEATS],
        })
    return rows


def emit_census(zf: zipfile.ZipFile, names: dict[str, str]) -> None:
    """由來源量出全部宣告值，印成可直接貼上的常數區塊。

    ⚠️ **這個函式不得讀取任何被它量測的宣告值。** 讀了就變成自我證明——
       常數與量測會永遠一致，而那正是它要防的錯誤。
       `load_source(..., check_counts=False)` 就是為此存在。

    ⚠️ 存在的理由：手抄宣告值本身就是錯誤來源。實作這個 change 到 3.1 時，
       宣告值上已錯八次，其中四次的根因是「跑了普查、印出摘要、
       把摘要當成資料」——截斷、四捨五入、只印一個分母各自銷毀了資訊，
       而摘要看起來永遠是完整的。第五次是根本沒量就寫。
       產生取代手抄之後，這兩種錯都變成不可能。
    """
    src = {y: {s: load_source(zf, names, y, s, check_counts=False)
               for s in SOURCE_FILES} for y in TERMS}

    print("# ---- EXPECTED_ROWS ----")
    print("EXPECTED_ROWS = {")
    for year in TERMS:
        cells = ", ".join(f'("{year}", "{s}"): {len(src[year][s])}'
                          for s in SOURCE_FILES)
        print(f"    {cells},")
    print("}")

    print()
    print("# ---- EXPECTED_RATE_SUMS ----")
    print("EXPECTED_RATE_SUMS = {")
    for year in TERMS:
        rows = src[year]["elretks"]
        s1 = sum(Decimal(r[R_STAGE1]) for r in rows)
        s2 = sum(Decimal(r[R_STAGE2]) for r in rows)
        print(f'    "{year}": {{"stage1": "{s1}", "stage2": "{s2}"}},')
    print("}")

    print()
    print("# ---- EXPECTED_RETKS ----")
    print("EXPECTED_RETKS = {")
    for year in TERMS:
        rows = src[year]["elretks"]
        parties = len(rows)
        cands = sum(int(r[R_CANDIDATES]) for r in rows)
        passed = sum(1 for r in rows if Decimal(r[R_STAGE2]) > 0)
        print(f'    "{year}": {{"parties": {parties}, '
              f'"candidates": {cands}, "passed": {passed}}},')
    print("}")

    print()
    print("# ---- EXPECTED_JOIN（政黨票所, 原住民所, 交集）----")
    print("EXPECTED_JOIN = {")
    electors = {}
    for year in TERMS:
        ind, ind_total = indigenous_station_totals(zf, names, year)
        electors[year] = ind_total
        pl = {unit_key(r) for r in src[year]["elprof"] if r[5].strip("0")}
        both = pl & set(ind)
        print(f'    "{year}": ({len(pl):_}, {len(ind):_}, {len(both):_}),')
    print("}")

    print()
    print("# ---- EXPECTED_INDIGENOUS_ELECTORS ----")
    print("EXPECTED_INDIGENOUS_ELECTORS = {")
    cells = ", ".join(f'"{y}": {electors[y]:_}' for y in TERMS)
    print(f"    {cells},")
    print("}")

    print()
    print("# ---- 漂移的政黨代號 ----")
    names_by_term = party_names_by_term(src)
    seen: dict[str, set[str]] = {}
    for table in names_by_term.values():
        for code, name in table.items():
            seen.setdefault(code, set()).add(name)
    drift = sorted({c for c, v in seen.items() if len(v) > 1}, key=int)
    print(f"EXPECTED_DRIFT_COUNT = {len(drift)}")
    quoted = ", ".join(f'"{c}"' for c in drift)
    print(f"KNOWN_PARTY_CODE_DRIFT = frozenset({{{quoted}}})")


def main() -> None:
    if not ZIP_PATH.exists():
        raise SystemExit(
            f"找不到 {ZIP_PATH}。該檔不入庫，"
            f"請自 https://data.cec.gov.tw/ 下載。"
        )
    census = "--census" in sys.argv
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zip_names(zf)
        if census:
            emit_census(zf, names)
            return
        sources = {}
        bounds: list[dict] = []
        summary: list[dict] = []
        votes: list[dict] = []
        seat_rows: list[dict] = []
        for year in TERMS:
            src = load_term(zf, names, year)
            sources[year] = src
            units = check_votes_reconcile(year, src["elprof"], src["elctks"])
            seats = check_seat_allocation(year, src["elretks"])
            ind, ind_total = indigenous_station_totals(zf, names, year)
            shares, gaps = indigenous_shares(
                year, src["elprof"], ind, ind_total)
            usable = sum(1 for v in shares.values()
                         if v["原住民可接"] == "true")
            zero = sum(1 for v in shares.values()
                       if v["缺席原因"] == "該所無原住民選民")
            unknown = sum(1 for v in shares.values()
                          if v["原住民可接"] == "false")
            print(f"  {year}: 逐所對帳 {units:,}｜"
                  f"政黨 {seats['政黨數']}、當選 {seats['當選人數']} 席｜"
                  f"投開票所 {len(shares):,}：可用 {usable:,}"
                  f"（其中 p=0 的 {zero:,}）、未知 {unknown:,}｜"
                  f"原住民選舉人 {ind_total:,}")
            for side, per_county in gaps.items():
                if per_county:
                    print(f"       具名缺口（{side}）: {per_county}")

            paty = {r[0]: r[1] for r in src["elpaty"]}
            party_of_number = {c[5]: party_key(c[7], paty.get(c[7], c[7]))
                               for c in src["elcand"]}
            bounds += stratum_bounds(year, src["elprof"], src["elctks"],
                                     shares, party_of_number)
            summary += build_summary_rows(year, src["elprof"], shares)
            votes += build_votes_rows(year, src["elctks"], party_of_number)
            seat_rows += build_seats_rows(year, src["elretks"], paty)

    names_by_term = party_names_by_term(sources)
    drift = check_party_code_drift(names_by_term)
    print(f"\n政黨代號：跨屆漂移 {len(drift)} 個 {sorted(drift)}，與具名清單相符。")
    # ⚠️ 估計值與官方數字【分表】。這一份的每個數值欄都帶
    #    觀察_／下界_／上界_ 前綴，且每一列都帶產生它的範圍
    #    （門檻、所數、涵蓋率、p、q），下游不可能只讀到一個看似官方的欄位。
    tables = {
        "party_list_summary": summary,
        "party_list_votes": votes,
        "party_list_seats": seat_rows,
        "indigenous_party_preference_bounds": bounds,
    }
    check_no_personal_data(tables)

    check_output_manifests(tables)

    commit_outputs(OUT_DIR, {
        "cec-party-list-summary-long.csv.gz":
            render_csv(summary, "cec-party-list-summary-long.csv.gz", True),
        "cec-party-list-votes-long.csv.gz":
            render_csv(votes, "cec-party-list-votes-long.csv.gz", True),
        "cec-party-list-seats.csv":
            render_csv(seat_rows, "cec-party-list-seats.csv"),
        "indigenous-party-preference-bounds.csv":
            render_csv(bounds, "indigenous-party-preference-bounds.csv"),
    })
    print(f"\n輸出 {len(summary):,} / {len(votes):,} / {len(seat_rows)} 列"
          f"（summary / votes / seats）"
          f"，界限表 {len(bounds)} 列")

    # oracle 文件由 manifest 生成，手寫會脫節。原子寫入見 oracles.py。
    write_oracle_document()

    print("讀檔、對帳、界限與輸出完成。")


if __name__ == "__main__":
    main()
