import os
import xml.etree.ElementTree as ET

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui import icons, theme  # noqa: E402
from utils.paths import ASSETS_DIR  # noqa: E402

REQUIRED = ["logo", "calendar", "droplet", "settings", "chevron-left", "chevron-right",
            "chevron-down", "chevron-up", "plus", "refresh", "check", "cloud-off", "alert",
            "map-pin", "clock", "x", "trash", "user", "bell", "log-out", "log-in", "window",
            "power"]


@pytest.fixture(scope="module")
def qapp():
    try:
        return QApplication.instance() or QApplication([])
    except Exception as e:
        pytest.skip(f"無法建立 QApplication: {e}")


def test_colorize_replaces_current_color():
    out = icons.colorize_svg('<svg stroke="currentColor"/>', "#112233")
    assert out == '<svg stroke="#112233"/>'


def test_colorize_without_current_color_unchanged():
    assert icons.colorize_svg("<svg/>", "#112233") == "<svg/>"


def test_colorize_rgba_raises():
    with pytest.raises(ValueError):
        icons.colorize_svg('<svg stroke="currentColor"></svg>', "rgba(255,0,0,0.5)")


def test_export_colored_svg_rejects_rgba():
    with pytest.raises(ValueError):
        icons.export_colored_svg("check", "rgba(255,0,0,0.5)")


def test_pixmap_alpha_color_is_multiplied(qapp):
    # 實心方塊 svg 以外也可：用 x 圖示取最大 alpha，應約等於 0.5 * 255
    pm = icons.pixmap("plus", "rgba(255,255,255,0.5)", 48)
    img = pm.toImage()
    max_alpha = max(img.pixelColor(x, y).alpha() for x in range(img.width()) for y in range(img.height()))
    assert abs(max_alpha - 128) <= 10
    opaque = icons.pixmap("plus", "#ffffff", 48).toImage()
    assert max(opaque.pixelColor(x, y).alpha() for x in range(opaque.width()) for y in range(opaque.height())) >= 250


def test_export_skips_rewrite_when_unchanged_and_recreates(tmp_path):
    path = icons.export_colored_svg("check", theme.SUCCESS)
    mtime = os.stat(path).st_mtime_ns
    assert icons.export_colored_svg("check", theme.SUCCESS) == path
    assert os.stat(path).st_mtime_ns == mtime  # 內容相同不重寫
    os.remove(path)
    assert icons.export_colored_svg("check", theme.SUCCESS) == path
    assert os.path.isfile(path)  # 被清掉時重建
    assert not [f for f in os.listdir(os.path.dirname(path)) if ".tmp" in f]


def test_colorize_invalid_color_raises():
    with pytest.raises(ValueError):
        icons.colorize_svg('<svg stroke="currentColor"/>', "red")


@pytest.mark.parametrize("name", REQUIRED)
def test_icon_file_exists_and_valid_xml(name):
    path = os.path.join(ASSETS_DIR, "icons", f"{name}.svg")
    assert os.path.isfile(path), name
    root = ET.parse(path).getroot()
    assert root.tag.endswith("svg")
    with open(path, encoding="utf-8") as f:
        assert "currentColor" in f.read()


def test_load_svg_missing_returns_empty_svg():
    assert "<svg" in icons.load_svg("no-such-icon")


def test_pixmap_size(qapp):
    pm = icons.pixmap("calendar", theme.TEXT_PRIMARY, theme.ICON_MD)
    assert not pm.isNull()
    assert round(pm.width() / pm.devicePixelRatio()) == theme.ICON_MD


def test_icon_with_active_color(qapp):
    ic = icons.icon("calendar", theme.TEXT_SECONDARY, theme.ICON_MD, active_color=theme.ACCENT)
    assert not ic.isNull()


def test_export_colored_svg_writes_file():
    path = icons.export_colored_svg("check", theme.ACCENT)
    assert "\\" not in path
    assert os.path.isfile(path)
    with open(path, encoding="utf-8") as f:
        assert theme.ACCENT in f.read()


def test_export_switch_svg_writes_file():
    path = icons.export_switch_svg(True, theme.ACCENT, theme.TEXT_ON_ACCENT, theme.ACCENT)
    ET.parse(path)
