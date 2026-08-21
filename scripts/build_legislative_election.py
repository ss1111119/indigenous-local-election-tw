"""由中選會選舉資料庫建置「原住民立法委員」長表。

涵蓋九屆山地原住民（L3）與平地原住民（L2）立委：
1995、1998、2001、2004、2008、2012、2016、2020、2024。

⚠️ 本檔【不處理】地方公職。地方公職在 scripts/build_local_election.py，
   兩者刻意分開：地方公職那支內含縣市代碼跨屆換算、鄉鎮市區檔內重編、
   婦女保障名額、主序列過濾、63 筆當選註記具名異常等只對地方公職成立的邏輯，
   立委一項都用不到。把兩者塞進同一支腳本會讓每個函式都要帶
   「這是哪一種選舉」的分支——那正是本專案「具名到最細粒度」的相反做法。

   共用的只有低階工具（zip_names／read_csv／is_blank／admin_level 等），
   以 import 沿用，**不搬動也不修改** build_local_election.py。

⚠️ 立委與地方公職在層級語意上不同：原住民立委是【全國單一選區】，
   `選舉區` 欄不帶選區意義（1995-2008 恆為 '00'、2012 起 '00' 與 '01' 並存）。
   不要拿地方公職的選舉區語意套用在這裡。
"""
from __future__ import annotations

import collections
import csv
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ⚠️ 只 import 低階工具，不 import 地方公職的驗證邏輯與具名清單。
#    若某天需要的東西不在這份清單裡，先問「它是不是只對地方公職成立」，
#    而不是直接加進來。
from build_local_election import (  # noqa: E402
    ADMIN_LEVELS,
    ELECTED_MARKS,
    KEY_COLS,
    WIN_MARKS,
    ValidationError,
    ZIP_PATH,
    admin_level,
    is_blank,
    read_csv,
    zip_names,
)

# 各來源檔的欄數。逐列檢查，只驗「至少幾欄」會讓多出來的欄位靜默通過。
SOURCE_COLS = {
    "elbase": 6, "elcand": 16, "elctks": 10, "elprof": 20, "elpaty": 2,
}

OUT_DIR = ROOT / "data" / "processed"

# 選舉種類代碼。
# ⚠️ `L2`／`L3` 是【本專案自訂】的代碼，不是中選會原始檔裡的代碼。
#    來源以資料夾名稱區分（「山原」／「平原」／「山地立委」／「平地立委」），
#    沒有給定代碼。刻意用 `L` 前綴與地方公職議員的 `T2`／`T3` 區隔——
#    兩者都叫「平地／山地原住民」，但一個是議員、一個是立委，
#    共用代碼會讓兩個資料集併看時無法分辨。
ELECTION_TYPES = {
    "L2": "立法委員(平地原住民)選舉",
    "L3": "立法委員(山地原住民)選舉",
}

# 九屆的應選名額。
# ⚠️ 逐屆釘死，不可寫成單一數字——席次跨屆變動過兩次：
#    1995 各 3 席 → 1998/2001/2004 各 4 席 → 2008 起各 3 席。
#    2008 年立委席次減半並改行單一選區兩票制，原住民立委回到各 3 席。
SEATS_BY_TERM = {
    "1995": 3, "1998": 4, "2001": 4, "2004": 4,
    "2008": 3, "2012": 3, "2016": 3, "2020": 3, "2024": 3,
}

TERMS = tuple(SEATS_BY_TERM)

