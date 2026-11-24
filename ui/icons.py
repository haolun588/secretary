"""
ui/icons.py
SVG 圖示載入、上色與繪製（圖示為專案自繪，風格參考 Lucide）

svg 檔以 currentColor 描邊。上色一律先換成不透明的 #rrggbb；
若 theme 色帶透明度（rgba 形式），在 pixmap 層以 DestinationIn 乘上 alpha。
"""

import os
import re
import tempfile
from functools import lru_cache

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QIcon, QImage, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

from ui import theme
from utils.logger import get_logger
from utils.paths import asset_path

logger = get_logger(__name__)

_EMPTY_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"></svg>'
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_ALPHA_RE = re.compile(
    r"^rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([0-9.]+)\s*\)$")
_NAME_RE = re.compile(r"^[a-z0-9-]+$")


def _require_hex(color):
    color = color.strip()
    if not _HEX_RE.match(color):
        raise ValueError(f"只接受 #rrggbb 色碼: {color!r}")
    return color.lower()


def _split_alpha(color):
    """把 theme 色拆成 (不透明 #rrggbb, alpha 0~1)；僅供 pixmap / icon 使用。"""
    color = color.strip()
    if _HEX_RE.match(color):
        return color.lower(), 1.0
    m = _ALPHA_RE.match(color)
    if m:
        r, g, b = (min(255, int(m.group(i))) for i in (1, 2, 3))
        alpha = max(0.0, min(1.0, float(m.group(4))))
        return "#{:02x}{:02x}{:02x}".format(r, g, b), alpha
    raise ValueError(f"不支援的顏色格式: {color!r}")


def colorize_svg(svg_text, color):
    """把 currentColor 換成指定的 #rrggbb；非 hex 色碼 raise ValueError。"""
    hex_color = _require_hex(color)
    return svg_text.replace("currentColor", hex_color)


@lru_cache(maxsize=None)
def load_svg(name):
    """讀取 assets/icons/{name}.svg；缺檔時記錄警告並回傳空 SVG。"""
    if not _NAME_RE.match(name or ""):
        logger.warning(f"圖示名稱不合法: {name!r}")
        return _EMPTY_SVG
    path = asset_path(os.path.join("icons", f"{name}.svg"))
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        logger.warning(f"找不到圖示檔: {path}")
        return _EMPTY_SVG


def _device_pixel_ratio():
    screen = QGuiApplication.primaryScreen()
    return float(screen.devicePixelRatio()) if screen is not None else 1.0


@lru_cache(maxsize=512)
def _render(name, color, size, dpr):
    hex_color, alpha = _split_alpha(color)
    svg = colorize_svg(load_svg(name), hex_color)
    px = max(1, int(round(size * dpr)))
    image = QImage(px, px, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    if alpha < 1.0:
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        mask = QColor(0, 0, 0)
        mask.setAlphaF(alpha)
        painter.fillRect(image.rect(), mask)
    painter.end()
    pm = QPixmap.fromImage(image)
    pm.setDevicePixelRatio(dpr)
    return pm


def pixmap(name, color=theme.TEXT_SECONDARY, size=theme.ICON_MD):
    """繪製圖示；邏輯尺寸 size，實際像素依螢幕 devicePixelRatio 放大。color 可為 hex 或帶 alpha 的 theme 色。"""
    return _render(name, color, int(size), _device_pixel_ratio())


@lru_cache(maxsize=16)
def _render_logo(size, dpr):
    px = max(1, int(round(size * dpr)))
    image = QImage(px, px, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(asset_path("logo.svg"))
    if not renderer.isValid():
        logger.warning("找不到或無法解析 assets/logo.svg")
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    pm = QPixmap.fromImage(image)
    pm.setDevicePixelRatio(dpr)
    return pm


def logo_pixmap(size):
    """以原色渲染 assets/logo.svg（品牌 logo，不重新上色）；邏輯尺寸 size，依 devicePixelRatio 放大。"""
    return _render_logo(int(size), _device_pixel_ratio())


def icon(name, color=theme.TEXT_SECONDARY, size=theme.ICON_MD, active_color=None):
    """建立 QIcon；active_color 會加上 Selected / On / Active 狀態的 pixmap。"""
    ic = QIcon()
    ic.addPixmap(pixmap(name, color, size), QIcon.Mode.Normal, QIcon.State.Off)
    ic.addPixmap(pixmap(name, color, size), QIcon.Mode.Active, QIcon.State.Off)
    if active_color:
        active = pixmap(name, active_color, size)
        ic.addPixmap(active, QIcon.Mode.Normal, QIcon.State.On)
        ic.addPixmap(active, QIcon.Mode.Active, QIcon.State.On)
        ic.addPixmap(active, QIcon.Mode.Selected, QIcon.State.Off)
        ic.addPixmap(active, QIcon.Mode.Selected, QIcon.State.On)
    return ic


def clear_caches():
    """清除 SVG 文字與 pixmap 快取（應用程式結束前呼叫，避免 QPixmap 晚於 QApplication 釋放）。"""
    _render.cache_clear()
    _render_logo.cache_clear()
    load_svg.cache_clear()


def _icon_cache_dir():
    out_dir = os.path.join(tempfile.gettempdir(), "secretary_icons")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _write_if_changed(path, content):
    """內容相同就跳過；否則寫暫存檔再 os.replace（避免並行讀到半成品）。"""
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                if f.read() == content:
                    return
        tmp = f"{path}.tmp{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except OSError:
        logger.exception(f"寫入暫存圖示失敗: {path}")


def export_colored_svg(name, color):
    """把上色後的 SVG 寫到暫存資料夾（僅 hex 色碼），回傳可放進 QSS url(...) 的路徑（正斜線）。"""
    hex_color = _require_hex(color)
    path = os.path.join(_icon_cache_dir(), f"{name}_{hex_color[1:]}.svg")
    _write_if_changed(path, colorize_svg(load_svg(name), hex_color))
    return path.replace("\\", "/")


def export_switch_svg(on, track, knob, outline):
    """產生開關（膠囊 + 圓鈕）SVG 寫到暫存資料夾，回傳 QSS 可用路徑；顏色限 #rrggbb。"""
    track_c = _require_hex(track)
    knob_c = _require_hex(knob)
    outline_c = _require_hex(outline)
    w, h = theme.SWITCH_W, theme.ICON_MD
    r = h / 2
    cx = w - r if on else r
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{r - 0.5}" '
        f'fill="{track_c}" stroke="{outline_c}"/>'
        f'<circle cx="{cx}" cy="{r}" r="{r - 3.5}" fill="{knob_c}"/></svg>'
    )
    state = "on" if on else "off"
    path = os.path.join(_icon_cache_dir(), f"switch_{state}_{track_c[1:]}{knob_c[1:]}{outline_c[1:]}.svg")
    _write_if_changed(path, svg)
    return path.replace("\\", "/")
