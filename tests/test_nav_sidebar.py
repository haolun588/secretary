import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")

from ui import theme  # noqa: E402
from ui.nav_sidebar import NavSidebar, format_countdown  # noqa: E402


class FakeConfig:
    def __init__(self, data=None):
        self.data = data if data is not None else {"minimize_to_tray": True}

    def load_config(self):
        return dict(self.data)

    def save_config(self, data):
        return True


@pytest.fixture
def sidebar(_session_qapplication):
    sb = NavSidebar()
    yield sb
    sb.deleteLater()


@pytest.fixture
def window(_session_qapplication, tmp_path):
    from services.event_store import EventStore
    from ui.main_window import MainWindow
    store = EventStore(runner=lambda fn, ok, err: None, oauth_runner=lambda fn, ok, err: None,
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    win = MainWindow(FakeConfig(), store)
    yield win
    win.deleteLater()


# ---------------------------------------------------------------- format_countdown

@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00"),
    (5, "00:05"),
    (522, "08:42"),
    (3599, "59:59"),
    (3600, "1:00:00"),
    (3725, "1:02:05"),
    (-3, "00:00"),
])
def test_format_countdown(seconds, expected):
    assert format_countdown(seconds) == expected


# ---------------------------------------------------------------- NavSidebar

def test_sidebar_fixed_width(sidebar):
    assert sidebar.width() == theme.NAV_WIDTH
    assert sidebar.minimumWidth() == sidebar.maximumWidth() == theme.NAV_WIDTH


def test_initial_state_calendar_checked(sidebar):
    assert sidebar.btn_calendar.isChecked()
    assert not sidebar.btn_water.isChecked()
    assert not sidebar.btn_settings.isChecked()


def test_click_buttons_emit_signals_and_checked_exclusive(sidebar):
    pages, waters = [], []
    sidebar.page_changed.connect(pages.append)
    sidebar.water_requested.connect(lambda: waters.append(True))

    sidebar.btn_settings.click()
    assert pages == [1]
    assert sidebar.btn_settings.isChecked()
    assert not sidebar.btn_calendar.isChecked()

    sidebar.btn_water.click()
    assert waters == [True]
    assert pages == [1]  # 喝水按鈕不發 page_changed，由 MainWindow 處理
    assert sidebar.btn_water.isChecked()
    assert not sidebar.btn_settings.isChecked()
    assert not sidebar.btn_calendar.isChecked()

    sidebar.btn_calendar.click()
    assert pages == [1, 0]
    checked = [b.isChecked() for b in (sidebar.btn_calendar, sidebar.btn_water, sidebar.btn_settings)]
    assert checked == [True, False, False]


def test_set_active_page(sidebar):
    pages = []
    sidebar.page_changed.connect(pages.append)
    sidebar.set_active_page(1)
    assert sidebar.btn_settings.isChecked()
    sidebar.set_active_page(0)
    assert sidebar.btn_calendar.isChecked()
    assert pages == [1, 0]


def test_set_countdown_none_shows_off_state(sidebar):
    sidebar.set_countdown(522)
    assert sidebar.countdown_label.text() == "08:42"
    assert sidebar.countdown_label.property("off") == "false"

    sidebar.set_countdown(None)
    assert sidebar.countdown_label.text() == "關"
    assert sidebar.countdown_label.property("off") == "true"
    assert "已關閉" in sidebar.countdown_label.toolTip()


def test_update_countdown_compat(sidebar):
    sidebar.update_countdown("下次提醒: 08:42 後", is_enabled=True)
    assert sidebar.countdown_label.text() == "08:42"
    assert sidebar.countdown_label.property("off") == "false"

    sidebar.update_countdown("提醒狀態: 已關閉", is_enabled=False)
    assert sidebar.countdown_label.text() == "關"
    assert sidebar.countdown_label.property("off") == "true"

    sidebar.update_countdown("下次提醒: 120:00 後", is_enabled=True)
    assert sidebar.countdown_label.text() == "2:00:00"
    assert sidebar.countdown_label.property("off") == "false"


def test_update_countdown_parse_failure_keeps_previous(sidebar):
    sidebar.update_countdown("下次提醒: 08:42 後")
    sidebar.update_countdown("沒有時間字樣")
    sidebar.update_countdown("還是沒有")
    assert sidebar.countdown_label.text() == "08:42"
    assert sidebar.countdown_label.property("off") == "false"


def test_set_active_page_invalid_index_ignored(sidebar):
    pages = []
    sidebar.page_changed.connect(pages.append)
    sidebar.set_active_page(7)
    sidebar.set_active_page(-1)
    sidebar.set_active_page(None)
    assert pages == []
    assert sidebar.btn_calendar.isChecked()


def test_set_active_page_when_water_checked(sidebar):
    sidebar.btn_water.click()
    sidebar.set_active_page(0)
    assert [b.isChecked() for b in (sidebar.btn_calendar, sidebar.btn_water, sidebar.btn_settings)] == [True, False, False]
    sidebar.btn_water.click()
    sidebar.set_active_page(1)
    assert [b.isChecked() for b in (sidebar.btn_calendar, sidebar.btn_water, sidebar.btn_settings)] == [False, False, True]


def test_show_event_enables_dark_titlebar_once(window, monkeypatch):
    from PyQt6.QtGui import QShowEvent
    import ui.main_window as mw
    calls = []
    monkeypatch.setattr(mw, "enable_dark_titlebar", lambda w: calls.append(w) or False)
    window.showEvent(QShowEvent())
    window.showEvent(QShowEvent())
    assert calls == [window]


# ---------------------------------------------------------------- MainWindow

def test_main_window_sizes_use_tokens(window):
    assert window.minimumWidth() == theme.WINDOW_MIN_W
    assert window.minimumHeight() == theme.WINDOW_MIN_H
    assert window.width() == theme.WINDOW_W
    assert window.height() == theme.WINDOW_H


def test_main_window_public_attributes(window):
    assert window.stacked_widget.count() == 2
    assert window.stacked_widget.widget(0) is window.calendar_view
    assert window.stacked_widget.widget(1) is window.settings_view
    assert window.stacked_widget.currentIndex() == 0


def test_main_window_settings_button_switches_page(window):
    window.sidebar.btn_settings.click()
    assert window.stacked_widget.currentIndex() == 1
    window.sidebar.btn_calendar.click()
    assert window.stacked_widget.currentIndex() == 0


def test_main_window_water_button_goes_to_settings_and_scrolls(window):
    calls = []
    window.settings_view.scroll_to_water = lambda: calls.append(True)
    window.sidebar.btn_water.click()
    assert window.stacked_widget.currentIndex() == 1
    assert calls == [True]
    assert window.sidebar.btn_water.isChecked()
    assert not window.sidebar.btn_settings.isChecked()


def test_settings_view_scroll_to_water_does_not_raise(window):
    window.settings_view.scroll_to_water()


def test_close_event_respects_minimize_to_tray(_session_qapplication, tmp_path):
    from PyQt6.QtGui import QCloseEvent
    from services.event_store import EventStore
    from ui.main_window import MainWindow
    store = EventStore(runner=lambda fn, ok, err: None, oauth_runner=lambda fn, ok, err: None,
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    win = MainWindow(FakeConfig({"minimize_to_tray": False}), store)
    ev = QCloseEvent()
    win.closeEvent(ev)
    assert ev.isAccepted()

    win2 = MainWindow(FakeConfig({"minimize_to_tray": True}), store)
    ev2 = QCloseEvent()
    win2.closeEvent(ev2)
    assert not ev2.isAccepted()
    win.deleteLater()
    win2.deleteLater()
