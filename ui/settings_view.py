"""
ui/settings_view.py
設定頁（段落式清單）：一般、Google 日曆（喝水提醒已獨立為 ui/water_view.py）。
所有設定皆即時生效並由 main.py 即時儲存，沒有「儲存」按鈕。樣式由全域 QSS（_SETTINGS）負責。
"""

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from ui import icons, theme
from ui.confirm_dialog import ConfirmDialog
from ui.styles import repolish
from utils.logger import get_logger

logger = get_logger(__name__)


class SettingsRow(QFrame):
    """設定列：左側標題 + 說明，右側控制項。last=True 時不畫下分隔線。"""

    def __init__(self, title, desc=None, control=None, last=False, desc_widget=None, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsRow")
        self.setProperty("last", "true" if last else "false")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.SPACE_4, theme.SPACE_3, theme.SPACE_4, theme.SPACE_3)
        layout.setSpacing(theme.SPACE_4)

        text_col = QVBoxLayout()
        text_col.setSpacing(theme.SPACE_1)
        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("SettingsRowTitle")
        text_col.addWidget(self.title_label)

        self.desc_label = None
        if desc_widget is not None:
            text_col.addWidget(desc_widget)
        elif desc:
            self.desc_label = QLabel(desc, self)
            self.desc_label.setObjectName("SettingsRowDesc")
            self.desc_label.setWordWrap(True)
            text_col.addWidget(self.desc_label)
        layout.addLayout(text_col, 1)

        if control is not None:
            layout.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)


def make_switch(parent):
    chk = QCheckBox(parent)
    chk.setProperty("variant", "switch")
    chk.setCursor(Qt.CursorShape.PointingHandCursor)
    return chk


