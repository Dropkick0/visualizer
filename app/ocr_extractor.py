"""
Production-Ready OCR Extractor for FileMaker PORTRAITS Table
Implements column-isolated OCR with high-DPI scaling and intelligent row reconstruction
"""

import cv2
import numpy as np
import re
import difflib
import time
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from loguru import logger

try:
    import winocr
    WINOCR_AVAILABLE = True
except ImportError:
    WINOCR_AVAILABLE = False
    logger.warning("winocr not available - will use fallback OCR")


def win_ocr(pil_image):
    """Run Windows OCR and return list of (bbox, text) tuples."""
    if not WINOCR_AVAILABLE:
        return []
    try:
        result = winocr.recognize_pil_sync(pil_image, "en-US")
        lines = []
        if isinstance(result, dict) and result.get("lines"):
            for line in result["lines"]:
                txt = str(line.get("text", "")).strip()
                if not txt:
                    continue
                bbox = line.get("boundingBox") or line.get("bounding_box")
                if bbox:
                    ys = bbox[1::2]
                    y_top = min(ys)
                    y_bot = max(ys)
                else:
                    # Fallback estimate
                    idx = len(lines)
                    y_top = idx * 30
                    y_bot = y_top + 30
                lines.append(((y_top, y_bot), txt))
        else:
            text = result.get("text", "") if isinstance(result, dict) else ""
            for i, ln in enumerate(text.split("\n")):
                txt = ln.strip()
                if txt:
                    y_top = i * 30
                    lines.append(((y_top, y_top + 30), txt))
        return lines
    except Exception as e:
        logger.error(f"Windows OCR wrapper failed: {e}")
        return []

from .bbox_map import (
    get_column_boxes,
    get_sentinel_coords,
    LAYOUT_COLORS,
    UI_VERSION,
    COLUMN_FIELDS,
)

# --- Additional OCR regions for frames/retouch --------------------------------
# Coordinates tuned for the reference 1680x1050 screenshot resolution.
FRAMES_TABLE = (953, 593, 1385, 700)
RETOUCH_BOX = (1250, 250, 1370, 380)

# ----- Row grid tuning -----
ROW_COUNT_DEFAULT = 18
ORDER_ROI_TOP = 140     # px from screenshot top
ORDER_ROI_BOTTOM = 1850 # px from screenshot top
ROW_EXTRA_PAD = 6       # px pad added above/below each row

# Optional manual tweaks: row_index -> (dy_top, dy_bot)
ROW_MANUAL_OFFSETS = {
    # Example: 3: (-4, 8)
}

# Toggle row-based OCR via environment variable
SINGLE_LINE_MODE = os.getenv("SINGLE_LINE_MODE", "0") == "1"

# Regular expression patterns for parsing the extra tables
# FRAMES table contains quantity, frame number and a free form description that
# includes the size and color.  The OCR noise can vary, so we first capture the
# three main columns then search the description for the size/color keywords.
FRAME_ROW = re.compile(r"^(?P<qty>\d+)\s+\S+\s+(?P<desc>.+)$", re.I)
SIZE_RE = re.compile(r"(\d+\s*x\s*\d+)", re.I)
COLOR_RE = re.compile(r"\b(cherry|chetry|black|blk)\b", re.I)

# Normalize common OCR quirks for frame size/color text
SIZE_FIXES = {
    r"^34x7\b": "5x7",
    r"^8\s*x\s*10\b": "8x10",
}

COLOR_FIXES = {
    "chetry": "cherry",
    "blk": "black",
}

# Retouch/Artist Series options share a box. We'll look for common keywords in
# the description text and track their quantities separately.
OPTION_ROW = re.compile(r"^(?P<qty>\d+)\s+(?P<desc>.+)$", re.I)
RETOUCH_KEYS = ["retouch", "softens facial lines", "whitens teeth", "blends skin tones"]
ARTIST_KEYS = ["artist brush", "artist series"]


