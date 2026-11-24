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


# ---------------------------------------------------------------- 開始/結束連動

def _pick_date(btn, date):
    """模擬使用者在彈出日曆選日期（setDate 不發訊號，需補發 dateChanged）。"""
    btn.setDate(date)
    btn.dateChanged.emit(date)


def test_set_date_does_not_emit_date_changed(qapp):
    from ui.calendar_dialog import DatePopupButton
    btn = DatePopupButton(QDate(2026, 1, 1))
    got = []
    btn.dateChanged.connect(got.append)
    btn.setDate(QDate(2026, 1, 2))
    assert got == []


def test_start_time_change_moves_end_keeping_duration(dialog_cls):
    dlg = dialog_cls(default_date=QDate(2026, 5, 6))  # 09:00-10:00，長度 60 分
    dlg.start_time.setCurrentText("13:30")
    assert dlg.end_date_btn.date() == QDate(2026, 5, 6)
    assert dlg.end_time.currentText() == "14:30"


def test_start_date_change_moves_end_date(dialog_cls):
    dlg = dialog_cls(event_data=_timed_event())  # 09:15-10:30，長度 75 分
    _pick_date(dlg.start_date_btn, QDate(2026, 3, 20))
    assert dlg.end_date_btn.date() == QDate(2026, 3, 20)
    assert dlg.end_time.currentText() == "10:30"
    assert dlg.start_time.currentText() == "09:15"


def test_off_grid_end_time_is_inserted(dialog_cls):
    dlg = dialog_cls(event_data=_timed_event())  # 長度 75 分
    dlg.start_time.setCurrentText("10:00")
    assert dlg.end_time.currentText() == "11:15"
    assert dlg.get_data()["end"] == "2026-03-10T11:15:00"


def test_end_rolls_over_to_next_day(dialog_cls):
    dlg = dialog_cls(default_date=QDate(2026, 5, 6))  # 長度 60 分
    dlg.start_time.setCurrentText("23:30")
    assert dlg.end_date_btn.date() == QDate(2026, 5, 7)
    assert dlg.end_time.currentText() == "00:30"
    assert dlg._validation_error() is None
    assert dlg.save_btn.isEnabled()


def test_end_change_updates_duration(dialog_cls):
    dlg = dialog_cls(default_date=QDate(2026, 5, 6))
    dlg.end_time.setCurrentText("12:00")  # 長度 180 分
    dlg.start_time.setCurrentText("10:00")
    assert dlg.end_time.currentText() == "13:00"


def test_end_before_start_disables_save_and_marks_invalid(dialog_cls):
    dlg = dialog_cls(default_date=QDate(2026, 5, 6))
    dlg.end_time.setCurrentText("08:00")
    assert not dlg.save_btn.isEnabled()
    assert dlg.end_time.property("invalid") == "true"
    assert dlg.end_date_btn.property("invalid") == "true"
    # 長度維持原值：再改開始時間，結束依舊長度前進並恢復合法
    dlg.start_time.setCurrentText("07:00")
    assert dlg.end_time.currentText() == "08:00"
    assert dlg.save_btn.isEnabled()
    assert dlg.end_time.property("invalid") == "false"
    assert dlg.end_date_btn.property("invalid") == "false"


def test_invalid_recovers_when_end_fixed(dialog_cls):
    dlg = dialog_cls(default_date=QDate(2026, 5, 6))
    _pick_date(dlg.end_date_btn, QDate(2026, 5, 5))
    assert not dlg.save_btn.isEnabled()
    _pick_date(dlg.end_date_btn, QDate(2026, 5, 7))
    assert dlg.save_btn.isEnabled()
    assert dlg.end_date_btn.property("invalid") == "false"


def test_all_day_linkage_keeps_day_span(dialog_cls):
    dlg = dialog_cls(event_data=_all_day_event())  # 3/10 - 3/12，長度 2 天
    _pick_date(dlg.start_date_btn, QDate(2026, 3, 31))
    assert dlg.end_date_btn.date() == QDate(2026, 4, 2)
    _pick_date(dlg.end_date_btn, QDate(2026, 3, 30))
    assert not dlg.save_btn.isEnabled()
    _pick_date(dlg.end_date_btn, QDate(2026, 4, 5))
    assert dlg.save_btn.isEnabled()
    _pick_date(dlg.start_date_btn, QDate(2026, 4, 10))
    assert dlg.end_date_btn.date() == QDate(2026, 4, 15)  # 長度已更新為 5 天


