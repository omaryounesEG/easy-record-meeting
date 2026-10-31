@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $sc = $ws.CreateShortcut(\"$d\OMAR_REC.lnk\"); $sc.TargetPath = \"%~dp0OMAR_REC.exe\"; $sc.WorkingDirectory = \"%~dp0\"; $sc.IconLocation = \"%~dp0mic_icon.ico,0\"; $sc.Save()"
echo ========================================================
echo   تم انشاء اختصار البرنامج على سطح المكتب بنجاح!
echo ========================================================
pause
