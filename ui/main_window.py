"""
ui/main_window.py
主視窗外框容器：左側窄版導覽列 + 右側頁面堆疊（0=日曆、1=喝水、2=MLB、3=設定）。
樣式由全域 QSS（ui/styles.py）負責；此檔只處理版面與頁面切換。
"""

import os

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from ui import theme
from ui.calendar_view import CalendarView
from ui.mlb_view import MlbView
from ui.nav_sidebar import NavSidebar
from ui.settings_view import SettingsView
from ui.water_view import WaterView
from utils.logger import get_logger
from utils.paths import asset_path
from utils.win_titlebar import enable_dark_titlebar, set_cloak

logger = get_logger(__name__)

# 視窗顯示後延遲取消 cloak 的毫秒數：等 RHI 第一張畫面畫好再露出，避免白閃
_UNCLOAK_DELAY_MS = 30


class MainWindow(QMainWindow):
    def __init__(self, config_manager=None, event_store=None, parent=None):
        super().__init__(parent)
        self.event_store = event_store
        self.config_manager = config_manager
        self.config = self.config_manager.load_config() if self.config_manager else {}
        self._titlebar_done = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Secretary 智能桌面小助理")
        self.resize(theme.WINDOW_W, theme.WINDOW_H)
        self.setMinimumSize(theme.WINDOW_MIN_W, theme.WINDOW_MIN_H)

        # 設定左上角與工作列圖示
        icon_path = asset_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左側導覽列（固定寬度）
        self.sidebar = NavSidebar(self)
        self.sidebar.page_changed.connect(self.on_page_changed)
        main_layout.addWidget(self.sidebar)

        # 右側多頁面堆疊視窗 (QStackedWidget)，可伸縮
        self.stacked_widget = QStackedWidget(self)

        self.calendar_view = CalendarView(self.event_store, self)
        self.water_view = WaterView(self)
        self.mlb_view = MlbView(self)
        self.settings_view = SettingsView(self.event_store, self)

        self.stacked_widget.addWidget(self.calendar_view)  # Index 0: 日曆
        self.stacked_widget.addWidget(self.water_view)  # Index 1: 喝水
        self.stacked_widget.addWidget(self.mlb_view)  # Index 2: MLB
        self.stacked_widget.addWidget(self.settings_view)  # Index 3: 設定

        main_layout.addWidget(self.stacked_widget, stretch=1)

    def on_page_changed(self, index):
        self.stacked_widget.setCurrentIndex(index)

    def showEvent(self, event):
        super().showEvent(event)
        # Qt 先送 QShowEvent 才真正顯示 native 視窗，此處 cloak 可蓋住 RHI 首張畫面前的白底
        if not event.spontaneous() and set_cloak(self, True):
            QTimer.singleShot(_UNCLOAK_DELAY_MS, lambda: set_cloak(self, False))
        if not self._titlebar_done:
            self._titlebar_done = True
            enable_dark_titlebar(self)

    def closeEvent(self, event):
        if self.config_manager:
            self.config = self.config_manager.load_config()

        minimize_to_tray = self.config.get("minimize_to_tray", True)

        if minimize_to_tray:
            event.ignore()
            self.hide()
        else:
            event.accept()
