"""
ui/calendar_logic.py
日曆頁的純邏輯（不 import Qt）：日期解析、月/週格、行程排序、即將到來、時間軸分欄、標題格式。

事件 dict 欄位：id, title, all_day, start, end, priority, location, notes。
全天 start/end 為 YYYY-MM-DD（end 含當天）；定時為 YYYY-MM-DDTHH:MM:SS（naive 本機時間）。
"""

import calendar
from datetime import date, datetime, time, timedelta

from ui import theme

DAY_MINUTES = 24 * 60
MIN_DISPLAY_MINUTES = 30      # 時間軸上過短（或零長度）行程的最小分欄長度
WEEKDAY_CHARS = "一二三四五六日"  # 對應 date.weekday() 0=Mon..6=Sun
SUNDAY_FIRST = 6              # first_weekday：Python 的 0=Mon..6=Sun

VIEW_MONTH = "month"
VIEW_WEEK = "week"
VIEW_DAY = "day"

_PRIORITY_RANK = {"major": 0, "medium": 1, "minor": 2}
_DEFAULT_PRIORITY = "minor"


# ---------------------------------------------------------------- 解析

def _parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def parse_event_dates(evt):
    """回傳 (起始日, 結束日含當天)；start 無法解析時回傳 None。

    - end 缺漏、無法解析或早於 start → 視為與 start 同日。
    - 定時行程若 end 剛好是隔天 00:00:00（或只有日期、視同 00:00，且跨日），顯示上只算到前一天。
    """
    start = _parse_date(evt.get("start"))
    if start is None:
        return None
    end_raw = evt.get("end") or evt.get("start")
    end = _parse_date(end_raw)
    if end is None or end < start:
        end = start
    elif not evt.get("all_day") and end > start and str(end_raw)[11:19] in ("", "00:00:00"):
        # 定時行程 end 為隔天 00:00（或只有日期、視同 00:00）→ 顯示上只到前一天
        end = end - timedelta(days=1)
    return start, end


def parse_event_times(evt):
    """定時行程 -> (開始 datetime, 結束 datetime)；全天或無法解析時回傳 None。
    結束早於開始時等同開始；結束只有日期時視為該日 00:00（與 parse_event_dates 的退一天規則一致）。"""
    if evt.get("all_day"):
        return None
    try:
        start = datetime.fromisoformat(str(evt.get("start"))[:19])
    except (TypeError, ValueError):
        return None
    try:
        end = datetime.fromisoformat(str(evt.get("end") or evt.get("start"))[:19])
    except (TypeError, ValueError):
        end = start
    if end < start:
        end = start
    return start, end


def _dates_of(evt):
    """優先使用 CalendarView 預先算好的 _d_start/_d_end，否則即時解析。"""
    cached_start, cached_end = evt.get("_d_start"), evt.get("_d_end")
    if cached_start is not None and cached_end is not None:
        return cached_start, cached_end
    return parse_event_dates(evt)


# ---------------------------------------------------------------- 日期格

def month_grid_dates(year, month, first_weekday=SUNDAY_FIRST):
    """固定 42 格（6 週）的日期；first_weekday 為一週起始日（0=Mon..6=Sun）。"""
    first = date(year, month, 1)
    offset = (first.weekday() - first_weekday) % 7
    start = first - timedelta(days=offset)
    return [start + timedelta(days=i) for i in range(42)]


def week_dates(day, first_weekday=SUNDAY_FIRST):
    """包含 day 的那一週 7 天。"""
    offset = (day.weekday() - first_weekday) % 7
    start = day - timedelta(days=offset)
    return [start + timedelta(days=i) for i in range(7)]


def view_dates(mode, selected, first_weekday=SUNDAY_FIRST):
    """目前視圖顯示的日期清單：月=42 格、週=7 天、日=1 天。"""
    if mode == VIEW_MONTH:
        return month_grid_dates(selected.year, selected.month, first_weekday)
    if mode == VIEW_WEEK:
        return week_dates(selected, first_weekday)
    return [selected]


def fetch_months_for_range(start, end):
    """[start, end]（含頭尾）涵蓋的 (year, month) 清單，由早到晚。"""
    if end < start:
        start, end = end, start
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return months


