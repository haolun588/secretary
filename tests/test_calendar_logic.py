from datetime import date, datetime, timedelta

import pytest

from ui import calendar_logic as cl


def ev(title="T", start="2026-03-10", end=None, all_day=True, priority="minor", eid=None):
    return {"id": eid or title, "title": title, "all_day": all_day, "start": start,
            "end": end or start, "priority": priority, "location": "", "notes": ""}


def timed(title, start_hm, end_hm, day="2026-03-10", end_day=None, priority="minor"):
    return ev(title, f"{day}T{start_hm}:00", f"{end_day or day}T{end_hm}:00", all_day=False,
              priority=priority)


# ---------------------------------------------------------------- parse_event_dates

def test_parse_all_day_single():
    assert cl.parse_event_dates(ev(start="2026-03-10")) == (date(2026, 3, 10), date(2026, 3, 10))


def test_parse_all_day_multi_keeps_end():
    assert cl.parse_event_dates(ev(start="2026-03-10", end="2026-03-12")) == (
        date(2026, 3, 10), date(2026, 3, 12))


def test_parse_timed_ending_midnight_steps_back_one_day():
    e = ev(start="2026-03-10T22:00:00", end="2026-03-11T00:00:00", all_day=False)
    assert cl.parse_event_dates(e) == (date(2026, 3, 10), date(2026, 3, 10))


def test_parse_timed_crossing_midnight_covers_two_days():
    e = ev(start="2026-03-10T22:00:00", end="2026-03-11T01:00:00", all_day=False)
    assert cl.parse_event_dates(e)[1] == date(2026, 3, 11)


def test_parse_timed_same_day_midnight_end_not_moved():
    e = ev(start="2026-03-10T00:00:00", end="2026-03-10T00:00:00", all_day=False)
    assert cl.parse_event_dates(e) == (date(2026, 3, 10), date(2026, 3, 10))


def test_parse_all_day_midnight_string_not_moved():
    e = ev(start="2026-03-10", end="2026-03-12T00:00:00", all_day=True)
    assert cl.parse_event_dates(e)[1] == date(2026, 3, 12)


def test_parse_invalid_start_returns_none():
    assert cl.parse_event_dates({"start": "oops"}) is None
    assert cl.parse_event_dates({}) is None


def test_parse_end_before_start_or_missing():
    assert cl.parse_event_dates(ev(start="2026-03-10", end="2026-03-01"))[1] == date(2026, 3, 10)
    assert cl.parse_event_dates({"start": "2026-03-10", "end": None, "all_day": True}) == (
        date(2026, 3, 10), date(2026, 3, 10))
    assert cl.parse_event_dates({"start": "2026-03-10", "end": "garbage", "all_day": True})[1] == date(2026, 3, 10)


def test_parse_across_year_and_leap_day():
    e = ev(start="2026-12-31", end="2027-01-02")
    assert cl.parse_event_dates(e) == (date(2026, 12, 31), date(2027, 1, 2))
    e = ev(start="2028-02-28", end="2028-03-01")
    assert cl.parse_event_dates(e)[1] == date(2028, 3, 1)
    e = ev(start="2028-02-28T23:00:00", end="2028-02-29T00:00:00", all_day=False)
    assert cl.parse_event_dates(e)[1] == date(2028, 2, 28)


# ---------------------------------------------------------------- month / week

def test_month_grid_is_42_days_sunday_first():
    dates = cl.month_grid_dates(2026, 3)   # 2026-03-01 是週日
    assert len(dates) == 42
    assert dates[0] == date(2026, 3, 1)
    assert dates[0].weekday() == 6
    assert dates[-1] == date(2026, 3, 1) + timedelta(days=41)


def test_month_grid_leading_days_from_previous_month():
    dates = cl.month_grid_dates(2026, 4)   # 2026-04-01 是週三 → 前面補 3 天
    assert dates[0] == date(2026, 3, 29)
    assert dates[3] == date(2026, 4, 1)


def test_month_grid_cross_year_and_leap():
    dates = cl.month_grid_dates(2027, 1)
    assert date(2027, 1, 1) in dates and dates[0].year == 2026
    dates = cl.month_grid_dates(2028, 2)
    assert date(2028, 2, 29) in dates
    assert len(set(dates)) == 42


