"""
Production-Ready OCR Extractor for FileMaker PORTRAITS Table
Implements column-isolated OCR with high-DPI scaling and intelligent row reconstruction
"""

import cv2
import numpy as np
import re
import difflib
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple
from collections import defaultdict
from dataclasses import dataclass
from loguru import logger

try:
    import winocr
    WINOCR_AVAILABLE = True
except ImportError:
    WINOCR_AVAILABLE = False
    logger.warning("winocr not available - will use fallback OCR")

from .bbox_map import (
    get_column_boxes,
    get_sentinel_coords,
    COLUMN_FIELDS,
    LAYOUT_COLORS,
    UI_VERSION,
    validate_ui_version,
    BB,
)

# --- Additional OCR regions for frames/retouch --------------------------------
# Coordinates tuned for the reference 1680x1050 screenshot resolution.
FRAMES_TABLE = (1120, 500, 1580, 760)
RETOUCH_BOX = (970, 300, 1270, 450)

# Regular expression patterns for parsing the extra tables
FRAME_ROW_RE = re.compile(
    r"(?P<qty>\d+)\s+(?P<num>\d+)\s+(?P<size>\d+\s*x\s*\d+)\s+(?P<color>black|cherry)",
    re.IGNORECASE,
)
RETOUCH_RE = re.compile(r"(?P<qty>\d+)\s+(?P<name>Artist brush strokes.*)", re.I)


def parse_frames(lines: List[str]) -> Dict[str, Dict[str, int]]:
    """Parse frame counts from OCR lines."""
    frame_counts: Dict[str, Dict[str, int]] = {}
    for ln in lines:
        m = FRAME_ROW_RE.search(ln)
        if not m:
            continue
        size = m.group("size").replace(" ", "")
        color = m.group("color").lower()
        qty = int(m.group("qty"))
        frame_counts.setdefault(size, {}).setdefault(color, 0)
        frame_counts[size][color] += qty
    return frame_counts


