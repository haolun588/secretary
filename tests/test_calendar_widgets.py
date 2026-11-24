"""MonthGrid / TimeGrid / SidePanel：以 resize() 後計算座標做命中測試，不依賴事件迴圈（不呼叫 processEvents）。"""

import os
from datetime import date, datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtCore import QPoint, Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

from ui import theme  # noqa: E402

TODAY = date(2026, 3, 10)


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    try:
        return QApplication.instance() or QApplication([])
    except Exception as e:
        pytest.skip(f"無法建立 QApplication: {e}")


def _ev(title, start="2026-03-10", end=None, all_day=True, priority="medium", eid=None):
    return {"id": eid or title, "title": title, "all_day": all_day, "start": start,
            "end": end or start, "priority": priority, "location": "", "notes": ""}


def _timed(title, sh, eh, day="2026-03-10", priority="medium"):
    return _ev(title, f"{day}T{sh}:00", f"{day}T{eh}:00", all_day=False, priority=priority)


# ---------------------------------------------------------------- MonthGrid

@pytest.fixture
def grid(qapp):
    from ui.month_grid import MonthGrid
    g = MonthGrid()
    g._today = lambda: TODAY
    g.resize(700, 600)
    g.set_month(2026, 3)
    return g


def _cell_center(g, day):
    i = g.dates().index(day)
    return g.cell_rect(i).center()


def test_month_grid_has_42_cells_covering_widget(grid):
    from ui.month_grid import HEADER_H
    assert len(grid.dates()) == 42
    assert grid.dates()[0] == date(2026, 3, 1)
    first, last = grid.cell_rect(0), grid.cell_rect(41)
    assert (first.left(), first.top()) == (0, HEADER_H)
    assert last.right() + 1 == grid.width() and last.bottom() + 1 == grid.height()


def test_date_at_maps_cell_centers_and_rejects_header(grid):
    for day in (date(2026, 3, 1), date(2026, 3, 10), date(2026, 3, 31), date(2026, 4, 11)):
        assert grid.date_at(_cell_center(grid, day)) == day
    assert grid.date_at(QPoint(10, 5)) is None          # 週名列
    assert grid.date_at(QPoint(-5, 100)) is None
    assert grid.date_at(QPoint(10, grid.height() + 5)) is None


def test_event_at_returns_chip_event_and_none_on_blank(grid):
    e = _ev("開會")
    grid.set_events([e])
    chips, more, hidden = grid.chip_layout(grid.dates().index(TODAY))
    assert len(chips) == 1 and more is None and hidden == 0
    assert grid.event_at(chips[0][0].center()) is e
    # 格內日期數字列（chip 之上）不是行程
    cell = grid.cell_rect(grid.dates().index(TODAY))
    assert grid.event_at(QPoint(cell.left() + 2, cell.top() + 2)) is None
    assert grid.tooltip_at(chips[0][0].center()).startswith("開會")


def test_more_indicator_when_cell_overflows(grid):
    events = [_ev(f"e{i}") for i in range(10)]
    grid.set_events(events)
    index = grid.dates().index(TODAY)
    chips, more, hidden = grid.chip_layout(index)
    assert more is not None
    assert len(chips) + hidden == 10 and hidden >= 2
    assert grid.more_at(more.center()) == hidden
    assert grid.event_at(more.center()) is None
    assert "還有" in grid.tooltip_at(more.center())
    # 所有 chip 都在格內
    cell = grid.cell_rect(index)
    assert all(cell.contains(r) for r, _ in chips) and cell.contains(more)


def test_no_more_indicator_when_all_fit(grid):
    grid.set_events([_ev("a"), _ev("b")])
    chips, more, hidden = grid.chip_layout(grid.dates().index(TODAY))
    assert len(chips) == 2 and more is None and hidden == 0


def test_multi_day_event_gets_chip_each_day(grid):
    e = _ev("出差", start="2026-03-10", end="2026-03-12")
    grid.set_events([e])
    for day in (date(2026, 3, 10), date(2026, 3, 11), date(2026, 3, 12)):
        chips, _, _ = grid.chip_layout(grid.dates().index(day))
        assert [c[1] for c in chips] == [e]
    chips, _, _ = grid.chip_layout(grid.dates().index(date(2026, 3, 13)))
    assert chips == []


