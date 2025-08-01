@echo off
setlocal

REM ---- Self elevate if needed ----
>nul 2>&1 "%SystemRoot%\system32\cacls.exe" "%SystemRoot%\system32\config\system"
if %errorlevel% neq 0 (
  echo Requesting administrative privileges...
  powershell Start-Process '%~f0' -Verb runAs
  exit /b
)

REM ---- Variables ----
set "APPDIR=%ProgramFiles%\PortraitVisualizer"
set "PY=%ProgramFiles%\Python311\python.exe"

REM 1. Install Python silently if missing
if not exist "%PY%" (
  curl -L -o py.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
  py.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
)

REM 2. Install AutoHotkey v2 for all users
if not exist "%ProgramFiles%\AutoHotkey\AutoHotkey64.exe" (
  curl -L -o ahk.exe https://www.autohotkey.com/download/ahk-v2.exe
  ahk.exe /silent /Elevate /installto "%ProgramFiles%\AutoHotkey"
)

REM 3. Copy program files & assets
mkdir "%APPDIR%" 2>nul
xcopy "%~dp0" "%APPDIR%" /E /I /Y >nul

REM 4. Install Python dependencies
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r "%APPDIR%\requirements.txt"

REM 5. Ensure assets exist
xcopy "%~dp0Composites" "%APPDIR%\Composites" /E /I /Y >nul
xcopy "%~dp0Frames" "%APPDIR%\Frames" /E /I /Y >nul
if not exist "%APPDIR%\config.json" copy "%~dp0config.json" "%APPDIR%" >nul

REM 6. Desktop shortcut
powershell -ExecutionPolicy Bypass -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\PortraitVisualizer.lnk');" ^
  "$s.TargetPath='%APPDIR%\\Visualizer (3).ahk';$s.Save()"

echo Installation complete. Launch via desktop shortcut.
pause
