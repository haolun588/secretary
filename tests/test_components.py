import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui import theme  # noqa: E402
from ui.components import (IconButton, SegmentedControl, SyncStatusBadge, level_bg,  # noqa: E402
                           level_color, level_text, sync_state_presentation)


@pytest.fixture(scope="module")
def qapp():
    try:
        return QApplication.instance() or QApplication([])
    except Exception as e:
        pytest.skip(f"無法建立 QApplication: {e}")


@pytest.mark.parametrize("state,label,icon_name,tone", [
    ("idle", "未連線", "cloud-off", "neutral"),
    ("authorizing", "授權中", "refresh", "busy"),
    ("syncing", "同步中", "refresh", "busy"),
    ("ok", "已同步", "check", "ok"),
    ("offline", "離線", "cloud-off", "neutral"),
    ("error", "同步錯誤", "alert", "error"),
])
def test_sync_state_presentation(state, label, icon_name, tone):
    assert sync_state_presentation(state) == (label, icon_name, tone)


def test_sync_state_presentation_unknown_falls_back_to_idle():
    assert sync_state_presentation("bogus") == sync_state_presentation("idle")


def test_level_color():
    assert level_color("major") == theme.PRIORITY["major"]
    assert level_color("unknown") == theme.PRIORITY["medium"]


def test_level_bg_and_text_fallback():
    assert level_bg("major") == theme.PRIORITY_BG["major"]
    assert level_bg("major", hovered=True) == theme.PRIORITY_BG_HOVER["major"]
    assert level_bg("unknown") == theme.PRIORITY_BG["medium"]
    assert level_bg(None, hovered=True) == theme.PRIORITY_BG_HOVER["medium"]
    assert level_text("minor") == theme.PRIORITY_TEXT["minor"]
    assert level_text("unknown") == theme.PRIORITY_TEXT["medium"]
    assert level_text(None) == theme.PRIORITY_TEXT["medium"]


def test_segmented_changed_signal(qapp):
    seg = SegmentedControl([("month", "月"), ("week", "週"), ("day", "日")])
    got = []
    seg.changed.connect(got.append)
    assert seg.current() == "month"
    seg._buttons["week"].click()
    assert got == ["week"] and seg.current() == "week"
    seg._buttons["week"].click()  # 點同一個不重複發出
    assert got == ["week"]


def test_segmented_set_current_is_silent(qapp):
    seg = SegmentedControl([("a", "A"), ("b", "B")])
    got = []
    seg.changed.connect(got.append)
    seg.set_current("b")
    assert seg.current() == "b" and got == []
    assert seg._buttons["b"].isChecked()


def test_sync_badge_set_state(qapp):
    badge = SyncStatusBadge()
    badge.set_state("error", "網路失敗")
    assert badge.text() == "同步錯誤"
    assert badge.toolTip() == "網路失敗"
    assert badge.property("tone") == "error"
    badge.set_state("bogus")
    assert badge.text() == "未連線"


def test_icon_button(qapp):
    btn = IconButton("plus", "新增")
    assert btn.toolTip() == "新增"
    assert not btn.icon().isNull()
