# Quick Deployment Guide

## 🚀 One-Click Deployment Process

### Step 1: Pre-Check (Optional but Recommended)
```bash
pre_deploy_check.bat
```
This verifies your system is ready for deployment.

### Step 2: Deploy
```bash
deploy.bat
```
When prompted "Continue anyway? (y/N):", type `y` and press Enter.

### Step 3: Test Locally
```bash
cd bundle\PortraitPreview
Launch_Portrait_Preview.bat
```
Open http://localhost:5000 in your browser.

### Step 4: Distribute
Share `bundle\PortraitPreview_Bundle.zip` with users.

## 🔧 Troubleshooting

### "Exiting..." after typing 'y'
This was a bug in the original script, now fixed. The new version should work correctly.

### "PyInstaller failed"
```bash
pip install --upgrade pyinstaller
```

### "Windows OCR not available"
Run as Administrator:
```powershell
Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"
```

### "Bundle too large"
Normal size is 200-400MB. To reduce:
- Remove unused backgrounds from `assets/backgrounds/`
- Remove unused frames from `assets/frames/`

## 📋 What Gets Bundled

✅ **Standalone .exe** - No Python needed  
✅ **Windows OCR** - No Tesseract needed  
✅ **All assets** - Backgrounds, frames, configs  
✅ **Web interface** - Complete Flask app  
✅ **Easy launcher** - Double-click to start  

## 📦 Bundle Contents

```
bundle/
├── PortraitPreview_Bundle.zip    # Share this file
├── INSTALL.bat                   # User setup script
└── PortraitPreview/              # App folder
    ├── PortraitPreview.exe       # Main executable
    ├── Launch_Portrait_Preview.bat # Easy launcher
    ├── assets/                   # All backgrounds & frames
    ├── config/                   # Product definitions
    └── README.md                 # User documentation
```

## 👥 User Instructions

Send users these simple steps:

1. **Extract** the ZIP file anywhere
2. **Run** `INSTALL.bat` as Administrator (one-time only)
3. **Start** with `Launch_Portrait_Preview.bat`  
4. **Open** browser to http://localhost:5000

That's it! No Python, no Tesseract, no complex setup required.

## 🔍 Verification

Test the bundle works by:
1. Going to a different computer
2. Extracting the ZIP file
3. Running the installer and launcher
4. Uploading a test screenshot
5. Verifying OCR and preview generation works

The bundled app should work on any Windows 10/11 machine with the OCR language pack installed. 