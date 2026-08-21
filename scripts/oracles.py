#!/usr/bin/env python3
"""每個輸出欄位的 oracle 宣告。

## 為什麼需要這個

本專案曾經有 147 項測試全部通過，同時卻：

- 把 `有效票`／`無效票` 誤記為「投票數 男／女」——算術自我驗證照樣通過，
  因為 `63,768 + 3,067 = 66,835` 兩種解讀都成立
- 宣稱資料中「未出現 `-`」而從未清點——實際有 36 筆
- 把 `得票率` 原樣抄出，從未做過任何驗證

問題不是驗證太少，而是**沒有區分「驗了什麼」**。欄數對、加總對、鍵唯一，
都不能告訴你這一欄的**語意**是否正確。因此把每個欄位的正確性拆成三層，
並且逐欄記錄**是什麼東西**確立了它：

| 層 | 回答的問題 | 可用的 oracle |
| --- | --- | --- |
| 結構 | 這一欄在不在它該在的位置、格式對不對 | 官方格式文件；內部一致性 |
| 算術 | 它與其他欄位的數值關係成不成立 | 檔案內部的加總關係 |
| 語意 | **它到底是什麼意思** | 官方格式文件；官方代碼表；同母體的外部約束；外部資料集 |

**語意層是唯一能抓出 idx6/idx7 那類錯誤的。** 前兩層再多都不行。

## 誠實的分級

`semantic` 欄位只允許以下值，不得含糊：

- `official-doc`      — 官方格式文件明文定義
- `official-table`    — 官方代碼對照表（如 選舉種類代碼.xlsx、elpaty）
- `cross-population`  — 用「同一母體的兩份資料」這類外部約束確立
                        （例：D2 與 R3 是同一批選民，證明 idx7 不是性別）
- `external-dataset`  — 與專案外的資料集交叉驗證（如內政部行政區代碼）
- `project-defined`   — 本專案自己定義的欄位，無外部 oracle 可言
- `project-inferred`  — **本專案推定，來源未明說**
- `none`              — **已抽取，尚無獨立語意驗證**

最後兩種是誠實的答案，不是缺陷；把它們寫成 `official-doc` 才是。
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 本專案自訂的選舉種類代碼
#
# 官方對照表 選舉種類代碼.xlsx 只涵蓋 2022 年的種類。1994-2006 有兩類在官方表中
# 根本不存在，強行寫成 T2／T3 會讓跨屆折線出現無意義的跳點：
#
#   1. 台灣省議員（山地／平地原住民）——省議會於 1998 年精省後廢除，
#      與現行縣市議員是不同的職位，不可與 T2／T3 相加。
#   2. 直轄市議員的「原住民」合併類別（1994／1998／2002／2006）——未分平地／山地。
#      T2 與 T3 互斥，合併類別是兩者的聯集，因此【兩者皆非】。
#      實測：該支的 elbase 無選舉區層級、elcand 選舉區欄全為 00，
#      沒有任何欄位可以拆出山地／平地。
#
# ⚠️ 代碼形式刻意含連字號。官方代碼一律為【兩字元英數】（T1/T2/T3/D2/R3/R2），
#    沒有任何官方代碼含 '-'，所以連字號本身就是「這不是官方代碼」的標記，
#    同時也保證中選會日後新增代碼時不會與本專案自訂者衝突。
CUSTOM_ELECTION_TYPES = {
    "T-PRV3": "臺灣省議員(山地原住民)選舉",
    "T-PRV2": "臺灣省議員(平地原住民)選舉",
    "T-COMBO": "直轄市議員(原住民，未分平地／山地)選舉",
}

# 行政區代碼系統。跨屆的代碼互不相通，下游比對行政區前必須先確認系統相同。
#
# ⚠️ 1998／2002 的值指的是【同屆「區域」檔的代碼系統】——山原／平原檔的原始代碼
#    是各檔內部重新編號的，建置時已依 cec-county-code-crosswalk-1998-2002.csv
#    轉換為區域檔代碼，故標記的是轉換後的系統，不是來源檔的原始編號。
# ⚠️ 1994 的省議員檔【沒有縣市層級】（elbase 只有檔別合計與選舉區／鄉鎮市區），
#    同屆直轄市檔才有縣市代碼。兩者共用「1994」這個標記，但可比對的層級不同。
ADMIN_CODE_SYSTEMS = {
    "1994": "1994",
    "1998": "1998",
    "2002": "2002",
    "2005": "2005+",
    "2006": "2005+",
    "2009-2010": "2009",
    "2014": "2014+",
    "2018": "2014+",
    "2022": "2014+",
}

# 檔別涵蓋的行政層級。來源用過三種寫法（2022 的 city／prv、2014-2018 的中文名、
# 2009-2010 的含日期名），所以逐一列舉而【不用字串比對去猜】。
# None 代表該檔為全國單一檔，層級由選舉種類本身決定。
#
# ⚠️ 新增屆別時必須在此登記檔別名稱，否則 office_type() 會中止。
#    這是刻意的：猜錯 city／prv 會把直轄市的數字記成縣市的，而且不會報錯。
FILE_SCOPE = {
    "city": "縣市",
    "prv": "直轄市",
    "單一": None,
    "縣市 2009-12-05": "縣市",
    "五都 2010-11-27": "直轄市",
}

# 類別粒度：這個選舉種類把原住民分到什麼程度。
# 這份對照表的鍵是本檔認識的【全部】選舉種類——官方六種加上自訂三種。
# scripts/test_build_local_election.py 有一項測試釘住它與 ELECTION_TYPES 的一致性，
# 任何一邊新增種類而另一邊沒跟上都會被擋下。
ELECTION_TYPE_GRANULARITY = {
    "T1": "非原住民選舉種類（對照組）",
    "T2": "分平地山地",
    "T3": "分平地山地",
    "R2": "分平地山地",
    "D2": "不分平地山地（原住民區）",
    "R3": "不分平地山地（原住民區）",
    "T-PRV2": "分平地山地",
    "T-PRV3": "分平地山地",
    "T-COMBO": "合併未分平地山地",
}

# 各選舉種類的職位。T1／T2／T3 的職位取決於檔別（縣市議員或直轄市議員），
# 其餘種類與檔別無關。
_COUNCILLOR_TYPES = {"T1", "T2", "T3"}
_FIXED_OFFICE = {
    "D2": "直轄市原住民區長",
    "R3": "直轄市原住民區民代表",
    "R2": "鄉(鎮、市)民代表",
    "T-PRV2": "臺灣省議員",
    "T-PRV3": "臺灣省議員",
    "T-COMBO": "直轄市議員",
}


# 人口數欄適用的行政層級。spec 明定 county-level and above。
#
# ⚠️ 「適用」不等於「已驗證」。實測（2026-08-19）：
#    - 檔別合計與縣市層級出現帶小數的值（如 2002 山原全國 206740.121634792），
#      而戶籍人口是離散的人頭計數，不可能有小數——該數字顯然經過推算，
#      不是原始統計值。這一欄沒有算術 oracle、底層來源也未查證。
#    - 選舉區層級雖然「人口數 ≥ 選舉人數」的違反率只有 1/607，但那是弱證據，
#      一個恰好大於選舉人數的常數也會通過。故不放寬。
#    - 舊屆鄉鎮市區以下多為常數（1998／2002 的 1888、1994 的 81169、2005 的 1234）；
#      既有四屆的村里／投開票所則是來源未填（值為 0）。兩者都不適用。
POPULATION_APPLICABLE_LEVELS = ("檔別合計", "直轄市縣市")
POPULATION_APPLICABLE = "縣市以上"
POPULATION_NOT_APPLICABLE = "低於縣市_不適用"


def population_applicability(level: str) -> str:
    """人口數欄在這個行政層級是否適用。

    刻意用「適用」而非「可用」或「有效」——後兩者會被讀成「數值已驗證」，
    而本專案對這一欄的數值正確性【不作任何保證】。
    """
    return (POPULATION_APPLICABLE if level in POPULATION_APPLICABLE_LEVELS
            else POPULATION_NOT_APPLICABLE)


class OracleError(Exception):
    """可比性標記無法判定。中止而不是套用預設值。"""


def is_main_sequence(etype: str) -> bool:
    """這個選舉種類能不能進入跨屆主序列（可畫折線圖）。

    自訂代碼一律不進主序列：省議員是已廢除的不同職位，直轄市合併類別
    與 T2／T3 的粒度不同。兩者若混入折線，1994→1998 會被讀成參政權暴增。

    ⚠️ 這是【推導值，不是查表值】——主序列資格等同於「是官方選舉種類代碼」，
    另建一份清單就會有兩個真相來源。
    """
    if etype not in ELECTION_TYPE_GRANULARITY:
        raise OracleError(
            f"未登記的選舉種類 {etype!r}。新增種類必須同時登記於 "
            f"ELECTION_TYPE_GRANULARITY（自訂代碼另需登記於 CUSTOM_ELECTION_TYPES）"
        )
    return etype not in CUSTOM_ELECTION_TYPES


def office_type(etype: str, label: str) -> str:
    """職位類型。T1／T2／T3 由檔別決定是縣市議員還是直轄市議員。"""
    if etype in _FIXED_OFFICE:
        return _FIXED_OFFICE[etype]
    if etype not in _COUNCILLOR_TYPES:
        raise OracleError(f"未登記的選舉種類 {etype!r}，無法判定職位類型")
    if label not in FILE_SCOPE:
        raise OracleError(
            f"未登記的檔別 {label!r}。新增屆別必須在 FILE_SCOPE 登記其檔別名稱——"
            f"猜錯 city／prv 會把直轄市的數字記成縣市的，且不會報錯"
        )
    scope = FILE_SCOPE[label]
    if scope is None:
        raise OracleError(
            f"檔別 {label!r} 為全國單一檔，但選舉種類 {etype!r} 的職位取決於檔別，"
            f"無法判定是縣市議員還是直轄市議員"
        )
    return f"{scope}議員"


def comparability_flags(year: str, etype: str, label: str) -> dict[str, str]:
    """三張長表共用的可比性標記欄位。

    下游開發者不能靠閱讀 README 來過濾資料，長表本身必須具備自我描述能力。
    布林值寫成小寫 'true'／'false' 字串——CSV 沒有布林型別，
    而 Python 的 'True'／'False' 大寫形式對其他語言的讀取端不友善。
    """
    main = is_main_sequence(etype)   # 先驗選舉種類是否已登記
    if year not in ADMIN_CODE_SYSTEMS:
        raise OracleError(
            f"未登記的屆別 {year!r}。新增屆別必須在 ADMIN_CODE_SYSTEMS 登記其"
            f"行政區代碼系統——跨屆代碼互不相通，漏登記等於默認可比對"
        )
    return {
        "office_type": office_type(etype, label),
        "category_granularity": ELECTION_TYPE_GRANULARITY[etype],
        "is_main_sequence": "true" if main else "false",
        "admin_code_system": ADMIN_CODE_SYSTEMS[year],
    }


# 三張長表共用的識別與行政區欄位
_SHARED = {
    "年度": dict(
        provenance="project", structure="本專案指定的屆別標籤",
        arithmetic=None, semantic="project-defined",
        note="2009-2010 合併兩次投票，是本專案的建模判斷，非來源給的分屆方式",
    ),
    "選舉種類": dict(
        provenance="official", structure="來源資料夾對應",
        arithmetic=None, semantic="official-table",
        note="T2/T3/D2/R3/R2/T1 是【2022 年】官方對照表的代碼。"
             "套用到 2018／2014／2009-2010 是本專案依資料夾名稱推定，"
             "非官方宣告的跨屆對應——語意在 2022 為 official-table，其餘屆為 project-inferred",
    ),
    "選舉種類名稱": dict(
        provenance="official", structure="官方對照表原始字串",
        arithmetic=None, semantic="official-table", note="未改寫，含半形括號",
    ),
    "檔別": dict(
        provenance="project", structure="本專案指定",
        arithmetic=None, semantic="project-defined",
        note="city／prv／單一；2009-2010 為「縣市 2009-12-05」「五都 2010-11-27」，"
             "日期取自來源資料夾名稱",
    ),
    "省市": dict(
        provenance="official", structure="official-doc（欄位順序）",
        arithmetic=None, semantic="official-doc",
        note="⚠️ 2014 起可與內政部戶役政代碼互通（已交叉驗證）；"
             "2009-2010 及更早是另一套編碼，【未與任何外部來源交叉驗證】",
    ),
    "縣市": dict(provenance="official", structure="official-doc",
                arithmetic=None, semantic="official-doc", note="同上"),
    "選舉區": dict(provenance="official", structure="official-doc",
                 arithmetic=None, semantic="official-doc", note=None),
    "鄉鎮市區": dict(
        provenance="official", structure="official-doc", arithmetic=None,
        semantic="external-dataset",
        note="2014 起：省市+縣市+鄉鎮市區 = 內政部 TOWNCODE，368/368 完全對上。"
             "2009-2010 及更早未驗證",
    ),
    "村里": dict(
        provenance="official", structure="official-doc", arithmetic=None,
        semantic="external-dataset",
        note="2014 起與內政部村里代碼對上 7,688/7,976（96.39%），"
             "差額已逐筆分類（行政區改制、跨村里投開票所自訂碼）。首碼可能為英文",
    ),
    "縣市_正規化": dict(
        provenance="project", structure="1998／2002 經對照表換算，其餘屆別為原碼",
        arithmetic="換算時驗證本地檔名稱、對照表名稱、同屆區域檔名稱三方一致",
        semantic="project-defined",
        note="**本專案定義**：同屆「區域」檔口徑的縣市代碼。"
             "1998／2002 的原住民分項檔縣市代碼在各檔內部重新編號"
             "（與區域檔不一致者：1998 山原 6/12、平原 9/10、2002 山原 6/12、平原 10/11），"
             "跨檔用原碼 join 會【靜默對錯縣市】。**跨檔比對縣市請用本欄，不要用 `縣市`**",
    ),
    "鄉鎮市區_正規化": dict(
        provenance="project", structure="可跨檔比對者為原碼，否則留空",
        arithmetic=None, semantic="project-defined",
        note="⚠️ **空字串代表「該檔的鄉鎮市區代碼是檔內重編、本專案未正規化」，"
             "不是資料缺漏。**實測 1998／2002／2005 的原住民分項檔鄉鎮市區代碼"
             "皆為檔內重編（與同屆區域檔名稱不同者：1998 山原 195/226、平原 139/177、"
             "2002 山原 168/226、平原 99/211、2005 山原 153/226、平原 76/224）——"
             "所以「2005 起才是全域代碼」**只在縣市層級成立**。"
             "刻意留空而非放原始碼：放原始碼會變成偽裝成標準鍵的毒藥，"
             "下游用（縣市, 鄉鎮市區）join 會成功但對錯行政區。"
             "各屆直轄市原住民檔與同屆直轄市區域檔完全相同，不受影響",
    ),
    "行政區名稱": dict(
        provenance="official", structure="elbase 對照", arithmetic=None,
        semantic="official-doc",
        note="⚠️ 含 Unicode 私用區字元（Big5 遺留），多數字型無字形；"
             "2014 D2 有 417 次查無對應（該屆 elbase 與 elprof 的選舉區欄不一致），"
             "查無次數寫入 validation-report.json",
    ),
}

# 可比性標記欄位（Comparability Flags）。三張長表都有。
#
# 這四欄【全部是本專案的衍生欄位】，來源一欄都沒有，因此語意層一律 project-defined，
# 也一律沒有算術 oracle——沒有任何檔案內部的數值關係可以驗證它們。
# 它們的正確性靠 scripts/test_build_local_election.py 的單元測試守住。
_FLAGS = {
    "office_type": dict(
        provenance="project", structure="由選舉種類與檔別推導",
        arithmetic=None, semantic="project-defined",
        note="T1／T2／T3 的職位取決於檔別（縣市議員或直轄市議員），"
             "檔別名稱須登記於 FILE_SCOPE，未登記即中止——"
             "猜錯 city／prv 會把直轄市的數字記成縣市的且不會報錯",
    ),
    "category_granularity": dict(
        provenance="project", structure="由選舉種類推導",
        arithmetic=None, semantic="project-defined",
        note="這個選舉種類把原住民分到什麼程度：分平地山地／合併未分／"
             "不分平地山地（原住民區）／非原住民選舉種類。"
             "⚠️ 1994-2006 直轄市議員為【合併類別】，與 T2／T3 粒度不同，不可混計",
    ),
    "is_main_sequence": dict(
        provenance="project", structure="由選舉種類推導（是否為官方代碼）",
        arithmetic=None, semantic="project-defined",
        note="**本專案定義**：僅官方選舉種類代碼進主序列，可用於畫跨屆折線。"
             "1994 台灣省議員（已廢除的職位）與直轄市原住民合併類別標為 false。"
             "值為小寫 'true'／'false' 字串——CSV 沒有布林型別",
    ),
    "admin_code_system": dict(
        provenance="project", structure="由屆別推導",
        arithmetic=None, semantic="project-defined",
        note="行政區代碼系統至少六套互不相通：1994／1998／2002／2005+／2009／2014+。"
             "⚠️ 1998／2002 標記的是【轉換後】的同屆區域檔系統，"
             "來源檔的原始代碼是各檔內部重新編號的。跨屆比對行政區前必須先確認此欄相同",
    ),
}

_LEVEL = {
    "層級": dict(
        provenance="project", structure="由補零規則推導",
        arithmetic=None, semantic="official-doc",
        note="official-doc 說明各層級彙總時下位欄為 0；本專案據此推導出層級標籤。"
             "這是【本專案的衍生欄位】，來源沒有這一欄",
    ),
    "投開票所": dict(provenance="official", structure="official-doc",
                  arithmetic=None, semantic="official-doc", note=None),
}

SUMMARY = {
    **_SHARED, **_FLAGS, **_LEVEL,
    "有效票": dict(
        provenance="official", structure="official-doc（idx6）",
        arithmetic="有效票 + 無效票 = 投票數（逐列）；逐一行政單位的候選人得票加總 = 有效票",
        semantic="official-doc",
        note="⚠️ 曾被本專案誤記為「投票數 男」。算術驗證無法分辨——"
             "63,768+3,067=66,835 兩種解讀都成立。是 official-doc 與 "
             "cross-population（D2/R3 同批選民、無效票率不同）共同確立的",
    ),
    "無效票": dict(
        provenance="official", structure="official-doc（idx7）",
        arithmetic="同上", semantic="official-doc", note="同上",
    ),
    "投票數": dict(
        provenance="official", structure="official-doc（idx8）",
        arithmetic="有效票+無效票=投票數；投票數 ≤ 選舉人數",
        semantic="official-doc", note=None,
    ),
    "選舉人數": dict(
        provenance="official", structure="official-doc（idx9）",
        arithmetic="投票數 ≤ 選舉人數；投票率重算的分母",
        semantic="official-doc",
        note="為 0 的列必須整列為 0（已驗證）。T2/T3 有近四成是這種全零列",
    ),
    "人口數": dict(
        provenance="official", structure="official-doc（idx10）",
        arithmetic=None,
        semantic="official-doc",
        note="⚠️ **本欄沒有任何算術 oracle**——檔案內沒有任何關係可以驗證它。"
             "且其【底層來源未查證】：一般認為係中選會彙編內政部戶政司戶籍資料，"
             "但本專案未查到明文依據，故不作此宣稱。"
             "**原樣保留為字串、不轉型、不重算**——舊屆有帶小數的值"
             "（2002 山原全國 206740.121634792），int() 會直接拋例外。"
             "適用層級見 `人口數適用層級` 欄；本專案不保證本欄任何層級的數值正確性",
    ),
    "人口數適用層級": dict(
        provenance="project", structure="由層級推導",
        arithmetic=None, semantic="project-defined",
        note="**本專案定義**：`縣市以上`（檔別合計與直轄市縣市）或 `低於縣市_不適用`。"
             "⚠️ 「適用」【不等於】「數值已驗證」——縣市層級也出現不可能是人頭計數的"
             "小數值。實測不適用的證據：舊屆鄉鎮市區以下多為常數（1888／81169／1234）、"
             "既有四屆的村里與投開票所為來源未填（值為 0，共 200,175 列）",
    ),
    "候選人數": dict(
        provenance="official", structure="official-doc（idx11-16，多種版面）",
        arithmetic="男+女=合計 的版面偵測；與 elcand 實際列數對帳",
        semantic="official-doc",
        note="⚠️ official-doc（民國 101 年）的欄序與 2022 實際資料【不符】。"
             "文件已過時但欄位語意仍為權威；欄序靠算術自我驗證分辨，"
             "兩種版面皆不通過或同時通過皆中止",
    ),
    "當選人數": dict(
        provenance="official", structure="official-doc（idx11-16）",
        arithmetic="男+女=合計；與 elcand 中當選為 Y 的列數對帳",
        semantic="official-doc",
        note="對帳會抓到「只數 * 漏掉 !」——實測 R2 會報 72 vs 70",
    ),
    "投票率": dict(
        provenance="official", structure="official-doc（idx18）",
        arithmetic="逐列精確重算，四捨五入（ROUND_HALF_UP），157,081 列，不設容差",
        semantic="official-doc",
        note="慣例已確認為四捨五入而非銀行家捨入（後者有 47 列差 0.01）。"
             "1 列已具名為來源異常（2010 進位臨界的浮點產物）",
    ),
    "版面": dict(
        provenance="project", structure="本專案偵測結果",
        arithmetic=None, semantic="project-defined",
        note="來源沒有這一欄。保留偵測結果作為可稽核性的一部分",
    ),
}

CANDIDATES = {
    **_SHARED, **_FLAGS,
    "號次": dict(provenance="official", structure="official-doc",
               arithmetic="（行政區＋號次）在檔別內唯一",
               semantic="official-doc", note=None),
    "姓名": dict(
        provenance="official", structure="official-doc", arithmetic=None,
        semantic="official-doc",
        note="⚠️ 可能同時含漢名與族語名，來源即如此未拆分；部分含私用區字元。"
             "**來源沒有跨屆的候選人識別碼**，相同姓名不可推定為同一人",
    ),
    "政黨代號": dict(provenance="official", structure="official-doc",
                 arithmetic=None, semantic="official-doc", note=None),
    "政黨名稱": dict(
        provenance="official", structure="elpaty 對照", arithmetic=None,
        semantic="official-table",
        note="999 的官方名稱是「無黨籍及未經政黨推薦」，不等同一般語意的「無黨籍」",
    ),
    "性別": dict(provenance="official", structure="official-doc",
               arithmetic=None, semantic="official-doc",
               note="official-doc 明定 1:男 2:女；本專案已解讀為中文"),
    "年齡": dict(
        provenance="project", structure="有記載為原值，未記載留空",
        arithmetic=None, semantic="project-defined",
        note="⚠️ **這是乾淨值，不是來源原樣**——來源原值在 `年齡_原始`。"
             "空字串代表「來源未記載」，不是資料缺漏。"
             "official-doc 明列兩個無資料值，本專案的處置不對稱："
             "`0` 不可能是真實年齡，任何屆別都留空；"
             "`99` 落在合法年齡值域內，只在具名的 1994／1998／2002／2005／2006 "
             "五屆留空（實測那五屆共 483 位候選人整批是 99，"
             "2009-2010 以後四屆從未出現 99、範圍 23–89，全資料的 0 出現 0 次）。"
             "若把 99 寫成無條件規則，將來真有 99 歲候選人時會吃掉真值。"
             "⚠️ **乾淨不等於正確**：只保證不含哨兵值，不保證年齡本身正確——"
             "來源記載的年齡正確與否，本專案未查證也無從查證。"
             "⚠️ 對調的理由：`年齡` 有最強的預設吸引力，不讀文件的分析者第一直覺"
             "就是 `AVG(年齡)`。把乾淨值放在最直覺的名字下才真正封閉陷阱。"),
    "年齡_原始": dict(
        provenance="official", structure="official-doc",
        arithmetic=None, semantic="official-doc",
        note="**來源原樣，含無資料值。** official-doc 說明可能為 0 或 99（無資料）。"
             "要聚合請用 `年齡`（已移除哨兵值）"),
    "現任": dict(provenance="official", structure="official-doc",
               arithmetic=None, semantic="official-doc",
               note="official-doc 明定 Y:現任 N:非現任。非本專案判定"),
    "當選註記": dict(
        provenance="official", structure="official-doc",
        arithmetic="值域必須是官方定義的四值，出現未知值即中止；與 elctks 一致",
        semantic="official-doc",
        note="official-doc 明定四值：* 當選、空白 未當選、! 婦女保障、"
             "- 因婦女保障被排擠未當選。⚠️ 本專案曾誤稱資料中未出現 '-'，"
             "實際有 36 筆。註記分布現已寫入 validation-report.json",
    ),
    "當選註記語意": dict(provenance="project", structure="本專案解讀",
                   arithmetic=None, semantic="official-doc",
                   note="official-doc 的四值定義，逐字對應"),
    "當選": dict(
        provenance="project", structure="本專案解讀",
        arithmetic="與 elprof 的當選人數對帳",
        semantic="project-defined",
        note="**本專案定義**：* 與 ! 皆計為當選。只數 * 會系統性少算且不報錯。"
             "⚠️ 本欄由 `elcand` 的當選註記推導，**會反映來源的已知錯誤**——"
             "2005 縣市議員的 elcand 當選註記欄損壞（山原只標 18 席、平原 20 席）。"
             "需要正確席次者請用 `elected_authoritative`",
    ),
    "elected_authoritative": dict(
        provenance="project", structure="由 elctks 跨檔推導",
        arithmetic="總數 = elprof 當選人數；逐選舉區人數 = elprof 當選人數；"
                   "與 elcand 的 `當選` 必須一致，除逐一具名的已知異常",
        semantic="project-defined",
        note="**本專案定義的當選權威值。**由 elctks 推導：以候選人非空白的行政區"
             "代碼欄約束 elctks 的列，取最高層級，該層級註記須一致，否則中止。"
             "⚠️ 與 `當選` 的分工：`當選` 是【來源怎麼寫】，本欄是【跨檔比對後的判定】。"
             "健康屆別兩者相同（既有四屆 7,335 筆實測零不一致），"
             "2005 兩檔不同。**下游要席次請用本欄**。"
             "值為小寫 'true'／'false' 字串——CSV 沒有布林型別",
    ),
    "elected_authoritative_basis": dict(
        provenance="project", structure="推導時記錄",
        arithmetic=None, semantic="project-defined",
        note="本專案定義：權威值取自 elctks 的哪一個層級，如 `elctks_選舉區`、"
             "`elctks_鄉鎮市區`。⚠️ 刻意保留依據而非只留布林值——"
             "既有四屆有 726 筆取自鄉鎮市區層級（該候選人沒有選舉區層級的彙總列），"
             "沒有這一欄就看不出哪些列的依據較弱",
    ),
}

VOTES = {
    **_SHARED, **_FLAGS, **_LEVEL,
    "號次": dict(provenance="official", structure="official-doc",
               arithmetic="（行政單位＋號次）唯一；與 elcand 雙向參照完整",
               semantic="official-doc", note=None),
    "得票數": dict(
        provenance="official", structure="official-doc",
        arithmetic="逐一行政單位的加總 = elprof 同單位的有效票（71,631 個單位）；不得為負",
        semantic="official-doc", note=None,
    ),
    "得票率": dict(
        provenance="official", structure="official-doc",
        arithmetic="**部分**——慣例已確認但無法完全重現，見 note",
        semantic="official-doc",
        note="⚠️ **本欄長期沒有任何驗證，是原樣抄出的。**建立 oracle 分層時才發現。\n"
             "已查明的事實：捨入慣例【隨屆別改變】——2009-2010／2014／2018 為"
             "無條件捨去（吻合 99.97–99.98%），2022 為四捨五入（吻合 100.00%）。"
             "這與同一份資料的 `投票率` 不同（四屆皆四捨五入）。\n"
             "殘餘 0.02–0.03% 無法重現：精確值在小數第一位終止者（如 51/125 = 40.8）"
             "檔案寫 40.79，是來源端浮點的產物；但改用浮點重算會讓不符數從 253 增至 613"
             "（29/50 = 58 檔案寫 58，浮點截斷得 57.99），兩個方向的誤差都有。\n"
             "**結論：本專案原樣保留來源值，不重算、不宣稱已驗證。**",
    ),
    "當選註記": dict(provenance="official", structure="official-doc",
                 arithmetic="值域四值；與 elcand 一致",
                 semantic="official-doc", note=None),
}

MANIFEST = {"summary": SUMMARY, "candidates": CANDIDATES, "votes": VOTES}

SEMANTIC_LEVELS = {
    "official-doc", "official-table", "cross-population",
    "external-dataset", "project-defined", "project-inferred", "none",
}


def check_manifest(actual_columns: dict[str, list[str]]) -> list[str]:
    """比對 manifest 與實際輸出欄位，回傳問題清單。

    這個檢查是 manifest 不腐爛的唯一保證：新增欄位而未宣告 oracle 就會被擋下。
    """
    problems = []
    for table, cols in actual_columns.items():
        declared = MANIFEST.get(table)
        if declared is None:
            problems.append(f"{table}：manifest 中沒有這張表")
            continue
        missing = [c for c in cols if c not in declared]
        extra = [c for c in declared if c not in cols]
        if missing:
            problems.append(f"{table}：這些欄位沒有宣告 oracle：{missing}")
        if extra:
            problems.append(f"{table}：manifest 宣告了不存在的欄位：{extra}")
        for c, d in declared.items():
            if d["semantic"] not in SEMANTIC_LEVELS:
                problems.append(f"{table}.{c}：semantic 值不合法：{d['semantic']!r}")
    return problems


_LAYER_DESC = {
    "official-doc": "官方格式文件明文定義",
    "official-table": "官方代碼對照表",
    "cross-population": "同一母體的外部約束",
    "external-dataset": "與專案外資料集交叉驗證",
    "project-defined": "本專案定義，無外部 oracle",
    "project-inferred": "本專案推定，來源未明說",
    "none": "已抽取，尚無獨立語意驗證",
}


def render_markdown() -> str:
    """由 manifest 生成文件。手寫一份會脫節，所以用生成的。"""
    out = [
        "# 欄位 oracle 宣告",
        "",
        "**這份文件由 `scripts/oracles.py` 生成，不要手改。**",
        "",
        (__doc__ or "").split("## 誠實的分級")[0].split("## 為什麼需要這個")[1].strip(),
        "",
        "## 語意層的分級",
        "",
        "| 值 | 意思 |",
        "| --- | --- |",
    ]
    for k, v in _LAYER_DESC.items():
        out.append(f"| `{k}` | {v} |")
    out += [
        "",
        "`project-inferred` 與 `none` 是誠實的答案，不是缺陷；"
        "把它們寫成 `official-doc` 才是。",
        "",
    ]
    names = {"summary": "選舉概況 summary", "candidates": "候選人 candidates",
             "votes": "候選人得票 votes"}
    for table, fields in MANIFEST.items():
        n_arith = sum(1 for v in fields.values() if v["arithmetic"])
        out += [
            f"## {names[table]}",
            "",
            f"共 {len(fields)} 欄，其中 **{n_arith} 欄有算術 oracle**"
            f"（其餘 {len(fields) - n_arith} 欄只靠語意 oracle，"
            f"沒有任何檔案內部的數值關係可以驗證）。",
            "",
            "| 欄位 | 來源 | 語意 oracle | 算術 oracle | 備註 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for col, d in fields.items():
            prov = {"official": "官方原值", "project": "本專案"}[d["provenance"]]
            arith = d["arithmetic"] or "—"
            note = (d["note"] or "").replace("\n", " ")
            out.append(
                f"| `{col}` | {prov} | `{d['semantic']}` | {arith} | {note} |"
            )
        out.append("")
    return "\n".join(out)
