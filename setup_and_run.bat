@echo off
setlocal enabledelayedexpansion

:: Portrait Visualizer Setup and Launch Script
:: This script ensures Python is installed before running the visualizer

echo.
echo ================================================================
echo           PORTRAIT VISUALIZER SETUP
echo ================================================================
echo.
echo This tool will:
echo  1. Check if Python is installed on your system
echo  2. Install Python 3.11.0 if needed (requires admin permission)
echo  3. Automatically launch the Portrait Visualizer
echo.
echo Please wait while we check your system...
echo.

:: Check if Python is installed and accessible
call :detect_python
if defined PYTHON_CMD (
    echo ✓ Python is already installed: %PYTHON_CMD%
    for /f "tokens=2" %%v in ('"%PYTHON_CMD%" --version 2^>^&1') do echo ✓ Version: %%v
    goto :run_visualizer
)

:: Python not found, need to install
echo.
echo ⚠️  Python is not installed or not in your system PATH
echo.
echo Installing Python 3.11.0 for you...
echo.
echo IMPORTANT NOTES:
echo  • The Python installer will run automatically
echo  • This may take several minutes to complete
echo  • If automatic installation fails, we'll try manual installation
echo.
echo Press any key to start Python installation...
pause

:: Check if the Python installer exists
if not exist "python-3.11.0-amd64.exe" (
    echo.
    echo ❌ ERROR: Python installer not found!
    echo.
    echo The file "python-3.11.0-amd64.exe" should be in the same folder as this script.
    echo Please make sure the Python installer is in the correct location.
    echo.
    pause
    exit /b 1
)

echo.
echo 🔄 Launching Python installer...
echo    (This may take a few moments)
echo.

:: Run the Python installer with recommended settings
:: InstallAllUsers=0 installs for current user (more reliable)
:: PrependPath=1 adds Python to PATH automatically
:: Include_tcltk=1 includes Tkinter
echo Running installer with parameters: InstallAllUsers=0 PrependPath=1 Include_tcltk=1
"python-3.11.0-amd64.exe" InstallAllUsers=0 PrependPath=1 Include_tcltk=1

:: Check if installation was successful
if !errorlevel! neq 0 (
    echo.
    echo ❌ Python installation failed or was cancelled.
    echo.
    echo Please try running this script again, or install Python manually:
    echo  1. Double-click "python-3.11.0-amd64.exe" 
    echo  2. Make sure to check "Add Python to PATH"
    echo  3. Complete the installation
    echo  4. Run this script again
    echo.
    pause
    exit /b 1
)

echo.
echo ✓ Python installation completed!
echo.

:: Wait for installation to complete and files to be written
echo Waiting for installation to complete...
timeout /t 5 /nobreak >nul

echo.
echo 🔍 Debugging Python installation...
echo Checking if Python files were created...

:: Check common Python installation locations
set "INSTALL_FOUND=0"
for %%P in (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311-32"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python310"
    "C:\Python311"
    "C:\Python310"
    "C:\Program Files\Python311"
    "C:\Program Files\Python310"
    "C:\Program Files (x86)\Python311"
    "C:\Program Files (x86)\Python310"
) do (
    if exist "%%P\python.exe" (
        echo ✓ Found Python at: %%P\python.exe
        set "INSTALL_FOUND=1"
    )
)

if !INSTALL_FOUND! == 0 (
    echo ⚠️  No Python installation found in expected locations
    echo Checking if installer is still running...
    tasklist /FI "IMAGENAME eq python-3.11.0-amd64.exe" 2>nul | find /I "python-3.11.0-amd64.exe" >nul
    if !errorlevel! == 0 (
        echo 🔄 Installer still running, waiting longer...
        timeout /t 10 /nobreak >nul
    )
)

echo Refreshing system PATH...
call :refresh_path

:: Try to detect Python after installation
echo Detecting Python installation...
call :detect_python
if not defined PYTHON_CMD (
    echo.
    echo ❌ Python installation may not have completed properly.
    echo.
    echo Debugging information:
    echo • Checked standard installation paths
    echo • Refreshed environment PATH
    echo • Waited for installation completion
    echo.
    echo Would you like to try manual installation instead?
    echo.
    echo  Y - Yes, open the Python installer manually
    echo  N - No, exit and try again later
    echo.
    set /p choice=Your choice (Y/N): 
    if /i "!choice!"=="Y" goto :manual_install
    if /i "!choice!"=="y" goto :manual_install
    exit /b 1
)

echo ✓ Python found: %PYTHON_CMD%

:: Verify Python version is 3.11+
for /f "tokens=2" %%v in ('"%PYTHON_CMD%" --version 2^>^&1') do set "PYTHON_VERSION=%%v"
echo ✓ Python version: %PYTHON_VERSION%

:run_visualizer
echo.
echo ================================================================
echo           INSTALLING REQUIRED DEPENDENCIES
echo ================================================================
echo.