def test_month_grid_monday_first():
    dates = cl.month_grid_dates(2026, 3, first_weekday=0)
    assert dates[0].weekday() == 0
    assert dates[0] == date(2026, 2, 23)


def test_week_dates():
    week = cl.week_dates(date(2026, 3, 10))   # 週二
    assert week[0] == date(2026, 3, 8) and week[-1] == date(2026, 3, 14)
    assert len(week) == 7
    assert cl.week_dates(date(2026, 3, 8))[0] == date(2026, 3, 8)   # 週日自己是起點
    assert cl.week_dates(date(2026, 3, 14))[0] == date(2026, 3, 8)
    assert cl.week_dates(date(2026, 3, 10), first_weekday=0)[0] == date(2026, 3, 9)


def test_week_dates_cross_year():
    week = cl.week_dates(date(2027, 1, 1))
    assert week[0] == date(2026, 12, 27) and week[-1] == date(2027, 1, 2)


def test_view_dates():
    sel = date(2026, 3, 10)
    assert len(cl.view_dates("month", sel)) == 42
    assert len(cl.view_dates("week", sel)) == 7
    assert cl.view_dates("day", sel) == [sel]


def test_fetch_months_for_range():
    assert cl.fetch_months_for_range(date(2026, 3, 10), date(2026, 3, 20)) == [(2026, 3)]
    assert cl.fetch_months_for_range(date(2026, 3, 29), date(2026, 5, 9)) == [
        (2026, 3), (2026, 4), (2026, 5)]
    assert cl.fetch_months_for_range(date(2026, 12, 27), date(2027, 1, 2)) == [(2026, 12), (2027, 1)]
    assert cl.fetch_months_for_range(date(2026, 1, 1), date(2027, 1, 1))[-1] == (2027, 1)
    assert len(cl.fetch_months_for_range(date(2026, 1, 1), date(2027, 1, 1))) == 13
    # 順序顛倒時自動對調
    assert cl.fetch_months_for_range(date(2026, 4, 1), date(2026, 3, 1)) == [(2026, 3), (2026, 4)]


def test_fetch_months_for_month_grid_spans_up_to_three_months():
    months = cl.fetch_months_for_range(*(lambda d: (d[0], d[-1]))(cl.month_grid_dates(2026, 3)))
    assert months[0] == (2026, 3) and months[-1] == (2026, 4)


def test_add_months_clamps_day():
    assert cl.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert cl.add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)
    assert cl.add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)
    assert cl.add_months(date(2026, 1, 15), -1) == date(2025, 12, 15)
    assert cl.add_months(date(2026, 3, 31), -1) == date(2026, 2, 28)


def test_shift_anchor():
    d = date(2026, 3, 10)
    assert cl.shift_anchor(d, "month", 1) == date(2026, 4, 10)
    assert cl.shift_anchor(d, "week", -1) == date(2026, 3, 3)
    assert cl.shift_anchor(d, "day", 1) == date(2026, 3, 11)
    assert cl.shift_anchor(date(2026, 12, 31), "day", 1) == date(2027, 1, 1)


# ---------------------------------------------------------------- events_on

def test_events_on_range_inclusive_and_sorted():
    events = [
        timed("late", "15:00", "16:00", priority="major"),
        timed("early", "09:00", "10:00"),
        ev("allday", start="2026-03-09", end="2026-03-11", priority="minor"),
        ev("other-day", start="2026-03-11"),
    ]
    titles = [e["title"] for e in cl.events_on(events, date(2026, 3, 10))]
    assert titles == ["allday", "early", "late"]


def test_events_on_priority_breaks_tie_and_skips_invalid():
    events = [ev("b", priority="minor"), ev("a", priority="major"), {"start": "bad"}]
    titles = [e["title"] for e in cl.events_on(events, date(2026, 3, 10))]
    assert titles == ["a", "b"]


def test_events_on_midnight_end_not_next_day():
    e = timed("night", "22:00", "00:00", end_day="2026-03-11")
    assert cl.events_on([e], date(2026, 3, 10)) == [e]
    assert cl.events_on([e], date(2026, 3, 11)) == []


