import os

# Row image inflation constants for Windows OCR
ROW_SCALE_X = 5
ROW_SCALE_Y = 4
ROW_MIN_WIDTH = 1600
ROW_SIDE_PAD = 60

# Debug flag for per-row outputs
OCR_DEBUG_ROWS = os.getenv("OCR_DEBUG_ROWS", "1") == "1"

# Row band geometry defaults (override via environment variables)
ROW_COUNT_DEFAULT = int(os.getenv("OCR_ROW_COUNT", 18))
ORDER_ROI_TOP = int(os.getenv("OCR_ROI_TOP", 485))
ORDER_ROI_BOTTOM = int(os.getenv("OCR_ROI_BOTTOM", 891))
ORDER_ROI_LEFT = int(os.getenv("OCR_ROI_LEFT", 31))
ORDER_ROI_RIGHT = int(os.getenv("OCR_ROI_RIGHT", 950))
ROW_EXTRA_PAD = int(os.getenv("OCR_ROW_PAD", 0))
# row_index -> (dy_top, dy_bot)
ROW_MANUAL_OFFSETS: dict[int, tuple[int, int]] = {}
