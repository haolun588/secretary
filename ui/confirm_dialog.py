"""
ui/confirm_dialog.py
深色標題列對話框基底（DarkTitleDialog）與通用確認對話框（ConfirmDialog，取消 secondary + 確認 danger）。
"""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ui import icons, theme
from utils.paths import asset_path
from utils.win_titlebar import enable_dark_titlebar


def apply_window_icon(dialog):
    icon_path = asset_path("icon.png")
    if os.path.exists(icon_path):
        dialog.setWindowIcon(QIcon(icon_path))


class DarkTitleDialog(QDialog):
    """第一次顯示時啟用深色標題列的 QDialog 基底。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._titlebar_done = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._titlebar_done:
            self._titlebar_done = True
            enable_dark_titlebar(self)


class ConfirmDialog(DarkTitleDialog):
    """通用確認對話框：警示圖示 + 標題 + 說明，取消（secondary）與確認（danger 實心）。"""

    def __init__(self, window_title, heading, message, detail="", confirm_text="確定", parent=None):
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.setMinimumWidth(theme.CONFIRM_MIN_W)
        apply_window_icon(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.SPACE_5, theme.SPACE_5, theme.SPACE_5, theme.SPACE_4)
        layout.setSpacing(theme.SPACE_2)

        top_row = QHBoxLayout()
        top_row.setSpacing(theme.SPACE_2)
        warn_icon = QLabel(self)
        warn_icon.setPixmap(icons.pixmap("alert", theme.DANGER, theme.ICON_MD))
        top_row.addWidget(warn_icon)
        title_lbl = QLabel(heading, self)
        title_lbl.setProperty("role", "subtitle")
        top_row.addWidget(title_lbl)
        top_row.addStretch(1)
        layout.addLayout(top_row)

        msg_lbl = QLabel(message, self)
        msg_lbl.setTextFormat(Qt.TextFormat.PlainText)
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)

        if detail:
            sub_lbl = QLabel(detail, self)
            sub_lbl.setProperty("role", "secondary")
            sub_lbl.setWordWrap(True)
            layout.addWidget(sub_lbl)

        layout.addSpacing(theme.SPACE_3)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(theme.SPACE_2)
        btn_row.addStretch(1)

        self.cancel_btn = QPushButton("取消", self)
        self.cancel_btn.setProperty("variant", "secondary")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton(confirm_text, self)
        self.confirm_btn.setProperty("variant", "danger")
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.confirm_btn)

        layout.addLayout(btn_row)
