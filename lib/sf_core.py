"""styleforge core: cross-platform prompt-pack installer for Claude Code.

Mechanism (verified on Claude Code 2.1.296):

  settings.json -> "outputStyle": "<name>"
  ~/.claude/output-styles/<file>.md   (frontmatter `name:` must match the key)

The style body is injected into the system prompt as a named "Output Style"
section, alongside the built-in tool definitions. Unlike settings.systemPrompt
/ appendSystemPrompt / systemPromptFile / CLAUDE_CODE_SYSTEM_PROMPT — all of
which are accepted but ignored by the harness — outputStyle reaches the system
prompt layer and persists from a single user-scope write. No shell wrapper, no
CLI flag, no launcher migration.

Cross-platform notes:
  - Home resolution honours $HOME on every OS; os.path.expanduser('~') is only
    a fallback because on Windows it reads USERPROFILE and ignores a $HOME set
    by Git Bash / MSYS2.
  - All writes are atomic (temp file + os.replace). settings.json is created
    with 0600 and an existing file keeps its current permissions (TD-CORE-003);
    style files are created 0644.
  - The shell entry points are plain POSIX sh; a .cmd twin covers Windows.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
MANAGED_KEY = "outputStyle"
STYLES_DIRNAME = "output-styles"
PACKS_DIRNAME = "packs"
PRODUCT = "styleforge"

# settings.json keys we manage. Anything else in the file is left untouched.
OWN_KEYS = (MANAGED_KEY,)
BACKUP_SUFFIX = ".styleforge-bak"
TEMP_PREFIX = ".styleforge-tmp-"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


# ------------------------------------------------------------------ errors


class StyleForgeError(Exception):
    """Base error carrying a user-facing message."""


class SettingsCorrupt(StyleForgeError):
    pass


# ------------------------------------------------------------------ paths


def resolve_home() -> Path:
    """$STYLEFORGE_HOME > $HOME (any OS) > expanduser('~').

    Windows: expanduser reads USERPROFILE and would silently ignore a $HOME
    exported by Git Bash / MSYS2, so $HOME wins when present.
    """
    override = os.environ.get("STYLEFORGE_HOME")
    if override:
        return Path(override).expanduser()
    home = os.environ.get("HOME")
    if home:
        return Path(home)
    return Path(os.path.expanduser("~"))


def claude_dir() -> Path:
    return resolve_home() / ".claude"


def styles_dir() -> Path:
    return claude_dir() / STYLES_DIRNAME


def settings_path() -> Path:
    return claude_dir() / "settings.json"


def plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def packs_root() -> Path:
    return plugin_root() / PACKS_DIRNAME


def installed_style_path(name: str) -> Path:
    return styles_dir() / (name + ".md")


# ------------------------------------------------------------------ json io


def load_settings_raw(path: Path | None = None) -> tuple[dict[str, Any], str]:
    """Return (parsed, raw_text). Missing file -> ({}, '')."""
    p = path or settings_path()
    if not p.exists():
        return {}, ""
    raw = p.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SettingsCorrupt(f"{p} 不是合法 JSON ({exc})。请先手动修复，或用 restore 从备份恢复。")
    if not isinstance(data, dict):
        raise SettingsCorrupt(f"{p} 顶层必须是 object。")
    return data, raw


def dump_settings(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def atomic_write_text(path: Path, content: str, mode: int = 0o644) -> None:
    """Write text atomically; never leave a half-written settings file.

    Permissions (TD-CORE-003): an existing target keeps its current mode —
    os.replace would otherwise widen a 0600 settings.json to the temp file's
    mode. `mode` only applies when creating a new file.
    """
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)  # 沿用已有权限
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=TEMP_PREFIX + path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(tmp_path, mode)
        except OSError:
            pass
        os.replace(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def read_bytes_as_text(path: Path) -> str:
    """Read without newline translation.

    Path.read_text() applies universal-newline conversion (CRLF -> LF), which
    would silently alter prompt bytes. The bundled templates ship with CRLF and
    must round-trip byte-exact.
    """
    if not path.exists():
        raise StyleForgeError("文件不存在: " + str(path))
    if not path.is_file():
        raise StyleForgeError("不是普通文件: " + str(path))
    return path.read_bytes().decode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------ backup


def backup_settings(tag: str | None = None) -> Path | None:
    """Timestamped copy of settings.json next to the original."""
    p = settings_path()
    if not p.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = ("-" + tag) if tag else ""
    target = p.with_name(p.name + BACKUP_SUFFIX + "." + ts + label)
    counter = 1
    while target.exists():
        counter += 1
        target = p.with_name(p.name + BACKUP_SUFFIX + "." + ts + label + "." + str(counter))
    target.write_bytes(p.read_bytes())
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target


def list_settings_backups() -> list[Path]:
    p = settings_path()
    if not p.parent.is_dir():
        return []
    prefix = p.name + BACKUP_SUFFIX
    return sorted(x for x in p.parent.glob(prefix + "*") if x.is_file())


# ------------------------------------------------------------------ names

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def normalize_style_name(name: str) -> str:
    """Reject path separators, traversal, and shell-ish names."""
    raw = (name or "").strip()
    if not raw:
        raise StyleForgeError("style 名不能为空")
    if "/" in raw or "\\" in raw or os.sep in raw:
        raise StyleForgeError("style 名不能包含路径分隔符")
    if raw in (".", "..") or ".." in raw:
        raise StyleForgeError("style 名不能包含 '..'")
    if not NAME_RE.fullmatch(raw):
        raise StyleForgeError(
            "style 名只能包含字母、数字、点、下划线和连字符，且须以字母或数字开头"
        )
    return raw


# ------------------------------------------------------------------ packs


def list_packs() -> list[str]:
    root = packs_root()
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))


def pack_dir(pack: str) -> Path:
    if not pack or pack in (".", "..") or "/" in pack or "\\" in pack:
        raise StyleForgeError("非法 pack 名: " + repr(pack))
    d = packs_root() / pack
    if not d.is_dir():
        available = ", ".join(list_packs()) or "(none)"
        raise StyleForgeError(f"未知 pack: {pack}。可用: {available}")
    return d


def read_pack_file(pack: str, filename: str) -> str:
    return read_bytes_as_text(pack_dir(pack) / filename)


# ------------------------------------------------------------------ style body


def ensure_trailing_newline(content: str) -> str:
    if content.endswith("\n"):
        return content
    if content.endswith("\r"):
        return content + "\n"
    if "\r\n" in content:
        return content + "\r\n"
    return content + "\n"


def strip_markdown_h1(content: str) -> str:
    """Drop a leading '# H1' so the body reads as instructions, not a title."""
    lines = content.splitlines()
    if lines and lines[0].lstrip().startswith("# "):
        nl = "\r\n" if "\r\n" in content else "\n"
        body = nl.join(lines[1:])
        return ensure_trailing_newline(body)
    return content


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Split YAML-ish frontmatter (key: value lines) from the body."""
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, content[match.end() :]


