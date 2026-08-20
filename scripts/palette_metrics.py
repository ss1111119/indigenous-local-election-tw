#!/usr/bin/env python3
"""配色距離量測：OKLab ΔE 與色覺障礙模擬。

**這支存在的理由是：spec 要求「顏色驗證須記錄工具與實測值」，但原本用來量測的
工具（`dataviz` skill 的 `validate_palette.js`）不在這個 repo 裡，也不是每個
session 都摸得到。** 依賴一個拿不到的工具，等於那條 requirement 沒有人能履行。

## 實作與校準

- **OKLab**：Björn Ottosson 的 sRGB→OKLab 轉換。ΔE 為 OKLab 空間的歐氏距離 ×100。
- **色覺障礙模擬**：Machado, Oliveira & Fernandes (2009) 的 severity 1.0 矩陣，
  **套用在線性 RGB**（不是 gamma 空間——實測差 0.6~1.2）。

對照 `validate_palette.js` 的輸出校準過，四個參考點：

| 配對 | 型別 | 參考值 | 本實作 | 差 |
| --- | --- | ---: | ---: | ---: |
| `#ADB3B9`↔`#1baf7a` | 常人 | 16.9 | 16.9 | 0.04 |
| `#6A7178`↔`#1da77a` | 常人 | 16.6 | 16.6 | 0.04 |
| `#ADB3B9`↔`#1baf7a` | protan | 9.0 | 9.0 | 0.01 |
| `#1da77a`↔`#d95926` | deutan | 9.7 | 9.7 | 0.03 |

⚠️ **tritan（藍黃色盲）沒有實作。** 試過 Viénot 單平面近似與 Machado 矩陣，
與參考值分別差 8~20 與 4~18，顯然對方用的是別的方法（可能是 Brettel 雙平面）。
與其提供一個對不上的數字，這裡直接不提供——需要 tritan 就得用外部驗證器。
本專案 spec 的 CVD 門檻只涵蓋 protan 與 deutan，所以不影響那條 requirement。

## 用法

    python scripts/palette_metrics.py "#2a78d6,#eb6834,#1baf7a,#ADB3B9"
    python scripts/palette_metrics.py "#3987e5,#d95926,#1da77a,#6A7178" --labels 國民黨,無黨籍,民進黨,其他

門檻（與 `site-chart-accessibility` spec 一致）：相鄰配對常人 ΔE ≥ 15、
protan／deutan ΔE ≥ 8。列出所有配對，並標出不過門檻者。
"""

from __future__ import annotations

import argparse
import math
import sys

# sRGB(linear) → OKLab，Ottosson
M1 = ((0.4122214708, 0.5363325363, 0.0514459929),
      (0.2119034982, 0.6806995451, 0.1073969566),
      (0.0883024619, 0.2817188376, 0.6299787005))
M2 = ((0.2104542553, 0.7936177850, -0.0040720468),
      (1.9779984951, -2.4285922050, 0.4505937099),
      (0.0259040371, 0.7827717662, -0.8086757660))

# Machado 2009, severity 1.0，套用於線性 RGB
CVD_MATRICES = {
    "protan": ((0.152286, 1.052583, -0.204868),
               (0.114503, 0.786281, 0.099216),
               (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968),
               (0.280085, 0.672501, 0.047413),
               (-0.011820, 0.042940, 0.968881)),
}

NORMAL_FLOOR = 15.0
CVD_FLOOR = 8.0


def _mul(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))


