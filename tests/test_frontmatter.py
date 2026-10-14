"""frontmatter / 正文组装（含 CRLF 字节保真回归——README 的 byte-exact 承诺）。"""

from __future__ import annotations

from sf_core import (
    compose_style_file,
    ensure_trailing_newline,
    parse_frontmatter,
    preview_style,
    strip_markdown_h1,
    style_frontmatter,
)


class TestParseFrontmatter:
    def test_no_frontmatter(self):
        meta, body = parse_frontmatter("just body\n")
        assert meta == {}
        assert body == "just body\n"

    def test_simple(self):
        content = "---\nname: default\ndescription: hello\n---\n\nbody"
        meta, body = parse_frontmatter(content)
        assert meta == {"name": "default", "description": "hello"}
        assert body == "body"  # 结束符后的空白（含空行）被正则一并吃掉（现状行为）

    def test_quotes_stripped(self):
        meta, _ = parse_frontmatter("---\nname: \"q\"\npack: 'p'\n---\nx")
        assert meta == {"name": "q", "pack": "p"}

    def test_line_without_colon_ignored(self):
        meta, _ = parse_frontmatter("---\nname: x\nnoise line\n---\nx")
        assert meta == {"name": "x"}


class TestStripH1:
    def test_strips_leading_h1(self):
        out = strip_markdown_h1("# Title\nbody line\n")
        assert out == "body line\n"

    def test_keeps_when_not_h1(self):
        assert strip_markdown_h1("## Not h1\n") == "## Not h1\n"


class TestNewline:
    def test_plain(self):
        assert ensure_trailing_newline("a") == "a\n"

    def test_already(self):
        assert ensure_trailing_newline("a\n") == "a\n"

    def test_crlf_content_gets_crlf(self):
        assert ensure_trailing_newline("a\r\nb") == "a\r\nb\r\n"


class TestCompose:
    def test_frontmatter_contains_name_and_pack(self):
        fm = style_frontmatter("nm", "desc", "pk")
        assert "name: nm" in fm and "pack: pk" in fm

    def test_compose_is_crlf_byte_safe(self):
        """packs/default 模板是 CRLF；组装不得翻译换行（README 承诺 byte-exact）。"""
        composed = compose_style_file("default", "default")
        assert "\r\n" in composed  # 原始 CRLF 存活
        composed.encode("utf-8")  # 可编码

    def test_preview_uses_placeholder_name(self):
        assert "name: <name>" in preview_style("default")
