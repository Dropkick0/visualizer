# OCR constants for row extraction
from os import getenv

# Default row band configuration
ROW_COUNT_DEFAULT = 18
ORDER_ROI_TOP = 485
ORDER_ROI_BOTTOM = 891
ORDER_ROI_LEFT = 31
ORDER_ROI_RIGHT = 950
ROW_EXTRA_PAD = 0
# row_index -> (dy_top, dy_bot)
ROW_MANUAL_OFFSETS: dict[int, tuple[int, int]] = {}

# Allow quick tuning via environment variables
ROW_COUNT_DEFAULT = int(getenv("OCR_ROW_COUNT", ROW_COUNT_DEFAULT))
ORDER_ROI_TOP = int(getenv("OCR_ROI_TOP", ORDER_ROI_TOP))
ORDER_ROI_BOTTOM = int(getenv("OCR_ROI_BOTTOM", ORDER_ROI_BOTTOM))
ORDER_ROI_LEFT = int(getenv("OCR_ROI_LEFT", ORDER_ROI_LEFT))
ORDER_ROI_RIGHT = int(getenv("OCR_ROI_RIGHT", ORDER_ROI_RIGHT))
ROW_EXTRA_PAD = int(getenv("OCR_ROW_PAD", ROW_EXTRA_PAD))
