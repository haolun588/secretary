"""
ui/toast_window.py
螢幕右下角提醒視窗 (Toast Notification Window) - 安全提示音與垃圾回收防護
"""

import sys
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGraphicsOpacityEffect

try:
    import winsound
except ImportError:
    winsound = None

class ToastWindow(QWidget):
    def __init__(self, title="提醒", message="內容", display_time_ms=3000, fade_time_ms=800, parent=None):
        super().__init__(parent)
        self.display_time_ms = display_time_ms
        self.fade_time_ms = fade_time_ms
        self.init_ui(title, message)
        self.play_notification_sound()

    def play_notification_sound(self):
        """播放 Windows 系統訊息音效 (100% 安全不崩潰)"""
        if winsound:
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception as e:
                print(f"[ToastWindow] 音效播放忽略: {e}")

    def init_ui(self, title, message):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True) # 關閉時自動安全釋放資源
        self.setFixedSize(320, 100)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget(self)
        container.setStyleSheet("""
            QWidget {
                background-color: #1c1c24;
                border: 1px solid #8b5cf6;
                border-radius: 14px;
            }
            QLabel#ToastTitle {
                color: #8b5cf6;
                font-size: 15px;
                font-weight: bold;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
            }
            QLabel#ToastMessage {
                color: #ffffff;
                font-size: 12.5px;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
            }
        """)

        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(16, 14, 16, 14)
        c_layout.setSpacing(12)

        icon_lbl = QLabel("💧", container)
        icon_lbl.setStyleSheet("font-size: 26px; border: none; background: transparent;")
        c_layout.addWidget(icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        title_lbl = QLabel(title, container)
        title_lbl.setObjectName("ToastTitle")
        title_lbl.setStyleSheet("border: none; background: transparent;")
        text_layout.addWidget(title_lbl)

        msg_lbl = QLabel(message, container)
        msg_lbl.setObjectName("ToastMessage")
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("border: none; background: transparent;")
        text_layout.addWidget(msg_lbl)

        c_layout.addLayout(text_layout)
        main_layout.addWidget(container)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        self.position_at_bottom_right()

        QTimer.singleShot(self.display_time_ms, self.start_fade_out)

    def position_at_bottom_right(self):
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - 20
            y = geo.bottom() - self.height() - 20
            self.move(x, y)

    def start_fade_out(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(self.fade_time_ms)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.finished.connect(self.close)
        self.anim.start()
