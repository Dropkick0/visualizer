"""
OCR processing module for FileMaker Field Order screenshots
Handles image preprocessing, text extraction, and result structuring
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple
from PIL import Image, ImageOps
import pytesseract
from loguru import logger

from .errors import OCRError
from .config import AppConfig


class OCRWord(NamedTuple):
    """Individual word detected by OCR"""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x, y, width, height


class OCRResult(NamedTuple):
    """Complete OCR result structure"""
    raw_text: str
    lines: List[str]
    words: List[OCRWord]
    confidence_avg: float
    roi_bbox: Optional[Tuple[int, int, int, int]]  # Region of interest used


class FileMakerOCR:
    """OCR processor specifically designed for FileMaker Field Order screenshots"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.tesseract_path = self._get_tesseract_path()
        
        # OCR configuration strings
        self.general_config = f"--psm {config.OCR_PSM} --oem {config.OCR_OEM}"
        self.digits_config = f"--psm {config.OCR_PSM} --oem {config.OCR_OEM} -c tessedit_char_whitelist=0123456789"
        
        logger.info(f"OCR initialized with Tesseract path: {self.tesseract_path}")
    
    def _get_tesseract_path(self) -> str:
        """Detect or use configured Tesseract path"""
        if self.config.TESSERACT_PATH:
            tesseract_path = self.config.TESSERACT_PATH
        else:
            # Common Windows installation paths
            possible_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                "tesseract"  # If in PATH
            ]
            
            tesseract_path = None
            for path in possible_paths:
                if os.path.exists(path) or path == "tesseract":
                    tesseract_path = path
                    break
        
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            return tesseract_path
        else:
            raise OCRError("Tesseract OCR not found. Please install Tesseract or set TESSERACT_PATH")
    
    def process_screenshot(self, image_path: Path, work_dir: Path) -> OCRResult:
        """
        Main OCR processing pipeline for FileMaker screenshots
        Steps 56-74 of the implementation plan
        """
        logger.info(f"Processing screenshot: {image_path}")
        
        try:
            # Step 56: Load uploaded screenshot
            original_image = self._load_and_normalize_image(image_path)
            
            # Step 57: Auto-deskew (optional for now)
            deskewed_image = self._auto_deskew(original_image)
            
            # Step 58: Crop region of interest to PORTRAITS table
            roi_image, roi_bbox = self._crop_portraits_table(deskewed_image)
            
            # Save debug images
            debug_roi_path = work_dir / "debug_roi.png"
            cv2.imwrite(str(debug_roi_path), roi_image)
            logger.debug(f"ROI saved to: {debug_roi_path}")
            
            # Steps 60-66: Preprocess for OCR
            processed_image = self._preprocess_for_ocr(roi_image, work_dir)
            
            # Steps 67-73: Run OCR
            ocr_result = self._run_tesseract_ocr(processed_image, work_dir)
            
            # Add ROI information to result
            final_result = OCRResult(
                raw_text=ocr_result.raw_text,
                lines=ocr_result.lines, 
                words=ocr_result.words,
                confidence_avg=ocr_result.confidence_avg,
                roi_bbox=roi_bbox
            )
            
            logger.info(f"OCR completed - {len(final_result.lines)} lines, "
                       f"avg confidence: {final_result.confidence_avg:.1f}%")
            
            return final_result
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise OCRError(f"Failed to process screenshot: {e}")
    
    def _load_and_normalize_image(self, image_path: Path) -> np.ndarray:
        """Load image and convert to OpenCV format"""
        try:
            # Load with PIL first to handle EXIF orientation
            pil_image = Image.open(image_path)
            pil_image = ImageOps.exif_transpose(pil_image)  # Auto-correct rotation
            
            # Convert to RGB then to OpenCV BGR format
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert PIL to numpy array (RGB)
            np_image = np.array(pil_image)
            
            # Convert RGB to BGR for OpenCV
            cv_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
            
            logger.debug(f"Image loaded: {cv_image.shape}")
            return cv_image
            
        except Exception as e:
            raise OCRError(f"Failed to load image {image_path}: {e}")
    
    def _auto_deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Optional: Auto-deskew image based on text lines
        For now, return image unchanged - can enhance later
        """
        # TODO: Implement deskewing using HoughLines if needed
        return image
    
    def _crop_portraits_table(self, image: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
        """
        Crop region of interest containing the PORTRAITS table
        Uses template matching or hardcoded coordinates
        """
        height, width = image.shape[:2]
        
        # Strategy 1: Try to find "PORTRAITS" text to locate table
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        try:
            # Quick OCR to find "PORTRAITS" text
            portraits_config = "--psm 6 --oem 3"
            data = pytesseract.image_to_data(gray, config=portraits_config, output_type=pytesseract.Output.DICT)
            
            portraits_bbox = None
            for i, text in enumerate(data['text']):
                if text.strip().upper() == 'PORTRAITS':
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    portraits_bbox = (x, y, w, h)
                    logger.debug(f"Found PORTRAITS at: {portraits_bbox}")
                    break
            
            if portraits_bbox:
                # Expand ROI to include full table below PORTRAITS header
                x, y, w, h = portraits_bbox
                roi_x1 = max(0, x - 50)  # Expand left
                roi_y1 = y  # Start at PORTRAITS header
                roi_x2 = min(width, x + w + 400)  # Expand right to include image codes
                roi_y2 = min(height, y + 600)  # Expand down to capture table rows
                
                roi_bbox = (roi_x1, roi_y1, roi_x2 - roi_x1, roi_y2 - roi_y1)
                roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]
                
                logger.info(f"PORTRAITS table found and cropped: {roi_bbox}")
                return roi_image, roi_bbox
        
        except Exception as e:
            logger.warning(f"Template matching failed: {e}")
        
        # Strategy 2: Fallback to estimated coordinates for FileMaker layout
        # Based on typical FileMaker window layout
        roi_x1 = int(width * 0.02)  # Left margin
        roi_y1 = int(height * 0.35)  # Below top toolbar area
        roi_x2 = int(width * 0.98)  # Right margin
        roi_y2 = int(height * 0.90)  # Above bottom
        
        roi_bbox = (roi_x1, roi_y1, roi_x2 - roi_x1, roi_y2 - roi_y1)
        roi_image = image[roi_y1:roi_y2, roi_x1:roi_x2]
        
        logger.info(f"Using fallback ROI coordinates: {roi_bbox}")
        return roi_image, roi_bbox
    
    def _preprocess_for_ocr(self, image: np.ndarray, work_dir: Path) -> np.ndarray:
        """
        Apply image preprocessing to enhance OCR accuracy
        Steps 60-66: Grayscale, contrast, threshold, noise removal, scaling
        """
        # Step 60: Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Step 61: Apply contrast enhancement (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Step 62: Apply adaptive threshold for high contrast text
        # Using adaptive mean threshold works well for FileMaker's beige background
        thresh = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Step 63: Remove noise with morphological operations
        kernel = np.ones((1, 1), np.uint8)
        denoised = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Step 64: Scale up for better OCR (2x)
        height, width = denoised.shape
        scaled = cv2.resize(denoised, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
        
        # Save debug images
        cv2.imwrite(str(work_dir / "debug_gray.png"), gray)
        cv2.imwrite(str(work_dir / "debug_enhanced.png"), enhanced)
        cv2.imwrite(str(work_dir / "debug_thresh.png"), thresh)
        cv2.imwrite(str(work_dir / "debug_final.png"), scaled)
        
        logger.debug(f"Preprocessing complete: {scaled.shape}")
        return scaled
    
    def _run_tesseract_ocr(self, image: np.ndarray, work_dir: Path) -> OCRResult:
        """
        Run Tesseract OCR on preprocessed image
        Steps 68-73: Full text extraction and word-level data
        """
        try:
            # Step 68: Run full OCR for text extraction
            raw_text = pytesseract.image_to_string(image, config=self.general_config)
            
            # Step 68: Get word-level data with bounding boxes and confidence
            word_data = pytesseract.image_to_data(
                image, 
                config=self.general_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Parse word data
            words = []
            confidences = []
            
            for i in range(len(word_data['text'])):
                text = word_data['text'][i].strip()
                conf = word_data['conf'][i]
                
                if text and conf > 0:  # Filter out empty text and invalid confidence
                    bbox = (
                        word_data['left'][i],
                        word_data['top'][i], 
                        word_data['width'][i],
                        word_data['height'][i]
                    )
                    words.append(OCRWord(text, conf, bbox))
                    confidences.append(conf)
            
            # Step 75: Process lines
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            
            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Step 72: Check OCR quality
            if avg_confidence < self.config.OCR_MIN_CONFIDENCE:
                logger.warning(f"Low OCR confidence: {avg_confidence:.1f}% < {self.config.OCR_MIN_CONFIDENCE}%")
            
            # Save OCR outputs for debugging
            with open(work_dir / "ocr_raw_text.txt", 'w', encoding='utf-8') as f:
                f.write(raw_text)
            
            with open(work_dir / "ocr_lines.txt", 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(f"{line}\n")
            
            logger.info(f"OCR extracted {len(words)} words, {len(lines)} lines")
            
            return OCRResult(
                raw_text=raw_text,
                lines=lines,
                words=words,
                confidence_avg=avg_confidence,
                roi_bbox=None  # Will be set by caller
            )
            
        except Exception as e:
            raise OCRError(f"Tesseract OCR failed: {e}")
    
    def test_tesseract_installation(self) -> bool:
        """Test if Tesseract is properly installed and accessible"""
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
            return True
        except Exception as e:
            logger.error(f"Tesseract test failed: {e}")
            return False 