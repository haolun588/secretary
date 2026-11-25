import os
import re

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtCore import QtMsgType, qInstallMessageHandler  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QMenu, QPushButton,  # noqa: E402
                             QScrollBar, QSpinBox)

from ui import styles, theme  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    try:
        return QApplication.instance() or QApplication([])
    except Exception as e:
        pytest.skip(f"無法建立 QApplication: {e}")


def test_qcolor_hex(qapp):
    c = styles.qcolor("#8b7cf6")
    assert (c.red(), c.green(), c.blue(), c.alpha()) == (139, 124, 246, 255)


def test_qcolor_rgba(qapp):
    c = styles.qcolor("rgba(139,124,246,0.14)")
    assert (c.red(), c.green(), c.blue()) == (139, 124, 246)
    assert abs(c.alphaF() - 0.14) < 0.01


def test_qcolor_all_theme_colors(qapp):
    for name in ("BG", "ACCENT", "ACCENT_MUTED", "ACCENT_SOFT", "HOVER", "PRESSED",
                 "DANGER_MUTED", "OVERLAY", "TEXT_ON_ACCENT"):
        assert styles.qcolor(theme.TOKENS[name]).isValid(), name


def test_qcolor_invalid_raises(qapp):
    with pytest.raises(ValueError):
        styles.qcolor("red")


def test_app_stylesheet_has_no_leftover_tokens():
    css = styles.app_stylesheet()
    assert css.strip()
    assert not re.findall(r"\{[A-Z][A-Z0-9_]*\}", css)


def test_app_stylesheet_covers_components():
    css = styles.app_stylesheet()
    for needle in ('QPushButton[variant="primary"]', 'QCheckBox[variant="switch"]',
                   "QFrame#NavSidebar", "QWidget#Segmented", "QPushButton#SyncBadge",
                   "QFrame#SidePanel", "QFrame#SettingsRow", "QFrame#ToastCard", "QMenu", "QToolTip"):
        assert needle in css, needle


def test_apply_app_style_sets_stylesheet(qapp):
    styles.apply_app_style(qapp)
    assert "QPushButton" in qapp.styleSheet()
    assert qapp.font().pixelSize() == theme.FONT_SM


def test_repolish_unpolishes_then_polishes(qapp):
    from PyQt6.QtWidgets import QProxyStyle
    calls = []

    class _CountingStyle(QProxyStyle):
        def unpolish(self, widget):
            calls.append("unpolish")
            super().unpolish(widget)

        def polish(self, widget):
            calls.append("polish")
            super().polish(widget)

    proxy = _CountingStyle()
    btn = QPushButton("x")
    btn.setStyle(proxy)
    calls.clear()
    styles.repolish(btn)
    assert calls == ["unpolish", "polish"]


def test_repolish_applies_new_variant(qapp):
    old = qapp.styleSheet()
    qapp.setStyleSheet(styles.app_stylesheet())
    try:
        btn = QPushButton("x")
        btn.ensurePolished()
        before = btn.grab().toImage().pixelColor(btn.width() // 2, 2)
        btn.setProperty("variant", "primary")
        styles.repolish(btn)
        after = btn.grab().toImage().pixelColor(btn.width() // 2, 2)
        assert before != after
    finally:
        qapp.setStyleSheet(old)


def test_stylesheet_parses_without_warnings(qapp):
    messages = []

    def handler(mode, context, message):
        messages.append(message)

    previous = qInstallMessageHandler(handler)
    old = qapp.styleSheet()
    try:
        qapp.setStyleSheet(styles.app_stylesheet())
        widgets = [QPushButton("a"), QComboBox(), QSpinBox(), QCheckBox("c"), QScrollBar()]
        widgets[1].addItems(["a", "b"])
        sw = QCheckBox("s")
        sw.setProperty("variant", "switch")
        widgets.append(sw)
        menu = QMenu()
        menu.addAction("item")
        widgets.append(menu)
        # 不呼叫 processEvents：避免處理到其他測試遺留的事件
        for w in widgets:
            w.ensurePolished()
            w.grab()
    finally:
        qapp.setStyleSheet(old)
        qInstallMessageHandler(previous)
    bad = [m for m in messages if "parse" in m.lower() or "stylesheet" in m.lower()]
    assert not bad, bad


def test_build_palette_roles(qapp):
    from PyQt6.QtGui import QPalette
    pal = styles.build_palette()
    assert pal.color(QPalette.ColorRole.Window) == styles.qcolor(theme.BG)
    assert pal.color(QPalette.ColorRole.Highlight) == styles.qcolor(theme.ACCENT)
    assert pal.color(QPalette.ColorRole.PlaceholderText) == styles.qcolor(theme.TEXT_MUTED)


def test_single_line_collapses_whitespace():
    assert styles.single_line("a\nb\t c  ") == "a b c"
    assert styles.single_line("  x\r\ny ") == "x y"


def test_fit_text_strips_newlines(qapp):
    from PyQt6.QtGui import QFontMetrics
    fm = QFontMetrics(styles.make_font(theme.FONT_SM))
    title = "Introduction to Digital\nCommunication"
    assert "\n" not in styles.fit_text(fm, title, 1000)
    assert styles.fit_text(fm, title, 1000) == "Introduction to Digital Communication"
    assert "\n" not in styles.fit_text(fm, title, 60)
    assert "\n" not in styles.fit_text(fm, title, 1)


def test_elided_text_keeps_original_text_but_displays_single_line(qapp):
    from ui.side_panel import _ElidedText
    label = _ElidedText("Introduction to Digital\nCommunication")
    assert label.text() == "Introduction to Digital\nCommunication"
    assert label.toolTip() == "Introduction to Digital\nCommunication"
    assert label._display == "Introduction to Digital Communication"
    label.set_text("a\n b")
    assert label._display == "a b"
