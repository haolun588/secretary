import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtCore import QDate  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    try:
        return QApplication.instance() or QApplication([])
    except Exception as e:  # offscreen 平台不可用
        pytest.skip(f"無法建立 QApplication: {e}")


@pytest.fixture
def dialog_cls(qapp):
    from ui.calendar_dialog import CalendarDialog
    return CalendarDialog


def _all_day_event():
    return {"id": "a", "title": "全天", "all_day": True, "start": "2026-03-10",
            "end": "2026-03-12", "priority": "major", "location": "L", "notes": "N"}


def _timed_event():
    return {"id": "b", "title": "定時", "all_day": False, "start": "2026-03-10T09:15:00",
            "end": "2026-03-10T10:30:00", "priority": "minor", "location": "", "notes": ""}


def test_edit_all_day_event_loads(dialog_cls):
    dlg = dialog_cls(event_data=_all_day_event())
    assert dlg.all_day_chk.isChecked()
    assert dlg.start_date_btn.date() == QDate(2026, 3, 10)
    assert dlg.end_date_btn.date() == QDate(2026, 3, 12)
    assert dlg.start_time.isHidden() and dlg.end_time.isHidden()
    data = dlg.get_data()
    assert data["all_day"] is True
    assert data["start"] == "2026-03-10"
    assert data["end"] == "2026-03-12"
    assert data["priority"] == "major"
    assert set(data) == {"title", "priority", "all_day", "start", "end", "location", "notes"}


def test_edit_timed_event_loads_times_including_off_grid(dialog_cls):
    dlg = dialog_cls(event_data=_timed_event())
    assert not dlg.all_day_chk.isChecked()
    assert dlg.start_time.currentText() == "09:15"  # 不在 30 分清單中，自動插入
    assert dlg.end_time.currentText() == "10:30"
    data = dlg.get_data()
    assert data["all_day"] is False
    assert data["start"] == "2026-03-10T09:15:00"
    assert data["end"] == "2026-03-10T10:30:00"


def test_new_event_uses_default_date(dialog_cls):
    dlg = dialog_cls(default_date=QDate(2026, 5, 6))
    assert dlg.start_date_btn.date() == QDate(2026, 5, 6)
    data = dlg.get_data()
    assert data["start"] == "2026-05-06T09:00:00"
    assert data["end"] == "2026-05-06T10:00:00"
    assert data["title"] == "新行程"


def test_edit_keeps_original_title_when_blank(dialog_cls):
    dlg = dialog_cls(event_data=_timed_event())
    dlg.title_input.setText("  ")
    assert dlg.get_data()["title"] == "定時"


def test_end_before_start_is_invalid(dialog_cls):
    dlg = dialog_cls(event_data=_timed_event())
    assert dlg._validation_error() is None
    dlg.end_date_btn.setDate(QDate(2026, 3, 9))
    assert dlg._validation_error()
    dlg.all_day_chk.setChecked(True)
    assert dlg._validation_error()
    dlg.end_date_btn.setDate(QDate(2026, 3, 10))
    assert dlg._validation_error() is None


def _roundtrip_no_patch(dialog_cls, item):
    from datetime import timedelta, timezone
    from services import event_mapping as m
    tz = timezone(timedelta(hours=8))
    old = m.from_google(item, tz)
    dlg = dialog_cls(event_data=old)
    data = dlg.get_data()
    assert m.build_patch_body(old, data, tz) == {}


def test_roundtrip_all_day_multi_day_produces_no_patch(dialog_cls):
    _roundtrip_no_patch(dialog_cls, {
        "id": "a", "summary": "  多日  ", "colorId": "5",
        "start": {"date": "2026-03-10"}, "end": {"date": "2026-03-13"},
        "location": " 地點 ", "description": "\n備註\n",
    })


def test_roundtrip_timed_produces_no_patch(dialog_cls):
    _roundtrip_no_patch(dialog_cls, {
        "id": "b", "summary": "定時", "colorId": "11",
        "start": {"dateTime": "2026-03-10T09:15:00+08:00"},
        "end": {"dateTime": "2026-03-10T10:45:00+08:00"},
        "location": "L", "description": " N ",
    })


def test_roundtrip_timed_utc_produces_no_patch(dialog_cls):
    _roundtrip_no_patch(dialog_cls, {
        "id": "c", "summary": "UTC",
        "start": {"dateTime": "2026-03-10T01:00:00Z"},
        "end": {"dateTime": "2026-03-10T02:00:00Z"},
    })
