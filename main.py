"""
main.py
Secretary 智能桌面小助理 - 主程式入口 (Application Entry Point)
包含單一實體防護 (Single Instance Protection - QLocalServer & QLocalSocket)
確保全系統同時僅會有 1 個小助理進程在運作，重複點擊捷徑自動喚醒原視窗。
"""

import sys
import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QAction, QPixmap, QColor, QPainter
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from utils.logger import get_logger
from utils.paths import asset_path, ensure_data_dirs, migrate_legacy_files

logger = get_logger("main")
try:
    ensure_data_dirs()
    migrate_legacy_files()
except Exception as _e:
    logger.exception("初始化 data/ 目錄或搬移舊檔失敗，繼續執行")

from utils.config_manager import ConfigManager
from utils.autostart import AutoStartManager
from services.event_store import EventStore
from ui.main_window import MainWindow
from ui.toast_window import ToastWindow

SINGLE_INSTANCE_SOCKET = "SecretaryApp_SingleInstance_Lock_haolun588"

def get_app_icon():
    icon_path = asset_path("icon.png")
    if os.path.exists(icon_path):
        return QIcon(icon_path)

    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#8b5cf6"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)
    painter.setPen(QColor("#ffffff"))
    font = painter.font()
    font.setPixelSize(18)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "⚡")
    painter.end()
    return QIcon(pixmap)

class SecretaryApp:
    def __init__(self, sys_argv):
        self.app = QApplication(sys_argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.app_icon = get_app_icon()
        self.app.setWindowIcon(self.app_icon)

        self.config = ConfigManager.load_config()
        self.is_minimized = "--minimized" in sys_argv

        # 狀態控制變數
        self.water_enabled = self.config.get("water_enabled", True)
        self.autostart_enabled = self.config.get("autostart", True)
        self.interval_minutes = self.config.get("interval_minutes", 10)
        self.remaining_seconds = self.interval_minutes * 60

        # 開機自啟動登錄檔同步
        AutoStartManager.set_autostart(self.autostart_enabled)

        # 維護作用中的 Toast 物件引用清單，防記憶體垃圾回收崩潰
        self.active_toasts = []

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

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #1c1c24;
                color: #ffffff;
                border: 1px solid #2a2a36;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #8b5cf6;
                color: #ffffff;
            }
        """)

        show_action = QAction("🖥️ 顯示小助理主視窗", self.app)
        show_action.triggered.connect(self.show_main_window)
        tray_menu.addAction(show_action)

        test_toast_action = QAction("💧 測試喝水提醒彈窗", self.app)
        test_toast_action.triggered.connect(self.trigger_water_toast)
        tray_menu.addAction(test_toast_action)

        settings_action = QAction("⚙️ 系統與提醒設定", self.app)
        settings_action.triggered.connect(self.show_settings_page)
        tray_menu.addAction(settings_action)

        tray_menu.addSeparator()

        quit_action = QAction("❌ 退出程式", self.app)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_second_tick(self):
        """每秒觸發倒數計時與 UI 左下角實時文字更新"""
        if not self.water_enabled:
            self.window.sidebar.update_countdown("提醒狀態: 已關閉", is_enabled=False)
            return

        self.remaining_seconds -= 1

        if self.remaining_seconds <= 0:
            self.trigger_water_toast()
            self.remaining_seconds = self.interval_minutes * 60

        m = self.remaining_seconds // 60
        s = self.remaining_seconds % 60
        self.window.sidebar.update_countdown(f"下次提醒: {m:02d}:{s:02d} 後", is_enabled=True)

    def trigger_water_toast(self):
        """安全跳出右下角 3 秒淡出提醒彈窗"""
        try:
            toast = ToastWindow(
                title="喝水時間到了 💧",
                message="長時間坐在電腦前，記得喝杯水、伸展一下身體喔！",
                display_time_ms=3000,
                fade_time_ms=800
            )
            self.active_toasts.append(toast)
            toast.destroyed.connect(lambda obj, t=toast: self.cleanup_toast(t))
            toast.show()
        except Exception as e:
            logger.exception("觸發提醒彈窗異常")

    def on_store_failed(self, action, message):
        """行程同步／寫入失敗統一提示。fetch/check 失敗同一訊息連續只提示一次。"""
        if action in ("fetch", "check"):
            if message == self._last_fetch_error:
                return
            self._last_fetch_error = message
        try:
            toast = ToastWindow(
                title="同步失敗 ⚠️",
                message=message,
                display_time_ms=4000,
                fade_time_ms=800
            )
            self.active_toasts.append(toast)
            toast.destroyed.connect(lambda obj, t=toast: self.cleanup_toast(t))
            toast.show()
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

    def cleanup_toast(self, toast_instance):
        if toast_instance in self.active_toasts:
            self.active_toasts.remove(toast_instance)

    def on_water_enabled_toggled(self, enabled):
        self.water_enabled = enabled
        self.config["water_enabled"] = enabled
        ConfigManager.save_config(self.config)
        if enabled:
            self.remaining_seconds = self.interval_minutes * 60

    def on_autostart_toggled(self, enabled):
        self.autostart_enabled = enabled
        self.config["autostart"] = enabled
        ConfigManager.save_config(self.config)
        AutoStartManager.set_autostart(enabled)

    def on_interval_changed(self, minutes):
        self.interval_minutes = minutes
        self.remaining_seconds = minutes * 60
        self.config["interval_minutes"] = minutes
        ConfigManager.save_config(self.config)

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