def test_events_on_uses_cached_dates():
    e = ev("x", start="2026-03-10")
    e["_d_start"], e["_d_end"] = date(2026, 3, 1), date(2026, 3, 2)
    assert cl.events_on([e], date(2026, 3, 1)) == [e]
    assert cl.events_on([e], date(2026, 3, 10)) == []


# ---------------------------------------------------------------- days_until / upcoming

def test_days_until_and_label():
    today = date(2026, 3, 10)
    assert cl.days_until(today, date(2026, 3, 10)) == 0
    assert cl.days_until(today, date(2026, 3, 9)) == 0   # 進行中
    assert cl.days_until(today, date(2026, 3, 13)) == 3
    assert cl.days_until_label(0) == "今天"
    assert cl.days_until_label(1) == "明天"
    assert cl.days_until_label(5) == "還有 5 天"


def _up(priority, n, today=date(2026, 3, 10)):
    d = today + timedelta(days=n)
    return ev(f"{priority}{n}", start=d.isoformat(), priority=priority)


@pytest.mark.parametrize("priority,limit", [("major", 30), ("medium", 7), ("minor", 3)])
def test_upcoming_thresholds(priority, limit):
    today = date(2026, 3, 10)
    inside = _up(priority, limit)
    outside = _up(priority, limit + 1)
    result = cl.upcoming([inside, outside], today)
    assert [e["title"] for e, _ in result] == [inside["title"]]
    assert result[0][1] == limit


NOW = datetime(2026, 3, 10, 12, 0)


def test_upcoming_ongoing_multi_day_is_zero_and_ended_excluded():
    today = date(2026, 3, 10)
    ongoing = ev("ongoing", start="2026-03-08", end="2026-03-12", priority="minor")
    ended = ev("ended", start="2026-03-01", end="2026-03-09", priority="major")
    ends_today = ev("endsToday", start="2026-03-09", end="2026-03-10", priority="minor")
    result = cl.upcoming([ongoing, ended, ends_today], today, NOW)
    assert {e["title"]: n for e, n in result} == {"ongoing": 0, "endsToday": 0}


def test_upcoming_ongoing_ignores_priority_window():
    ongoing = ev("long", start="2026-01-01", end="2026-12-31", priority="minor")
    assert cl.upcoming([ongoing], date(2026, 3, 10), NOW) == [(ongoing, 0)]


def test_upcoming_excludes_events_starting_today():
    today = date(2026, 3, 10)
    allday = ev("todayAll", start="2026-03-10", priority="major")
    timed_today = timed("todayTimed", "15:00", "16:00", priority="major")
    tomorrow = _up("major", 1)
    result = cl.upcoming([allday, timed_today, tomorrow], today, NOW)
    assert [e["title"] for e, _ in result] == ["major1"]


def test_upcoming_timed_event_ending_at_or_before_now_excluded():
    today = date(2026, 3, 10)
    finished = ev("fin", start="2026-03-09T20:00:00", end="2026-03-10T11:00:00", all_day=False)
    ends_exact = ev("exact", start="2026-03-09T20:00:00", end="2026-03-10T12:00:00", all_day=False)
    running = ev("run", start="2026-03-09T20:00:00", end="2026-03-10T12:01:00", all_day=False)
    result = cl.upcoming([finished, ends_exact, running], today, NOW)
    assert [e["title"] for e, _ in result] == ["run"]


def test_upcoming_timed_event_ending_midnight_yesterday_excluded():
    today = date(2026, 3, 10)
    e = ev("nightShift", start="2026-03-09T22:00:00", end="2026-03-10T00:00:00", all_day=False)
    assert cl.upcoming([e], today, NOW) == []


def test_upcoming_now_defaults_to_current_time():
    today = date.today()
    e = ev("far", start=(today + timedelta(days=1)).isoformat(), priority="major")
    assert cl.upcoming([e], today) == [(e, 1)]


