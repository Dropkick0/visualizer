#!/usr/bin/env python3
"""
Automated FileMaker Order Processing Workflow
1. Capture FileMaker screenshot (Field/Master Order File)
2. Process with OCR and parse order items
3. Search Dropbox folder for images using 4-digit codes
4. Generate portrait previews with found images
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import load_config, load_product_config
from app.parse import FileMakerParser
from app.ocr_windows import WindowsOCR
from app.screenshot import capture_order_screenshot
from app.image_search import create_image_searcher
from app.enhanced_preview import EnhancedPortraitPreviewGenerator


class AutomatedOrderProcessor:
    """Automated processing of FileMaker order files"""
    
    def __init__(self):
        # Load configuration
        self.config = load_config()
        self.products = load_product_config()
        
        # Initialize components
        self.ocr = WindowsOCR(self.config)
        self.parser = FileMakerParser(self.products)
        self.image_searcher = create_image_searcher(self.config)
        
        logger.info("✅ Automated order processor initialized")
    
    def process_order_automatically(self) -> bool:
        """
        Complete automated workflow:
        1. Capture screenshot
        2. Process with OCR
        3. Search for images
        4. Generate previews
        """
        logger.info("🚀 Starting automated order processing...")
        
        try:
            # Step 1: Capture FileMaker screenshot with optimal zoom
            logger.info("📸 Step 1: Capturing optimized FileMaker screenshot...")
            screenshot_path = capture_order_screenshot()
            
            if not screenshot_path:
                logger.error("❌ Failed to capture optimized screenshot")
                return False
            
            logger.info(f"✅ Optimized screenshot captured with zoom control: {screenshot_path}")
            
            # Step 2: Process with OCR
            logger.info("🔍 Step 2: Processing screenshot with OCR...")
            work_dir = Path("tmp")
            work_dir.mkdir(exist_ok=True)
            ocr_result = self.ocr.process_screenshot(screenshot_path, work_dir)
            
            # Convert OCR result to expected format
            if hasattr(ocr_result, 'raw_text'):
                ocr_dict = {
                    'success': True,
                    'text': ocr_result.raw_text
                }
            else:
                logger.error("❌ OCR failed: Invalid result format")
                return False
            
            logger.info(f"✅ OCR completed, extracted {len(ocr_dict['text'])} characters")
            
            # Step 3: Parse order items
            logger.info("📋 Step 3: Parsing order items...")
            order_items = self.parser.parse_ocr_lines([ocr_dict['text']])
            
            if not order_items:
                logger.error("❌ No valid order items found")
                return False
            
            logger.info(f"✅ Found {len(order_items)} order items:")
            for item in order_items:
                logger.info(f"  - {item.quantity}x {item.product_slug}: {item.codes}")
            
            # Step 4: Search for images in Dropbox
            logger.info("🔍 Step 4: Searching for images in Dropbox...")
            
            if not self.image_searcher:
                logger.error("❌ Image searcher not available - check Dropbox configuration")
                return False
            
            image_results = self.image_searcher.find_images_for_order_items(order_items)
            
            # Report image search results
            total_codes = sum(len(item.codes) for item in order_items)
            found_codes = 0
            
            for product_slug, code_images in image_results.items():
                for code, images in code_images.items():
                    if images:
                        found_codes += 1
                        logger.info(f"  Code {code}: ✅ {len(images)} images found")
                    else:
                        logger.warning(f"  Code {code}: ❌ No images found")
            
            logger.info(f"✅ Image search complete: {found_codes}/{total_codes} codes have images")
            
            # Step 5: Generate preview
            logger.info("🎨 Step 5: Generating portrait preview...")
            preview_result = self.generate_preview(order_items, image_results)
            
            if preview_result:
                logger.info(f"✅ Preview generated successfully: {preview_result}")
                return True
            else:
                logger.error("❌ Preview generation failed")
                return False
            
        except Exception as e:
            logger.error(f"❌ Automated processing failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_preview(self, order_items: List, image_results: Dict) -> Optional[Path]:
        """Generate enhanced portrait preview with found images and trio composites"""
        try:
            # Prepare images_found dictionary for enhanced generator
            images_found = {}
            for product_slug, code_images in image_results.items():
                for code, image_paths in code_images.items():
                    if image_paths:
                        images_found[code] = image_paths
            
            # Create enhanced preview generator
            output_dir = Path("app/static/previews")
            preview_gen = EnhancedPortraitPreviewGenerator(
                products_config=self.products,
                images_found=images_found,
                output_dir=output_dir
            )
            
            # Prepare enhanced preview items
            enhanced_items = []
            
            for item in order_items:
                # Create enhanced preview item format
                enhanced_item = {
                    'product_slug': item.product_slug,
                    'product_code': getattr(item, 'product_code', ''),
                    'quantity': item.quantity,
                    'image_codes': item.codes,  # Use codes directly
                    'frame_style': item.frame_style,
                    'orientation': item.orientation,
                    'warnings': item.warnings,
                    'size_category': self._determine_size_category(item.product_slug)
                }
                
                enhanced_items.append(enhanced_item)
            
            # Generate the enhanced preview with trio composites
            timestamp = int(time.time())
            preview_path = output_dir / f"automated_preview_with_composites_{timestamp}.png"
            
            logger.info(f"🎨 Generating enhanced preview with trio composites...")
            logger.info(f"   Items: {len(enhanced_items)}")
            logger.info(f"   Images found: {list(images_found.keys())}")
            
            success = preview_gen.generate_size_based_preview_with_composites(
                items=enhanced_items,
                output_path=preview_path
            )
            
            if success:
                logger.info(f"✅ Enhanced preview with composites generated: {preview_path}")
                return preview_path
            else:
                logger.error("❌ Failed to generate enhanced preview")
                return None
            
        except Exception as e:
            logger.error(f"Error generating enhanced preview: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _determine_size_category(self, product_slug: str) -> str:
        """Determine size category for layout purposes"""
        if 'wallet' in product_slug.lower():
            return 'wallet'
        elif 'trio' in product_slug.lower():
            # Trio products get their own special handling but are categorized as large for layout
            return 'large'  
        elif '5x7' in product_slug or '57' in product_slug:
            return 'medium'
        elif '8x10' in product_slug or '810' in product_slug:
            return 'medium'
        elif '10x13' in product_slug or '1013' in product_slug:
            return 'large'
        elif '16x20' in product_slug or '1620' in product_slug:
            return 'large'
        elif '20x24' in product_slug or '2024' in product_slug:
            return 'large'
        else:
            return 'medium'  # Default
    
    def process_manual_screenshot(self, screenshot_path: Path) -> bool:
        """Process a manually provided screenshot"""
        logger.info(f"📸 Processing manual screenshot: {screenshot_path}")
        
        if not screenshot_path.exists():
            logger.error(f"❌ Screenshot file not found: {screenshot_path}")
            return False
        
        try:
            # Skip step 1 (screenshot capture) and start from OCR
            logger.info("🔍 Processing screenshot with OCR...")
            work_dir = Path("tmp")
            work_dir.mkdir(exist_ok=True)
            ocr_result = self.ocr.process_screenshot(screenshot_path, work_dir)
            
            # Convert OCR result to expected format
            if hasattr(ocr_result, 'raw_text'):
                ocr_dict = {
                    'success': True,
                    'text': ocr_result.raw_text
                }
            else:
                logger.error("❌ OCR failed: Invalid result format")
                return False
            
            # Continue with steps 3-5
            order_items = self.parser.parse_ocr_lines([ocr_dict['text']])
            
            if not order_items:
                logger.error("❌ No valid order items found")
                return False
            
            logger.info(f"✅ Found {len(order_items)} order items")
            
            # Search for images and generate preview
            if self.image_searcher:
                image_results = self.image_searcher.find_images_for_order_items(order_items)
                preview_result = self.generate_preview(order_items, image_results)
                
                if preview_result:
                    logger.info(f"✅ Processing complete: {preview_result}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Manual processing failed: {e}")
            return False


def main():
    """Main entry point for automated workflow"""
    print("🎨 FileMaker Automated Order Processing")
    print("=" * 60)
    
    processor = AutomatedOrderProcessor()
    
    # Check if a manual screenshot was provided
    if len(sys.argv) > 1:
        screenshot_path = Path(sys.argv[1])
        success = processor.process_manual_screenshot(screenshot_path)
    else:
        # Run full automated workflow
        print("Starting automated capture and processing...")
        print("Please ensure:")
        print("1. FileMaker is open")
        print("2. Layout is set to 'Item Entry, Wish List'")
        print("3. Order file is displayed")
        print()
        
        input("Press Enter when ready to capture screenshot...")
        
        success = processor.process_order_automatically()
    
    if success:
        print("✅ Order processing completed successfully!")
    else:
        print("❌ Order processing failed. Check logs for details.")
    
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main() 