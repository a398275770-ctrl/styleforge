"""styleforge CLI: install / status / uninstall / restore / packs / doctor."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

from sf_core import (  # noqa: E402
    VERSION,
    StyleForgeError,
    apply_style,
    current_state,
    list_packs,
    list_settings_backups,
    pack_dir,
    preview_style,
    remove_style,
    restore_settings,
    settings_path,
    styles_dir,
)

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_USAGE = 2


# ------------------------------------------------------------------ output


class Out:
    def __init__(self, json_mode: bool, quiet: bool = False):
        self.json_mode = json_mode
        self.quiet = quiet
        self._payload: dict[str, Any] = {"schema": "styleforge/v1", "version": VERSION}
        self._exit = EXIT_OK

    def set(self, key: str, value: Any) -> None:
        self._payload[key] = value

    def add_action(self, action: str, detail: str, path: Any = None) -> None:
        self._payload.setdefault("actions", []).append(
            {"action": action, "detail": detail, "path": str(path) if path is not None else None}
        )

    def warn(self, message: str) -> None:
        self._payload.setdefault("warnings", []).append(message)
        if not self.json_mode and not self.quiet:
            print("  提示: " + message)

    def error(self, message: str) -> None:
        self._payload.setdefault("errors", []).append(message)
        self._exit = EXIT_BLOCKED

    def fail(self) -> None:
        """Mark the operation as blocked without emitting a message (doctor's checks)."""
        self._exit = EXIT_BLOCKED

    def is_blocked(self) -> bool:
        return self._exit != EXIT_OK

    def info(self, message: str) -> None:
        if not self.json_mode and not self.quiet:
            print(message)

    def header(self, title: str) -> None:
        self._payload["operation"] = title
        if not self.json_mode and not self.quiet:
            print(title)

    def finish(self) -> int:
        if self.json_mode:
            print(json.dumps(self._payload, ensure_ascii=False, indent=2))
        elif not self.quiet and self._exit == EXIT_BLOCKED:
            for e in self._payload.get("errors", []):
                print("错误: " + e, file=sys.stderr)
        return self._exit


# ------------------------------------------------------------------ commands


def cmd_install(args: argparse.Namespace, out: Out) -> int:
    out.header("install")
    name = args.name or args.pack
    out.set("name", name)
    out.set("pack", args.pack)

    state = current_state()
    if state["active_style"] and state["active_style"] != name:
        out.warn(f"当前激活的是 {state['active_style']}，将被替换为 {name}")

    try:
        result = apply_style(name, args.pack, description=args.description)
    except StyleForgeError as exc:
        out.error(str(exc))
        return out.finish()

    out.set("result", result)
    if result.get("noop"):
        out.info(f"  已是最新：{name}（无需改动）")
    else:
        if result["style_written"]:
            out.add_action("write-style", f"写入 output style ({args.pack})", result["style_file"])
        if result["settings_changed"]:
            out.add_action("set-settings", f"settings.json: outputStyle = {name}", settings_path())
        for b in result["backups"]:
            out.add_action("backup", "备份 settings.json", b)
        out.info(f"  已安装 style: {name}  (pack: {args.pack})")
        out.info(f"  style 文件: {result['style_file']}")
        out.info(f"  settings : {settings_path()}")
    out.info("  重启或新开会话后生效。")
    return out.finish()


def cmd_status(args: argparse.Namespace, out: Out) -> int:
    out.header("status")
    state = current_state()
    out.set("state", state)
    out.set("packs", list_packs())

    out.info(f"  settings.json : {state['settings_path']}")
    out.info(f"  styles 目录   : {state['styles_dir']}")
    active = state["active_style"]
    if active:
        mark = "ok" if state["installed"] else "缺失"
        out.info(f"  激活的 style  : {active}  [{mark}]")
        if state["style_meta"]:
            desc = state["style_meta"].get("description")
            pack = state["style_meta"].get("pack")
            if pack:
                out.info(f"  来源 pack     : {pack}")
            if desc:
                out.info(f"  描述          : {desc}")
    else:
        out.info("  激活的 style  : (无)")
    out.info(f"  可用 packs    : {', '.join(list_packs()) or '(none)'}")
    out.info(f"  备份数量      : {len(list_settings_backups())}")
    return out.finish()


def cmd_uninstall(args: argparse.Namespace, out: Out) -> int:
    out.header("uninstall")
    try:
        result = remove_style(name=args.name)
    except StyleForgeError as exc:
        out.error(str(exc))
        return out.finish()

    out.set("result", result)
    if result.get("noop"):
        out.info("  无需卸载：未安装任何 style")
        return out.finish()

    if result["settings_cleared"]:
        out.add_action("clear-settings", "移除 settings.json 的 outputStyle 键", settings_path())
    if result["style_file_removed"]:
        out.add_action("remove-style", f"删除 style 文件 {result['removed_style']}", styles_dir())
    for b in result["backups"]:
        out.add_action("backup", "备份 settings.json", b)
    for w in result.get("warnings", []):
        out.warn(w)
    out.info(f"  已卸载: {result['removed_style']}")
    out.info("  备份已保留（可用 restore 找回）。")
    return out.finish()


def cmd_restore(args: argparse.Namespace, out: Out) -> int:
    out.header("restore")
    try:
        result = restore_settings(Path(args.backup))
    except StyleForgeError as exc:
        out.error(str(exc))
        return out.finish()
    out.set("result", result)
    out.add_action("restore", "从备份恢复 settings.json", result["restored_from"])
    if result.get("safety_backup"):
        out.add_action("backup", "恢复前的安全备份", result["safety_backup"])
    out.info(f"  已恢复 settings.json ({result['restored_bytes']} bytes, {result['keys']} 键)")
    return out.finish()


def cmd_backups(args: argparse.Namespace, out: Out) -> int:
    out.header("backups")
    items = list_settings_backups()
    out.set("backups", [str(x) for x in items])
    out.info(f"  备份目录: {settings_path().parent}")
    for x in items:
        out.info(f"    {x.name}  ({x.stat().st_size} bytes)")
    if not items:
        out.info("    (无)")
    return out.finish()


def cmd_packs(args: argparse.Namespace, out: Out) -> int:
    out.header("packs")
    packs = list_packs()
    out.set("packs", packs)
    for p in packs:
        d = pack_dir(p)
        files = sorted(f.name for f in d.iterdir() if f.is_file())
        out.info(f"  {p}: {', '.join(files)}")
    if not packs:
        out.info("  (无)")
    return out.finish()


def cmd_doctor(args: argparse.Namespace, out: Out) -> int:
    """Check that the mechanism is actually live on this machine."""
    out.header("doctor")
    checks: list[dict[str, Any]] = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": label, "ok": ok, "detail": detail})
        mark = "PASS" if ok else "FAIL"
        line = f"  [{mark}] {label}"
        if detail:
            line += f" — {detail}"
        if not out.json_mode:
            print(line)
        if not ok:
            out.fail()

    home = Path(os.environ.get("STYLEFORGE_HOME") or os.environ.get("HOME") or "~")
    settings = settings_path()
    styles = styles_dir()

    check("home 可解析", str(home) not in ("", "~"), str(home))
    check("settings.json 存在", settings.exists(), str(settings))
    check("output-styles 目录存在或可创建", styles.exists() or styles.parent.exists(), str(styles))

    from sf_core import load_settings_raw

    try:
        data, _ = load_settings_raw()
        check("settings.json 可解析", True, f"{len(data)} 键")
    except StyleForgeError as exc:
        check("settings.json 可解析", False, str(exc))
        data = {}

    active = data.get("outputStyle") if isinstance(data, dict) else None
    if isinstance(active, str) and active:
        f = styles / (active + ".md")
        check("激活的 style 文件存在", f.exists(), str(f))
    else:
        check("未安装 style（install 后可再查）", True)

    packs = list_packs()
    check("存在可用 pack", bool(packs), ", ".join(packs))

    out.set("checks", checks)
    if not out.is_blocked():
        out.info("  一切就绪。")
    return out.finish()


def cmd_preview(args: argparse.Namespace, out: Out) -> int:
    if not args.raw:
        out.header("preview")  # TD-CLI-004：raw 模式直写正文，标题行不得泄漏进重定向
    try:
        body = preview_style(args.pack)
    except StyleForgeError as exc:
        out.error(str(exc))
        return out.finish()
    out.set("preview_bytes", len(body.encode("utf-8")))
    if args.raw:
        sys.stdout.write(body)
    else:
        out.info(body)
    return out.finish()


# ------------------------------------------------------------------ parser


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="styleforge",
        description="Claude Code 持久化提示词注入器（基于 settings.json 的 outputStyle 通道）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s install --pack default
  %(prog)s install --pack mypack --name my-style --description "我的规则"
  %(prog)s status
  %(prog)s doctor
  %(prog)s preview --pack default --raw > /tmp/preview.md
  %(prog)s uninstall
  %(prog)s backups
  %(prog)s restore --backup ~/.claude/settings.json.styleforge-bak.20261014_120000
""",
    )
    p.add_argument("--version", action="version", version=f"{p.prog} {VERSION}")
    p.add_argument("--json", action="store_true", help="输出稳定 JSON（styleforge/v1）")
    p.add_argument("-q", "--quiet", action="store_true", help="仅输出错误")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str, fn):
        sp = sub.add_parser(name, help=help_text)
        sp.set_defaults(func=fn)
        # Mirror the global flags onto each subcommand so both
        # `styleforge -q install` and `styleforge install -q` work.
        # SUPPRESS keeps a value already parsed before the subcommand.
        sp.add_argument(
            "--json",
            action="store_true",
            default=argparse.SUPPRESS,
            help="输出稳定 JSON（styleforge/v1）",
        )
        sp.add_argument(
            "-q", "--quiet", action="store_true", default=argparse.SUPPRESS, help="仅输出错误"
        )
        return sp

    sp = add("install", "安装一个 pack 为激活的 output style", cmd_install)
    sp.add_argument("--pack", default="default", help="pack 目录名（默认 default）")
    sp.add_argument(
        "--name", default=None, help="style 名，须与 frontmatter name 一致（默认等于 pack 名）"
    )
    sp.add_argument("--description", default="", help="style 描述")

    add("status", "查看当前安装状态", cmd_status)
    add("doctor", "检查本机机制是否可用", cmd_doctor)

    sp = add("uninstall", "一键卸载（移除 outputStyle 键与 style 文件）", cmd_uninstall)
    sp.add_argument("--name", default=None, help="指定要卸载的 style（默认当前激活的）")

    sp = add("restore", "从备份恢复 settings.json", cmd_restore)
    sp.add_argument("--backup", required=True, help=".styleforge-bak.* 备份路径")

    add("backups", "列出所有 settings.json 备份", cmd_backups)
    add("packs", "列出可用 pack", cmd_packs)

    sp = add("preview", "预览某个 pack 会写入的内容", cmd_preview)
    sp.add_argument("--pack", default="default")
    sp.add_argument("--raw", action="store_true", help="只输出原始内容（便于重定向）")

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    json_mode = bool(getattr(args, "json", False)) or "--json" in argv
    quiet = bool(getattr(args, "quiet", False))
    out = Out(json_mode, quiet)
    try:
        return args.func(args, out)
    except StyleForgeError as exc:
        out.error(str(exc))
        return out.finish()
    except KeyboardInterrupt:
        out.error("已中断")
        return out.finish()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