def parse_frames(lines: List[str]) -> Dict[str, Dict[str, int]]:
    """Parse frame counts from OCR lines."""
    logger.debug("FRAMES raw lines:\n" + "\n".join(lines))
    frame_counts: Dict[str, Dict[str, int]] = {}
    for ln in lines:
        m = FRAME_ROW.search(ln)
        if not m:
            continue
        qty = int(m.group("qty"))
        desc = m.group("desc")
        desc_lower = desc.lower()
        size_m = SIZE_RE.search(desc)
        color_m = COLOR_RE.search(desc)
        if not size_m:
            size_value = next((kw for kw in ["5x7", "8x10", "10x20", "5x10", "10x13", "16x20", "20x24"] if kw in desc_lower), None)
        else:
            size_value = size_m.group(1)

        if not color_m:
            color_value = next((kw for kw in ["cherry", "black", "white"] if kw in desc_lower), None)
        else:
            color_value = color_m.group(1)
        if not size_value or not color_value:
            continue
        size = size_value.replace(" ", "")
        color = color_value.lower()
        for pat, repl in SIZE_FIXES.items():
            size = re.sub(pat, repl, size, flags=re.I)
        color = COLOR_FIXES.get(color, color)
        frame_counts.setdefault(size, {}).setdefault(color, 0)
        frame_counts[size][color] += qty
    return frame_counts


def parse_retouch(lines: List[str]) -> Tuple[List[Dict[str, int]], bool, Set[str], Set[str]]:
    """Parse retouch entries and detect Artist Series with image codes."""
    retouch: List[Dict[str, int]] = []
    artist_series = False
    retouch_codes: Set[str] = set()
    artist_codes: Set[str] = set()
    for ln in lines:
        m = OPTION_ROW.search(ln)
        if not m:
            continue
        qty = int(m.group("qty"))
        if qty <= 0:
            continue
        desc = m.group("desc")
        desc_lower = desc.lower()
        codes = re.findall(r"\b\d{3,4}\b", desc)
        if any(k in desc_lower for k in ARTIST_KEYS):
            artist_series = True
            artist_codes.update(codes)
        elif any(k in desc_lower for k in RETOUCH_KEYS):
            retouch.append({"name": desc.strip(), "qty": qty})
            retouch_codes.update(codes)
    return retouch, artist_series, retouch_codes, artist_codes


def build_row_bboxes(img_h: int) -> List[Tuple[int, int, Optional[int], int]]:
    """Build a list of row bounding boxes covering the order table."""
    top = ORDER_ROI_TOP
    bottom = ORDER_ROI_BOTTOM if ORDER_ROI_BOTTOM > 0 else img_h + ORDER_ROI_BOTTOM
    total_h = bottom - top
    row_h = total_h / ROW_COUNT_DEFAULT

    bboxes: List[Tuple[int, int, Optional[int], int]] = []
    for i in range(ROW_COUNT_DEFAULT):
        y1 = int(top + i * row_h)
        y2 = int(top + (i + 1) * row_h)
        dy_top, dy_bot = ROW_MANUAL_OFFSETS.get(i, (0, 0))
        y1 = max(0, y1 + dy_top - ROW_EXTRA_PAD)
        y2 = min(img_h, y2 + dy_bot + ROW_EXTRA_PAD)
        bboxes.append((0, y1, None, y2))
    return bboxes


ROW_RE = re.compile(
    r'^\s*(?P<qty>\d+)\s+'
    r'(?P<code>\d+(?:\.\d+)?)\s+'
    r'(?P<desc>.+?)'
    r'(?:\s+(?P<imgs>(?:\d{3,4}(?:\s*,\s*\d{3,4})*)))?\s*$',
    re.I
)


@dataclass
class OcrLine:
    top: float
    bottom: float
    mid: float
    text: str


