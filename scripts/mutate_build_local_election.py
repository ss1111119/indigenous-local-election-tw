"""變異測試：把 build_local_election.py 與 oracles.py 的驗證逐一改壞，
確認 test_build_local_election.py 會失敗（而不是照樣通過）。

用法：python scripts/mutate_build_local_election.py

每個變異都在 scratch/mut/ 的獨立副本上做，**不動真正的 scripts/**。

⚠️ 副本必須放在 repo 內一層深的資料夾。測試檔以 `__file__.parent.parent`
   推導 ROOT 去找 `data/`；副本放到系統暫存目錄的話，非零退出會是
   「找不到檔案」而不是「抓到變異」——那樣會得出假通過。

⚠️ 檔名不可用 `*_test.py` 或 `test_*.py` 結尾，執行的部分也必須包在 `main()` 裡。
   本檔原名 `mutation_test.py` 且變異迴圈寫在模組層級——放進 `scripts/` 後
   pytest 會依預設的 `*_test.py` 樣式收集它，**在收集階段就把整套變異跑完**
   （實測 52 秒），最後以 `INTERNALERROR: SystemExit` 收場。
"""
import shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# ⚠️ 必須是 repo 根目錄【正下方一層】，與 scripts/ 同深度。
#    測試檔以 __file__.parent.parent 推導 ROOT。原本放在 scratch/mut/（兩層），
#    ROOT 會解析成 scratch/，於是 data/processed 與原始壓縮檔都找不到，
#    **迴歸／舊屆／自訂種類三項測試全部靜默跳過而 pytest 仍報 passed**。
#    那段期間「48 個變異全部被偵測到」完全是靠單元測試達成的。
MUT = ROOT / "_mut"
SEL = ("test_custom_election_types or test_comparability_flags "
       "or test_oracles or test_read_csv or test_population or test_process_one "
       "or test_elected or test_county_crosswalk or test_legacy_terms "
       "or test_custom_type_terms or test_regression or test_valid_age "
       "or test_age_valid_column_in_output "
       "or test_unguarded_source_checks")