def _to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(color: str) -> tuple[float, float, float]:
    h = color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"不是合法的顏色：{color!r}")
    return tuple(_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


def oklab(rgb_linear) -> tuple[float, float, float]:
    lms = _mul(M1, rgb_linear)
    # 負值取立方根要保留正負號，否則會在色域外的顏色上靜默失真
    lms_ = tuple(math.copysign(abs(v) ** (1 / 3), v) for v in lms)
    return _mul(M2, lms_)


def simulate(rgb_linear, kind: str):
    out = _mul(CVD_MATRICES[kind], rgb_linear)
    return tuple(min(1.0, max(0.0, c)) for c in out)


def delta_e(a: str, b: str, kind: str | None = None) -> float:
    """兩色在 OKLab 的距離 ×100。kind 為 None 時是常人視覺。"""
    la, lb = hex_to_linear(a), hex_to_linear(b)
    if kind is not None:
        la, lb = simulate(la, kind), simulate(lb, kind)
    return 100 * math.dist(oklab(la), oklab(lb))


def adjacent_pairs(colors: list[str]) -> list[tuple[int, int]]:
    """系列順序上相接的兩個。"""
    return [(i, i + 1) for i in range(len(colors) - 1)]


def all_pairs(colors: list[str]) -> list[tuple[int, int]]:
    """所有兩兩配對。

    ⚠️ **門檻應該套在全配對，不只相鄰配對。** 只驗相鄰，等於假設圖表的物理排列
       永遠是 s1-s2-s3-s4——但圖例在窄螢幕折成 2×2 時，原本非相鄰的 s1 與 s4
       會直接上下相接，讀者跨區比對時視線也會跳躍配對。
       實例：把「其他」桶改成紫色的方案，在【非相鄰】的國民黨藍↔紫上
       色盲 ΔE 只有 5.9（門檻 8），只驗相鄰完全抓不到。
    """
    return [(i, j) for i in range(len(colors)) for j in range(i + 1, len(colors))]


def report(colors: list[str], labels: list[str] | None = None,
           every_pair: bool = False):
    labels = labels or [c for c in colors]
    pairs = all_pairs(colors) if every_pair else adjacent_pairs(colors)
    rows, failures = [], []
    for i, j in pairs:
        n = delta_e(colors[i], colors[j])
        p = delta_e(colors[i], colors[j], "protan")
        d = delta_e(colors[i], colors[j], "deutan")
        bad = []
        if n < NORMAL_FLOOR:
            bad.append(f"常人 {n:.1f} < {NORMAL_FLOOR:.0f}")
        if min(p, d) < CVD_FLOOR:
            bad.append(f"色盲 {min(p, d):.1f} < {CVD_FLOOR:.0f}")
        rows.append((labels[i], labels[j], n, p, d, bad))
        if bad:
            failures.append((labels[i], labels[j], bad))
    return rows, failures


def main() -> int:
    ap = argparse.ArgumentParser(description="量測配色的相鄰距離（OKLab ΔE、protan／deutan）")
    ap.add_argument("colors", help="以逗號分隔的十六進位色，依系列順序")
    ap.add_argument("--labels", help="以逗號分隔的系列名稱，數量須與顏色相同")
    ap.add_argument("--all-pairs", action="store_true", help="量所有配對，不只相鄰")
    args = ap.parse_args()

    colors = [c.strip() for c in args.colors.split(",") if c.strip()]
    labels = [s.strip() for s in args.labels.split(",")] if args.labels else None
    if labels and len(labels) != len(colors):
        print("--labels 的數量與顏色不符", file=sys.stderr)
        return 2

    rows, failures = report(colors, labels, every_pair=args.all_pairs)
    print(f"{'配對':<28}{'常人':>7}{'protan':>9}{'deutan':>9}")
    for a, b, n, p, d, bad in rows:
        mark = "  ✗ " + "、".join(bad) if bad else ""
        print(f"{a + ' ↔ ' + b:<28}{n:>7.1f}{p:>9.1f}{d:>9.1f}{mark}")
    print()
    if failures:
        print(f"未過門檻：{len(failures)} 組（常人 ≥{NORMAL_FLOOR:.0f}、色盲 ≥{CVD_FLOOR:.0f}）")
        return 1
    print(f"全部通過（常人 ≥{NORMAL_FLOOR:.0f}、色盲 ≥{CVD_FLOOR:.0f}）")
    print("註：tritan 未實作，見本檔 docstring。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