@dataclass
class RowRecord:
    """Structured representation of a PORTRAITS table row"""
    qty: Optional[int] = None
    code: str = ""
    desc: str = ""
    imgs: str = ""
    y_position: float = 0.0
    confidence: float = 0.0
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class OCRExtractor:
    """Column-isolated OCR processor with intelligent row reconstruction"""
    
    def __init__(self):
        self.ui_version = UI_VERSION
        self.column_boxes = get_column_boxes()
        self.ocr_engine = 'winocr'
        assert self.ocr_engine == 'winocr', "Tesseract must not be used"
        self.performance_stats = {}
        self.single_line_mode = SINGLE_LINE_MODE
        self.frame_counts: Dict[str, Dict[str, int]] = {}
        self.retouch_items: List[Dict[str, int]] = []
        self.artist_series: bool = False
        self.retouch_codes: Set[str] = set()
        self.artist_codes: Set[str] = set()
        
        # Load product codes for fuzzy matching
        self._load_product_codes()
        
        logger.info(f"OCR Extractor initialized - UI Version: {self.ui_version}")
        logger.info(f"Column boxes: {len(self.column_boxes)} configured")
    
    def _load_product_codes(self):
        """Load valid product codes from POINTS SHEET for fuzzy matching"""
        # Known product codes from the CSV
        self.valid_codes = [
            "001", "002", "003", "200", "350", "510", "510.1", "510.2", "510.3",
            "511", "511.1", "511.2", "511.3", "570", "571", "572", "810", "811", "812",
            "1013", "1014", "1015", "1020", "1020.1", "1020.2", "1020.3", "1020.4",
            "1020.5", "1020.6", "1020.7", "1620", "1621", "1622", "2024", "2025", "2026"
        ]
        logger.debug(f"Loaded {len(self.valid_codes)} valid product codes for fuzzy matching")
    
    def extract_rows(self, screenshot_path: Path, work_dir: Path = None) -> List[RowRecord]:
        """
        Main entry point: Extract structured rows from FileMaker screenshot
        
        Args:
            screenshot_path: Path to the FileMaker screenshot
            work_dir: Optional work directory for debug outputs
            
        Returns:
            List of RowRecord objects with structured data
        """
        start_time = time.time()
        
        if work_dir is None:
            work_dir = Path("tmp")
        work_dir.mkdir(exist_ok=True)
        
        logger.info(f"Starting OCR extraction from {screenshot_path}")
        
        try:
            # Step 1: Validate layout hasn't drifted
            if not self._validate_layout(screenshot_path):
                logger.warning("Layout validation failed - bounding boxes may be outdated")
            
            # Step 2: Load and prepare base image
            base_image = cv2.imread(str(screenshot_path))
            if base_image is None:
                raise ValueError(f"Could not load screenshot: {screenshot_path}")
            
            from PIL import Image
            pil_img = Image.fromarray(cv2.cvtColor(base_image, cv2.COLOR_BGR2RGB))

            # Additional ROIs for frames and retouch sections
            self.frames_lines = self._ocr_roi(base_image, FRAMES_TABLE, "FRAMES", work_dir)
            self.retouch_lines = self._ocr_roi(base_image, RETOUCH_BOX, "RETOUCH", work_dir)
            self.frame_counts = parse_frames(self.frames_lines)
            (
                self.retouch_items,
                self.artist_series,
                self.retouch_codes,
                self.artist_codes,
            ) = parse_retouch(self.retouch_lines)
            logger.info(f"Frames parsed: {self.frame_counts}")
            logger.info(f"Retouch parsed: {self.retouch_items}")
            logger.info(f"Artist series detected: {self.artist_series}")
            
            if self.single_line_mode:
                rows = self._ocr_rows_full_line(pil_img)
            else:
                ocr_results = self._run_column_isolated_ocr(base_image, work_dir)
                rows = self._reconstruct_rows(ocr_results)
            
            # Step 5: Apply domain-aware fuzzy corrections
            cleaned_rows = self._clean_rows(rows)
            
            # Step 6: Validate and log results
            validated_rows = self._validate_rows(cleaned_rows, work_dir)

            # Performance tracking
            total_time = time.time() - start_time
            self.performance_stats['last_extraction_time'] = total_time
            
            logger.info(f"Extraction complete in {total_time:.2f}s - {len(validated_rows)} rows extracted")
            
            if total_time > 1.0:
                logger.warning(f"Extraction time {total_time:.2f}s exceeds 1.0s target")
            
            return validated_rows

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise
    
    def _validate_layout(self, screenshot_path: Path) -> bool:
        """Detect if FileMaker layout has drifted using sentinel coordinates"""
        try:
            image = cv2.imread(str(screenshot_path))
            sentinels = get_sentinel_coords()
            
            expected_bg = LAYOUT_COLORS["background"]
            tolerance = LAYOUT_COLORS["tolerance"]
            
            for x, y in sentinels:
                if y >= image.shape[0] or x >= image.shape[1]:
                    continue
                    
                pixel = image[y, x]  # Note: OpenCV uses [y, x] indexing
                bgr_pixel = tuple(pixel)  # Convert from numpy array
                
                # Check if pixel color matches expected background
                color_diff = sum(abs(a - b) for a, b in zip(bgr_pixel, expected_bg))
                if color_diff > tolerance * 3:  # 3 channels
                    logger.debug(f"Sentinel ({x},{y}) color drift: {bgr_pixel} vs {expected_bg}")
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Layout validation failed: {e}")
            return False

    def _ocr_rows_full_line(self, pil_img) -> List[RowRecord]:
        """OCR each physical row as a full line using fixed grid."""
        h = pil_img.height
        boxes = build_row_bboxes(h)
        rows: List[RowRecord] = []
        for idx, (x1, y1, x2, y2) in enumerate(boxes):
            crop = pil_img.crop((x1, y1, x2 or pil_img.width, y2))
            ocr_lines = win_ocr(crop)
            text = " ".join(txt for (_, _), txt in ocr_lines).strip()
            if not text:
                continue
            m = ROW_RE.match(text)
            if not m:
                logger.debug("Row %d unparsable: %r", idx, text)
                continue
            rows.append(
                RowRecord(
                    qty=m.group('qty'),
                    code=m.group('code'),
                    desc=m.group('desc').strip(),
                    imgs=m.group('imgs') or '',
                    y_position=(y1 + y2) / 2,
                )
            )
        return rows
    
    def _run_column_isolated_ocr(self, base_image: np.ndarray, work_dir: Path) -> Dict[str, List[OcrLine]]:
        """Run OCR on each column separately with high-DPI upscaling"""
        results: Dict[str, List[OcrLine]] = {}

        for col_name, bbox in self.column_boxes.items():
            field = COLUMN_FIELDS.get(col_name, col_name)
            try:
                # Step 1: Crop column
                x1, y1, x2, y2 = bbox
                column_crop = base_image[y1:y2, x1:x2]

                # Step 2: High-DPI preprocessing (3x upscaling)
                processed_crop = self._preprocess_for_ocr(column_crop, col_name, work_dir)

                # Step 3: Run OCR on processed crop using Windows OCR
                from PIL import Image
                pil_image = Image.fromarray(processed_crop)
                ocr_lines = win_ocr(pil_image)

                lines: List[OcrLine] = []
                for (y_top, y_bot), txt in ocr_lines:
                    line = OcrLine(top=y_top, bottom=y_bot, mid=(y_top + y_bot) / 2, text=txt)
                    lines.append(line)

                if WINOCR_AVAILABLE and len(lines) == 0:
                    raise AssertionError(f"WinOCR returned 0 lines for {col_name}")

                results[field] = lines
                logger.debug("Column %s: %d lines", col_name, len(lines))

            except Exception as e:
                raise RuntimeError(f"OCR failed for column {col_name}") from e

        return results

    def _ocr_roi(self, base_image: np.ndarray, bbox: Tuple[int, int, int, int], label: str, work_dir: Path) -> List[str]:
        """OCR a single region of interest and return text lines."""
        try:
            x1, y1, x2, y2 = bbox
            crop = base_image[y1:y2, x1:x2]
            processed = self._preprocess_for_ocr(crop, label, work_dir)
            blocks = self._run_ocr_on_crop(processed, label)
            lines = []
            for block in blocks:
                txt = str(block.get("text", "")).strip()
                if txt:
                    lines.append(txt)
            logger.debug(f"ROI {label}: {len(lines)} lines")
            return lines
        except Exception as e:
            logger.error(f"OCR failed for ROI {label}: {e}")
            return []
    
    def _preprocess_for_ocr(self, crop: np.ndarray, col_name: str, work_dir: Path) -> np.ndarray:
        """Apply high-DPI preprocessing pipeline for optimal OCR"""
        
        # Step 1: Convert to grayscale
        if len(crop.shape) == 3:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop.copy()
        
        # Step 2: High-DPI virtual scaling (3x upscale)
        height, width = gray.shape
        upscaled = cv2.resize(gray, (width * 3, height * 3), interpolation=cv2.INTER_CUBIC)
        
        # Step 3: Adaptive thresholding for FileMaker's beige background
        thresh = cv2.adaptiveThreshold(
            upscaled, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 3
        )
        
        # Step 4: Optional morphological operations for thin fonts
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Save debug images
        debug_path = work_dir / f"debug_{col_name.lower()}_processed.png"
        cv2.imwrite(str(debug_path), processed)
        
        return processed
    
    def _run_ocr_on_crop(self, processed_crop: np.ndarray, col_name: str) -> List[Dict]:
        """Run Windows OCR on a preprocessed crop"""

        if not WINOCR_AVAILABLE:
            return self._mock_ocr_result(col_name)

        try:
            from PIL import Image
            pil_image = Image.fromarray(processed_crop)
            ocr_lines = win_ocr(pil_image)
            blocks = []
            for (y_top, y_bot), txt in ocr_lines:
                blocks.append({
                    'text': txt,
                    'y_position': (y_top + y_bot) / 2,
                    'boundingBox': [0, y_top, 0, y_top, 0, y_bot, 0, y_bot],
                    'column': col_name,
                    'confidence': 90.0,
                })
            return blocks
        except Exception as e:
            logger.error(f"Windows OCR failed for {col_name}: {e}")
            return []
    
    def _mock_ocr_result(self, col_name: str) -> List[OcrLine]:
        """Mock OCR for development when winocr not available"""
        # Mock data based on the actual FileMaker screenshot
        mock_data = {
            "COL_QTY": ["12", "1", "3", "1", "1", "3", "1", "1", "1"],
            "COL_CODE": ["200", "570", "350", "810", "1020.5", "510.3", "1013", "1620", "2024"],
            "COL_DESC": [
                "sheet of 8 wallets",
                "pair 5x7 BASIC", 
                "3.5\" x 5\" BASIC 1 sheet of 4",
                "8x10 BASIC",
                "10x20 TRIO PORTRAIT black digital mat, cherry frame",
                "5x10 triple opening with BLACK digital mat and cherry frame",
                "10x13 BASIC",
                "16x20 BASIC", 
                "20x24 BASIC"
            ],
            "COL_IMG": ["0033", "0033", "0033", "0033", "0033, 0044, 0039", "0039, 0033, 0044", "0102", "0033", "0102"]
        }
        
        lines: List[OcrLine] = []
        if col_name in mock_data:
            for i, text in enumerate(mock_data[col_name]):
                y_top = i * 35 + 420
                y_bot = y_top + 30
                lines.append(OcrLine(top=y_top, bottom=y_bot, mid=(y_top + y_bot) / 2, text=text))

        return lines
    
    def _reconstruct_with_anchor(self, cols: Dict[str, List[OcrLine]], qty_rows: List[OcrLine]) -> List[RowRecord]:
        """Original reconstruction anchored on quantity column."""

        med_h = np.median([(ln.bottom - ln.top) for ln in qty_rows]) if qty_rows else 0
        tol = med_h * 0.45

        def pick(col_lines: List[OcrLine], y_top: float, y_bot: float) -> str:
            band_mid = (y_top + y_bot) / 2
            best = None
            best_d = 9999
            for line in col_lines:
                d = abs(line.mid - band_mid)
                if d < best_d and (y_top - tol) <= line.mid <= (y_bot + tol):
                    best = line.text
                    best_d = d
            return best.strip() if best else ""

        rows = []
        for ln in qty_rows:
            row = RowRecord(
                qty=ln.text.strip(),
                code=pick(cols.get('code', []), ln.top, ln.bottom),
                desc=pick(cols.get('desc', []), ln.top, ln.bottom),
                imgs=pick(cols.get('imgs', []), ln.top, ln.bottom),
                y_position=ln.mid,
            )
            rows.append(row)
        return rows

    def _reconstruct_rows(self, cols: Dict[str, List[OcrLine]]) -> List[RowRecord]:
        """Rebuild rows, falling back to column-agnostic clustering when qty is sparse."""

        if not cols:
            return []

        logger.info(
            "Per-column line counts: " + ", ".join(f"{k}:{len(v)}" for k, v in cols.items())
        )

        qty_rows = sorted(cols.get('qty', []), key=lambda l: l.top)
        if len(qty_rows) >= 5:
            rows = self._reconstruct_with_anchor(cols, qty_rows)
            if rows:
                return rows

        # Fallback: cluster using all column lines
        bands: List[float] = []
        for lines in cols.values():
            for ln in lines:
                bands.append(ln.mid)

        if not bands:
            raise ValueError("No OCR lines to cluster")

        bands = sorted(bands)
        tol = np.median(np.diff(bands)) * 0.6 if len(bands) > 1 else 20
        clusters: List[Tuple[float, float]] = []
        cur = [bands[0]]
        for y in bands[1:]:
            if y - cur[-1] <= tol:
                cur.append(y)
            else:
                clusters.append((min(cur), max(cur)))
                cur = [y]
        clusters.append((min(cur), max(cur)))

        def pick(col_lines: List[OcrLine], y_top: float, y_bot: float) -> str:
            best = ""
            best_d = 1e9
            y_mid_band = (y_top + y_bot) / 2
            for line in col_lines:
                d = abs(line.mid - y_mid_band)
                if d < best_d and y_top - tol <= line.mid <= y_bot + tol:
                    best = line.text.strip()
                    best_d = d
            return best

        rows = []
        for y_top, y_bot in clusters:
            rows.append(
                RowRecord(
                    qty=pick(cols.get('qty', []), y_top, y_bot),
                    code=pick(cols.get('code', []), y_top, y_bot),
                    desc=pick(cols.get('desc', []), y_top, y_bot),
                    imgs=pick(cols.get('imgs', []), y_top, y_bot),
                    y_position=(y_top + y_bot) / 2,
                )
            )

        rows = [r for r in rows if any([r.qty, r.code, r.desc, r.imgs])]
        if len(rows) < 5:
            raise ValueError(f"Row reconstruction still too small ({len(rows)})")
        return rows
    
    def _clean_rows(self, rows: List[RowRecord]) -> List[RowRecord]:
        """Apply domain-aware fuzzy corrections to extracted data"""
        
        cleaned_rows = []
        for row in rows:
            try:
                # Clean quantity field
                row.qty = self._fix_qty(row.qty)
                
                # Clean product code
                row.code = self._fix_code(row.code)
                
                # Clean image codes
                row.imgs = self._fix_imgs(row.imgs)
                
                cleaned_rows.append(row)
                
            except Exception as e:
                logger.warning(f"Error cleaning row: {e}")
                row.warnings.append(f"Cleaning error: {e}")
                cleaned_rows.append(row)
        
        return cleaned_rows
    
    def _fix_qty(self, text: str) -> Optional[int]:
        """Fix quantity field - must be integer ≤ 30"""
        if not text:
            return None
            
        # Extract first number found
        match = re.search(r'\d+', str(text))
        if match:
            qty = int(match.group())
            if qty <= 30:  # Reasonable quantity limit
                return qty
            else:
                logger.warning(f"Quantity {qty} exceeds limit of 30")
                return qty  # Return anyway but flag warning
        
        return None
    
    def _fix_code(self, text: str) -> str:
        """Fix product code using fuzzy matching against known codes"""
        if not text:
            return ""
        
        text = str(text).strip()
        
        # Try exact match first
        if text in self.valid_codes:
            return text
        
        # Try fuzzy matching
        candidates = difflib.get_close_matches(text, self.valid_codes, n=1, cutoff=0.7)
        if candidates:
            corrected = candidates[0]
            if corrected != text:
                logger.debug(f"Fuzzy corrected code: '{text}' → '{corrected}'")
            return corrected
        
        # Return as-is if no match found
        return text
    
    def _fix_imgs(self, text: str) -> str:
        """Fix image codes - extract 4-digit comma-delimited sequences"""
        if not text:
            return ""
        
        # Extract all 4-digit codes preserving OCR order
        codes = re.findall(r'\b\d{4}\b', str(text))
        return ", ".join(codes)
    
    def _validate_rows(self, rows: List[RowRecord], work_dir: Path) -> List[RowRecord]:
        """Validate extracted rows and create QA log"""
        
        valid_rows = []
        
        for i, row in enumerate(rows):
            # Skip completely empty rows
            if not any([row.qty, row.code, row.desc, row.imgs]):
                continue
            
            # Validate composite products have exactly 3 image codes
            if row.code in ["510.3", "1020.5"]:  # Trio products
                img_count = len(row.imgs.split(", ")) if row.imgs else 0
                if img_count != 3:
                    row.warnings.append(f"Trio product {row.code} should have 3 images, found {img_count}")
            
            # Add row number for tracking
            row.row_number = i + 1
            valid_rows.append(row)

        # Gather unique image codes from rows
        IMG_RE = re.compile(r'\b\d{3,4}\b')
        image_codes: List[str] = []
        for r in valid_rows:
            image_codes += IMG_RE.findall(r.imgs or '')
        self.performance_stats['image_codes'] = list(dict.fromkeys(image_codes))

        # Create QA log CSV
        self._create_qa_log(valid_rows, work_dir)
        
        logger.info(f"Validated {len(valid_rows)} rows with {sum(len(r.warnings) for r in valid_rows)} total warnings")
        return valid_rows
    
    def _create_qa_log(self, rows: List[RowRecord], work_dir: Path):
        """Create CSV log for QA review"""
        try:
            import csv

            qa_log_path = work_dir / "ocr_extraction_qa.csv"
            fieldnames = [
                "Row",
                "Qty",
                "Code",
                "Description",
                "Image_Codes",
                "FramesCherry",
                "FramesBlack",
                "Retouch",
                "Confidence",
                "Warnings",
            ]
            fieldnames += ["FrameParsed", "RetouchParsed", "ArtistParsed"]
            with open(qa_log_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                # Data rows
                frames_cherry_total = sum(v.get('cherry', 0) for v in self.frame_counts.values())
                frames_black_total = sum(v.get('black', 0) for v in self.frame_counts.values())
                retouch_summary = "; ".join(f"{x['qty']}x {x['name']}" for x in self.retouch_items)
                
                for row in rows:
                    writer.writerow({
                        "Row": getattr(row, 'row_number', ''),
                        "Qty": row.qty or '',
                        "Code": row.code or '',
                        "Description": row.desc or '',
                        "Image_Codes": row.imgs or '',
                        "FramesCherry": frames_cherry_total,
                        "FramesBlack": frames_black_total,
                        "Retouch": retouch_summary,
                        "Confidence": f"{row.confidence:.1f}%",
                        "Warnings": '; '.join(row.warnings) if row.warnings else '',
                        "FrameParsed": json.dumps(self.frame_counts, ensure_ascii=False),
                        "RetouchParsed": retouch_summary,
                        "ArtistParsed": "Yes" if self.artist_series else "",
                    })
            
            logger.debug(f"QA log created: {qa_log_path}")
            
        except Exception as e:
            logger.warning(f"Failed to create QA log: {e}")
    
    def get_performance_stats(self) -> Dict:
        """Return performance statistics"""
        return self.performance_stats.copy()


# Convenience function for simple usage
def extract_portrait_rows(screenshot_path: Path, work_dir: Path = None) -> List[RowRecord]:
    """
    Simple function to extract portrait rows from a FileMaker screenshot
    
    Args:
        screenshot_path: Path to the FileMaker screenshot
        work_dir: Optional work directory for debug outputs
        
    Returns:
        List of RowRecord objects
    """
    extractor = OCRExtractor()
    return extractor.extract_rows(screenshot_path, work_dir) 
