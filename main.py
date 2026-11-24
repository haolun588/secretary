"""
main.py
Secretary 智能桌面小助理 - 主程式入口 (Application Entry Point)
包含單一實體防護 (Single Instance Protection - QLocalServer & QLocalSocket)
確保全系統同時僅會有 1 個小助理進程在運作，重複點擊捷徑自動喚醒原視窗。
"""

import sys
import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from utils.logger import get_logger
from utils.paths import asset_path, ensure_data_dirs, migrate_legacy_files

logger = get_logger("main")
try:
    ensure_data_dirs()
    migrate_legacy_files()
except Exception as _e:
    logger.exception("初始化 data/ 目錄或搬移舊檔失敗，繼續執行")

from utils.config_manager import ConfigManager, save_config_or_warn
from utils.autostart import AutoStartManager
from services.event_store import EventStore
from ui import icons, theme
from ui.main_window import MainWindow
from ui.styles import apply_app_style
from ui.toast_window import ToastStack, ToastWindow
from ui.tray_menu import build_tray_menu
from utils.water_timer import WaterCountdown

SINGLE_INSTANCE_SOCKET = "SecretaryApp_SingleInstance_Lock_haolun588"

WATER_SNOOZE_MINUTES = 10

def get_app_icon():
    icon_path = asset_path("icon.png")
    if os.path.exists(icon_path):
        return QIcon(icon_path)

    return QIcon(icons.pixmap("logo", theme.ACCENT, theme.APP_ICON))