MUTATIONS = [
    # ⚠️ 字串必須唯一。`"T-COMBO": "直轄市議員` 在 oracles.py 出現兩次
    #    （CUSTOM_ELECTION_TYPES 與 _FIXED_OFFICE），故帶上完整名稱。
    ("自訂代碼去掉連字號（變成兩字元、與官方代碼無法分辨）",
     "oracles.py",
     '"T-COMBO": "直轄市議員(原住民，未分平地／山地)選舉",',
     '"TC": "直轄市議員(原住民，未分平地／山地)選舉",'),
    ("主序列改成一律 true（1994 與合併類別會混進折線）",
     "oracles.py", "return etype not in CUSTOM_ELECTION_TYPES", "return True"),
    ("1998 與 2002 標成同一套代碼系統",
     "oracles.py", '"2002": "2002",', '"2002": "1998",'),
    ("FILE_SCOPE 刪掉 prv（直轄市腿會判成縣市）",
     "oracles.py", '"prv": "直轄市",', '"prv": "縣市",'),
    ("拿掉一個可比性標記欄位（is_main_sequence 不宣告 oracle）",
     "oracles.py", '    "is_main_sequence": dict(', '    "_unused_is_main_sequence": dict('),
    ("KEY_COLS 拿掉 elprof 的投開票所欄（層級判定會全判成投開票所）",
     "build_local_election.py", '"elprof": (0, 1, 2, 3, 4, 5),', '"elprof": (0, 1, 2, 3, 4),'),
    ("KEY_COLS 拿掉 elctks 的號次欄（2005 跨檔對照會全數落空）",
     "build_local_election.py", '"elctks": (0, 1, 2, 3, 4, 5, 6),', '"elctks": (0, 1, 2, 3, 4, 5),'),
    ("read_csv 改成全面 strip（非關聯鍵的來源值被一起改掉）",
     "build_local_election.py",
     "row = [c.strip() if i in keys else c for i, c in enumerate(row)]",
     "row = [c.strip() for c in row]"),
    ("把得票率欄列進白名單（原樣保留的紀律被破壞）",
     "build_local_election.py", '"elctks": (0, 1, 2, 3, 4, 5, 6),', '"elctks": (0, 1, 2, 3, 4, 5, 6, 8),'),
    ("keys 參數被忽略（正規化整組失效）",
     "build_local_election.py", "        if keys:", "        if False:"),
    ("人口數改回 int() 轉型（舊屆小數會拋例外）",
     "build_local_election.py",
     'n = {i: int(r[i]) for i in range(6, 17) if i != 10}',
     'n = {i: int(r[i]) for i in range(6, 17)}'),
    ("選舉區被放寬成適用層級",
     "oracles.py", 'POPULATION_APPLICABLE_LEVELS = ("檔別合計", "直轄市縣市")',
     'POPULATION_APPLICABLE_LEVELS = ("檔別合計", "直轄市縣市", "選舉區")'),
    ("標記改用「可用」（會被讀成數值已驗證）",
     "oracles.py", 'POPULATION_APPLICABLE = "縣市以上"',
     'POPULATION_APPLICABLE = "縣市以上_可用"'),
    ("人口數適用層級欄不宣告 oracle",
     "oracles.py", '    "人口數適用層級": dict(', '    "_unused_pop_level": dict('),
    ("權威值直接抄 elcand（2005 損壞就抄壞的）",
     "build_local_election.py",
     'out[key] = (marks.pop() in ELECTED_MARKS, f"elctks_{ADMIN_LEVELS[top]}")',
     'out[key] = (c[14] in ELECTED_MARKS, f"elctks_{ADMIN_LEVELS[top]}")'),
    ("推導鍵改成必須整組相等（屏東 16 區會對不上）",
     "build_local_election.py",
     'if all(is_blank(c[i]) or c[i] == r[i] for i in cols)',
     'if all(c[i] == r[i] for i in cols)'),
    ("推導鍵不約束鄉鎮市區欄（D2／R3 不同區會被併成一個）",
     "build_local_election.py",
     'cols = [0, 1, 3, 4] if ignore_district else [0, 1, 2, 3, 4]',
     'cols = [0, 1, 2] if True else [0, 1, 2, 3, 4]'),
    ("取任一層級而非最高層級（2002 平原鄉鎮市區註記全空）",
     "build_local_election.py",
     'top = min(ADMIN_LEVELS.index(admin_level(r)) for r in hits)',
     'top = max(ADMIN_LEVELS.index(admin_level(r)) for r in hits)'),
    ("同層級註記矛盾時取「任一為星號」而不中止",
     "build_local_election.py",
     "        if len(marks) > 1:",
     "        if False:"),
    ("elctks 無列時靜默回傳未當選而不中止",
     "build_local_election.py",
     "        if not hits:",
     '        if not hits and False:'),
    ("identity 改成無條件退回（未知縣市代碼會靜默通過）",
     "build_local_election.py",
     "    reg_name = regional.get(code)\n    if reg_name is not None and reg_name == local_name:\n        return county",
     "    return county\n    reg_name = regional.get(code)\n    if reg_name is not None and reg_name == local_name:\n        return county"),
    ("第1段不驗三方名稱一致",
     "build_local_election.py",
     "        if not (local_name == cw_name == reg_name):",
     "        if False:"),
    ("identity 只比代碼不比名稱",
     "build_local_election.py",
     "    if reg_name is not None and reg_name == local_name:",
     "    if reg_name is not None:"),
    # ⚠️ 這一項守的不是資料，是「輸入不要放在輸出目錄」。改回去之後建置
    #    照樣成功、輸出逐位元相同——只有明寫的位置檢查會失敗。
    ("對照表搬回輸出目錄（清空輸出再重跑就會把輸入刪掉）",
     "build_local_election.py",
     'COUNTY_CROSSWALK_PATH = (\n'
     '    ROOT / "data" / "reference" / "cec-county-code-crosswalk-1998-2002.csv"\n'
     ')',
     'COUNTY_CROSSWALK_PATH = OUT_DIR / "cec-county-code-crosswalk-1998-2002.csv"'),
    ("對照表的鍵不含選舉種類（T2 的列會被 T3 用到）",
     "build_local_election.py",
     '    key = (year, etype, code)',
     '    key = (year, etype, code) if False else (year, "T2", code)'),
    # ⚠️ 這一行在 summary／candidates／votes 三處列組裝各出現一次，
    #    故帶上後一行以指定 summary 那一處。
    ("鄉鎮市區_正規化 直接放原始碼（偽裝成標準鍵的毒藥）",
     "build_local_election.py",
     '"鄉鎮市區_正規化": "" if town_local else r[3],\n'
     '            "有效票": valid,',
     '"鄉鎮市區_正規化": r[3],\n'
     '            "有效票": valid,'),
    ("TOWN_CODES_FILE_LOCAL 漏掉 2005（2005 縣市碼全域但鄉鎮市區碼仍重編）",
     "build_local_election.py",
     '    ("2005", "T2"), ("2005", "T3"),\n}',
     '}'),
    ("2005 的具名當選註記異常清單少一筆（記錄過期）",
     "build_local_election.py",
     '        ("01", "015", "10", "000", "0000", "2"),   # 呂必賢 漏標',
     ''),
    ("2005 的具名清單多一筆（不符集合不吻合）",
     "build_local_election.py",
     '        ("01", "002", "11", "000", "0000", "2"),   # 簡海樹 漏標',
     '        ("01", "002", "11", "000", "0000", "1"),   # 捏造的一筆\n'
     '        ("01", "002", "11", "000", "0000", "2"),   # 簡海樹 漏標'),
    ("彙總層級投票率異常改成任何層級都放行",
     "build_local_election.py",
     'TURNOUT_AGGREGATE_LEVELS = ("檔別合計", "直轄市縣市")',
     'TURNOUT_AGGREGATE_LEVELS = ADMIN_LEVELS'),
    ("投票數>選舉人數 的具名檢查被拿掉",
     "build_local_election.py",
     "                if area_key(s) not in allow_e:",
     "                if False:"),
    ("鄉鎮市區配錯選舉區：不驗多重集合相同",
     "build_local_election.py",
     "            if p_multi != c_multi:",
     "            if False:"),
    ("鄉鎮市區配錯選舉區：具名清單多一個沒問題的選舉區",
     "build_local_election.py",
     '            ("01", "010", "07"),   # 嘉義縣 第07選舉區（18 個鄉鎮市區）',
     '            ("01", "011", "07"),   # 捏造的一個\n'
     '            ("01", "010", "07"),   # 嘉義縣 第07選舉區（18 個鄉鎮市區）'),
    ("寶山鄉的上層級補償檢查被拿掉",
     "build_local_election.py",
     '                    if up["選舉人數"] and up["投票數"] > up["選舉人數"]:',
     "                    if False:"),
    ("鄉鎮市區代碼集合差異的檢查被拿掉",
     "build_local_election.py",
     "                if unexplained:",
     "                if False:"),
    ("1998 平原的跨選舉區移動不具名（多一個鄉鎮市區被靜默放行）",
     "build_local_election.py",
     '        "moved_towns": {("009", ("01", "009", "07"), ("01", "009", "06"))},',
     '        "moved_towns": set(),'),
    ("自訂代碼被當成官方代碼（1994 與合併類別會進主序列）",
     "oracles.py",
     '    "T-COMBO": "直轄市議員(原住民，未分平地／山地)選舉",',
     ""),
    # ⚠️ 這三個鍵在 KNOWN_* 與 DISTRICT_COLUMN_INCONSISTENT 兩張表都出現，
    #    且 elctks 的 {"01"} 在四個直轄市檔各出現一次。全部帶上後一行以指定。
    ("選舉區欄不一致的宣告漏掉 1994 平原2",
     "build_local_election.py",
     '    ("1994", "T-PRV2", "平原2"): {\n'
     '        "elbase": {"00"}, "elcand": {"02"},',
     '    ("1994", "T-PRV2", "_never"): {\n'
     '        "elbase": {"00"}, "elcand": {"02"},'),
    ("選舉區欄不一致的宣告漏掉 2006 直轄市",
     "build_local_election.py",
     '    ("2006", "T-COMBO", "直轄市"): {\n'
     '        "elbase": {"00"}, "elcand": {"00"},',
     '    ("2006", "T-COMBO", "_never"): {\n'
     '        "elbase": {"00"}, "elcand": {"00"},'),
    ("選舉區欄的允許值宣告錯（1994 直轄市的 elctks 01 改宣告成 00）",
     "build_local_election.py",
     '    ("1994", "T-COMBO", "直轄市"): {\n'
     '        "elbase": {"00"}, "elcand": {"00"}, "elprof": {"00"}, "elctks": {"01"},',
     '    ("1994", "T-COMBO", "直轄市"): {\n'
     '        "elbase": {"00"}, "elcand": {"00"}, "elprof": {"00"}, "elctks": {"00"},'),
    ("選舉區欄的允許值檢查被拿掉",
     "build_local_election.py",
     "            if got != allowed_dist[kind]:",
     "            if False:"),
    ("孤兒層級的向上加總檢查被拿掉",
     "build_local_election.py",
     "                if got_sum != up[\"有效票\"]:",
     "                if False:"),
    # ⚠️ `if up is None:` 出現兩次：一次在寶山鄉補償檢查裡（後接 continue）、
    #    一次在孤兒單位這裡（後接 raise）。原本的字串一直改到前者，
    #    也就是這個變異從來沒測過它描述的東西。帶上後一行以指定。
    ("孤兒單位的父單位不存在時不中止",
     "build_local_election.py",
     "                if up is None:\n"
     "                    raise ValidationError(",
     "                if False:\n"
     "                    raise ValidationError("),
    ("驗證7 的鍵不套用選舉區正規化（四個直轄市檔等於什麼都沒驗）",
     "build_local_election.py",
     "            if drop_district:\n                k = (k[0], k[1], \"00\") + tuple(k[3:])\n            return (*k, row[\"號次\"])",
     "            return (*k, row[\"號次\"])"),
    ("忽略選舉區欄時不驗候選人身分唯一",
     "build_local_election.py",
     "        if len(set(ids)) != len(ids):",
     "        if False:"),
    ("elctks 比 elprof 細：不驗層級是否真的更深",
     "build_local_election.py",
     "            if too_shallow:",
     "            if False:"),
    ("crosswalk 誤套用到直轄市檔（拿縣市議員區域檔查直轄市代碼）",
     "build_local_election.py",
     'COUNTY_CROSSWALK_TYPES = {"T2", "T3"}',
     'COUNTY_CROSSWALK_TYPES = {"T2", "T3", "T-COMBO"}'),
    ("1994 高雄市的當選註記異常不具名",
     "build_local_election.py",
     '        ("02", "000", "00", "000", "0000", "1"),   # 高玉生 481票 漏標',
     ""),
    ("議員種類遇單一檔時靜默回傳預設值而不中止",
     "oracles.py",
     '        raise OracleError(\n            f"檔別 {label!r} 為全國單一檔',
     '        return "縣市議員"  # noqa\n    if False:\n        raise OracleError(\n            f"檔別 {label!r} 為全國單一檔'),

    # ---- 當選註記的補償檢查 ----
    #
    # ⚠️ 這兩項的辨識力都來自真實資料裡的那 63 筆具名異常，不需要合成資料。
    ("補償檢查改回比對兩個權威值（兩側同源後恆不成立，一筆都收不到）",
     "build_local_election.py",
     '            source_says_elected = c["當選註記"] in ELECTED_MARKS\n'
     '            if (c["當選"] == "Y") != source_says_elected:',
     '            if (c["當選"] == "Y") != (c["當選"] == "Y"):'),
    # 第 4 項的當選人數那一半會恆等於 elprof，永不觸發、也不會報錯。
    ("驗證4 的 n_win 改數權威值（elcand 損壞從此偵測不到，且無錯誤訊息）",
     "build_local_election.py",
     '        n_win = sum(1 for c in p["candidates"]\n'
     '                    if c["當選註記"] in ELECTED_MARKS)',
     '        n_win = sum(1 for c in p["candidates"] if c["當選"] == "Y")'),
    # 報告會保有 63 筆、長度檢查照樣通過，但兩欄變成恆等、資訊歸零。
    ("異常紀錄的兩側改讀同一欄（報告仍有 63 筆但不再含資訊）",
     "build_local_election.py",
     '                        "由註記推導": "Y" if source_says_elected else "N",',
     '                        "由註記推導": c["當選"],'),
    # 恆真同義反覆的偵測器：白名單清空後建置必須中止。
    # 若仍通過，代表那個檢查早已失去對真實異常的辨識力。
    ("當選註記異常的具名白名單被清空（那 63 筆應立刻變成中止）",
     "build_local_election.py",
     "KNOWN_ELECTED_MARK_ANOMALIES: dict[tuple, set] = {",
     "KNOWN_ELECTED_MARK_ANOMALIES: dict[tuple, set] = {}\n"
     "_UNUSED_ANOMALIES: dict[tuple, set] = {"),

    # ---- 年齡的未記載哨兵（判準由站台端搬到這裡）----
    #
    # ⚠️ 這些變異的辨識力來自 test_build_local_election.py 的合成斷言，
    #    不是真實資料。真實資料正好滿足前提（五個舊屆整批 99、
    #    新四屆從未出現 99、0 出現 0 次），所以兩條中止永遠不會觸發。
    ("哨兵清單清空（舊屆的 99 會被當成年齡放進乾淨的 年齡 欄）",
     "build_local_election.py",
     'AGE_UNRECORDED_TERMS = frozenset({"1994", "1998", "2002", "2005", "2006"})',
     'AGE_UNRECORDED_TERMS = frozenset()'),
    ("判準改成無條件「99 一律當未記載」（新屆真有 99 歲時會被吃掉）",
     "build_local_election.py",
     '    if raw == AGE_UNRECORDED_VALUE and year in AGE_UNRECORDED_TERMS:',
     '    if raw == AGE_UNRECORDED_VALUE:'),
    ("0 與空白不再視為無資料（會出現「0 歲」的候選人）",
     "build_local_election.py",
     'AGE_ALWAYS_NO_DATA = frozenset({"0", ""})',
     'AGE_ALWAYS_NO_DATA = frozenset()'),
    ("空白不再視為無資料（來源出現空白時會誤中止）",
     "build_local_election.py",
     'AGE_ALWAYS_NO_DATA = frozenset({"0", ""})',
     'AGE_ALWAYS_NO_DATA = frozenset({"0"})'),
    ("年齡 直接抄 r[10]（哨兵值原封不動流進乾淨欄位）",
     "build_local_election.py",
     '            "年齡": valid_age(year, r[10]),',
     '            "年齡": r[10],'),
    ("拿掉「列入的屆別必須整批是無資料值」那條斷言",
     "build_local_election.py",
     '            extra = ages - AGE_NO_DATA_VALUES\n            if extra:',
     '            extra = ages - AGE_NO_DATA_VALUES\n            if False:'),
    ("拿掉「清單外不得出現哨兵值」那條斷言",
     "build_local_election.py",
     '        elif AGE_UNRECORDED_VALUE in ages:',
     '        elif False:'),
]

