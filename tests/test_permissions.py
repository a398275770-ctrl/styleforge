"""settings.json 权限守恒（TD-CORE-003 回归：0600 不得被放宽为 0644）。

背景：atomic_write_text 曾以固定 0o644 chmod 临时文件后 os.replace，
覆盖已有 settings.json 时会把 0600 放宽为 0644（2026-10-14 沙箱实测）。
修复语义：目标已存在 → 沿用其现有权限；新建 settings.json → 0600。
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from sf_core import (
    apply_style,
    atomic_write_text,
    remove_style,
    restore_settings,
    settings_path,
)


def file_mode(path: Path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


@pytest.mark.skipif(os.name != "posix", reason="chmod 语义仅 POSIX")
class TestAtomicWritePreservesMode:
    def test_existing_0600_stays_0600(self, tmp_path):
        target = tmp_path / "settings.json"
        target.write_text("{}", encoding="utf-8")
        os.chmod(target, 0o600)
        atomic_write_text(target, '{"a": 1}', mode=0o600)
        assert file_mode(target) == 0o600

    def test_existing_0644_stays_0644(self, tmp_path):
        target = tmp_path / "plain.txt"
        target.write_text("x", encoding="utf-8")
        os.chmod(target, 0o644)
        atomic_write_text(target, "y", mode=0o600)
        assert file_mode(target) == 0o644  # 已有权限优先于参数

    def test_new_file_gets_param_mode(self, tmp_path):
        target = tmp_path / "new" / "settings.json"
        atomic_write_text(target, "{}", mode=0o600)
        assert file_mode(target) == 0o600


@pytest.mark.skipif(os.name != "posix", reason="chmod 语义仅 POSIX")
class TestSettingsPermissionsAcrossActions:
    def _install(self):
        apply_style("default", "default")

    def test_install_keeps_existing_0600(self, sandbox):
        settings_path().parent.mkdir(parents=True)
        settings_path().write_text("{}", encoding="utf-8")
        os.chmod(settings_path(), 0o600)
        self._install()
        assert file_mode(settings_path()) == 0o600

    def test_install_creates_settings_as_0600(self, sandbox):
        self._install()
        assert file_mode(settings_path()) == 0o600

    def test_uninstall_keeps_permissions(self, sandbox):
        self._install()
        os.chmod(settings_path(), 0o600)
        remove_style()
        assert file_mode(settings_path()) == 0o600

    def test_restore_keeps_permissions(self, sandbox, tmp_path):
        self._install()
        os.chmod(settings_path(), 0o600)
        backup = tmp_path / "bak"
        backup.write_text('{"x": 1}', encoding="utf-8")
        restore_settings(backup)
        assert file_mode(settings_path()) == 0o600

    def test_widening_regression_guard(self, sandbox):
        """核心回归：0600 → 任何动作后不得变 0644。"""
        settings_path().parent.mkdir(parents=True)
        settings_path().write_text("{}", encoding="utf-8")
        os.chmod(settings_path(), 0o600)
        self._install()
        assert file_mode(settings_path()) != 0o644
