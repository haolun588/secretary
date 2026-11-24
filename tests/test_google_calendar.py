import importlib
import socket

import pytest


@pytest.fixture(scope="module")
def gc():
    """匯入 google_calendar 會 monkeypatch socket.getaddrinfo 並設定全域逾時，匯入後還原。"""
    pytest.importorskip("PyQt6.QtCore")
    orig_getaddrinfo = socket.getaddrinfo
    orig_timeout = socket.getdefaulttimeout()
    try:
        module = importlib.import_module("utils.google_calendar")
    finally:
        socket.getaddrinfo = orig_getaddrinfo
        socket.setdefaulttimeout(orig_timeout)
    return module


def test_maps_are_consistent(gc):
    for priority, color_id in gc.PRIORITY_COLOR_MAP.items():
        assert gc.COLOR_PRIORITY_MAP[color_id] == priority


def test_parse_known_values(gc):
    svc = gc.GoogleCalendarService()
    assert svc.parse_priority_from_color("11") == "major"
    assert svc.parse_priority_from_color("4") == "major"
    assert svc.parse_priority_from_color("5") == "medium"
    assert svc.parse_priority_from_color(6) == "medium"
    assert svc.parse_priority_from_color("2") == "minor"
    assert svc.parse_priority_from_color("10") == "minor"


def test_parse_unknown_returns_minor(gc):
    svc = gc.GoogleCalendarService()
    assert svc.parse_priority_from_color(None) == "minor"
    assert svc.parse_priority_from_color("") == "minor"
    assert svc.parse_priority_from_color("99") == "minor"


def test_import_side_effects_restored(gc):
    assert socket.getaddrinfo.__name__ != "_ipv4_only_getaddrinfo"
