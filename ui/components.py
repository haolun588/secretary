"""
ui/components.py
共用 UI 元件：IconButton、SegmentedControl、SyncStatusBadge、LevelDot 與相關純函式
"""

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QToolButton, QWidget

from ui import icons, theme
from ui.styles import qcolor, repolish
from utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_PRIORITY = "medium"

# state -> (顯示文字, 圖示名稱, tone)
_SYNC_PRESENTATION = {
    "idle": ("未連線", "cloud-off", "neutral"),
    "authorizing": ("授權中", "refresh", "busy"),
    "syncing": ("同步中", "refresh", "busy"),
    "ok": ("已同步", "check", "ok"),
    "offline": ("離線", "cloud-off", "neutral"),
    "error": ("同步錯誤", "alert", "error"),
}
_TONE_ICON_COLOR = {
    "neutral": theme.TEXT_MUTED,
    "busy": theme.ACCENT,
    "ok": theme.SUCCESS,
    "error": theme.DANGER,
}


def level_color(priority):
    """行程等級對應的色碼；未知等級視為 medium。"""
    return theme.PRIORITY.get(priority, theme.PRIORITY[_DEFAULT_PRIORITY])


def level_bg(priority, hovered=False):
    """行程格子整格底色（半透明 rgba）；未知等級視為 medium。"""
    table = theme.PRIORITY_BG_HOVER if hovered else theme.PRIORITY_BG
    return table.get(priority, table[_DEFAULT_PRIORITY])


def level_text(priority):
    """行程格子文字色；未知等級視為 medium。"""
    return theme.PRIORITY_TEXT.get(priority, theme.PRIORITY_TEXT[_DEFAULT_PRIORITY])


def sync_state_presentation(state):
    """同步狀態 -> (顯示文字, 圖示名稱, tone)；未知狀態退回 idle 的呈現。"""
    return _SYNC_PRESENTATION.get(state, _SYNC_PRESENTATION["idle"])


class IconButton(QToolButton):
    """純圖示按鈕；hover 底色由全域 QSS（#IconButton）負責。"""

    def __init__(self, icon_name, tooltip="", size=theme.ICON_MD,
                 color=theme.TEXT_SECONDARY, active_color=None, parent=None):
        super().__init__(parent)
        self.setObjectName("IconButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(size, size))
        self.setAutoRaise(True)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.set_icon_name(icon_name, color, size, active_color)
        if tooltip:
            self.setToolTip(tooltip)

    def set_icon_name(self, icon_name, color=theme.TEXT_SECONDARY, size=None, active_color=None):
        size = size or self.iconSize().width()
        self.setIcon(icons.icon(icon_name, color, size, active_color))


class SegmentedControl(QWidget):
    """分段選擇器。options 為 [(key, label), ...]；使用者點擊切換時發出 changed(key)。
    set_current() 為程式設定，不發出 changed。"""

    changed = pyqtSignal(str)

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.setObjectName("Segmented")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._buttons = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.SPACE_1, theme.SPACE_1, theme.SPACE_1, theme.SPACE_1)
        layout.setSpacing(theme.SPACE_1)
        for key, label in options:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, k=key: self._on_clicked(k))
            self._group.addButton(btn)
            layout.addWidget(btn)
            self._buttons[key] = btn
        self._current = None
        if options:
            self.set_current(options[0][0])

    def _on_clicked(self, key):
        if key != self._current:
            self._current = key
            self.changed.emit(key)

    def set_current(self, key):
        btn = self._buttons.get(key)
        if btn is None:
            logger.warning(f"SegmentedControl 沒有選項: {key!r}")
            return
        btn.setChecked(True)
        self._current = key

    def current(self):
        return self._current

    def keys(self):
        return list(self._buttons)


class SyncStatusBadge(QPushButton):
    """同步狀態徽章；只有圖示帶語意色，文字維持次要色。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SyncBadge")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(theme.ICON_SM, theme.ICON_SM))
        self._state = "idle"
        self.set_state("idle", "")

    def state(self):
        return self._state

    def set_state(self, state, message=""):
        label, icon_name, tone = sync_state_presentation(state)
        self._state = state if state in _SYNC_PRESENTATION else "idle"
        self.setText(label)
        self.setIcon(icons.icon(icon_name, _TONE_ICON_COLOR[tone], theme.ICON_SM))
        self.setToolTip(message or label)
        self.setProperty("tone", tone)
        repolish(self)


class LevelDot(QWidget):
    """行程等級色點。"""

    def __init__(self, priority="medium", size=theme.SPACE_2, parent=None):
        super().__init__(parent)
        self._size = size
        self._priority = priority
        self.setFixedSize(size, size)

    def set_priority(self, priority):
        self._priority = priority
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor(level_color(self._priority)))
        painter.drawEllipse(0, 0, self._size, self._size)
        painter.end()
