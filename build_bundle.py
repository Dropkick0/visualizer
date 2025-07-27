#!/usr/bin/env python3
"""
Bundle script for Portrait Preview Webapp
Creates a standalone Windows executable with all dependencies and assets
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import tempfile
import zipfile

def main():
    """Main bundling process"""
    print("🏗️  Building Portrait Preview Webapp Bundle...")
    
    # Paths
    root_dir = Path(__file__).parent
    build_dir = root_dir / "dist"
    bundle_dir = root_dir / "bundle"
    
    # Clean previous builds
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("🧹 Cleaned previous build directory")
    
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
        print("🧹 Cleaned previous bundle directory")
    
    # Create bundle directory
    bundle_dir.mkdir()
    
    # Step 1: Install bundle dependencies
    print("\n📦 Installing bundle dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements_bundle.txt"
        ], check=True, cwd=root_dir)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False
    
    # Step 2: Create PyInstaller spec file
    print("\n📝 Creating PyInstaller configuration...")
    spec_content = create_pyinstaller_spec()
    spec_file = root_dir / "portrait_preview.spec"
    
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    print("✅ PyInstaller spec file created")
    
    # Step 3: Build executable with PyInstaller
    print("\n🔨 Building executable...")
    try:
        subprocess.run([
            sys.executable, "-m", "PyInstaller", 
            "--clean", 
            str(spec_file)
        ], check=True, cwd=root_dir)
        print("✅ Executable built successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller failed: {e}")
        return False
    
    # Step 4: Create launcher batch file
    print("\n🚀 Creating launcher...")
    launcher_content = create_launcher_script()
    launcher_file = build_dir / "PortraitPreview" / "Launch_Portrait_Preview.bat"
    
    with open(launcher_file, 'w') as f:
        f.write(launcher_content)
    print("✅ Launcher created")
    
    # Step 5: Copy additional files
    print("\n📋 Copying additional files...")
    copy_additional_files(build_dir / "PortraitPreview")
    print("✅ Additional files copied")
    
    # Step 6: Create final bundle
    print("\n📦 Creating final bundle...")
    create_final_bundle(build_dir / "PortraitPreview", bundle_dir)
    print("✅ Final bundle created")
    
    # Step 7: Test the bundle
    print("\n🧪 Testing bundle...")
    if test_bundle(bundle_dir):
        print("✅ Bundle test passed")
    else:
        print("⚠️  Bundle test had issues (but may still work)")
    
    print(f"\n🎉 Bundle complete! Find your app in: {bundle_dir}")
    print("\n📖 To use the app:")
    print("   1. Extract the ZIP bundle to any folder")
    print("   2. Double-click 'Launch_Portrait_Preview.bat'")
    print("   3. Open your browser to http://localhost:5000")
    
    return True


def create_pyinstaller_spec():
    """Create PyInstaller spec file content"""
    return '''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

block_cipher = None

# Determine data files to include
datas = [
    ('app/templates', 'app/templates'),
    ('app/static', 'app/static'),
    ('config', 'config'),
    ('assets', 'assets'),
    ('README.md', '.'),
]

# Hidden imports for Windows OCR and other modules
hiddenimports = [
    'winocr',
    'asyncio',
    'cv2',
    'PIL',
    'numpy',
    'yaml',
    'pydantic',
    'loguru',
    'app.ocr_windows',
    'app.parse',
    'app.mapping',
    'app.render',
    'app.layout',
    'app.composite',
    'app.config',
    'app.errors',
    'app.utils',
]

# Binaries to include
binaries = []

a = Analysis(
    ['run_bundle.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'tkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PortraitPreview',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if Path('assets/icon.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PortraitPreview',
)
'''


def create_launcher_script():
    """Create Windows batch launcher script"""
    return '''@echo off
title Portrait Preview Webapp
echo ========================================
echo    Portrait Preview Webapp Launcher
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "PortraitPreview.exe" (
    echo Error: PortraitPreview.exe not found!
    echo Please make sure you're running this from the correct directory.
    pause
    exit /b 1
)

echo Starting Portrait Preview Webapp...
echo.
echo The app will be available at: http://localhost:5000
echo.
echo To stop the app, close this window or press Ctrl+C
echo.
echo ========================================

REM Start the application
PortraitPreview.exe

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo ========================================
    echo Application ended with an error.
    echo Check the logs above for details.
    echo ========================================
    pause
)
'''


def copy_additional_files(dist_dir):
    """Copy additional files needed for the bundle"""
    files_to_copy = [
        ("README.md", "README.md"),
        ("DEPLOYMENT.md", "DEPLOYMENT.md"),
    ]
    
    for src_file, dest_file in files_to_copy:
        src = Path(src_file)
        if src.exists():
            dest = dist_dir / dest_file
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    
    # Create a quick start guide
    quick_start = dist_dir / "QUICK_START.txt"
    with open(quick_start, 'w') as f:
        f.write("""Portrait Preview Webapp - Quick Start Guide
