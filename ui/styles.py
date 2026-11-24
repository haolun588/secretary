"""
ui/styles.py
全域樣式：色彩轉換、重新套用樣式、全域 QSS（依元件分段，全部由 theme token 組成）

選擇器慣例：
- 按鈕以動態屬性 variant 區分：primary / secondary / ghost / danger（danger 加 soft="true" 為淡底版）
- 語意 label 以動態屬性 role：title / subtitle / body / secondary / muted / section / error / field
- 容器以 objectName：NavSidebar、Toolbar、Segmented、SyncBadge、SidePanel、SettingsRow、ToastCard ...
- 變更動態屬性後呼叫 repolish(widget)
"""

import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPalette

from ui import theme
from ui.icons import clear_caches, export_colored_svg, export_switch_svg
from utils.logger import get_logger

logger = get_logger(__name__)

_HEX_RE = re.compile(r"^#([0-9a-fA-F]{6})$")
_RGBA_RE = re.compile(
    r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([0-9.]+)\s*)?\)$")


def qcolor(value):
    """把 theme 色字串（#rrggbb 或 rgba(r,g,b,a)，a 為 0~1）轉成 QColor。"""
    text = str(value).strip()
    m = _HEX_RE.match(text)
    if m:
        return QColor("#" + m.group(1))
    m = _RGBA_RE.match(text)
    if m:
        r, g, b = (min(255, int(m.group(i))) for i in (1, 2, 3))
        alpha = float(m.group(4)) if m.group(4) is not None else 1.0
        color = QColor(r, g, b)
        color.setAlphaF(max(0.0, min(1.0, alpha)))
        return color
    raise ValueError(f"不支援的顏色格式: {value!r}")


def make_font(size=theme.FONT_SM, weight=theme.WEIGHT_REGULAR):
    """依 theme token 建立 QFont（給自訂 QPainter 元件用）。weight 只接受 400 / 600。"""
    font = QFont()
    font.setFamilies(list(theme.FONT_FAMILIES))
    font.setPixelSize(size)
    font.setWeight(QFont.Weight.DemiBold if weight >= theme.WEIGHT_SEMIBOLD else QFont.Weight.Normal)
    return font


def fit_text(metrics, text, width):
    """單行文字配合寬度：放得下原文或能顯示部分字 + 省略號就用 elide 結果；
    窄到只剩省略號時改回傳原文，由呼叫端以 setClipRect 裁切，至少露出前 1–2 個字。"""
    elided = metrics.elidedText(text, Qt.TextElideMode.ElideRight, max(0, width))
    if text and not elided.replace("…", ""):
        return text
    return elided


def repolish(widget):
    """動態屬性變更後重新套用樣式。"""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


_BASE = """
QWidget {
    color: {TEXT_PRIMARY};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SM}px;
    font-weight: {WEIGHT_REGULAR};
}
QMainWindow { background: {BG}; }
QStackedWidget { background: {BG}; }
QLabel { background: transparent; }
QLabel[role="title"] { font-size: {FONT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; }
QLabel[role="subtitle"] { font-size: {FONT_MD}px; font-weight: {WEIGHT_SEMIBOLD}; }
QLabel[role="body"] { font-size: {FONT_SM}px; }
QLabel[role="secondary"] { color: {TEXT_SECONDARY}; }
QLabel[role="muted"] { color: {TEXT_MUTED}; font-size: {FONT_XS}px; }
QLabel[role="section"] {
    color: {TEXT_MUTED};
    font-size: {FONT_XS}px;
    font-weight: {WEIGHT_SEMIBOLD};
    padding-top: {SPACE_2}px;
}
QLabel[role="error"] { color: {DANGER}; }
QFrame[role="divider"] { background: {BORDER}; border: none; max-height: 1px; min-height: 1px; }
"""

