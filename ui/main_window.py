"""
ui/main_window.py
主視窗外框容器 (Main Application Window Container)
綁定應用程式專屬紫光電光圖示 (icon.png)，美化左上角的視窗外框與工作列標誌。
"""

import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget
from PyQt6.QtGui import QIcon

from utils.paths import asset_path
from ui.nav_sidebar import NavSidebar
from ui.calendar_view import CalendarView
from ui.settings_view import SettingsView

class MainWindow(QMainWindow):
    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = self.config_manager.load_config() if self.config_manager else {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Secretary 智能桌面小助理")
        self.resize(1180, 740)
        self.setMinimumSize(960, 620)
        self.setStyleSheet("QMainWindow { background-color: #121217; }")

        # 設定左上角與工作列圖示
        icon_path = asset_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central_widget = QWidget(self)
        central_widget.setStyleSheet("background-color: #121217;")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左側導覽列
        self.sidebar = NavSidebar(self)
        self.sidebar.page_changed.connect(self.on_page_changed)
        main_layout.addWidget(self.sidebar)

        # 右側多頁面堆疊視窗 (QStackedWidget)
        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.setStyleSheet("background-color: #121217;")

        self.calendar_view = CalendarView(self)
        self.settings_view = SettingsView(self)

        self.stacked_widget.addWidget(self.calendar_view) # Index 0: 日曆儀表板
        self.stacked_widget.addWidget(self.settings_view) # Index 1: 系統與喝水設定

        # 串接 Google 授權連線成功訊號至日曆視窗
        self.settings_view.google_connected_signal.connect(self.calendar_view.on_google_events_synced)

        main_layout.addWidget(self.stacked_widget, stretch=1)

    def on_page_changed(self, index):
        self.stacked_widget.setCurrentIndex(index)

    def closeEvent(self, event):
        if self.config_manager:
            self.config = self.config_manager.load_config()
            
        minimize_to_tray = self.config.get("minimize_to_tray", True)
        
        if minimize_to_tray:
            event.ignore()
            self.hide()
        else:
            event.accept()
