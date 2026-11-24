"""
ui/month_grid.py
月視圖：7 欄 x 6 列自繪格子（QPainter）。

選擇 QPainter 自繪而非 QCalendarWidget / QTableView + delegate 的理由：
格內要放行程色條 chip、「+N」收合、今天淡底與日期圓、hover / 點擊命中區域，
這些都需要逐格精細控制；QCalendarWidget 無法在格內放行程，
QTableView 則需另建 model / delegate，且跨日與收合處理反而更繞。
"""

from datetime import date

from PyQt6.QtCore import QEvent, QPoint, QRect, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QPainter, QPainterPath
from PyQt6.QtWidgets import QSizePolicy, QToolTip, QWidget

from ui import calendar_logic as cl
from ui import theme
from ui.components import level_bg, level_color, level_text
from ui.styles import fit_text, make_font, qcolor
from utils.logger import get_logger

logger = get_logger(__name__)

WEEKDAY_HEADERS = ("日", "一", "二", "三", "四", "五", "六")
HEADER_H = theme.SPACE_5                      # 週名列高度
DAY_ROW_H = theme.SPACE_5 + theme.SPACE_1     # 格內日期數字列高度（chip 從這之下開始）
DAY_CIRCLE = theme.SPACE_5                    # 日期圓直徑
CELL_PAD = theme.SPACE_1
CHIP_GAP = theme.SPACE_1 // 2
MIN_CELL_W = theme.SPACE_6 * 2 + theme.SPACE_4  # 最小格寬 80 → 7 欄 560 < 608


