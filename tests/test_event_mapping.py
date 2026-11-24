from datetime import date, timedelta, timezone

import pytest

from services import event_mapping as m

TZ8 = timezone(timedelta(hours=8))


def test_maps_are_consistent():
    for priority, color_id in m.PRIORITY_COLOR_MAP.items():
        assert m.COLOR_PRIORITY_MAP[color_id] == priority


@pytest.mark.parametrize("color,expected", [
    ("11", "major"), ("4", "major"), ("5", "medium"), ("6", "medium"),
    ("2", "minor"), ("10", "minor"), (11, "major"), (5, "medium"),
    ("1", "minor"), ("999", "minor"), (None, "minor"), ("", "minor"),
])
def test_priority_from_color(color, expected):
    assert m.priority_from_color(color) == expected


def test_priority_from_color_default():
    assert m.priority_from_color(None, default="medium") == "medium"


def test_color_from_priority():
    assert m.color_from_priority("major") == "11"
    assert m.color_from_priority("medium") == "5"
    assert m.color_from_priority("minor") == "2"
    assert m.color_from_priority("unknown") == "2"
    assert m.color_from_priority(None) == "2"


def test_from_google_all_day_single():
    item = {"id": "a", "summary": "T", "start": {"date": "2026-03-10"},
            "end": {"date": "2026-03-11"}, "colorId": "11"}
    ev = m.from_google(item, TZ8)
    assert ev["all_day"] is True
    assert ev["start"] == "2026-03-10"
    assert ev["end"] == "2026-03-10"
    assert ev["priority"] == "major"
    assert ev["color_id"] == "11"
    assert ev["id"] == "a"


def test_from_google_all_day_multi_day():
    item = {"id": "a", "start": {"date": "2026-03-10"}, "end": {"date": "2026-03-13"}}
    ev = m.from_google(item, TZ8)
    assert (ev["start"], ev["end"]) == ("2026-03-10", "2026-03-12")


def test_from_google_all_day_missing_end():
    ev = m.from_google({"id": "a", "start": {"date": "2026-03-10"}}, TZ8)
    assert ev["end"] == "2026-03-10"


def test_from_google_all_day_end_not_after_start_clamped():
    item = {"id": "a", "start": {"date": "2026-03-10"}, "end": {"date": "2026-03-10"}}
    assert m.from_google(item, TZ8)["end"] == "2026-03-10"


def test_from_google_defaults():
    ev = m.from_google({"id": "a", "start": {"date": "2026-03-10"}}, TZ8)
    assert ev["title"] == "無標題行程"
    assert ev["location"] == ""
    assert ev["notes"] == ""
    assert ev["priority"] == "minor"
    assert ev["color_id"] is None


@pytest.mark.parametrize("start,end,exp_start,exp_end", [
    ("2026-03-10T01:00:00Z", "2026-03-10T02:30:00Z",
     "2026-03-10T09:00:00", "2026-03-10T10:30:00"),
    ("2026-03-10T09:00:00+08:00", "2026-03-10T10:00:00+08:00",
     "2026-03-10T09:00:00", "2026-03-10T10:00:00"),
    ("2026-03-09T20:00:00-05:00", "2026-03-09T21:00:00-05:00",
     "2026-03-10T09:00:00", "2026-03-10T10:00:00"),
])
def test_from_google_timed_converts_to_tz(start, end, exp_start, exp_end):
    item = {"id": "a", "start": {"dateTime": start}, "end": {"dateTime": end}}
    ev = m.from_google(item, TZ8)
    assert ev["all_day"] is False
    assert ev["start"] == exp_start
    assert ev["end"] == exp_end


def test_from_google_timed_naive_treated_as_tz():
    item = {"id": "a", "start": {"dateTime": "2026-03-10T09:00:00"},
            "end": {"dateTime": "2026-03-10T10:00:00"}}
    assert m.from_google(item, TZ8)["start"] == "2026-03-10T09:00:00"


def test_to_google_body_all_day_end_plus_one():
    ev = {"title": "T", "all_day": True, "start": "2026-03-10", "end": "2026-03-12",
          "priority": "major", "location": "L", "notes": "N"}
    body = m.to_google_body(ev, TZ8)
    assert body["start"] == {"date": "2026-03-10"}
    assert body["end"] == {"date": "2026-03-13"}
    assert body["colorId"] == "11"
    assert body["summary"] == "T"
    assert body["location"] == "L"
    assert body["description"] == "N"


def test_to_google_body_timed_has_offset_no_timezone_key():
    ev = {"title": "T", "all_day": False, "start": "2026-03-10T09:00:00",
          "end": "2026-03-10T10:00:00", "priority": "minor"}
    body = m.to_google_body(ev, TZ8)
    assert body["start"] == {"dateTime": "2026-03-10T09:00:00+08:00"}
    assert body["end"] == {"dateTime": "2026-03-10T10:00:00+08:00"}
    assert "timeZone" not in body["start"]
    assert "Asia/Taipei" not in str(body)


def test_to_google_body_uses_injected_tz_not_hardcoded():
    tz = timezone(timedelta(hours=-5))
    ev = {"title": "T", "all_day": False, "start": "2026-03-10T09:00:00",
          "end": "2026-03-10T10:00:00", "priority": "minor"}
    assert m.to_google_body(ev, tz)["start"]["dateTime"].endswith("-05:00")


def _base():
    return {"id": "a", "title": "T", "all_day": False, "start": "2026-03-10T09:00:00",
            "end": "2026-03-10T10:00:00", "priority": "minor", "location": "", "notes": "",
            "color_id": None}


