#!/usr/bin/env python3
"""變異測試：把 build_party_list_election.py 與 oracles.py 的檢查逐一改壞，
確認 test_build_party_list_election.py 會失敗（而不是照樣通過）。

用法：python scripts/mutate_build_party_list_election.py

每個變異都在 `_mut/` 的獨立副本上做，**不動真正的 scripts/**。

⚠️ 副本必須放在 repo 根目錄【正下方一層】，與 scripts/ 同深度。
   測試檔以 `__file__.parent.parent` 推導 ROOT 去找 data/；放深一層的話，
   迴歸測試會靜默跳過而 pytest 仍報 passed——本專案在那上面出過事。

⚠️ 檔名不可用 `test_*.py` 或 `*_test.py`，執行部分必須包在 main() 裡，
   否則 pytest 會在收集階段把整套變異跑完。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUT = ROOT / "_mut"

SEL = ("test_bounds_formula or test_bounds_guard or test_declarations "
       "or test_personal_data_excluded or test_manifest "
       "or test_source_guards or test_cross_file_guards "
       "or test_party_and_seats or test_shares_and_denominator "
       "or test_2020_special_stations or test_regression "
       "or test_existing_outputs_untouched")

COPIES = ("build_party_list_election.py", "test_build_party_list_election.py",
          "build_local_election.py", "build_legislative_election.py",
          "oracles.py")

# (描述, 檔名, 原字串, 換成)
#
# ⚠️ 每個原字串必須在該檔【恰好出現一次】。不唯一時 str.replace 會改到
#    別處，變異測試本身就壞了——下面有自我檢查。
MUTATIONS: list[tuple[str, str, str, str]] = [
    # ---- 讀檔層 ----
    ("欄數不再逐列檢查（多出的欄位靜默通過）",
     "build_party_list_election.py",
     '    "elbase": 6, "elcand": 16, "elpaty": 2, "elprof": 20,',
     '    "elbase": 6, "elcand": 16, "elpaty": 2, "elprof": 21,'),
    ("列數宣告不再核對（來源換版靜默通過）",
     "build_party_list_election.py",
     "    if check_counts:\n        expected = EXPECTED_ROWS[(year, stem)]",
     "    if False:\n        expected = EXPECTED_ROWS[(year, stem)]"),
    ("引號宣告只驗單向（宣告過期不會響）",
     "build_party_list_election.py",
     "    if declared and not found:",
     "    if False and declared and not found:"),
    ("引號宣告的另一向也不驗（來源新增引號靜默通過）",
     "build_party_list_election.py",
     "    if found and not declared:",
     "    if False and found and not declared:"),
    ("選區欄的允許值不再檢查",
     "build_party_list_election.py",
     "    got = {r[2] for r in rows}\n    want = district_allowed(year, stem)\n"
     "    if got != want:",
     "    got = {r[2] for r in rows}\n    want = district_allowed(year, stem)\n"
     "    if False:"),
    ("2008 的 elprof 選區欄宣告誤寫成與 2012 起相同",
     "build_party_list_election.py",
     '    "2008": {"00"},\n    "2012": {"00", "01"},',
     '    "2008": {"00", "01"},\n    "2012": {"00", "01"},'),
    ("old/ 目錄不再具名排除（2016 會混入舊版重複資料）",
     "build_party_list_election.py",
     "    if EXCLUDED_PATH_SEGMENT in parts:",
     "    if False and EXCLUDED_PATH_SEGMENT in parts:"),
    ("elpaty 也套用檔名後綴（2016 會找不到檔）",
     "build_party_list_election.py",
     'FILES_WITHOUT_SUFFIX = frozenset({"elpaty"})',
     "FILES_WITHOUT_SUFFIX = frozenset()"),

    # ---- 跨檔對帳 ----
    ("配對鍵含選區欄（2008 會有 22,555 個單位對不上）",
     "build_party_list_election.py",
     "    return (row[0], row[1], row[3], row[4], row[5])",
     "    return (row[0], row[1], row[2], row[3], row[4], row[5])"),
    ("政黨票加總不再與有效票對帳",
     "build_party_list_election.py",
     "    bad = [(k, valid[k], summed[k]) for k in valid if valid[k] != summed[k]]",
     "    bad = []"),
    ("elprof 的單位鍵不再驗唯一（重複列會讓加總失去意義）",
     "build_party_list_election.py",
     "        if key in valid:",
     "        if False:"),
    ("elctks 的孤兒單位不再中止",
     "build_party_list_election.py",
     "    orphan = sorted(set(summed) - set(valid))\n    if orphan:",
     "    orphan = sorted(set(summed) - set(valid))\n    if False:"),

    # ---- 政黨與席次 ----
    ("同屆同代號兩名稱不再中止（配對鍵無法識別政黨）",
     "build_party_list_election.py",
     "            if code in table and table[code] != name:",
     "            if False:"),
    ("漂移代號的具名清單不再核對（清單過期靜默通過）",
     "build_party_list_election.py",
     "    if extra or stale:",
     "    if False:"),
    ("漂移代號的數量不再核對",
     "build_party_list_election.py",
     "    if len(drift) != EXPECTED_DRIFT_COUNT:",
     "    if False:"),
    ("政黨鍵改成只用代號（9 個漂移代號會被誤併）",
     "build_party_list_election.py",
     '    return (code, name)',
     '    return (code, code)'),
    ("席次合計不再與 34 核對",
     "build_party_list_election.py",
     "    if seats != AT_LARGE_SEATS:",
     "    if False:"),
    ("得票率合計不再與具名值核對",
     "build_party_list_election.py",
     "        if total != want:",
     "        if False:"),
    ("捨入上界不再檢查（殘差再大也放行）",
     "build_party_list_election.py",
     "        if residual > bound:",
     "        if False:"),
    ("elretks 的統計不再與宣告核對",
     "build_party_list_election.py",
     "    if got != want:\n        raise ValidationError(\n"
     '            f"{year} elretks 的統計為 {got}，宣告為 {want}。"',
     "    if False:\n        raise ValidationError(\n"
     '            f"{year} elretks 的統計為 {got}，宣告為 {want}。"'),
    ("候選人數被當成應選席次",
     "build_party_list_election.py",
     "R_CANDIDATES = 3  # 候選人數（該黨名單長度）——⚠️【不是】應選席次",
     "R_CANDIDATES = 4  # 候選人數（該黨名單長度）——⚠️【不是】應選席次"),

    # ---- 原住民佔比與分母 ----
    ("投開票所加總不再與檔別合計核對（分母可以算錯）",
     "build_party_list_election.py",
     "    if station_sum != file_total:",
     "    if False:"),
    ("原住民選舉人總數不再與宣告核對",
     "build_party_list_election.py",
     "    if file_total != declared:",
     "    if False:"),
    ("可接的三個整數不再核對",
     "build_party_list_election.py",
     "    got = (len(pl_keys), len(indigenous), matched)\n    if got != want:",
     "    got = (len(pl_keys), len(indigenous), matched)\n    if False:"),
    ("缺席一律當成未知（2020 嘉義市的 189 個 p=0 會變成缺口）",
     "build_party_list_election.py",
     "        elif got is None and not reverse_gap_by_county.get((key[0], key[1])):",
     "        elif False:"),
    ("q 改用選舉人數而不是投票數（權重用錯）",
     "build_party_list_election.py",
     '                "q": str(Decimal(ind_v) / Decimal(total_v)),',
     '                "q": str(Decimal(ind_e) / Decimal(total_e)),'),

    # ---- 極限法 ----
    ("極限法的 (1-q) 寫成 (1+q)（界限被放鬆，仍含住觀察值）",
     "build_party_list_election.py",
     "    lower = max(Fraction(0), (y - (1 - q)) / q)",
     "    lower = max(Fraction(0), (y - (1 + q)) / q)"),
    ("極限法的上界不再截斷到 1",
     "build_party_list_election.py",
     "    upper = min(Fraction(1), y / q)",
     "    upper = y / q"),
    ("界限的含住關係不再檢查",
     "build_party_list_election.py",
     "    if not (Fraction(0) <= lower <= y <= upper <= Fraction(1)):",
     "    if False:"),
    ("界限的寬度恆等式不再檢查（放鬆的界限會通過）",
     "build_party_list_election.py",
     "    if width > max_width:",
     "    if False:"),
    ("分層改用 q 篩所而不是 p",
     "build_party_list_election.py",
     '            and Decimal(v["p"]) >= threshold',
     '            and Decimal(v["q"]) >= threshold'),
    ("門檻少一個（涵蓋率與精度的取捨被隱藏）",
     "build_party_list_election.py",
     'THRESHOLDS = (Decimal("0.95"), Decimal("0.90"), Decimal("0.80"))',
     'THRESHOLDS = (Decimal("0.95"), Decimal("0.90"))'),

    # ---- 個資與 manifest ----
    ("個資欄名檢查被拿掉",
     "build_party_list_election.py",
     "                if word in col:",
     "                if False:"),
    ("個資字樣清單漏掉出生地",
     "build_party_list_election.py",
     'FORBIDDEN_COLUMN_WORDS = ("出生日期", "出生地", "學歷", "生日")',
     'FORBIDDEN_COLUMN_WORDS = ("出生日期", "學歷", "生日")'),
    ("manifest 不再與輸出核對",
     "build_party_list_election.py",
     "    if problems:",
     "    if False:"),
    ("manifest 少宣告一欄（q 的 note 是關鍵警語）",
     "oracles.py",
     '        "q": dict(\n            provenance="project",',
     '        "_unused_q": dict(\n            provenance="project",'),
]


# 每個被變異的檔各一個【必定會被抓到】的變異。
# 它若沒被抓到，代表該檔的副本沒有生效——針對它的變異全部無意義，
# 而那會偽裝成「測試涵蓋不足」。
CANARIES: tuple[tuple[str, str, str], ...] = (
    ("build_party_list_election.py",
     "TERMS = tuple(TERM_FOLDERS)", "TERMS = ()"),
    ("oracles.py",
     '    "party_list_seats": {', '    "_canary_gone": {'),
)


def fresh_copies() -> Path:
    """把要用的檔複製到 _mut/，回傳測試檔的路徑。"""
    shutil.rmtree(MUT, ignore_errors=True)
    MUT.mkdir()
    for name in COPIES:
        shutil.copy(ROOT / "scripts" / name, MUT / name)
    return MUT / "test_build_party_list_election.py"


def apply_to_copy(filename: str, old: str, new: str) -> bool:
    """在副本上套用變異。原字串必須恰好出現一次。"""
    path = MUT / filename
    src = path.read_text(encoding="utf-8")
    if src.count(old) != 1:
        return False
    path.write_text(src.replace(old, new), encoding="utf-8")
    return True


def run_pytest(test_path: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_path), "-q", "-k", SEL,
         "--no-header", "-p", "no:randomly"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    rc = 0

    # ⚠️ 變異字串的唯一性自我檢查。不唯一時 replace 會改到別處，
    #    變異測試本身就壞了——而那會偽裝成「變異被偵測到」。
    broken = []
    for i, (desc, filename, old, _new) in enumerate(MUTATIONS, 1):
        src = (ROOT / "scripts" / filename).read_text(encoding="utf-8")
        n = src.count(old)
        if n != 1:
            broken.append(f"{i}. 出現 {n} 次（須恰為 1）：{desc}")
    if broken:
        print("★ 變異字串不唯一，變異測試本身壞了：")
        for b in broken:
            print("   " + b)
        return 1

    # ⚠️ Canary：一個【必定】會被抓到的變異。它若也「漏網」，代表副本
    #    根本沒被載入——變異測試自己壞了，而那會偽裝成「測試全面失效」。
    #
    #    實測發生過：測試檔寫 `sys.path.insert(0, ROOT / "scripts")`，
    #    從 _mut/ 執行時指回真正的 scripts/，36 個變異全部漏網而基準通過。
    #    沒有 canary 的話，那份報告看起來像測試寫壞了，不像工具壞了。
    # ⚠️ **每個被變異的檔各一個 canary。** 只驗一個檔不夠：
    #    實測 build_party_list_election.py 的 canary 通過，但 oracles.py 的
    #    變異全部無效——因為前者的 sys.path 把【真正的】scripts/ 插到最前面，
    #    它之後 import 的 oracles 就載入原版了。單一 canary 看不出這件事。
    for filename, old, new in CANARIES:
        test_path = fresh_copies()
        if not apply_to_copy(filename, old, new):
            print(f"★ {filename} 的 canary 字串不唯一，變異測試本身壞了")
            shutil.rmtree(MUT, ignore_errors=True)
            return 1
        crc, cout = run_pytest(test_path)
        if crc == 0:
            print(f"★ CANARY（{filename}）沒被偵測到——該檔的副本沒有生效，"
                  f"針對它的變異全部無意義。")
            print("   檢查 sys.path：測試檔與【被測模組】都必須用 "
                  "Path(__file__).parent，不是 ROOT/'scripts'——"
                  "後者會把真正的 scripts/ 插到最前面。")
            print(cout[-1200:])
            shutil.rmtree(MUT, ignore_errors=True)
            return 1
        print(f"canary（{filename}）→ 必定會被抓到的變異確實被抓到 ✓")

    test_path = fresh_copies()
    base_rc, base_out = run_pytest(test_path)
    skipped = "SKIP" in base_out or "skipped" in base_out
    print(f"基準對照 → 未變異的副本"
          f"{'通過' if base_rc == 0 else '★失敗'}"
          f"{'，且無測試被跳過 ✓' if not skipped else '，★但有測試被跳過'}")
    if base_rc != 0 or skipped:
        print(base_out[-2000:])
        shutil.rmtree(MUT, ignore_errors=True)
        return 1

    for i, (desc, filename, old, new) in enumerate(MUTATIONS, 1):
        test_path = fresh_copies()
        if not apply_to_copy(filename, old, new):
            print(f"{i}. ★ 副本上套用失敗：{desc}")
            rc = 1
            continue
        mrc, mout = run_pytest(test_path)
        caught = mrc != 0 and "INTERNALERROR" not in mout
        print(f"{i}. {'偵測到 ✓' if caught else '★ 沒被偵測到'} — {desc}")
        if not caught:
            rc = 1
            print("      " + mout.strip()[-300:].replace("\n", " | "))

    shutil.rmtree(MUT, ignore_errors=True)
    print()
    print("變異測試全部被偵測到" if rc == 0 else "★ 有漏網的變異")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
