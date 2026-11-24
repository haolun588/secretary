import sys
import types

import pytest

from utils import autostart
from utils.autostart import AutoStartManager, plan_sync


@pytest.mark.parametrize("desired,current,expected,result", [
    (True, None, "cmd", "set"),
    (True, "old", "cmd", "set"),
    (True, "cmd", "cmd", None),
    (False, None, "cmd", None),
    (False, "cmd", "cmd", "delete"),
    (False, "", "cmd", "delete"),
])
def test_plan_sync(desired, current, expected, result):
    assert plan_sync(desired, current, expected) == result


def _patch_manager(monkeypatch, current, expected="cmd", set_result=True):
    calls = []
    monkeypatch.setattr(AutoStartManager, "get_registered_command", staticmethod(lambda: current))
    monkeypatch.setattr(AutoStartManager, "get_executable_command", staticmethod(lambda: expected))
    monkeypatch.setattr(AutoStartManager, "set_autostart",
                        staticmethod(lambda enable=True: calls.append(enable) or set_result))
    return calls


def test_sync_no_action_does_not_write(monkeypatch):
    calls = _patch_manager(monkeypatch, current="cmd")
    assert AutoStartManager.sync(True) is True
    assert calls == []
    calls = _patch_manager(monkeypatch, current=None)
    assert AutoStartManager.sync(False) is True
    assert calls == []


def test_sync_sets_when_different(monkeypatch):
    calls = _patch_manager(monkeypatch, current="old")
    assert AutoStartManager.sync(True) is True
    assert calls == [True]


def test_sync_deletes_when_registered(monkeypatch):
    calls = _patch_manager(monkeypatch, current="cmd")
    assert AutoStartManager.sync(False) is True
    assert calls == [False]


def test_sync_returns_false_on_failure(monkeypatch):
    calls = _patch_manager(monkeypatch, current=None, set_result=False)
    assert AutoStartManager.sync(True) is False
    assert calls == [True]


class FakeWinreg(types.SimpleNamespace):
    pass


def _fake_winreg(monkeypatch, values=None, open_error=None, delete_error=None):
    log = {"open_access": [], "closed": 0, "set": [], "deleted": []}
    values = values if values is not None else {}

    def open_key(root, path, reserved, access):
        if open_error:
            raise open_error
        log["open_access"].append(access)
        return object()

    def set_value(key, name, reserved, typ, val):
        log["set"].append((name, val))

    def delete_value(key, name):
        if delete_error:
            raise delete_error
        log["deleted"].append(name)

    def query(key, name):
        if name not in values:
            raise FileNotFoundError
        return values[name], 1

    def close(key):
        log["closed"] += 1

    fake = FakeWinreg(
        HKEY_CURRENT_USER="HKCU", KEY_SET_VALUE=2, KEY_READ=131097, KEY_ALL_ACCESS=983103,
        REG_SZ=1, OpenKey=open_key, SetValueEx=set_value, DeleteValue=delete_value,
        QueryValueEx=query, CloseKey=close,
    )
    monkeypatch.setitem(sys.modules, "winreg", fake)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(AutoStartManager, "get_executable_command", staticmethod(lambda: "cmd"))
    return log


def test_set_autostart_uses_set_value_and_closes(monkeypatch):
    log = _fake_winreg(monkeypatch)
    assert AutoStartManager.set_autostart(True) is True
    assert log["open_access"] == [2]
    assert log["set"] == [(autostart.APP_NAME, "cmd")]
    assert log["closed"] == 1


def test_set_autostart_delete_missing_is_ok(monkeypatch):
    log = _fake_winreg(monkeypatch, delete_error=FileNotFoundError())
    assert AutoStartManager.set_autostart(False) is True
    assert log["closed"] == 1


def test_set_autostart_failure_returns_false(monkeypatch):
    _fake_winreg(monkeypatch, open_error=PermissionError("no"))
    assert AutoStartManager.set_autostart(True) is False


def test_set_autostart_closes_key_on_error(monkeypatch):
    log = _fake_winreg(monkeypatch, delete_error=PermissionError("no"))
    assert AutoStartManager.set_autostart(False) is False
    assert log["closed"] == 1


def test_get_registered_command(monkeypatch):
    log = _fake_winreg(monkeypatch, values={autostart.APP_NAME: "abc"})
    assert AutoStartManager.get_registered_command() == "abc"
    assert log["open_access"] == [131097]
    assert log["closed"] == 1
    assert AutoStartManager.is_autostart_enabled() is True


def test_get_registered_command_missing_returns_none(monkeypatch):
    log = _fake_winreg(monkeypatch)
    assert AutoStartManager.get_registered_command() is None
    assert log["closed"] == 1
    assert AutoStartManager.is_autostart_enabled() is False


def test_get_registered_command_non_win32(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert AutoStartManager.get_registered_command() is None