def test_toggle_all_day_recomputes_duration(dialog_cls):
    dlg = dialog_cls(default_date=QDate(2026, 5, 6))
    _pick_date(dlg.end_date_btn, QDate(2026, 5, 8))  # 09:00 -> 5/8 10:00
    dlg.all_day_chk.setChecked(True)  # 長度 2 天
    _pick_date(dlg.start_date_btn, QDate(2026, 6, 1))
    assert dlg.end_date_btn.date() == QDate(2026, 6, 3)
    dlg.all_day_chk.setChecked(False)  # 6/1 09:00 -> 6/3 10:00，長度 2 天又 60 分
    dlg.start_time.setCurrentText("12:00")
    assert dlg.end_date_btn.date() == QDate(2026, 6, 3)
    assert dlg.end_time.currentText() == "13:00"


def test_toggle_all_day_reruns_validity(dialog_cls):
    dlg = dialog_cls(default_date=QDate(2026, 5, 6))
    dlg.end_time.setCurrentText("08:00")  # 同日結束早於開始
    assert not dlg.save_btn.isEnabled()
    dlg.all_day_chk.setChecked(True)  # 全天只比日期，同日合法
    assert dlg.save_btn.isEnabled()
    assert dlg.end_date_btn.property("invalid") == "false"


def test_accept_still_guards_invalid(dialog_cls, monkeypatch):
    import ui.calendar_dialog as cd
    shown = []
    monkeypatch.setattr(cd.QMessageBox, "warning", lambda *a, **k: shown.append(a))
    dlg = dialog_cls(default_date=QDate(2026, 5, 6))
    dlg.end_date_btn.setDate(QDate(2026, 5, 1))
    dlg.accept()
    assert shown and dlg.result() == 0


def test_invalid_then_toggle_all_day_does_not_mix_units(dialog_cls):
    dlg = dialog_cls(default_date=QDate(2026, 5, 6))  # 09:00-10:00，分鐘長度 60
    _pick_date(dlg.end_date_btn, QDate(2026, 5, 5))  # 非法
    dlg.all_day_chk.setChecked(True)  # 全天仍非法，天數沿用初始 0
    _pick_date(dlg.start_date_btn, QDate(2026, 5, 10))
    assert dlg.end_date_btn.date() == QDate(2026, 5, 10)


def test_invalid_all_day_then_toggle_back_does_not_mix_units(dialog_cls):
    dlg = dialog_cls(event_data=_all_day_event())  # 3/10 - 3/12，天數 2
    _pick_date(dlg.end_date_btn, QDate(2026, 3, 9))  # 非法
    dlg.all_day_chk.setChecked(False)  # 定時 09:00 起，3/9 結束仍非法，分鐘沿用 60
    dlg.start_time.setCurrentText("10:00")
    assert dlg.end_date_btn.date() == QDate(2026, 3, 10)
    assert dlg.end_time.currentText() == "11:00"


def test_linked_off_grid_items_do_not_accumulate(dialog_cls):
    dlg = dialog_cls(default_date=QDate(2026, 5, 6))
    dlg._select_time(dlg.end_time, "09:45")  # 長度 45 分（09:45 不在 30 分清單，手動插入）
    base = dlg.end_time.count()
    for t in ("10:00", "11:00", "12:00", "13:00"):
        dlg.start_time.setCurrentText(t)
    assert dlg.end_time.count() <= base + 1
    assert dlg.end_time.currentText() == "13:45"


def test_popup_date_click_emits_only_when_changed(qapp):
    from ui.calendar_dialog import DatePopupButton
    btn = DatePopupButton(QDate(2026, 1, 1))
    got = []
    btn.dateChanged.connect(got.append)
    btn._on_popup_date_clicked(QDate(2026, 1, 1))  # 同一天：不發
    assert got == []
    btn._on_popup_date_clicked(QDate(2026, 1, 5))  # 不同天：發一次
    assert got == [QDate(2026, 1, 5)]
    assert btn.date() == QDate(2026, 1, 5)