# 壓縮檔內的目錄名稱逐屆逐種類【具名】。
#
# ⚠️ 刻意不用萬用字元或樣式比對推導。三個理由：
#    1. 目錄命名毫無規律——「3屆立委/山原」「2008立委/山原」
#       「20120114-總統及立委/山地立委」「2016總統立委/山地立委」四種寫法都有。
#    2. 2016 的檔名帶 `_T2`／`_T3` 後綴，其餘八屆沒有。
#    3. `2016總統立委/old/` 底下有一份重複目錄。用樣式比對會把它一起抓進來，
#       而它的 elctks 比正式版多 54,880 列（見 EXCLUDED_PATH_SEGMENT）。
#
# 值為 (目錄, 檔名後綴)。後綴接在 elbase／elcand／elctks／elprof 之後，
# elpaty 不帶後綴（2016 亦然，實測確認）。
SOURCE_DIRS: dict[tuple[str, str], tuple[str, str]] = {
    ("1995", "L3"): ("3屆立委/山原", ""),
    ("1995", "L2"): ("3屆立委/平原", ""),
    ("1998", "L3"): ("4屆立委/山原", ""),
    ("1998", "L2"): ("4屆立委/平原", ""),
    ("2001", "L3"): ("5屆立委/山原", ""),
    ("2001", "L2"): ("5屆立委/平原", ""),
    ("2004", "L3"): ("2004第6屆立法委員/山原", ""),
    ("2004", "L2"): ("2004第6屆立法委員/平原", ""),
    ("2008", "L3"): ("2008立委/山原", ""),
    ("2008", "L2"): ("2008立委/平原", ""),
    ("2012", "L3"): ("20120114-總統及立委/山地立委", ""),
    ("2012", "L2"): ("20120114-總統及立委/平地立委", ""),
    ("2016", "L3"): ("2016總統立委/山地立委", "_T3"),
    ("2016", "L2"): ("2016總統立委/平地立委", "_T2"),
    ("2020", "L3"): ("2020總統立委/山地立委", ""),
    ("2020", "L2"): ("2020總統立委/平地立委", ""),
    ("2024", "L3"): ("2024總統立委/山地立委", ""),
    ("2024", "L2"): ("2024總統立委/平地立委", ""),
}

ZIP_PREFIX = "votedata/votedata/voteData/"

# 每個來源目錄必須有的五個檔。少一個即中止——「少了就跳過該檔」會讓
# 某屆靜默地少掉一整個資料維度，而總數看起來仍然合理。
SOURCE_FILES = ("elbase", "elcand", "elctks", "elprof", "elpaty")

# 不帶後綴的檔（2016 的 elpaty 也沒有後綴）。
FILES_WITHOUT_SUFFIX = frozenset({"elpaty"})

# ⚠️ 被取代的重複目錄，以路徑段排除。
#
#    `2016總統立委/old/` 底下有一份 2016 的副本：elcand 與正式版位元組相同，
#    但 elctks 多出 54,880 列、elprof 大小相同而內容不同。兩者的全國合計一致
#    （山原得票 112,965、選舉人 200,029），差異出在細層級的列數，**成因未查明**。
#
#    以正式路徑為準並主動排除 old。不採「取列數多者」或「先找到的算」——
#    在成因未查明的情況下靜默選擇，下次結構再變時不會有人察覺。
EXCLUDED_PATH_SEGMENT = "old"

# 帶前置單引號的檔，具名到（屆別, 選舉種類, 檔）。
#
# ⚠️ **粒度必須到「檔」，不是「屆別」。** 2008 只有 elcand 帶引號，
#    同屆的 elbase／elctks／elprof 都沒有；2012 是四個檔帶、elpaty 不帶。
#    提案階段只抽驗 elprof 就宣稱「唯一帶引號的是 2012」——那是以部分樣本
#    下的全稱宣稱，清點 90 個檔之後推翻了。
#
# ⚠️ 撇號不只出現在鍵欄：2008 elcand 的政黨代號欄是 `'73`。所以剝除是整列，
#    不是只對鍵欄——read_csv(quoted=True) 的行為正是整列 lstrip("'")。
QUOTED_FILES: frozenset[tuple[str, str, str]] = frozenset(
    {(year, etype, stem)
     for etype in ("L2", "L3")
     for year, stem in (
         ("2008", "elcand"),
         ("2012", "elbase"), ("2012", "elcand"),
         ("2012", "elctks"), ("2012", "elprof"),
     )}
)


