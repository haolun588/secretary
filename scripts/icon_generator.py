"""
scripts/icon_generator.py
生成 Secretary 桌面小助理高畫質圖示檔 (PNG & ICO)
"""

import os
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPainterPath

def create_app_icons():
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(assets_dir, exist_ok=True)

    png_path = os.path.join(assets_dir, "icon.png")
    ico_path = os.path.join(assets_dir, "icon.ico")

    # 繪製 256x256 高畫質圓角矩形暗紫電光圖示
    size = 256
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 1. 漸層紫光背景
    path = QPainterPath()
    path.addRoundedRect(QRectF(8, 8, size - 16, size - 16), 48, 48)
    painter.fillPath(path, QColor("#8b5cf6"))

    # 2. 邊框
    painter.setPen(QColor("#a78bfa"))
    painter.drawPath(path)

    # 3. 白色水滴/閃電標誌
    font = QFont("Segoe UI Emoji", 110, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "⚡")
    painter.end()

    # 儲存 PNG 與 ICO
    pixmap.save(png_path, "PNG")
    try:
        pixmap.save(ico_path, "ICO")
    except Exception as e:
        print(f"ICO 轉檔提示: {e}")

    print(f"[IconGenerator] 已建立桌面與應用程式圖示: {png_path}")
    return png_path, ico_path

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    create_app_icons()
