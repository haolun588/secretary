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


def test_delete_button_hidden_in_new_mode_and_shown_in_edit(dialog_cls):
    new_dlg = dialog_cls()
    assert new_dlg.delete_btn.isHidden()
    edit_dlg = dialog_cls(event_data=_timed_event())
    assert not edit_dlg.delete_btn.isHidden()
    assert edit_dlg.delete_btn.property("variant") == "danger"


def test_window_title_new_and_edit(dialog_cls):
    assert dialog_cls().windowTitle() == "新增行程"
    assert dialog_cls(event_data=_timed_event()).windowTitle() == "編輯行程"


def test_all_day_toggle_hides_time_fields(dialog_cls):
    dlg = dialog_cls()
    assert not dlg.start_time.isHidden() and not dlg.end_time.isHidden()
    dlg.all_day_chk.setChecked(True)
    assert dlg.start_time.isHidden() and dlg.end_time.isHidden()
    dlg.all_day_chk.setChecked(False)
    assert not dlg.start_time.isHidden() and not dlg.end_time.isHidden()


def test_all_day_switch_variant(dialog_cls):
    assert dialog_cls().all_day_chk.property("variant") == "switch"


def test_priority_combo_current_data(dialog_cls):
    assert dialog_cls().priority_combo.currentData() == "medium"
    assert dialog_cls(event_data=_all_day_event()).priority_combo.currentData() == "major"
    assert dialog_cls(event_data=_timed_event()).priority_combo.currentData() == "minor"
    dlg = dialog_cls()
    combo = dlg.priority_combo
    assert [combo.itemData(i) for i in range(combo.count())] == ["major", "medium", "minor"]
    assert all(not combo.itemIcon(i).isNull() for i in range(combo.count()))


def test_delete_confirm_sets_is_delete(dialog_cls, monkeypatch):
    from PyQt6.QtWidgets import QDialog
    import ui.calendar_dialog as mod
    monkeypatch.setattr(mod.ConfirmDeleteDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    dlg = dialog_cls(event_data=_timed_event())
    dlg.on_delete_clicked()
    assert dlg.is_delete is True
    assert dlg.result() == 2


def test_delete_confirm_cancel_keeps_dialog(dialog_cls, monkeypatch):
    from PyQt6.QtWidgets import QDialog
    import ui.calendar_dialog as mod
    monkeypatch.setattr(mod.ConfirmDeleteDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    dlg = dialog_cls(event_data=_timed_event())
    dlg.on_delete_clicked()
    assert dlg.is_delete is False


def test_confirm_delete_dialog_buttons(qapp):
    from ui.calendar_dialog import ConfirmDeleteDialog
    dlg = ConfirmDeleteDialog("開會")
    assert dlg.cancel_btn.property("variant") == "secondary"
    assert dlg.confirm_btn.property("variant") == "danger"


def test_date_button_uses_chinese_weekday(dialog_cls):
    dlg = dialog_cls(default_date=QDate(2026, 11, 25))
    assert dlg.start_date_btn.text() == "2026/11/25 週三"
    dlg.start_date_btn.setDate(QDate(2026, 11, 29))
    assert dlg.start_date_btn.text() == "2026/11/29 週日"