# 選舉區欄（第 3 欄，索引 2）的允許值，具名到（屆別, 選舉種類, 檔）。
#
# ⚠️ 原住民立委是【全國單一選區】，這一欄不帶選區意義。但它不是常數——
#    取值由【檔】決定，不是由屆別決定。清點 90 個來源檔的結果：
#
#      elbase  九屆恆為 {'00'}
#      elcand  九屆恆為 {'01'}
#      elctks  1995-2008 為 {'00'}；2012 起為 {'00', '01'}
#      elprof  1995-2008 為 {'00'}；2012 起為 {'00', '01'}
#
#    也就是說**同一屆的四個檔對這一欄各說各話**。提案階段只抽驗 elprof
#    得到的「1995-2008 為 00」只對 elprof 成立。L2 與 L3 已逐檔比對，形態一致。
#
# ⚠️ 不採用「一律忽略選舉區欄」。忽略等於在這一欄上停掉驗證——
#    未來若出現第三種值（例如來源改用真正的選區編號），不會有任何人察覺。
_DISTRICT_EARLY = ("1995", "1998", "2001", "2004", "2008")

DISTRICT_ALLOWED: dict[tuple[str, str, str], frozenset[str]] = {
    (year, etype, stem): allowed
    for etype in ("L2", "L3")
    for year in TERMS
    for stem, allowed in (
        ("elbase", frozenset({"00"})),
        ("elcand", frozenset({"01"})),
        ("elctks", frozenset({"00"}) if year in _DISTRICT_EARLY
         else frozenset({"00", "01"})),
        ("elprof", frozenset({"00"}) if year in _DISTRICT_EARLY
         else frozenset({"00", "01"})),
    )
}

DISTRICT_COL = 2

# `選舉區_語意` 欄的值。原住民立委九屆皆為全國單一選區，沒有例外——
# 但仍逐列寫出而非省略：省略等於要求讀者先讀文件才知道這一欄不能拿來分組。
DISTRICT_MEANING_NATIONWIDE = "無選區意義（全國單一選區）"


# 每屆【預期達到的最細層級】，具名到屆別。
#
# ⚠️ 逐屆宣告，不以「有多少列」推斷。若不宣告，某屆的細層級資料在來源端整批
#    遺失時，建置會安靜地產出一張較粗的表——各層級的加總仍然正確、
#    沒有任何錯誤訊息，而下游對「該屆不支援投開票所分析」與「查詢結果為空」
#    無從分辨。
#
# 實測：1995-2004 的 elprof 各約 395 列、最細到鄉鎮市區；
#      2008 起 2.2-2.6 萬列、最細到投開票所。
FINEST_LEVEL_BY_TERM = {
    "1995": "鄉鎮市區", "1998": "鄉鎮市區", "2001": "鄉鎮市區", "2004": "鄉鎮市區",
    "2008": "投開票所", "2012": "投開票所", "2016": "投開票所",
    "2020": "投開票所", "2024": "投開票所",
}


def check_finest_level(year: str, etype: str, stem: str,
                       rows: list[list[str]]) -> None:
    """該檔實際達到的最細層級必須恰等於宣告值，且不得出現「選舉區」層級。

    ⚠️ 比對的是【相等】而非【至少】。只驗「不比宣告更粗」會讓來源某天
       多出更細的一層時無人察覺；只驗「不比宣告更細」則放過整批遺失。

    ⚠️ 「不得出現選舉區層級」是這裡唯一守得住未來結構改變的斷言。
       原住民立委是全國單一選區，`選舉區` 欄只是常數標記（elcand 恆為 '01'）。
       實測 72 個檔中沒有任何一列以選舉區為最深層級——若哪天有了，
       代表這一欄開始帶真正的層級意義，整套層級判定都要重新檢視。
    """
    if year not in FINEST_LEVEL_BY_TERM:
        raise ValidationError(f"最細層級未具名宣告：{year}")
    levels = {admin_level(r[:6]) for r in rows}
    if "選舉區" in levels:
        raise ValidationError(
            f"{year} {etype} {stem} 出現以【選舉區】為最深層級的列。"
            f"原住民立委為全國單一選區，該欄應只是常數標記；"
            f"若來源開始以它表示層級，整套層級判定須重新檢視。"
        )
    deepest = max(levels, key=ADMIN_LEVELS.index)
    want = FINEST_LEVEL_BY_TERM[year]
    if deepest != want:
        raise ValidationError(
            f"{year} {etype} {stem} 的最細層級是 {deepest}，宣告為 {want}。"
            f"變粗代表細層級資料整批遺失——各層級加總仍會正確，不會有別的錯誤訊息；"
            f"變細代表來源新增了層級，層級判定須重新檢視。"
        )


