"""
ui/calendar_view.py
日曆頁：工具列（標題 / 導覽 / 月週日切換 / 同步狀態 / 新增）+ 月格或時間軸 + 右側面板。

資料來源是 EventStore（events_changed 推送完整清單）；本頁不直接碰網路。
樣式一律來自 ui/styles.py 全域 QSS（Toolbar、CalendarSurface、SidePanel…）。
"""

from datetime import date

from PyQt6.QtCore import QDate, QSize, Qt, QTimer
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                             QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

from ui import calendar_logic as cl
from ui import icons, theme
from ui.calendar_dialog import CalendarDialog
from ui.components import IconButton, SegmentedControl, SyncStatusBadge
from ui.month_grid import MonthGrid
from ui.side_panel import SidePanel
from ui.styles import make_font
from ui.time_grid import TimeGrid
from utils.logger import get_logger

logger = get_logger(__name__)

_VIEW_OPTIONS = [(cl.VIEW_MONTH, "月"), (cl.VIEW_WEEK, "週"), (cl.VIEW_DAY, "日")]
_PREV_TIPS = {cl.VIEW_MONTH: "上個月", cl.VIEW_WEEK: "上一週", cl.VIEW_DAY: "前一天"}
_NEXT_TIPS = {cl.VIEW_MONTH: "下個月", cl.VIEW_WEEK: "下一週", cl.VIEW_DAY: "後一天"}


def _to_qdate(d):
    return QDate(d.year, d.month, d.day)