_BUTTONS = """
QPushButton {
    min-height: {CONTROL_H}px;
    max-height: {CONTROL_H}px;
    padding: 0 {SPACE_4}px;
    border-radius: {RADIUS_SM}px;
    border: 1px solid {BORDER_STRONG};
    background: {SURFACE_2};
    color: {TEXT_PRIMARY};
    font-weight: {WEIGHT_SEMIBOLD};
}
QPushButton:hover { background: {SURFACE_3}; }
QPushButton:pressed { background: {BORDER}; }
QPushButton:disabled { color: {TEXT_MUTED}; background: {SURFACE_1}; border-color: {BORDER}; }
QPushButton:focus { border-color: {ACCENT}; }

QPushButton[variant="primary"] {
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: {TEXT_ON_ACCENT};
}
QPushButton[variant="primary"]:hover { background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }
QPushButton[variant="primary"]:pressed { background: {ACCENT_HOVER}; }
QPushButton[variant="primary"]:disabled { background: {ACCENT_MUTED}; border-color: transparent; color: {TEXT_MUTED}; }

QPushButton[variant="secondary"] {
    background: transparent;
    border: 1px solid {BORDER_STRONG};
    color: {TEXT_PRIMARY};
}
QPushButton[variant="secondary"]:hover { background: {HOVER}; border-color: {TEXT_MUTED}; }
QPushButton[variant="secondary"]:pressed { background: {PRESSED}; }

QPushButton[variant="ghost"] {
    background: transparent;
    border: 1px solid transparent;
    color: {TEXT_SECONDARY};
}
QPushButton[variant="ghost"]:hover { background: {HOVER}; color: {TEXT_PRIMARY}; }
QPushButton[variant="ghost"]:pressed { background: {PRESSED}; }

QPushButton[variant="danger"] {
    background: {DANGER};
    border: 1px solid {DANGER};
    color: {TEXT_ON_DANGER};
}
QPushButton[variant="danger"]:hover { background: {DANGER_HOVER}; border-color: {DANGER_HOVER}; }
QPushButton[variant="danger"]:disabled { background: {DANGER_MUTED}; border-color: transparent; color: {TEXT_MUTED}; }
QPushButton[variant="danger"][soft="true"] {
    background: transparent;
    border: 1px solid transparent;
    color: {DANGER};
}
QPushButton[variant="danger"][soft="true"]:hover { background: {DANGER_MUTED}; }
QPushButton[variant="danger"][soft="true"]:pressed { background: {DANGER_MUTED}; }

QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: {RADIUS_SM}px;
    padding: {SPACE_1}px;
    color: {TEXT_SECONDARY};
}
QToolButton:hover { background: {HOVER}; }
QToolButton:pressed { background: {PRESSED}; }
QToolButton:disabled { color: {TEXT_MUTED}; }
QToolButton#IconButton {
    min-width: {CONTROL_H}px;
    max-width: {CONTROL_H}px;
    min-height: {CONTROL_H}px;
    max-height: {CONTROL_H}px;
    padding: 0;
}
QToolButton#IconButton:focus { border-color: {ACCENT}; }
"""

_INPUTS = """
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QDateEdit, QComboBox {
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 0 {SPACE_3}px;
    min-height: {CONTROL_H}px;
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT};
    selection-color: {TEXT_ON_ACCENT};
}
QTextEdit, QPlainTextEdit { padding: {SPACE_2}px {SPACE_3}px; min-height: 0; }
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QTimeEdit:hover, QDateEdit:hover, QComboBox:hover { border-color: {BORDER_STRONG}; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QTimeEdit:focus, QDateEdit:focus, QComboBox:focus, QComboBox:on { border: 1px solid {ACCENT}; }
QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QTimeEdit:disabled, QComboBox:disabled {
    color: {TEXT_MUTED}; background: {SURFACE_1};
}
QLineEdit[invalid="true"], QTextEdit[invalid="true"] { border: 1px solid {DANGER}; }

QComboBox { padding-right: {SPACE_5}px; }
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: {SPACE_5}px;
    border: none;
}
QComboBox::down-arrow { image: url({ICON_CHEVRON_DOWN}); width: {ICON_SM}px; height: {ICON_SM}px; }
QComboBox QAbstractItemView {
    background: {SURFACE_2};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS_SM}px;
    padding: {SPACE_1}px;
    outline: none;
    selection-background-color: {ACCENT_MUTED};
    selection-color: {TEXT_PRIMARY};
}
QComboBox QAbstractItemView::item {
    min-height: {CONTROL_H}px;
    padding: 0 {SPACE_2}px;
    border-radius: {RADIUS_SM}px;
}
QComboBox QAbstractItemView::item:hover { background: {HOVER}; }

QSpinBox, QDoubleSpinBox, QTimeEdit, QDateEdit { padding-right: {SPACE_5}px; }
QSpinBox::up-button, QDoubleSpinBox::up-button, QTimeEdit::up-button, QDateEdit::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: {SPACE_5}px;
    border: none;
    background: transparent;
}
QSpinBox::down-button, QDoubleSpinBox::down-button, QTimeEdit::down-button, QDateEdit::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: {SPACE_5}px;
    border: none;
    background: transparent;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QTimeEdit::up-arrow, QDateEdit::up-arrow {
    image: url({ICON_CHEVRON_UP}); width: {SPACE_3}px; height: {SPACE_3}px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QTimeEdit::down-arrow, QDateEdit::down-arrow {
    image: url({ICON_CHEVRON_DOWN}); width: {SPACE_3}px; height: {SPACE_3}px;
}

QCalendarWidget QWidget { background: {SURFACE_2}; color: {TEXT_PRIMARY}; }
QCalendarWidget QToolButton { color: {TEXT_PRIMARY}; font-weight: {WEIGHT_SEMIBOLD}; padding: {SPACE_1}px {SPACE_2}px; }
QCalendarWidget QAbstractItemView {
    background: {SURFACE_2};
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT};
    selection-color: {TEXT_ON_ACCENT};
    outline: none;
}
QCalendarWidget QAbstractItemView:disabled { color: {TEXT_MUTED}; }
"""