def add_months(day, delta):
    """加減月份；日數超出該月時取該月最後一天（1/31 + 1 月 = 2/28 或 2/29）。"""
    index = day.year * 12 + (day.month - 1) + delta
    year, month = divmod(index, 12)
    month += 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def shift_anchor(day, mode, step):
    """‹ › 依視圖移動：月 ±1 月、週 ±7 天、日 ±1 天。"""
    if mode == VIEW_MONTH:
        return add_months(day, step)
    if mode == VIEW_WEEK:
        return day + timedelta(days=7 * step)
    return day + timedelta(days=step)


# ---------------------------------------------------------------- 行程查詢

def _sort_key(evt):
    start = str(evt.get("start", ""))
    rank = _PRIORITY_RANK.get(evt.get("priority"), _PRIORITY_RANK[_DEFAULT_PRIORITY])
    return (0 if evt.get("all_day") else 1, start[11:19], rank, str(evt.get("title", "")))


def events_on(events, day):
    """day 當天的行程：全天優先，其次依開始時間、等級（大→小）、標題。"""
    found = []
    for evt in events:
        span = _dates_of(evt)
        if span is not None and span[0] <= day <= span[1]:
            found.append(evt)
    found.sort(key=_sort_key)
    return found


def days_until(today, start_date):
    """距離開始還有幾天；已經開始（進行中）為 0。"""
    return max(0, (start_date - today).days)


def days_until_label(n):
    if n <= 0:
        return "今天"
    if n == 1:
        return "明天"
    return f"還有 {n} 天"


def upcoming(events, today, now=None):
    """即將到來的行程 [(evt, n)]，依 n 再依時間排序。

    - 只列「明天以後開始」（n >= 1，依等級門檻：大 ≤30、中 ≤7、小 ≤3 天）
      與「今天以前開始、仍在進行中」（n = 0）的行程；今天才開始的行程由日清單呈現，不在此重複。
    - 已結束的行程排除：結束日早於今天，或定時行程結束時間 <= now（now 預設 datetime.now()）。
    """
    now = now or datetime.now()
    items = []
    for evt in events:
        span = _dates_of(evt)
        if span is None or span[1] < today:
            continue
        times = parse_event_times(evt)
        if times is not None and times[1] <= now:
            continue
        start = span[0]
        if start == today:
            continue
        n = days_until(today, start)
        if n > 0:
            priority = evt.get("priority")
            if priority not in theme.PRIORITY_WINDOW_DAYS:
                priority = _DEFAULT_PRIORITY
            if n > theme.PRIORITY_WINDOW_DAYS[priority]:
                continue
        items.append((evt, n))
    items.sort(key=lambda it: (it[1],) + _sort_key(it[0]))
    return items


def upcoming_subtitle(evt, n):
    """側欄副標：進行中 -> 「M/D–M/D · 進行中」（單日則「進行中」）；其餘「M/D 週X · 明天／還有 N 天」。"""
    span = _dates_of(evt)
    if span is None:
        return days_until_label(n)
    start, end = span
    if n == 0:
        if start == end:
            return "進行中"
        return f"{short_date(start)}–{short_date(end)} · 進行中"
    return f"{short_date(start)} {weekday_label(start)} · {days_until_label(n)}"


def priority_window_hint():
    """空狀態說明：由門檻 token 組字串，例如「大型行程 30 天內、中型 7 天內、小型 3 天內會出現在這裡」。"""
    parts = []
    for i, key in enumerate(("major", "medium", "minor")):
        suffix = "行程" if i == 0 else ""
        parts.append(f"{theme.PRIORITY_LABEL[key]}型{suffix} {theme.PRIORITY_WINDOW_DAYS[key]} 天內")
    return "、".join(parts) + "會出現在這裡"


def title_width_samples(mode):
    """工具列標題在該視圖模式下可能最寬的字串（用 0 代表數字），供預留寬度。"""
    if mode == VIEW_DAY:
        return ["0000 年 00 月 00 日 週三", "0000 年 00 月 00 日 週六"]
    if mode == VIEW_WEEK:
        return ["0000 年 00–00 月", "0000 年 00 月 – 0000 年 00 月"]
    return ["0000 年 00 月"]