def style_frontmatter(name: str, description: str, pack: str) -> str:
    """Frontmatter block. `name` is what settings.json's outputStyle must match."""
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"pack: {pack}\n"
        f"styleforge: {VERSION}\n"
        "---\n\n"
    )


def build_style_body(pack: str) -> str:
    """Concatenate the pack's templates into one style body.

    Order mirrors the original tool: project rules first (system layer), then
    the append prompt (creative-delivery layer).
    """
    rules = strip_markdown_h1(read_pack_file(pack, "claude-project-rules.md"))
    append = strip_markdown_h1(read_pack_file(pack, "claude-append-prompt.md"))
    return ensure_trailing_newline(rules) + "\n" + ensure_trailing_newline(append)


def compose_style_file(name: str, pack: str, description: str = "") -> str:
    body = build_style_body(pack)
    return style_frontmatter(name, description or f"styleforge pack {pack}", pack) + body


# ------------------------------------------------------------------ state


def current_state() -> dict[str, Any]:
    """Read-only view of what is installed right now."""
    settings, _ = load_settings_raw()
    active = settings.get(MANAGED_KEY)
    style_file = installed_style_path(active) if isinstance(active, str) and active else None
    meta: dict[str, str] = {}
    exists = False
    if style_file is not None and style_file.is_file():
        exists = True
        meta, _ = parse_frontmatter(read_bytes_as_text(style_file))
    return {
        "settings_path": str(settings_path()),
        "styles_dir": str(styles_dir()),
        "active_style": active if isinstance(active, str) else None,
        "style_file": str(style_file) if style_file else None,
        "style_file_exists": exists,
        "style_meta": meta,
        "installed": bool(isinstance(active, str) and active and exists),
        "settings_key_count": len(settings),
    }


