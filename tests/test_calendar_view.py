import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtCore import QDate  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui import theme  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    try:
        return QApplication.instance() or QApplication([])
    except Exception as e:
        pytest.skip(f"無法建立 QApplication: {e}")


@pytest.fixture
def view(qapp, tmp_path):
    from services.event_store import EventStore
    from ui.calendar_view import CalendarView
    # runner 不執行任何工作：不連網、不開執行緒
    store = EventStore(runner=lambda fn, ok, err: None, oauth_runner=lambda fn, ok, err: None,
                       token_path=str(tmp_path / "t.json"),
                       credentials_path=str(tmp_path / "c.json"))
    return CalendarView(store)


def _ev(event_id, start, end, all_day=False):
    return {"id": event_id, "title": "T", "all_day": all_day, "start": start, "end": end,
            "priority": "minor", "location": "", "notes": "", "color_id": None}


def test_timed_event_ending_at_midnight_does_not_occupy_next_day(view):
    view.on_events_changed([_ev("a", "2026-03-10T22:00:00", "2026-03-11T00:00:00")])
    item = view._events[0]
    assert item["_qdate_start"] == QDate(2026, 3, 10)
    assert item["_qdate_end"] == QDate(2026, 3, 10)


def test_timed_event_crossing_midnight_covers_both_days(view):
    view.on_events_changed([_ev("a", "2026-03-10T22:00:00", "2026-03-11T01:00:00")])
    assert view._events[0]["_qdate_end"] == QDate(2026, 3, 11)


def test_all_day_multi_day_keeps_end(view):
    view.on_events_changed([_ev("a", "2026-03-10", "2026-03-12", all_day=True)])
    assert view._events[0]["_qdate_end"] == QDate(2026, 3, 12)


def test_store_dict_not_polluted(view):
    ev = _ev("a", "2026-03-10", "2026-03-10", all_day=True)
    view.on_events_changed([ev])
    assert "_qdate_start" not in ev


def test_sync_click_unauthorized_gives_feedback(view, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox
    calls = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: calls.append(a))
    view.on_sync_clicked()
    assert len(calls) == 1
    assert "設定頁授權" in view.sync_btn.toolTip()


def test_timer_sync_unauthorized_is_silent(view, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox
    calls = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: calls.append(a))
    view.sync_google_events()
    assert calls == []


# ---------------------------------------------------------------- 批次 3：日曆頁行為

TODAY = date(2026, 3, 10)


@pytest.fixture
def cview(view):
    """固定「今天」為 2026-03-10 的 CalendarView。"""
    view._today = lambda: TODAY
    view._selected = TODAY
    view.month_grid._today = lambda: TODAY
    view.time_grid._today = lambda: TODAY
    view._ensured_key = None
    view._refresh_all()
    return view


def _record_ensure(view, monkeypatch):
    calls = []
    monkeypatch.setattr(view.event_store, "ensure_month", lambda y, m: calls.append((y, m)))
    return calls


def test_initial_ensure_month_called_once(qapp, tmp_path, monkeypatch):
    from services.event_store import EventStore
    from ui.calendar_view import CalendarView
    calls = []
    monkeypatch.setattr(EventStore, "ensure_month", lambda self, y, m: calls.append((y, m)))
    store = EventStore(runner=lambda fn, ok, err: None, oauth_runner=lambda fn, ok, err: None,
                       token_path=str(tmp_path / "t.json"), credentials_path=str(tmp_path / "c.json"))
    v = CalendarView(store)
    today = date.today()
    assert calls == [(today.year, today.month)]
    assert v.view_mode() == "month"


def test_title_and_navigation_per_view(cview):
    assert cview.title_label.text() == "2026 年 3 月"
    cview.navigate(1)
    assert cview.selected_date() == date(2026, 4, 10)
    assert cview.title_label.text() == "2026 年 4 月"
    cview.go_today()
    assert cview.selected_date() == TODAY

    cview.set_view_mode("week")
    assert cview.view_seg.current() == "week"
    assert cview.time_grid.days()[0] == date(2026, 3, 8) and len(cview.time_grid.days()) == 7
    cview.navigate(1)
    assert cview.selected_date() == date(2026, 3, 17)
    cview.navigate(-2)
    assert cview.selected_date() == date(2026, 3, 3)

    cview.set_view_mode("day")
    assert cview.time_grid.days() == [date(2026, 3, 3)]
    assert cview.title_label.text() == "2026 年 3 月 3 日 週二"
    cview.navigate(1)
    assert cview.selected_date() == date(2026, 3, 4)


