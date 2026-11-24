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
