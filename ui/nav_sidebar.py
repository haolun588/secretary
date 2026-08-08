"""
ui/nav_sidebar.py
左側主選單導覽欄 (Left Navigation Sidebar Container)
包含動態倒數計時文字標籤 update_countdown(text)
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtGui import QFont

class NavSidebar(QFrame):
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setFixedWidth(230)
        self.setStyleSheet("""
            QFrame#NavSidebar {
                background-color: #16161e;
                border-right: 1px solid #23232e;
            }
            QPushButton.NavBtn {
                background-color: transparent;
                color: #a0a0ab;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
                border: none;
                border-radius: 12px;
                padding: 12px 16px;
                text-align: left;
            }
            QPushButton.NavBtn:hover {
                background-color: #23232e;
                color: #ffffff;
            }
            QPushButton.NavBtnActive {
                background-color: #8b5cf6;
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
                border: none;
                border-radius: 12px;
                padding: 12px 16px;
                text-align: left;
            }
            QFrame#StatusCard {
                background-color: #1c1c24;
                border: 1px solid #2a2a36;
                border-radius: 14px;
            }
        """)
        self.setObjectName("NavSidebar")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(12)

        # 頂部 Logo
        logo_box = QHBoxLayout()
        logo_box.setSpacing(10)

        logo_icon = QLabel("⚡", self)
        logo_icon.setFont(QFont("Segoe UI Emoji", 20))
        logo_icon.setStyleSheet("""
            background-color: #8b5cf6;
            color: #ffffff;
            border-radius: 10px;
            padding: 4px;
        """)
        logo_icon.setFixedSize(36, 36)
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_text_box = QVBoxLayout()
        logo_text_box.setSpacing(0)
        
        logo_title = QLabel("Secretary", self)
        logo_title.setStyleSheet("color: #ffffff; font-size: 17px; font-weight: 800;")
        
        logo_sub = QLabel("智能桌面小助理", self)
        logo_sub.setStyleSheet("color: #a0a0ab; font-size: 11px;")

        logo_text_box.addWidget(logo_title)
        logo_text_box.addWidget(logo_sub)

        logo_box.addWidget(logo_icon)
        logo_box.addLayout(logo_text_box)
        logo_box.addStretch(1)

        layout.addLayout(logo_box)
        layout.addSpacing(16)

        # 導覽按鈕群組
        self.btn_calendar = QPushButton("📅  日曆與行程", self)
        self.btn_calendar.setObjectName("btn_calendar")
        self.btn_calendar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calendar.setProperty("active", True)
        self.btn_calendar.setProperty("class", "NavBtnActive")
        self.btn_calendar.clicked.connect(lambda: self.set_active_page(0))
        layout.addWidget(self.btn_calendar)

        self.btn_settings = QPushButton("⚙️  喝水與設定", self)
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setProperty("class", "NavBtn")
        self.btn_settings.clicked.connect(lambda: self.set_active_page(1))
        layout.addWidget(self.btn_settings)

        layout.addStretch(1)

        # 底部狀態卡片 (即時實時倒數文字)
        status_card = QFrame(self)
        status_card.setObjectName("StatusCard")
        sc_layout = QVBoxLayout(status_card)
        sc_layout.setContentsMargins(12, 12, 12, 12)
        sc_layout.setSpacing(8)

        status_top = QHBoxLayout()
        self.status_dot = QLabel("●", status_card)
        self.status_dot.setStyleSheet("color: #10b981; font-size: 14px;")
        
        self.status_title = QLabel("助理背景運作中", status_card)
        self.status_title.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 700;")
        
        status_top.addWidget(self.status_dot)
        status_top.addWidget(self.status_title)
        status_top.addStretch(1)

        self.status_lbl = QLabel("下次提醒: 10:00 後", status_card)
        self.status_lbl.setStyleSheet("color: #a0a0ab; font-size: 11.5px;")

        sc_layout.addLayout(status_top)
        sc_layout.addWidget(self.status_lbl)

        layout.addWidget(status_card)

    def set_active_page(self, page_index):
        if page_index == 0:
            self.btn_calendar.setProperty("class", "NavBtnActive")
            self.btn_settings.setProperty("class", "NavBtn")
        else:
            self.btn_calendar.setProperty("class", "NavBtn")
            self.btn_settings.setProperty("class", "NavBtnActive")

        self.btn_calendar.setStyle(self.btn_calendar.style())
        self.btn_settings.setStyle(self.btn_settings.style())

        self.page_changed.emit(page_index)

    def update_countdown(self, text, is_enabled=True):
        """實時更新左下角倒數計時文字與狀態點"""
        self.status_lbl.setText(text)
        if is_enabled:
            self.status_dot.setStyleSheet("color: #10b981; font-size: 14px;")
            self.status_title.setText("助理背景運作中")
            self.status_title.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 700;")
        else:
            self.status_dot.setStyleSheet("color: #f43f5e; font-size: 14px;")
            self.status_title.setText("喝水提醒已關閉")
            self.status_title.setStyleSheet("color: #f43f5e; font-size: 12px; font-weight: 700;")
