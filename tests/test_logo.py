import os
import struct

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")

from ui import icons  # noqa: E402
from ui.nav_sidebar import NavSidebar  # noqa: E402
from utils.paths import ASSETS_DIR  # noqa: E402


def test_logo_svg_exists():
    assert os.path.isfile(os.path.join(ASSETS_DIR, "logo.svg"))


def test_icon_png_is_256():
    from PyQt6.QtGui import QImage
    img = QImage(os.path.join(ASSETS_DIR, "icon.png"))
    assert (img.width(), img.height()) == (256, 256)
    assert img.hasAlphaChannel()


def test_icon_ico_has_all_sizes():
    with open(os.path.join(ASSETS_DIR, "icon.ico"), "rb") as f:
        _, kind, count = struct.unpack("<HHH", f.read(6))
        assert kind == 1
        sizes = []
        for _ in range(count):
            w, _h = struct.unpack("<BB", f.read(2))
            f.read(14)
            sizes.append(w or 256)
    assert sizes == [16, 24, 32, 48, 64, 128, 256]


def test_logo_pixmap_is_not_empty(_session_qapplication):
    pm = icons.logo_pixmap(28)
    assert not pm.isNull()
    img = pm.toImage()
    # 原色渲染：中心像素不透明
    assert img.pixelColor(img.width() // 2, img.height() // 2).alpha() == 255


def test_sidebar_logo_has_pixmap(_session_qapplication):
    sb = NavSidebar()
    try:
        assert not sb.logo.pixmap().isNull()
    finally:
        sb.deleteLater()
