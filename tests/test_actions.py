"""install / uninstall / restore / state 全流程（沙箱内）。"""

from __future__ import annotations

import pytest

from sf_core import (
    StyleForgeError,
    apply_style,
    current_state,
    installed_style_path,
    load_settings_raw,
    remove_style,
    restore_settings,
    settings_path,
)


class TestApplyStyle:
    def test_fresh_install(self, sandbox):
        result = apply_style("default", "default", description="d")
        assert result["style_written"] and result["settings_changed"]
        assert result["noop"] is False
        assert installed_style_path("default").is_file()
        settings, _ = load_settings_raw()
        assert settings["outputStyle"] == "default"
        assert result["backups"] == []  # 首装时 settings.json 尚不存在，无备份

    def test_idempotent_noop(self, sandbox):
        apply_style("default", "default")
        second = apply_style("default", "default")
        assert second["noop"] is True
        assert second["style_written"] is False and second["settings_changed"] is False

    def test_reinstall_after_manual_edit_rewrites(self, sandbox):
        apply_style("default", "default")
        installed_style_path("default").write_text("tampered", encoding="utf-8")
        again = apply_style("default", "default")
        assert again["style_written"] is True  # 内容漂移会被纠正

    def test_install_other_name_keeps_old_file(self, sandbox):
        """现状行为：换名安装不删除旧 style 文件（只改 settings 指向）。"""
        apply_style("default", "default")
        apply_style("renamed", "default")
        assert installed_style_path("default").is_file()  # 旧文件留存
        settings, _ = load_settings_raw()
        assert settings["outputStyle"] == "renamed"

    def test_backup_created_when_settings_existed(self, sandbox):
        settings_path().parent.mkdir(parents=True)
        settings_path().write_text('{"other": 1}', encoding="utf-8")
        result = apply_style("default", "default")
        assert len(result["backups"]) == 1
        preserved, _ = load_settings_raw()
        assert preserved["other"] == 1  # 非管理键原样保留

    def test_illegal_name_rejected(self, sandbox):
        with pytest.raises(StyleForgeError):
            apply_style("../evil", "default")


class TestRemoveStyle:
    def test_noop_when_nothing_installed(self, sandbox):
        result = remove_style()
        assert result["noop"] is True
        assert "无需卸载" in result["warnings"][0]

    def test_uninstall_removes_key_and_file(self, sandbox):
        apply_style("default", "default")
        result = remove_style()
        assert result["settings_cleared"] and result["style_file_removed"]
        assert not installed_style_path("default").exists()
        settings, _ = load_settings_raw()
        assert "outputStyle" not in settings
        # TD-CORE-001 已修复：卸载只产生一份统一备份（修复前为 2 份同内容）。
        assert len(result["backups"]) == 1

    def test_missing_style_file_warns(self, sandbox):
        apply_style("default", "default")
        installed_style_path("default").unlink()
        result = remove_style()
        assert result["style_file_removed"] is False
        assert any("不存在" in w for w in result["warnings"])


class TestRestoreSettings:
    def test_restore_roundtrip(self, sandbox):
        apply_style("default", "default")
        backup = settings_path().parent / "manual-bak"
        backup.write_text('{"custom": true}', encoding="utf-8")
        result = restore_settings(backup)
        assert result["keys"] == 1
        settings, _ = load_settings_raw()
        assert settings == {"custom": True}
        assert result["safety_backup"]  # 恢复前自动安全备份

    def test_restore_missing_backup_raises(self, sandbox):
        with pytest.raises(StyleForgeError, match="备份不存在"):
            restore_settings(sandbox / "nope.json")

    def test_restore_corrupt_backup_raises(self, sandbox, tmp_path):
        bad = tmp_path / "bad-bak"
        bad.write_text("{oops", encoding="utf-8")
        with pytest.raises(StyleForgeError, match="不是合法 JSON"):
            restore_settings(bad)

    def test_restore_non_object_raises(self, sandbox, tmp_path):
        bad = tmp_path / "arr-bak"
        bad.write_text("[1]", encoding="utf-8")
        with pytest.raises(StyleForgeError, match="顶层必须是 object"):
            restore_settings(bad)


class TestInstallCompensation:
    """TD-CLI-003：settings 写失败时回滚本次 style 写入（不留孤儿/半更新）。"""

    @staticmethod
    def _fail_settings_write(monkeypatch):
        import sf_core

        real = sf_core.atomic_write_text

        def failing(path, content, mode=0o644):
            if path.name == "settings.json":
                raise OSError("注入：settings 写失败")
            return real(path, content, mode)

        monkeypatch.setattr(sf_core, "atomic_write_text", failing)

    def test_new_style_removed_when_settings_fails(self, sandbox, monkeypatch):
        import sf_core

        self._fail_settings_write(monkeypatch)
        with pytest.raises(OSError, match="注入"):
            sf_core.apply_style("default", "default")
        assert not sf_core.installed_style_path("default").exists()  # 无孤儿文件

    def test_overwritten_style_restored_when_settings_fails(self, sandbox, monkeypatch):
        import sf_core

        sf_core.apply_style("first", "default")
        sf_core.apply_style("second", "default")  # settings -> second
        original_first = sf_core.read_bytes_as_text(sf_core.installed_style_path("first"))
        self._fail_settings_write(monkeypatch)
        # 重装 first（覆写旧文件 + settings 需改回）——settings 阶段失败
        with pytest.raises(OSError, match="注入"):
            sf_core.apply_style("first", "default", description="changed")
        assert sf_core.read_bytes_as_text(sf_core.installed_style_path("first")) == original_first
        settings, _ = sf_core.load_settings_raw()
        assert settings["outputStyle"] == "second"  # settings 未被半改


class TestCurrentState:
    def test_clean_state(self, sandbox):
        state = current_state()
        assert state["installed"] is False
        assert state["active_style"] is None
        assert state["style_meta"] == {}

    def test_installed_state_reads_meta(self, sandbox):
        apply_style("default", "default", description="my desc")
        state = current_state()
        assert state["installed"] is True
        assert state["active_style"] == "default"
        assert state["style_meta"]["pack"] == "default"
        assert state["style_meta"]["description"] == "my desc"

    def test_dangling_pointer_marks_missing(self, sandbox):
        apply_style("default", "default")
        installed_style_path("default").unlink()
        state = current_state()
        assert state["installed"] is False  # settings 有键但文件缺失
        assert state["style_file_exists"] is False