def district_meaning(year: str, etype: str) -> str:
    """該（屆別, 選舉種類）的選舉區欄是否帶選區意義。

    ⚠️ 本批九屆全部是全國單一選區，回傳值恆為同一個字串——但**仍然逐列輸出**。
       省略它等於要求讀者先讀文件才知道這一欄不能拿來分組；有了這一欄，
       拿它 groupby 的人會在結果旁邊看到「無選區意義」。

       函式而非常數：若日後納入區域立委（真的有選區），這裡是唯一要改的地方，
       而不是散落在列組裝處的一個字面值。
    """
    if (year, etype) not in SOURCE_DIRS:
        raise ValidationError(f"未具名的（屆別, 選舉種類）：{(year, etype)}")
    return DISTRICT_MEANING_NATIONWIDE


# `elcand` 的欄位索引，取自壓縮檔內的官方格式文件〈選舉資料庫格式.odt〉。
#
# ⚠️ 語意權威是那份文件，不是任何既有腳本。文件明列 16 個欄位：
#    0 省市別 1 縣市別 2 選區別 3 鄉鎮市區 4 村里別 5 號次 6 名字 7 政黨代號
#    8 性別 9 出生日期 10 年齡 11 出生地 12 學歷 13 現任 14 當選註記 15 副手
C_NUM, C_NAME, C_PARTY, C_SEX = 5, 6, 7, 8
C_AGE, C_INCUMBENT, C_MARK = 10, 13, 14

# ⚠️⚠️ 個資欄位：出生日期、出生地、學歷。**任何輸出都不得包含這三欄**，
#       也不得輸出可回推它們的衍生值（例如由出生日期算出的生日）。
#       `年齡` 是獨立欄位、非由出生日期推導，可以輸出。
PERSONAL_DATA_COLS = {9: "出生日期", 11: "出生地", 12: "學歷"}

# 年齡的無資料哨兵。官方格式文件：「年齡 Num(3)（部分選舉未必有資料，可能 0 或 99）」。
#
# ⚠️ **不可沿用 `build_local_election.AGE_UNRECORDED_TERMS`。**
#    那一份是地方公職的屆別（1994／1998／2002／2005／2006），與立委只有 1998 重疊。
#    普查結果：立委的哨兵屆別是 1995／1998／2001／2004，那四屆的 72 位候選人
#    **全部**是 `99`（不是部分），2008 起完全沒有哨兵值。
#    直接沿用會讓 1995／2001／2004 的 `99` 當成「99 歲」輸出。
AGE_UNRECORDED_TERMS = frozenset({"1995", "1998", "2001", "2004"})
AGE_UNRECORDED_VALUE = "99"
AGE_ALWAYS_NO_DATA = frozenset({"0", ""})
AGE_NO_DATA_VALUES = AGE_ALWAYS_NO_DATA | {AGE_UNRECORDED_VALUE}


def valid_age(year: str, raw: str) -> str:
    """年齡的乾淨值。無資料一律留空，不留哨兵。

    `99` 只在已具名的屆別視為無資料——否則 2008 年以後真有 99 歲的候選人時，
    他的年齡會被靜默吃掉。
    """
    if raw in AGE_ALWAYS_NO_DATA:
        return ""
    if raw == AGE_UNRECORDED_VALUE and year in AGE_UNRECORDED_TERMS:
        return ""
    return raw


def check_age_sentinel(year: str, rows: list[list[str]]) -> None:
    """雙向核對年齡哨兵的宣告與來源實況。

    ⚠️ 兩個方向都要驗：具名屆別若出現哨兵以外的值，代表那屆其實有真實年齡、
       宣告過期；未具名屆別若出現 `99`，代表哨兵擴散到新的屆別而無人察覺。
    """
    vals = {r[C_AGE] for r in rows}
    if year in AGE_UNRECORDED_TERMS:
        odd = vals - AGE_NO_DATA_VALUES
        if odd:
            raise ValidationError(
                f"{year} 已具名為年齡整批無資料，但出現非哨兵值 {sorted(odd)[:5]}。"
                f"宣告過期——該屆其實有真實年齡。"
            )
    elif AGE_UNRECORDED_VALUE in vals:
        raise ValidationError(
            f"{year} 未具名為年齡無資料屆別，卻出現 {AGE_UNRECORDED_VALUE!r}。"
            f"若那是哨兵，會被當成「99 歲」輸出；若真有 99 歲候選人，"
            f"必須確認後才可放行。"
        )


