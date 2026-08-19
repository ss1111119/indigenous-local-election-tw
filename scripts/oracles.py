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
    "行政區名稱": dict(
        provenance="official", structure="elbase 對照", arithmetic=None,
        semantic="official-doc",
        note="⚠️ 含 Unicode 私用區字元（Big5 遺留），多數字型無字形；"
             "2014 D2 有 417 次查無對應（該屆 elbase 與 elprof 的選舉區欄不一致），"
             "查無次數寫入 validation-report.json",
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
    **_SHARED, **_LEVEL,
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
             "但本專案未查到明文依據，故不作此宣稱",
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
    **_SHARED,
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
    "年齡": dict(provenance="official", structure="official-doc",
               arithmetic=None, semantic="official-doc",
               note="official-doc 說明可能為 0 或 99（無資料）"),
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
        note="**本專案定義**：* 與 ! 皆計為當選。只數 * 會系統性少算且不報錯",
    ),
}

VOTES = {
    **_SHARED, **_LEVEL,
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