class SettingsView(QWidget):
    autostart_signal = pyqtSignal(bool)
    minimize_to_tray_signal = pyqtSignal(bool)

    def __init__(self, event_store, parent=None):
        super().__init__(parent)
        self.event_store = event_store
        self._auth_failed = False
        self.init_ui()

    # ------------------------------------------------------------ 版面

    def _add_section(self, layout, title, rows):
        """加入「段落標題 + 圓角群組（多列）」；回傳群組 QFrame。"""
        section = QWidget(self._container)
        s_layout = QVBoxLayout(section)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(theme.SPACE_2)

        label = QLabel(title, section)
        label.setProperty("role", "section")
        s_layout.addWidget(label)

        group = QFrame(section)
        group.setObjectName("SettingsGroup")
        g_layout = QVBoxLayout(group)
        g_layout.setContentsMargins(0, 0, 0, 0)
        g_layout.setSpacing(0)
        for i, row in enumerate(rows):
            row.setProperty("last", "true" if i == len(rows) - 1 else "false")
            g_layout.addWidget(row)
        s_layout.addWidget(group)

        layout.addWidget(section)
        return group, section

    def init_ui(self):
        self.setObjectName("SettingsPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        page.setObjectName("SettingsScrollContent")
        page_layout = QHBoxLayout(page)
        page_layout.setContentsMargins(theme.SPACE_6, theme.SPACE_5, theme.SPACE_6, theme.SPACE_5)
        page_layout.addStretch(1)

        self._container = QWidget(page)
        self._container.setMaximumWidth(theme.SETTINGS_MAX_W)
        self._container.setMinimumWidth(0)
        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_3)

        title = QLabel("設定", self._container)
        title.setProperty("role", "title")
        layout.addWidget(title)

        # ---- 一般 ----
        self.chk_autostart = make_switch(self._container)
        self.chk_autostart.setChecked(False)
        self.chk_autostart.toggled.connect(self.on_autostart_toggled)

        self.chk_minimize_to_tray = make_switch(self._container)
        self.chk_minimize_to_tray.setChecked(True)
        self.chk_minimize_to_tray.toggled.connect(self.on_minimize_to_tray_toggled)

        self._add_section(layout, "一般", [
            SettingsRow("開機自動啟動", "登入 Windows 後在背景自動啟動", self.chk_autostart),
            SettingsRow("關閉視窗時縮到系統匣", "按下視窗關閉鈕時保留在系統匣繼續執行",
                        self.chk_minimize_to_tray),
        ])

        # ---- Google 日曆 ----
        self.g_status_lbl = QLabel("檢查連線中…", self._container)
        self.g_status_lbl.setObjectName("AccountStatus")
        self.g_status_lbl.setProperty("state", "neutral")

        self.connect_btn = QPushButton("登入", self._container)
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setIconSize(QSize(theme.ICON_SM, theme.ICON_SM))
        self.connect_btn.clicked.connect(self.on_google_button_clicked)

        self._add_section(layout, "Google 日曆", [
            SettingsRow("Google 帳號", control=self.connect_btn, desc_widget=self.g_status_lbl),
        ])

        note = QLabel("登入後會同步 Google 日曆的行程；日曆上的顏色標籤會對應為大、中、小三種等級。",
                      self._container)
        note.setProperty("role", "muted")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch(1)
        page_layout.addWidget(self._container, 100)
        page_layout.addStretch(1)

        self._scroll_area.setWidget(page)

        main_vbox = QVBoxLayout(self)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.addWidget(self._scroll_area)

        self._set_google_button(authenticated=False)

        self.event_store.auth_state_changed.connect(self.on_auth_state_changed)
        self.event_store.sync_state_changed.connect(self.on_sync_state_changed)
        self.event_store.operation_failed.connect(self.on_operation_failed)
        self.event_store.operation_succeeded.connect(self.on_operation_succeeded)
        # 狀態由 main.py 呼叫 event_store.start() 後的 auth_state_changed 驅動

    # ------------------------------------------------------------ Google 狀態

    def _set_status(self, text, state="neutral"):
        self.g_status_lbl.setText(text)
        self.g_status_lbl.setProperty("state", state)
        repolish(self.g_status_lbl)

    def _set_google_button(self, authenticated, busy=False):
        """依狀態切換按鈕：未連線 -> 登入（primary）；已連線 -> 登出（secondary）；授權中停用。"""
        if authenticated:
            self.connect_btn.setText("登出")
            self.connect_btn.setProperty("variant", "secondary")
            self.connect_btn.setIcon(icons.icon("log-out", theme.TEXT_PRIMARY, theme.ICON_SM))
        else:
            self.connect_btn.setText("登入")
            self.connect_btn.setProperty("variant", "primary")
            self.connect_btn.setIcon(icons.icon("log-in", theme.TEXT_ON_ACCENT, theme.ICON_SM))
        self.connect_btn.setEnabled(not busy)
        repolish(self.connect_btn)

    def _show_unauthorized(self):
        self._set_status("未連線", "neutral")
        self._set_google_button(authenticated=False)

    def _show_connected(self):
        self._set_status("已連線，雲端同步運作中", "ok")
        self._set_google_button(authenticated=True)

    def _show_authorizing(self):
        self._set_status("等待瀏覽器授權（最多 3 分鐘）…", "neutral")
        self._set_google_button(authenticated=False, busy=True)

    def on_auth_state_changed(self, authenticated):
        if self.event_store.is_authorizing:
            return  # 授權進行中維持「等待瀏覽器授權」
        if authenticated:
            self._auth_failed = False
            self._show_connected()
        elif self._auth_failed:
            self._set_google_button(authenticated=False)  # 保留「授權失敗」文字
        else:
            self._show_unauthorized()

    def on_operation_succeeded(self, action):
        if action == "auth":
            QMessageBox.information(
                self,
                "Google 授權成功",
                "已成功連線至你的 Google 日曆。\n行程將自動同步，並依色彩標籤分類為大、中、小等級。"
            )

    def on_sync_state_changed(self, state, message):
        if state == "authorizing":
            self._show_authorizing()
        elif self.event_store.is_authorizing:
            return  # 授權進行中不覆寫「等待瀏覽器授權」狀態文字
        elif state == "offline":
            self._set_status("無法連線（離線或逾時）", "error")
        elif state == "ok" and self.event_store.is_authenticated:
            self._show_connected()

    def on_operation_failed(self, action, message):
        """授權失敗的提示由 main.py 統一處理；這裡只恢復按鈕與狀態文字。"""
        if action == "auth":
            if self.event_store.is_authenticated:
                self._auth_failed = False
                self._show_connected()
            else:
                self._auth_failed = True
                self._show_unauthorized()
                self._set_status("授權失敗，請重新登入", "error")

    def on_google_button_clicked(self):
        if self.event_store.is_authenticated:
            self.on_google_logout()
        else:
            self.on_google_connect()

    def on_google_connect(self):
        self._auth_failed = False
        self.event_store.authorize()

    def _confirm_logout(self):
        dlg = ConfirmDialog(
            window_title="登出 Google 帳號",
            heading="登出 Google 帳號？",
            message="登出後會停止同步 Google 日曆。",
            detail="本機的授權資料會被刪除、畫面上的行程會清空，需要重新登入才能再次同步。",
            confirm_text="登出",
            parent=self,
        )
        return dlg.exec() == ConfirmDialog.DialogCode.Accepted

    def on_google_logout(self):
        if self._confirm_logout():
            self.event_store.logout()

    # ------------------------------------------------------------ 其他設定

    def on_autostart_toggled(self, checked):
        self.autostart_signal.emit(checked)

    def on_minimize_to_tray_toggled(self, checked):
        self.minimize_to_tray_signal.emit(checked)
