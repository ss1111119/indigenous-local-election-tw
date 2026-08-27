#!/usr/bin/env python3
"""驗證 `openspec/specs/*/spec.md` 的 `@trace` 條目指向拿得到的檔案。

⚠️ **這支腳本驗的是「路徑指得到」，不是「溯源正確」。**
通過不代表 `@trace` 列的檔案真的是該條 Requirement 的實作位置。實測
（2026-08-27）剝除死鏈後仍有六個檔案各出現在 53–73 個區塊（共 83 個）——
出現在 88% 的 Requirement 上的檔案沒有指出任何東西。見 HANDOFF 地雷。

判準是**是否在版控內**，不是「檔案是否存在」。`scratch/` 下的檔案在作者本機
確實存在，但它在 `.gitignore` 內，任何人 clone 都拿不到——溯源的用途是讓別人
找得到，判準必須是「別人拿得到嗎」。

⚠️ `git ls-files` 預設會把非 ASCII 路徑輸出成跳脫字串（如
`"docs/\\345\\261\\261..."`），直接比對中文檔名會**全部誤判為死鏈**。
必須加 `-c core.quotepath=false`。本專案第一次量測就是這樣錯的。

用法：
    python scripts/check_spec_traces.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = ROOT / "openspec" / "specs"

TRACE_RE = re.compile(r"<!-- @trace(.*?)-->", re.S)
REQ_RE = re.compile(r"(?m)^### Requirement: (.+)$")


class TraceCheckError(Exception):
    """檢查無法執行，或發現違規。一律中止，不回退成較弱的判準。"""


def tracked_files() -> set[str]:
    """回傳版控內的檔案路徑集合。

    ⚠️ 取不到時**中止**，不可回退成「檔案是否存在」——那會讓 `scratch/`
    條目在沒有 git 的環境下靜默通過，也就是這支腳本存在的唯一理由失效。
    """
    try:
        out = subprocess.run(
            ["git", "-c", "core.quotepath=false", "ls-files"],
            cwd=ROOT, capture_output=True, check=True,
        ).stdout.decode("utf-8")
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TraceCheckError(
            f"取不到版控檔案清單（{type(exc).__name__}: {exc}）。"
            f"本檢查的判準是「是否在版控內」，取不到就無法判定——"
            f"刻意不回退成「檔案是否存在」，那會讓未入庫的路徑靜默通過。"
        ) from exc
    files = {line for line in out.split("\n") if line}
    if not files:
        raise TraceCheckError("版控檔案清單是空的——不在 repo 內或 git 狀態異常。")
    return files


def collect_trace_entries(
    specs_dir: Path | None = None,
) -> list[tuple[str, str, str]]:
    """收集所有 `@trace` 條目，回傳 [(能力, Requirement 名稱, 路徑)]。

    Requirement 名稱取該 `@trace` 區塊**之前**最近的一個
    `### Requirement:` 標題——區塊是接在它所屬的 Requirement 後面的。
    """
    specs_dir = SPECS_DIR if specs_dir is None else specs_dir
    spec_files = sorted(specs_dir.glob("*/spec.md"))
    if not spec_files:
        raise TraceCheckError(
            f"{specs_dir} 下找不到任何 spec 檔。"
            f"零違規若來自零輸入，與「全部通過」無法分辨。"
        )
    entries: list[tuple[str, str, str]] = []
    for f in spec_files:
        text = f.read_text(encoding="utf-8")
        cap = f.parent.name
        req_at = [(m.start(), m.group(1).strip()) for m in REQ_RE.finditer(text)]
        for m in TRACE_RE.finditer(text):
            prior = [name for pos, name in req_at if pos < m.start()]
            req = prior[-1] if prior else "(不在任何 Requirement 之下)"
            for line in m.group(1).splitlines():
                line = line.strip()
                if line.startswith("- "):
                    entries.append((cap, req, line[2:].strip()))
    if not entries:
        raise TraceCheckError(
            "所有 spec 檔內都找不到 @trace 條目。"
            "零違規若來自零輸入，與「全部通過」無法分辨。"
        )
    return entries


def check_traces(
    entries: list[tuple[str, str, str]], tracked: set[str],
) -> list[tuple[str, str, str]]:
    """回傳違規條目 [(能力, Requirement, 路徑)]。"""
    return [e for e in entries if e[2] not in tracked]


def main() -> int:
    try:
        entries = collect_trace_entries()
        tracked = tracked_files()
    except TraceCheckError as exc:
        print(f"中止：{exc}", file=sys.stderr)
        return 1

    bad = check_traces(entries, tracked)
    caps = len({e[0] for e in entries})
    print(f"@trace 條目 {len(entries)} 條，涵蓋 {caps} 個能力")

    if not bad:
        print("全部指向版控內的檔案 ✓")
        print("⚠️ 本檢查【只驗路徑指得到】，不驗溯源是否正確——見 HANDOFF 地雷。")
        return 0

    print(f"\n{len(bad)} 條指向版控外的路徑：", file=sys.stderr)
    shown = 0
    for cap, req, path in bad:
        if shown < 20:
            print(f"  {cap} / {req}\n    → {path}", file=sys.stderr)
            shown += 1
    if len(bad) > shown:
        print(f"  …另有 {len(bad) - shown} 條未列出", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