def check_district_values(year: str, etype: str, stem: str,
                          rows: list[list[str]]) -> None:
    """選舉區欄的實際取值必須恰等於宣告集合。多一個少一個都中止。

    ⚠️ 比對的是【集合相等】而非【子集合】。只驗「沒有超出宣告的值」，
       會讓宣告過期（某個值在來源消失了）靜默通過。
    """
    key = (year, etype, stem)
    if key not in DISTRICT_ALLOWED:
        raise ValidationError(f"選舉區欄允許值未具名宣告：{key}")
    got = {r[DISTRICT_COL] for r in rows}
    want = DISTRICT_ALLOWED[key]
    if got != set(want):
        raise ValidationError(
            f"{year} {etype} {stem} 的選舉區欄取值為 {sorted(got)}，"
            f"宣告為 {sorted(want)}。原住民立委為全國單一選區，這一欄不帶選區意義；"
            f"取值改變代表來源結構變了，不可自動接受。"
        )


def is_quoted(year: str, etype: str, stem: str) -> bool:
    """該檔是否宣告為帶前置單引號。"""
    return (year, etype, stem) in QUOTED_FILES


def check_quoting_declaration(year: str, etype: str, stem: str,
                              first_row: list[str]) -> None:
    """雙向核對引號宣告與來源實況。任一方向不符即中止。

    ⚠️ 這項檢查的辨識力**不**來自「剝除有沒有做對」——全域剝除與具名剝除
       在現有資料上產生完全相同的輸出（其餘 80 個檔本來就沒有引號）。
       它守的是【宣告與來源脫節】：來源改版後引號消失或新增，
       若不中止，跨檔 join 會安靜地一列都對不上而不報錯。

    傳入的 first_row 必須是**未經剝除**的原始列。
    """
    found = any(cell.startswith("'") for cell in first_row)
    declared = is_quoted(year, etype, stem)
    if found and not declared:
        raise ValidationError(
            f"{year} {etype} {stem}：來源的欄位值帶前置單引號，但未具名宣告。"
            f"未宣告即不剝除，跨檔 join 會一列都對不上且不報錯。"
            f"首列={first_row[:6]}"
        )
    if declared and not found:
        raise ValidationError(
            f"{year} {etype} {stem}：已具名宣告為帶前置單引號，但來源實際沒有。"
            f"宣告已過期——若放著不管，下次真的有檔新增引號時這項檢查也不會響。"
            f"首列={first_row[:6]}"
        )


def available_terms() -> list[str]:
    """回傳本腳本涵蓋的屆別，由早到晚。"""
    return list(TERMS)


# 候選人長表的欄序。列組裝一律照這個清單產生，不在別處各寫一份。
CANDIDATE_COLUMNS = (
    "年度", "選舉種類", "選舉種類名稱",
    "省市", "縣市", "選舉區", "選舉區_語意", "鄉鎮市區", "村里", "行政區名稱",
    "縣市_正規化", "鄉鎮市區_正規化",
    "號次", "姓名", "政黨代號", "政黨名稱", "性別",
    "年齡", "年齡_原始", "現任",
    "當選註記", "當選註記語意", "當選", "當選_依據",
)


def source_paths(year: str, etype: str) -> dict[str, str]:
    """回傳一個（屆別, 選舉種類）的五個來源檔在壓縮檔內的完整路徑。

    路徑一律由 SOURCE_DIRS 具名推導，不做任何搜尋或樣式比對。
    """
    key = (year, etype)
    if key not in SOURCE_DIRS:
        raise ValidationError(f"未具名的（屆別, 選舉種類）：{key}")
    folder, suffix = SOURCE_DIRS[key]
    out = {}
    for stem in SOURCE_FILES:
        sfx = "" if stem in FILES_WITHOUT_SUFFIX else suffix
        out[stem] = f"{ZIP_PREFIX}{folder}/{stem}{sfx}.csv"
    return out


