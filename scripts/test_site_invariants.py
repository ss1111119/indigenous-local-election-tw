#!/usr/bin/env python3
"""站台的不變量：用真實檔案驗，而不是合成資料。

**這個檔案存在的理由是：`site-accessibility-baseline` 那一輪修好的東西，
沒有任何測試在守。** 兩件事都屬於「改壞了畫面不會壞、測試也不會紅」的類型：

1. `docs/index.html` 的內嵌常數與長表不一致。`build_site_data.py --check`
   早就抓得到——它當時回報 36 項差異、退出碼 1——但沒有任何流程會執行它，
   所以 1994-2005 的無黨籍席次被算成「其他」，在站台上活了一整天。
   缺的不是規則，是**執行點**。這裡就是那個執行點。

2. 段內數字的墨色。`--lab1`~`--lab4` 是四個只用在一處的 CSS 變數，
   下一個人很容易當成冗餘而移除，然後白字回來、淺色「其他」上的對比
   掉回 2.12:1。這裡把 4.5:1 這條下限釘住。

3. 相鄰系列的色差。原本只守文字對比，**色差本身沒有任何測試**——把「其他」
   的灰改成任何顏色都不會有測試失敗，包含改成跟旁邊那個系列糊在一起的顏色。
   這正是 `fix-party-bucket-drift` 的 4.1（無黨籍改中性深色）會踩到的地方：
   兩個中性色相鄰、只靠亮度分，是整套配色最容易失效的組合。

⚠️ 與 `test_build_site_data.py` 的分工：那個檔案只放「現有真實資料觸發不到的
   分支」，並明文寫著不重複 `--check` 已在做的事。本檔相反——它**刻意**執行
   `--check`，因為問題從來不是那個比對不夠強，而是沒人跑。

用法：
    pytest scripts/test_site_invariants.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from palette_metrics import (  # noqa: E402
    CVD_FLOOR,
    NORMAL_FLOOR,
    all_pairs,
    delta_e,
)

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
GENERATOR = Path(__file__).resolve().parent / "build_site_data.py"

# 段內文字的最低對比。WCAG AA 對一般大小文字的門檻；段內數字是 9.5px，
# 不能用 large text 的 3:1。
MIN_CONTRAST = 4.5

# 主題區塊：名稱 -> 起始選擇器。淺色是裸 :root，暗色取 [data-theme="dark"]
# 那一份（media query 內的那份與它同值，見 index.html）。
THEME_SELECTORS = {
    "light": ":root{",
    "dark": ':root[data-theme="dark"]{',
}


# ------------------------------------------------------------ WCAG 對比

def _channel(v: float) -> float:
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ------------------------------------------------------------ 讀 CSS 變數

def theme_vars(css: str, selector: str) -> dict[str, str]:
    """取出某個主題區塊裡的 --name:#value 對映。"""
    start = css.find(selector)
    if start == -1:
        raise AssertionError(f"找不到主題區塊 {selector!r}")
    end = css.find("}", start)
    block = css[start:end]
    return {m.group(1): m.group(2)
            for m in re.finditer(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})", block)}


# ------------------------------------------------------------ 測試

def test_embedded_constants_match_long_tables() -> None:
    """站台常數必須與 data/processed 的長表一致。

    這是把 `--check` 拉進測試套件本身。任何改動了衍生邏輯（政黨歸屬、席次
    來源…）卻沒重新產生站台常數的變更，會在這裡失敗並列出差異的鍵。
    """
    proc = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT), timeout=600,
    )
    detail = "\n".join(
        line for line in (proc.stdout or "").splitlines()
        if line.startswith("★") or line.strip().startswith("types[")
    )
    assert proc.returncode == 0, (
        "站台內嵌常數與長表不一致。跑 `python scripts/build_site_data.py --write` "
        f"重新產生，或把差異具名記錄下來。\n{detail or proc.stderr}"
    )


def test_in_mark_label_contrast() -> None:
    """段內數字與政黨徽章的文字，對自己的填色都要有 4.5:1。

    `--labN` 與 `--sN` 一一對應。改了填色卻沒重算墨色，或把四個墨色變數
    收斂成單一顏色，都會在這裡失敗。
    """
    failures: list[str] = []
    for name in ("index.html", "roster.html"):
        css = (DOCS / name).read_text(encoding="utf-8")
        for theme, selector in THEME_SELECTORS.items():
            v = theme_vars(css, selector)
            for i in (1, 2, 3, 4):
                fill, ink = v.get(f"s{i}"), v.get(f"lab{i}")
                assert fill, f"{name} {theme}: 找不到 --s{i}"
                assert ink, (
                    f"{name} {theme}: 找不到 --lab{i}。段內文字的墨色必須依各系列"
                    f"填色分別指定——單一顏色套用到四個填色一定有組合低於 "
                    f"{MIN_CONTRAST}:1，見 site-chart-accessibility spec。"
                )
                ratio = contrast(ink, fill)
                if ratio < MIN_CONTRAST:
                    failures.append(
                        f"{name} {theme} 系列{i}：墨色 {ink} 對填色 {fill} "
                        f"只有 {ratio:.2f}:1（需 ≥{MIN_CONTRAST}）"
                    )
    assert not failures, "段內文字對比不足：\n  " + "\n  ".join(failures)


