"""
ui/water_view.py
喝水提醒頁：上方大字顯示距離下次提醒的倒數，下方為啟用開關、提醒間隔、測試按鈕。
設定即時生效並由 main.py 即時儲存；樣式由全域 QSS（_SETTINGS 區段的 WaterPage / WaterCountdown）負責。
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

from ui import theme
from ui.nav_sidebar import format_countdown
from ui.settings_view import SettingsRow, make_switch
from ui.styles import repolish

WATER_INTERVAL_RANGE = (1, 180)

_OFF_TEXT = "已停用"
_ON_CAPTION = "距離下次喝水提醒"
_OFF_CAPTION = "喝水提醒已關閉"


class WaterView(QWidget):
    water_enabled_signal = pyqtSignal(bool)
    test_toast_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._countdown_off = None
        self.init_ui()
        self.set_countdown(None)

    def init_ui(self):
        self.setObjectName("WaterPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(theme.SPACE_6, theme.SPACE_5, theme.SPACE_6, theme.SPACE_5)
        outer.addStretch(1)

        container = QWidget(self)
        container.setMaximumWidth(theme.SETTINGS_MAX_W)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_3)

        title = QLabel("喝水提醒", container)
        title.setProperty("role", "title")
        layout.addWidget(title)

        # ---- 倒數 ----
        layout.addSpacing(theme.SPACE_3)
        self.countdown_label = QLabel(container)
        self.countdown_label.setObjectName("WaterCountdown")
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.countdown_label)

        self.caption_label = QLabel(container)
        self.caption_label.setObjectName("WaterCountdownCaption")
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.caption_label)
        layout.addSpacing(theme.SPACE_3)

        # ---- 控制項（行為與原設定頁相同）----
        self.chk_water_enabled = make_switch(container)
        self.chk_water_enabled.setChecked(True)
        self.chk_water_enabled.toggled.connect(self.on_water_enabled_toggled)

        self.spin_interval = QSpinBox(container)
        self.spin_interval.setRange(*WATER_INTERVAL_RANGE)
        self.spin_interval.setValue(10)
        self.spin_interval.setSuffix(" 分鐘")
        self.spin_interval.setMinimumWidth(theme.SETTINGS_CONTROL_W)

        self.test_btn = QPushButton("測試", container)
        self.test_btn.setProperty("variant", "secondary")
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.clicked.connect(self.on_test_toast)

        rows = [
            SettingsRow("啟用喝水提醒", "定時在螢幕右下角跳出提醒", self.chk_water_enabled),
            SettingsRow("提醒間隔", "每隔多久提醒一次", self.spin_interval),
            SettingsRow("測試提醒", "立即跳出一則提醒，確認外觀與音效", self.test_btn),
        ]
        group = QFrame(container)
        group.setObjectName("SettingsGroup")
        g_layout = QVBoxLayout(group)
        g_layout.setContentsMargins(0, 0, 0, 0)
        g_layout.setSpacing(0)
        for i, row in enumerate(rows):
            row.setProperty("last", "true" if i == len(rows) - 1 else "false")
            g_layout.addWidget(row)
        layout.addWidget(group)
        layout.addStretch(1)

        outer.addWidget(container, 100)
        outer.addStretch(1)

    def set_countdown(self, seconds):
        """顯示倒數；seconds 為 None 表示喝水提醒已停用。只有開/關狀態改變時才 repolish。"""
        off = seconds is None
        self.countdown_label.setText(_OFF_TEXT if off else format_countdown(seconds))
        if off == self._countdown_off:
            return
        self._countdown_off = off
        self.countdown_label.setProperty("off", "true" if off else "false")
        self.caption_label.setText(_OFF_CAPTION if off else _ON_CAPTION)
        repolish(self.countdown_label)

    def on_water_enabled_toggled(self, checked):
        self.spin_interval.setEnabled(checked)
        self.water_enabled_signal.emit(checked)

    def on_test_toast(self):
        """測試提醒由 main.py 負責顯示（與實際喝水提醒相同），這裡只發出請求。"""
        self.test_toast_requested.emit()