class CalendarView(QWidget):
    def __init__(self, event_store, parent=None):
        super().__init__(parent)

        self.event_store = event_store
        # store 推來的事件複本；QDate 另存於 _qdate_start/_qdate_end（date 另存於 _d_start/_d_end），
        # 不寫回 store 的 dict
        self._events = []
        self._today = date.today            # 可注入，方便測試
        self._selected = self._today()
        self._view_mode = cl.VIEW_MONTH
        self._ensured_key = None

        self.init_ui()

        self.event_store.events_changed.connect(self.on_events_changed)
        self.event_store.sync_state_changed.connect(self.on_sync_state_changed)

        # 每 60 秒背景非同步靜默刷新 Google 日曆
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.sync_google_events)
        self.sync_timer.start(60000)

        self._refresh_all()

    # ------------------------------------------------------------ 版面

    def init_ui(self):
        self.setObjectName("CalendarView")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        surface = QFrame(self)
        surface.setObjectName("CalendarSurface")
        surface.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        surface.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(theme.SPACE_4, theme.SPACE_3, theme.SPACE_4, theme.SPACE_4)
        self.view_stack = QStackedWidget(surface)
        self.month_grid = MonthGrid(self.view_stack)
        self.time_grid = TimeGrid(self.view_stack)
        self.view_stack.addWidget(self.month_grid)   # 0 = 月
        self.view_stack.addWidget(self.time_grid)    # 1 = 週 / 日
        surface_layout.addWidget(self.view_stack)
        body.addWidget(surface, 1)

        self.side_panel = SidePanel(self)
        body.addWidget(self.side_panel)
        root.addLayout(body, 1)

        self.month_grid.date_selected.connect(self.set_selected_date)
        self.month_grid.date_activated.connect(self._add_event_on)
        self.month_grid.event_activated.connect(self.on_edit_event)
        self.time_grid.date_selected.connect(self.set_selected_date)
        self.time_grid.date_activated.connect(self._add_event_on)
        self.time_grid.event_activated.connect(self.on_edit_event)
        self.side_panel.event_activated.connect(self.on_edit_event)

    def _build_toolbar(self):
        bar = QFrame(self)
        bar.setObjectName("Toolbar")
        bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(theme.SPACE_4, theme.SPACE_3, theme.SPACE_4, theme.SPACE_3)
        layout.setSpacing(theme.SPACE_2)
        self.toolbar = bar

        self.title_label = QLabel("")
        self.title_label.setObjectName("ToolbarTitle")
        self._title_metrics = QFontMetrics(make_font(theme.FONT_LG, theme.WEIGHT_SEMIBOLD))
        self._reserve_title_width(self._view_mode)
        layout.addWidget(self.title_label)

        self.btn_prev = IconButton("chevron-left", _PREV_TIPS[self._view_mode])
        self.btn_next = IconButton("chevron-right", _NEXT_TIPS[self._view_mode])
        self.btn_prev.clicked.connect(lambda: self.navigate(-1))
        self.btn_next.clicked.connect(lambda: self.navigate(1))
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_next)

        self.btn_today = QPushButton("今天")
        self.btn_today.setProperty("variant", "secondary")
        self.btn_today.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_today.clicked.connect(self.go_today)
        layout.addWidget(self.btn_today)

        layout.addStretch(1)

        self.view_seg = SegmentedControl(_VIEW_OPTIONS)
        self.view_seg.set_current(self._view_mode)
        self.view_seg.changed.connect(self.set_view_mode)
        layout.addWidget(self.view_seg)

        self.sync_btn = SyncStatusBadge()
        self.sync_btn.setToolTip("同步 Google 日曆")
        self.sync_btn.clicked.connect(self.on_sync_clicked)
        layout.addWidget(self.sync_btn)

        self.btn_add = QPushButton("新增")
        self.btn_add.setProperty("variant", "primary")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setIcon(icons.icon("plus", theme.TEXT_ON_ACCENT, theme.ICON_SM))
        self.btn_add.setIconSize(QSize(theme.ICON_SM, theme.ICON_SM))
        self.btn_add.clicked.connect(self.on_add_event_clicked)
        layout.addWidget(self.btn_add)
        return bar

    # ------------------------------------------------------------ 視圖狀態

    def selected_date(self):
        return self._selected

    def view_mode(self):
        return self._view_mode

    def set_selected_date(self, day):
        if day == self._selected:
            return
        self._selected = day
        self._refresh_all()

    def set_view_mode(self, mode):
        if mode not in (cl.VIEW_MONTH, cl.VIEW_WEEK, cl.VIEW_DAY):
            logger.warning(f"未知的視圖模式: {mode!r}")
            return
        self._view_mode = mode
        self.view_seg.set_current(mode)      # 程式呼叫時同步分段鈕（不發 signal）
        self._refresh_all()

    def navigate(self, step):
        self.set_selected_date(cl.shift_anchor(self._selected, self._view_mode, step))

    def go_today(self):
        self.set_selected_date(self._today())

    def _reserve_title_width(self, mode):
        """依視圖模式預留該模式可能出現的最長標題寬度：連點 ‹ › 時按鈕不跳動，又不浪費空間。"""
        width = max(self._title_metrics.horizontalAdvance(t) for t in cl.title_width_samples(mode))
        self.title_label.setMinimumWidth(width)

    def _refresh_all(self):
        mode, sel = self._view_mode, self._selected
        dates = cl.view_dates(mode, sel)
        self._reserve_title_width(mode)
        self.title_label.setText(cl.format_view_title(mode, sel, dates))
        self.btn_prev.setToolTip(_PREV_TIPS[mode])
        self.btn_next.setToolTip(_NEXT_TIPS[mode])
        if mode == cl.VIEW_MONTH:
            self.month_grid.set_month(sel.year, sel.month)
            self.month_grid.set_selected(sel)
            self.view_stack.setCurrentWidget(self.month_grid)
        else:
            self.time_grid.set_days(dates)
            self.time_grid.set_selected(sel)
            self.view_stack.setCurrentWidget(self.time_grid)
        self._refresh_data_views()
        self._ensure_visible_months(dates)

    def _refresh_data_views(self):
        """把 _events 推給目前的視圖與側欄。"""
        today = self._today()
        if self._view_mode == cl.VIEW_MONTH:
            self.month_grid.set_events(self._events)
        else:
            self.time_grid.set_events(self._events)
        self.side_panel.set_upcoming(cl.upcoming(self._events, today))
        self.side_panel.set_selected_day(self._selected, cl.events_on(self._events, self._selected), today)

    def _ensure_visible_months(self, dates):
        """換範圍時通知 store 拉資料；範圍（anchor 月份）沒變就不重複呼叫。

        EventStore.ensure_month 會拉前後各一個月，所以只需指定一個月份：
        週視圖用該週第一天所在月份（週內點跨月日期不重拉），月 / 日視圖用選取日所在月份。
        """
        anchor_day = dates[0] if self._view_mode == cl.VIEW_WEEK else self._selected
        anchor = (anchor_day.year, anchor_day.month)
        if anchor == self._ensured_key:
            return
        self._ensured_key = anchor
        self.event_store.ensure_month(*anchor)

    # ------------------------------------------------------------ 同步

    def sync_google_events(self):
        """60 秒計時器用：未授權時靜默略過"""
        if self.event_store.is_authenticated:
            self.event_store.refresh()

    def on_sync_clicked(self):
        """手動按鈕：未授權時給回饋，已授權則重新拉取"""
        if self.event_store.is_authenticated:
            self.event_store.refresh()
            return
        message = "尚未連線 Google 日曆，請到設定頁授權"
        self.sync_btn.setToolTip(message)
        QMessageBox.information(self, "尚未連線", message)

    def on_sync_state_changed(self, state, message):
        self.sync_btn.set_state(state, message)

    # ------------------------------------------------------------ 資料

    def on_events_changed(self, events):
        """store 推送完整事件清單（含空清單，需清空並重繪）"""
        self._events = []
        for ev in events:
            try:
                span = cl.parse_event_dates(ev)
                if span is None:
                    continue
                item = dict(ev)
                item["_d_start"], item["_d_end"] = span
                item["_qdate_start"] = _to_qdate(span[0])
                item["_qdate_end"] = _to_qdate(span[1])
                self._events.append(item)
            except Exception:
                logger.exception("解析行程時間失敗")
        self._refresh_data_views()

    # ------------------------------------------------------------ 新增 / 編輯

    def on_add_event_clicked(self):
        self._add_event_on(self._selected)

    def _add_event_on(self, day):
        dlg = CalendarDialog(parent=self, default_date=_to_qdate(day))
        if dlg.exec() == CalendarDialog.DialogCode.Accepted:
            # 不在本地 append，等 store 寫入成功後以 events_changed 更新
            self.event_store.add_event(dlg.get_data())

    def on_edit_event(self, evt):
        dlg = CalendarDialog(parent=self, event_data=evt)
        res = dlg.exec()
        evt_id = evt.get("id")
        if dlg.is_delete or res == 2:
            if evt_id:
                self.event_store.delete_event(evt_id)
        elif res == CalendarDialog.DialogCode.Accepted:
            if evt_id:
                self.event_store.update_event(evt_id, dlg.get_data())
