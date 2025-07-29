# Portrait Preview Webapp

**Internal tool for generating customer portrait previews from FileMaker Field Order screenshots**

This Flask-based web application allows staff to upload a screenshot of a FileMaker Field Order (Item Entry screen) and specify a Dropbox folder path to automatically generate a professional portrait preview for customers. The system uses OCR to extract product information and image codes, then composites customer photos with frames and backgrounds.

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** (64-bit recommended)
2. **Tesseract OCR** - Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - Install to: `C:\Program Files\Tesseract-OCR`
   - Ensure `tesseract.exe` is in PATH or set `TESSERACT_PATH` in environment
3. **MSVC++ Redistributables** (if needed for image libraries)

### Installation

1. **Clone or extract the project**
   ```bash
   cd "Dynamic Order Viewer"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment** (optional)
   - Copy `.env.example` to `.env` 
   - Configure `TESSERACT_PATH` and `DROPBOX_ROOT` if needed

5. **Add sample assets**
   - Place background images in `assets/backgrounds/`
   - Place frame PNGs in `assets/frames/single/` and `assets/frames/multi/`

6. **Run the application**
   ```bash
   python run_dev.py
   ```

7. **Open in browser**
   - Navigate to `http://localhost:5000`

## 📁 Project Structure

```
portrait_preview_webapp/
├── app/                    # Flask application package
│   ├── __init__.py        # App factory and setup
│   ├── config.py          # Configuration management
│   ├── routes.py          # Web routes and handlers
│   ├── utils.py           # Utility functions
│   ├── errors.py          # Custom exceptions
│   ├── static/            # Static web assets
│   │   ├── css/app.css   # Custom styling
│   │   ├── js/app.js     # Client-side JavaScript
│   │   └── previews/     # Generated preview images
│   └── templates/         # Jinja2 HTML templates
│       ├── base.html     # Base template
│       ├── index.html    # Upload form
│       ├── result.html   # Preview display
│       └── error.html    # Error page
├── assets/                # Static assets
│   ├── backgrounds/      # Background images
│   └── frames/           # Frame overlay PNGs
│       ├── single/       # Single opening frames
│       └── multi/        # Multi-opening frames
├── config/               # Configuration files
│   ├── settings.yaml     # Application settings
│   ├── products.yaml     # Product definitions
│   └── frames.yaml       # Frame asset mappings
├── tmp/                  # Temporary work directories
├── logs/                 # Application logs
├── requirements.txt      # Python dependencies
└── run_dev.py           # Development server
```

## 🔧 Configuration

### Product Configuration (`config/products.yaml`)

Defines mapping from FileMaker text to product specifications:

```yaml
products:
  - slug: "8x10_basic"
    width_in: 8.0
    height_in: 10.0
    count_images: 1
    frame_style_default: "none"
    frame_styles_allowed: ["none", "cherry", "black"]
    quantity_behavior: "single"
    parsing_patterns:
      - "8x10"
      - "810"  # SKU code
      - "complimentary 8x10"
```

### Frame Configuration (`config/frames.yaml`)

Maps product sizes and styles to frame assets:

```yaml
frames:
  - product_slug: "8x10_basic" 
    style: "cherry"
    asset_path: "assets/frames/single/frame_8x10_cherry.png"
    opening_boxes: [[0.12, 0.08, 0.88, 0.92]]  # [x1,y1,x2,y2] relative coords
```

### Application Settings (`config/settings.yaml`)

Global application configuration:

```yaml
PX_PER_INCH_DEFAULT: 40.0
MAX_UPLOAD_SIZE: 20971520  # 20MB
BACKGROUND_DEFAULT: "Virtual Background 2021.jpg"
QUANTITY_BADGE_ENABLED: true
```

## 📋 Usage Instructions

### For Staff Users

1. **Prepare FileMaker Screenshot**
   - Open Item Entry layout at 100% zoom
   - Ensure full PORTRAITS table is visible
   - Include Image Code column (4-digit numbers)
   - Take screenshot (Snipping Tool or PrtScn)

2. **Get Dropbox Folder Path**
   - Navigate to customer's sit folder in Dropbox
   - Right-click address bar → "Copy address as text"
   - Example: `C:\Users\remem\Re MEMBER Dropbox\PHOTOGRAPHY PROOFING\PHOTOGRAPHER UPLOADS (1)\7-15 Brent Price\bp071525.1`

3. **Generate Preview**
   - Open webapp in browser
   - Upload screenshot
   - Paste folder path
   - Select background (optional)
   - Click "Generate Preview"