class SecretaryApp:
    def __init__(self, sys_argv):
        self.app = QApplication(sys_argv)
        self.app.setQuitOnLastWindowClosed(False)
        apply_app_style(self.app)

        self.app_icon = get_app_icon()
        self.app.setWindowIcon(self.app_icon)

        self.config = ConfigManager.load_config()
        self.is_minimized = "--minimized" in sys_argv

        # 狀態控制變數
        self.water_enabled = self.config.get("water_enabled", True)
        self.autostart_enabled = self.config.get("autostart", False)
        self.minimize_to_tray = self.config.get("minimize_to_tray", True)
        self.interval_minutes = self.config.get("interval_minutes", 10)
        self.water = WaterCountdown(self.interval_minutes, enabled=self.water_enabled)

        # 維護作用中的 Toast 物件引用清單，防記憶體垃圾回收崩潰
        self.toast_stack = ToastStack()

        # 開機自啟動登錄檔同步（僅在與設定不一致時才寫入）
        if not AutoStartManager.sync(self.autostart_enabled):
            self._notify_danger("開機自動啟動設定失敗", "無法更新 Windows 開機啟動設定，詳情請見日誌。")

        # 行程資料唯一來源；以 app 為 parent，並注入各 view
        self.event_store = EventStore(parent=self.app)
        self._last_fetch_error = None
        self.event_store.operation_failed.connect(self.on_store_failed)
        self.event_store.operation_succeeded.connect(self.on_store_succeeded)
        self.event_store.sync_state_changed.connect(self.on_store_sync_state)

        self.window = MainWindow(config_manager=ConfigManager, event_store=self.event_store)

        # 設定頁面初始化狀態
        self.window.settings_view.chk_water_enabled.setChecked(self.water_enabled)
        self.window.settings_view.chk_autostart.setChecked(self.autostart_enabled)
        self.window.settings_view.chk_minimize_to_tray.setChecked(self.minimize_to_tray)
        self.window.settings_view.spin_interval.setValue(self.interval_minutes)

        # 實時 1 秒背景倒數計時器
        self.second_timer = QTimer()
        self.second_timer.timeout.connect(self.on_second_tick)
        self.second_timer.start(1000)

        self.init_system_tray()
        self.init_single_instance_server()

        # 連接設定訊號
        self.window.settings_view.water_enabled_signal.connect(self.on_water_enabled_toggled)
        self.window.settings_view.autostart_signal.connect(self.on_autostart_toggled)
        self.window.settings_view.minimize_to_tray_signal.connect(self.on_minimize_to_tray_toggled)
        self.window.settings_view.test_toast_requested.connect(self.trigger_water_toast)
        self.window.settings_view.spin_interval.valueChanged.connect(self.on_interval_changed)

    def init_single_instance_server(self):
        """啟動 QLocalServer 監聽重複啟動的喚醒訊號"""
        self.local_server = QLocalServer(self.app)
        QLocalServer.removeServer(SINGLE_INSTANCE_SOCKET)
        if self.local_server.listen(SINGLE_INSTANCE_SOCKET):
            self.local_server.newConnection.connect(self.on_new_instance_connection)

    def on_new_instance_connection(self):
        client_socket = self.local_server.nextPendingConnection()
        if client_socket:
            client_socket.readyRead.connect(lambda: self.handle_instance_message(client_socket))

    def handle_instance_message(self, client_socket):
        try:
            msg = client_socket.readAll().data().decode("utf-8")
            if "SHOW" in msg:
                self.show_main_window()
        except Exception as e:
            logger.exception("處理喚醒訊號異常")
        finally:
            client_socket.disconnectFromServer()

    def init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self.app_icon, self.app)
        self.tray_icon.setToolTip("Secretary 智能桌面小助理 (背景運作中)")

        tray_menu = build_tray_menu({
            "show": self.show_main_window,
            "test_water": self.trigger_water_toast,
            "settings": self.show_settings_page,
            "quit": self.quit_app,
        })
        self.tray_menu = tray_menu  # 持有引用，避免被回收

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_second_tick(self):
        """每秒觸發倒數計時與左側導覽列倒數更新"""
        if not self.water.enabled:
            self.window.sidebar.set_countdown(None)
            return

        if self.water.tick():
            self.trigger_water_toast()

        self.window.sidebar.set_countdown(self.water.remaining)

    def show_toast(self, **kwargs):
        """建立並顯示 toast；多個同時存在時由 ToastStack 往上堆疊。"""
        toast = ToastWindow(**kwargs)
        self.toast_stack.add(toast)
        toast.show()
        return toast

    def trigger_water_toast(self):
        """安全跳出右下角喝水提醒（可延後或標記已喝）"""
        try:
            self.show_toast(
                title="該喝水了",
                message="久坐一段時間了，起來喝杯水、活動一下吧。",
                display_time_ms=3000,
                fade_time_ms=800,
                kind="water",
                actions=[
                    (f"延後 {WATER_SNOOZE_MINUTES} 分鐘", lambda: self.water.snooze(WATER_SNOOZE_MINUTES)),
                    ("已喝", self.water.reset),
                ],
            )
        except Exception as e:
            logger.exception("觸發提醒彈窗異常")

    def on_store_failed(self, action, message):
        """行程同步／寫入失敗統一提示。fetch/check 失敗同一訊息連續只提示一次。"""
        if action in ("fetch", "check"):
            if message == self._last_fetch_error:
                return
            self._last_fetch_error = message
        try:
            self.show_toast(
                title="同步失敗",
                message=message,
                display_time_ms=4000,
                fade_time_ms=800,
                kind="danger",
            )
        except Exception:
            logger.exception("顯示同步失敗提示異常")

        if action in ("add", "update", "delete", "auth") and self.window.isVisible():
            QMessageBox.warning(self.window, "Google 日曆操作失敗", message)

    def on_store_succeeded(self, action):
        if action in ("fetch", "check"):
            self._last_fetch_error = None

    def on_store_sync_state(self, state, message):
        if state == "ok":
            self._last_fetch_error = None

    def _notify_danger(self, title, message):
        try:
            self.show_toast(title=title, message=message, display_time_ms=4000,
                            fade_time_ms=800, kind="danger")
        except Exception:
            logger.exception("顯示設定儲存失敗提示異常")

    def save_config(self):
        """寫入設定檔；失敗時以 danger toast 提示使用者（不可只記 log）。"""
        return save_config_or_warn(self.config, ConfigManager.save_config, self._notify_danger)

    def on_water_enabled_toggled(self, enabled):
        self.water_enabled = enabled
        self.water.set_enabled(enabled)
        self.config["water_enabled"] = enabled
        self.save_config()

    def on_autostart_toggled(self, enabled):
        if not AutoStartManager.set_autostart(enabled):
            self._notify_danger("開機自動啟動設定失敗", "無法更新 Windows 開機啟動設定，詳情請見日誌。")
            chk = self.window.settings_view.chk_autostart
            chk.blockSignals(True)
            chk.setChecked(not enabled)
            chk.blockSignals(False)
            return
        self.autostart_enabled = enabled
        self.config["autostart"] = enabled
        self.save_config()

    def on_minimize_to_tray_toggled(self, enabled):
        self.minimize_to_tray = enabled
        self.config["minimize_to_tray"] = enabled
        self.save_config()

    def on_interval_changed(self, minutes):
        self.interval_minutes = minutes
        self.water.set_interval(minutes)
        self.config["interval_minutes"] = minutes
        self.save_config()

    def show_main_window(self):
        self.window.show()
        self.window.setWindowState(self.window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.window.activateWindow()
        self.window.raise_()

    def show_settings_page(self):
        self.window.sidebar.btn_settings.click()
        self.show_main_window()

    def on_tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.window.isVisible() and not self.window.isMinimized():
                self.window.hide()
            else:
                self.show_main_window()

    def quit_app(self):
        logger.info("正在退出 Secretary 小助理...")
        self.second_timer.stop()
        self.event_store.shutdown()
        QLocalServer.removeServer(SINGLE_INSTANCE_SOCKET)
        self.tray_icon.hide()
        self.app.quit()

    def run(self):
        if not self.is_minimized:
            self.show_main_window()
        else:
            logger.info("開機靜默啟動模式：隱藏於背景系統托盤")
        
        # 背景靜默載入 token，成功則拉取行程
        self.event_store.start()

        return self.app.exec()

def is_already_running():
    """檢查是否有已存在的 Secretary 進程，若有則喚醒並回傳 True"""
    socket = QLocalSocket()
    socket.connectToServer(SINGLE_INSTANCE_SOCKET)
    if socket.waitForConnected(500):
        socket.write(b"SHOW")
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        logger.info("小助理已在背景運作中，已喚醒現有視窗。")
        return True
    return False

if __name__ == "__main__":
    if is_already_running():
        sys.exit(0)

    app_runner = SecretaryApp(sys.argv)
    sys.exit(app_runner.run())
