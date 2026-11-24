import os
import re

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")

from ui.tray_menu import TRAY_MENU_ITEMS, build_tray_menu  # noqa: E402

_EMOJI_RE = re.compile("[\U0001F000-\U0001FFFF☀-➿⬀-⯿️]")


@pytest.fixture
def calls():
    return []


@pytest.fixture
def menu(_session_qapplication, calls):
    handlers = {k: (lambda k=k: calls.append(k)) for k in ("show", "test_water", "settings", "quit")}
    m = build_tray_menu(handlers)
    yield m
    m.deleteLater()


def test_item_texts(menu):
    texts = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert texts == ["顯示主視窗", "測試喝水提醒", "設定", "結束"]


def test_has_one_separator_before_quit(menu):
    acts = menu.actions()
    assert [a.isSeparator() for a in acts] == [False, False, False, True, False]


def test_no_emoji_and_all_have_icons(menu):
    for a in menu.actions():
        if a.isSeparator():
            continue
        assert not _EMOJI_RE.search(a.text())
        assert not a.icon().isNull()


def test_trigger_calls_handler(menu, calls):
    for key, _text, _icon in (i for i in TRAY_MENU_ITEMS if i):
        menu.actions_by_key[key].trigger()
    assert calls == ["show", "test_water", "settings", "quit"]


def test_missing_handler_disables_action(_session_qapplication):
    m = build_tray_menu({"show": lambda: None})
    assert m.actions_by_key["show"].isEnabled()
    assert not m.actions_by_key["quit"].isEnabled()
    m.deleteLater()