class MonthGrid(QWidget):
    date_selected = pyqtSignal(object)      # datetime.date
    date_activated = pyqtSignal(object)     # 雙擊空白 → 新增
    event_activated = pyqtSignal(dict)      # 點行程 → 編輯

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._today = date.today        # 可注入，方便測試
        self._events = []
        self._by_day = {}
        self._selected = self._today()
        self._year, self._month = self._selected.year, self._selected.month
        self._dates = cl.month_grid_dates(self._year, self._month)
        self._hover = None               # (index, id(evt)) 或 ("more", index)
        self._last_clicked = None
        self._suppress_release = False

    # ------------------------------------------------------------ 資料

    def set_month(self, year, month):
        self._year, self._month = year, month
        self._dates = cl.month_grid_dates(year, month)
        self._rebuild()

    def set_events(self, events):
        self._events = list(events)
        self._rebuild()

    def set_selected(self, day):
        self._selected = day
        self.update()

    def dates(self):
        return list(self._dates)

    def _rebuild(self):
        self._by_day = {d: cl.events_on(self._events, d) for d in self._dates}
        self._hover = None
        self.update()

    # ------------------------------------------------------------ 幾何與命中

    def minimumSizeHint(self):
        return QSize(7 * MIN_CELL_W, HEADER_H + 6 * (DAY_ROW_H + theme.MONTH_CHIP_H))

    def sizeHint(self):
        return QSize(7 * MIN_CELL_W * 2, HEADER_H + 6 * (DAY_ROW_H + 3 * (theme.MONTH_CHIP_H + CHIP_GAP)))

    def cell_rect(self, index):
        w, h = self.width(), max(0, self.height() - HEADER_H)
        col, row = index % 7, index // 7
        x0, x1 = col * w // 7, (col + 1) * w // 7
        y0, y1 = HEADER_H + row * h // 6, HEADER_H + (row + 1) * h // 6
        return QRect(x0, y0, x1 - x0, y1 - y0)

    def index_at(self, pos):
        """座標 -> 格子索引（0~41）；週名列或範圍外回傳 None。"""
        if pos.y() < HEADER_H:
            return None
        for i in range(42):
            if self.cell_rect(i).contains(pos):
                return i
        return None

    def date_at(self, pos):
        index = self.index_at(pos)
        return None if index is None else self._dates[index]

    def chip_layout(self, index):
        """格子內的 chip 配置：([(QRect, evt)], +N 的 QRect 或 None, 被收合的筆數)。"""
        rect = self.cell_rect(index)
        events = self._by_day.get(self._dates[index], [])
        slot = theme.MONTH_CHIP_H + CHIP_GAP
        avail = rect.height() - DAY_ROW_H - CELL_PAD
        capacity = max(0, (avail + CHIP_GAP) // slot)
        if len(events) <= capacity:
            shown, hidden = events, 0
        else:
            shown = events[:max(0, capacity - 1)]
            hidden = len(events) - len(shown)
        x, w = rect.left() + CELL_PAD, rect.width() - 2 * CELL_PAD
        y = rect.top() + DAY_ROW_H
        chips = []
        for evt in shown:
            chips.append((QRect(x, y, w, theme.MONTH_CHIP_H), evt))
            y += slot
        more = QRect(x, y, w, theme.MONTH_CHIP_H) if hidden else None
        return chips, more, hidden

    def event_at(self, pos):
        """座標落在某個行程 chip 上 -> 該行程 dict；否則 None（「+N」不算）。"""
        index = self.index_at(pos)
        if index is None:
            return None
        for rect, evt in self.chip_layout(index)[0]:
            if rect.contains(pos):
                return evt
        return None

    def more_at(self, pos):
        """座標落在「+N」上 -> 被收合的筆數；否則 0。"""
        index = self.index_at(pos)
        if index is None:
            return 0
        _, more, hidden = self.chip_layout(index)
        return hidden if more is not None and more.contains(pos) else 0

    def tooltip_at(self, pos):
        evt = self.event_at(pos)
        if evt is not None:
            return cl.event_tooltip(evt)
        hidden = self.more_at(pos)
        if hidden:
            return f"還有 {hidden} 筆行程"
        return None

    # ------------------------------------------------------------ 事件

    def event(self, e):
        if e.type() == QEvent.Type.ToolTip:
            text = self.tooltip_at(e.pos())
            if text:
                QToolTip.showText(e.globalPos(), text, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(e)

    def _hover_key(self, pos):
        index = self.index_at(pos)
        if index is None:
            return None
        chips, more, _ = self.chip_layout(index)
        for rect, evt in chips:
            if rect.contains(pos):
                return (index, id(evt))
        if more is not None and more.contains(pos):
            return ("more", index)
        return None

    def mouseMoveEvent(self, e):
        key = self._hover_key(e.position().toPoint())
        if key != self._hover:
            self._hover = key
            self.setCursor(Qt.CursorShape.PointingHandCursor if key else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        if self._hover is not None:
            self._hover = None
            self.unsetCursor()
            self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        # 每次按下都重設雙擊遺留狀態，避免雙擊後沒收到 release 時，下一次單擊被吃掉或用到舊日期
        if e.button() == Qt.MouseButton.LeftButton:
            self._suppress_release = False
            self._last_clicked = None

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if self._suppress_release:
            self._suppress_release = False
            return
        self._click_at(e.position().toPoint())

    def _click_at(self, pos):
        evt = self.event_at(pos)
        if evt is not None:
            self.event_activated.emit(evt)
            return
        day = self.date_at(pos)
        if day is not None:
            self._last_clicked = day
            self.date_selected.emit(day)

    def mouseDoubleClickEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        self._suppress_release = True
        pos = e.position().toPoint()
        if self.index_at(pos) is None or self.event_at(pos) is not None:
            return      # 週名列或行程上的雙擊不新增
        # 第一下點擊可能讓月份切換（點到非本月日期），所以優先用第一下記錄的日期
        day = self._last_clicked or self.date_at(pos)
        if day is not None:
            self.date_activated.emit(day)

    # ------------------------------------------------------------ 繪製

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcolor(theme.BG))
        self._paint_header(p)
        today = self._today()
        for i, day in enumerate(self._dates):
            self._paint_cell(p, i, day, today)
        # 選取日外框畫在最上層，避免被相鄰格線蓋住
        if self._selected in self._dates:
            rect = self.cell_rect(self._dates.index(self._selected))
            accent = qcolor(theme.ACCENT)
            p.fillRect(QRect(rect.left(), rect.top(), rect.width(), 1), accent)
            p.fillRect(QRect(rect.left(), rect.bottom(), rect.width(), 1), accent)
            p.fillRect(QRect(rect.left(), rect.top(), 1, rect.height()), accent)
            p.fillRect(QRect(rect.right(), rect.top(), 1, rect.height()), accent)
        p.end()

    def _paint_header(self, p):
        p.setFont(make_font(theme.FONT_XS, theme.WEIGHT_REGULAR))
        p.setPen(qcolor(theme.TEXT_MUTED))
        for col, name in enumerate(WEEKDAY_HEADERS):
            rect = QRect(col * self.width() // 7, 0, self.width() // 7, HEADER_H)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)

    def _paint_cell(self, p, index, day, today):
        rect = self.cell_rect(index)
        in_month = day.month == self._month and day.year == self._year
        if not in_month:
            p.fillRect(rect, qcolor(theme.SURFACE_1))
        if day == today:
            p.fillRect(rect, qcolor(theme.ACCENT_SOFT))
        # 格線：右與下各 1px
        # 用 fillRect 畫 1px 線，避免反鋸齒把線畫成兩列半透明像素
        border = qcolor(theme.BORDER)
        p.fillRect(QRect(rect.right(), rect.top(), 1, rect.height()), border)
        p.fillRect(QRect(rect.left(), rect.bottom(), rect.width(), 1), border)

        # 日期數字
        circle = QRect(rect.left() + CELL_PAD, rect.top() + CELL_PAD, DAY_CIRCLE, DAY_CIRCLE)
        if day == today:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolor(theme.ACCENT))
            p.drawEllipse(QRectF(circle))
            p.setPen(qcolor(theme.TEXT_ON_ACCENT))
            p.setFont(make_font(theme.FONT_XS, theme.WEIGHT_SEMIBOLD))
        else:
            p.setPen(qcolor(theme.TEXT_PRIMARY if in_month else theme.TEXT_MUTED))
            p.setFont(make_font(theme.FONT_XS, theme.WEIGHT_REGULAR))
        p.drawText(circle, Qt.AlignmentFlag.AlignCenter, str(day.day))

        chips, more, hidden = self.chip_layout(index)
        for chip_rect, evt in chips:
            self._paint_chip(p, chip_rect, evt, in_month, self._hover == (index, id(evt)))
        if more is not None:
            hovered = self._hover == ("more", index)
            p.setFont(make_font(theme.FONT_XS, theme.WEIGHT_SEMIBOLD if hovered else theme.WEIGHT_REGULAR))
            p.setPen(qcolor(theme.TEXT_PRIMARY if hovered else theme.TEXT_SECONDARY))
            text_rect = more.adjusted(theme.SPACE_1, 0, 0, 0)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"+{hidden}")

    def _paint_chip(self, p, rect, evt, in_month, hovered):
        p.save()
        if not in_month:
            p.setOpacity(0.6)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), theme.RADIUS_SM, theme.RADIUS_SM)
        p.setClipPath(path)
        p.fillRect(rect, qcolor(theme.SURFACE_2))      # 不透明底，避免半透明疊色透出格線
        p.fillRect(rect, qcolor(level_bg(evt.get("priority"), hovered)))
        bar = QRect(rect.left(), rect.top(), theme.LEVEL_BAR, rect.height())
        p.fillRect(bar, qcolor(level_color(evt.get("priority"))))
        p.setClipping(False)
        font = make_font(theme.FONT_XS, theme.WEIGHT_REGULAR)
        p.setFont(font)
        p.setPen(qcolor(level_text(evt.get("priority"))))
        text_rect = rect.adjusted(theme.LEVEL_BAR + theme.SPACE_1, 0, -theme.SPACE_1, 0)
        title = str(evt.get("title") or "（無標題）")
        elided = fit_text(QFontMetrics(font), title, text_rect.width())
        p.setClipRect(text_rect)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)
        p.restore()
