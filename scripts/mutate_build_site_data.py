#!/usr/bin/env python3
"""build_site_data.py 與其測試的變異測試。

**驗證通過不代表驗證有效。** 每一項變異都必須讓 pytest 非零退出；
還原後必須回到通過。有一項漏網就是那條檢查沒有辨識力。

用法：
    python scripts/mutate_build_site_data.py

⚠️ 檔名不可用 `*_test.py` 或 `test_*.py` 結尾，執行的部分也必須包在 `main()` 裡，
   否則 pytest 會把它當測試檔收集並在收集階段執行整套變異。
   姊妹檔 `mutate_build_local_election.py` 原名 `mutation_test.py`，
   實測就是這樣被跑了 52 秒後以 INTERNALERROR 收場。

⚠️ 兩件事是踩過坑才這樣寫的：

1. **在 pytest 下驗，不是直接執行測試檔。** 這個專案出過「直接執行 exit 1、
   pytest 卻報 passed」的事（見測試檔 @reports 的註解）。變異測試若只用直接
   執行來驗，那個坑會原封不動地回來。

2. **變異做在副本上，副本放在 repo 根目錄【正下方一層】（`_mut/`）。**
   測試檔以 `__file__.parent.parent` 推導 ROOT 去找 `docs/` 與 `data/`。
   深度錯了不會報錯，只會讓需要那些檔案的測試**靜默跳過而 pytest 仍報 passed**——
   於是變異看起來「被偵測到」或「測試通過」，其實那些斷言根本沒跑。
   放到系統暫存目錄會整組失效；放在 `scratch/mut/`（兩層）也一樣，
   姊妹檔 `mutate_build_local_election.py` 就曾因此讓迴歸測試全程未執行。

⚠️ 例外：`docs/index.html` 的變異**只能改真檔**。測試是用 node 執行 HTML 裡
   那兩行來驗前端過濾，而它讀的是 `ROOT/docs/index.html`；改副本測不到。
   那一項因此有額外的防護，見 mutate_index_html()。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUT = ROOT / "_mut"
HTML = ROOT / "docs" / "index.html"
COPIED = ("build_site_data.py", "test_build_site_data.py")

# (說明, 檔名, 原字串, 變異字串)
MUTATIONS = [
    # ---- 席次取自權威值 ----
    ("index：當選與否改用來源註記 `當選註記 == '*'`",
     'won = [c for c in rows if c["elected_authoritative"] == "true"]',
     'won = [c for c in rows if c["當選註記"] == "*"]'),
    ("index：選舉區內的席次改用來源註記（同額競選會算錯）",
     '                if c["elected_authoritative"] == "true":\n'
     '                    d["seats"] += 1',
     '                if c["當選註記"] == "*":\n'
     '                    d["seats"] += 1'),
    ("index：政黨當選數改用來源註記",
     '                if c["elected_authoritative"] == "true":\n'
     '                    party[b][0] += 1',
     '                if c["當選註記"] == "*":\n'
     '                    party[b][0] += 1'),
    ("roster：名錄標記整個改用來源註記",
     '    mark = row["當選註記"]\n'
     '    if mark in ("!", "-"):\n'
     '        return mark\n'
     '    return "*" if row["elected_authoritative"] == "true" else ""',
     '    return row["當選註記"]'),
    ("roster：`!` 不再原樣保留（婦女保障當選被寫成一般當選）",
     '    if mark in ("!", "-"):',
     '    if mark in ("-",):'),

    # ---- 分桶鍵 ----
    #
    # ⚠️ 下面三項裡，只有第一項在真實資料上會失敗。實測：對照表內的五個代號
    #    各自只對到一個名稱，全資料五組「同代號多名稱」全部落在表外。
    #    所以「只用代號」與「代號回退」在現有資料上的輸出與正確實作**完全相同**。
    #    它們之所以會被偵測到，靠的是 test_party_bucket_key_semantics 的合成斷言。
    #    把那個測試刪掉，這兩項就會變成漏網——這正是它存在的理由。
    ("分桶鍵改成只用名稱（舊屆的代號 99／無 會掉回其他）",
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    return {n: b for (c, n), b in PARTY_IDENTITY_BUCKETS.items()}.get(\n'
     '        row["政黨名稱"], OTHER_BUCKET)'),
    ("分桶鍵改成只用代號（真實資料看不出差別）",
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    return {c: b for (c, n), b in PARTY_IDENTITY_BUCKETS.items()}.get(\n'
     '        row["政黨代號"], OTHER_BUCKET)'),
    ("配對查不到時以代號回退（等同同代號自動合併）",
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    hit = PARTY_IDENTITY_BUCKETS.get((row["政黨代號"], row["政黨名稱"]))\n'
     '    if hit is not None:\n'
     '        return hit\n'
     '    for (c, n), b in PARTY_IDENTITY_BUCKETS.items():\n'
     '        if c == row["政黨代號"]:\n'
     '            return b\n'
     '    return OTHER_BUCKET'),
    ("分桶鍵改成鬆散的「代號在表內 and 名稱在表內」",
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    codes = {c for c, n in PARTY_IDENTITY_BUCKETS}\n'
     '    for (c, n), b in PARTY_IDENTITY_BUCKETS.items():\n'
     '        if row["政黨代號"] in codes and row["政黨名稱"] == n:\n'
     '            return b\n'
     '    return OTHER_BUCKET'),
    ("無黨籍改用子字串比對（會吸收無黨團結聯盟）",
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)',
     '    if "無" in row["政黨名稱"]:\n'
     '        return "無黨籍及未經政黨推薦"\n'
     '    return PARTY_IDENTITY_BUCKETS.get(\n'
     '        (row["政黨代號"], row["政黨名稱"]), OTHER_BUCKET)'),
    ("把舊屆無黨籍那一筆從對照表移除（本次修正的本體）",
     '    ("99", "無"): "無黨籍及未經政黨推薦",\n',
     ''),

    # ---- 主序列旗標 ----
    ("旗標寫死為 true（前端會把自訂選舉種類畫進跨屆折線）",
     '        ms = r["is_main_sequence"] == "true"',
     '        ms = True'),
    ("旗標寫死為 false",
     '        ms = r["is_main_sequence"] == "true"',
     '        ms = False'),
    ("旗標不一致時不再中止，改為沿用先出現的值",
     '            if out[code]["mainSequence"] != ms:\n'
     '                raise SiteDataError(',
     '            if False:\n'
     '                raise SiteDataError('),

    # ---- 四捨五入 ----
    ("投票率改用 Python round()（銀行家捨入）",
     '            turnout = (float(_round_half_up(\n'
     '                Decimal(100 * tot["votes"]) / Decimal(tot["electors"]), "0.01"))\n'
     '                if tot["electors"] else None)',
     '            turnout = (round(100 * tot["votes"] / tot["electors"], 2)\n'
     '                if tot["electors"] else None)'),
    ("四捨五入方向改為一律進位",
     '    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)',
     '    return value.quantize(Decimal(places), rounding=ROUND_CEILING)'),
    ("四捨五入方向改為一律捨去",
     '    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)',
     '    return value.quantize(Decimal(places), rounding=ROUND_FLOOR)'),

    # ---- 邊界防護 ----
    ("零當選時不再回傳 None，直接相除",
     '            per_seat = (int(_round_half_up(\n'
     '                Decimal(tot["electors"]) / Decimal(len(won)), "1"))\n'
     '                if won else None)',
     '            per_seat = int(_round_half_up(\n'
     '                Decimal(tot["electors"]) / Decimal(len(won)), "1"))'),
    ("選舉人數為零時不再回傳 None",
     '                Decimal(100 * tot["votes"]) / Decimal(tot["electors"]), "0.01"))\n'
     '                if tot["electors"] else None)',
     '                Decimal(100 * tot["votes"]) / Decimal(tot["electors"]), "0.01")))'),

    # ---- 輸入欄位契約（兩個方向）----
    ("契約：把實際會讀的 `鄉鎮市區` 從 candidates 清單移除",
     '        "省市", "縣市", "選舉區", "鄉鎮市區", "行政區名稱",\n'
     '        "號次", "姓名", "政黨代號", "政黨名稱", "性別", "年齡", "現任",',
     '        "省市", "縣市", "選舉區", "行政區名稱",\n'
     '        "號次", "姓名", "政黨代號", "政黨名稱", "性別", "年齡", "現任",'),
    ("契約：把實際會讀的 `政黨代號` 從 candidates 清單移除",
     '        "號次", "姓名", "政黨代號", "政黨名稱", "性別", "年齡", "現任",',
     '        "號次", "姓名", "政黨名稱", "性別", "年齡", "現任",'),
    ("契約：把不讀的 `候選人數`／`當選人數` 加回 summary 清單",
     '        "選舉人數", "投票數",\n'
     '        "admin_code_system", "is_main_sequence",',
     '        "選舉人數", "投票數", "候選人數", "當選人數",\n'
     '        "admin_code_system", "is_main_sequence",'),
    ("契約：拿掉缺欄檢查本身",
     '        if missing:',
     '        if False:'),
]

# 只能改真檔的那一項。見模組 docstring。
HTML_MUTATION = ("前端：MAIN 不再過濾（Python 端全綠、站台卻畫錯）",
                 'const MAIN = DATA.types.filter(t => t.mainSequence);',
                 'const MAIN = DATA.types;')

# @reports 是否承重，不能用一般變異的方式驗——單獨拿掉它時程式是好的，
# 測試本來就會通過，會被誤判成「漏網」。要驗的是：
#   壞掉的程式 + 有 @reports → pytest 失敗（由上面的變異清單涵蓋）
#   壞掉的程式 + 無 @reports → pytest 通過  ← 證明少了它失敗就看不見
REPORTS_ASSERT = '        assert not new, f"{fn.__name__} 有 {len(new)} 項失敗：{new}"'
BREAK_CODE = ('        ms = r["is_main_sequence"] == "true"', '        ms = True')


def run_pytest(test_path: Path) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_path), "-q", "--no-header"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, r.stdout + r.stderr


def fresh_copies() -> Path:
    """把原始碼與測試檔複製到 scratch/mut/，回傳測試檔路徑。"""
    if MUT.exists():
        shutil.rmtree(MUT)
    MUT.mkdir(parents=True)
    for f in COPIED:
        shutil.copy(ROOT / "scripts" / f, MUT / f)
    return MUT / "test_build_site_data.py"


def apply_to_copy(fname: str, old: str, new: str) -> bool:
    target = MUT / fname
    src = target.read_text(encoding="utf-8")
    if src.count(old) != 1:
        return False
    mutated = src.replace(old, new, 1)
    if "ROUND_CEILING" in new or "ROUND_FLOOR" in new:
        mutated = mutated.replace(
            "from decimal import Decimal, ROUND_HALF_UP",
            "from decimal import (Decimal, ROUND_CEILING, "
            "ROUND_FLOOR, ROUND_HALF_UP)")
    target.write_text(mutated, encoding="utf-8")
    return True


def git_is_clean(path: Path) -> bool:
    r = subprocess.run(["git", "status", "--porcelain", "--", str(path)],
                       capture_output=True, text=True, cwd=ROOT)
    return r.returncode == 0 and not r.stdout.strip()


def mutate_index_html() -> tuple[bool, str]:
    """唯一必須改真檔的變異。回傳（是否偵測到, 說明）。

    ⚠️ 還原用 `git checkout --` 而不是把備份寫回去：若這支腳本在改完之後、
       寫回之前被中斷，記憶體裡的備份就沒了，而 git 的版本還在。
       前提是執行前該檔必須乾淨，否則會連使用者未提交的改動一起還原掉——
       所以不乾淨就直接拒絕執行，不做「應該沒差」的判斷。
    """
    desc, old, new = HTML_MUTATION
    if not git_is_clean(HTML):
        return False, (f"★ 跳過「{desc}」：docs/index.html 有未提交的改動。"
                       "這項變異需要改真檔並以 git 還原，會連你的改動一起還原掉。"
                       "請先提交或暫存後再跑。")
    src = HTML.read_text(encoding="utf-8")
    if src.count(old) != 1:
        return False, f"★ 變異字串在 index.html 出現 {src.count(old)} 次（需恰好 1 次）"
    test_path = fresh_copies()
    try:
        HTML.write_text(src.replace(old, new, 1), encoding="utf-8")
        rc, out = run_pytest(test_path)
        caught = rc != 0 and "INTERNALERROR" not in out
    finally:
        subprocess.run(["git", "checkout", "--", str(HTML)], cwd=ROOT,
                       capture_output=True)
    return caught, f"  {desc} → {'偵測到 ✓' if caught else '★沒被偵測到'}"


def main() -> int:
    rc = 0

    test_path = fresh_copies()
    base_rc, base_out = run_pytest(test_path)
    print(f"未變異的副本 → {'通過 ✓' if base_rc == 0 else '★失敗'}")
    if base_rc != 0:
        print(base_out[-1500:])
        shutil.rmtree(MUT, ignore_errors=True)
        return 1

    for desc, old, new in MUTATIONS:
        test_path = fresh_copies()
        if not apply_to_copy("build_site_data.py", old, new):
            print(f"  ★ 變異字串未恰好出現一次，變異測試本身壞了：{desc}")
            rc = 1
            continue
        mrc, mout = run_pytest(test_path)
        caught = mrc != 0 and "INTERNALERROR" not in mout
        print(f"  {desc} → {'偵測到 ✓' if caught else '★沒被偵測到'}")
        if not caught:
            rc = 1
            print("      ", mout.strip()[-300:].replace("\n", " | "))

    # ⚠️ 「因前置條件未驗證」與「驗證後漏網」是兩件不同的事，分開計數。
    #    但兩者都不算通過——把未驗證的項目算成通過，就是「靜默縮減涵蓋範圍」。
    skipped_msgs: list[str] = []
    caught, msg = mutate_index_html()
    print(msg)
    if not caught:
        if msg.lstrip().startswith("★ 跳過"):
            skipped_msgs.append(msg.strip())
        else:
            rc = 1

    # ---- @reports 承重驗證 ----
    print("\n[骨架] 驗證 @reports 是承重的，不是裝飾")
    test_path = fresh_copies()
    apply_to_copy("build_site_data.py", *BREAK_CODE)
    with_rc, _ = run_pytest(test_path)
    tf = MUT / "test_build_site_data.py"
    tf.write_text(tf.read_text(encoding="utf-8")
                  .replace(REPORTS_ASSERT, "        pass", 1), encoding="utf-8")
    without_rc, _ = run_pytest(test_path)
    print(f"  壞掉的程式 + 有 @reports → pytest rc={with_rc}"
          f"（應非零）{'✓' if with_rc != 0 else ' ★'}")
    print(f"  壞掉的程式 + 無 @reports → pytest rc={without_rc}"
          f"（應為零，證明少了它失敗就看不見）{'✓' if without_rc == 0 else ' ★'}")
    if not (with_rc != 0 and without_rc == 0):
        rc = 1

    shutil.rmtree(MUT, ignore_errors=True)

    # 真檔必須完好如初：副本法動不到它，但 index.html 那一項改過真檔
    final_rc, final_out = run_pytest(ROOT / "scripts" / "test_build_site_data.py")
    print(f"\n真正的 scripts/ 與 docs/ → {'通過 ✓' if final_rc == 0 else '★失敗（還原不完全）'}")
    if final_rc != 0:
        print(final_out[-1500:])
        rc = 1

    print()
    if rc:
        print("★ 有變異漏網——那些檢查沒有辨識力，必須補斷言")
    elif skipped_msgs:
        print(f"★ 全部已驗證的變異都被偵測到，但有 {len(skipped_msgs)} 項"
              f"因前置條件【未驗證】：")
        for m in skipped_msgs:
            print("   ", m)
        print("    未驗證不等於通過。處理前置條件後請重跑。")
    else:
        print("全部通過")
    # 未驗證的項目一樣不算通過——把它算成通過就是靜默縮減涵蓋範圍。
    return rc or (1 if skipped_msgs else 0)


if __name__ == "__main__":
    raise SystemExit(main())
