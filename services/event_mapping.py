"""
services/event_mapping.py
Google 事件 <-> 內部 event dict 的純函式對應。不 import Qt、不連網。

內部 event dict：
    id, title, all_day, start, end, priority, location, notes, color_id
    - all_day: start/end 為 "YYYY-MM-DD"，end 含當天（= Google end.date - 1 天）
    - 定時:    start/end 為 "YYYY-MM-DDTHH:MM:SS"（已轉為本機時區的 naive 字串）
"""

from datetime import date, datetime, time, timedelta

COLOR_PRIORITY_MAP = {
    "11": "major",   # Tomato (番茄大紅)
    "4": "major",    # Flamingo (火鶴粉紅)
    "5": "medium",   # Banana (香蕉鮮黃)
    "6": "medium",   # Tangerine (柑橘亮橘)
    "2": "minor",    # Sage (鼠尾草淺綠)
    "10": "minor",   # Basil (羅勒深綠)
}

PRIORITY_COLOR_MAP = {
    "major": "11",
    "medium": "5",
    "minor": "2",
}

DEFAULT_TITLE = "無標題行程"


def priority_from_color(color_id, default="minor"):
    """Google colorId -> 等級；未知或空值回傳 default"""
    if color_id is None or color_id == "":
        return default
    return COLOR_PRIORITY_MAP.get(str(color_id), default)


def color_from_priority(priority):
    """等級 -> Google colorId；未知等級回傳 "2"（小事件）"""
    return PRIORITY_COLOR_MAP.get(priority, "2")


def local_tz():
    """目前本機時區（含 DST 當下偏移）"""
    return datetime.now().astimezone().tzinfo


def _tz(tz):
    return tz if tz is not None else local_tz()


def _parse_date(text):
    return date.fromisoformat(text[:10])


def _fmt_naive(dt):
    return dt.replace(tzinfo=None).isoformat(timespec="seconds")


def _aware(text, tz):
    """解析 ISO 字串為 aware datetime；無 offset 時視為 tz。"""
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt


def from_google(item, tz=None):
    """Google event resource -> 內部 event dict"""
    tz = _tz(tz)
    start_raw = item.get("start") or {}
    end_raw = item.get("end") or {}

    if "date" in start_raw:
        all_day = True
        start_d = _parse_date(start_raw["date"])
        if end_raw.get("date"):
            end_d = _parse_date(end_raw["date"]) - timedelta(days=1)
            if end_d < start_d:
                end_d = start_d
        else:
            end_d = start_d
        start = start_d.isoformat()
        end = end_d.isoformat()
    else:
        all_day = False
        start_dt = _aware(start_raw["dateTime"], tz).astimezone(tz)
        if end_raw.get("dateTime"):
            end_dt = _aware(end_raw["dateTime"], tz).astimezone(tz)
        else:
            end_dt = start_dt
        start = _fmt_naive(start_dt)
        end = _fmt_naive(end_dt)

    color_id = item.get("colorId")
    return {
        "id": item.get("id"),
        "title": item.get("summary") or DEFAULT_TITLE,
        "all_day": all_day,
        "start": start,
        "end": end,
        "priority": priority_from_color(color_id),
        "location": item.get("location", "") or "",
        "notes": item.get("description", "") or "",
        "color_id": str(color_id) if color_id is not None else None,
    }


def _is_all_day(ev):
    if "all_day" in ev:
        return bool(ev["all_day"])
    return "T" not in str(ev.get("start", ""))


def _time_fields(ev, tz):
    """回傳 (start_field, end_field)，供 insert / patch 共用。"""
    if _is_all_day(ev):
        start_d = _parse_date(ev["start"])
        end_d = _parse_date(ev.get("end") or ev["start"])
        if end_d < start_d:
            end_d = start_d
        return (
            {"date": start_d.isoformat()},
            {"date": (end_d + timedelta(days=1)).isoformat()},
        )
    start_dt = _aware(ev["start"], tz)
    end_dt = _aware(ev.get("end") or ev["start"], tz)
    return {"dateTime": start_dt.isoformat()}, {"dateTime": end_dt.isoformat()}


def to_google_body(ev, tz=None):
    """內部 event dict -> Google insert 用完整 body"""
    tz = _tz(tz)
    start, end = _time_fields(ev, tz)
    return {
        "summary": ev.get("title") or "新行程",
        "location": ev.get("location", "") or "",
        "description": ev.get("notes", "") or "",
        "colorId": color_from_priority(ev.get("priority", "minor")),
        "start": start,
        "end": end,
    }


def build_patch_body(old, new, tz=None):
    """只包含變動欄位的 patch body；無變動回傳 {}。
    start/end 任一或 all_day 變動時，同時送 start 與 end，
    並把另一種型態的 key 設為 None 以清除（全天 <-> 定時切換）。"""
    tz = _tz(tz)
    new = {**old, **new}
    body = {}

    # 文字欄位前後空白視為相同（對話框會 strip），避免未改動也送 patch；新值仍送 strip 後的
    new_title = (new.get("title") or "").strip()
    if new_title != (old.get("title") or "").strip():
        body["summary"] = new_title or "行程"
    new_location = (new.get("location") or "").strip()
    if new_location != (old.get("location") or "").strip():
        body["location"] = new_location
    new_notes = (new.get("notes") or "").strip()
    if new_notes != (old.get("notes") or "").strip():
        body["description"] = new_notes
    if new.get("priority") != old.get("priority"):
        body["colorId"] = color_from_priority(new.get("priority", "minor"))

    old_all_day = _is_all_day(old)
    new_all_day = _is_all_day(new)
    if (
        new_all_day != old_all_day
        or new.get("start") != old.get("start")
        or new.get("end") != old.get("end")
    ):
        start, end = _time_fields({**new, "all_day": new_all_day}, tz)
        clear_key = "dateTime" if new_all_day else "date"
        body["start"] = {**start, clear_key: None}
        body["end"] = {**end, clear_key: None}
    return body


def month_range(year, month, margin_months=1):
    """回傳 (起始日, 結束日_不含)：目標月份前後各 margin_months 個月。"""
    index = year * 12 + (month - 1) - margin_months
    start = date(index // 12, index % 12 + 1, 1)
    end_index = year * 12 + (month - 1) + 1 + margin_months
    end = date(end_index // 12, end_index % 12 + 1, 1)
    return start, end


def to_rfc3339(d, tz=None):
    """日期 -> 本機午夜的 RFC3339 字串（供 timeMin / timeMax）"""
    return datetime.combine(d, time.min, tzinfo=_tz(tz)).isoformat()
