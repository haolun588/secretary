"""
ui/toast_window.py
螢幕右下角提醒視窗（Toast）。樣式由全域 QSS（ui/styles.py 的 _TOAST）負責。

- kind：info / water / danger，決定左側色條與圖示。
- actions：[(label, callable)]；有按鈕時至少顯示 ACTION_MIN_DISPLAY_MS。
- 滑鼠停在上方時暫停倒數與淡出（pause），移開後 RESUME_DELAY_MS 再淡出（resume）。
"""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer
from PyQt6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton,
                             QToolButton, QVBoxLayout, QWidget)

from ui import icons, theme
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import winsound
except ImportError:
    winsound = None

ACTION_MIN_DISPLAY_MS = 8000   # 有操作按鈕時的最短顯示時間
RESUME_DELAY_MS = 2000         # 滑鼠移開後多久開始淡出

# kind -> (圖示名稱, 圖示色)
_KIND_ICON = {
    "info": ("bell", theme.TEXT_SECONDARY),
    "water": ("droplet", theme.ACCENT),
    "danger": ("alert", theme.DANGER),
}


class ToastWindow(QWidget):
    def __init__(self, title="提醒", message="內容", display_time_ms=3000, fade_time_ms=800,
                 parent=None, kind="info", actions=None):
        super().__init__(parent)
        self.kind = kind if kind in _KIND_ICON else "info"
        self.actions = list(actions or [])
        self.display_time_ms = max(display_time_ms, ACTION_MIN_DISPLAY_MS) if self.actions else display_time_ms
        self.fade_time_ms = fade_time_ms
        self.anim = None
        self._paused = False
        self._remaining_ms = 0
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.start_fade_out)
        self.init_ui(title, message)
        self.play_notification_sound()

    def play_notification_sound(self):
        """播放 Windows 系統訊息音效 (100% 安全不崩潰)"""
        if winsound:
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception as e:
                logger.warning(f"音效播放忽略: {e}")

    def init_ui(self, title, message):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)  # 關閉時自動安全釋放資源

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame(self)
        self.card.setObjectName("ToastCard")
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(theme.SPACE_3, theme.SPACE_3, theme.SPACE_3, theme.SPACE_3)
        card_layout.setSpacing(theme.SPACE_3)

        self.bar = QFrame(self.card)
        self.bar.setObjectName("ToastBar")
        self.bar.setProperty("kind", self.kind)
        self.bar.setFixedWidth(theme.LEVEL_BAR)
        card_layout.addWidget(self.bar)

        content = QVBoxLayout()
        content.setSpacing(theme.SPACE_2)

        header = QHBoxLayout()
        header.setSpacing(theme.SPACE_2)
        icon_name, icon_color = _KIND_ICON[self.kind]
        self.icon_label = QLabel(self.card)
        self.icon_label.setPixmap(icons.pixmap(icon_name, icon_color, theme.ICON_MD))
        header.addWidget(self.icon_label)

        self.title_label = QLabel(title, self.card)
        self.title_label.setObjectName("ToastTitle")
        self.title_label.setTextFormat(Qt.TextFormat.PlainText)
        header.addWidget(self.title_label, 1)

        self.close_btn = QToolButton(self.card)
        self.close_btn.setObjectName("ToastClose")
        self.close_btn.setAutoRaise(True)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setIcon(icons.icon("x", theme.TEXT_MUTED, theme.ICON_SM))
        self.close_btn.setIconSize(QSize(theme.ICON_SM, theme.ICON_SM))
        self.close_btn.setToolTip("關閉")
        self.close_btn.clicked.connect(lambda: self.close())
        header.addWidget(self.close_btn)
        content.addLayout(header)

        self.message_label = QLabel(message, self.card)
        self.message_label.setObjectName("ToastMessage")
        self.message_label.setTextFormat(Qt.TextFormat.PlainText)
        self.message_label.setWordWrap(True)
        content.addWidget(self.message_label)

        self.action_buttons = []
        if self.actions:
            action_row = QHBoxLayout()
            action_row.setSpacing(theme.SPACE_2)
            action_row.addStretch(1)
            for label, callback in self.actions:
                btn = QPushButton(label, self.card)
                btn.setProperty("variant", "secondary")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _checked=False, cb=callback: self._on_action(cb))
                action_row.addWidget(btn)
                self.action_buttons.append(btn)
            content.addLayout(action_row)

        card_layout.addLayout(content, 1)
        outer.addWidget(self.card)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        self._fit_size()
        self.position_at_bottom_right()
        self._hide_timer.start(self.display_time_ms)

    def _fit_size(self):
        """寬度固定 TOAST_WIDTH，高度依內容（含自動換行）自適應。"""
        self.setFixedWidth(theme.TOAST_WIDTH)
        self.ensurePolished()
        for child in self.findChildren(QWidget):
            child.ensurePolished()
        layout = self.layout()
        layout.activate()
        height = layout.heightForWidth(theme.TOAST_WIDTH)
        if height <= 0:
            height = self.sizeHint().height()
        self.setFixedHeight(height)

    def position_at_bottom_right(self, stack_offset=0):
        """移到主螢幕右下角；stack_offset 為往上堆疊的像素（多個 toast 同時存在時使用）。"""
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - theme.SPACE_5
            y = geo.bottom() - self.height() - theme.SPACE_5 - stack_offset
            self.move(x, y)

    # ---- 計時 / 淡出 ----

    def _on_action(self, callback):
        self._hide_timer.stop()
        try:
            callback()
        except Exception:
            logger.exception("toast 按鈕動作執行失敗")
        self.close()

    def _on_fade_finished(self):
        if not self._paused:
            self.close()

    def start_fade_out(self):
        if self._paused:
            return
        if self.anim is not None:
            self.anim.stop()
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(self.fade_time_ms)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.finished.connect(self._on_fade_finished)
        self.anim.start()

    def pause(self):
        """暫停倒數與淡出，並恢復完全不透明。"""
        self._paused = True
        remaining = self._hide_timer.remainingTime()
        if remaining > 0:
            self._remaining_ms = remaining
        self._hide_timer.stop()
        if self.anim is not None:
            self.anim.stop()
        self.opacity_effect.setOpacity(1.0)

    def resume(self):
        """重新計時：無按鈕 RESUME_DELAY_MS 後淡出；有按鈕時不短於原本剩餘的顯示時間。"""
        self._paused = False
        delay = RESUME_DELAY_MS
        if self.actions:
            delay = max(RESUME_DELAY_MS, self._remaining_ms)
        self._hide_timer.start(delay)

    def enterEvent(self, event):
        self.pause()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.resume()
        super().leaveEvent(event)


class ToastStack:
    """管理同時存在的 toast：由下而上堆疊在螢幕右下角；toast 銷毀時自動移除並重排。"""

    def __init__(self, gap=theme.SPACE_2):
        self.gap = gap
        self._toasts = []

    @property
    def toasts(self):
        return list(self._toasts)

    def add(self, toast):
        self._toasts.append(toast)
        toast.destroyed.connect(lambda _obj=None, t=toast: self.remove(t))
        self.restack()

    def remove(self, toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
        self.restack()

    def restack(self):
        """依加入順序重新計算位移（最早的在最下方）。"""
        offset = 0
        for toast in list(self._toasts):
            try:
                toast.position_at_bottom_right(offset)
                offset += toast.height() + self.gap
            except RuntimeError:
                self._toasts.remove(toast)  # 底層物件已被釋放
