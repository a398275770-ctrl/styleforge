"""命名白名单与 pack 目录校验（安全面回归）。"""

from __future__ import annotations

import pytest
from sf_core import StyleForgeError, normalize_style_name, pack_dir


class TestNormalizeStyleName:
    @pytest.mark.parametrize(
        "name",
        [
            "default",
            "my-style",
            "my_style",
            "my.style",
            "Style2",
            "a",
            "v1.0-beta_1",
        ],
    )
    def test_accepts_valid(self, name):
        assert normalize_style_name(name) == name

    def test_strips_whitespace(self):
        assert normalize_style_name("  default  ") == "default"

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "   ",
            "../escape",
            "a/b",
            "a\\b",
            ".",
            "..",
            "a..b",
            "-leading",
            "has space",
            "sh;rm",
            "na$me",
            "括号名",
            "*",
        ],
    )
    def test_rejects_dangerous_or_invalid(self, name):
        with pytest.raises(StyleForgeError):
            normalize_style_name(name)


class TestPackDir:
    @pytest.mark.parametrize("pack", ["", ".", "..", "a/b", "x\\y"])
    def test_rejects_illegal(self, pack):
        with pytest.raises(StyleForgeError):
            pack_dir(pack)

    def test_unknown_pack_lists_available(self):
        with pytest.raises(StyleForgeError, match="可用"):
            pack_dir("__no_such_pack__")

    def test_default_pack_resolves(self):
        assert pack_dir("default").is_dir()