echo 📦 Installing Python dependencies...
echo    This may take a few minutes on first run...
echo.

:: Test pip first
echo    • Testing pip...
%PIP_CMD% --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ❌ pip is not working properly
    pause
    exit /b 1
)

:: Try to upgrade pip first
echo    • Upgrading pip...
%PIP_CMD% install --upgrade pip --quiet

:: Install each package individually with the found Python/pip
echo    • Installing Flask...
%PIP_CMD% install Flask --quiet
if !errorlevel! neq 0 (
    echo ❌ Failed to install Flask
    pause
    exit /b 1
)

echo    • Installing loguru...
%PIP_CMD% install loguru --quiet
if !errorlevel! neq 0 (
    echo ❌ Failed to install loguru  
    pause
    exit /b 1
)

echo    • Installing python-dotenv...
%PIP_CMD% install python-dotenv --quiet
if !errorlevel! neq 0 (
    echo ❌ Failed to install python-dotenv
    pause
    exit /b 1
)

echo    • Installing pydantic...
%PIP_CMD% install pydantic --quiet
if !errorlevel! neq 0 (
    echo ❌ Failed to install pydantic
    pause
    exit /b 1
)

echo    • Installing PyYAML...
%PIP_CMD% install PyYAML --quiet
if !errorlevel! neq 0 (
    echo ❌ Failed to install PyYAML
    pause
    exit /b 1
)

echo    • Installing Pillow...
%PIP_CMD% install Pillow --quiet
if !errorlevel! neq 0 (
    echo ❌ Failed to install Pillow
    pause
    exit /b 1
)

echo    • Installing numpy...
%PIP_CMD% install numpy --quiet
if !errorlevel! neq 0 (
    echo ❌ Failed to install numpy
    pause
    exit /b 1
)

echo    • Installing opencv-python...
%PIP_CMD% install opencv-python --quiet
if !errorlevel! neq 0 (
    echo ⚠️  Standard opencv-python failed, trying opencv-python-headless...
    %PIP_CMD% install opencv-python-headless --quiet
    if !errorlevel! neq 0 (
        echo ❌ Both opencv versions failed - continuing anyway
    ) else (
        echo ✓ opencv-python-headless installed successfully
    )
) else (
    echo ✓ opencv-python installed successfully
)

echo    • Installing optional packages...
%PIP_CMD% install python-magic --quiet >nul 2>&1
%PIP_CMD% install winocr --quiet >nul 2>&1

echo ✓ All dependencies installed successfully!

:: Final test - verify Python can import required modules
echo.
echo 🧪 Testing Python installation...
echo Testing individual modules...

:: Test each module individually to identify which one fails
echo   • Testing flask...
%PYTHON_CMD% -c "import flask; print('✓ flask OK')" 2>nul
if !errorlevel! neq 0 echo   ❌ flask failed

echo   • Testing loguru...
%PYTHON_CMD% -c "import loguru; print('✓ loguru OK')" 2>nul
if !errorlevel! neq 0 echo   ❌ loguru failed

echo   • Testing pydantic...
%PYTHON_CMD% -c "import pydantic; print('✓ pydantic OK')" 2>nul
if !errorlevel! neq 0 echo   ❌ pydantic failed

echo   • Testing PIL...
%PYTHON_CMD% -c "import PIL; print('✓ PIL OK')" 2>nul
if !errorlevel! neq 0 echo   ❌ PIL failed

echo   • Testing numpy...
%PYTHON_CMD% -c "import numpy; print('✓ numpy OK')" 2>nul
if !errorlevel! neq 0 echo   ❌ numpy failed

echo   • Testing opencv...
%PYTHON_CMD% -c "import cv2; print('✓ cv2 OK')" 2>nul
if !errorlevel! neq 0 (
    echo   ❌ cv2 failed - trying to fix...
    echo   Attempting OpenCV fixes...
    
    :: Try uninstalling and reinstalling opencv
    %PIP_CMD% uninstall opencv-python opencv-python-headless -y --quiet >nul 2>&1
    
    :: Try opencv-python-headless first (more compatible)
    echo   • Trying opencv-python-headless...
    %PIP_CMD% install opencv-python-headless --quiet
    %PYTHON_CMD% -c "import cv2; print('✓ cv2 fixed with headless version')" 2>nul
    if !errorlevel! neq 0 (
        :: Try specific opencv version
        echo   • Trying specific opencv version...
        %PIP_CMD% install opencv-python==4.8.1.78 --quiet
        %PYTHON_CMD% -c "import cv2; print('✓ cv2 fixed with specific version')" 2>nul
        if !errorlevel! neq 0 (
            echo   ❌ OpenCV fixes failed - may need Visual C++ redistributables
        )
    )
)

echo.
echo Press any key to see detailed test results...
pause

