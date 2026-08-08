"""
utils/shortcut_creator.py
建立 Windows 桌面快捷方式捷徑 (Desktop Shortcut Creator)
於使用者桌面產生 「Secretary 智能桌面小助理.lnk」點擊圖示即可開啟軟體。
"""

import os
import sys
import subprocess
from datetime import datetime

class ShortcutCreator:
    @staticmethod
    def create_desktop_shortcut():
        """使用 PowerShell 於使用者桌面建立 Secretary 捷徑圖示"""
        if sys.platform != "win32":
            print(f"[{datetime.now().isoformat()}] [ShortcutCreator] 非 Windows 系統，無法建立桌面捷徑")
            return False

        try:
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop_dir):
                # 嘗試中文桌面路徑
                desktop_dir = os.path.join(os.path.expanduser("~"), "桌面")
                if not os.path.exists(desktop_dir):
                    os.makedirs(desktop_dir, exist_ok=True)

            shortcut_path = os.path.join(desktop_dir, "Secretary 智能桌面小助理.lnk")
            
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            main_script = os.path.join(project_dir, "main.py")
            ico_path = os.path.join(project_dir, "assets", "icon.ico")
            png_path = os.path.join(project_dir, "assets", "icon.png")
            
            icon_file = ico_path if os.path.exists(ico_path) else png_path

            python_dir = os.path.dirname(sys.executable)
            pythonw = os.path.join(python_dir, "pythonw.exe")
            target_path = pythonw if os.path.exists(pythonw) else sys.executable
            arguments = f'"{main_script}"'

            # 透過 PowerShell 創建 WScript.Shell 捷徑
            ps_script = f"""
            $WshShell = New-Object -ComObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
            $Shortcut.TargetPath = '{target_path}'
            $Shortcut.Arguments = '{arguments}'
            $Shortcut.WorkingDirectory = '{project_dir}'
            $Shortcut.IconLocation = '{icon_file}'
            $Shortcut.Description = 'Secretary 智能桌面小助理'
            $Shortcut.Save()
            """

            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"[{datetime.now().isoformat()}] [ShortcutCreator] 成功建立桌面捷徑: {shortcut_path}")
                return True
            else:
                print(f"[{datetime.now().isoformat()}] [ShortcutCreator] PowerShell 建立捷徑失敗: {result.stderr}")
                return False
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [ShortcutCreator] 建立捷徑過程異常: {e}")
            return False

if __name__ == "__main__":
    ShortcutCreator.create_desktop_shortcut()