# ---------------------------------------------------------------- 時間軸分欄

def timed_layout(events, day):
    """day 當天的定時行程分欄：[(evt, start_minute, end_minute, column, column_count)]。

    - 跨日行程裁切到 0~1440；全天行程不在此列。
    - 彼此（直接或間接）重疊的行程為一組，組內貪婪分欄，同組共用 column_count。
    """
    day_start = datetime.combine(day, time.min)
    day_end = day_start + timedelta(days=1)
    items = []
    for evt in events:
        times = parse_event_times(evt)
        if times is None:
            continue
        start, end = times
        if end <= start:
            if not (day_start <= start < day_end):
                continue
        elif start >= day_end or end <= day_start:
            continue
        s_min = 0 if start < day_start else int((start - day_start).total_seconds() // 60)
        e_min = DAY_MINUTES if end >= day_end else int((end - day_start).total_seconds() // 60)
        if e_min - s_min < MIN_DISPLAY_MINUTES:
            e_min = min(DAY_MINUTES, s_min + MIN_DISPLAY_MINUTES)
        items.append((evt, s_min, e_min))
    items.sort(key=lambda it: (it[1], -it[2]))

    result = []
    cluster = []          # [(evt, s, e, col)]
    col_ends = []
    cluster_end = 0

    def flush():
        count = len(col_ends)
        for evt, s, e, col in cluster:
            result.append((evt, s, e, col, count))

    for evt, s, e in items:
        if cluster and s >= cluster_end:
            flush()
            cluster, col_ends, cluster_end = [], [], 0
        for col, end in enumerate(col_ends):
            if end <= s:
                col_ends[col] = e
                break
        else:
            col = len(col_ends)
            col_ends.append(e)
        cluster.append((evt, s, e, col))
        cluster_end = max(cluster_end, e)
    if cluster:
        flush()
    return result


# ---------------------------------------------------------------- 文字格式

def weekday_label(day):
    return "週" + WEEKDAY_CHARS[day.weekday()]


def short_date(day):
    return f"{day.month}/{day.day}"


def minute_label(minute):
    """分鐘數 -> HH:MM（1440 顯示為 24:00）。"""
    return f"{minute // 60:02d}:{minute % 60:02d}"


def event_time_text(evt):
    """全天 -> 「全天」；定時 -> HH:MM - HH:MM（取字串，不做時區轉換）。"""
    if evt.get("all_day"):
        return "全天"
    start = str(evt.get("start", ""))
    end = str(evt.get("end", ""))
    start_t = start[11:16] if len(start) >= 16 else ""
    end_t = end[11:16] if len(end) >= 16 else ""
    if start_t and end_t:
        return f"{start_t} - {end_t}"
    return start_t or end_t


def format_view_title(mode, selected, dates=None):
    """工具列標題。月：YYYY 年 M 月；週：跨月 YYYY 年 M–M 月、跨年完整寫出；日：含日期與星期。"""
    if mode == VIEW_DAY:
        return f"{selected.year} 年 {selected.month} 月 {selected.day} 日 {weekday_label(selected)}"
    if mode == VIEW_WEEK:
        days = dates or week_dates(selected)
        first, last = days[0], days[-1]
        if (first.year, first.month) == (last.year, last.month):
            return f"{first.year} 年 {first.month} 月"
        if first.year == last.year:
            return f"{first.year} 年 {first.month}–{last.month} 月"
        return f"{first.year} 年 {first.month} 月 – {last.year} 年 {last.month} 月"
    return f"{selected.year} 年 {selected.month} 月"


def selected_title(selected, today):
    """側欄「選取日」標題：今天 -> 「今天 M/D」；其他 -> 「M/D 週X」。"""
    if selected == today:
        return f"今天 {short_date(selected)}"
    return f"{short_date(selected)} {weekday_label(selected)}"


def event_tooltip(evt):
    """hover 提示：標題、時間；有地點時再加一行。"""
    lines = [str(evt.get("title") or "（無標題）"), event_time_text(evt)]
    if evt.get("location"):
        lines.append(str(evt["location"]))
    return "\n".join(line for line in lines if line)