def test_week_title_crosses_month(cview):
    cview.set_view_mode("week")
    cview.set_selected_date(date(2026, 3, 31))
    assert cview.title_label.text() == "2026 年 3–4 月"


def test_ensure_month_anchor_per_view(cview, monkeypatch):
    calls = _record_ensure(cview, monkeypatch)
    cview.set_selected_date(date(2026, 3, 20))      # 月視圖同月，不重複
    assert calls == []
    cview.set_view_mode("week")                     # 週 3/15–3/21，anchor 仍是 3 月
    assert calls == []
    cview.set_selected_date(date(2026, 3, 31))      # 週 3/29–4/4：anchor 取週第一天所在月份（3 月）
    cview.set_selected_date(date(2026, 4, 2))       # 同一週內點跨月日期，不重拉
    assert calls == []
    cview.navigate(1)                               # 週 4/5–4/11 -> 4 月
    assert calls == [(2026, 4)]
    cview.set_selected_date(date(2026, 4, 10))      # 同週
    assert calls == [(2026, 4)]
    cview.set_view_mode("day")                      # 日視圖用選取日月份（4 月），沒變
    assert calls == [(2026, 4)]
    cview.set_selected_date(date(2026, 5, 2))
    assert calls == [(2026, 4), (2026, 5)]
    cview.set_view_mode("week")                     # 週 4/26–5/2，anchor = 4 月
    assert calls[-1] == (2026, 4)


def test_title_width_reserved_per_mode(cview):
    cview.set_view_mode("month")
    month_w = cview.title_label.minimumWidth()
    cview.set_view_mode("day")
    day_w = cview.title_label.minimumWidth()
    cview.set_view_mode("week")
    week_w = cview.title_label.minimumWidth()
    assert 0 < month_w < day_w
    assert week_w >= month_w


def test_selected_date_drives_side_panel_title(cview):
    assert cview.side_panel.selected_title.text() == "今天 3/10"
    cview.set_selected_date(date(2026, 3, 11))
    assert cview.side_panel.selected_title.text() == "3/11 週三"


def test_events_flow_to_grid_and_panel(cview):
    evs = [_ev("a", "2026-03-10", "2026-03-10", all_day=True),
           {**_ev("b", "2026-03-10T09:00:00", "2026-03-10T10:00:00"), "priority": "major"},
           _ev("c", "2026-03-11", "2026-03-11", all_day=True)]
    cview.month_grid.resize(700, 600)     # 未顯示的 widget 不會自動版面計算
    cview.on_events_changed(evs)
    assert cview.side_panel.selected_row_count() == 2
    assert cview.side_panel.upcoming_row_count() == 1      # 只有明天的 c；今天開始的 a、b 在日清單
    idx = cview.month_grid.dates().index(TODAY)
    assert len(cview.month_grid.chip_layout(idx)[0]) == 2
    cview.on_events_changed([])
    assert cview.side_panel.selected_row_count() == 0
    assert cview._events == []


def test_invalid_events_skipped_and_store_not_polluted(cview):
    ev = _ev("a", "2026-03-10", "2026-03-10", all_day=True)
    cview.on_events_changed([ev, {"id": "x", "title": "bad", "start": "oops"}])
    assert len(cview._events) == 1
    assert "_d_start" not in ev and "_qdate_start" not in ev
    assert cview._events[0]["_d_start"] == TODAY


def test_events_reach_time_grid_after_switching_view(cview):
    cview.on_events_changed([_ev("a", "2026-03-10T09:00:00", "2026-03-10T10:00:00")])
    cview.set_view_mode("week")
    assert len(cview.time_grid.hours.blocks()) == 1


def test_sync_state_updates_badge(cview):
    cview.on_sync_state_changed("syncing", "")
    assert cview.sync_btn.state() == "syncing"
    cview.on_sync_state_changed("error", "網路錯誤")
    assert cview.sync_btn.state() == "error"
    assert cview.sync_btn.toolTip() == "網路錯誤"