def test_upcoming_sorted_by_days_then_time():
    today = date(2026, 3, 10)
    a = timed("a", "15:00", "16:00", day="2026-03-11", priority="major")
    b = timed("b", "09:00", "10:00", day="2026-03-11", priority="major")
    ongoing = ev("on", start="2026-03-09", end="2026-03-11", priority="major")
    d = _up("major", 20)
    result = cl.upcoming([d, a, b, ongoing], today, NOW)
    assert [e["title"] for e, _ in result] == ["on", "b", "a", "major20"]


def test_upcoming_unknown_priority_treated_as_minor_and_skips_invalid():
    today = date(2026, 3, 10)
    odd = ev("odd", start="2026-03-14", priority="???")
    near = ev("near", start="2026-03-12", priority=None)
    result = cl.upcoming([odd, near, {"start": "bad"}], today, NOW)
    assert [e["title"] for e, _ in result] == ["near"]


def test_upcoming_across_year_boundary():
    today = date(2026, 12, 25)
    e = ev("ny", start="2027-01-10", priority="major")   # 16 天
    assert cl.upcoming([e], today, datetime(2026, 12, 25, 8)) == [(e, 16)]


def test_upcoming_leap_day():
    today = date(2028, 2, 27)
    e = ev("leap", start="2028-02-29", priority="medium")
    assert cl.upcoming([e], today, datetime(2028, 2, 27, 8)) == [(e, 2)]


def test_upcoming_subtitle():
    today = date(2026, 3, 10)
    assert cl.upcoming_subtitle(_up("major", 1), 1) == "3/11 週三 · 明天"
    assert cl.upcoming_subtitle(_up("major", 5), 5) == "3/15 週日 · 還有 5 天"
    multi = ev("m", start="2026-03-08", end="2026-03-12")
    assert cl.upcoming_subtitle(multi, 0) == "3/8–3/12 · 進行中"
    single = ev("s", start="2026-03-10")
    assert cl.upcoming_subtitle(single, 0) == "進行中"
    assert today  # 只為語意：副標不依賴 today，由 n 決定


def test_priority_window_hint_built_from_tokens():
    assert cl.priority_window_hint() == "大型行程 30 天內、中型 7 天內、小型 3 天內會出現在這裡"


def test_title_width_samples_per_mode():
    assert cl.title_width_samples("month") == ["0000 年 00 月"]
    assert any("週" in t for t in cl.title_width_samples("day"))
    assert len(cl.title_width_samples("week")) == 2


def test_parse_timed_date_only_end_is_midnight_and_steps_back():
    e = {"start": "2026-03-10T22:00:00", "end": "2026-03-11", "all_day": False}
    assert cl.parse_event_times(e) == (datetime(2026, 3, 10, 22), datetime(2026, 3, 11))
    assert cl.parse_event_dates(e) == (date(2026, 3, 10), date(2026, 3, 10))
    layout = cl.timed_layout([e], date(2026, 3, 10))
    assert (layout[0][1], layout[0][2]) == (22 * 60, 1440)
    assert cl.timed_layout([e], date(2026, 3, 11)) == []


# ---------------------------------------------------------------- timed_layout

def test_timed_layout_three_overlapping_get_three_columns():
    events = [timed("a", "09:00", "11:00"), timed("b", "09:30", "10:30"), timed("c", "10:00", "12:00")]
    layout = cl.timed_layout(events, date(2026, 3, 10))
    assert len(layout) == 3
    assert {item[4] for item in layout} == {3}
    assert sorted(item[3] for item in layout) == [0, 1, 2]


def test_timed_layout_non_overlapping_same_column():
    events = [timed("a", "09:00", "10:00"), timed("b", "10:00", "11:00"), timed("c", "13:00", "14:00")]
    layout = cl.timed_layout(events, date(2026, 3, 10))
    assert [(item[3], item[4]) for item in layout] == [(0, 1), (0, 1), (0, 1)]


def test_timed_layout_column_reuse_within_cluster():
    # a 9-11, b 10-12 重疊；c 11-12 可重用 a 的欄 → 共 2 欄
    events = [timed("a", "09:00", "11:00"), timed("b", "10:00", "12:00"), timed("c", "11:00", "12:00")]
    layout = {item[0]["title"]: item for item in cl.timed_layout(events, date(2026, 3, 10))}
    assert layout["a"][3] == 0 and layout["b"][3] == 1 and layout["c"][3] == 0
    assert {item[4] for item in layout.values()} == {2}