_CHECK_SWITCH = """
QCheckBox { spacing: {SPACE_2}px; background: transparent; }
QCheckBox::indicator {
    width: {ICON_SM}px;
    height: {ICON_SM}px;
    border-radius: {RADIUS_SM}px;
    border: 1px solid {BORDER_STRONG};
    background: {SURFACE_2};
}
QCheckBox::indicator:hover { border-color: {ACCENT}; }
QCheckBox::indicator:checked { background: {ACCENT}; border-color: {ACCENT}; image: url({ICON_CHECK}); }
QCheckBox::indicator:disabled { background: {SURFACE_1}; border-color: {BORDER}; }

QCheckBox[variant="switch"]::indicator {
    width: {SWITCH_W}px;
    height: {ICON_MD}px;
    border: none;
    border-radius: 0;
    background: transparent;
    image: url({SWITCH_OFF});
}
QCheckBox[variant="switch"]::indicator:checked { image: url({SWITCH_ON}); background: transparent; border: none; }
QCheckBox[variant="switch"]::indicator:disabled { image: url({SWITCH_OFF}); }
QCheckBox[variant="switch"]::indicator:checked:disabled { image: url({SWITCH_ON}); }

QRadioButton { spacing: {SPACE_2}px; }
"""

_MENU = """
QMenu {
    background: {SURFACE_2};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS_MD}px;
    padding: {SPACE_1}px;
}
QMenu::item {
    padding: {SPACE_2}px {SPACE_4}px {SPACE_2}px {SPACE_3}px;
    border-radius: {RADIUS_SM}px;
    color: {TEXT_PRIMARY};
}
QMenu::item:selected { background: {ACCENT_MUTED}; }
QMenu::item:disabled { color: {TEXT_MUTED}; }
QMenu::icon { padding-left: {SPACE_2}px; }
QMenu::separator { height: 1px; background: {BORDER}; margin: {SPACE_1}px {SPACE_2}px; }
"""

