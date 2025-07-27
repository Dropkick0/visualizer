# bbox_map.py  –  one authoritative place for all FileMaker UI crop rectangles
# ---------------------------------------------------------------------------
UI_VERSION = "FileOrder_v1.10.25"          # bump this if FileMaker layout shifts

# Screenshot capture standards
CAPTURE_STANDARDS = {
    "resolution": "1680x1050",  # Native monitor resolution (measured)
    "scaling": "100%",          # Windows display scaling
    "format": "PNG",            # Lossless format
    "dpi": 96                   # Standard Windows DPI at 100% scaling
}

# (x1, y1, x2, y2)  – inclusive top-left, bottom-right pixel coords
BB = {
    # --- PORTRAITS master table block (helps for QA overlay) -------------
    "PORTRAIT_TABLE" : (  30,  430,   796,  875),   # whole red-outlined table

    # --- Column-isolated crops (feed each to WinRT OCR) ------------------
    "COL_QTY"        : (  30,  430,    70,  875),   # Quantity column
    "COL_CODE"       : (  70,  430,   150,  875),   # 3-digit/decimal product code
    "COL_DESC"       : ( 150,  430,   550,  875),   # Long description text
    "COL_IMG"        : ( 550,  430,   700,  875),   # 4-digit image IDs (comma-sep)
    # ---------- (Ignore ArtistSeries, Frames, Retouch blocks for now) ----
}

# Fine-tuning parameters for quick adjustments
PAD_X = 4   # extra px added left/right to every box  
PAD_Y = 2   # extra px added top/bottom

# Legacy compatibility functions
def get_column_boxes():
    """Return column bounding boxes with optional padding applied"""
    boxes = {}
    for name, (x1, y1, x2, y2) in BB.items():
        if name.startswith('COL_'):
            boxes[name] = (x1 - PAD_X, y1 - PAD_Y, x2 + PAD_X, y2 + PAD_Y)
    return boxes

def get_sentinel_coords():
    """Return layout drift detection coordinates"""
    return [
        (50, 420),   # Above qty header
        (300, 420),  # Above description header  
        (600, 420),  # Above image header
        (50, 450),   # Inside qty column
        (600, 450)   # Inside image column
    ]

# Column field mapping for row reconstruction
COLUMN_FIELDS = {
    "COL_QTY": "qty",
    "COL_CODE": "code", 
    "COL_DESC": "desc",
    "COL_IMG": "image_codes"
}

# Layout validation colors (for drift detection)
LAYOUT_COLORS = {
    "background": (240, 240, 240),  # Light gray background
    "tolerance": 30
}

def validate_ui_version():
    """Validate UI version compatibility"""
    return True  # Always compatible for now

def get_layout_info():
    """Return current layout configuration info"""
    return {
        "ui_version": UI_VERSION,
        "capture_standards": CAPTURE_STANDARDS,
        "total_columns": len([k for k in BB.keys() if k.startswith('COL_')]),
        "table_area": BB["PORTRAIT_TABLE"]
    } 