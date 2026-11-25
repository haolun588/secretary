import os
import sys
import subprocess

def get_real_desktop():
    """取得 PowerShell 回報的官方真實桌面路徑 (包含 OneDrive 桌面)；失敗時回傳空字串。"""
    ps_cmd = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;"
        "[System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)"
    )
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, encoding="utf-8", errors="replace",
        )
        path = (res.stdout or "").strip()
        if path and os.path.exists(path):
            return path
    except Exception as e:
        print("取得桌面路徑失敗:", e)
    return ""


def create_all_shortcuts():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_script = os.path.join(project_dir, "main.py")
    icon_file = os.path.join(project_dir, "assets", "icon.ico")
    
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    target_exec = pythonw if os.path.exists(pythonw) else sys.executable

    real_desktop = get_real_desktop()

    candidate_desktops = [
        real_desktop,
        os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Desktop"),
        os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "桌面"),
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        os.path.join(os.environ.get("USERPROFILE", ""), "桌面")
    ]

    # 去重
    valid_desktops = []
    for d in candidate_desktops:
        if d and os.path.exists(d) and d not in valid_desktops:
            valid_desktops.append(d)

    created_paths = []
    for d in valid_desktops:
        lnk_path = os.path.join(d, "Secretary 智能桌面小助理.lnk")
        ps_create = f"""
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut('{lnk_path}')
        $Shortcut.TargetPath = '{target_exec}'
        $Shortcut.Arguments = '"{main_script}"'
        $Shortcut.WorkingDirectory = '{project_dir}'
        $Shortcut.IconLocation = '{icon_file}'
        $Shortcut.Description = 'Secretary 智能桌面小助理'
        $Shortcut.Save()
        """
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_create],
            capture_output=True, encoding="utf-8", errors="replace",
        )
        if r.returncode == 0:
            created_paths.append(lnk_path)
        else:
            print(f"建立捷徑失敗 ({lnk_path}):", (r.stderr or "").strip())

    # 另外在專案根目錄下也建立一個「啟動 Secretary 小助理.bat」批次檔雙擊即可執行
    bat_path = os.path.join(project_dir, "啟動 Secretary 小助理.bat")
    with open(bat_path, "w", encoding="ansi") as f:
        f.write(f'@echo off\nstart "" "{target_exec}" "{main_script}"\n')

    print("SUCCESS_DESKTOPS:", created_paths)
    print("BAT_PATH:", bat_path)

if __name__ == "__main__":
    create_all_shortcuts()
