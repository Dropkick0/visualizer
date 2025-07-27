@echo off
title Portrait Preview Webapp - One-Click Deployment
echo ========================================
echo Portrait Preview Webapp - Deployment
echo ========================================
echo.

echo This script will:
echo 1. Install PyInstaller (if needed)
echo 2. Install Windows OCR dependencies
echo 3. Create a standalone executable
echo 4. Bundle everything for easy distribution
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.11+ and try again
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check if we're in a virtual environment
if defined VIRTUAL_ENV (
    echo [OK] Virtual environment detected: %VIRTUAL_ENV%
    goto start_install
) else (
    echo [WARNING] Not in a virtual environment
    echo It's recommended to use a virtual environment
    echo.
    goto ask_continue
)

:ask_continue
set /p continue="Continue anyway? (y/N): "

REM Check for yes responses
if "%continue%"=="y" goto continue_deploy
if "%continue%"=="Y" goto continue_deploy
if "%continue%"=="yes" goto continue_deploy
if "%continue%"=="Yes" goto continue_deploy
if "%continue%"=="YES" goto continue_deploy

REM Check for no responses
if "%continue%"=="n" goto exit_deploy
if "%continue%"=="N" goto exit_deploy
if "%continue%"=="no" goto exit_deploy
if "%continue%"=="No" goto exit_deploy
if "%continue%"=="NO" goto exit_deploy
if "%continue%"=="" goto exit_deploy

REM Invalid response - ask again
echo Please enter 'y' for yes or 'n' for no
goto ask_continue

:exit_deploy
echo Exiting...
pause
exit /b 0

:continue_deploy
echo [OK] Continuing without virtual environment...
goto start_install

:start_install

echo Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller
    echo Check your internet connection and Python installation
    pause
    exit /b 1
)

echo [OK] PyInstaller installed
echo.

echo Running bundle creation script...
python build_bundle.py
if errorlevel 1 (
    echo [ERROR] Bundle creation failed
    echo Check the output above for detailed error information
    pause
    exit /b 1
)

echo.
echo ========================================
echo    DEPLOYMENT COMPLETE!
echo ========================================
echo.
echo Your bundled app is ready in the 'bundle' folder:
echo.
if exist bundle (
    dir bundle /b
) else (
    echo [ERROR] Bundle folder not found!
)
echo.
echo === DISTRIBUTION INSTRUCTIONS ===
echo 1. Share the "PortraitPreview_Bundle.zip" file
echo 2. Recipients should extract and run "INSTALL.bat"
echo 3. Then use "Launch_Portrait_Preview.bat" to start
echo.
echo === TESTING LOCALLY ===
echo 1. Go to bundle\PortraitPreview\
echo 2. Double-click "Launch_Portrait_Preview.bat"
echo 3. Open browser to http://localhost:5000
echo.
echo === NEXT STEPS ===
echo - Test the bundle before distributing
echo - See BUNDLE_GUIDE.md for more details
echo - Check Windows OCR language pack is installed
echo.
pause 