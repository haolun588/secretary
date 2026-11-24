"""
utils/autostart.py
Windows 開機自動啟動登錄檔控制模組 (Auto-Start Registry Helper)
支援帶入 --minimized 參數實現開機靜默啟動。
"""

import sys
import os
from datetime import datetime
from utils.paths import PROJECT_DIR

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
        """開啟或關閉 Windows 開機自動啟動"""
        if sys.platform != "win32":
            print(f"[{datetime.now().isoformat()}] [AutoStartManager] 非 Windows 系統，略過登錄檔寫入")
            return False

        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_ALL_ACCESS)
            
            if enable:
                cmd = AutoStartManager.get_executable_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                print(f"[{datetime.now().isoformat()}] [AutoStartManager] 已設定開機自啟動: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    print(f"[{datetime.now().isoformat()}] [AutoStartManager] 已取消開機自啟動")
                except FileNotFoundError:
                    pass
            
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [AutoStartManager] 登錄檔操作失敗: {e}")
            return False

    @staticmethod
    def is_autostart_enabled():
        """檢查當前 Windows 登錄檔中開機自啟動狀態"""
        if sys.platform != "win32":
            return False

        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ)
            try:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
                winreg.CloseKey(key)
                return bool(val)
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [AutoStartManager] 查詢開機自啟啟狀態失敗: {e}")
            return False
