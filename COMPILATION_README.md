# Portrait Visualizer - Compilation Guide

## Creating a Standalone Executable

This guide shows how to compile the Portrait Visualizer into a single `.exe` file that can be shared and used without requiring AutoHotkey installation.

## Prerequisites

1. **AutoHotkey v2.0** - [Download from autohotkey.com](https://www.autohotkey.com/)
2. **Ahk2Exe Compiler** - Included with AutoHotkey installation
3. **Python 3.11+** - Must be installed on target machines (or included separately)

## Compilation Steps

### Method 1: Using Ahk2Exe GUI

1. **Open Ahk2Exe**:
   - Find it in your AutoHotkey installation folder (usually `C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe`)
   - Or right-click on `Visualizer (3).ahk` and select "Compile Script"

2. **Configure Compilation**:
   - **Source (script file)**: `Visualizer (3).ahk`
   - **Destination (.exe file)**: `PortraitVisualizer.exe`
   - **Base file (.exe)**: Use default AutoHotkey v2 base file
   - **Icon file**: Leave default or add custom icon

3. **Click "Convert"** to create the executable

### Method 2: Command Line Compilation

Open Command Prompt in the project directory and run:

```batch
"C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe" /in "Visualizer (3).ahk" /out "PortraitVisualizer.exe"
```

### PyInstaller Build (Python Only)

To freeze the Python preview script into a single executable run:

```bash
pyinstaller --onefile \
            --add-data "Composites;Composites" \
            --add-data "Frames;Frames" \
            --add-data "config.json;." \
            test_preview_with_fm_dump.py
```

The helper function `resource_path()` will locate these files at run time.

## What Gets Included

The compiled executable automatically includes:
- ✅ All Python scripts (`test_preview_with_fm_dump.py`, `app/` folder)
- ✅ All composite images (`Composites/` folder)
- ✅ All frame images (`Frames/` folder)
- ✅ Configuration files
- ✅ Requirements file

## Distribution

### For End Users

**What they need**:
1. `PortraitVisualizer.exe` (the compiled file)
2. **Python 3.11+** installed with required packages:
   ```bash
   pip install Flask loguru python-dotenv pydantic PyYAML Pillow numpy opencv-python python-magic winocr
   ```

**How it works**:
1. Double-click `PortraitVisualizer.exe`
2. Select photographer's folder
3. Follow on-screen instructions (NumPad * to run)
4. Files are saved to `Documents\VisualizerWorkspace\`
5. Preview image opens automatically

### Directory Structure (After First Run)

```
Documents\VisualizerWorkspace\
├── app/                     # Python modules
├── Composites/             # Composite templates
├── Frames/                 # Frame images
├── preview_output/         # Generated previews
├── fm_dump.tsv            # Extracted data
└── test_preview_with_fm_dump.py
```

## Testing the Compiled Version

1. Compile the script following steps above
2. Move the `.exe` to a different folder (to test self-containment)
3. Run the executable
4. Verify all files are created in `Documents\VisualizerWorkspace\`
5. Test the full workflow with FileMaker Pro

## Troubleshooting

**"Python not found" error**:
- Ensure Python is installed and in PATH
- Test with: `python --version` in Command Prompt

**"Preview image not found" error**:
- Check if Python packages are installed correctly
- Verify working directory permissions
- Look for error details in the popup message

**FileInstall errors during compilation**:
- Ensure all source files exist in the project directory
- Check file paths in the AutoHotkey script match actual files

## File Locations for Users

- **Working Files**: `%USERPROFILE%\Documents\VisualizerWorkspace\`
- **Preview Images**: `%USERPROFILE%\Documents\VisualizerWorkspace\preview_output\`
- **Data Export**: `%USERPROFILE%\Documents\VisualizerWorkspace\fm_dump.tsv`