def test_timed_layout_clusters_are_independent():
    events = [timed("a", "09:00", "10:00"), timed("b", "09:30", "10:30"), timed("c", "15:00", "16:00")]
    layout = {item[0]["title"]: item for item in cl.timed_layout(events, date(2026, 3, 10))}
    assert layout["a"][4] == 2 and layout["b"][4] == 2 and layout["c"][4] == 1


def test_timed_layout_minutes_and_skips_all_day():
    events = [timed("a", "09:15", "10:45"), ev("allday", start="2026-03-10")]
    layout = cl.timed_layout(events, date(2026, 3, 10))
    assert len(layout) == 1
    _, s, e, col, count = layout[0]
    assert (s, e, col, count) == (9 * 60 + 15, 10 * 60 + 45, 0, 1)


def test_timed_layout_cross_midnight_clipped_each_day():
    e = timed("night", "22:00", "01:30", end_day="2026-03-11")
    day1 = cl.timed_layout([e], date(2026, 3, 10))
    day2 = cl.timed_layout([e], date(2026, 3, 11))
    assert (day1[0][1], day1[0][2]) == (22 * 60, 1440)
    assert (day2[0][1], day2[0][2]) == (0, 90)
    assert cl.timed_layout([e], date(2026, 3, 12)) == []
    assert cl.timed_layout([e], date(2026, 3, 9)) == []


def test_timed_layout_ending_at_midnight_clips_to_1440_and_not_next_day():
    e = timed("night", "22:00", "00:00", end_day="2026-03-11")
    assert cl.timed_layout([e], date(2026, 3, 10))[0][2] == 1440
    assert cl.timed_layout([e], date(2026, 3, 11)) == []


def test_timed_layout_short_event_gets_minimum_length():
    e = timed("blip", "09:00", "09:05")
    _, s, end, _, _ = cl.timed_layout([e], date(2026, 3, 10))[0]
    assert end - s == cl.MIN_DISPLAY_MINUTES
    z = timed("zero", "09:00", "09:00")
    assert cl.timed_layout([z], date(2026, 3, 10))[0][2] == 9 * 60 + cl.MIN_DISPLAY_MINUTES
    late = timed("late", "23:50", "23:55")
    _, s, end, _, _ = cl.timed_layout([late], date(2026, 3, 10))[0]
    assert end == 1440 and s == 23 * 60 + 50


def test_timed_layout_skips_invalid():
    assert cl.timed_layout([{"start": "bad", "all_day": False}], date(2026, 3, 10)) == []


# ---------------------------------------------------------------- 文字

def test_weekday_and_short_date():
    assert cl.weekday_label(date(2026, 3, 8)) == "週日"
    assert cl.weekday_label(date(2026, 3, 9)) == "週一"
    assert cl.short_date(date(2026, 3, 8)) == "3/8"


def test_event_time_text():
    assert cl.event_time_text(ev(start="2026-03-10")) == "全天"
    assert cl.event_time_text(timed("a", "09:00", "10:30")) == "09:00 - 10:30"
    assert cl.event_time_text({"all_day": False, "start": "2026-03-10T09:00:00", "end": ""}) == "09:00"


def test_minute_label():
    assert cl.minute_label(0) == "00:00"
    assert cl.minute_label(9 * 60 + 5) == "09:05"
    assert cl.minute_label(1440) == "24:00"


def test_format_view_title():
    sel = date(2026, 3, 10)
    assert cl.format_view_title("month", sel) == "2026 年 3 月"
    assert cl.format_view_title("day", sel) == "2026 年 3 月 10 日 週二"
    assert cl.format_view_title("week", sel) == "2026 年 3 月"
    assert cl.format_view_title("week", date(2026, 3, 30)) == "2026 年 3–4 月"
    assert cl.format_view_title("week", date(2026, 12, 30)) == "2026 年 12 月 – 2027 年 1 月"


def test_selected_title():
    today = date(2026, 3, 10)
    assert cl.selected_title(today, today) == "今天 3/10"
    assert cl.selected_title(date(2026, 3, 11), today) == "3/11 週三"