def test_toolbar_has_no_legacy_buttons_or_emoji(cview):
    from PyQt6.QtWidgets import QPushButton
    texts = [b.text() for b in cview.findChildren(QPushButton)]
    for legacy in ("日時間軸", "月網格", "雲端同步"):
        assert not any(legacy in t for t in texts)
    assert not any(ord(ch) >= 0x1F000 or 0x2600 <= ord(ch) <= 0x27BF for t in texts for ch in t)
    assert cview.btn_add.property("variant") == "primary"
    assert cview.btn_today.property("variant") == "secondary"


class _FakeDialog:
    """CalendarDialog 替身：記錄建構參數，exec 回傳預設結果。"""
    result = 1
    delete_flag = False
    last = None

    class DialogCode:
        Accepted = 1
        Rejected = 0

    def __init__(self, parent=None, event_data=None, default_date=None):
        type(self).last = self
        self.event_data, self.default_date = event_data, default_date
        self.is_delete = type(self).delete_flag

    def exec(self):
        return type(self).result

    def get_data(self):
        return {"title": "新"}


def _patch_dialog(monkeypatch, result, is_delete=False):
    import ui.calendar_view as cvmod
    cls = type("D", (_FakeDialog,), {"result": result, "delete_flag": is_delete})
    monkeypatch.setattr(cvmod, "CalendarDialog", cls)
    return cls


def test_add_event_uses_selected_date_and_calls_store(cview, monkeypatch):
    added = []
    monkeypatch.setattr(cview.event_store, "add_event", lambda d: added.append(d))
    cview.set_selected_date(date(2026, 3, 18))
    cls = _patch_dialog(monkeypatch, 1)
    cview.on_add_event_clicked()
    assert added == [{"title": "新"}]
    assert cls.last.default_date == QDate(2026, 3, 18)


def test_add_event_cancelled_does_nothing(cview, monkeypatch):
    added = []
    monkeypatch.setattr(cview.event_store, "add_event", lambda d: added.append(d))
    _patch_dialog(monkeypatch, 0)
    cview.on_add_event_clicked()
    assert added == []


def test_double_click_date_opens_dialog_with_that_date(cview, monkeypatch):
    monkeypatch.setattr(cview.event_store, "add_event", lambda d: None)
    cls = _patch_dialog(monkeypatch, 0)
    cview.month_grid.date_activated.emit(date(2026, 3, 25))
    assert cls.last.default_date == QDate(2026, 3, 25)


def test_edit_event_update_and_delete_paths(cview, monkeypatch):
    updated, deleted = [], []
    monkeypatch.setattr(cview.event_store, "update_event", lambda i, d: updated.append((i, d)))
    monkeypatch.setattr(cview.event_store, "delete_event", lambda i: deleted.append(i))
    evt = _ev("a", "2026-03-10", "2026-03-10", all_day=True)

    _patch_dialog(monkeypatch, 1)
    cview.on_edit_event(evt)
    assert updated == [("a", {"title": "新"})] and deleted == []

    _patch_dialog(monkeypatch, 2)           # done(2) 表刪除
    cview.on_edit_event(evt)
    assert deleted == ["a"]

    deleted.clear()
    _patch_dialog(monkeypatch, 0, is_delete=True)
    cview.on_edit_event(evt)
    assert deleted == ["a"]


def test_grid_and_panel_event_signals_open_edit_dialog(cview, monkeypatch):
    updated = []
    monkeypatch.setattr(cview.event_store, "update_event", lambda i, d: updated.append(i))
    cls = _patch_dialog(monkeypatch, 1)
    evt = {"id": "a"}
    for sig in (cview.month_grid.event_activated, cview.time_grid.event_activated,
                cview.side_panel.event_activated):
        sig.emit(evt)
        assert cls.last.event_data is evt
    assert updated == ["a", "a", "a"]


def test_view_grabs_in_all_modes(cview):
    cview.resize(theme.WINDOW_W - theme.NAV_WIDTH, theme.WINDOW_H)
    cview.on_events_changed([_ev("a", "2026-03-10T09:00:00", "2026-03-10T10:00:00")])
    for mode in ("month", "week", "day"):
        cview.set_view_mode(mode)
        assert not cview.grab().isNull()
