@echo off
echo ====================================
echo   Portrait Visualizer Compiler
echo ====================================
echo.

REM Check if AutoHotkey compiler is available
set AHK_COMPILER=
set USE_AHK_SCRIPT=0

REM First check for compiled Ahk2Exe.exe in various locations
if exist "C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe" (
    set "AHK_COMPILER=C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe"
    goto :found_compiler
)

if exist "C:\Program Files\AutoHotkey\Ahk2Exe.exe" (
    set "AHK_COMPILER=C:\Program Files\AutoHotkey\Ahk2Exe.exe"
    goto :found_compiler
)

if exist "%USERPROFILE%\AppData\Local\Programs\AutoHotkey\Compiler\Ahk2Exe.exe" (
    set "AHK_COMPILER=%USERPROFILE%\AppData\Local\Programs\AutoHotkey\Compiler\Ahk2Exe.exe"
    goto :found_compiler
)

REM Check for local downloaded version (script form)
if exist "Ahk2Exe-master\Ahk2Exe.ahk" (
    echo Found local Ahk2Exe source - will use AutoHotkey to run compiler script
    set "AHK_COMPILER=Ahk2Exe-master\Ahk2Exe.ahk"
    set USE_AHK_SCRIPT=1
    goto :found_compiler
)

echo ERROR: AutoHotkey compiler not found
echo.
echo Checked locations:
echo - C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe
echo - C:\Program Files\AutoHotkey\Ahk2Exe.exe
echo - Local: Ahk2Exe-master\Ahk2Exe.ahk
echo.
echo The script has downloaded Ahk2Exe source to Ahk2Exe-master\
echo but something went wrong. Please check the folder exists.
echo.
pause
exit /b 1

:found_compiler

REM Check if source file exists
if not exist "Visualizer (3).ahk" (
    echo ERROR: Source file "Visualizer (3).ahk" not found
    echo Please run this batch file from the project directory
    echo.
    pause
    exit /b 1
)

echo Compiling Visualizer (3).ahk to PortraitVisualizer.exe...
echo.

REM Compile the script
echo Using compiler: %AHK_COMPILER%

if %USE_AHK_SCRIPT%==1 (
    echo Running Ahk2Exe script with AutoHotkey...
    "C:\Program Files\AutoHotkey\AutoHotkey.exe" "%AHK_COMPILER%" /in "Visualizer (3).ahk" /out "PortraitVisualizer.exe" /base "C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe"
) else (
    echo Running compiled Ahk2Exe with v2.0 base...
    "%AHK_COMPILER%" /in "Visualizer (3).ahk" /out "PortraitVisualizer.exe" /base "C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe"
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo   Compilation Successful!
    echo ====================================
    echo.
    echo Output file: PortraitVisualizer.exe
    echo.
    echo This executable can now be distributed and will work on any
    echo Windows computer with Python 3.11+ installed.
    echo.
    echo Next steps:
    echo 1. Test the compiled executable
    echo 2. Distribute PortraitVisualizer.exe to users
    echo 3. Ensure users have Python and required packages installed
    echo.
    echo For detailed instructions, see COMPILATION_README.md
    echo.
) else (
    echo.
    echo ====================================
    echo   Compilation Failed!
    echo ====================================
    echo.
    echo Please check the error messages above and:
    echo 1. Ensure all source files are present
    echo 2. Check AutoHotkey installation
    echo 3. Review COMPILATION_README.md for troubleshooting
    echo.
)

pause
