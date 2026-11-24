"""
ui/settings_view.py
系統與喝水提醒設定頁面 (Settings & Configuration View) - 移除備份儲存按鈕
所有設定選項 (喝水開關、時間間隔) 均為實時自動儲存 (Auto-Save)，無需手動點擊儲存按鈕。
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QPushButton, QCheckBox, QFrame, QGroupBox, QMessageBox, QScrollArea
)
from ui.toast_window import ToastWindow
from utils.google_calendar import GoogleCalendarService

class SettingsView(QWidget):
    google_connected_signal = pyqtSignal(list)
    water_enabled_signal = pyqtSignal(bool)
    autostart_signal = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.google_service = GoogleCalendarService()
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget#SettingsView {
                background-color: #121217;
                color: #ffffff;
            }
            QGroupBox {
                background-color: #1c1c24;
                border: 1px solid #2a2a36;
                border-radius: 16px;
                margin-top: 20px;
                padding-top: 28px;
                padding-bottom: 16px;
                padding-left: 20px;
                padding-right: 20px;
                font-weight: 700;
                font-size: 14.5px;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
                color: #8b5cf6;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 20px;
                top: 2px;
                padding: 0 8px;
                background-color: #1c1c24;
                border-radius: 4px;
            }
            QLabel {
                color: #a0a0ab;
                font-size: 13.5px;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
                line-height: 1.5;
            }
            QSpinBox {
                background-color: #121217;
                border: 1px solid #2a2a36;
                border-radius: 10px;
                padding: 8px 16px;
                color: #8b5cf6;
                font-size: 15px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border-color: #8b5cf6;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
                spacing: 10px;
            }
            QPushButton#TestBtn {
                background-color: #8b5cf6;
                color: #ffffff;
                font-weight: 700;
                font-size: 13.5px;
                border: none;
                border-radius: 10px;
                padding: 11px 22px;
            }
            QPushButton#TestBtn:hover {
                background-color: #7c3aed;
            }
            QPushButton#ConnectGoogleBtn {
                background-color: #ea4335;
                color: #ffffff;
                font-weight: 700;
                font-size: 13.5px;
                border: none;
                border-radius: 10px;
                padding: 11px 22px;
            }
            QPushButton#ConnectGoogleBtn:hover {
                background-color: #d93025;
            }
        """)
        self.setObjectName("SettingsView")

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background: transparent;")

        container_widget = QWidget()
        container_widget.setStyleSheet("background-color: #121217;")

        layout = QVBoxLayout(container_widget)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # 頂部標題
        header_box = QVBoxLayout()
        header_box.setSpacing(6)

        header_lbl = QLabel("⚙️ 系統與喝水提醒設定", container_widget)
        header_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff;")
        header_box.addWidget(header_lbl)

        header_sub = QLabel("個人化提醒時間偏好、提醒總開關與 Google Calendar 雲端帳號授權管理", container_widget)
        header_sub.setStyleSheet("font-size: 13px; color: #a0a0ab;")
        header_box.addWidget(header_sub)

        layout.addLayout(header_box)

        # ----------------------------------------------------
        # 1. 喝水提醒設定卡片
        # ----------------------------------------------------
        water_group = QGroupBox("💧 喝水定時提醒偏好", container_widget)
        w_layout = QVBoxLayout(water_group)
        w_layout.setContentsMargins(24, 20, 24, 20)
        w_layout.setSpacing(18)

        self.chk_water_enabled = QCheckBox("啟用喝水定時提醒通知 (Enable Drink Water Reminders)", water_group)
        self.chk_water_enabled.setChecked(True)
        self.chk_water_enabled.toggled.connect(self.on_water_enabled_toggled)
        w_layout.addWidget(self.chk_water_enabled)

        interval_row = QHBoxLayout()
        interval_lbl = QLabel("提醒時間間隔 (分鐘)：", water_group)
        interval_lbl.setStyleSheet("color: #ffffff; font-weight: 600;")
        interval_row.addWidget(interval_lbl)

        self.spin_interval = QSpinBox(water_group)
        self.spin_interval.setRange(1, 180)
        self.spin_interval.setValue(10)
        self.spin_interval.setSuffix(" 分鐘")
        self.spin_interval.setFixedWidth(150)
        interval_row.addWidget(self.spin_interval)
        interval_row.addStretch(1)

        w_layout.addLayout(interval_row)

        desc_lbl = QLabel("💡 說明：小助理於背景倒數，每隔設定時間在螢幕右下角跳出 3 秒淡出彈窗提醒。", water_group)
        desc_lbl.setStyleSheet("color: #a0a0ab; font-size: 12.5px; padding-left: 2px;")
        w_layout.addWidget(desc_lbl)

        test_row = QHBoxLayout()
        test_btn = QPushButton("🔔 庫即測試右下角提醒彈窗 (3秒淡出)", water_group)
        test_btn.setObjectName("TestBtn")
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.clicked.connect(self.on_test_toast)
        test_row.addWidget(test_btn)
        test_row.addStretch(1)
        w_layout.addLayout(test_row)

        layout.addWidget(water_group)

        # ----------------------------------------------------
        # 2. Windows 開機自啟動與系統設定卡片
        # ----------------------------------------------------
        system_group = QGroupBox("🚀 Windows 系統自動啟動偏好", container_widget)
        s_layout = QVBoxLayout(system_group)
        s_layout.setContentsMargins(24, 20, 24, 20)
        s_layout.setSpacing(14)

        self.chk_autostart = QCheckBox("開機自動啟動 Windows (Start automatically on Windows boot)", system_group)
        self.chk_autostart.setChecked(True)
        self.chk_autostart.toggled.connect(self.on_autostart_toggled)
        s_layout.addWidget(self.chk_autostart)

        s_desc = QLabel("💡 說明：勾選後將寫入 Windows 登錄檔，電腦開機後小助理將自動背景靜默啟動並隱藏於系統工作列圖示。", system_group)
        s_desc.setStyleSheet("color: #a0a0ab; font-size: 12.5px; padding-left: 2px;")
        s_layout.addWidget(s_desc)

        layout.addWidget(system_group)

        # ----------------------------------------------------
        # 3. Google 日曆 API 串接設定卡片
        # ----------------------------------------------------
        google_group = QGroupBox("📅 Google Calendar 雲端串接", container_widget)
        g_layout = QVBoxLayout(google_group)
        g_layout.setContentsMargins(24, 20, 24, 20)
        g_layout.setSpacing(18)

        g_status_row = QHBoxLayout()
        self.g_status_lbl = QLabel("狀態：🔴 尚未授權 (點擊右側按鈕開啟 Google OAuth2 授權)", google_group)
        self.g_status_lbl.setStyleSheet("font-size: 13px;")
        g_status_row.addWidget(self.g_status_lbl)
        g_status_row.addStretch(1)

        connect_btn = QPushButton("🔑 登入 Google 帳號串接", google_group)
        connect_btn.setObjectName("ConnectGoogleBtn")
        connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        connect_btn.clicked.connect(self.on_google_connect)
        g_status_row.addWidget(connect_btn)

        g_layout.addLayout(g_status_row)

        g_desc = QLabel("💡 說明：登入授權後，系統將自動同步 Google 日曆，並依「色彩標籤」(紅:大30天 / 黃:中7天 / 綠藍:小3天) 進行分類提醒。", google_group)
        g_desc.setStyleSheet("color: #a0a0ab; font-size: 12.5px; padding-left: 2px;")
        g_layout.addWidget(g_desc)

        layout.addWidget(google_group)

        layout.addStretch(1)

        scroll_area.setWidget(container_widget)

        main_vbox = QVBoxLayout(self)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.addWidget(scroll_area)

        # 實質測試 Google Calendar API 雲端連線狀態
        if self.google_service.check_connection():
            self.g_status_lbl.setText("狀態：🟢 已成功連線 Google 日曆 (雲端同步運作中)")
            self.g_status_lbl.setStyleSheet("color: #10b981; font-weight: bold;")
        else:
            self.g_status_lbl.setText("狀態：🔴 尚未授權 (點擊右側按鈕開啟 Google OAuth2 授權)")
            self.g_status_lbl.setStyleSheet("color: #f43f5e; font-weight: bold;")

    def on_water_enabled_toggled(self, checked):
        self.spin_interval.setEnabled(checked)
        self.water_enabled_signal.emit(checked)

    def on_autostart_toggled(self, checked):
        self.autostart_signal.emit(checked)

    def on_test_toast(self):
        interval = self.spin_interval.value()
        self.test_toast = ToastWindow(
            title="喝水提醒 (測試模式) 💧",
            message=f"這是提醒視窗測試！當前設定每 {interval} 分鐘提醒一次。",
            display_time_ms=3000,
            fade_time_ms=800
        )
        self.test_toast.show()

    def on_google_connect(self):
        success = self.google_service.authenticate(force_interactive=True)
        if success:
            self.g_status_lbl.setText("狀態：🟢 已成功連線 Google 日曆 (雲端同步運作中)")
            self.g_status_lbl.setStyleSheet("color: #10b981; font-weight: bold;")
            events = self.google_service.fetch_upcoming_events()
            self.google_connected_signal.emit(events)
            QMessageBox.information(
                self,
                "Google 授權成功",
                "🎉 已成功連線至您的 Google 日曆！\n已同步雲端行程，並自動依色彩標籤 (紅:大30天 / 黃:中7天 / 綠藍:小3天) 進行分類提醒。"
            )
        else:
            self.g_status_lbl.setText("狀態：🔴 尚未授權 (點擊右側按鈕開啟 Google OAuth2 授權)")
            self.g_status_lbl.setStyleSheet("color: #f43f5e; font-weight: bold;")
            QMessageBox.warning(
                self,
                "Google 授權提示",
                "尚未偵測到 credentials.json 憑證檔或網頁授權未完成。\n\n如需正式同步您的私人 Google 日曆：\n1. 請確認憑證檔命名為 credentials.json 並放置於專案的 data 資料夾內（data/credentials.json）。\n2. 點擊按鈕授權時，請於彈出的瀏覽器視窗完成允許授權。"
            )