def load_source(zf: zipfile.ZipFile, names: dict[str, str],
                year: str, etype: str, stem: str) -> list[list[str]]:
    """讀一個來源檔：核對引號宣告 → 剝除引號 → 正規化關聯鍵的尾隨空白。

    ⚠️ 引號的核對必須在 read_csv(quoted=True) 【之前】做。順序對調的話
       撇號已經被吃掉，檢查就永遠看不到「來源本來有引號」——那是恆真檢查。

    ⚠️ **`keys` 一定要傳。** 舊屆的鍵欄帶尾隨空白：1995 兩個 elctks 各有
       225 列的投開票所欄是 `'0 '`（零加一個空白）而不是 `'0'`。
       `is_blank('0 ')` 為偽，那 225 列會被判成【投開票所】層級——
       1995 明明只到鄉鎮市區。實測就是這樣先誤判、才發現漏傳 keys 的。
       正規化範圍沿用既有的 KEY_COLS 白名單，不另立一份，也不整列 strip
       （整列 strip 會改到非關聯鍵的來源值）。
    """
    path = source_paths(year, etype)[stem]
    if path not in names:
        raise ValidationError(f"壓縮檔內找不到 {path}")
    raw = zf.read(names[path]).decode("utf-8", errors="strict")
    first = next((r for r in csv.reader(io.StringIO(raw, newline="")) if r), None)
    if first is None:
        raise ValidationError(f"{path} 沒有任何資料列")
    check_quoting_declaration(year, etype, stem, first)
    return read_csv(zf, names, path, SOURCE_COLS[stem],
                    quoted=is_quoted(year, etype, stem), keys=KEY_COLS[stem])


def check_no_excluded_paths(paths: list[str]) -> None:
    """任何含 `old` 路徑段的來源路徑即中止。

    ⚠️ 這是對【路徑集合】而非對單一路徑的檢查，因為出事的形態是
       「有人把搜尋改成樣式比對，於是 old 那份也被收進來」——
       那時錯的不是某一條路徑，是整個集合多了幾條。
    """
    bad = [p for p in paths
           if EXCLUDED_PATH_SEGMENT in p.split("/")]
    if bad:
        raise ValidationError(
            f"來源路徑含已被取代的 {EXCLUDED_PATH_SEGMENT!r} 目錄，共 {len(bad)} 條："
            f"{sorted(bad)}。正式路徑不含該目錄；該副本的 elctks 比正式版多 54,880 列，"
            f"差異成因未查明，不可混用。"
        )


def resolve_all_sources(names: dict[str, str]) -> dict[tuple[str, str], dict[str, str]]:
    """解析全部十八個（屆別, 選舉種類）的來源路徑，並逐一確認存在。

    `names` 為 zip_names() 的還原表。缺任何一個檔即中止並指名。
    """
    resolved: dict[tuple[str, str], dict[str, str]] = {}
    missing: list[str] = []
    for year in TERMS:
        for etype in ELECTION_TYPES:
            paths = source_paths(year, etype)
            check_no_excluded_paths(list(paths.values()))
            for stem, path in paths.items():
                if path not in names:
                    missing.append(f"{year} {etype} {stem}: {path}")
            resolved[(year, etype)] = paths
    if missing:
        raise ValidationError(
            f"壓縮檔內找不到 {len(missing)} 個來源檔：" + "；".join(missing)
        )
    return resolved


