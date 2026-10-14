#!/usr/bin/env python3
"""styleforge 仓库度量基线脚本（阶段 1 产出，阶段 3/4/5 复算对比）。

用途：
  1. 输出 Python 文件行数与函数长度热点（T1 品味不变量的度量基础）；
  2. 输出 packs/ 资产 md5 指纹（TD-PACKS-001 的机械校验雏形）；
  3. 扫描 TODO/FIXME 标记与应忽略产物（__pycache__ 等）。

运行：python3 -I scripts/analysis/repo_metrics.py [仓库根目录]
退出码：0 = 无热点；1 = 存在热点（可直接接入门禁）。
修复指引：每个 FAIL 行都附带如何修复的说明。
"""
from __future__ import annotations

import ast
import hashlib
import pathlib
import sys

# 品味不变量 T1 阈值（阶段 3 固化为门禁时可调整）
FILE_MAX_LINES = 500
FUNC_MAX_LINES = 80
IGNORED_DIRS = {'__pycache__', '.git', 'docs', 'packs'}


def main(root: pathlib.Path) -> int:
    hotspots: list[str] = []
    print('# styleforge 仓库度量报告')
    print()
    print('## Python 文件与函数')
    print()
    print('| 文件 | 总行数 | 函数数 | 最长函数 |')
    print('|---|---|---|---|')
    for py in sorted(root.rglob('*.py')):
        rel = py.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        src = py.read_text(encoding='utf-8')
        lines = src.splitlines()
        tree = ast.parse(src)
        funcs = [(n.name, (n.end_lineno or n.lineno) - n.lineno + 1) for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef)]
        longest = max((length for _, length in funcs), default=0)
        print(f'| {rel} | {len(lines)} | {len(funcs)} | {longest} |')
        if len(lines) > FILE_MAX_LINES:
            hotspots.append(
                f'FAIL 文件超长: {rel} {len(lines)} 行 > {FILE_MAX_LINES}'
                f' —— 修复：按职责拆分该文件')
        for name, length in funcs:
            if length > FUNC_MAX_LINES:
                hotspots.append(
                    f'FAIL 函数超长: {rel} {name}() {length} 行 > {FUNC_MAX_LINES}'
                    f' —— 修复：按单一职责拆分函数')

    print()
    print('## packs 资产指纹 (md5)')
    print()
    print('| 文件 | 字节 | md5 |')
    print('|---|---|---|')
    for md in sorted((root / 'packs').rglob('*.md')):
        data = md.read_bytes()
        print(f'| {md.relative_to(root)} | {len(data)} |'
              f' {hashlib.md5(data).hexdigest()} |')

    print()
    print('## TODO/FIXME 标记')
    print()
    found_todo = False
    self_path = (pathlib.Path(__file__).resolve())
    for py in sorted(root.rglob('*.py')):
        if py.resolve() == self_path:
            continue  # 分析工具自身不是被分析对象
        rel = py.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        for no, line in enumerate(py.read_text(encoding='utf-8').splitlines(), 1):
            if 'TODO' in line or 'FIXME' in line:
                print(f'- {rel}:{no}: {line.strip()}')
                found_todo = True
    if not found_todo:
        print('（无）')

    print()
    print('## 应忽略产物检查')
    print()
    for pattern, why in [('**/__pycache__', '字节码缓存不应入库 —— 修复：加入 .gitignore'),
                         ('**/*.pyc', '同上')]:
        hits = [p for p in root.glob(pattern)
                if '.git' not in p.parts]
        status = 'FAIL' if hits else 'PASS'
        print(f'- [{status}] {pattern}: {len(hits)} 处'
              + (f' —— {why}' if hits else ''))
        if hits:
            hotspots.append(f'FAIL {why}: {[str(p) for p in hits]}')

    print()
    if hotspots:
        print('## 热点汇总（退出码 1）')
        for h in hotspots:
            print(f'- {h}')
        return 1
    print('## 热点汇总：无（退出码 0）')
    return 0


if __name__ == '__main__':
    repo = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else \
        pathlib.Path(__file__).resolve().parents[2]
    sys.exit(main(repo))