def parse_retouch(lines: List[str]) -> Tuple[List[Dict[str, int]], bool]:
    """Parse retouch entries from OCR lines and detect Artist Series."""
    retouch = []
    artist_series = False
    for ln in lines:
        if "artist brush strokes" in ln.lower():
            artist_series = True
        m = RETOUCH_RE.search(ln)
        if m and int(m.group("qty")) > 0:
            retouch.append({"name": m.group("name").strip(), "qty": int(m.group("qty"))})
    return retouch, artist_series


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
        self.ocr_engine = None
        self.performance_stats = {}
        self.frame_counts: Dict[str, Dict[str, int]] = {}
        self.retouch_items: List[Dict[str, int]] = []
        self.artist_series: bool = False
        
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
        
        logger.info(f"Starting column-isolated OCR extraction from {screenshot_path}")
        
        try:
            # Step 1: Validate layout hasn't drifted
            if not self._validate_layout(screenshot_path):
                logger.warning("Layout validation failed - bounding boxes may be outdated")
            
            # Step 2: Load and prepare base image
            base_image = cv2.imread(str(screenshot_path))
            if base_image is None:
                raise ValueError(f"Could not load screenshot: {screenshot_path}")
            
            # Step 3: Run column-isolated OCR
            ocr_results = self._run_column_isolated_ocr(base_image, work_dir)

            # Additional ROIs for frames and retouch sections
            self.frames_lines = self._ocr_roi(base_image, FRAMES_TABLE, "FRAMES", work_dir)
            self.retouch_lines = self._ocr_roi(base_image, RETOUCH_BOX, "RETOUCH", work_dir)
            self.frame_counts = parse_frames(self.frames_lines)
            self.retouch_items, self.artist_series = parse_retouch(self.retouch_lines)
            logger.info(f"Frames parsed: {self.frame_counts}")
            logger.info(f"Retouch parsed: {self.retouch_items}")
            logger.info(f"Artist series detected: {self.artist_series}")
            
            # Step 4: Reconstruct rows by Y-centroid matching
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
            # Fallback: return empty list with error
            return [RowRecord(warnings=[f"Extraction failed: {e}"])]
    
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
    
    def _run_column_isolated_ocr(self, base_image: np.ndarray, work_dir: Path) -> Dict[str, List[tuple]]:
        """Run OCR on each column separately with high-DPI upscaling"""
        results: Dict[str, List[tuple]] = {}

        for col_name, bbox in self.column_boxes.items():
            try:
                # Step 1: Crop column
                x1, y1, x2, y2 = bbox
                column_crop = base_image[y1:y2, x1:x2]

                # Step 2: High-DPI preprocessing (3x upscaling)
                processed_crop = self._preprocess_for_ocr(column_crop, col_name, work_dir)

                # Step 3: Run OCR on processed crop
                ocr_blocks = self._run_ocr_on_crop(processed_crop, col_name)

                # Convert OCR blocks to (text, y_mid) tuples
                lines = []
                for block in ocr_blocks:
                    txt = str(block.get('text', '')).strip()
                    if not txt:
                        continue
                    if 'boundingBox' in block:
                        bbox = block['boundingBox']
                        y_mid = (bbox[1] + bbox[5]) / 2
                    else:
                        y_mid = block.get('y_position', 0)
                    lines.append((txt, y_mid))

                results[col_name] = lines
                logger.debug("Column %s: %d lines", col_name, len(lines))

            except Exception as e:
                logger.error(f"OCR failed for column {col_name}: {e}")
                results[col_name] = []

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
            # Convert to PIL format for winocr
            from PIL import Image
            pil_image = Image.fromarray(processed_crop)
            
            # Run Windows OCR
            result = winocr.recognize_pil_sync(pil_image, 'en-US')
            text = result.get('text', '') if isinstance(result, dict) else ''
            
            # Parse lines with Y positions
            lines = []
            if text.strip():
                raw_lines = text.split('\n')
                for i, line_text in enumerate(raw_lines):
                    if line_text.strip():
                        lines.append({
                            'text': line_text.strip(),
                            'y_position': i * 30,  # Estimate line height
                            'confidence': 90.0,    # Default high confidence for Windows OCR
                            'column': col_name
                        })
            
            return lines
            
        except Exception as e:
            logger.error(f"Windows OCR failed for {col_name}: {e}")
            return []
    
    def _mock_ocr_result(self, col_name: str) -> List[Dict]:
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
        
        lines = []
        if col_name in mock_data:
            for i, text in enumerate(mock_data[col_name]):
                lines.append({
                    'text': text,
                    'y_position': i * 35 + 420,  # Start at y=420, 35px spacing
                    'confidence': 95.0,
                    'column': col_name
                })
        
        return lines
    
    def _reconstruct_rows(self, cols: Dict[str, List[tuple]]) -> List[RowRecord]:
        """Rebuild row records by aligning text using Y centroids."""

        if not cols:
            return []

        anchor = sorted(cols.get('COL_QTY', []), key=lambda t: t[1])
        rows = [{'y': y, 'qty': '', 'code': '', 'desc': '', 'imgs': ''} for _, y in anchor]

        def assign(col_name: str, key: str):
            for text, y in cols.get(col_name, []):
                target = min(rows, key=lambda r: abs(r['y'] - y))
                if abs(target['y'] - y) < 12:
                    target[key] = text

        assign('COL_QTY', 'qty')
        assign('COL_CODE', 'code')
        assign('COL_DESC', 'desc')
        assign('COL_IMG', 'imgs')

        row_records = [RowRecord(qty=r['qty'], code=r['code'], desc=r['desc'], imgs=r['imgs'], y_position=r['y']) for r in rows]
        logger.debug("Reconstructed %d rows", len(row_records))
        return row_records
    
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
        
        # Extract all 4-digit codes
        codes = re.findall(r'\b\d{4}\b', str(text))
        
        # Remove duplicates while preserving order
        unique_codes = []
        for code in codes:
            if code not in unique_codes:
                unique_codes.append(code)
        
        return ", ".join(unique_codes)
    
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
                        "Warnings": '; '.join(row.warnings) if row.warnings else ''
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
