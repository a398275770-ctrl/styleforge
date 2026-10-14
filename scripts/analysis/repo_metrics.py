#!/usr/bin/env python3
"""styleforge 仓库度量基线脚本（阶段 1 产出，阶段 3/4/5 复算对比）。

用途：
  1. 输出 Python 文件行数与函数长度热点（T1 品味不变量的度量基础）；
  2. 输出 packs/ 资产 md5 指纹（TD-PACKS-001 的机械校验雏形）；
  3. 扫描 TODO/FIXME 标记与被 git 追踪的缓存产物。

运行：python3 -I scripts/analysis/repo_metrics.py [仓库根目录]
退出码：0 = 无热点；1 = 存在热点（可直接接入门禁）。
修复指引：每个 FAIL 行都附带如何修复的说明。
"""

from __future__ import annotations

import ast
import hashlib
import pathlib
import subprocess
import sys

# 品味不变量 T1 阈值（阶段 3 固化为门禁时可调整）
FILE_MAX_LINES = 500
FUNC_MAX_LINES = 80
IGNORED_DIRS = {"__pycache__", ".git", ".venv", "docs", "packs"}


def iter_repo_python(root: pathlib.Path):
    """仓库内参与度量的 .py（排除忽略目录与工具自身）。"""
    self_path = pathlib.Path(__file__).resolve()
    for py in sorted(root.rglob("*.py")):
        rel = py.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        if py.resolve() == self_path:
            continue  # 分析工具自身不是被分析对象
        yield py, rel


def report_python_files(root: pathlib.Path, hotspots: list[str]) -> None:
    print("## Python 文件与函数")
    print()
    print("| 文件 | 总行数 | 函数数 | 最长函数 |")
    print("|---|---|---|---|")
    for py, rel in iter_repo_python(root):
        src = py.read_text(encoding="utf-8")
        lines = src.splitlines()
        tree = ast.parse(src)
        funcs = [
            (n.name, (n.end_lineno or n.lineno) - n.lineno + 1)
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef)
        ]
        longest = max((length for _, length in funcs), default=0)
        print(f"| {rel} | {len(lines)} | {len(funcs)} | {longest} |")
        if len(lines) > FILE_MAX_LINES:
            hotspots.append(
                f"FAIL 文件超长: {rel} {len(lines)} 行 > {FILE_MAX_LINES} —— 修复：按职责拆分该文件"
            )
        for name, length in funcs:
            if length > FUNC_MAX_LINES:
                hotspots.append(
                    f"FAIL 函数超长: {rel} {name}() {length} 行 > {FUNC_MAX_LINES}"
                    f" —— 修复：按单一职责拆分函数"
                )


def report_pack_fingerprints(root: pathlib.Path) -> None:
    print("## packs 资产指纹 (md5)")
    print()
    print("| 文件 | 字节 | md5 |")
    print("|---|---|---|")
    for md in sorted((root / "packs").rglob("*.md")):
        data = md.read_bytes()
        print(f"| {md.relative_to(root)} | {len(data)} | {hashlib.md5(data).hexdigest()} |")


def report_todo_markers(root: pathlib.Path) -> None:
    print("## TODO/FIXME 标记")
    print()
    found = False
    for py, rel in iter_repo_python(root):
        for no, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if "TODO" in line or "FIXME" in line:
                print(f"- {rel}:{no}: {line.strip()}")
                found = True
    if not found:
        print("（无）")


def check_tracked_artifacts(root: pathlib.Path, hotspots: list[str]) -> None:
    print("## 应忽略产物检查")
    print()
    # 语义：磁盘上存在但被 .gitignore 忽略 = 正常；被 git 追踪 = 违规。
    # （TD-REPO-002 收口：检查从『存在即失败』改为『入库即失败』）
    try:
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.splitlines()
    except Exception:
        print("- [SKIP] 非 git 环境，跳过追踪检查")
        return
    bad = [f for f in tracked if f.endswith(".pyc") or "__pycache__" in f]
    status = "FAIL" if bad else "PASS"
    print(
        f"- [{status}] 缓存产物入库检查: {len(bad)} 处"
        + (" —— 修复：git rm --cached 这些文件（.gitignore 已就位）" if bad else "")
    )
    if bad:
        hotspots.append(f"FAIL 缓存产物被追踪: {bad}")


def main(root: pathlib.Path) -> int:
    hotspots: list[str] = []
    print("# styleforge 仓库度量报告")
    print()
    report_python_files(root, hotspots)
    print()
    report_pack_fingerprints(root)
    print()
    report_todo_markers(root)
    print()
    check_tracked_artifacts(root, hotspots)
    print()
    if hotspots:
        print("## 热点汇总（退出码 1）")
        for h in hotspots:
            print(f"- {h}")
        return 1
    print("## 热点汇总：无（退出码 0）")
    return 0


if __name__ == "__main__":
    repo = (
        pathlib.Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else pathlib.Path(__file__).resolve().parents[2]
    )
    sys.exit(main(repo))
