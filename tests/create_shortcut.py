import os
import subprocess

def create_shortcut():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "EchoLyrics.lnk")
    main_py = r"e:\projects\jlyrics\main.py"
    work_dir = r"e:\projects\jlyrics"
    
    ps_cmd = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = 'pythonw.exe'
    $Shortcut.Arguments = '"{main_py}"'
    $Shortcut.WorkingDirectory = '{work_dir}'
    $Shortcut.Description = 'EchoLyrics Subtitle App'
    $Shortcut.Save()
    """
    
    subprocess.run(["powershell", "-Command", ps_cmd], check=True)
    print(f"Shortcut successfully created at: {shortcut_path}")

if __name__ == "__main__":
    create_shortcut()
