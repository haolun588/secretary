"""
scripts/icon_generator.py
由 assets/logo.svg 產生應用程式圖示：assets/icon.png（256x256）與多尺寸 assets/icon.ico。
每個 ico 尺寸都各自從 SVG 渲染（不縮放大圖），以 PNG 內嵌方式手寫 ICO 檔。
"""

import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
PNG_SIZE = 256


def render_svg(svg_path, size):
    """把 SVG 渲染成 size x size、透明背景的 QImage。"""
    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        raise RuntimeError(f"無法載入 SVG: {svg_path}")
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()
    return image


def _png_bytes(image):
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buf, "PNG")
    buf.close()
    return bytes(ba)


def build_ico(svg_path, sizes=ICO_SIZES):
    """回傳多尺寸 ICO 的 bytes（PNG 內嵌）。"""
    entries = [(s, _png_bytes(render_svg(svg_path, s))) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    directory = b""
    body = b""
    for size, data in entries:
        dim = 0 if size >= 256 else size  # 0 代表 256
        directory += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        body += data
        offset += len(data)
    return header + directory + body


def list_ico_sizes(ico_path):
    """解析 ICO 檔頭，回傳各 entry 的邊長清單。"""
    with open(ico_path, "rb") as f:
        _, kind, count = struct.unpack("<HHH", f.read(6))
        if kind != 1:
            raise ValueError("不是 ICO 檔")
        sizes = []
        for _ in range(count):
            w, h = struct.unpack("<BB", f.read(2))
            f.read(14)
            sizes.append(w or 256)
    return sizes


def create_app_icons():
    assets_dir = os.path.join(ROOT, "assets")
    svg_path = os.path.join(assets_dir, "logo.svg")
    png_path = os.path.join(assets_dir, "icon.png")
    ico_path = os.path.join(assets_dir, "icon.ico")

    render_svg(svg_path, PNG_SIZE).save(png_path, "PNG")
    with open(ico_path, "wb") as f:
        f.write(build_ico(svg_path))

    print(f"[IconGenerator] 已建立: {png_path}")
    print(f"[IconGenerator] 已建立: {ico_path} 尺寸 {list_ico_sizes(ico_path)}")
    return png_path, ico_path


if __name__ == "__main__":
    app = QApplication(sys.argv)
    create_app_icons()