_SCROLLBAR = """
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: {SPACE_3}px; margin: 0; }
QScrollBar::handle:vertical { background: {BORDER_STRONG}; border-radius: {RADIUS_SM}px; margin: 0 {SPACE_1}px; min-height: {SPACE_6}px; }
QScrollBar::handle:vertical:hover { background: {TEXT_MUTED}; }
QScrollBar:horizontal { background: transparent; height: {SPACE_3}px; margin: 0; }
QScrollBar::handle:horizontal { background: {BORDER_STRONG}; border-radius: {RADIUS_SM}px; margin: {SPACE_1}px 0; min-width: {SPACE_6}px; }
QScrollBar::handle:horizontal:hover { background: {TEXT_MUTED}; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; background: none; border: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""

_TOOLTIP = """
QToolTip {
    background: {SURFACE_3};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS_SM}px;
    padding: {SPACE_1}px {SPACE_2}px;
    font-size: {FONT_XS}px;
}
"""

_NAV = """
QFrame#NavSidebar { background: {SURFACE_1}; border: none; border-right: 1px solid {BORDER}; }
QFrame#NavSidebar QToolButton {
    min-width: {NAV_BTN}px;
    max-width: {NAV_BTN}px;
    min-height: {NAV_BTN}px;
    max-height: {NAV_BTN}px;
    padding: 0;
    border-radius: {RADIUS_MD}px;
    background: transparent;
    border: none;
}
QFrame#NavSidebar QToolButton:hover { background: {HOVER}; }
QFrame#NavSidebar QToolButton:checked { background: {ACCENT_MUTED}; }
QLabel#NavCountdown { color: {TEXT_SECONDARY}; font-size: {FONT_XS}px; }
QLabel#NavCountdown[off="true"] { color: {TEXT_MUTED}; }
QLabel#NavLogo { background: transparent; }
"""

_TOOLBAR = """
QFrame#Toolbar { background: transparent; border: none; border-bottom: 1px solid {BORDER}; }
QLabel#ToolbarTitle { font-size: {FONT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; }
"""

_SEGMENTED = """
QWidget#Segmented {
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_MD}px;
}
QWidget#Segmented QPushButton {
    min-height: {SPACE_5}px;
    max-height: {SPACE_5}px;
    padding: 0 {SPACE_3}px;
    border: none;
    border-radius: {RADIUS_SM}px;
    background: transparent;
    color: {TEXT_SECONDARY};
    font-weight: {WEIGHT_REGULAR};
}
QWidget#Segmented QPushButton:hover { color: {TEXT_PRIMARY}; background: {HOVER}; }
QWidget#Segmented QPushButton:checked {
    background: {SURFACE_3};
    color: {TEXT_PRIMARY};
    font-weight: {WEIGHT_SEMIBOLD};
}
"""

_SYNC_BADGE = """
QPushButton#SyncBadge {
    min-height: {CONTROL_H}px;
    padding: 0 {SPACE_3}px;
    border-radius: {RADIUS_SM}px;
    border: 1px solid transparent;
    background: transparent;
    color: {TEXT_SECONDARY};
    font-weight: {WEIGHT_REGULAR};
}
QPushButton#SyncBadge:hover { background: {HOVER}; }
QPushButton#SyncBadge[tone="error"] { color: {TEXT_PRIMARY}; }
QPushButton#SyncBadge[tone="busy"] { color: {TEXT_PRIMARY}; }
QPushButton#SyncBadge[tone="ok"] { color: {TEXT_SECONDARY}; }
QPushButton#SyncBadge[tone="neutral"] { color: {TEXT_SECONDARY}; }
"""

_PANEL = """
QFrame#SidePanel { background: {SURFACE_1}; border: none; border-left: 1px solid {BORDER}; }
QFrame#SidePanel QLabel[role="section"] { padding-top: {SPACE_3}px; }
QFrame#PanelRow { background: transparent; border-radius: {RADIUS_SM}px; border: none; }
QFrame#PanelRow:hover { background: {HOVER}; }
QFrame#LevelBar { border: none; border-radius: 0; }
QFrame#CalendarSurface { background: {BG}; border: none; }
"""

_DIALOG = """
QDialog { background: {SURFACE_1}; }
QMessageBox { background: {SURFACE_1}; }
QMessageBox QLabel { color: {TEXT_PRIMARY}; font-size: {FONT_SM}px; }
QDialog QLabel[role="field"] { color: {TEXT_SECONDARY}; font-size: {FONT_XS}px; }
QDialog#DatePopup { background: {SURFACE_2}; border: 1px solid {BORDER_STRONG}; }
QFrame#DialogFooter { background: transparent; border: none; border-top: 1px solid {BORDER}; }
QPushButton#DatePopupButton { text-align: left; font-weight: {WEIGHT_REGULAR}; background: {SURFACE_2}; border: 1px solid {BORDER}; }
QPushButton#DatePopupButton:hover { border-color: {BORDER_STRONG}; }
"""

_SETTINGS = """
QWidget#SettingsPage { background: {BG}; }
QFrame#SettingsGroup {
    background: {SURFACE_1};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_MD}px;
}
QFrame#SettingsRow { background: transparent; border: none; border-bottom: 1px solid {BORDER}; }
QFrame#SettingsRow[last="true"] { border-bottom: none; }
QLabel#SettingsRowTitle { font-size: {FONT_SM}px; font-weight: {WEIGHT_SEMIBOLD}; }
QLabel#SettingsRowDesc { font-size: {FONT_XS}px; color: {TEXT_SECONDARY}; }
QLabel#AccountStatus { font-size: {FONT_XS}px; color: {TEXT_SECONDARY}; }
QLabel#AccountStatus[state="ok"] { color: {SUCCESS}; }
QLabel#AccountStatus[state="error"] { color: {DANGER}; }
"""

_TOAST = """
QFrame#ToastCard {
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_LG}px;
}
QFrame#ToastBar { border: none; border-radius: 0; background: {BORDER_STRONG}; }
QFrame#ToastBar[kind="water"] { background: {ACCENT}; }
QFrame#ToastBar[kind="danger"] { background: {DANGER}; }
QFrame#ToastBar[kind="info"] { background: {BORDER_STRONG}; }
QLabel#ToastTitle { font-size: {FONT_SM}px; font-weight: {WEIGHT_SEMIBOLD}; }
QLabel#ToastMessage { font-size: {FONT_SM}px; color: {TEXT_SECONDARY}; }
QToolButton#ToastClose {
    min-width: {ICON_MD}px;
    max-width: {ICON_MD}px;
    min-height: {ICON_MD}px;
    max-height: {ICON_MD}px;
    padding: 0;
}
"""

_SECTIONS = (_BASE, _BUTTONS, _INPUTS, _CHECK_SWITCH, _MENU, _SCROLLBAR, _TOOLTIP,
             _NAV, _TOOLBAR, _SEGMENTED, _SYNC_BADGE, _PANEL, _DIALOG, _SETTINGS, _TOAST)


def app_stylesheet():
    """組出全域 QSS 字串；箭頭 / 勾選 / 開關圖示會寫成上色 SVG 暫存檔再引用。"""
    icon_urls = {
        "ICON_CHEVRON_DOWN": export_colored_svg("chevron-down", theme.TEXT_SECONDARY),
        "ICON_CHEVRON_UP": export_colored_svg("chevron-up", theme.TEXT_SECONDARY),
        "ICON_CHECK": export_colored_svg("check", theme.TEXT_ON_ACCENT),
        "SWITCH_OFF": export_switch_svg(False, theme.SURFACE_3, theme.TEXT_SECONDARY, theme.BORDER_STRONG),
        "SWITCH_ON": export_switch_svg(True, theme.ACCENT, theme.TEXT_ON_ACCENT, theme.ACCENT),
    }
    return theme.qss("\n".join(_SECTIONS), **icon_urls)


def build_palette():
    """依 theme token 建立全域調色盤（讓未被 QSS 涵蓋的元件也跟著深色）。"""
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: theme.BG,
        QPalette.ColorRole.WindowText: theme.TEXT_PRIMARY,
        QPalette.ColorRole.Base: theme.SURFACE_2,
        QPalette.ColorRole.AlternateBase: theme.SURFACE_1,
        QPalette.ColorRole.Text: theme.TEXT_PRIMARY,
        QPalette.ColorRole.Button: theme.SURFACE_2,
        QPalette.ColorRole.ButtonText: theme.TEXT_PRIMARY,
        QPalette.ColorRole.Highlight: theme.ACCENT,
        QPalette.ColorRole.HighlightedText: theme.TEXT_ON_ACCENT,
        QPalette.ColorRole.ToolTipBase: theme.SURFACE_3,
        QPalette.ColorRole.ToolTipText: theme.TEXT_PRIMARY,
        QPalette.ColorRole.PlaceholderText: theme.TEXT_MUTED,
    }
    for role, value in roles.items():
        pal.setColor(role, qcolor(value))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, qcolor(theme.TEXT_MUTED))
    return pal


def apply_app_style(app):
    """設定全域字型、調色盤與 QSS；結束前清除圖示快取（避免 QPixmap 在 QApplication 之後才釋放）。"""
    font = QFont()
    font.setFamilies(list(theme.FONT_FAMILIES))
    font.setPixelSize(theme.FONT_SM)
    app.setFont(font)
    app.setPalette(build_palette())
    app.setStyleSheet(app_stylesheet())
    app.aboutToQuit.connect(clear_caches)
