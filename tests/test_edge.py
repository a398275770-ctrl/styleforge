"""边界与异常补全（阶段 5）：路径解析 fallback、写失败清理、能力降级路径。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import sf_core
from sf_core import (
    StyleForgeError,
    atomic_write_text,
    backup_settings,
    ensure_trailing_newline,
    list_packs,
    list_settings_backups,
    read_bytes_as_text,
    resolve_home,
    settings_path,
)


class TestResolveHomeFallbacks:
    def test_styleforge_home_wins(self, monkeypatch, tmp_path):
        monkeypatch.setenv("STYLEFORGE_HOME", str(tmp_path))
        monkeypatch.setenv("HOME", "/definitely/not/this")
        assert resolve_home() == tmp_path

    def test_home_when_no_override(self, monkeypatch, tmp_path):
        monkeypatch.delenv("STYLEFORGE_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        assert resolve_home() == tmp_path

    def test_expanduser_last_resort(self, monkeypatch):
        monkeypatch.delenv("STYLEFORGE_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)
        # 无 HOME 的环境：expanduser 兜底（值为 OS 依赖，只断言不抛错且是绝对形态）
        home = resolve_home()
        assert isinstance(home, Path)

    def test_override_expands_tilde(self, monkeypatch):
        monkeypatch.setenv("STYLEFORGE_HOME", "~")
        assert resolve_home() == Path.home()


class TestReadBytesAsText:
    def test_directory_is_not_a_file(self, tmp_path):
        with pytest.raises(StyleForgeError, match="不是普通文件"):
            read_bytes_as_text(tmp_path)


class TestAtomicWriteCleanupOnReplaceFailure:
    def test_replace_failure_cleans_temp(self, tmp_path, monkeypatch):
        target = tmp_path / "f.txt"
        target.write_text("old", encoding="utf-8")
        real_replace = os.replace

        def failing_replace(src, dst):
            raise OSError("注入：replace 失败")

        monkeypatch.setattr(sf_core.os, "replace", failing_replace)
        with pytest.raises(OSError, match="注入"):
            atomic_write_text(target, "new")
        monkeypatch.setattr(sf_core.os, "replace", real_replace)
        assert target.read_text(encoding="utf-8") == "old"  # 原文件未损
        leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".styleforge-tmp")]
        assert leftovers == []  # 临时文件已清理

    def test_chmod_failure_is_not_fatal(self, tmp_path, monkeypatch):
        def failing_chmod(path, mode):
            raise OSError("注入：chmod 失败")

        monkeypatch.setattr(sf_core.os, "chmod", failing_chmod)
        target = tmp_path / "f.txt"
        atomic_write_text(target, "ok")  # chmod 失败被吞，写入仍成功
        assert target.read_text(encoding="utf-8") == "ok"


class TestDegradedPaths:
    def test_backup_survives_chmod_failure(self, sandbox, monkeypatch):
        settings_path().parent.mkdir(parents=True)
        settings_path().write_text("{}", encoding="utf-8")

        def failing_chmod(path, mode):
            raise OSError("注入")

        monkeypatch.setattr(sf_core.os, "chmod", failing_chmod)
        b = backup_settings("t")
        assert b is not None and b.exists()  # 0600 失败不阻塞备份本身

    def test_list_packs_without_dir(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sf_core, "packs_root", lambda: tmp_path / "nope")
        assert list_packs() == []

    def test_list_backups_without_dir(self, sandbox):
        # 沙箱 home 尚未创建任何 .claude 目录
        assert list_settings_backups() == []


class TestNewlineEdges:
    def test_cr_only_tail(self):
        # 老式 CR 结尾（结尾字符是 \r）：补 \n 形成 \r\n（现状语义，登记在案）
        assert ensure_trailing_newline("a\rb\r") == "a\rb\r\n"
