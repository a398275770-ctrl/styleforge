"""pack 资产指纹：README 登记的 md5/字节数与实际文件一致（TD-PACKS-001）。

改动 pack 内容时必须同步更新 README「文件」节——本测试强制二者不漂移。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
README = (REPO / "README.md").read_text(encoding="utf-8")

# 匹配形如「claude-project-rules.md     770 B  md5 0164424...」的登记行
ENTRY_RE = re.compile(r"([a-z][a-z0-9-]*\.md)\s+(\d+) B\s+md5 ([0-9a-f]{32})")
REGISTERED = {name: (int(size), digest) for name, size, digest in ENTRY_RE.findall(README)}


def test_readme_registry_is_complete():
    """packs/default 每个 .md 都在 README 登记——修复：补登记行（字节数+md5）。"""
    actual = {p.name for p in (REPO / "packs" / "default").glob("*.md")}
    assert actual == set(REGISTERED), (
        f"README 登记与实际 pack 不符: 缺登记 {actual - set(REGISTERED)}, "
        f"多登记 {set(REGISTERED) - actual}"
    )


def test_fingerprints_match():
    """指纹必须与实际字节一致——修复：改了 pack 就同步改 README 的 md5。"""
    for name, (size, digest) in REGISTERED.items():
        data = (REPO / "packs" / "default" / name).read_bytes()
        assert len(data) == size, f"{name}: README 登记 {size} B，实际 {len(data)} B"
        assert hashlib.md5(data).hexdigest() == digest, f"{name}: md5 与 README 登记不符"


def test_pack_templates_are_crlf():
    """默认 pack 保持 CRLF（byte-exact 承诺的前提）。"""
    for name in REGISTERED:
        assert b"\r\n" in (REPO / "packs" / "default" / name).read_bytes(), (
            f"{name}: CRLF 丢失，检查是否被编辑器转换"
        )
