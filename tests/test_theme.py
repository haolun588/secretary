import re

import pytest

from ui import theme

COLOR_RE = re.compile(r"^(#[0-9a-f]{6}|rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[0-9.]+\s*\))$")


def test_qss_replaces_tokens_and_keeps_braces():
    out = theme.qss("QWidget { background: {BG}; border-radius: {RADIUS_MD}px; }")
    assert out == f"QWidget {{ background: {theme.BG}; border-radius: 10px; }}"


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
             "ACCENT_MUTED", "ACCENT_SOFT", "TEXT_ON_ACCENT", "TEXT_ON_DANGER", "HOVER", "PRESSED",
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


KEYS = {"major", "medium", "minor"}


def test_priority_extra_tables():
    for table in (theme.PRIORITY_BG, theme.PRIORITY_BG_HOVER, theme.PRIORITY_TEXT):
        assert set(table) == KEYS
        for color in table.values():
            assert COLOR_RE.match(color)
    for name in ("PRIORITY_BG", "PRIORITY_BG_HOVER", "PRIORITY_TEXT"):
        assert name not in theme.TOKENS
    assert COLOR_RE.match(theme.TEXT_ON_DANGER)


def _rgb(color):
    if color.startswith("#"):
        return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    nums = re.findall(r"[0-9.]+", color)
    return tuple(int(n) for n in nums[:3])


def _alpha(color):
    return float(re.findall(r"[0-9.]+", color)[3]) if color.startswith("rgba") else 1.0


def _composite(fg, bg):
    a = _alpha(fg)
    return tuple(c * a + b * (1 - a) for c, b in zip(_rgb(fg), _rgb(bg)))


def _luminance(rgb):
    def chan(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    """fg、bg 為 theme 色字串；fg 若半透明則先疊在 bg 上。bg 需為不透明。"""
    f = _composite(fg, bg)
    l1, l2 = _luminance(f), _luminance(_rgb(bg))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def test_contrast_accent_and_danger():
    assert contrast(theme.TEXT_ON_ACCENT, theme.ACCENT) >= 4.5
    assert contrast(theme.TEXT_ON_ACCENT, theme.ACCENT_HOVER) >= 4.5
    assert contrast(theme.TEXT_ON_DANGER, theme.DANGER) >= 3.0


def test_contrast_text_on_surfaces():
    assert contrast(theme.TEXT_PRIMARY, theme.BG) >= 7
    assert contrast(theme.TEXT_SECONDARY, theme.SURFACE_2) >= 4.5


@pytest.mark.parametrize("key", sorted(KEYS))
def test_contrast_priority_text_on_chip(key):
    for table in (theme.PRIORITY_BG, theme.PRIORITY_BG_HOVER):
        chip = _composite(table[key], theme.SURFACE_2)
        chip_hex = "#%02x%02x%02x" % tuple(round(c) for c in chip)
        assert contrast(theme.PRIORITY_TEXT[key], chip_hex) >= 4.5
