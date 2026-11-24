"""
ui/time_grid.py
週 / 日共用的時間軸視圖：頂部日期列 + 全天列，下方可捲動的 24 小時格。

與 MonthGrid 相同，採 QPainter 自繪：定時行程區塊要依 calendar_logic.timed_layout 分欄、
疊現在時間線、做 hover / 點擊命中，QTableView 或 QCalendarWidget 都無法表達。
"""

from datetime import date, datetime

from PyQt6.QtCore import QEvent, QRect, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QPainter, QPainterPath
from PyQt6.QtWidgets import QFrame, QScrollArea, QSizePolicy, QToolTip, QVBoxLayout, QWidget

from ui import calendar_logic as cl
from ui import theme
from ui.components import level_bg, level_color, level_text
from ui.styles import fit_text, make_font, qcolor
from utils.logger import get_logger

logger = get_logger(__name__)

DATE_ROW_H = theme.SPACE_6 + theme.SPACE_4      # 日期列（週名 + 日期數字）
ALLDAY_PAD = theme.SPACE_1
CHIP_GAP = theme.SPACE_1 // 2
ALLDAY_MAX_ROWS = 3                              # 全天列最多顯示幾列，其餘收合成「+N」
DAY_CIRCLE = theme.SPACE_5
BLOCK_PAD = theme.SPACE_1 // 2
INITIAL_SCROLL_HOUR = 8
INITIAL_SCROLL_MARGIN = theme.SPACE_3            # 多留一點上緣，08:00 的時間標才不會被日期列切掉
MIN_DAY_COL_W = theme.SPACE_6 * 2               # 日欄最小寬度（週視圖 7 欄 + 時間標仍 < 608）


