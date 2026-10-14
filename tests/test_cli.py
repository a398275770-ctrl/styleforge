"""CLI 冒烟：退出码与 --json 契约（schema styleforge/v1）。"""

from __future__ import annotations

import json
import sys

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


class TestTextMode:
    """文本模式全命令（覆盖各 info/warn 渲染分支）。"""

    def test_install_replace_warning(self, capsys):
        assert main(["install", "--pack", "default"]) == 0
        assert main(["install", "--pack", "default", "--name", "other"]) == 0
        out = capsys.readouterr().out
        assert "将被替换为 other" in out

    def test_install_noop_message(self, capsys):
        main(["install", "--pack", "default"])
        capsys.readouterr()
        assert main(["install", "--pack", "default"]) == 0
        assert "已是最新" in capsys.readouterr().out

    def test_status_without_active_style(self, capsys):
        assert main(["status"]) == 0
        assert "(无)" in capsys.readouterr().out

    def test_uninstall_noop_message(self, capsys):
        assert main(["uninstall"]) == 0
        assert "无需卸载" in capsys.readouterr().out

    def test_backups_packs_preview_text(self, capsys):
        main(["install", "--pack", "default"])
        capsys.readouterr()
        assert main(["backups"]) == 0
        assert "备份目录" in capsys.readouterr().out
        assert main(["packs"]) == 0
        packs_out = capsys.readouterr().out
        assert "default" in packs_out and "claude-project-rules.md" in packs_out
        assert main(["preview", "--pack", "default"]) == 0
        assert "name: <name>" in capsys.readouterr().out

    def test_preview_raw_writes_body_only(self, capsys):
        assert main(["preview", "--pack", "default", "--raw"]) == 0
        out = capsys.readouterr().out
        assert out.startswith("---")  # TD-CLI-004：首行不得是 'preview' 标题泄漏
        assert "name: <name>" in out

    def test_warn_prints_hint_in_text_mode(self, capsys):
        from styleforge import Out

        out = Out(json_mode=False, quiet=False)
        out.warn("注意这条")
        assert "提示: 注意这条" in capsys.readouterr().out

    def test_quiet_suppresses_info(self, capsys):
        assert main(["-q", "status"]) == 0
        assert capsys.readouterr().out == ""


class TestMainExceptionExits:
    def test_keyboard_interrupt_exits_blocked(self, monkeypatch, capsys):
        import styleforge

        def interrupted(args, out):
            raise KeyboardInterrupt

        monkeypatch.setattr(styleforge, "cmd_status", interrupted)
        assert main(["status"]) == EXIT_BLOCKED
        assert "已中断" in capsys.readouterr().err

    def test_broken_pipe_exits_ok(self, monkeypatch, capsys):
        import styleforge

        def piped(args, out):
            raise BrokenPipeError

        # 被测代码会 close stdout（BrokenPipe 的正确处置）；在 capsys 环境下
        # noop 掉 close，避免关掉捕获流污染后续测试。
        monkeypatch.setattr(sys.stdout, "close", lambda: None)
        monkeypatch.setattr(styleforge, "cmd_status", piped)
        assert main(["status"]) == 0

    def test_argparse_usage_error_returns_two(self, capsys):
        capsys.readouterr()
        assert main(["__no_such_command__"]) == 2


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
