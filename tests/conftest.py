"""pytest 公共配置。

沙箱铁律：autouse fixture 强制把 STYLEFORGE_HOME 指向临时目录，
任何测试触碰 settings.json / output-styles 都物理上不可能影响真实 ~/.claude。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "lib"))


@pytest.fixture(autouse=True)
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "sf-home"
    monkeypatch.setenv("STYLEFORGE_HOME", str(home))
    return home
