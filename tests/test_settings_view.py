import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtCore import QObject, pyqtSignal  # noqa: E402

import ui.settings_view as sv  # noqa: E402
from ui.styles import app_stylesheet  # noqa: E402


class FakeStore(QObject):
    events_changed = pyqtSignal(list)
    sync_state_changed = pyqtSignal(str, str)
    operation_failed = pyqtSignal(str, str)
    operation_succeeded = pyqtSignal(str)
    auth_state_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.is_authenticated = False
        self.is_authorizing = False
        self.calls = []

    def authorize(self):
        self.calls.append("authorize")

    def logout(self):
        self.calls.append("logout")


@pytest.fixture
def store():
    return FakeStore()


@pytest.fixture
def view(_session_qapplication, store):
    _session_qapplication.setStyleSheet(app_stylesheet())
    v = sv.SettingsView(store)
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


def test_autostart_signal(view):
    got = []
    view.autostart_signal.connect(got.append)
    view.chk_autostart.setChecked(False)
    view.chk_autostart.setChecked(True)
    assert got == [False, True]


def test_minimize_to_tray_signal(view):
    got = []
    view.minimize_to_tray_signal.connect(got.append)
    assert view.chk_minimize_to_tray.isChecked()
    view.chk_minimize_to_tray.setChecked(False)
    view.chk_minimize_to_tray.setChecked(True)
    assert got == [False, True]


def test_interval_range_and_suffix(view):
    assert (view.spin_interval.minimum(), view.spin_interval.maximum()) == (1, 180)
    assert view.spin_interval.suffix() == " 分鐘"


def test_switch_variants(view):
    for chk in (view.chk_water_enabled, view.chk_autostart, view.chk_minimize_to_tray):
        assert chk.property("variant") == "switch"


def test_login_button_when_unauthenticated(view):
    assert view.connect_btn.text() == "登入"
    assert view.connect_btn.property("variant") == "primary"
    assert view.connect_btn.isEnabled()


def test_auth_state_switches_button(view, store):
    store.is_authenticated = True
    store.auth_state_changed.emit(True)
    assert view.connect_btn.text() == "登出"
    assert view.connect_btn.property("variant") == "secondary"
    assert view.g_status_lbl.property("state") == "ok"
    store.is_authenticated = False
    store.auth_state_changed.emit(False)
    assert view.connect_btn.text() == "登入"
    assert view.connect_btn.property("variant") == "primary"


def test_authorizing_disables_button(view, store):
    store.is_authorizing = True
    store.sync_state_changed.emit("authorizing", "")
    assert not view.connect_btn.isEnabled()
    # 授權進行中 auth_state_changed 不覆寫狀態
    store.auth_state_changed.emit(False)
    assert not view.connect_btn.isEnabled()
    store.is_authorizing = False
    store.auth_state_changed.emit(True)
    assert view.connect_btn.isEnabled()


def test_auth_failure_restores_button_and_shows_error(view, store):
    store.is_authorizing = True
    store.sync_state_changed.emit("authorizing", "")
    store.is_authorizing = False
    store.operation_failed.emit("auth", "boom")
    assert view.connect_btn.isEnabled()
    assert view.connect_btn.text() == "登入"
    assert view.g_status_lbl.property("state") == "error"


def test_login_click_authorizes(view, store):
    view.connect_btn.click()
    assert store.calls == ["authorize"]


def test_logout_requires_confirmation(view, store, monkeypatch):
    store.is_authenticated = True
    monkeypatch.setattr(view, "_confirm_logout", lambda: False)
    view.connect_btn.click()
    assert store.calls == []
    monkeypatch.setattr(view, "_confirm_logout", lambda: True)
    view.connect_btn.click()
    assert store.calls == ["logout"]


def test_confirm_logout_uses_dialog_exec(view, monkeypatch):
    monkeypatch.setattr(sv.ConfirmDialog, "exec", lambda self: sv.ConfirmDialog.DialogCode.Rejected)
    assert view._confirm_logout() is False
    monkeypatch.setattr(sv.ConfirmDialog, "exec", lambda self: sv.ConfirmDialog.DialogCode.Accepted)
    assert view._confirm_logout() is True


def test_auth_success_message_box(view, store, monkeypatch):
    shown = []
    monkeypatch.setattr(sv.QMessageBox, "information", lambda *a, **k: shown.append(a))
    store.operation_succeeded.emit("auth")
    store.operation_succeeded.emit("fetch")
    assert len(shown) == 1


def test_test_button_emits_signal(view):
    got = []
    view.test_toast_requested.connect(lambda: got.append(True))
    view.test_btn.click()
    assert got == [True]
    assert not hasattr(sv, "ToastWindow")


def test_auth_failure_text_survives_following_auth_state_false(view, store):
    store.is_authorizing = True
    store.sync_state_changed.emit("authorizing", "")
    store.is_authorizing = False
    store.operation_failed.emit("auth", "boom")
    store.auth_state_changed.emit(False)
    assert view.g_status_lbl.text() == "授權失敗，請重新登入"
    assert view.g_status_lbl.property("state") == "error"
    assert view.connect_btn.text() == "登入" and view.connect_btn.isEnabled()


def test_login_click_clears_auth_failed_flag(view, store):
    store.operation_failed.emit("auth", "boom")
    view.connect_btn.click()
    store.auth_state_changed.emit(False)
    assert view.g_status_lbl.text() == "未連線"


def test_scroll_to_water_does_not_raise(view):
    view.resize(800, 300)
    view.scroll_to_water()