def test_patch_no_change():
    assert m.build_patch_body(_base(), _base(), TZ8) == {}


def test_patch_title_only():
    new = {**_base(), "title": "X"}
    assert m.build_patch_body(_base(), new, TZ8) == {"summary": "X"}


def test_patch_priority_unchanged_no_color():
    old = {**_base(), "color_id": "3"}
    new = {**old, "title": "X"}
    assert "colorId" not in m.build_patch_body(old, new, TZ8)


def test_patch_priority_changed_sends_color():
    new = {**_base(), "priority": "major"}
    assert m.build_patch_body(_base(), new, TZ8) == {
        "colorId": "11",
        "extendedProperties": {"private": {"secretary_priority": "major"}},
    }


def test_patch_location_notes():
    new = {**_base(), "location": "L", "notes": "N"}
    assert m.build_patch_body(_base(), new, TZ8) == {"location": "L", "description": "N"}


def test_patch_time_change_sends_both_start_end():
    new = {**_base(), "end": "2026-03-10T11:00:00"}
    body = m.build_patch_body(_base(), new, TZ8)
    assert set(body) == {"start", "end"}
    assert body["start"] == {"dateTime": "2026-03-10T09:00:00+08:00", "date": None}
    assert body["end"] == {"dateTime": "2026-03-10T11:00:00+08:00", "date": None}


def test_patch_timed_to_all_day():
    new = {**_base(), "all_day": True, "start": "2026-03-10", "end": "2026-03-10"}
    body = m.build_patch_body(_base(), new, TZ8)
    assert body["start"] == {"date": "2026-03-10", "dateTime": None}
    assert body["end"] == {"date": "2026-03-11", "dateTime": None}


def test_patch_all_day_to_timed():
    old = {**_base(), "all_day": True, "start": "2026-03-10", "end": "2026-03-10"}
    body = m.build_patch_body(old, _base(), TZ8)
    assert body["start"] == {"dateTime": "2026-03-10T09:00:00+08:00", "date": None}
    assert body["end"] == {"dateTime": "2026-03-10T10:00:00+08:00", "date": None}


@pytest.mark.parametrize("year,month,exp_start,exp_end", [
    (2026, 5, date(2026, 4, 1), date(2026, 7, 1)),
    (2026, 1, date(2025, 12, 1), date(2026, 3, 1)),
    (2026, 12, date(2026, 11, 1), date(2027, 2, 1)),
])
def test_month_range(year, month, exp_start, exp_end):
    assert m.month_range(year, month) == (exp_start, exp_end)


def test_month_range_margin_zero():
    assert m.month_range(2026, 12, margin_months=0) == (date(2026, 12, 1), date(2027, 1, 1))


def test_to_rfc3339_midnight_local():
    assert m.to_rfc3339(date(2026, 3, 10), TZ8) == "2026-03-10T00:00:00+08:00"


def test_patch_text_whitespace_only_difference_is_no_change():
    old = {**_base(), "title": "  T  ", "location": " L ", "notes": "\nN\n"}
    new = {**old, "title": "T", "location": "L", "notes": "N"}
    assert m.build_patch_body(old, new, TZ8) == {}


def test_patch_text_sends_stripped_new_value():
    new = {**_base(), "title": "  X  ", "location": " L ", "notes": " N "}
    body = m.build_patch_body(_base(), new, TZ8)
    assert body == {"summary": "X", "location": "L", "description": "N"}


def _item(color=None, ext="__none__"):
    item = {"id": "a", "start": {"date": "2026-03-10"}}
    if color is not None:
        item["colorId"] = color
    if ext != "__none__":
        item["extendedProperties"] = ext
    return item


def test_priority_from_item_ext_overrides_color():
    item = _item("11", {"private": {"secretary_priority": "minor"}})
    assert m.priority_from_item(item) == "minor"
    assert m.from_google(item, TZ8)["priority"] == "minor"


@pytest.mark.parametrize("bad", ["urgent", 123, "", None, ["major"]])
def test_priority_from_item_invalid_ext_falls_back_to_color(bad):
    item = _item("11", {"private": {"secretary_priority": bad}})
    assert m.priority_from_item(item) == "major"


@pytest.mark.parametrize("ext", [
    "__none__", None, {}, {"private": None}, {"private": {}}, {"shared": {}}, "oops",
    {"private": "oops"},
])
def test_priority_from_item_missing_ext_falls_back_to_color(ext):
    assert m.priority_from_item(_item("5", ext)) == "medium"
    assert m.priority_from_item(_item(None, ext), default="minor") == "minor"


def test_to_google_body_has_extended_priority():
    for pri in ("major", "medium", "minor"):
        ev = {"title": "T", "all_day": True, "start": "2026-03-10", "priority": pri}
        body = m.to_google_body(ev, TZ8)
        assert body["extendedProperties"] == {"private": {"secretary_priority": pri}}


def test_to_google_body_unknown_priority_writes_minor():
    ev = {"title": "T", "all_day": True, "start": "2026-03-10", "priority": "weird"}
    body = m.to_google_body(ev, TZ8)
    assert body["extendedProperties"]["private"]["secretary_priority"] == "minor"
    assert body["colorId"] == "2"


def test_patch_priority_unchanged_no_extended_properties():
    new = {**_base(), "title": "X"}
    assert "extendedProperties" not in m.build_patch_body(_base(), new, TZ8)


def test_from_google_then_patch_same_data_is_empty():
    item = _item("11", {"private": {"secretary_priority": "minor"}})
    ev = m.from_google(item, TZ8)
    assert m.build_patch_body(ev, dict(ev), TZ8) == {}
