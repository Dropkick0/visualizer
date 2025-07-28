import os

ROW_COUNT_DEFAULT = int(os.getenv("OCR_ROW_COUNT", 18))
ORDER_ROI_TOP = int(os.getenv("OCR_ROI_TOP", 485))
ORDER_ROI_BOTTOM = int(os.getenv("OCR_ROI_BOTTOM", 891))
ORDER_ROI_LEFT = int(os.getenv("OCR_ROI_LEFT", 31))
ORDER_ROI_RIGHT = int(os.getenv("OCR_ROI_RIGHT", 950))
ROW_EXTRA_PAD = int(os.getenv("OCR_ROW_PAD", 0))

# row_index -> (dy_top, dy_bot)
ROW_MANUAL_OFFSETS: dict[int, tuple[int, int]] = {}
