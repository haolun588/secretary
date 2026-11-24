"""
utils/autostart.py
Windows 開機自動啟動登錄檔控制模組 (Auto-Start Registry Helper)
支援帶入 --minimized 參數實現開機靜默啟動。
"""

import sys
import os
from utils.logger import get_logger
from utils.paths import PROJECT_DIR

logger = get_logger(__name__)

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "SecretaryAssistant"

class AutoStartManager:
    @staticmethod
    def get_executable_command():
        """取得開機啟動執行命令 (帶入 --minimized 靜默啟動參數)"""
        main_script = os.path.join(PROJECT_DIR, "main.py")
        
        # 若為已編譯 exe 或通用 Python 環境
        if getattr(sys, 'frozen', False):
            executable = sys.executable
            return f'"{executable}" --minimized'
        else:
            # 優先使用 pythonw.exe 避開命令列黑框，若不存在則退回 sys.executable
            python_dir = os.path.dirname(sys.executable)
            pythonw = os.path.join(python_dir, "pythonw.exe")
            exec_bin = pythonw if os.path.exists(pythonw) else sys.executable
            return f'"{exec_bin}" "{main_script}" --minimized'

    @staticmethod
    def set_autostart(enable=True):
        """開啟或關閉 Windows 開機自動啟動；成功回傳 True，失敗回傳 False"""
        if sys.platform != "win32":
            logger.warning("非 Windows 系統，略過登錄檔寫入")
            return False

        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE)
            try:
                if enable:
                    cmd = AutoStartManager.get_executable_command()
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                    logger.info("已設定開機自啟動")
                    logger.debug(f"開機自啟命令: {cmd}")
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                        logger.info("已取消開機自啟動")
                    except FileNotFoundError:
                        pass
            finally:
                winreg.CloseKey(key)
            return True
        except Exception:
            logger.exception("登錄檔操作失敗")
            return False

    @staticmethod
    def get_registered_command():
        """唯讀取得 Run 機碼中已登錄的命令；不存在、非 Windows 或例外時回傳 None"""
        if sys.platform != "win32":
            return None

        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ)
            try:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
                return val
            except FileNotFoundError:
                return None
            finally:
                winreg.CloseKey(key)
        except Exception:
            logger.exception("查詢開機自啟啟狀態失敗")
            return None

    @staticmethod
    def is_autostart_enabled():
        """檢查當前 Windows 登錄檔中開機自啟動狀態"""
        return bool(AutoStartManager.get_registered_command())

    @staticmethod
    def sync(desired):
        """依期望狀態與登錄檔現況同步；僅在需要時才寫入。回傳是否成功"""
        action = plan_sync(
            desired,
            AutoStartManager.get_registered_command(),
            AutoStartManager.get_executable_command(),
        )
        if action is None:
            return True
        return AutoStartManager.set_autostart(action == "set")


def plan_sync(desired, current_cmd, expected_cmd):
    """純函式：決定需要的登錄檔動作，回傳 "set" / "delete" / None"""
    if desired:
        return "set" if current_cmd != expected_cmd else None
    return "delete" if current_cmd is not None else None
