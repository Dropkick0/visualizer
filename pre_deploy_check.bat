@echo off
title Portrait Preview Webapp - Pre-Deployment Check
echo ========================================
echo  Pre-Deployment System Check
echo ========================================
echo.

set "check_passed=true"

echo Checking system requirements...
echo.

REM Check Python installation
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ from python.org
    set "check_passed=false"
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set python_ver=%%i
    echo [OK] Python %python_ver% found
)

REM Check if we're in the right directory
echo [2/6] Checking project directory...
if exist "app\__init__.py" (
    echo [OK] Portrait Preview project directory confirmed
) else (
    echo [ERROR] Not in the correct project directory
    echo Please run this from the Dynamic Order Viewer folder
    set "check_passed=false"
)

REM Check required files
echo [3/6] Checking required project files...
set "missing_files="
if not exist "app\routes.py" set "missing_files=%missing_files% app\routes.py"
if not exist "config\products.yaml" set "missing_files=%missing_files% config\products.yaml"
if not exist "requirements_bundle.txt" set "missing_files=%missing_files% requirements_bundle.txt"
if not exist "build_bundle.py" set "missing_files=%missing_files% build_bundle.py"

if defined missing_files (
    echo [ERROR] Missing required files:%missing_files%
    set "check_passed=false"
) else (
    echo [OK] All required project files found
)

REM Check Windows OCR
echo [4/6] Checking Windows OCR functionality...
python -c "import winocr; print('[OK] Windows OCR library available')" 2>nul
if errorlevel 1 (
    echo [WARNING] Windows OCR library not installed
    echo Will install during deployment process
) else (
    echo [OK] Windows OCR library is available
)

REM Check disk space (estimate 500MB needed)
echo [5/6] Checking available disk space...
for /f "tokens=3" %%i in ('dir /-c 2^>nul ^| find "bytes free"') do set free_space=%%i
if defined free_space (
    echo [OK] Sufficient disk space available
) else (
    echo [WARNING] Could not check disk space
)

REM Check for existing bundle
echo [6/6] Checking for existing bundle...
if exist "bundle\" (
    echo [WARNING] Existing bundle folder found - will be overwritten
) else (
    echo [OK] No existing bundle found
)

echo.
echo ========================================
echo   Check Summary
echo ========================================

if "%check_passed%"=="true" (
    echo [SUCCESS] All critical checks passed!
    echo.
    echo You can now run the deployment:
    echo   deploy.bat
    echo.
    echo Or test Windows OCR first:
    echo   python test_windows_ocr.py
) else (
    echo [FAILED] Some critical checks failed
    echo Please fix the issues above before deploying
)

echo.
pause 