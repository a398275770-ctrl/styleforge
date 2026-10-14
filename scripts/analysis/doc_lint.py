#!/usr/bin/env python3
"""文档门禁（阶段 2 产出）：死链 / 必填节 / 索引完整性 / AGENTS.md 长度。

运行：python3 -I scripts/analysis/doc_lint.py [仓库根目录]
退出码：0 = 全部通过；1 = 存在违规（每条 FAIL 附修复指引）。
门禁接入：阶段 3 挂入 CI 与 pre-commit。
"""

from __future__ import annotations

import pathlib
import re
import sys

AGENTS_MAX_LINES = 200  # 规则 §2.2：AGENTS.md 超 200 行即为反模式

# 必填节：文件 -> 必须出现的章节标题关键词
REQUIRED_SECTIONS = {
    "AGENTS.md": ["这是什么项目", "常用命令", "目录地图", "硬性约束"],
    "ARCHITECTURE.md": ["依赖方向", "设计决策"],
    "docs/QUALITY_SCORE.md": ["当前评分"],
    "docs/CI.md": ["框架判定"],
    "docs/SECURITY.md": ["安全承诺", "已知问题"],
    "docs/index.md": ["docs/ 索引"],
}

# 参与 lint 的文档（施工图两份除外：施工期常驻、竣工归档）
LINTED_DOCS = list(REQUIRED_SECTIONS) + [
    "docs/design-docs/index.md",
    "docs/design-docs/core-beliefs.md",
    "README.md",
]

MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")


def check_links(root: pathlib.Path, failures: list[str]) -> None:
    for doc in LINTED_DOCS + [
        "docs/exec-plans/active/harness-migration.md",
        "docs/exec-plans/tech-debt-tracker.md",
    ]:
        path = root / doc
        if not path.exists():
            failures.append(f"FAIL 文档缺失: {doc} —— 修复：恢复该文件或更新 doc_lint.py 的清单")
            continue
        base = path.parent
        for text, target in MD_LINK.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue  # 外链/锚点不查存在性
            file_part = target.split("#")[0]
            if not file_part:
                continue
            if not (base / file_part).exists():
                failures.append(
                    f"FAIL 死链: {doc} 中的 [{text}]({target}) —— "
                    f"修复：更正路径，或创建 {base / file_part}"
                )


def check_sections(root: pathlib.Path, failures: list[str]) -> None:
    for doc, sections in REQUIRED_SECTIONS.items():
        path = root / doc
        if not path.exists():
            continue  # 缺失已在 check_links 报
        text = path.read_text(encoding="utf-8")
        for section in sections:
            if section not in text:
                failures.append(
                    f"FAIL 缺必填节: {doc} 缺「{section}」 —— "
                    f"修复：补该节内容（见 docs/design-docs/core-beliefs.md 的结构约定）"
                )


def check_index_covers_docs(root: pathlib.Path, failures: list[str]) -> None:
    index = root / "docs" / "index.md"
    if not index.exists():
        return  # 已在 check_links 报
    text = index.read_text(encoding="utf-8")
    for md in sorted((root / "docs").glob("*.md")):
        if md.name == "index.md":
            continue
        if md.name not in text:
            failures.append(
                f"FAIL 索引缺条目: docs/{md.name} 未出现在 docs/index.md —— "
                f"修复：在 docs/index.md 表格中补一行"
            )


def check_agents_length(root: pathlib.Path, failures: list[str]) -> None:
    agents = root / "AGENTS.md"
    if not agents.exists():
        return
    lines = agents.read_text(encoding="utf-8").splitlines()
    if len(lines) > AGENTS_MAX_LINES:
        failures.append(
            f"FAIL AGENTS.md 超长: {len(lines)} 行 > {AGENTS_MAX_LINES} —— "
            f"修复：按规则 §2.2 把细节下推到 docs/，入口只留地图"
        )


def main(root: pathlib.Path) -> int:
    failures: list[str] = []
    check_links(root, failures)
    check_sections(root, failures)
    check_index_covers_docs(root, failures)
    check_agents_length(root, failures)

    print("# styleforge 文档门禁报告")
    print()
    if failures:
        print(f"## 违规 {len(failures)} 条（退出码 1）")
        for f in failures:
            print(f"- {f}")
        return 1
    print("## 全部通过（退出码 0）：链接 / 必填节 / 索引完整性 / AGENTS 长度")
    return 0


if __name__ == "__main__":
    repo = (
        pathlib.Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else pathlib.Path(__file__).resolve().parents[2]
    )
    sys.exit(main(repo))
