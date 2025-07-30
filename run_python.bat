@echo off
setlocal enabledelayedexpansion

:: Robust Python launcher for AHK exe
:: This script finds Python and runs the visualizer script with proper arguments

:: Get arguments passed from AHK
set "SCRIPT_PATH=%~1"
set "TSV_PATH=%~2"
set "DROPBOX_ROOT=%~3"
set "DEBUG_FLAG=%~4"

:: Detect Python installation
call :detect_python
if not defined PYTHON_CMD (
    echo ERROR: Python not found. Please run setup_and_run.bat first.
    echo.
    echo Checked locations:
    echo - PATH commands (python, python3)
    echo - %USERPROFILE%\AppData\Local\Programs\Python\
    echo - C:\Python311\, C:\Python310\
    echo - Program Files locations
    echo.
    pause
    exit /b 1
)

:: Run the Python script
echo ================================================================
echo PYTHON VISUALIZER LAUNCHER
echo ================================================================
echo Python: %PYTHON_CMD%
echo Script: %SCRIPT_PATH%
echo TSV: %TSV_PATH%
echo Dropbox: %DROPBOX_ROOT%
echo Working Dir: %CD%
echo.
echo Starting Python script...
echo.

:: Test Python first
echo Testing Python installation...
"%PYTHON_CMD%" --version
if !errorlevel! neq 0 (
    echo ERROR: Python test failed!
    pause
    exit /b 1
)

echo.
echo Python test passed. Running visualizer script...
echo.

:: Run with verbose output and capture both stdout and stderr
echo Running Python command:
if defined DEBUG_FLAG (
    echo "%PYTHON_CMD%" "%SCRIPT_PATH%" "%TSV_PATH%" "%DROPBOX_ROOT%" %DEBUG_FLAG%
) else (
    echo "%PYTHON_CMD%" "%SCRIPT_PATH%" "%TSV_PATH%" "%DROPBOX_ROOT%"
)
echo.

if defined DEBUG_FLAG (
    "%PYTHON_CMD%" "%SCRIPT_PATH%" "%TSV_PATH%" "%DROPBOX_ROOT%" %DEBUG_FLAG% 2>&1
) else (
    "%PYTHON_CMD%" "%SCRIPT_PATH%" "%TSV_PATH%" "%DROPBOX_ROOT%" 2>&1
)
set "PYTHON_EXIT_CODE=%errorlevel%"

echo.
echo Python command finished.

echo.
echo ================================================================
echo Python script finished with exit code: %PYTHON_EXIT_CODE%
echo ================================================================

if !PYTHON_EXIT_CODE! neq 0 (
    echo.
    echo ================================================================
    echo ERROR: Python script failed with exit code !PYTHON_EXIT_CODE!
    echo ================================================================
    echo.
    echo The script ran but encountered an error.
    echo Please scroll up to see the detailed error messages.
    echo.
    echo Press any key to close this window...
    pause
) else (
    echo.
    echo ================================================================
    echo PYTHON SCRIPT COMPLETED (exit code 0)
    echo ================================================================
    echo.
    echo However, the preview image was not created successfully.
    echo Please scroll up to see why the preview generation failed.
    echo.
    echo Common issues:
    echo - No images found in Dropbox folder
    echo - Missing composite/frame files
    echo - Permission issues creating output file
    echo.
    echo Press any key to close this window...
    pause
)

exit /b %PYTHON_EXIT_CODE%

:detect_python
:: Detect Python installation in various locations
set "PYTHON_CMD="

:: Check standard locations for Python 3.11 and 3.10
for %%P in (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311-32\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python310\python.exe"
    "C:\Program Files (x86)\Python311\python.exe"
    "C:\Program Files (x86)\Python310\python.exe"
) do (
    if exist "%%P" (
        :: Test if it actually works
        "%%P" --version >nul 2>&1
        if !errorlevel! == 0 (
            set "PYTHON_CMD=%%P"
            goto :eof
        )
    )
)

:: Try Python launcher first (standard on modern Windows)
py --version >nul 2>&1
if !errorlevel! == 0 (
    set "PYTHON_CMD=py"
    goto :eof
)

:: Try PATH-based commands  
python --version >nul 2>&1
if !errorlevel! == 0 (
    set "PYTHON_CMD=python"
    goto :eof
)

python3 --version >nul 2>&1
if !errorlevel! == 0 (
    set "PYTHON_CMD=python3"
    goto :eof
)

:: Check Windows Store Python
for %%P in (
    "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\python.exe"
    "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\python3.exe"
) do (
    if exist "%%P" (
        "%%P" --version >nul 2>&1
        if !errorlevel! == 0 (
            set "PYTHON_CMD=%%P"
            goto :eof
        )
    )
)

goto :eof