def prepare() -> None:
    """建立一份乾淨的副本。"""
    if MUT.exists():
        shutil.rmtree(MUT)
    MUT.mkdir(parents=True)
    for f in ("oracles.py", "build_local_election.py",
              "test_build_local_election.py"):
        shutil.copy(ROOT / "scripts" / f, MUT / f)


def run(extra: list[str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest",
         str(MUT / "test_build_local_election.py"), "-q", "-k", SEL,
         *(extra or [])],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT,
    )


def baseline() -> int:
    """⚠️ 基準對照：未變異的副本必須通過，而且該跑的測試必須真的跑到。

    少了這一關，只要副本環境有問題（例如放錯深度導致找不到 data/），
    48 個變異會【全部失敗】而被報成「全部被偵測到」——證明不了任何事。
    這個專案已經在「副本放錯深度、迴歸測試靜默跳過」上吃過一次虧。
    """
    prepare()
    p = run()
    if p.returncode != 0:
        print("★ 基準對照失敗：未變異的副本就跑不過，變異結果全部無效")
        print((p.stdout + p.stderr)[-1500:])
        return 1
    # 「通過」不夠，還要確認需要外部資料的測試沒有被跳過
    out = run(["-s"]).stdout
    skipped = [ln.strip() for ln in out.splitlines() if "SKIP" in ln]
    if skipped:
        print("★ 基準對照失敗：有測試被跳過，那些斷言在整輪變異中都沒有執行")
        for ln in skipped:
            print("   ", ln)
        return 1
    print("基準對照 → 未變異的副本通過，且無測試被跳過 ✓")
    return 0