4. **Review Output**
   - Verify faces, frame styles, and quantities
   - Check for missing image warnings
   - Show to customer when approved

## 🧩 Implementation Status

### ✅ Completed Phases

- **Phase 0**: Environment setup and requirements
- **Phase 1**: Project structure scaffolding  
- **Phase 2**: Product and frame configuration system
- **Phase 3**: Flask web UI with upload handling

### 🔨 Next Phases (To Be Implemented)

- **Phase 4**: Screenshot preprocessing for OCR
- **Phase 5**: Parse OCR text into structured order items
- **Phase 6**: Map image codes to actual files  
- **Phase 7**: Render prep (scaling, cropping, frame assets)
- **Phase 8**: Layout engine (place items on background)
- **Phase 9**: Composite final preview image
- **Phase 10**: Response rendering improvements

## 🛠️ Technical Details

### OCR Pipeline (Planned)
1. **Preprocessing**: Deskew, crop ROI, enhance contrast
2. **Text Extraction**: Tesseract OCR with custom configurations
3. **Parsing**: Extract quantities, products, image codes, frame styles
4. **Validation**: Check against product configurations

### Image Processing (Planned)
1. **File Discovery**: Scan Dropbox folder for image files
2. **Code Matching**: Map 4-digit codes to filenames
3. **Cropping**: Center-crop to target aspect ratios
4. **Scaling**: Resize based on px/inch settings
5. **Framing**: Apply frame overlays with proper openings

### Layout Engine (Planned)
1. **Sorting**: Arrange by size (largest first)
2. **Placement**: Use curated templates or auto-grid
3. **Collision Detection**: Prevent overlapping items
4. **Scaling**: Auto-adjust if items don't fit

## 🔍 Development Tools

### Debug Features
- Session debug endpoint: `/debug/{session_id}` (debug mode only)
- OCR overlay generation for troubleshooting
- Detailed logging with session tracking
- Work directory preservation for analysis

### Configuration Validation
```bash
python -c "from app.config import load_config; print('Config valid!')"
```

### Asset Validation
Run startup checks to ensure required directories and files exist.

### Preview from TSV
The `test_preview_with_fm_dump.py` helper script can render a preview from a
FileMaker TSV export without performing OCR. Use this for debugging complex
orders. Pass `--extreme` to replicate items and stress‑test the layout engine:

```bash
python test_preview_with_fm_dump.py --extreme
```

## 📝 Adding New Products

1. **Update `config/products.yaml`**
   ```yaml
   - slug: "new_product_size"
     width_in: X.X
     height_in: Y.Y
     parsing_patterns: ["new pattern", "SKU"]
   ```

2. **Add frame assets** (if framed)
   - Create PNG with transparent background
   - Place in `assets/frames/single/`
   - Update `config/frames.yaml` with opening coordinates

3. **Test with sample order**
   - Upload screenshot containing new product
   - Verify parsing and rendering

## 🚨 Troubleshooting

### Common Issues

**"No items detected in screenshot"**
- Ensure PORTRAITS table is fully visible
- Check zoom level (100% recommended)
- Verify text is clear and readable

**"Folder not found"**
- Check path for typos
- Ensure quotes are stripped
- Verify Dropbox folder is accessible

**"Missing images"**
- Confirm image files exist in specified folder
- Check 4-digit code matching in filenames
- Look in subfolders if necessary

**Tesseract not found**
- Install Tesseract OCR
- Set `TESSERACT_PATH` environment variable
- Ensure PATH includes Tesseract directory

### Log Files
- Application logs: `logs/app.log`
- Session artifacts: `tmp/{session_id}/`
- Debug mode preserves work directories

## 🔐 Security Notes

- **Internal use only** - No external exposure
- File uploads limited to 20MB images
- Basic path traversal protection
- Session cleanup prevents disk filling

## 🚀 Deployment (Future)

### Production Checklist
- [ ] Change `SECRET_KEY` in production
- [ ] Set `FLASK_ENV=production`
- [ ] Configure proper HTTPS
- [ ] Set up log rotation
- [ ] Install on Windows server with Dropbox access
- [ ] Create service/scheduled task for startup

### Performance Considerations
- OCR processing: ~2-5 seconds per screenshot
- Image processing: depends on file count and sizes
- Memory usage: ~100-500MB during processing
- Concurrent sessions: limited by server resources

---

**Version**: 1.0-dev  
**Last Updated**: December 2024  
**Internal Tool** - Re MEMBER Photography 