def test_event_spanning_into_previous_month_cells(grid):
    e = _ev("跨月", start="2026-02-27", end="2026-03-02")
    grid.set_events([e])
    for day in (date(2026, 3, 1), date(2026, 3, 2)):
        assert grid.chip_layout(grid.dates().index(day))[0][0][1] is e


def test_click_empty_selects_date_and_click_event_activates(grid):
    e = _ev("開會")
    grid.set_events([e])
    selected, activated, added = [], [], []
    grid.date_selected.connect(selected.append)
    grid.event_activated.connect(activated.append)
    grid.date_activated.connect(added.append)

    QTest.mouseClick(grid, Qt.MouseButton.LeftButton, pos=_cell_center(grid, date(2026, 3, 20)))
    assert selected == [date(2026, 3, 20)]

    chip_center = grid.chip_layout(grid.dates().index(TODAY))[0][0][0].center()
    QTest.mouseClick(grid, Qt.MouseButton.LeftButton, pos=chip_center)
    assert activated == [e]
    assert selected == [date(2026, 3, 20)]      # 點行程不改選取日
    assert added == []


def test_double_click_empty_activates_new_event_date(grid):
    added = []
    grid.date_activated.connect(added.append)
    QTest.mouseDClick(grid, Qt.MouseButton.LeftButton, pos=_cell_center(grid, date(2026, 3, 18)))
    assert added == [date(2026, 3, 18)]


