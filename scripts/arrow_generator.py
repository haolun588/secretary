"""
scripts/arrow_generator.py
生成 QSpinBox 大尺寸清晰箭頭圖示 (arrow_up.png & arrow_down.png)
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPolygonF

from ui import theme

def generate_arrow_icons():
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(assets_dir, exist_ok=True)

    up_path = os.path.join(assets_dir, "arrow_up.png")
    down_path = os.path.join(assets_dir, "arrow_down.png")

    size = 24

    # 1. 生成向上箭頭 (▲)
    pix_up = QPixmap(size, size)
    pix_up.fill(Qt.GlobalColor.transparent)
    p_up = QPainter(pix_up)
    p_up.setRenderHint(QPainter.RenderHint.Antialiasing)
    p_up.setBrush(QColor(theme.TEXT_PRIMARY))
    p_up.setPen(Qt.PenStyle.NoPen)
    
    triangle_up = QPolygonF([
        QPointF(size / 2.0, 4.0),
        QPointF(4.0, size - 6.0),
        QPointF(size - 4.0, size - 6.0)
    ])
    p_up.drawPolygon(triangle_up)
    p_up.end()
    pix_up.save(up_path, "PNG")

    # 2. 生成向下箭頭 (▼)
    pix_down = QPixmap(size, size)
    pix_down.fill(Qt.GlobalColor.transparent)
    p_down = QPainter(pix_down)
    p_down.setRenderHint(QPainter.RenderHint.Antialiasing)
    p_down.setBrush(QColor(theme.TEXT_PRIMARY))
    p_down.setPen(Qt.PenStyle.NoPen)

    triangle_down = QPolygonF([
        QPointF(4.0, 6.0),
        QPointF(size - 4.0, 6.0),
        QPointF(size / 2.0, size - 4.0)
    ])
    p_down.drawPolygon(triangle_down)
    p_down.end()
    pix_down.save(down_path, "PNG")

    print("[ArrowGenerator] 已成功生成大尺寸清晰箭頭圖示:", up_path, down_path)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    generate_arrow_icons()
