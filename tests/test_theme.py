import re

import pytest

from ui import theme

COLOR_RE = re.compile(r"^(#[0-9a-f]{6}|rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[0-9.]+\s*\))$")


def test_qss_replaces_tokens_and_keeps_braces():
    out = theme.qss("QWidget { background: {BG}; border-radius: {RADIUS_MD}px; }")
    assert out == "QWidget { background: #0f0f14; border-radius: 10px; }"


def test_qss_override():
    assert theme.qss("{ACCENT}", ACCENT="#ffffff") == "#ffffff"


def test_qss_unknown_token_raises():
    with pytest.raises(KeyError):
        theme.qss("color: {NOT_A_TOKEN};")


def test_qss_leaves_lowercase_braces():
    assert theme.qss("a { color: red; }") == "a { color: red; }"


def test_color_tokens_format():
    names = ["BG", "SURFACE_1", "SURFACE_2", "SURFACE_3", "BORDER", "BORDER_STRONG",
             "TEXT_PRIMARY", "TEXT_SECONDARY", "TEXT_MUTED", "ACCENT", "ACCENT_HOVER",
             "ACCENT_MUTED", "DANGER", "SUCCESS", "WARNING"]
    for name in names:
        assert COLOR_RE.match(theme.TOKENS[name]), name


def test_priority_keys_and_values():
    assert set(theme.PRIORITY) == {"major", "medium", "minor"}
    for color in theme.PRIORITY.values():
        assert COLOR_RE.match(color)


def test_tokens_dict_contains_numeric_tokens():
    assert theme.TOKENS["SPACE_4"] == 16
    assert theme.TOKENS["FONT_FAMILY"].startswith("'Segoe UI'")
