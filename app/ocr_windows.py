"""
Windows OCR processing module for FileMaker Field Order screenshots
Uses Windows built-in OCR instead of Tesseract for better deployment
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple
from PIL import Image, ImageOps
from loguru import logger
import asyncio

# Import Windows OCR library
try:
    import winocr
    WINOCR_AVAILABLE = True
except ImportError:
    WINOCR_AVAILABLE = False
    logger.warning("winocr not available")

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


class WindowsOCR:
    """OCR processor using Windows built-in OCR capabilities"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.language = "en-US"  # Default to English, could be configurable
        
        if not WINOCR_AVAILABLE:
            logger.warning("Windows OCR not available")
        
        logger.info(f"Windows OCR initialized for language: {self.language}")
    
    def process_screenshot(self, image_path: Path, work_dir: Path) -> OCRResult:
        """
        Main OCR processing pipeline for FileMaker screenshots using Windows OCR
        """
        logger.info(f"Processing screenshot with Windows OCR: {image_path}")
        
        try:
            # Load and normalize image
            original_image = self._load_and_normalize_image(image_path)
            
            # Auto-deskew (optional for now)
            deskewed_image = self._auto_deskew(original_image)
            
            # Crop region of interest to PORTRAITS table
            roi_image, roi_bbox = self._crop_portraits_table(deskewed_image)
            
            # Save debug images
            debug_roi_path = work_dir / "debug_roi.png"
            cv2.imwrite(str(debug_roi_path), roi_image)
            logger.debug(f"ROI saved to: {debug_roi_path}")
            
            # Preprocess for OCR
            processed_image = self._preprocess_for_ocr(roi_image, work_dir)
            
            # Run Windows OCR
            ocr_result = self._run_windows_ocr(processed_image, work_dir)
            
            # Add ROI information to result
            final_result = OCRResult(
                raw_text=ocr_result.raw_text,
                lines=ocr_result.lines, 
                words=ocr_result.words,
                confidence_avg=ocr_result.confidence_avg,
                roi_bbox=roi_bbox
            )
            
            logger.info(f"Windows OCR completed - {len(final_result.lines)} lines, "
                       f"avg confidence: {final_result.confidence_avg:.1f}%")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Windows OCR processing failed: {e}")
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
        return image
    
    def _crop_portraits_table(self, image: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
        """
        Locate and crop the PORTRAITS table for better OCR accuracy
        Uses strategic bounding boxes to capture different sections
        Returns cropped image and bbox coordinates (x1, y1, x2, y2)
        """
        try:
            # Convert to grayscale for text detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            
            # Try to detect "PORTRAITS" text more precisely using OCR
            pil_image = Image.fromarray(cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB))
            
            portraits_bbox = None
            try:
                import winocr
                # Quick OCR to find PORTRAITS location
                ocr_result = winocr.recognize_pil_sync(pil_image, 'en-US')
                text = ocr_result.get('text', '') if isinstance(ocr_result, dict) else ''
                
                if 'PORTRAITS' in text.upper():
                    # Try to get word-level data if available
                    if 'lines' in ocr_result:
                        for line in ocr_result['lines']:
                            if 'words' in line:
                                for word in line['words']:
                                    if 'PORTRAITS' in word.get('text', '').upper():
                                        bbox_data = word.get('bounding_rect', {})
                                        if bbox_data:
                                            portraits_bbox = (
                                                int(bbox_data.get('x', 0)),
                                                int(bbox_data.get('y', 0)),
                                                int(bbox_data.get('width', 0)),
                                                int(bbox_data.get('height', 0))
                                            )
                                            logger.debug(f"Found PORTRAITS text, estimated bbox: {portraits_bbox}")
                                            break
                    
                    if portraits_bbox:
                        x, y, w, h = portraits_bbox
                        
                        # STRATEGIC BOUNDING BOX - Expand to capture full table
                        # Based on FileMaker layout, expand significantly to catch all data
                        table_left = max(0, int(width * 0.01))      # Nearly full width - left edge
                        table_right = min(width, int(width * 0.99))  # Nearly full width - right edge
                        table_top = max(0, y - 20)                   # Start just above PORTRAITS header
                        table_bottom = min(height, int(height * 0.95))  # Go almost to bottom of screen
                        
                        logger.info(f"PORTRAITS table found and cropped: ({table_left}, {table_top}, {table_right}, {table_bottom})")
                        
                    else:
                        # Fallback: Use estimated coordinates based on typical FileMaker layout
                        table_left = max(0, int(width * 0.01))
                        table_right = min(width, int(width * 0.99))
                        table_top = max(0, int(height * 0.25))      # Start higher to catch header
                        table_bottom = min(height, int(height * 0.95))
                        
                        logger.info(f"Using estimated PORTRAITS table region: ({table_left}, {table_top}, {table_right}, {table_bottom})")
                
                else:
                    # No PORTRAITS found - use full screen strategy
                    table_left = max(0, int(width * 0.01))
                    table_right = min(width, int(width * 0.99))
                    table_top = max(0, int(height * 0.2))
                    table_bottom = min(height, int(height * 0.95))
                    
                    logger.warning(f"PORTRAITS text not found, using full screen strategy: ({table_left}, {table_top}, {table_right}, {table_bottom})")
                    
            except Exception as e:
                logger.warning(f"OCR detection failed: {e}")
                # Ultimate fallback
                table_left = max(0, int(width * 0.01))
                table_right = min(width, int(width * 0.99))
                table_top = max(0, int(height * 0.25))
                table_bottom = min(height, int(height * 0.95))
                
                logger.info(f"Using fallback PORTRAITS table region: ({table_left}, {table_top}, {table_right}, {table_bottom})")
            
            # Crop the image to the calculated region
            roi_bbox = (table_left, table_top, table_right, table_bottom)
            cropped = image[table_top:table_bottom, table_left:table_right]
            
            # Save debug cropped image to help with tuning
            debug_crop_path = Path("tmp") / "debug_portraits_crop.png"
            cv2.imwrite(str(debug_crop_path), cropped)
            logger.debug(f"Debug cropped PORTRAITS table saved to: {debug_crop_path}")
            
            return cropped, roi_bbox
            
        except Exception as e:
            logger.warning(f"Could not crop PORTRAITS table: {e}")
            # Return full image if cropping fails
            height, width = image.shape[:2]
            return image, (0, 0, width, height)
    
    def _preprocess_for_ocr(self, image: np.ndarray, work_dir: Path) -> np.ndarray:
        """
        Apply image preprocessing to enhance OCR accuracy
        Windows OCR works well with good contrast images
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply contrast enhancement (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Apply adaptive threshold for high contrast text
        thresh = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Remove noise with morphological operations
        kernel = np.ones((1, 1), np.uint8)
        denoised = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Scale up for better OCR (2x) - Windows OCR benefits from higher resolution
        height, width = denoised.shape
        scaled = cv2.resize(denoised, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
        
        # Save debug images
        cv2.imwrite(str(work_dir / "debug_gray.png"), gray)
        cv2.imwrite(str(work_dir / "debug_enhanced.png"), enhanced)
        cv2.imwrite(str(work_dir / "debug_thresh.png"), thresh)
        cv2.imwrite(str(work_dir / "debug_final.png"), scaled)
        
        logger.debug(f"Preprocessing complete: {scaled.shape}")
        return scaled
    
    def _run_windows_ocr(self, image: np.ndarray, work_dir: Path) -> OCRResult:
        """
        Run Windows OCR on preprocessed image
        """
        try:
            if not WINOCR_AVAILABLE:
                raise OCRError(
                    "winocr not available; install it or enable Windows OCR."
                )
            
            # Convert OpenCV image to PIL for Windows OCR
            if len(image.shape) == 3:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            
            pil_image = Image.fromarray(rgb_image)
            
            # Run Windows OCR
            result = winocr.recognize_pil_sync(pil_image, self.language)
            
            # Extract text and lines
            raw_text = result['text']
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            
            # Parse word data with bounding boxes and confidence
            words = []
            confidences = []
            
            # For winocr sync version, we get a simpler structure
            if 'lines' in result:
                for line in result['lines']:
                    if 'words' in line:
                        for word in line['words']:
                            if word.get('text', '').strip():
                                # Convert Windows OCR bounding rect to our format
                                bbox_data = word.get('bounding_rect', {})
                                bbox = (
                                    int(bbox_data.get('x', 0)),
                                    int(bbox_data.get('y', 0)),
                                    int(bbox_data.get('width', 0)),
                                    int(bbox_data.get('height', 0))
                                )
                                # Windows OCR doesn't provide confidence per word, use a default high value
                                confidence = 90.0
                                words.append(OCRWord(word['text'].strip(), confidence, bbox))
                                confidences.append(confidence)
            else:
                # Fallback: create word objects from text parsing
                word_texts = raw_text.split()
                for i, word_text in enumerate(word_texts):
                    if word_text.strip():
                        # Estimate bounding box
                        bbox = (i * 50, 0, 50, 20)
                        confidence = 85.0
                        words.append(OCRWord(word_text.strip(), confidence, bbox))
                        confidences.append(confidence)
            
            # Calculate average confidence (high for Windows OCR)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 85.0
            
            # Check OCR quality
            if avg_confidence < self.config.OCR_MIN_CONFIDENCE:
                logger.warning(f"OCR confidence: {avg_confidence:.1f}% < {self.config.OCR_MIN_CONFIDENCE}%")
            
            # Save OCR outputs for debugging
            with open(work_dir / "ocr_raw_text.txt", 'w', encoding='utf-8') as f:
                f.write(raw_text)
            
            with open(work_dir / "ocr_lines.txt", 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(f"{line}\n")
            
            logger.info(f"Windows OCR extracted {len(words)} words, {len(lines)} lines")
            
            return OCRResult(
                raw_text=raw_text,
                lines=lines,
                words=words,
                confidence_avg=avg_confidence,
                roi_bbox=None  # Will be set by caller
            )
            
        except Exception as e:
            raise OCRError(f"Windows OCR failed: {e}")
    
    
    def test_windows_ocr_installation(self) -> bool:
        """Test if Windows OCR is available and working"""
        try:
            if not WINOCR_AVAILABLE:
                logger.error("winocr library not installed")
                return False
            
            # Test with a simple image using sync version
            test_image = Image.new('RGB', (100, 50), color='white')
            
            # Try to run OCR using sync version
            result = winocr.recognize_pil_sync(test_image, self.language)
            logger.info("Windows OCR test successful")
            return True
        except Exception as e:
            logger.error(f"Windows OCR test failed: {e}")
            return False


# Alias for compatibility with existing code
FileMakerOCR = WindowsOCR 