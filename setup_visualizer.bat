@echo off
setlocal

:: Portrait Visualizer one-click setup

:: 1. Install Python silently
curl -L -o python-installer.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

:: 2. Install AutoHotkey v2 silently
curl -L -o ahk-setup.exe https://www.autohotkey.com/download/ahk-v2.exe
ahk-setup.exe /silent /installto "%ProgramFiles%\AutoHotkey"

:: 3. Copy program files
set "APPDIR=%ProgramFiles%\PortraitVisualizer"
xcopy "%~dp0" "%APPDIR%" /E /I /Y >nul

:: 4. Pip packages
py -m pip install --upgrade pip
py -m pip install -r "%APPDIR%\requirements.txt"

:: 5. Ensure assets
xcopy "%~dp0Composites" "%APPDIR%\Composites" /E /I /Y >nul
xcopy "%~dp0Frames" "%APPDIR%\Frames" /E /I /Y >nul

:: 6. Write config.json
> "%APPDIR%\config.json" echo { "photo_root":"C:/Users/%USERNAME%/Re MEMBER Dropbox/PHOTOGRAPHY PROOFING/PHOTOGRAPHER UPLOADS (1)" }

:: 7. Desktop shortcut
powershell -ExecutionPolicy Bypass -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop') + '\\PortraitVisualizer.lnk');" ^
  "$s.TargetPath='%APPDIR%\\Visualizer.ahk';$s.Save()"

echo Done!  Double-click the PortraitVisualizer shortcut to begin.
pause
