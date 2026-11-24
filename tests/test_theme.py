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
             "ACCENT_MUTED", "ACCENT_SOFT", "TEXT_ON_ACCENT", "HOVER", "PRESSED",
             "DANGER_MUTED", "OVERLAY", "DANGER", "DANGER_HOVER", "SUCCESS", "WARNING"]
    for name in names:
        assert COLOR_RE.match(theme.TOKENS[name]), name


def test_priority_keys_and_values():
    assert set(theme.PRIORITY) == {"major", "medium", "minor"}
    for color in theme.PRIORITY.values():
        assert COLOR_RE.match(color)


def test_tokens_dict_contains_numeric_tokens():
    assert theme.TOKENS["SPACE_4"] == 16
    assert theme.TOKENS["FONT_FAMILY"].startswith("'Segoe UI'")


def test_layout_tokens_present_and_int():
    names = ["NAV_WIDTH", "SIDE_PANEL_WIDTH", "WINDOW_W", "WINDOW_H", "WINDOW_MIN_W",
             "WINDOW_MIN_H", "CONTROL_H", "ICON_SM", "ICON_MD", "NAV_BTN", "LEVEL_BAR",
             "TOAST_WIDTH", "DIALOG_WIDTH", "HOUR_HEIGHT", "TIME_GUTTER", "MONTH_CHIP_H"]
    for name in names:
        assert isinstance(theme.TOKENS[name], int), name


def test_font_families_not_in_tokens():
    assert theme.FONT_FAMILIES == ("Segoe UI", "Microsoft JhengHei UI", "Microsoft JhengHei")
    assert "FONT_FAMILIES" not in theme.TOKENS
    assert "PRIORITY_LABEL" not in theme.TOKENS


def test_priority_label_and_window_days():
    assert theme.PRIORITY_LABEL == {"major": "大", "medium": "中", "minor": "小"}
    assert theme.PRIORITY_WINDOW_DAYS == {"major": 30, "medium": 7, "minor": 3}