def main() -> int:
    rc = baseline()
    if rc:
        shutil.rmtree(MUT, ignore_errors=True)
        return rc
    for i, (desc, fname, old, new) in enumerate(MUTATIONS, 1):
        prepare()   # 與基準對照用同一份複製邏輯，兩邊的檔案清單不會各自漂移
        target = MUT / fname
        src = target.read_text(encoding="utf-8")
        # ⚠️ 必須【恰好出現一次】。只驗「有沒有出現」會讓不唯一的字串
        #    靜默改到第一個出現的地方——那未必是描述所指的那一處。
        #    實測 2026-08-21：59 項裡有 6 項字串不唯一，其中「孤兒單位的
        #    父單位不存在」用的 `if up is None:` 出現兩次，一直在改寶山鄉
        #    補償檢查的 continue，而不是它描述的那一行。
        #    **變異測試自己測錯地方，比漏網更難察覺**——它會顯示為
        #    「偵測到」或「漏網」，但兩者都與描述無關。
        n = src.count(old)
        if n != 1:
            print(f"{i}. ★ 變異字串出現 {n} 次（須恰為 1），變異測試本身壞了：{desc}")
            rc = 1
            continue
        target.write_text(src.replace(old, new, 1), encoding="utf-8")
        p = run()
        ok = p.returncode != 0
        print(f"{i}. {'偵測到 ✓' if ok else '★ 沒被偵測到（測試無效）'} — {desc}")
        if not ok:
            rc = 1
    if MUT.exists():
        shutil.rmtree(MUT)
    print("\n變異測試" + ("全部被偵測到" if rc == 0 else "有漏網"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
