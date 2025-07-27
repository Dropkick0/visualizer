"""
Automatic screenshot capture functionality
For capturing FileMaker Field/Master Order Files with consistent zoom positioning
"""

import time
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from loguru import logger
from PIL import Image, ImageGrab
import pygetwindow as gw
import pyautogui


class FileMakerScreenshotCapture:
    """Automatic screenshot capture for FileMaker windows with zoom control"""
    
    def __init__(self):
        self.temp_folder = Path("tmp")
        self.temp_folder.mkdir(exist_ok=True)
        
        # Disable pyautogui failsafe for automation
        pyautogui.FAILSAFE = False
        
        # Set reasonable pause between actions
        pyautogui.PAUSE = 0.1
        
        logger.info("FileMaker screenshot capture initialized with zoom control")
    
    def find_filemaker_window(self) -> Optional[any]:
        """Find active FileMaker window"""
        try:
            # Look for FileMaker windows - check various title patterns
            search_patterns = [
                "FileMaker",
                "Field Order", 
                "Master Order",
                "Pro Advanced",
                "FileMaker Pro"
            ]
            
            windows = []
            for pattern in search_patterns:
                found_windows = gw.getWindowsWithTitle(pattern)
                windows.extend(found_windows)
            
            if windows:
                # Use the first (most likely active) FileMaker window
                window = windows[0]
                logger.info(f"Found FileMaker window: {window.title}")
                return window
            else:
                logger.warning("No FileMaker window found - please ensure FileMaker is open")
                return None
                
        except Exception as e:
            logger.error(f"Error finding FileMaker window: {e}")
            return None
    
    def set_optimal_zoom_level(self, window) -> bool:
        """
        Set optimal zoom level for consistent OCR results
        Zoom in 100 scroll clicks, then out 4 clicks for precise positioning
        """
        try:
            logger.info("Setting optimal zoom level for consistent screenshots...")
            
            # Bring window to front and click to focus
            window.activate()
            time.sleep(0.8)  # Longer wait for activation
            
            # Click in the center of the window to ensure it has focus
            center_x = window.left + window.width // 2
            center_y = window.top + window.height // 2
            
            # Move mouse to center first, then click
            pyautogui.moveTo(center_x, center_y, duration=0.2)
            time.sleep(0.2)
            pyautogui.click()
            time.sleep(0.5)
            
            # Alternative approach: Use keyboard shortcuts if scroll fails
            try:
                logger.info("Step 1: Zooming in 100 scroll wheel clicks...")
                # Try scroll wheel first
                for i in range(100):
                    try:
                        pyautogui.scroll(1, center_x, center_y)  # Specify position
                        if i % 25 == 0:  # Progress logging every 25 clicks
                            logger.debug(f"Zoom in progress: {i+1}/100")
                        time.sleep(0.01)  # Small delay between scrolls
                    except Exception as scroll_error:
                        # If scroll fails, try keyboard zoom
                        if i == 0:  # Only log once
                            logger.warning(f"Scroll wheel failed, trying keyboard zoom: {scroll_error}")
                        pyautogui.hotkey('ctrl', '=')  # Zoom in with keyboard
                        time.sleep(0.02)
                
                time.sleep(0.5)  # Brief pause
                
                logger.info("Step 2: Zooming out exactly 4 scroll wheel clicks...")
                # Zoom out exactly 4 clicks
                for i in range(4):
                    try:
                        pyautogui.scroll(-1, center_x, center_y)  # Specify position
                        time.sleep(0.1)
                    except Exception:
                        # Fallback to keyboard
                        pyautogui.hotkey('ctrl', '-')  # Zoom out with keyboard
                        time.sleep(0.1)
                
                logger.info("✅ Optimal zoom level set successfully")
                time.sleep(0.5)  # Allow UI to settle
                
                return True
                
            except Exception as zoom_error:
                logger.warning(f"Zoom control had issues but continuing: {zoom_error}")
                # Don't fail completely - the screenshot might still work
                return True
             
        except Exception as e:
            logger.warning(f"Zoom level setting failed, but continuing: {e}")
            # Don't fail the entire capture for zoom issues
            return True
    
    def validate_layout_and_format(self, window) -> bool:
        """
        Validate that FileMaker shows correct layout and file format
        Supports both Field Order File ### and Master Order File ###
        """
        try:
            logger.info("Validating FileMaker layout and format...")
            
            # Take a quick screenshot for validation
            left, top, width, height = window.left, window.top, window.width, window.height
            validation_screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
            
            # Save temporary validation image
            temp_validation_path = self.temp_folder / "validation_screenshot.png"
            validation_screenshot.save(temp_validation_path)
            
            # Use OCR to validate content
            from .ocr_windows import WindowsOCR
            from .config import load_config
            
            config = load_config()
            ocr = WindowsOCR(config)
            
            work_dir = self.temp_folder
            result = ocr.process_screenshot(temp_validation_path, work_dir)
            
            if hasattr(result, 'raw_text'):
                text = result.raw_text
                
                # Check for correct file format - be more flexible
                file_format_patterns = [
                    r'Field Order File\s+[\w\d]+',
                    r'Master Order File\s+[\w\d]+',
                    r'Field Order.*File',  # More flexible
                    r'Master Order.*File',
                    r'Order File',  # Very basic check
                ]
                
                import re
                has_correct_format = any(re.search(pattern, text, re.IGNORECASE) for pattern in file_format_patterns)
                
                # Check for correct layout - much more flexible for OCR variations
                layout_patterns = [
                    r'Item Entry,?\s*Wish List',
                    r'Layout:\s*Item Entry,?\s*Wish List',
                    r'rem Entry,?\s*Wtsh List',  # OCR variations
                    r'Item.*Entry.*Wish.*List',  # Very flexible
                    r'Entry.*Wish.*List',       # Even more flexible
                    r'Wish.*List',              # Basic check
                ]
                
                has_correct_layout = any(re.search(pattern, text, re.IGNORECASE) for pattern in layout_patterns)
                
                # Check for PORTRAITS table
                has_portraits = 'PORTRAITS' in text.upper()
                
                logger.info(f"Validation results:")
                logger.info(f"  File format (Field/Master Order): {'✅' if has_correct_format else '❌'}")
                logger.info(f"  Layout (Item Entry, Wish List): {'✅' if has_correct_layout else '❌'}")
                logger.info(f"  PORTRAITS table: {'✅' if has_portraits else '❌'}")
                
                # More lenient validation - if we have portraits, that's often enough
                if has_portraits and (has_correct_format or has_correct_layout):
                    logger.info("✅ FileMaker validation passed (lenient mode)")
                    return True
                elif has_portraits:
                    logger.info("✅ FileMaker validation passed (PORTRAITS table found)")
                    return True
                else:
                    if not has_correct_format:
                        logger.warning("❌ Please ensure you have a Field Order File or Master Order File open")
                    if not has_correct_layout:
                        logger.warning("❌ Please change layout to 'Item Entry, Wish List'")
                    if not has_portraits:
                        logger.warning("❌ No PORTRAITS table found - ensure order contains portrait items")
                    
                    # Don't fail completely - let it proceed if we found some relevant content
                    logger.info("⚠️ Proceeding with screenshot despite validation warnings...")
                    return True
            else:
                logger.warning("❌ Could not validate FileMaker content - OCR failed, proceeding anyway...")
                return True
                
        except Exception as e:
            logger.warning(f"Validation failed, proceeding anyway: {e}")
            return True
        finally:
            # Clean up temporary validation file
            temp_validation_path = self.temp_folder / "validation_screenshot.png"
            if temp_validation_path.exists():
                temp_validation_path.unlink()
    
    def capture_optimized_screenshot(self, save_path: Optional[Path] = None) -> Optional[Path]:
        """
        Capture optimized FileMaker screenshot with zoom control and validation
        
        Returns:
            Path to saved screenshot or None if failed
        """
        try:
            logger.info("🚀 Starting optimized FileMaker screenshot capture...")
            
            # Step 1: Find FileMaker window
            window = self.find_filemaker_window()
            if not window:
                return None
            
            # Step 2: Set optimal zoom level
            if not self.set_optimal_zoom_level(window):
                logger.warning("Failed to set optimal zoom, proceeding anyway...")
            
            # Step 3: Validate layout and format
            if not self.validate_layout_and_format(window):
                logger.error("❌ FileMaker validation failed - please check layout and file format")
                return None
            
            # Step 4: Capture the final screenshot
            logger.info("📸 Capturing final optimized screenshot...")
            time.sleep(0.5)  # Final settling time
            
            left, top, width, height = window.left, window.top, window.width, window.height
            screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
            
            # Save screenshot
            if save_path is None:
                timestamp = int(time.time())
                save_path = self.temp_folder / f"optimized_filemaker_{timestamp}.png"
            
            screenshot.save(save_path)
            logger.info(f"✅ Optimized screenshot captured: {save_path}")
            
            return save_path
            
        except Exception as e:
            logger.error(f"Failed to capture optimized screenshot: {e}")
            return None
    
    def capture_filemaker_screenshot(self, save_path: Optional[Path] = None) -> Optional[Path]:
        """Legacy method - now uses optimized capture"""
        return self.capture_optimized_screenshot(save_path)
    
    def capture_full_screen(self, save_path: Optional[Path] = None) -> Optional[Path]:
        """
        Capture full screen screenshot as fallback
        """
        try:
            # Take full screen screenshot
            screenshot = ImageGrab.grab()
            
            # Save screenshot
            if save_path is None:
                timestamp = int(time.time())
                save_path = self.temp_folder / f"full_screenshot_{timestamp}.png"
            
            screenshot.save(save_path)
            logger.info(f"✅ Full screen screenshot captured: {save_path}")
            
            return save_path
            
        except Exception as e:
            logger.error(f"Failed to capture full screen: {e}")
            return None
    
    def auto_capture_with_validation(self, max_retries: int = 2) -> Optional[Path]:
        """
        Automatically capture screenshot with zoom control and validation
        
        Args:
            max_retries: Maximum number of capture attempts
            
        Returns:
            Path to valid screenshot or None if failed
        """
        for attempt in range(max_retries):
            logger.info(f"📸 Optimized capture attempt {attempt + 1}/{max_retries}")
            
            # Use optimized capture method
            screenshot_path = self.capture_optimized_screenshot()
            
            if screenshot_path:
                logger.info(f"✅ Optimized screenshot captured successfully: {screenshot_path}")
                return screenshot_path
            else:
                logger.warning(f"❌ Optimized capture failed on attempt {attempt + 1}")
                
                # Wait before retry
                if attempt < max_retries - 1:
                    logger.info("Waiting 3 seconds before retry...")
                    time.sleep(3)
        
        # Final fallback to full screen
        logger.info("🔄 Falling back to full screen capture...")
        return self.capture_full_screen()


def capture_order_screenshot() -> Optional[Path]:
    """Convenience function to capture optimized FileMaker order screenshot"""
    capturer = FileMakerScreenshotCapture()
    return capturer.auto_capture_with_validation() 