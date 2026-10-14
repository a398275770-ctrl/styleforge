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
        # TD-CORE-001（在册 bug）：现状会产生 2 份相同备份；宽松断言现状，
        # 批次 3 修复后收紧为 == 1。
        assert 1 <= len(result["backups"]) <= 2

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
