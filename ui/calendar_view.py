"""
ui/calendar_view.py
日曆與近期提醒儀表板 (Calendar Dashboard View) - 包含 100% 依字數自適應高度與標題/地點/備註獨立三行卡片
"""

from datetime import datetime
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QCalendarWidget, QLabel,
    QPushButton, QScrollArea, QFrame, QSizePolicy, QHeaderView, QTableView
)
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCharFormat

from ui.calendar_dialog import CalendarDialog
from utils.google_calendar import GoogleCalendarService, GoogleFetchWorker

class CalendarView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.google_service = GoogleCalendarService()
        self.mock_events = []
        self.fetch_worker = None

        self.init_ui()
        self.customize_calendar_internals()

        # 每 60 秒背景非同步靜默刷新 Google 日曆
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.sync_google_events)
        self.sync_timer.start(60000)

        # 啟動時非同步載入 Google 日曆 (不阻塞 UI)
        QTimer.singleShot(100, self.sync_google_events)

    def init_ui(self):
        self.setStyleSheet("""
            QWidget#CalendarView {
                background-color: #121217;
                color: #ffffff;
            }
            
            /* 中間日曆卡片 (#1c1c24 底色) */
            QCalendarWidget {
                background-color: #1c1c24;
                border: 1px solid #2a2a36;
                border-radius: 16px;
                min-height: 380px;
            }
            
            /* 頂部年月導覽列 */
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #1c1c24;
                border-bottom: 1px solid #2a2a36;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                min-height: 52px;
            }
            QCalendarWidget QToolButton {
                color: #a0a0ab;
                font-size: 14.5px;
                font-weight: bold;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
                border-radius: 8px;
                padding: 6px 14px;
                margin: 2px;
                background-color: transparent;
                border: none;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #2a2a36;
                color: #8b5cf6;
            }
            QCalendarWidget QSpinBox {
                background-color: #121217;
                color: #ffffff;
                border: 1px solid #2a2a36;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                padding: 4px 34px 4px 10px;
                min-height: 36px;
            }
            QCalendarWidget QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 28px;
                height: 17px;
                background-color: #2a2a36;
                border-top-right-radius: 7px;
                margin: 1px 1px 0px 0px;
            }
            QCalendarWidget QSpinBox::up-button:hover {
                background-color: #8b5cf6;
            }
            QCalendarWidget QSpinBox::up-arrow {
                image: url(assets/arrow_up.png);
                width: 12px;
                height: 12px;
            }
            QCalendarWidget QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 28px;
                height: 17px;
                background-color: #2a2a36;
                border-bottom-right-radius: 7px;
                margin: 0px 1px 1px 0px;
            }
            QCalendarWidget QSpinBox::down-button:hover {
                background-color: #8b5cf6;
            }
            QCalendarWidget QSpinBox::down-arrow {
                image: url(assets/arrow_down.png);
                width: 12px;
                height: 12px;
            }
            QCalendarWidget QMenu {
                background-color: #1c1c24;
                color: #ffffff;
                border: 1px solid #2a2a36;
                border-radius: 8px;
            }
            
            /* 星期表頭 (日 一 二 三 四 五 六) */
            QCalendarWidget QHeaderView {
                background-color: #1c1c24;
                border: none;
            }
            QCalendarWidget QHeaderView::section {
                background-color: #1c1c24;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
                border: none;
                padding: 10px 0px;
            }
            
            /* 日期表格主體 */
            QCalendarWidget QTableView {
                background-color: #1c1c24;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
                selection-background-color: transparent;
                outline: 0;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
                selection-background-color: #8b5cf6;
                selection-color: #ffffff;
            }
            
            /* 全寬大紫光「+ 新增行程」按鈕 */
            QPushButton#AddEventBtn {
                background-color: #8b5cf6;
                color: #ffffff;
                font-weight: 700;
                font-size: 14px;
                border: none;
                border-radius: 12px;
                padding: 12px 20px;
            }
            QPushButton#AddEventBtn:hover {
                background-color: #7c3aed;
            }

            /* 右側頂點按鈕與同步鈕 */
            QPushButton#SyncGoogleBtn {
                background-color: #1c1c24;
                color: #8b5cf6;
                font-weight: 700;
                font-size: 11.5px;
                border: 1px solid rgba(139, 92, 246, 0.5);
                border-radius: 7px;
                padding: 5px 10px;
            }
            QPushButton#SyncGoogleBtn:hover {
                background-color: #8b5cf6;
                color: #ffffff;
            }
            QPushButton#TimeBtnActive {
                background-color: #8b5cf6;
                color: #ffffff;
                font-weight: 700;
                font-size: 11.5px;
                border: none;
                border-radius: 7px;
                padding: 5px 10px;
            }
            QPushButton#GridBtnOutline {
                background-color: #1c1c24;
                color: #a0a0ab;
                font-weight: 600;
                font-size: 11.5px;
                border: 1px solid #2a2a36;
                border-radius: 7px;
                padding: 5px 10px;
            }
            QPushButton#TodayNavBtn {
                background-color: transparent;
                color: #8b5cf6;
                font-weight: 600;
                font-size: 11.5px;
                border: 1px solid rgba(139, 92, 246, 0.4);
                border-radius: 7px;
                padding: 4px 8px;
            }
            
            QFrame#SidebarFrame {
                background-color: #16161e;
                border: 1px solid #23232e;
                border-radius: 18px;
            }
            QLabel#SidebarTitle {
                color: #ffffff;
                font-size: 16px;
                font-weight: 800;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
            }
            
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 5px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #2a2a36;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #8b5cf6;
            }
        """)
        self.setObjectName("CalendarView")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        # ----------------------------------------------------
        # 1. 中間區域：日曆與當日行程
        # ----------------------------------------------------
        middle_box = QVBoxLayout()
        middle_box.setSpacing(14)

        header_lbl = QLabel("今日行程", self)
        header_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff;")
        middle_box.addWidget(header_lbl)

        center_h_layout = QHBoxLayout()
        center_h_layout.setContentsMargins(0, 0, 0, 0)
        center_h_layout.addStretch(1)

        calendar_col = QVBoxLayout()
        calendar_col.setSpacing(14)

        self.calendar = QCalendarWidget(self)
        self.calendar.setFixedWidth(440)
        self.calendar.setMinimumHeight(380)
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        
        purple_fmt = QTextCharFormat()
        purple_fmt.setForeground(QColor("#8b5cf6"))
        purple_fmt.setFontWeight(QFont.Weight.Bold)
        self.calendar.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, purple_fmt)
        self.calendar.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, purple_fmt)

        self.calendar.selectionChanged.connect(self.on_date_selected)
        calendar_col.addWidget(self.calendar)

        add_btn = QPushButton("+ 新增行程", self)
        add_btn.setObjectName("AddEventBtn")
        add_btn.setFixedWidth(440)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.on_add_event_clicked)
        calendar_col.addWidget(add_btn)

        self.today_events_card = QFrame(self)
        self.today_events_card.setFixedWidth(440)
        self.today_events_card.setStyleSheet("""
            QFrame {
                background-color: #1c1c24;
                border: 1px solid #2a2a36;
                border-radius: 14px;
                padding: 12px;
            }
        """)
        card_layout = QVBoxLayout(self.today_events_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        self.selected_date_lbl = QLabel("📌 選取日期行程", self.today_events_card)
        self.selected_date_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #8b5cf6;")
        card_layout.addWidget(self.selected_date_lbl)

        self.date_events_area = QScrollArea(self.today_events_card)
        self.date_events_area.setWidgetResizable(True)
        self.date_events_area.setMinimumHeight(120)
        self.date_events_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.date_events_area.setStyleSheet("border: none; background: transparent;")
        
        self.date_events_widget = QWidget()
        self.date_events_layout = QVBoxLayout(self.date_events_widget)
        self.date_events_layout.setContentsMargins(0, 0, 0, 0)
        self.date_events_layout.setSpacing(8)
        self.date_events_area.setWidget(self.date_events_widget)

        card_layout.addWidget(self.date_events_area)
        calendar_col.addWidget(self.today_events_card)

        center_h_layout.addLayout(calendar_col)
        center_h_layout.addStretch(1)

        middle_box.addLayout(center_h_layout)
        middle_box.addStretch(1)

        main_layout.addLayout(middle_box, stretch=1)

        # ----------------------------------------------------
        # 2. 右側區域：提醒面板 (340px 寬，雙行頂部導覽按鈕列)
        # ----------------------------------------------------
        right_container = QWidget(self)
        right_container.setFixedWidth(340)

        right_box = QVBoxLayout(right_container)
        right_box.setContentsMargins(0, 0, 0, 0)
        right_box.setSpacing(8)

        top_nav_row1 = QHBoxLayout()
        top_nav_row1.setContentsMargins(0, 0, 0, 0)
        top_nav_row1.setSpacing(6)

        self.date_header_title = QLabel("📅 2026/08/09 (週日)", right_container)
        self.date_header_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #ffffff;")
        top_nav_row1.addWidget(self.date_header_title)

        prev_btn = QPushButton("‹", right_container)
        prev_btn.setFixedSize(24, 24)
        prev_btn.setStyleSheet("color: #ffffff; font-size: 15px; background-color: #1c1c24; border: 1px solid #2a2a36; border-radius: 6px;")
        prev_btn.clicked.connect(lambda: self.calendar.setSelectedDate(self.calendar.selectedDate().addDays(-1)))
        top_nav_row1.addWidget(prev_btn)

        next_btn = QPushButton("›", right_container)
        next_btn.setFixedSize(24, 24)
        next_btn.setStyleSheet("color: #ffffff; font-size: 15px; background-color: #1c1c24; border: 1px solid #2a2a36; border-radius: 6px;")
        next_btn.clicked.connect(lambda: self.calendar.setSelectedDate(self.calendar.selectedDate().addDays(1)))
        top_nav_row1.addWidget(next_btn)

        today_btn = QPushButton("回到今天", right_container)
        today_btn.setObjectName("TodayNavBtn")
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        today_btn.clicked.connect(lambda: self.calendar.setSelectedDate(QDate.currentDate()))
        top_nav_row1.addWidget(today_btn)

        top_nav_row1.addStretch(1)
        right_box.addLayout(top_nav_row1)

        top_nav_row2 = QHBoxLayout()
        top_nav_row2.setContentsMargins(0, 0, 0, 0)
        top_nav_row2.setSpacing(8)

        self.sync_btn = QPushButton("🔄 雲端同步", right_container)
        self.sync_btn.setObjectName("SyncGoogleBtn")
        self.sync_btn.setToolTip("手動非同步同步 Google 日曆最新行程")
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.clicked.connect(self.sync_google_events)
        top_nav_row2.addWidget(self.sync_btn)

        top_nav_row2.addStretch(1)

        time_btn = QPushButton("≡ 日時間軸", right_container)
        time_btn.setObjectName("TimeBtnActive")
        top_nav_row2.addWidget(time_btn)

        grid_btn = QPushButton("▦ 月網格", right_container)
        grid_btn.setObjectName("GridBtnOutline")
        top_nav_row2.addWidget(grid_btn)

        right_box.addLayout(top_nav_row2)

        sidebar_frame = QFrame(right_container)
        sidebar_frame.setObjectName("SidebarFrame")

        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(14, 14, 14, 14)
        sidebar_layout.setSpacing(10)

        sb_header = QHBoxLayout()
        sb_title = QLabel("🔔 近期倒數提醒", sidebar_frame)
        sb_title.setObjectName("SidebarTitle")
        sb_header.addWidget(sb_title)
        sb_header.addStretch(1)

        rule_badge = QLabel("等級過濾", sidebar_frame)
        rule_badge.setStyleSheet("""
            background-color: rgba(139, 92, 246, 0.15);
            color: #a78bfa;
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 10px;
            padding: 2px 7px;
            font-size: 10.5px;
            font-weight: 600;
        """)
        sb_header.addWidget(rule_badge)
        sidebar_layout.addLayout(sb_header)

        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(4)
        
        leg_items = [("🔴大:30天", "#f43f5e"), ("🟡中:7天", "#f59e0b"), ("🟢小:3天", "#10b981")]
        for text, color in leg_items:
            lbl = QLabel(text, sidebar_frame)
            lbl.setStyleSheet(f"color: {color}; font-size: 10.5px; font-weight: 600;")
            legend_layout.addWidget(lbl)
        legend_layout.addStretch(1)

        sidebar_layout.addLayout(legend_layout)

        self.sidebar_scroll = QScrollArea(sidebar_frame)
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar_scroll.setStyleSheet("border: none; background: transparent;")

        self.sidebar_content_widget = QWidget()
        self.sidebar_content_layout = QVBoxLayout(self.sidebar_content_widget)
        self.sidebar_content_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_content_layout.setSpacing(8)
        self.sidebar_scroll.setWidget(self.sidebar_content_widget)

        sidebar_layout.addWidget(self.sidebar_scroll)
        right_box.addWidget(sidebar_frame, stretch=1)

        main_layout.addWidget(right_container)

        self.refresh_upcoming_sidebar()
        self.on_date_selected()

    def customize_calendar_internals(self):
        try:
            pal = self.calendar.palette()
            pal.setColor(QPalette.ColorRole.Base, QColor("#1c1c24"))
            pal.setColor(QPalette.ColorRole.Window, QColor("#1c1c24"))
            pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#1c1c24"))
            pal.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
            pal.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
            pal.setColor(QPalette.ColorRole.Highlight, QColor("#8b5cf6"))
            pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            self.calendar.setPalette(pal)

            for child in self.calendar.findChildren(QWidget):
                child.setPalette(pal)
                if isinstance(child, QHeaderView) or child.inherits("QHeaderView"):
                    child.setStyleSheet("background-color: #1c1c24; color: #ffffff; border: none;")
                elif isinstance(child, QTableView) or child.inherits("QTableView") or "CalendarView" in child.metaObject().className():
                    child.setStyleSheet("background-color: #1c1c24; color: #ffffff; selection-background-color: #8b5cf6;")
        except Exception as e:
            print(f"[CalendarView] 樣式覆蓋: {e}")

    def sync_google_events(self):
        if self.fetch_worker and self.fetch_worker.isRunning():
            return

        self.sync_btn.setText("🔄 同步中...")
        self.fetch_worker = GoogleFetchWorker(self.google_service)
        self.fetch_worker.fetched_signal.connect(self.on_async_events_fetched)
        self.fetch_worker.start()

    def on_async_events_fetched(self, events):
        self.sync_btn.setText("🔄 雲端同步")
        if events:
            self.on_google_events_synced(events)

    def refresh_upcoming_sidebar(self):
        while self.sidebar_content_layout.count():
            item = self.sidebar_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today = QDate.currentDate()
        upcoming_items = []

        for evt in self.mock_events:
            evt_date = evt["date"]
            days_diff = today.daysTo(evt_date)

            if days_diff < 0:
                continue

            prio = evt.get("priority", "minor")
            show = False
            if prio == "major" and days_diff <= 30:
                show = True
            elif prio == "medium" and days_diff <= 7:
                show = True
            elif prio == "minor" and days_diff <= 3:
                show = True

            if show:
                upcoming_items.append((evt, days_diff))

        upcoming_items.sort(key=lambda x: x[1])

        if not upcoming_items:
            empty_box = QVBoxLayout()
            empty_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            icon_lbl = QLabel("✨", self)
            icon_lbl.setFont(QFont("Segoe UI Emoji", 24))
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_box.addWidget(icon_lbl)

            no_lbl = QLabel("目前無近期需提醒事項", self)
            no_lbl.setStyleSheet("color: #a0a0ab; font-size: 12px; text-align: center; margin-top: 4px;")
            no_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_box.addWidget(no_lbl)

            w = QWidget()
            w.setLayout(empty_box)
            self.sidebar_content_layout.addWidget(w)
        else:
            for evt, days_diff in upcoming_items:
                card = self.create_event_card(evt, days_diff)
                self.sidebar_content_layout.addWidget(card)

        self.sidebar_content_layout.addStretch(1)

    def create_event_card(self, evt, days_diff):
        card = QFrame(self)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        prio = evt.get("priority", "minor")
        if prio == "major":
            badge_text = "● 大事件 · 提前30天"
            badge_color = "#f43f5e"
            border_css = "border: 1px solid rgba(244, 63, 94, 0.4);"
            bg_css = "background-color: #1c1c24;"
        elif prio == "medium":
            badge_text = "● 中事件 · 提前7天"
            badge_color = "#f59e0b"
            border_css = "border: 1px solid rgba(245, 158, 11, 0.4);"
            bg_css = "background-color: #1c1c24;"
        else:
            badge_text = "● 小事件 · 提前3天"
            badge_color = "#10b981"
            border_css = "border: 1px solid rgba(16, 185, 129, 0.4);"
            bg_css = "background-color: #1c1c24;"

        card.setStyleSheet(f"""
            QFrame {{
                {bg_css}
                {border_css}
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: #8b5cf6;
                background-color: #23232e;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        top_h = QHBoxLayout()
        badge = QLabel(badge_text, card)
        badge.setStyleSheet(f"color: {badge_color}; font-weight: 700; font-size: 10.5px; border: none; background: transparent;")
        top_h.addWidget(badge)
        top_h.addStretch(1)

        countdown_str = "🔥 今天到期" if days_diff == 0 else f"⏳ 剩餘 {days_diff} 天"
        cnt_lbl = QLabel(countdown_str, card)
        cnt_lbl.setStyleSheet("""
            background-color: #2a2a36;
            color: #ffffff;
            font-weight: 700;
            font-size: 10.5px;
            border-radius: 5px;
            padding: 2px 5px;
            border: none;
        """)
        top_h.addWidget(cnt_lbl)
        layout.addLayout(top_h)

        title_lbl = QLabel(evt["title"], card)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 13px; border: none; background: transparent;")
        layout.addWidget(title_lbl)

        date_str = evt["date"].toString("yyyy/MM/dd (ddd)")
        date_lbl = QLabel(f"📅 {date_str}", card)
        date_lbl.setWordWrap(True)
        date_lbl.setStyleSheet("color: #a0a0ab; font-size: 10.5px; border: none; background: transparent;")
        layout.addWidget(date_lbl)

        if evt.get("location"):
            loc_lbl = QLabel(f"📍 {evt['location']}", card)
            loc_lbl.setWordWrap(True)
            loc_lbl.setStyleSheet("color: #71717a; font-size: 10.5px; border: none; background: transparent;")
            layout.addWidget(loc_lbl)

        card.mousePressEvent = lambda event, e=evt: self.on_edit_event(e)
        return card

    def create_today_event_card(self, evt):
        """建立當日行程列表卡片 (標題/地點/備註三行獨立，100% 依字數自適應高度)"""
        card = QFrame(self)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        prio = evt.get("priority", "minor")
        tag_color = "#f43f5e" if prio == "major" else ("#f59e0b" if prio == "medium" else "#10b981")

        card.setStyleSheet(f"""
            QFrame {{
                background-color: #121217;
                border: 1px solid #2a2a36;
                border-left: 4px solid {tag_color};
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: #8b5cf6;
                border-left: 4px solid {tag_color};
                background-color: #23232e;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        # 第一行：行程標題 (獨立一行，長字串自動折行)
        title_html = f'<div style="word-break: break-all; color: #ffffff; font-weight: 700; font-size: 13px; line-height: 1.3;">📌  {evt.get("title", "無標題")}</div>'
        title_lbl = QLabel(title_html, card)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("border: none; background: transparent; margin: 0; padding: 0;")
        layout.addWidget(title_lbl)

        # 第二行：地點 (若有填寫，獨立一行，不與標題搶位置)
        if evt.get("location"):
            loc_html = f'<div style="word-break: break-all; color: #a0a0ab; font-size: 11.5px; line-height: 1.3;">📍  {evt["location"]}</div>'
            loc_lbl = QLabel(loc_html, card)
            loc_lbl.setWordWrap(True)
            loc_lbl.setStyleSheet("border: none; background: transparent; margin: 0; padding: 0;")
            layout.addWidget(loc_lbl)

        # 第三行：備註資訊 (若有填寫，獨立一行，長字串自動折行)
        if evt.get("notes"):
            notes_html = f'<div style="word-break: break-all; color: #8b8b9e; font-size: 11.5px; line-height: 1.3;">📝  {evt["notes"]}</div>'
            notes_lbl = QLabel(notes_html, card)
            notes_lbl.setWordWrap(True)
            notes_lbl.setStyleSheet("border: none; background: transparent; margin: 0; padding: 0;")
            layout.addWidget(notes_lbl)

        card.mousePressEvent = lambda event, e=evt: self.on_edit_event(e)
        return card

    def on_date_selected(self):
        sel_date = self.calendar.selectedDate()
        date_str = sel_date.toString("yyyy/MM/dd (ddd)")
        self.date_header_title.setText(f"📅 {date_str}")
        self.selected_date_lbl.setText(f"📌 {date_str} 之當日行程")

        while self.date_events_layout.count():
            item = self.date_events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        date_events = [e for e in self.mock_events if e["date"] == sel_date]

        if not date_events:
            empty_lbl = QLabel("本日尚未安排任何行程，點擊上方按鈕新增 ➕", self)
            empty_lbl.setStyleSheet("color: #71717a; font-size: 12px; font-style: italic; margin-top: 4px;")
            self.date_events_layout.addWidget(empty_lbl)
        else:
            for evt in date_events:
                card = self.create_today_event_card(evt)
                self.date_events_layout.addWidget(card)
            # 加上彈性拉伸，確保所有卡片高度 100% 依字數緊縮適應！
            self.date_events_layout.addStretch(1)

    def on_add_event_clicked(self):
        dlg = CalendarDialog(self)
        if dlg.exec() == CalendarDialog.DialogCode.Accepted:
            data = dlg.get_data()
            new_evt = {
                "id": str(len(self.mock_events) + 1),
                "title": data["title"] or "新行程",
                "date": QDate.fromString(data["start"][:10], "yyyy-MM-dd"),
                "start": data["start"],
                "end": data["end"],
                "priority": data["priority"],
                "location": data["location"],
                "notes": data["notes"]
            }
            self.google_service.add_event(new_evt)

            self.mock_events.append(new_evt)
            self.refresh_upcoming_sidebar()
            self.on_date_selected()

    def on_google_events_synced(self, google_events):
        if google_events:
            self.mock_events = []
            for g_evt in google_events:
                try:
                    start_str = g_evt["start"][:10]
                    g_date = QDate.fromString(start_str, "yyyy-MM-dd")
                    g_evt["date"] = g_date
                    self.mock_events.append(g_evt)
                except Exception as e:
                    print(f"[CalendarView] 解析 Google 行程時間失敗: {e}")

            self.refresh_upcoming_sidebar()
            self.on_date_selected()

    def on_edit_event(self, evt):
        dlg = CalendarDialog(self, event_data=evt)
        res = dlg.exec()
        if dlg.is_delete or res == 2:
            evt_id = evt.get("id")
            if evt_id:
                self.google_service.delete_event(evt_id)
            if evt in self.mock_events:
                self.mock_events.remove(evt)
            self.refresh_upcoming_sidebar()
            self.on_date_selected()
        elif res == CalendarDialog.DialogCode.Accepted:
            data = dlg.get_data()
            evt["title"] = data["title"] or evt["title"]
            evt["priority"] = data["priority"]
            evt["location"] = data["location"]
            evt["notes"] = data["notes"]
            
            # 同步更新至 Google Calendar 雲端
            if evt.get("id"):
                self.google_service.update_event(evt)

            self.refresh_upcoming_sidebar()
            self.on_date_selected()
