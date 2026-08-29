#!/usr/bin/env python3
"""驗文件裡的高風險數字沒有與實際值漂移。

**為什麼只驗這幾個數字，不做通用的文件一致性檢查：**
通用檢查要先有「同一件事實在哪些地方被寫過」的登錄，而維護那份登錄本身
就會漂移。這裡只盯少數幾個「寫錯了會誤導接手的人、而且能從資料算出來」的數字。

已知的漂移（都是實際發生過的，不是假想）：
- HANDOFF 的 Requirement 總數停在 109，實際 110（歸檔後沒回頭改）
- HANDOFF 有兩個「最後更新」，改了一個另一個就過期（08-21 vs 08-29）
- 清點報告仍寫「未檢查」，而 HANDOFF 已記為已查證

⚠️ **這支不驗散文，也不驗溯源是否正確。** 它只驗數字。
   文件說了什麼、說得對不對，仍然只能靠人看——見 HANDOFF 地雷 1u。

用法：
    python scripts/check_doc_numbers.py
"""

from __future__ import annotations

import csv
import gzip
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class DocNumberError(Exception):
    """文件數字與實際不符。"""


def actual_spec_counts() -> tuple[int, int]:
    specs = sorted((ROOT / "openspec" / "specs").glob("*/spec.md"))
    if not specs:
        raise DocNumberError("找不到任何 openspec/specs/*/spec.md——無法比對")
    reqs = sum(len(re.findall(r"^### Requirement", p.read_text(encoding="utf-8"), re.M))
               for p in specs)
    return len(specs), reqs


def actual_d1mt_units() -> int:
    path = ROOT / "data" / "processed" / "cec-local-election-summary-long.csv.gz"
    if not path.exists():
        raise DocNumberError(f"找不到長表 {path}——無法比對 D1-MT 單位數")
    units = set()
    with gzip.open(path, "rt", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if row["選舉種類"] == "D1-MT" and row["層級"] == "鄉鎮市區":
                units.add((row["年度"], row["省市"], row["縣市"], row["鄉鎮市區"]))
    if not units:
        raise DocNumberError("長表中找不到任何 D1-MT 鄉鎮市區列——無法比對")
    return len(units)


def check_claims() -> list[str]:
    """回傳不符的敘述。每一項都具名到檔案、實際值與文件值。"""
    n_caps, n_reqs = actual_spec_counts()
    n_units = actual_d1mt_units()

    problems: list[str] = []

    # (檔案, 正規式, 期望值, 說明)。正規式必須恰好抓到一個數字群組。
    claims = [
        ("HANDOFF.md", r"主 specs：(\d+) 個能力", n_caps, "能力數"),
        ("HANDOFF.md", r"個能力、\*\*(\d+) 條 Requirement", n_reqs, "Requirement 數"),
    ]
    for fname, pattern, want, label in claims:
        text = (ROOT / fname).read_text(encoding="utf-8")
        found = re.findall(pattern, text)
        if not found:
            problems.append(f"{fname}：找不到「{label}」的敘述（正規式 {pattern!r}）"
                            "——文件改寫過就要同步改這支檢查")
            continue
        for got in found:
            if int(got) != want:
                problems.append(f"{fname}：{label} 寫 {got}，實際 {want}")

    # D1-MT 單位數散見多處，全部要一致。
    #
    # ⚠️ **必須錨定到「七屆」。** 第一版只抓 `(\d+) 個單位`，結果把
    #    「1,290 個單位」（鄉鎮市區正規化）、「1,402 個單位」（村里缺列）、
    #    「267,481 個單位」（逐一對帳）全抓成 D1-MT 而誤報四筆。
    #    **會誤報的檢查會被忽略**，忽略之後它與不存在無異。
    d1mt_units = re.compile(r"七屆(?:共)?\s*(\d[\d,]*) 個單位")
    for fname in ("HANDOFF.md", "README.md"):
        text = (ROOT / fname).read_text(encoding="utf-8")
        found = d1mt_units.findall(text)
        if not found:
            problems.append(f"{fname}：找不到「七屆…個單位」的敘述"
                            "——文件改寫過就要同步改這支檢查")
        for got in found:
            if int(got.replace(",", "")) != n_units:
                problems.append(f"{fname}：D1-MT 單位數寫 {got}，實際 {n_units}")

    # ⚠️ 同一份文件裡出現兩個日期戳，改一個另一個就過期。實際發生過
    #    （2026-08-29 時第 3 行停在 08-21、第 10 行已是 08-29）。
    #
    # ⚠️ 只數**帶日期的**那種。第一版數所有「最後更新」字樣，結果把
    #    解釋這個問題的那句散文自己也算進去——檢查絆倒在它自己的說明上。
    handoff = (ROOT / "HANDOFF.md").read_text(encoding="utf-8")
    stamps = re.findall(r"最後更新：\s*\d{4}-\d{2}-\d{2}", handoff)
    if len(stamps) > 1:
        problems.append(f"HANDOFF.md：出現 {len(stamps)} 個帶日期的「最後更新」，"
                        "只該有一個——多個必然有一個是過期的")
    if not stamps:
        problems.append("HANDOFF.md：找不到帶日期的「最後更新」戳記")

    return problems


def main() -> int:
    try:
        problems = check_claims()
    except DocNumberError as exc:
        print(f"★ 中止：{exc}")
        return 1

    if problems:
        print("★ 文件數字與實際不符：")
        for p in problems:
            print(f"    {p}")
        return 1

    n_caps, n_reqs = actual_spec_counts()
    print(f"✓ 文件數字與實際相符（{n_caps} 個能力、{n_reqs} 條 Requirement、"
          f"D1-MT {actual_d1mt_units()} 個單位）")
    print("⚠️ 本檢查只驗數字，不驗散文是否正確——見 HANDOFF 地雷 1u。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
