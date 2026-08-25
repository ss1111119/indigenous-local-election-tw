#!/usr/bin/env python3
"""變異測試：把 build_legislative_election.py 的驗證逐一改壞，
確認 test_build_legislative_election.py 會失敗（而不是照樣通過）。

用法：python scripts/mutate_build_legislative_election.py

每個變異都在 _mut_leg/ 的獨立副本上做，**不動真正的 scripts/**。

⚠️ 副本必須放在 repo 根目錄【正下方一層】，與 scripts/ 同深度。
   測試檔以 `__file__.parent.parent` 推導 ROOT 去找 data/；放深一層的話，
   非零退出會是「找不到檔案」而不是「抓到變異」——那樣會得出假通過。
   這個專案已經在「副本放錯深度、迴歸測試靜默跳過」上吃過一次虧。

⚠️ 檔名不可用 `test_*.py` 或 `*_test.py` 結尾，執行的部分也必須包在 main() 裡。
   否則 pytest 會依預設樣式收集它，在收集階段就把整套變異跑完。

⚠️ **在乾淨資料上不改變輸出的變異，必須配合成的髒資料。**
   本專案的立委來源目前沒有已知損壞，所以「把補償性檢查拿掉」這類變異
   若只餵真實資料就會存活。那種變異寫在這裡是自欺——測試檔用合成輸入
   驅動那些守衛（見 test_source_guards），變異才咬得到。
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUT = ROOT / "_mut_leg"

SEL = ("test_pipeline_end_to_end or test_synthetic_dirty_data "
       "or test_seat_sequence or test_anchor_2020 "
       "or test_personal_data_absent "
       "or test_age_sentinel or test_elected_from_authoritative "
       "or test_published_levels or test_geo_normalisation "
       "or test_named_defects or test_existing_outputs_untouched "
       "or test_reproducible or test_source_guards "
       "or test_legislative_oracle_rendered_into_shared_document "
       "or test_manifest_rendering_reflects_new_columns "
       "or test_population_is_valid_decimal "
       "or test_oracle_document_written_atomically")

# (說明, 檔名, 原字串, 替換字串)
MUTATIONS = [
    # ── 年齡哨兵 ──────────────────────────────────────────────
    ("年齡哨兵屆別改成地方公職那組（只有 1998 重疊，其餘三屆的 99 會變成年齡）",
     "build_legislative_election.py",
     'AGE_UNRECORDED_TERMS = frozenset({"1995", "1998", "2001", "2004"})',
     'AGE_UNRECORDED_TERMS = frozenset({"1994", "1998", "2002", "2005"})'),
    ("年齡改成無條件把 99 當未記載（新屆真有 99 歲時會被吃掉）",
     "build_legislative_election.py",
     '    if raw == AGE_UNRECORDED_VALUE and year in AGE_UNRECORDED_TERMS:',
     '    if raw == AGE_UNRECORDED_VALUE:'),
    ("年齡 直接抄原值（哨兵原封不動流進乾淨欄位）",
     "build_legislative_election.py",
     '            "年齡": valid_age(year, r[C_AGE]),',
     '            "年齡": r[C_AGE],'),
    ("拿掉「未具名屆別不得出現哨兵」那條斷言",
     "build_legislative_election.py",
     '    elif AGE_UNRECORDED_VALUE in vals:',
     '    elif False:'),

    # ── 席次 ─────────────────────────────────────────────────
    ("應選名額改成常數 3 席（1998／2001／2004 實際是 4 席）",
     "build_legislative_election.py",
     '    "1995": 3, "1998": 4, "2001": 4, "2004": 4,',
     '    "1995": 3, "1998": 3, "2001": 3, "2004": 3,'),
    ("席次三方核對改成只比兩方（釘死值與 elprof 不再交叉）",
     "build_legislative_election.py",
     '    if not (want == prof_seats == got):',
     '    if not (prof_seats == got):'),

    # ── 當選權威值 ────────────────────────────────────────────
    ("補償檢查的兩側改讀同一欄（恆不成立、一筆都收不到）",
     "build_legislative_election.py",
     '           if (c["當選"] == "Y") != (c["當選註記"] in ELECTED_MARKS)]',
     '           if (c["當選"] == "Y") != (c["當選"] == "Y")]'),
    ("權威值直接抄 elcand 註記（跨檔比對失去意義）",
     "build_legislative_election.py",
     '        c["當選"] = "Y" if mark in ELECTED_MARKS else "N"',
     '        c["當選"] = c["當選註記"] if False else ("Y" if c["當選註記"] in ELECTED_MARKS else "N")'),
    ("跨檔推導改成【不】忽略選舉區欄（十八個檔會全部對不上）",
     "build_legislative_election.py",
     '        k = (r[0], r[1], r[3], r[4], r[6])',
     '        k = (r[0], r[1], r[2], r[3], r[4], r[6])'),

    # ── 個資 ─────────────────────────────────────────────────
    ("把出生日期加進候選人長表的欄位宣告",
     "build_legislative_election.py",
     '    "年齡", "年齡_原始", "現任",\n    "當選註記", "當選註記語意", "當選", "當選_依據",\n)',
     '    "年齡", "年齡_原始", "現任", "出生日期",\n'
     '    "當選註記", "當選註記語意", "當選", "當選_依據",\n)'),

    # ── 2016 降級 ────────────────────────────────────────────
    ("取消 2016 的降級（村里以下 1,402 個無對應單位會流進輸出）",
     "build_legislative_election.py",
     'PUBLISHED_LEVEL_BY_TERM = dict(FINEST_LEVEL_BY_TERM, **{"2016": "鄉鎮市區"})',
     'PUBLISHED_LEVEL_BY_TERM = dict(FINEST_LEVEL_BY_TERM)'),
    ("把兩個層級宣告合併成一個（來源變粗與輸出過細只能二選一）",
     "build_legislative_election.py",
     '    want = PUBLISHED_LEVEL_BY_TERM[year]\n'
     '    return ADMIN_LEVELS.index(admin_level(codes)) <= ADMIN_LEVELS.index(want)',
     '    want = FINEST_LEVEL_BY_TERM[year]\n'
     '    return ADMIN_LEVELS.index(admin_level(codes)) <= ADMIN_LEVELS.index(want)'),

    # ── 地理正規化 ────────────────────────────────────────────
    ("鄉鎮市區_正規化 直接放原始碼（偽裝成標準鍵的毒藥）",
     "build_legislative_election.py",
     '        row["縣市_正規化"] = f"{cp}{cc}"',
     '        row["縣市_正規化"] = f"{cp}{cc}"\n        row["鄉鎮市區_正規化"] = row["鄉鎮市區"]'),
    ("未具名的縣市碼靜默放行而不中止",
     "build_legislative_election.py",
     '        if key not in crosswalk:',
     '        if False:'),
    ("具名合併的檢查改成子集合（合併少掉一半不會被抓到）",
     "build_legislative_election.py",
     '    if set(multi) != set(NAMED_COUNTY_MERGES):',
     '    if not set(multi) <= set(NAMED_COUNTY_MERGES):'),
    ("對照表不再檢查有無從未使用的列",
     "build_legislative_election.py",
     '    stale = set(crosswalk) - used\n    if stale:',
     '    stale = set(crosswalk) - used\n    if False:'),

    # ── 具名瑕疵 ──────────────────────────────────────────────
    ("清空 1995 的檔別合計錯置清單",
     "build_legislative_election.py",
     '    ("1995", "L2"): {"1": -1, "3": 1},   # 章仁香 少 1、莊金生 多 1',
     ''),
    ("清空 2004 的有效票不符清單（和平鄉那 58 票）",
     "build_legislative_election.py",
     '    ("2004", "L2"): {("03", "006"): 58,     # 臺中縣：少了和平鄉的 58 票',
     '    ("2004", "L2"): {("03", "006"): 0,'),
    ("清空 1998 的零投票率清單",
     "build_legislative_election.py",
     '        ("03", "011", "00", "025", "0000", "0"): "66.67",   # 臺南縣南化鄉 2/3',
     ''),

    # ── 來源守衛 ──────────────────────────────────────────────
    ("old 目錄的排除改成比對子字串（golden 之類會被誤判）",
     "build_legislative_election.py",
     '    bad = [p for p in paths\n           if EXCLUDED_PATH_SEGMENT in p.split("/")]',
     '    bad = [p for p in paths\n           if EXCLUDED_PATH_SEGMENT in p]'),
    ("引號宣告只驗一個方向（宣告過期不會被抓到）",
     "build_legislative_election.py",
     '    if declared and not found:',
     '    if False:'),
    # ⚠️ 「引號改成全域剝除」曾列於此，**已移除，因為它是等價變異**：
    #    check_quoting_declaration() 在剝除【之前】執行，未具名的檔一旦帶引號
    #    就先中止了，全域剝除永遠碰不到那種輸入。既有資料裡也沒有任何檔案的
    #    值以撇號【合法】開頭。行為上無法區分的變異留在清單裡只會製造
    #    「永遠漏網」的假訊號，把真正的漏網淹掉。
    #    守住「具名宣告不可失效」的是第 21 項（雙向核對只驗一個方向）。
    ("選舉區欄的允許值改成子集合比對（宣告過期不會被抓到）",
     "build_legislative_election.py",
     '    if got != set(want):',
     '    if not got <= set(want):'),
    ("拿掉「不得出現選舉區層級」的斷言",
     "build_legislative_election.py",
     '    if "選舉區" in levels:',
     '    if False:'),
    ("讀取時不做關聯鍵的尾隨空白正規化（1995 的 450 列會誤判層級）",
     "build_legislative_election.py",
     '                    quoted=is_quoted(year, etype, stem), keys=KEY_COLS[stem])',
     '                    quoted=is_quoted(year, etype, stem), keys=())'),

    # ── 輸出契約 ──────────────────────────────────────────────
    ("欄位集合檢查改成只驗「不缺」（多出來的欄位靜默通過）",
     "build_legislative_election.py",
     '        if set(row) != set(want):',
     '        if not set(want) <= set(row):'),
    ("CSV 換行改回平台預設（Windows 產出與 Linux 不同、雜湊對照失效）",
     "build_legislative_election.py",
     '    w = csv.DictWriter(buf, fieldnames=list(cols), lineterminator="\\n",',
     '    w = csv.DictWriter(buf, fieldnames=list(cols),'),
    ("gzip 不固定 mtime（同樣輸入產生不同位元組）",
     "build_legislative_election.py",
     '    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as fh:',
     '    with gzip.GzipFile(fileobj=buf, mode="wb") as fh:'),

    # ── 報告 ─────────────────────────────────────────────────
    ("報告的兩個當選人數改讀同一欄（差異消失、報告不再含資訊）",
     "build_legislative_election.py",
     '        if c["當選註記"] in ELECTED_MARKS:      # 來源怎麼寫',
     '        if c["當選"] == "Y":                    # 來源怎麼寫'),

    # ── oracles.py 的共用函式（本次變更新增）─────────────────────
    ("check_population_column 拿掉 is_finite 檢查（Infinity/NaN 會靜默通過）",
     "oracles.py",
     "        if not pop.is_finite():",
     "        if False:"),
    ("write_oracle_document 寫入的內容被置換（原子寫入本身失去意義）",
     "oracles.py",
     '        with os.fdopen(fd, "w", encoding="utf-8") as f:\n            f.write(content)',
     '        with os.fdopen(fd, "w", encoding="utf-8") as f:\n            f.write("MUTATED")'),
]


def prepare() -> None:
    """建立一份乾淨的副本。"""
    if MUT.exists():
        shutil.rmtree(MUT)
    MUT.mkdir(parents=True)
    for f in ("oracles.py", "build_local_election.py",
              "build_legislative_election.py",
              "test_build_legislative_election.py"):
        shutil.copy(ROOT / "scripts" / f, MUT / f)


def run(extra: list[str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest",
         str(MUT / "test_build_legislative_election.py"), "-q", "-k", SEL,
         *(extra or [])],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT,
    )


def baseline() -> int:
    """⚠️ 基準對照：未變異的副本必須通過，而且該跑的測試必須真的跑到。

    少了這一關，只要副本環境有問題（例如放錯深度導致找不到 data/），
    每個變異都會【全部失敗】而被報成「全部被偵測到」——證明不了任何事。
    """
    prepare()
    p = run()
    if p.returncode != 0:
        print("★ 基準對照失敗：未變異的副本就跑不過，變異結果全部無效")
        print((p.stdout + p.stderr)[-1500:])
        return 1
    out = run(["-s"]).stdout
    skipped = [ln.strip() for ln in out.splitlines() if "SKIP" in ln]
    if skipped:
        print(f"★ 基準對照有 {len(skipped)} 項測試被跳過，變異結果不可信：")
        for s in skipped:
            print("   ", s)
        return 1
    print("基準對照：未變異的副本通過，且無測試被跳過 ✓\n")
    return 0


ORACLE_DOC = ROOT / "docs" / "schema" / "oracles.md"


def _oracle_doc_is_clean() -> bool:
    """`write_oracle_document()` 的 ROOT 算的是真正的專案根目錄，即使從
    `_mut_leg/` 副本呼叫也一樣——所以任何一項變異只要跑到這個函式，
    寫的是【真正的】`docs/schema/oracles.md`，不是副本裡的檔案。
    跑之前該檔案必須乾淨，否則跑完用 `git checkout` 復原會連使用者
    未提交的改動一起還原掉。
    """
    r = subprocess.run(["git", "diff", "--quiet", "--", str(ORACLE_DOC)],
                       capture_output=True, cwd=ROOT)
    return r.returncode == 0


def main() -> int:
    if not _oracle_doc_is_clean():
        print(f"★ {ORACLE_DOC} 有未提交的改動：這個變異套件會呼叫"
              f"write_oracle_document() 寫到這個真檔，跑完會用 git checkout"
              f"復原，連你的改動一起還原掉。請先提交或暫存後再跑。")
        return 1
    rc = baseline()
    if rc:
        shutil.rmtree(MUT, ignore_errors=True)
        return rc
    try:
        for i, (desc, fname, old, new) in enumerate(MUTATIONS, 1):
            prepare()
            target = MUT / fname
            src = target.read_text(encoding="utf-8")
            if old not in src:
                print(f"{i}. ★ 變異字串找不到，變異測試本身壞了：{desc}")
                rc = 1
                continue
            target.write_text(src.replace(old, new, 1), encoding="utf-8")
            p = run()
            ok = p.returncode != 0 and "INTERNALERROR" not in (p.stdout + p.stderr)
            print(f"{i}. {'偵測到 ✓' if ok else '★ 沒被偵測到（測試無效）'} — {desc}")
            if not ok:
                rc = 1
    finally:
        # ⚠️ 不論成功或失敗都要復原：任何一項變異的測試執行過程都可能
        #    把真正的 oracles.md 寫壞（見上面 _oracle_doc_is_clean 的說明），
        #    不是只有針對 write_oracle_document 的那一項變異才有風險。
        subprocess.run(["git", "checkout", "--", str(ORACLE_DOC)], cwd=ROOT,
                       capture_output=True)
        if MUT.exists():
            shutil.rmtree(MUT)
    print("\n變異測試" + ("全部被偵測到" if rc == 0 else "有漏網"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