# ------------------------------------------------------------------ actions


def apply_style(
    name: str, pack: str, description: str = "", backup_tag: str | None = None
) -> dict[str, Any]:
    """Install one style: write the .md, then point settings.json at it."""
    name = normalize_style_name(name)
    pack_dir(pack)  # validate early
    content = compose_style_file(name, pack, description)
    target = installed_style_path(name)

    style_existed = target.exists()
    style_changed = not style_existed or read_bytes_as_text(target) != content

    settings, _ = load_settings_raw()
    settings_changed = settings.get(MANAGED_KEY) != name

    result: dict[str, Any] = {
        "name": name,
        "pack": pack,
        "style_file": str(target),
        "style_bytes": len(content.encode("utf-8")),
        "style_sha256": sha256_bytes(content.encode("utf-8")),
        "style_written": style_changed,
        "settings_changed": settings_changed,
        "backups": [],
    }
    if not style_changed and not settings_changed:
        result["noop"] = True
        return result

    original_style: str | None = read_bytes_as_text(target) if style_existed else None
    atomic_write_text(target, content)
    if settings_changed:
        b = backup_settings(backup_tag)
        if b:
            result["backups"].append(str(b))
        new_settings = dict(settings)
        new_settings[MANAGED_KEY] = name
        try:
            atomic_write_text(settings_path(), dump_settings(new_settings), mode=0o600)
        except BaseException:
            # TD-CLI-003：settings 写失败时回滚本次 style 写入——新建则删除
            # （不留孤儿），覆写则恢复原内容（不留半更新）。补偿是尽力而为：
            # 失败不吞原始错误；此前落盘的 settings 备份保留，restore 仍可用。
            try:
                if original_style is None:
                    target.unlink(missing_ok=True)
                else:
                    atomic_write_text(target, original_style)
            except OSError:
                pass
            raise
    result["noop"] = False
    return result


def remove_style(name: str | None = None, keep_backups: bool = True) -> dict[str, Any]:
    """Uninstall. Defaults to whatever settings.json currently points at."""
    settings, _ = load_settings_raw()
    active = settings.get(MANAGED_KEY)
    target_name = name or (active if isinstance(active, str) else None)

    result: dict[str, Any] = {
        "removed_style": target_name,
        "settings_cleared": False,
        "style_file_removed": False,
        "backups": [],
        "warnings": [],
    }
    if target_name is None and not isinstance(active, str):
        result["noop"] = True
        result["warnings"].append("settings.json 中没有 outputStyle 键，无需卸载")
        return result

    style_file = installed_style_path(target_name) if target_name else None
    file_exists = style_file is not None and style_file.is_file()
    active_present = isinstance(active, str) and bool(active)

    # TD-CORE-001：卸载只做一份统一的卸载前备份（settings.json 快照）。
    # 此前删 style 文件与改 settings 键各备份一次，同秒产生两份相同内容。
    if file_exists or active_present:
        b = backup_settings("uninstall")
        if b:
            result["backups"].append(str(b))

    if style_file is not None and file_exists:
        style_file.unlink()
        result["style_file_removed"] = True
    elif style_file is not None:
        result["warnings"].append(f"style 文件不存在: {style_file}")

    if active_present:
        settings = dict(settings)
        settings.pop(MANAGED_KEY, None)
        atomic_write_text(settings_path(), dump_settings(settings), mode=0o600)
        result["settings_cleared"] = True

    result["noop"] = False
    return result


def restore_settings(backup: Path) -> dict[str, Any]:
    """Point settings.json back at a .styleforge-bak file."""
    backup = Path(backup).expanduser()
    if not backup.exists():
        raise StyleForgeError("备份不存在: " + str(backup))
    raw = backup.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise StyleForgeError(f"备份不是合法 JSON: {exc}")
    if not isinstance(data, dict):
        raise StyleForgeError("备份顶层必须是 object")
    b = backup_settings("pre-restore")
    atomic_write_text(settings_path(), dump_settings(data), mode=0o600)
    return {
        "restored_from": str(backup),
        "safety_backup": str(b) if b else None,
        "restored_bytes": len(raw),
        "keys": len(data),
    }


def preview_style(pack: str) -> str:
    return compose_style_file("<name>", pack)