def build_candidates(year: str, etype: str, cand: list[list[str]],
                     paty: dict[str, str], names: dict[tuple, str]) -> list[dict]:
    """組裝候選人長表的列。

    ⚠️ **出生日期、出生地、學歷三欄不進入輸出**（PERSONAL_DATA_COLS）。
       這裡刻意逐欄具名取值而不是「整列複製再刪掉三欄」——後者在來源新增欄位時
       會把新欄位一起帶進輸出，而個資外洩不會有任何錯誤訊息。

    ⚠️ `行政區名稱` 的查表【忽略選舉區欄】。`elbase` 的選舉區欄恆為 `00`，
       而 `elcand` 恆為 `01`；用整組五碼鍵查，2012 起每屆有 8,000 個以上單位查不到。

    `當選`／`當選_依據` 此處留空佔位，由跨檔推導填入（見 derive_elected）。
    `縣市_正規化`／`鄉鎮市區_正規化` 同樣留空佔位，由地理正規化填入。
    """
    check_age_sentinel(year, cand)
    out = []
    for r in cand:
        mark = r[C_MARK].strip()
        if mark not in WIN_MARKS:
            raise ValidationError(
                f"{year} {etype} 候選人 {r[C_NUM]} 的當選註記 {r[C_MARK]!r} "
                f"不是官方定義的四個值之一 {sorted(WIN_MARKS)}"
            )
        party = r[C_PARTY]
        if party not in paty:
            raise ValidationError(
                f"{year} {etype} 候選人 {r[C_NUM]} 的政黨代號 {party!r} "
                f"不在 elpaty 內"
            )
        out.append({
            "年度": year,
            "選舉種類": etype,
            "選舉種類名稱": ELECTION_TYPES[etype],
            "省市": r[0], "縣市": r[1], "選舉區": r[2],
            "選舉區_語意": district_meaning(year, etype),
            "鄉鎮市區": r[3], "村里": r[4],
            # 忽略選舉區欄查名稱——理由見 docstring。
            "行政區名稱": names.get((r[0], r[1], r[3], r[4]), ""),
            "縣市_正規化": "",
            "鄉鎮市區_正規化": "",
            "號次": r[C_NUM],
            "姓名": r[C_NAME],
            "政黨代號": party,
            "政黨名稱": paty[party],
            "性別": r[C_SEX],
            # 乾淨值一律經 valid_age()，不得直接引用 r[C_AGE]。
            "年齡": valid_age(year, r[C_AGE]),
            "年齡_原始": r[C_AGE],
            "現任": r[C_INCUMBENT],
            "當選註記": mark,
            "當選註記語意": WIN_MARKS[mark],
            "當選": "",
            "當選_依據": "",
        })
    for c in out:
        if set(c) != set(CANDIDATE_COLUMNS):
            raise ValidationError(
                f"候選人列的欄位集合與 CANDIDATE_COLUMNS 不符："
                f"多 {sorted(set(c) - set(CANDIDATE_COLUMNS))}、"
                f"少 {sorted(set(CANDIDATE_COLUMNS) - set(c))}"
            )
    return out


def derive_elected(year: str, etype: str, ctks: list[list[str]],
                   cand: list[dict]) -> None:
    """由 elctks 推導當選權威值，就地填入 `當選` 與 `當選_依據`。

    ⚠️ **鍵一律忽略選舉區欄。** 普查確認 `elcand` 的該欄恆為 `01`、`elctks` 恆為 `00`
       （2012 起 `00`／`01` 並存），整組鍵相符數在十八個檔**全部為 0**；忽略後 100% 對上。
       在地方公職那邊忽略選舉區是少數檔案的具名例外，在立委這裡是常態。

    取【最高層級】的註記為準：同一位候選人在檔別合計、縣市、鄉鎮市區…各有一列，
    層級越高越是官方的最終認定。`當選_依據` 記下取自哪一層。
    """
    by_key: dict[tuple, list[tuple[int, str]]] = collections.defaultdict(list)
    for r in ctks:
        # 忽略選舉區欄（索引 2）
        k = (r[0], r[1], r[3], r[4], r[6])
        by_key[k].append((ADMIN_LEVELS.index(admin_level(r[:6])), r[9].strip()))
    for c in cand:
        k = (c["省市"], c["縣市"], c["鄉鎮市區"], c["村里"], c["號次"])
        hits = by_key.get(k)
        if not hits:
            raise ValidationError(
                f"{year} {etype} 候選人 {c['號次']}（{c['姓名']}）在 elctks 找不到任何列。"
                f"忽略選舉區欄後仍對不上，代表鍵的結構變了。"
            )
        top = min(h[0] for h in hits)
        marks = {m for lv, m in hits if lv == top}
        if len(marks) > 1:
            raise ValidationError(
                f"{year} {etype} 候選人 {c['號次']}（{c['姓名']}）在同一層級"
                f"（{ADMIN_LEVELS[top]}）有互相矛盾的當選註記 {sorted(marks)}"
            )
        mark = marks.pop()
        if mark not in WIN_MARKS:
            raise ValidationError(
                f"{year} {etype} 候選人 {c['號次']} 的 elctks 當選註記 {mark!r} "
                f"不是官方定義的四個值之一"
            )
        c["當選"] = "Y" if mark in ELECTED_MARKS else "N"
        c["當選_依據"] = f"elctks_{ADMIN_LEVELS[top]}"


