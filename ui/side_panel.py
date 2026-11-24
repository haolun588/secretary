"""
ui/side_panel.py
日曆頁右側面板（寬 theme.SIDE_PANEL_WIDTH）：即將到來、選取日清單、等級圖例。
樣式來自 ui/styles.py 的 _PANEL 區段（QFrame#SidePanel、QFrame#PanelRow）。
"""

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QPainter
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from ui import calendar_logic as cl
from ui import theme
from ui.components import LevelDot, level_color
from ui.styles import make_font, qcolor
from utils.logger import get_logger

logger = get_logger(__name__)

EMPTY_UPCOMING = "近期沒有需要注意的行程"
EMPTY_UPCOMING_HINT = cl.priority_window_hint()
EMPTY_DAY = "這天沒有行程"
EMPTY_DAY_HINT = "雙擊日曆格子或按「新增」建立行程"


class _ElidedText(QWidget):
    """單行文字，過長時以 … 截斷；顏色與字級直接用 theme token 繪製。"""

    def __init__(self, text, size=theme.FONT_SM, weight=theme.WEIGHT_REGULAR,
                 color=theme.TEXT_PRIMARY, parent=None):
        super().__init__(parent)
        self._font = make_font(size, weight)
        self._color = color
        self._text = ""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(QFontMetrics(self._font).height())
        self.set_text(text)

    def text(self):
        return self._text

    def set_text(self, text):
        self._text = str(text)
        self.setToolTip(self._text)
        self.update()

    def minimumSizeHint(self):
        return QSize(0, self.height())

    def sizeHint(self):
        return QSize(QFontMetrics(self._font).horizontalAdvance(self._text), self.height())

    def paintEvent(self, e):
        p = QPainter(self)
        p.setFont(self._font)
        p.setPen(qcolor(self._color))
        elided = QFontMetrics(self._font).elidedText(self._text, Qt.TextElideMode.ElideRight, self.width())
        p.drawText(QRect(0, 0, self.width(), self.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)
        p.end()


class _LevelBar(QWidget):
    """行程列左側的等級色條。"""

    def __init__(self, priority, parent=None):
        super().__init__(parent)
        self._priority = priority
        self.setFixedWidth(theme.LEVEL_BAR)

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), qcolor(level_color(self._priority)))
        p.end()


def row_height():
    """側欄每列固定高度（上下內距 + 標題行 + 副標行），捲動區高度才能對齊整數列。"""
    title_h = QFontMetrics(make_font(theme.FONT_SM, theme.WEIGHT_SEMIBOLD)).height()
    sub_h = QFontMetrics(make_font(theme.FONT_XS, theme.WEIGHT_REGULAR)).height()
    return 2 * theme.SPACE_2 + title_h + sub_h


class _EventRow(QFrame):
    clicked = pyqtSignal(dict)

    def __init__(self, evt, title, subtitle, parent=None):
        super().__init__(parent)
        self.setObjectName("PanelRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._evt = evt
        self.setFixedHeight(row_height())
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.SPACE_2, theme.SPACE_2, theme.SPACE_2, theme.SPACE_2)
        layout.setSpacing(theme.SPACE_2)
        layout.addWidget(_LevelBar(evt.get("priority")))
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        self.title_label = _ElidedText(title, theme.FONT_SM, theme.WEIGHT_SEMIBOLD, theme.TEXT_PRIMARY)
        self.sub_label = _ElidedText(subtitle, theme.FONT_XS, theme.WEIGHT_REGULAR, theme.TEXT_SECONDARY)
        text_col.addWidget(self.title_label)
        text_col.addWidget(self.sub_label)
        layout.addLayout(text_col, 1)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit(self._evt)