def test_series_palette_separation() -> None:
    """相鄰系列在常人視覺與 protan／deutan 下都要分得開。

    門檻與 `site-chart-accessibility` spec 一致：常人 ΔE ≥ 15、色盲 ΔE ≥ 8
    （OKLab ×100）。量測工具是同目錄的 `palette_metrics.py`，它對照外部
    驗證器校準過（見該檔 docstring）。

    這個測試在系列色被改動時會立刻回報是哪一對、在哪個主題、差多少。
    """
    failures: list[str] = []
    for name in ("index.html", "roster.html"):
        css = (DOCS / name).read_text(encoding="utf-8")
        for theme, selector in THEME_SELECTORS.items():
            v = theme_vars(css, selector)
            series = [v.get(f"s{i}") for i in (1, 2, 3, 4)]
            assert all(series), f"{name} {theme}: --s1~--s4 不齊"
            # ⚠️ 全配對，不只相鄰。原本只驗相鄰配對，那假設了「圖表的物理排列
            #    永遠是 s1-s2-s3-s4」——而圖例在窄螢幕折成 2×2 時，原本非相鄰的
            #    s1 與 s4 會直接上下相接；讀者跨區比對時視線也會跳躍配對。
            #    實測代價：擴到全配對後，現況四色在兩個頁面、兩個主題下仍全部通過，
            #    所以這是純增強、不是放寬也不是收緊到需要改色。
            #    這條擴充是必要的：把「其他」換成紫色的方案就是在【非相鄰】的
            #    國民黨藍↔紫 上以色盲 ΔE 5.9 失敗，只驗相鄰完全抓不到。
            for i, j in all_pairs(series):
                normal = delta_e(series[i], series[j])
                cvd = min(delta_e(series[i], series[j], "protan"),
                          delta_e(series[i], series[j], "deutan"))
                if normal < NORMAL_FLOOR or cvd < CVD_FLOOR:
                    adj = "相鄰" if j == i + 1 else "非相鄰"
                    failures.append(
                        f"{name} {theme} 系列{i + 1}↔{j + 1}（{adj}）"
                        f"（{series[i]}↔{series[j]}）："
                        f"常人 {normal:.1f}（需 ≥{NORMAL_FLOOR:.0f}）、"
                        f"色盲 {cvd:.1f}（需 ≥{CVD_FLOOR:.0f}）"
                    )
    assert not failures, "系列色差不足：\n  " + "\n  ".join(failures)


def test_pages_declare_encoding_language_and_viewport() -> None:
    """離線開啟不能變亂碼、手機不能用桌機寬度渲染。

    線上靠 GitHub Pages 送的 header 會蓋過缺少的 charset，所以這件事在
    瀏覽線上站台時看不出來——只有把檔案存下來開才會發現。
    """
    failures: list[str] = []
    for name in ("index.html", "roster.html"):
        head = (DOCS / name).read_text(encoding="utf-8")[:2000].lower()
        for needle, why in (
            ("<!doctype html>", "缺 doctype，瀏覽器會進入 quirks mode"),
            ('charset="utf-8"', "缺 charset，離線開啟會是亂碼"),
            ("name=\"viewport\"", "缺 viewport，手機會以桌機寬度渲染再縮小"),
            ('lang="zh-hant"', "缺 lang，螢幕閱讀器可能用錯語音"),
        ):
            if needle not in head:
                failures.append(f"{name}: {why}")
    assert not failures, "頁面文件層宣告不完整：\n  " + "\n  ".join(failures)


def test_spec_traces_point_to_tracked_files() -> None:
    """spec 的 `@trace` 條目必須指向版控內的檔案。

    ⚠️ 這一項放在這個檔案，是因為這個檔案存在的理由就是「缺的不是規則，
    是執行點」。`check_spec_traces.py` 若只是一支獨立腳本、沒有任何流程會
    跑它，就跟本檔開頭記載的 `build_site_data.py --check` 是同一個坑。

    ⚠️ 它驗的是【路徑指得到】，不是【溯源正確】。通過不代表 `@trace` 列的
    檔案真的是該條 Requirement 的實作位置——見 HANDOFF 地雷。
    """
    import check_spec_traces as C

    entries = C.collect_trace_entries()
    bad = C.check_traces(entries, C.tracked_files())
    assert not bad, (
        f"{len(bad)} 條 @trace 指向版控外的路徑，前三條：\n  "
        + "\n  ".join(f"{c} / {r} → {p}" for c, r, p in bad[:3])
    )


if __name__ == "__main__":
    for fn in (test_embedded_constants_match_long_tables,
               test_in_mark_label_contrast,
               test_series_palette_separation,
               test_pages_declare_encoding_language_and_viewport,
               test_spec_traces_point_to_tracked_files):
        fn()
        print(f"  PASS  {fn.__name__}")