def test_click_after_double_click_without_release_still_selects(grid):
    from PyQt6.QtCore import QEvent, QPointF
    from PyQt6.QtGui import QMouseEvent
    added, selected = [], []
    grid.date_activated.connect(added.append)
    grid.date_selected.connect(selected.append)
    pos = QPointF(_cell_center(grid, date(2026, 3, 18)))
    dbl = QMouseEvent(QEvent.Type.MouseButtonDblClick, pos, pos, Qt.MouseButton.LeftButton,
                      Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    grid.mouseDoubleClickEvent(dbl)           # 只有雙擊事件，release 遺失
    assert added == [date(2026, 3, 18)] and grid._suppress_release is True
    QTest.mouseClick(grid, Qt.MouseButton.LeftButton, pos=_cell_center(grid, date(2026, 3, 20)))
    assert selected == [date(2026, 3, 20)]    # press 重設狀態，單擊不被吃掉
    assert grid._last_clicked == date(2026, 3, 20)


def test_double_click_on_weekday_header_does_not_add(grid):
    QTest.mouseClick(grid, Qt.MouseButton.LeftButton, pos=_cell_center(grid, date(2026, 3, 18)))   # 留下舊日期
    added = []
    grid.date_activated.connect(added.append)
    QTest.mouseDClick(grid, Qt.MouseButton.LeftButton, pos=QPoint(40, 5))
    assert added == []


def test_double_click_on_event_does_not_add(grid):
    grid.set_events([_ev("開會")])
    added = []
    grid.date_activated.connect(added.append)
    chip_center = grid.chip_layout(grid.dates().index(TODAY))[0][0][0].center()
    QTest.mouseDClick(grid, Qt.MouseButton.LeftButton, pos=chip_center)
    assert added == []


def test_hover_sets_hand_cursor_and_clears(grid):
    grid.set_events([_ev("開會")])
    chip_center = grid.chip_layout(grid.dates().index(TODAY))[0][0][0].center()
    QTest.mouseMove(grid, chip_center)
    assert grid.cursor().shape() == Qt.CursorShape.PointingHandCursor
    QTest.mouseMove(grid, _cell_center(grid, date(2026, 3, 25)))
    assert grid.cursor().shape() == Qt.CursorShape.ArrowCursor


def test_month_grid_minimum_fits_main_area(grid):
    from ui.month_grid import MonthGrid
    main_min = theme.WINDOW_MIN_W - theme.NAV_WIDTH - theme.SIDE_PANEL_WIDTH
    assert MonthGrid().minimumSizeHint().width() <= main_min


def test_month_grid_grab_renders(grid):
    grid.set_events([_ev(f"e{i}", priority=p) for i, p in enumerate(("major", "medium", "minor") * 3)])
    grid.set_selected(TODAY)
    img = grid.grab().toImage()
    assert img.width() == 700 and img.height() == 600
    grid.resize(grid.minimumSizeHint())
    assert not grid.grab().isNull()


# ---------------------------------------------------------------- TimeGrid

def test_column_spans_cover_exactly_without_gaps():
    from ui.time_grid import column_spans
    spans = column_spans(703, theme.TIME_GUTTER, 7)
    assert spans[0][0] == theme.TIME_GUTTER and spans[-1][1] == 703
    assert all(spans[i][1] == spans[i + 1][0] for i in range(6))
    assert column_spans(500, theme.TIME_GUTTER, 1) == [(theme.TIME_GUTTER, 500)]


@pytest.fixture
def tgrid(qapp):
    from ui import calendar_logic as cl
    from ui.time_grid import TimeGrid
    t = TimeGrid()
    t._today = lambda: TODAY
    t._now = lambda: datetime(2026, 3, 10, 14, 30)
    t.resize(700, 600)
    t.set_days(cl.week_dates(TODAY))
    # 未顯示的 widget 不會經過版面計算，手動給兩個畫布與捲動區視口相同寬度
    t.hours.resize(683, t.hours.height())
    t.header.resize(683, t.header.height())
    return t


def test_time_grid_hour_canvas_height_and_minute_mapping(tgrid):
    assert tgrid.hours.height() == 24 * theme.HOUR_HEIGHT
    assert tgrid.hours.minute_at(QPoint(100, 0)) == 0
    assert tgrid.hours.minute_at(QPoint(100, 9 * theme.HOUR_HEIGHT)) == 9 * 60
    assert tgrid.hours.minute_at(QPoint(100, 10 ** 6)) == 24 * 60 - 1
    assert tgrid.hours.now_y() == (14 * 60 + 30) * theme.HOUR_HEIGHT // 60


def test_time_grid_blocks_position_and_columns(tgrid):
    from ui.time_grid import BLOCK_PAD, CHIP_GAP
    a, b, c = _timed("a", "09:00", "11:00"), _timed("b", "09:30", "10:30"), _timed("c", "13:00", "14:00")
    tgrid.set_events([a, b, c])
    blocks = {evt["title"]: rect for rect, evt, _day in tgrid.hours.blocks()}
    assert blocks["a"].top() == 9 * theme.HOUR_HEIGHT
    assert blocks["b"].top() == (9 * 60 + 30) * theme.HOUR_HEIGHT // 60
    assert blocks["a"].left() < blocks["b"].left()        # 重疊 -> 左右並排
    assert blocks["a"].right() < blocks["b"].left()       # 並排不互相覆蓋
    assert blocks["c"].width() > blocks["a"].width()      # 單一行程佔滿欄寬
    x0, x1 = tgrid.hours.spans()[tgrid.days().index(date(2026, 3, 10))]
    inner_w = x1 - x0 - 2 * BLOCK_PAD
    assert blocks["c"].left() == x0 + BLOCK_PAD and blocks["c"].width() == inner_w - CHIP_GAP
    assert tgrid.hours.event_at(blocks["b"].center()) is b
    assert tgrid.hours.event_at(QPoint(blocks["a"].center().x(), 3 * theme.HOUR_HEIGHT)) is None


def test_time_grid_three_overlapping_each_get_one_third(tgrid):
    from ui.time_grid import BLOCK_PAD, CHIP_GAP
    events = [_timed("a", "09:00", "11:00"), _timed("b", "09:30", "10:30"), _timed("c", "10:00", "12:00")]
    tgrid.set_events(events)
    rects = sorted((r for r, _e, _d in tgrid.hours.blocks()), key=lambda r: r.left())
    x0, x1 = tgrid.hours.spans()[tgrid.days().index(date(2026, 3, 10))]
    inner_w = x1 - x0 - 2 * BLOCK_PAD
    assert len(rects) == 3
    assert all(r.width() == inner_w // 3 - CHIP_GAP for r in rects)
    for left, right in zip(rects, rects[1:]):
        assert left.right() < right.left()                # 彼此不重疊
    assert rects[-1].right() <= x1 - BLOCK_PAD


def test_time_grid_day_at_and_click_signals(tgrid):
    e = _timed("a", "09:00", "10:00")
    tgrid.set_events([e])
    selected, activated, added = [], [], []
    tgrid.date_selected.connect(selected.append)
    tgrid.event_activated.connect(activated.append)
    tgrid.date_activated.connect(added.append)

    spans = tgrid.hours.spans()
    sunday_x = (spans[0][0] + spans[0][1]) // 2
    QTest.mouseClick(tgrid.hours, Qt.MouseButton.LeftButton, pos=QPoint(sunday_x, 2 * theme.HOUR_HEIGHT))
    assert selected == [date(2026, 3, 8)]
    QTest.mouseDClick(tgrid.hours, Qt.MouseButton.LeftButton, pos=QPoint(sunday_x, 2 * theme.HOUR_HEIGHT))
    assert added == [date(2026, 3, 8)]
    block = [r for r, ev, _ in tgrid.hours.blocks() if ev is e][0]
    QTest.mouseClick(tgrid.hours, Qt.MouseButton.LeftButton, pos=block.center())
    assert activated == [e]
    # 左側時間標區不屬於任何日期
    assert tgrid.hours.day_at(QPoint(5, 100)) is None


def test_time_grid_all_day_chips_in_header_and_hit_test(tgrid):
    e = _ev("出差", start="2026-03-09", end="2026-03-10")
    tgrid.set_events([e, _timed("a", "09:00", "10:00")])
    layout = tgrid.header.allday_layout()
    tue = tgrid.days().index(date(2026, 3, 10))
    chips, more, hidden = layout[tue]
    assert [c[1] for c in chips] == [e] and more is None
    assert tgrid.header.event_at(chips[0][0].center()) is e
    # 全天行程不會出現在小時格
    assert all(ev is not e for _, ev, _ in tgrid.hours.blocks())
    selected = []
    tgrid.date_selected.connect(selected.append)
    QTest.mouseClick(tgrid.header, Qt.MouseButton.LeftButton, pos=QPoint(tgrid.header.spans()[2][0] + 5, 5))
    assert selected == [date(2026, 3, 10)]


def test_time_grid_all_day_overflow_collapses(tgrid):
    tgrid.set_events([_ev(f"d{i}") for i in range(6)])
    tue = tgrid.days().index(date(2026, 3, 10))
    chips, more, hidden = tgrid.header.allday_layout()[tue]
    assert more is not None and len(chips) + hidden == 6
    assert tgrid.header.height() >= more.bottom()


def test_time_grid_single_day_and_grab(tgrid):
    tgrid.set_days([TODAY])
    tgrid.set_events([_timed("a", "09:00", "10:00")])
    assert len(tgrid.hours.spans()) == 1
    assert not tgrid.grab().isNull()


def test_time_grid_initial_scroll_to_eight(tgrid):
    # 範圍首次變動（內容高度確定）時捲到 08:00；直接觸發 slot，不依賴事件迴圈
    bar = tgrid.scroll.verticalScrollBar()
    bar.setRange(0, 24 * theme.HOUR_HEIGHT)
    tgrid._on_range_changed(0, bar.maximum())
    from ui.time_grid import INITIAL_SCROLL_MARGIN
    assert bar.value() == 8 * theme.HOUR_HEIGHT - INITIAL_SCROLL_MARGIN
    assert tgrid._initial_scroll_pending is False


def test_time_grid_clock_not_started_until_shown(tgrid):
    assert not tgrid._clock.isActive()
    assert tgrid._clock.interval() == 60000


# ---------------------------------------------------------------- SidePanel

def test_side_panel_upcoming_and_selected_sections(qapp):
    from ui import calendar_logic as cl
    from ui.side_panel import EMPTY_DAY, EMPTY_UPCOMING, SidePanel
    panel = SidePanel()
    assert panel.width() == theme.SIDE_PANEL_WIDTH

    panel.set_upcoming([])
    panel.set_selected_day(TODAY, [], TODAY)
    assert panel.upcoming_row_count() == 0 and panel.selected_row_count() == 0
    assert panel.selected_title.text() == "今天 3/10"
    texts = [lbl.text() for lbl in panel.findChildren(type(panel.selected_title))]
    assert EMPTY_UPCOMING in texts and EMPTY_DAY in texts

    a = _ev("大事", start="2026-03-15", priority="major")
    b = _timed("開會", "09:00", "10:00")
    c = _ev("明天", start="2026-03-11", priority="minor")
    panel.set_upcoming(cl.upcoming([a, b, c], TODAY, datetime(2026, 3, 10, 8)))   # b 今天開始，不列入
    panel.set_selected_day(date(2026, 3, 11), cl.events_on([b], TODAY), TODAY)
    assert panel.upcoming_row_count() == 2
    assert panel.selected_row_count() == 1
    assert panel.selected_title.text() == "3/11 週三"


def test_side_panel_row_click_emits_event(qapp):
    from ui.side_panel import SidePanel, _EventRow
    panel = SidePanel()
    e = _ev("大事", start="2026-03-15", priority="major")
    panel.set_upcoming([(e, 5)])
    got = []
    panel.event_activated.connect(got.append)
    row = [panel.upcoming_box.itemAt(i).widget() for i in range(panel.upcoming_box.count())
           if isinstance(panel.upcoming_box.itemAt(i).widget(), _EventRow)][0]
    row.resize(200, 40)
    QTest.mouseClick(row, Qt.MouseButton.LeftButton, pos=QPoint(20, 20))
    assert got == [e]
    assert "還有 5 天" in row.sub_label.text() and "3/15" in row.sub_label.text()


def test_side_panel_ongoing_subtitle(qapp):
    from ui import calendar_logic as cl
    from ui.side_panel import SidePanel
    panel = SidePanel()
    e = _ev("長期", start="2026-03-08", end="2026-03-12", priority="minor")
    panel.set_upcoming(cl.upcoming([e], TODAY, datetime(2026, 3, 10, 8)))
    row = panel.upcoming_box.itemAt(0).widget()
    assert row.sub_label.text() == "3/8–3/12 · 進行中"


def test_side_panel_empty_hint_from_tokens(qapp):
    from ui.side_panel import EMPTY_UPCOMING_HINT
    for key in ("major", "medium", "minor"):
        assert str(theme.PRIORITY_WINDOW_DAYS[key]) in EMPTY_UPCOMING_HINT
        assert theme.PRIORITY_LABEL[key] in EMPTY_UPCOMING_HINT


@pytest.mark.parametrize("height", [680, 560])
def test_side_panel_heights_snap_to_whole_rows(qapp, height):
    from ui import calendar_logic as cl
    from ui.side_panel import SidePanel, row_height
    panel = SidePanel()
    panel.resize(theme.SIDE_PANEL_WIDTH, height)
    many = [_ev(f"e{i}", start=f"2026-03-{11 + i % 9:02d}", priority="major") for i in range(20)]
    panel.set_upcoming(cl.upcoming(many, TODAY, datetime(2026, 3, 10, 8)))
    panel.set_selected_day(TODAY, [_ev(f"d{i}", start="2026-03-10") for i in range(20)], TODAY)
    unit = row_height()
    up_h, sel_h = panel.upcoming_scroll.height(), panel.selected_scroll.height()
    assert up_h % unit == 0 and sel_h % unit == 0           # 最後一列不被切半
    assert up_h >= unit and sel_h >= unit
    avail = panel._available_list_height()
    assert up_h + sel_h <= avail
    assert up_h <= avail // 2                               # 即將到來不超過可用一半
    panel.layout().activate()
    assert panel._legend.geometry().bottom() <= panel.height()


def test_side_panel_short_upcoming_leaves_rest_to_selected(qapp):
    from ui.side_panel import SidePanel, row_height
    panel = SidePanel()
    panel.resize(theme.SIDE_PANEL_WIDTH, 680)
    panel.set_upcoming([(_ev("x", start="2026-03-12"), 2)])
    panel.set_selected_day(TODAY, [_ev(f"d{i}", start="2026-03-10") for i in range(30)], TODAY)
    assert panel.upcoming_scroll.height() == row_height()
    assert panel.selected_scroll.height() > panel._available_list_height() // 2


def test_fit_text_keeps_leading_chars_when_too_narrow(qapp):
    from PyQt6.QtGui import QFontMetrics
    from ui.styles import fit_text, make_font
    fm = QFontMetrics(make_font(theme.FONT_XS, theme.WEIGHT_SEMIBOLD))
    title = "設計討論"
    assert fit_text(fm, title, 8).startswith("設")          # 窄到只剩省略號 -> 回傳原文交由裁切
    assert "…" not in fit_text(fm, title, 8)
    assert fit_text(fm, title, 10 ** 4) == title            # 放得下維持原文
    mid = fit_text(fm, title, fm.horizontalAdvance("設討") + 2)
    assert mid.startswith("設") and mid.endswith("…")   # 一般情況仍用省略號
    assert fit_text(fm, "", 5) == ""
