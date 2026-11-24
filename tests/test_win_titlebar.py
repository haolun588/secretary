import ctypes
import sys
import types

import pytest

from utils import win_titlebar


class _Widget:
    def __init__(self):
        self.window_called = False

    def window(self):
        self.window_called = True
        return self

    def winId(self):
        return 1234


class _FakeDwm:
    """假的 DwmSetWindowAttribute：依序回傳指定的 HRESULT，並記錄呼叫的屬性代碼。"""

    def __init__(self, results):
        self.results = list(results)
        self.attributes = []
        self.argtypes = None
        self.restype = None

    def __call__(self, hwnd, attribute, ref, size):
        assert hwnd == 1234
        self.attributes.append(attribute)
        return self.results.pop(0)


def _install_fake_dwm(monkeypatch, fake):
    windll = types.SimpleNamespace(dwmapi=types.SimpleNamespace(DwmSetWindowAttribute=fake))
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)
    monkeypatch.setattr(win_titlebar, "_is_supported", lambda: True)


def test_non_windows_returns_false(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert win_titlebar.enable_dark_titlebar(_Widget()) is False


def test_offscreen_returns_false(monkeypatch):
    qtgui = pytest.importorskip("PyQt6.QtGui")
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(qtgui.QGuiApplication, "platformName", staticmethod(lambda: "offscreen"))
    assert win_titlebar._is_supported() is False
    assert win_titlebar.enable_dark_titlebar(_Widget()) is False


def test_success_uses_top_level_window_and_attribute_20(monkeypatch):
    fake = _FakeDwm([0])
    _install_fake_dwm(monkeypatch, fake)
    widget = _Widget()
    assert win_titlebar.enable_dark_titlebar(widget) is True
    assert widget.window_called
    assert fake.attributes == [20]
    assert fake.restype is ctypes.c_long and len(fake.argtypes) == 4


def test_falls_back_to_attribute_19(monkeypatch):
    fake = _FakeDwm([-1, 0])
    _install_fake_dwm(monkeypatch, fake)
    assert win_titlebar.enable_dark_titlebar(_Widget()) is True
    assert fake.attributes == [20, 19]


def test_both_attributes_fail_returns_false(monkeypatch):
    fake = _FakeDwm([-1, -1])
    _install_fake_dwm(monkeypatch, fake)
    assert win_titlebar.enable_dark_titlebar(_Widget()) is False
    assert fake.attributes == [20, 19]


def test_dwm_exception_returns_false(monkeypatch):
    class _BoomDwm(_FakeDwm):
        def __call__(self, hwnd, attribute, ref, size):
            self.attributes.append(attribute)
            raise OSError("dwm failed")

    fake = _BoomDwm([])
    _install_fake_dwm(monkeypatch, fake)
    assert win_titlebar.enable_dark_titlebar(_Widget()) is False
    assert fake.attributes == [20]


def test_winid_exception_returns_false(monkeypatch):
    monkeypatch.setattr(win_titlebar, "_is_supported", lambda: True)
    reached = []

    class _Bad:
        def window(self):
            reached.append(True)
            raise RuntimeError("boom")

    assert win_titlebar.enable_dark_titlebar(_Bad()) is False
    assert reached == [True]