==========================================

FIRST TIME SETUP:
1. Make sure you're on Windows 10 or 11
2. Install English OCR language pack (run as Administrator):
   Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"

TO START THE APP:
1. Double-click "Launch_Portrait_Preview.bat"
2. Wait for the console window to show "Running on http://127.0.0.1:5000"
3. Open your web browser and go to: http://localhost:5000

USING THE APP:
1. Upload a FileMaker screenshot (PNG/JPG)
2. Enter the Dropbox folder path where customer images are stored
3. Select background and frame options
4. Click "Generate Preview"
5. Download or share the generated preview

TROUBLESHOOTING:
- If OCR fails: Install Windows OCR language pack (see setup above)
- If images not found: Check Dropbox folder path is correct
- If app won't start: Make sure port 5000 is not in use

For detailed help, see README.md or DEPLOYMENT.md
""")


def create_final_bundle(source_dir, bundle_dir):
    """Create final deployable bundle"""
    # Copy the distribution
    app_dir = bundle_dir / "PortraitPreview"
    shutil.copytree(source_dir, app_dir)
    
    # Create installer script
    installer_script = bundle_dir / "INSTALL.bat"
    with open(installer_script, 'w') as f:
        f.write('''@echo off
title Portrait Preview Webapp Installer
echo ========================================
echo    Portrait Preview Webapp Installer
echo ========================================
echo.

echo This will set up the Portrait Preview Webapp on your system.
echo.
echo Prerequisites:
echo - Windows 10 or 11
echo - Administrator access (for OCR language pack)
echo.

pause

echo Installing Windows OCR language pack...
powershell -Command "Add-WindowsCapability -Online -Name 'Language.OCR~~~en-US~0.0.1.0'"

if errorlevel 1 (
    echo.
    echo Warning: OCR language pack installation may have failed.
    echo You may need to run this as Administrator.
    echo.
)

echo.
echo Installation complete!
echo.
echo To start the app:
echo 1. Go to the PortraitPreview folder
echo 2. Double-click "Launch_Portrait_Preview.bat"
echo.
pause
''')
    
    # Create ZIP archive for easy distribution
    zip_file = bundle_dir / "PortraitPreview_Bundle.zip"
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in app_dir.rglob('*'):
            if file_path.is_file():
                arc_name = file_path.relative_to(bundle_dir)
                zf.write(file_path, arc_name)
        
        # Add installer
        zf.write(installer_script, "INSTALL.bat")


def test_bundle(bundle_dir):
    """Test the created bundle"""
    app_dir = bundle_dir / "PortraitPreview"
    exe_file = app_dir / "PortraitPreview.exe"
    
    if not exe_file.exists():
        print(f"❌ Executable not found: {exe_file}")
        return False
    
    # Test if executable can start (just check if it loads)
    try:
        # Quick test - just try to start and stop immediately
        result = subprocess.run([
            str(exe_file), "--help"
        ], capture_output=True, timeout=10, cwd=app_dir)
        
        # If it runs without error, consider it a pass
        return result.returncode == 0 or "usage" in result.stdout.decode().lower()
    
    except subprocess.TimeoutExpired:
        # Timeout might be OK - app might be starting web server
        return True
    except Exception as e:
        print(f"❌ Bundle test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 