def column_spans(width, gutter, count):
    """把 gutter 右側的寬度平分成 count 欄，回傳 [(x0, x1)]（整數像素，相鄰欄無縫）。"""
    count = max(1, count)
    usable = max(0, width - gutter)
    return [(gutter + i * usable // count, gutter + (i + 1) * usable // count) for i in range(count)]


def _hline(p, x0, x1, y, color):
    """1px 水平線（fillRect，避免反鋸齒把線畫成兩列半透明像素）。x1 為不含的右端。"""
    p.fillRect(QRect(x0, y, max(0, x1 - x0), 1), qcolor(color))


def _vline(p, x, y0, y1, color):
    """1px 垂直線（同上）。y1 為不含的下端。"""
    p.fillRect(QRect(x, y0, 1, max(0, y1 - y0)), qcolor(color))


def _column_at(spans, x):
    for i, (x0, x1) in enumerate(spans):
        if x0 <= x < x1:
            return i
    return None


class _GridBase(QWidget):
    """日期列與小時格共用：持有 days / events / selected 與欄幾何。"""

    def __init__(self, owner, parent=None):
        super().__init__(parent)
        self._owner = owner
        self.setMouseTracking(True)

    def spans(self):
        return column_spans(self.width(), theme.TIME_GUTTER, len(self._owner._days))

    def day_at(self, pos):
        idx = _column_at(self.spans(), pos.x())
        return None if idx is None else self._owner._days[idx]


class _HeaderCanvas(_GridBase):
    """日期列 + 全天行程列。"""

    def __init__(self, owner, parent=None):
        super().__init__(owner, parent)
        self._hover = None

    # 幾何
    def allday_layout(self):
        """{index: ([(QRect, evt)], more_rect|None, hidden)}；rect 為本 widget 座標。"""
        result = {}
        for i, (x0, x1) in enumerate(self.spans()):
            events = self._owner._allday_by_day.get(self._owner._days[i], [])
            shown, hidden = events, 0
            if len(events) > ALLDAY_MAX_ROWS:
                shown = events[:ALLDAY_MAX_ROWS - 1]
                hidden = len(events) - len(shown)
            y = DATE_ROW_H + ALLDAY_PAD
            chips = []
            for evt in shown:
                chips.append((QRect(x0 + ALLDAY_PAD, y, x1 - x0 - 2 * ALLDAY_PAD, theme.MONTH_CHIP_H), evt))
                y += theme.MONTH_CHIP_H + CHIP_GAP
            more = QRect(x0 + ALLDAY_PAD, y, x1 - x0 - 2 * ALLDAY_PAD, theme.MONTH_CHIP_H) if hidden else None
            result[i] = (chips, more, hidden)
        return result

    def event_at(self, pos):
        for chips, _more, _hidden in self.allday_layout().values():
            for rect, evt in chips:
                if rect.contains(pos):
                    return evt
        return None

    def tooltip_at(self, pos):
        evt = self.event_at(pos)
        if evt is not None:
            return cl.event_tooltip(evt)
        for _chips, more, hidden in self.allday_layout().values():
            if more is not None and more.contains(pos):
                return f"還有 {hidden} 筆全天行程"
        return None

    def date_at(self, pos):
        """日期列範圍內的日期；全天區空白處也算該欄日期。"""
        return self.day_at(pos)

    # 繪製
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        owner = self._owner
        p.fillRect(self.rect(), qcolor(theme.BG))
        today = owner._today()
        spans = self.spans()
        for i, (x0, x1) in enumerate(spans):
            day = owner._days[i]
            col = QRect(x0, 0, x1 - x0, self.height())
            if day == today:
                p.fillRect(col, qcolor(theme.ACCENT_SOFT))
            _vline(p, x0, 0, self.height(), theme.BORDER)
            # 週名
            p.setFont(make_font(theme.FONT_XS, theme.WEIGHT_REGULAR))
            p.setPen(qcolor(theme.TEXT_MUTED))
            p.drawText(QRect(x0, theme.SPACE_2, x1 - x0, theme.SPACE_4), Qt.AlignmentFlag.AlignCenter,
                       cl.weekday_label(day))
            # 日期數字
            circle = QRect(x0 + (x1 - x0 - DAY_CIRCLE) // 2, theme.SPACE_2 + theme.SPACE_4, DAY_CIRCLE, DAY_CIRCLE)
            selected = day == owner._selected
            if day == today:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qcolor(theme.ACCENT))
                p.drawEllipse(QRectF(circle))
                p.setPen(qcolor(theme.TEXT_ON_ACCENT))
            else:
                p.setPen(qcolor(theme.ACCENT if selected else theme.TEXT_PRIMARY))
            p.setFont(make_font(theme.FONT_SM, theme.WEIGHT_SEMIBOLD if (selected or day == today)
                                else theme.WEIGHT_REGULAR))
            p.drawText(circle, Qt.AlignmentFlag.AlignCenter, str(day.day))
        # 全天標籤
        p.setFont(make_font(theme.FONT_XS, theme.WEIGHT_REGULAR))
        p.setPen(qcolor(theme.TEXT_MUTED))
        if self.height() > DATE_ROW_H:
            p.drawText(QRect(0, DATE_ROW_H + ALLDAY_PAD, theme.TIME_GUTTER - theme.SPACE_2, theme.MONTH_CHIP_H),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "全天")
        # 全天 chip
        for i, (chips, more, hidden) in self.allday_layout().items():
            for rect, evt in chips:
                _paint_chip(p, rect, evt, self._hover is evt)
            if more is not None:
                p.setFont(make_font(theme.FONT_XS, theme.WEIGHT_REGULAR))
                p.setPen(qcolor(theme.TEXT_SECONDARY))
                p.drawText(more.adjusted(theme.SPACE_1, 0, 0, 0),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"+{hidden}")
        _hline(p, 0, self.width(), self.height() - 1, theme.BORDER)
        p.end()

    # 事件
    def event(self, e):
        if e.type() == QEvent.Type.ToolTip:
            text = self.tooltip_at(e.pos())
            if text:
                QToolTip.showText(e.globalPos(), text, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(e)

    def mouseMoveEvent(self, e):
        evt = self.event_at(e.position().toPoint())
        if evt is not self._hover:
            self._hover = evt
            self.setCursor(Qt.CursorShape.PointingHandCursor if evt is not None else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        if self._hover is not None:
            self._hover = None
            self.unsetCursor()
            self.update()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        pos = e.position().toPoint()
        evt = self.event_at(pos)
        if evt is not None:
            self._owner.event_activated.emit(evt)
            return
        day = self.date_at(pos)
        if day is not None:
            self._owner.date_selected.emit(day)

    def mouseDoubleClickEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        pos = e.position().toPoint()
        if self.event_at(pos) is None:
            day = self.date_at(pos)
            if day is not None:
                self._owner.date_activated.emit(day)


class _HourCanvas(_GridBase):
    """24 小時格 + 定時行程區塊 + 現在時間線。高度固定 24 * HOUR_HEIGHT。"""

    def __init__(self, owner, parent=None):
        super().__init__(owner, parent)
        self.setFixedHeight(24 * theme.HOUR_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._hover = None
        self._blocks_cache = None

    def invalidate(self):
        self._blocks_cache = None
        self._hover = None
        self.update()

    # 幾何
    def blocks(self):
        """[(QRect, evt, day)]：每個定時行程區塊在本 widget 座標的矩形。"""
        if self._blocks_cache is not None and self._blocks_cache[0] == self.width():
            return self._blocks_cache[1]
        out = []
        for i, (x0, x1) in enumerate(self.spans()):
            day = self._owner._days[i]
            inner_w = x1 - x0 - 2 * BLOCK_PAD
            for evt, s_min, e_min, col, count in self._owner._layout_by_day.get(day, []):
                # 依 timed_layout 分欄並排：每欄 1/count 寬，單一行程佔滿欄寬
                bx = x0 + BLOCK_PAD + col * inner_w // count
                width = inner_w // count - CHIP_GAP
                top = s_min * theme.HOUR_HEIGHT // 60
                height = max(theme.MONTH_CHIP_H, (e_min - s_min) * theme.HOUR_HEIGHT // 60 - CHIP_GAP)
                out.append((QRect(bx, top, max(1, width), height), evt, day))
        self._blocks_cache = (self.width(), out)
        return out

    def event_at(self, pos):
        for rect, evt, _day in reversed(self.blocks()):
            if rect.contains(pos):
                return evt
        return None

    def minute_at(self, pos):
        return max(0, min(cl.DAY_MINUTES - 1, pos.y() * 60 // theme.HOUR_HEIGHT))

    def now_y(self):
        now = self._owner._now()
        return (now.hour * 60 + now.minute) * theme.HOUR_HEIGHT // 60

    # 繪製
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        owner = self._owner
        p.fillRect(self.rect(), qcolor(theme.BG))
        today = owner._today()
        spans = self.spans()
        for i, (x0, x1) in enumerate(spans):
            if owner._days[i] == today:
                p.fillRect(QRect(x0, 0, x1 - x0, self.height()), qcolor(theme.ACCENT_SOFT))
        # 小時橫線與時間標
        label_font = make_font(theme.FONT_XS, theme.WEIGHT_REGULAR)
        for h in range(24):
            y = h * theme.HOUR_HEIGHT
            if h > 0:
                _hline(p, theme.TIME_GUTTER, self.width(), y, theme.BORDER)
            p.setFont(label_font)
            p.setPen(qcolor(theme.TEXT_MUTED))
            top = y if h == 0 else y - theme.SPACE_2
            p.drawText(QRect(0, top, theme.TIME_GUTTER - theme.SPACE_2, theme.SPACE_4),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{h:02d}:00")
        # 欄分隔線
        for x0, _x1 in spans:
            _vline(p, x0, 0, self.height(), theme.BORDER)
        # 行程區塊
        for rect, evt, _day in self.blocks():
            self._paint_block(p, rect, evt, self._hover is evt)
        # 現在時間線
        for i, (x0, x1) in enumerate(spans):
            if owner._days[i] == today:
                y = self.now_y()
                _hline(p, x0, x1, y, theme.ACCENT)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qcolor(theme.ACCENT))
                r = theme.SPACE_1
                p.drawEllipse(QRectF(x0 - r, y - r, 2 * r, 2 * r))
        p.end()

    def _paint_block(self, p, rect, evt, hovered):
        p.save()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), theme.RADIUS_SM, theme.RADIUS_SM)
        p.setClipPath(path)
        p.fillRect(rect, qcolor(theme.SURFACE_2))      # 不透明底，避免重疊行程與格線透出
        p.fillRect(rect, qcolor(level_bg(evt.get("priority"), hovered)))
        p.fillRect(QRect(rect.left(), rect.top(), theme.LEVEL_BAR, rect.height()),
                   qcolor(level_color(evt.get("priority"))))
        p.setClipping(False)
        text_rect = rect.adjusted(theme.LEVEL_BAR + theme.SPACE_1, theme.SPACE_1 // 2, -theme.SPACE_1, 0)
        title_font = make_font(theme.FONT_XS, theme.WEIGHT_SEMIBOLD)
        fm = QFontMetrics(title_font)
        p.setFont(title_font)
        p.setPen(qcolor(level_text(evt.get("priority"))))
        title = str(evt.get("title") or "（無標題）")
        line_h = fm.height()
        p.setClipRect(text_rect)      # 窄欄時標題只剩前幾個字也直接裁切顯示
        p.drawText(QRect(text_rect.left(), text_rect.top(), text_rect.width(), line_h),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   fit_text(fm, title, text_rect.width()))
        time_font = make_font(theme.FONT_XS, theme.WEIGHT_REGULAR)
        tfm = QFontMetrics(time_font)
        time_text = cl.event_time_text(evt)
        # 高度夠且寬度放得下完整時間才畫時間；窄欄只畫標題（完整資訊在 tooltip）
        if rect.height() >= 2 * line_h + theme.SPACE_1 and tfm.horizontalAdvance(time_text) <= text_rect.width():
            p.setFont(time_font)
            p.setPen(qcolor(theme.TEXT_SECONDARY))
            p.drawText(QRect(text_rect.left(), text_rect.top() + line_h, text_rect.width(), line_h),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       tfm.elidedText(cl.event_time_text(evt), Qt.TextElideMode.ElideRight,
                                      max(0, text_rect.width())))
        p.restore()

    # 事件
    def event(self, e):
        if e.type() == QEvent.Type.ToolTip:
            evt = self.event_at(e.pos())
            if evt is not None:
                QToolTip.showText(e.globalPos(), cl.event_tooltip(evt), self)
            else:
                QToolTip.hideText()
            return True
        return super().event(e)

    def mouseMoveEvent(self, e):
        evt = self.event_at(e.position().toPoint())
        if evt is not self._hover:
            self._hover = evt
            self.setCursor(Qt.CursorShape.PointingHandCursor if evt is not None else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        if self._hover is not None:
            self._hover = None
            self.unsetCursor()
            self.update()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        pos = e.position().toPoint()
        evt = self.event_at(pos)
        if evt is not None:
            self._owner.event_activated.emit(evt)
            return
        day = self.day_at(pos)
        if day is not None:
            self._owner.date_selected.emit(day)

    def mouseDoubleClickEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        pos = e.position().toPoint()
        if self.event_at(pos) is None:
            day = self.day_at(pos)
            if day is not None:
                self._owner.date_activated.emit(day)


def _paint_chip(p, rect, evt, hovered):
    """全天 chip（與月格相同樣式）。"""
    p.save()
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect), theme.RADIUS_SM, theme.RADIUS_SM)
    p.setClipPath(path)
    p.fillRect(rect, qcolor(theme.SURFACE_2))      # 不透明底，避免半透明疊色透出格線
    p.fillRect(rect, qcolor(level_bg(evt.get("priority"), hovered)))
    p.fillRect(QRect(rect.left(), rect.top(), theme.LEVEL_BAR, rect.height()),
               qcolor(level_color(evt.get("priority"))))
    p.setClipping(False)
    font = make_font(theme.FONT_XS, theme.WEIGHT_REGULAR)
    p.setFont(font)
    p.setPen(qcolor(level_text(evt.get("priority"))))
    text_rect = rect.adjusted(theme.LEVEL_BAR + theme.SPACE_1, 0, -theme.SPACE_1, 0)
    p.setClipRect(text_rect)
    p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
               fit_text(QFontMetrics(font), str(evt.get("title") or "（無標題）"), text_rect.width()))
    p.restore()


class TimeGrid(QWidget):
    date_selected = pyqtSignal(object)      # datetime.date
    date_activated = pyqtSignal(object)     # 雙擊空白 → 新增
    event_activated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._today = date.today            # 可注入，方便測試
        self._now = datetime.now            # 可注入，方便測試
        self._days = [self._today()]
        self._selected = self._today()
        self._events = []
        self._allday_by_day = {}
        self._layout_by_day = {}
        self._initial_scroll_pending = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = _HeaderCanvas(self)
        self._header_holder = QFrame(self)
        self._header_holder.setObjectName("TimeGridHeader")
        holder_layout = QVBoxLayout(self._header_holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.addWidget(self.header)
        layout.addWidget(self._header_holder)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.hours = _HourCanvas(self)
        self.scroll.setWidget(self.hours)
        layout.addWidget(self.scroll, 1)
        self.scroll.verticalScrollBar().rangeChanged.connect(self._on_range_changed)

        self._clock = QTimer(self)          # 每分鐘更新現在時間線；顯示時才啟動
        self._clock.setInterval(60000)
        self._clock.timeout.connect(self.refresh_now)

        self._rebuild()

    # ------------------------------------------------------------ 資料

    def set_days(self, days):
        self._days = list(days) or [self._today()]
        self._rebuild()

    def set_events(self, events):
        self._events = list(events)
        self._rebuild()

    def set_selected(self, day):
        self._selected = day
        self.header.update()

    def days(self):
        return list(self._days)

    def refresh_now(self):
        self.hours.update()

    def _rebuild(self):
        self._allday_by_day = {}
        self._layout_by_day = {}
        for day in self._days:
            on_day = cl.events_on(self._events, day)
            self._allday_by_day[day] = [e for e in on_day if e.get("all_day")]
            self._layout_by_day[day] = cl.timed_layout(self._events, day)
        rows = 0
        for events in self._allday_by_day.values():
            rows = max(rows, min(len(events), ALLDAY_MAX_ROWS))
        header_h = DATE_ROW_H
        if rows:
            header_h += ALLDAY_PAD * 2 + rows * theme.MONTH_CHIP_H + (rows - 1) * CHIP_GAP
        else:
            header_h += ALLDAY_PAD * 2 + theme.MONTH_CHIP_H     # 沒有全天行程仍保留一列，標示「全天」
        self.header.setFixedHeight(header_h)
        self.hours.invalidate()
        self.header.update()

    # ------------------------------------------------------------ 捲動

    def scroll_to_hour(self, hour):
        bar = self.scroll.verticalScrollBar()
        bar.setValue(max(0, min(bar.maximum(), hour * theme.HOUR_HEIGHT - INITIAL_SCROLL_MARGIN)))

    def _on_range_changed(self, _minimum, maximum):
        if self._initial_scroll_pending and maximum > 0:
            self._initial_scroll_pending = False
            self.scroll_to_hour(INITIAL_SCROLL_HOUR)

    def _sync_header_margin(self):
        """讓日期列右側讓出捲軸寬度，欄位才能和下方小時格對齊。"""
        bar_w = self.scroll.verticalScrollBar().sizeHint().width()   # 捲軸固定顯示，寬度恆定
        self._header_holder.layout().setContentsMargins(0, 0, bar_w, 0)

    # ------------------------------------------------------------ Qt 事件

    def minimumSizeHint(self):
        return QSize(theme.TIME_GUTTER + 7 * MIN_DAY_COL_W, DATE_ROW_H + 6 * theme.HOUR_HEIGHT)

    def showEvent(self, e):
        super().showEvent(e)
        self._clock.start()
        self._sync_header_margin()

    def hideEvent(self, e):
        self._clock.stop()
        super().hideEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._sync_header_margin()