def check_elected_agreement(year: str, etype: str, cand: list[dict]) -> None:
    """補償性檢查：來源註記推導的值 vs 權威值。

    ⚠️ 比對的兩側必須取自【不同的欄】——`當選註記`（來自 elcand）與
       `當選`（來自 elctks）。若哪天有人把左側也改成讀 `當選`，
       這個檢查會恆成立、一筆都收不到，而 63 筆那種異常會靜默流出。

    ⚠️ **不設具名白名單。** 普查確認十八個檔零不符——蓋一份空的白名單等於
       蓋一段沒有資料在測它的程式碼，它會永遠通過而看起來像在保護什麼。
       任何不符一律中止；真的出現異常時，那一刻才是決定怎麼具名的時候，
       而且會有實際資料可以測。
    """
    bad = [c for c in cand
           if (c["當選"] == "Y") != (c["當選註記"] in ELECTED_MARKS)]
    if bad:
        raise ValidationError(
            f"{year} {etype} 有 {len(bad)} 位候選人的 elcand 當選註記與由 elctks "
            f"推導的權威值不一致："
            + "；".join(f"{c['號次']} {c['姓名']} 註記={c['當選註記']!r} "
                        f"權威={c['當選']}（{c['當選_依據']}）" for c in bad[:5])
        )


def check_seat_total(year: str, etype: str, cand: list[dict],
                     prof_seats: int) -> None:
    """三方核對席次：釘死值、elprof 當選人數、由 `當選` 數出的人數。"""
    want = SEATS_BY_TERM[year]
    got = sum(1 for c in cand if c["當選"] == "Y")
    if not (want == prof_seats == got):
        raise ValidationError(
            f"{year} {etype} 席次三方不符：釘死值={want}、"
            f"elprof 當選人數={prof_seats}、由權威值數出={got}"
        )


def area_names(base: list[list[str]]) -> dict[tuple, str]:
    """由 elbase 建（省市, 縣市, 鄉鎮市區, 村里）→ 名稱的對照。

    ⚠️ 鍵**不含選舉區欄**。elbase 的該欄恆為 `00`，elprof／elctks 從 2012 起為 `01`——
       含進去會讓 2012-2024 每屆 8,000 個以上單位查不到名稱（實測 2012 為 8,175）。
       原住民立委是全國單一選區，去掉這一欄不會讓不同單位撞鍵。
    """
    out: dict[tuple, str] = {}
    for r in base:
        k = (r[0], r[1], r[3], r[4])
        if k in out and out[k] != r[5]:
            raise ValidationError(
                f"elbase 的 {k} 對應到兩個名稱：{out[k]!r} 與 {r[5]!r}。"
                f"忽略選舉區欄後撞鍵，這個簡化不成立。"
            )
        out[k] = r[5]
    return out


def main() -> int:
    print("原住民立委長表建置")
    print(f"  來源：{ZIP_PATH}")
    print(f"  輸出：{OUT_DIR}")
    print(f"  選舉種類：{', '.join(f'{k} {v}' for k, v in ELECTION_TYPES.items())}")
    print(f"  涵蓋 {len(TERMS)} 屆：")
    for year in available_terms():
        print(f"    {year}  應選 {SEATS_BY_TERM[year]} 席（每一選舉種類各自）")

    with zipfile.ZipFile(ZIP_PATH) as zf:
        resolved = resolve_all_sources(zip_names(zf))
    print(f"\n  來源路徑解析完成：{len(resolved)} 個（屆別, 選舉種類）、"
          f"{len(resolved) * len(SOURCE_FILES)} 個檔全部存在")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
