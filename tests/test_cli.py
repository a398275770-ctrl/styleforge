"""CLI 冒烟：退出码与 --json 契约（schema styleforge/v1）。"""

from __future__ import annotations

import json

from styleforge import EXIT_BLOCKED, main


def run(capsys, argv):
    code = main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


class TestSmoke:
    def test_version(self, capsys):
        # main() 捕获 argparse 的 SystemExit 并转为退出码（设计行为）
        assert main(["--version"]) == 0

    def test_install_status_uninstall(self, capsys):
        for argv in (["install", "--pack", "default"], ["status"], ["uninstall"]):
            code, out, err = run(capsys, argv)
            assert code == 0, f"{argv}: {err}"


class TestJsonContract:
    def test_install_json_schema(self, capsys):
        code, out, _ = run(capsys, ["--json", "install", "--pack", "default"])
        assert code == 0
        payload = json.loads(out)
        assert payload["schema"] == "styleforge/v1"
        assert payload["operation"] == "install"
        assert payload["result"]["style_written"] is True

    def test_flags_both_positions(self, capsys):
        assert main(["-q", "install", "--pack", "default"]) == 0
        assert main(["status", "-q"]) == 0


class TestErrors:
    def test_unknown_pack_exits_blocked(self, capsys):
        # 注意：--pack 的值同时充当默认 style 名，须用合法名字才能走到「未知 pack」分支
        code, out, err = run(capsys, ["install", "--pack", "NoSuchPack9"])
        assert code == EXIT_BLOCKED
        assert "NoSuchPack9" in err and "可用" in err

    def test_illegal_name_exits_blocked(self, capsys):
        code, out, err = run(capsys, ["install", "--pack", "default", "--name", "../evil"])
        assert code == EXIT_BLOCKED

    def test_corrupt_settings_exits_blocked(self, capsys, sandbox):
        settings_path = sandbox / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text("{broken", encoding="utf-8")
        code, _, err = run(capsys, ["status"])
        assert code == EXIT_BLOCKED


class TestDoctor:
    def test_doctor_passes_after_install(self, capsys):
        """doctor 的『settings.json 存在』检查要求先有安装——全新沙箱先装再查。"""
        assert main(["install", "--pack", "default"]) == 0
        code, out, err = run(capsys, ["doctor"])
        assert code == 0, err
        assert "PASS" in out

    def test_doctor_json_after_install(self, capsys):
        assert main(["install", "--pack", "default", "-q"]) == 0
        code, out, _ = run(capsys, ["--json", "doctor"])
        assert code == 0
        checks = json.loads(out)["checks"]
        assert all(c["ok"] for c in checks)

    def test_doctor_fails_on_bare_sandbox(self, capsys):
        """未安装任何东西时 doctor 必须红——这是它的本职（机制自检）。"""
        code, out, _ = run(capsys, ["doctor"])
        assert code == EXIT_BLOCKED
        assert "FAIL" in out
