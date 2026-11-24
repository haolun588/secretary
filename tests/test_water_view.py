import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")

from ui.styles import app_stylesheet  # noqa: E402
from ui.water_view import WaterView  # noqa: E402


@pytest.fixture
def view(_session_qapplication):
    _session_qapplication.setStyleSheet(app_stylesheet())
    v = WaterView()
    yield v
    v.deleteLater()
    _session_qapplication.setStyleSheet("")


def test_water_signal_and_interval_enabled(view):
    got = []
    view.water_enabled_signal.connect(got.append)
    view.chk_water_enabled.setChecked(False)
    assert got == [False]
    assert not view.spin_interval.isEnabled()
    view.chk_water_enabled.setChecked(True)
    assert got == [False, True]
    assert view.spin_interval.isEnabled()


def test_interval_range_default_and_suffix(view):
    assert (view.spin_interval.minimum(), view.spin_interval.maximum()) == (1, 180)
    assert view.spin_interval.suffix() == " 分鐘"
    assert view.spin_interval.value() == 10


def test_switch_variant_and_default_checked(view):
    assert view.chk_water_enabled.property("variant") == "switch"
    assert view.chk_water_enabled.isChecked()


def test_test_button_emits_request(view):
    got = []
    view.test_toast_requested.connect(lambda: got.append(True))
    view.test_btn.click()
    assert got == [True]


def test_countdown_display_and_disabled_state(view):
    view.set_countdown(522)
    assert view.countdown_label.text() == "08:42"
    assert view.countdown_label.property("off") == "false"
    view.set_countdown(3725)
    assert view.countdown_label.text() == "1:02:05"
    view.set_countdown(None)
    assert view.countdown_label.text() == "已停用"
    assert view.countdown_label.property("off") == "true"
    view.set_countdown(10)
    assert view.countdown_label.text() == "00:10"
    assert view.countdown_label.property("off") == "false"


def test_initial_state_is_disabled_text(view):
    assert view.countdown_label.text() == "已停用"


def test_main_window_has_water_view(_session_qapplication, tmp_path):
    from services.event_store import EventStore
    from ui.main_window import MainWindow

    class Cfg:
        def load_config(self):
            return {}

        def save_config(self, data):
            return True

    store = EventStore(runner=lambda fn, ok, err: None, oauth_runner=lambda fn, ok, err: None,
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    win = MainWindow(Cfg(), store)
    assert isinstance(win.water_view, WaterView)
    win.water_view.set_countdown(61)
    assert win.water_view.countdown_label.text() == "01:01"
    win.deleteLater()