class SidePanel(QFrame):
    event_activated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidePanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(theme.SIDE_PANEL_WIDTH)

        root = QVBoxLayout(self)
        root.setContentsMargins(theme.SPACE_4, theme.SPACE_2, theme.SPACE_2, theme.SPACE_3)
        root.setSpacing(theme.SPACE_2)

        # 兩個區塊各自一個捲動區（上下均分），選取日清單不會被很長的「即將到來」擠到畫面外
        self.upcoming_title = QLabel("即將到來")
        self.upcoming_title.setProperty("role", "section")
        root.addWidget(self.upcoming_title)
        self.upcoming_scroll, self.upcoming_box = self._make_list_area()
        root.addWidget(self.upcoming_scroll)

        self.selected_title = QLabel("")
        self.selected_title.setProperty("role", "section")
        root.addWidget(self.selected_title)
        self.selected_scroll, self.selected_box = self._make_list_area()
        root.addWidget(self.selected_scroll)
        root.addStretch(1)   # 清單高度由 _update_heights 手動決定，剩餘空間留在清單與圖例之間

        self._divider = QFrame()
        self._divider.setProperty("role", "divider")
        self._divider.setFrameShape(QFrame.Shape.NoFrame)
        self._divider.setFixedHeight(1)
        root.addWidget(self._divider)
        self._legend = self._build_legend()
        root.addWidget(self._legend)
        self._root = root

    @staticmethod
    def _make_list_area():
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        content = QWidget()
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        box = QVBoxLayout(content)
        box.setContentsMargins(0, 0, theme.SPACE_2, 0)
        box.setSpacing(0)
        box.addStretch(1)
        scroll.setWidget(content)
        content.setAutoFillBackground(False)   # QScrollArea.setWidget 會開啟自動填底，這裡要透出面板底色
        return scroll, box

    def _build_legend(self):
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, theme.SPACE_1, 0, 0)
        row.setSpacing(theme.SPACE_2)
        caption = QLabel("等級")
        caption.setProperty("role", "muted")
        row.addWidget(caption)
        for priority in ("major", "medium", "minor"):
            row.addWidget(LevelDot(priority))
            label = QLabel(theme.PRIORITY_LABEL[priority])
            label.setProperty("role", "muted")
            row.addWidget(label)
            row.addSpacing(theme.SPACE_2)
        row.addStretch(1)
        return holder

    # ------------------------------------------------------------ 高度

    def _content_height(self, box):
        """清單內容高度：每列固定高度 x 列數；空狀態以換行後的高度計。"""
        rows = sum(1 for i in range(box.count()) if isinstance(box.itemAt(i).widget(), _EventRow))
        if rows:
            return rows * row_height()
        for i in range(box.count()):
            widget = box.itemAt(i).widget()
            if widget is not None:
                width = theme.SIDE_PANEL_WIDTH - theme.SPACE_4 - 2 * theme.SPACE_2
                height = widget.layout().totalHeightForWidth(width)
                return height if height > 0 else widget.sizeHint().height()
        return 0

    def _available_list_height(self):
        for w in (self, self.upcoming_title, self.selected_title, self._legend):
            w.ensurePolished()
        margins = self._root.contentsMargins()
        fixed = (margins.top() + margins.bottom()
                 + self.upcoming_title.sizeHint().height() + self.selected_title.sizeHint().height()
                 + self._divider.height() + self._legend.sizeHint().height()
                 + 6 * self._root.spacing())          # 7 個項目（含 stretch）之間 6 個間距
        return max(0, self.height() - fixed)

    @staticmethod
    def _snap(content, room):
        """內容放得下就用內容高度；放不下則取整數列高（至少一列），讓最後一列不被切半。"""
        if content <= room:
            return content
        unit = row_height()
        return max(unit, room // unit * unit)

    def _update_heights(self):
        """「即將到來」高度 = min(內容, 可用一半)，其餘給選取日清單；超出的以整數列高捲動。"""
        avail = self._available_list_height()
        up_h = self._snap(self._content_height(self.upcoming_box), avail // 2)
        sel_h = self._snap(self._content_height(self.selected_box), max(0, avail - up_h))
        self.upcoming_scroll.setFixedHeight(up_h)
        self.selected_scroll.setFixedHeight(sel_h)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_heights()

    # ------------------------------------------------------------ 資料

    @staticmethod
    def _clear(box):
        # 最後一項是撐高用的 stretch，保留
        while box.count() > 1:
            item = box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    @staticmethod
    def _empty_state(primary, hint):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, theme.SPACE_2, theme.SPACE_2, theme.SPACE_2)
        layout.setSpacing(theme.SPACE_1)
        first = QLabel(primary)
        first.setProperty("role", "secondary")
        first.setWordWrap(True)
        second = QLabel(hint)
        second.setProperty("role", "muted")
        second.setWordWrap(True)
        layout.addWidget(first)
        layout.addWidget(second)
        return box

    def _add_row(self, box, evt, title, subtitle):
        row = _EventRow(evt, title, subtitle)
        row.clicked.connect(self.event_activated)
        box.insertWidget(box.count() - 1, row)

    def set_upcoming(self, items):
        """items: [(evt, days_until)]，由 calendar_logic.upcoming 產生。"""
        self._clear(self.upcoming_box)
        if not items:
            self.upcoming_box.insertWidget(0, self._empty_state(EMPTY_UPCOMING, EMPTY_UPCOMING_HINT))
            self._update_heights()
            return
        for evt, n in items:
            self._add_row(self.upcoming_box, evt, str(evt.get("title") or "（無標題）"),
                          cl.upcoming_subtitle(evt, n))
        self._update_heights()

    def set_selected_day(self, day, events, today):
        """events: 該日行程（已排序）。標題：今天 M/D 或 M/D 週X。"""
        self.selected_title.setText(cl.selected_title(day, today))
        self._clear(self.selected_box)
        if not events:
            self.selected_box.insertWidget(0, self._empty_state(EMPTY_DAY, EMPTY_DAY_HINT))
            self._update_heights()
            return
        for evt in events:
            sub = cl.event_time_text(evt)
            if evt.get("location"):
                sub = f"{sub} · {evt['location']}"
            self._add_row(self.selected_box, evt, str(evt.get("title") or "（無標題）"), sub)
        self._update_heights()

    def upcoming_row_count(self):
        return sum(1 for i in range(self.upcoming_box.count())
                   if isinstance(self.upcoming_box.itemAt(i).widget(), _EventRow))

    def selected_row_count(self):
        return sum(1 for i in range(self.selected_box.count())
                   if isinstance(self.selected_box.itemAt(i).widget(), _EventRow))
