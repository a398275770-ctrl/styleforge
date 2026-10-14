"""架构结构测试：依赖方向白名单（ARCHITECTURE.md §1 的机械强制）。

规则：入口 → CLI(styleforge.py) → core(lib/sf_core.py) → 仅标准库。
违反任何一条，本文件失败；报错信息直接给出修复方向。
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "styleforge.py"
CORE = REPO / "lib" / "sf_core.py"


def imported_top_levels(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


class TestCoreLayer:
    def test_core_imports_stdlib_only(self):
        """core 层零第三方依赖（core-beliefs #16）——修复：移除第三方 import。"""
        external = imported_top_levels(CORE) - set(sys.stdlib_module_names)
        assert external == set(), f"lib/sf_core.py 引入了非标准库: {sorted(external)}"

    def test_core_never_imports_cli(self):
        """禁止反向依赖——修复：把需要的逻辑上移到 CLI 层。"""
        assert "styleforge" not in imported_top_levels(CORE)


class TestCliLayer:
    def test_cli_only_stdlib_and_core(self):
        """CLI 只准依赖标准库 + sf_core——修复：新依赖先过 core-beliefs 裁决。"""
        allowed = set(sys.stdlib_module_names) | {"sf_core"}
        external = imported_top_levels(CLI) - allowed
        assert external == set(), f"styleforge.py 引入了越层/第三方依赖: {sorted(external)}"


class TestEntryPoints:
    def test_shell_entries_only_call_cli(self):
        """入口脚本只准转发给 styleforge.py——修复：业务逻辑移入 core。"""
        for sh in ("one-click-install.sh", "one-click-uninstall.sh"):
            text = (REPO / sh).read_text(encoding="utf-8")
            assert "styleforge.py" in text
            assert "sf_core" not in text, f"{sh} 越层直连 core"
        cmd = (REPO / "styleforge.cmd").read_text(encoding="utf-8")
        assert "styleforge.py" in cmd and "sf_core" not in cmd


class TestVersionSingleSource:
    def test_version_declared_only_in_core(self):
        """版本唯一声明点（规则 §6.1）——修复：删除多余声明，改由 sf_core 引出。"""
        version_decl = re.compile(r"^VERSION\s*=", re.MULTILINE)
        assert len(version_decl.findall(CORE.read_text(encoding="utf-8"))) == 1
        for other in (CLI, REPO / "pyproject.toml"):
            text = other.read_text(encoding="utf-8")
            assert not version_decl.search(text), f"{other.name} 出现第二版本声明点"