:: Test all together with more detailed error output
echo.
echo Testing all modules together...
%PYTHON_CMD% -c "
try:
    import flask
    print('✓ flask imported')
    import loguru  
    print('✓ loguru imported')
    import pydantic
    print('✓ pydantic imported')
    import PIL
    print('✓ PIL imported')
    import numpy
    print('✓ numpy imported')
    import cv2
    print('✓ cv2 imported')
    print('✅ All modules imported successfully!')
except ImportError as e:
    print(f'❌ Import failed: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    exit(1)
"

if !errorlevel! neq 0 (
    echo.
    echo ❌ Module import test failed. 
    echo.
    echo If only OpenCV (cv2) failed, this is very common and might not affect your visualizer.
    echo.
    echo Common OpenCV solutions:
    echo   1. Install Visual C++ Redistributables from Microsoft
    echo   2. Try running as Administrator
    echo   3. OpenCV may not be needed for your specific use case
    echo.
    echo Your visualizer might work perfectly without OpenCV!
    echo.
    echo Press any key to see your options...
    pause
    echo.
    set /p continue=Continue anyway? (Y/N): 
    if /i "!continue!"=="Y" goto :launch_visualizer
    if /i "!continue!"=="y" goto :launch_visualizer
    echo.
    echo OpenCV troubleshooting steps:
    echo 1. Download Visual C++ Redistributable from Microsoft
    echo 2. Run this script as Administrator
    echo 3. Try: pip uninstall opencv-python && pip install opencv-python-headless
    echo.
    echo Press any key to close...
    pause
    exit /b 1
)
echo ✓ Python installation test passed!

:launch_visualizer
echo.
echo ================================================================
echo           LAUNCHING PORTRAIT VISUALIZER
echo ================================================================
echo.

:: Check if the visualizer executable exists
if not exist "PortraitVisualizer.exe" (
    echo ❌ ERROR: PortraitVisualizer.exe not found!
    echo.
    echo Please make sure PortraitVisualizer.exe is in the same folder as this script.
    echo.
    pause
    exit /b 1
)

echo 🚀 Starting Portrait Visualizer...
echo.
echo The visualizer will now open. You can:
echo  • Select your photographer's folder when prompted
echo  • Press NUMPAD * to run the visualization
echo  • Press ESC to exit if needed
echo.

:: Launch the visualizer
start "" "PortraitVisualizer.exe"

echo ✓ Portrait Visualizer launched successfully!
echo.
echo This setup window will close in 5 seconds...
echo (You can close it manually if needed)
echo.

:: Wait a bit then close this window
timeout /t 5 /nobreak >nul
exit /b 0

:detect_python
:: Detect Python installation in various locations
set "PYTHON_CMD="
set "PIP_CMD="

echo   Checking direct file paths...
:: Check standard locations for Python 3.11
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
        echo   ✓ Found Python at: %%P
        :: Test if it actually works
        "%%P" --version >nul 2>&1
        if !errorlevel! == 0 (
            set "PYTHON_CMD=%%P"
            set "PIP_CMD=%%P -m pip"
            goto :eof
        ) else (
            echo   ⚠️  Python found but not working: %%P
        )
    )
)

echo   Checking PATH commands...
:: Try PATH-based commands  
python --version >nul 2>&1
if !errorlevel! == 0 (
    echo   ✓ Found python command in PATH
    set "PYTHON_CMD=python"
    set "PIP_CMD=python -m pip"
    goto :eof
)

python3 --version >nul 2>&1
if !errorlevel! == 0 (
    echo   ✓ Found python3 command in PATH
    set "PYTHON_CMD=python3"
    set "PIP_CMD=python3 -m pip"
    goto :eof
)

:: Check for any Python installations
echo   Checking for any Python installations...
where python >nul 2>&1
if !errorlevel! == 0 (
    echo   Found python in PATH:
    where python
)

where python3 >nul 2>&1
if !errorlevel! == 0 (
    echo   Found python3 in PATH:
    where python3
)

echo   No working Python installation detected
goto :eof

:manual_install
echo.
echo ================================================================
echo           MANUAL PYTHON INSTALLATION
echo ================================================================
echo.
echo Opening Python installer manually...
echo.
echo CRITICAL: In the installer, you MUST:
echo  ✓ Check "Add Python to PATH" at the bottom
echo  ✓ Click "Install Now" or "Customize Installation"
echo  ✓ If customizing, ensure "Add Python to environment variables" is checked
echo.
echo After installation completes, run this script again.
echo.
pause

:: Open the installer manually
start "" "python-3.11.0-amd64.exe"

echo.
echo Python installer opened. Please complete the installation and run this script again.
echo.
pause
exit /b 0

:refresh_path
:: Refresh environment variables to pick up newly installed Python
echo Refreshing PATH from registry...
for /f "skip=2 tokens=3*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "sys_path=%%b"
for /f "skip=2 tokens=3*" %%a in ('reg query HKCU\Environment /v PATH 2^>nul') do set "user_path=%%b"
if defined user_path (
    set "PATH=%sys_path%;%user_path%"
) else (
    set "PATH=%sys_path%"
)
echo Current PATH updated
goto :eof