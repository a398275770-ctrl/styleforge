"""JSON 原子读写 / 备份 / 损坏防护（README「安全性」节的回归面）。"""

from __future__ import annotations

import json

import pytest

from sf_core import (
    StyleForgeError,
    atomic_write_text,
    backup_settings,
    dump_settings,
    list_settings_backups,
    load_settings_raw,
    read_bytes_as_text,
    settings_path,
)


class TestLoadSettingsRaw:
    def test_missing_file_gives_empty(self, sandbox):
        data, raw = load_settings_raw()
        assert data == {} and raw == ""

    def test_valid(self, sandbox):
        settings_path().parent.mkdir(parents=True)
        settings_path().write_text('{"a": 1}', encoding="utf-8")
        data, raw = load_settings_raw()
        assert data == {"a": 1} and raw == '{"a": 1}'

    def test_corrupt_json_refuses(self, sandbox):
        settings_path().parent.mkdir(parents=True)
        settings_path().write_text("{ broken", encoding="utf-8")
        with pytest.raises(StyleForgeError, match="不是合法 JSON"):
            load_settings_raw()

    def test_non_object_toplevel_refuses(self, sandbox):
        settings_path().parent.mkdir(parents=True)
        settings_path().write_text("[1, 2]", encoding="utf-8")
        with pytest.raises(StyleForgeError, match="顶层必须是 object"):
            load_settings_raw()


class TestAtomicWriteText:
    def test_writes_content(self, sandbox, tmp_path):
        target = tmp_path / "nested" / "f.txt"
        atomic_write_text(target, "hello")
        assert target.read_text(encoding="utf-8") == "hello"

    def test_crlf_not_translated(self, tmp_path):
        """写入 newline=''：CRLF 不被翻译（byte-exact 承诺）。"""
        target = tmp_path / "crlf.txt"
        atomic_write_text(target, "a\r\nb\r\n")
        assert target.read_bytes() == b"a\r\nb\r\n"

    def test_failure_leaves_no_temp_file(self, tmp_path):
        target = tmp_path / "sub" / "f.txt"  # sub 不存在且不可创建（造一个文件占位）
        blocker = tmp_path / "sub"
        blocker.write_text("i am a file", encoding="utf-8")
        with pytest.raises(OSError):
            atomic_write_text(target, "x")
        leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".styleforge-tmp")]
        assert leftovers == []

    def test_roundtrip_settings(self, sandbox):
        p = settings_path()
        atomic_write_text(p, dump_settings({"k": "中文", "n": 1}))
        assert json.loads(p.read_text(encoding="utf-8")) == {"k": "中文", "n": 1}


class TestBackup:
    def test_no_settings_no_backup(self, sandbox):
        assert backup_settings() is None

    def test_backup_created_and_listed(self, sandbox):
        p = settings_path()
        p.parent.mkdir(parents=True)
        p.write_text('{"outputStyle": "x"}', encoding="utf-8")
        b = backup_settings("test")
        assert b is not None and b.exists()
        assert b.read_text(encoding="utf-8") == '{"outputStyle": "x"}'
        backups = list_settings_backups()
        assert [x.name for x in backups] == [b.name]

    def test_same_second_no_clobber(self, sandbox):
        p = settings_path()
        p.parent.mkdir(parents=True)
        p.write_text("{}", encoding="utf-8")
        first = backup_settings()
        second = backup_settings()
        assert first is not None and second is not None
        assert first != second and second.exists()

    def test_read_bytes_as_text_keeps_crlf(self, tmp_path):
        f = tmp_path / "x.md"
        f.write_bytes(b"a\r\nb\r\n")
        assert read_bytes_as_text(f) == "a\r\nb\r\n"

    def test_read_missing_raises(self, tmp_path):
        with pytest.raises(StyleForgeError):
            read_bytes_as_text(tmp_path / "nope.md")
