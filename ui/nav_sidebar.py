"""
ui/nav_sidebar.py
左側窄版圖示導覽列（寬 theme.NAV_WIDTH）：Logo、日曆、喝水、設定，底部為喝水倒數。
樣式一律來自 ui/styles.py 的 _NAV 區段（QFrame#NavSidebar、QToolButton:checked、NavCountdown）。
"""

import re

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QFrame, QLabel, QToolButton, QVBoxLayout

from ui import icons, theme
from ui.styles import repolish
from utils.logger import get_logger

logger = get_logger(__name__)

PAGE_CALENDAR = 0
PAGE_WATER = 1
PAGE_SETTINGS = 2

_COUNTDOWN_OFF_TEXT = "關"
_COUNTDOWN_OFF_TIP = "喝水提醒已關閉"
_COUNTDOWN_ON_TIP = "距離下次喝水提醒"
_TIME_RE = re.compile(r"(\d+):(\d{2})(?::(\d{2}))?")


def format_countdown(seconds):
    """秒數 -> 'mm:ss'；滿 60 分鐘以上為 'h:mm:ss'；負數視為 0。"""
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _parse_countdown_text(text):
    """從舊格式文字（例如「下次提醒: 08:42 後」）抓出秒數；抓不到回傳 None。"""
    match = _TIME_RE.search(text or "")
    if not match:
        return None
    a, b, c = match.groups()
    if c is None:
        return int(a) * 60 + int(b)
    return int(a) * 3600 + int(b) * 60 + int(c)


class NavSidebar(QFrame):
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(theme.NAV_WIDTH)
        self._countdown_off = None  # 尚未設定；用來只在狀態改變時 repolish
        self._parse_fail_logged = False
        self._build()
        self.set_countdown(None)

    def _make_nav_button(self, icon_name, tooltip):
        btn = QToolButton(self)
        btn.setCheckable(True)
        btn.setAutoRaise(True)
        btn.setIconSize(QSize(theme.ICON_MD, theme.ICON_MD))
        btn.setIcon(icons.icon(icon_name, theme.TEXT_SECONDARY, theme.ICON_MD, active_color=theme.ACCENT))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._group.addButton(btn)
        return btn

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, theme.SPACE_3, 0, theme.SPACE_3)
        layout.setSpacing(theme.SPACE_2)
        align = Qt.AlignmentFlag.AlignHCenter

        self.logo = QLabel(self)
        self.logo.setObjectName("NavLogo")
        logo_size = theme.ICON_MD + theme.SPACE_1
        self.logo.setPixmap(icons.logo_pixmap(logo_size))
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setFixedHeight(theme.NAV_BTN)
        layout.addWidget(self.logo, 0, align)
        layout.addSpacing(theme.SPACE_2)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        self.btn_calendar = self._make_nav_button("calendar", "日曆與行程")
        self.btn_water = self._make_nav_button("droplet", "喝水提醒")
        self.btn_settings = self._make_nav_button("settings", "設定")
        self.btn_calendar.setChecked(True)

        self.btn_calendar.clicked.connect(lambda: self.set_active_page(PAGE_CALENDAR))
        self.btn_water.clicked.connect(lambda: self.set_active_page(PAGE_WATER))
        self.btn_settings.clicked.connect(lambda: self.set_active_page(PAGE_SETTINGS))

        for btn in (self.btn_calendar, self.btn_water, self.btn_settings):
            layout.addWidget(btn, 0, align)

        layout.addStretch(1)

        self.countdown_icon = QLabel(self)
        self.countdown_icon.setPixmap(icons.pixmap("droplet", theme.TEXT_MUTED, theme.ICON_SM))
        self.countdown_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.countdown_icon, 0, align)

        self.countdown_label = QLabel(self)
        self.countdown_label.setObjectName("NavCountdown")
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.countdown_label)

    def set_active_page(self, page_index):
        """切換頁面：更新按鈕選取態並發出 page_changed；只接受 PAGE_CALENDAR / PAGE_WATER / PAGE_SETTINGS。"""
        if page_index == PAGE_CALENDAR:
            btn = self.btn_calendar
        elif page_index == PAGE_WATER:
            btn = self.btn_water
        elif page_index == PAGE_SETTINGS:
            btn = self.btn_settings
        else:
            logger.warning(f"set_active_page 收到無效頁面索引: {page_index!r}，已忽略")
            return
        btn.setChecked(True)
        self.page_changed.emit(page_index)

    def set_countdown(self, seconds):
        """顯示喝水倒數；seconds 為 None 表示提醒已關閉。只有開/關狀態改變時才 repolish 與更新 tooltip。"""
        off = seconds is None
        if off:
            self.countdown_label.setText(_COUNTDOWN_OFF_TEXT)
        else:
            self.countdown_label.setText(format_countdown(seconds))
        if off == self._countdown_off:
            return
        self._countdown_off = off
        self.countdown_label.setProperty("off", "true" if off else "false")
        tip = _COUNTDOWN_OFF_TIP if off else _COUNTDOWN_ON_TIP
        self.countdown_label.setToolTip(tip)
        self.countdown_icon.setToolTip(tip)
        repolish(self.countdown_label)

    def update_countdown(self, text, is_enabled=True):
        """相容舊介面：text 為「下次提醒: mm:ss 後」之類的文字。
        is_enabled=False 顯示關閉態；解析失敗時維持上一次顯示。"""
        if not is_enabled:
            self.set_countdown(None)
            return
        seconds = _parse_countdown_text(text)
        if seconds is None:
            if not self._parse_fail_logged:
                self._parse_fail_logged = True
                logger.debug(f"update_countdown 無法解析倒數文字: {text!r}")
            return
        self.set_countdown(seconds)
