# Portrait Preview Webapp - Bundling Guide

This guide explains how to create a one-click deployment package for the Portrait Preview Webapp that uses Windows built-in OCR instead of Tesseract.

## 🚀 Quick Start (One-Click Deployment)

### For Developers:

1. **Activate your virtual environment** (recommended):
   ```bash
   .venv\Scripts\activate
   ```

2. **Run the deployment script**:
   ```bash
   deploy.bat
   ```

3. **Share the bundle**:
   - Find `bundle/PortraitPreview_Bundle.zip`
   - Share this ZIP file with users

### For End Users:

1. **Extract the ZIP file** to any folder
2. **Run `INSTALL.bat`** as Administrator (one-time setup)
3. **Start the app** with `Launch_Portrait_Preview.bat`
4. **Open browser** to `http://localhost:5000`

## 📦 What Gets Bundled

The bundled package includes:
- ✅ **Standalone executable** - No Python installation required
- ✅ **Windows OCR integration** - No Tesseract dependency  
- ✅ **All assets** - Backgrounds, frames, configs
- ✅ **Web UI** - Complete Flask web interface
- ✅ **Easy launcher** - Double-click to start
- ✅ **Documentation** - Quick start guides

## 🔧 Manual Bundling Process

If you need more control, you can run the bundling steps manually:

### Step 1: Install Dependencies
```bash
pip install -r requirements_bundle.txt
pip install pyinstaller
```

### Step 2: Create Bundle
```bash
python build_bundle.py
```

### Step 3: Test Bundle
```bash
cd bundle\PortraitPreview
Launch_Portrait_Preview.bat
```

## 📁 Bundle Structure

```
bundle/
├── PortraitPreview_Bundle.zip     # Distribution file
├── INSTALL.bat                    # One-time setup
└── PortraitPreview/               # App folder
    ├── PortraitPreview.exe        # Main executable
    ├── Launch_Portrait_Preview.bat # Easy launcher
    ├── assets/                    # Backgrounds & frames
    ├── config/                    # Product configs
    ├── QUICK_START.txt           # User guide
    └── README.md                 # Documentation
```

## 🛠️ Customizing the Bundle

### Adding New Assets

1. **Add backgrounds**: Place in `assets/backgrounds/`
2. **Add frames**: Place in `assets/frames/single/` or `assets/frames/multi/`
3. **Update configs**: Modify `config/products.yaml` and `config/frames.yaml`
4. **Rebuild bundle**: Run `deploy.bat` again

### Changing App Settings

1. **Edit** `app/config.py` for default settings
2. **Modify** `config/settings.yaml` for runtime configs
3. **Update** product definitions in `config/products.yaml`
4. **Rebuild** with `deploy.bat`

### Bundle Size Optimization

The current bundle excludes heavy dependencies:
- ❌ matplotlib (plotting)
- ❌ tkinter (GUI toolkit) 
- ❌ Qt frameworks
- ❌ Development tools

To further reduce size:
- Remove unused assets from `assets/`
- Optimize images (use smaller backgrounds)
- Remove unused product configs

## 🔍 Troubleshooting Bundle Creation

### Common Issues:

**"PyInstaller not found"**
```bash
pip install pyinstaller
```

**"Module not found during bundle"**
- Add missing modules to `hiddenimports` in `build_bundle.py`
- Check `requirements_bundle.txt` includes all dependencies

**"Bundle too large"**  
- Check `excludes` list in PyInstaller spec
- Remove unused assets
- Use UPX compression (already enabled)

**"App won't start after bundling"**
- Test bundle with `python run_bundle.py`
- Check Windows OCR is available: `python -c "import winocr"`
- Verify all assets copied correctly

### Debug Bundle Issues:

1. **Run executable with console**:
   ```bash
   cd bundle\PortraitPreview
   PortraitPreview.exe --debug
   ```

2. **Check logs**:
   - Look for error messages in console output
   - Check if all assets are found

3. **Test OCR separately**:
   ```python
   import winocr
   from PIL import Image
   
   # Test Windows OCR
   img = Image.new('RGB', (100, 50), color='white')
   result = winocr.recognize_pil_sync(img)
   print(result['text'])
   ```

## 🔐 Security Considerations

**For Distribution:**
- Bundle may be flagged by antivirus (false positive)
- Consider code signing for production use
- Test on clean Windows VMs before distribution

**For Users:**
- Windows OCR requires language pack installation
- App needs network access for Dropbox folder scanning
- Runs local web server on port 5000

## 📋 Requirements for End Users

**System Requirements:**
- Windows 10 (version 1903+) or Windows 11
- 4GB RAM minimum, 8GB recommended  
- 500MB free disk space
- Internet connection (for Dropbox access)

**One-Time Setup:**
- Install English OCR language pack (via `INSTALL.bat`)
- Administrator access for OCR setup

**Runtime Requirements:**
- None! Everything is bundled

## 🚀 Advanced Deployment Options

### Silent Installation

Create a silent installer that runs OCR setup automatically:

```batch
@echo off
echo Installing OCR language pack silently...
powershell -Command "Add-WindowsCapability -Online -Name 'Language.OCR~~~en-US~0.0.1.0'" -WindowStyle Hidden
echo Done! Starting app...
cd PortraitPreview
PortraitPreview.exe
```

### Network Deployment

For corporate environments:
1. Create shared network folder
2. Copy bundle contents
3. Create desktop shortcuts pointing to launcher
4. Deploy OCR language pack via Group Policy

### Service Mode

To run as Windows service:
1. Install `python-windows-service`
2. Modify `run_bundle.py` to support service mode
3. Use `sc create` to install service

## 📞 Support

If users encounter issues:
1. Check `QUICK_START.txt` in bundle
2. Verify Windows OCR language pack installed
3. Ensure port 5000 is not blocked
4. Try running as Administrator

For developers:
- See main `README.md` for development setup
- Check `DEPLOYMENT.md` for production deployment
- Test bundle on multiple Windows versions 