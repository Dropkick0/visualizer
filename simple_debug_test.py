#!/usr/bin/env python3
"""
Simple debug test to see what OCR text is being extracted
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import load_config
from app.ocr_windows import WindowsOCR

def test_ocr_extraction():
    """Test OCR extraction to see what text is detected"""
    print("🔍 Testing OCR on Updated Screenshot")
    print("=" * 50)
    
    screenshot_path = Path("Test_Full_Screenshot.png")
    if not screenshot_path.exists():
        print(f"❌ Screenshot not found: {screenshot_path}")
        return
    
    try:
        # Initialize OCR
        config = load_config()
        ocr = WindowsOCR(config)
        
        # Process screenshot
        work_dir = Path("tmp")
        work_dir.mkdir(exist_ok=True)
        
        print("📸 Processing screenshot...")
        result = ocr.process_screenshot(screenshot_path, work_dir)
        
        if hasattr(result, 'raw_text'):
            print(f"✅ OCR Success! Extracted {len(result.raw_text)} characters")
            print(f"📊 Lines: {len(result.lines)}, Words: {len(result.words)}")
            print(f"🎯 Average confidence: {result.confidence_avg:.1f}%")
            
            print("\n📝 RAW OCR TEXT:")
            print("-" * 60)
            print(result.raw_text)
            print("-" * 60)
            
            # Test for FileMaker patterns
            text = result.raw_text
            has_field_order = "Field Order File" in text
            has_master_order = "Master Order File" in text
            has_item_entry = "Item Entry" in text
            has_wish_list = "Wish List" in text
            has_portraits = "PORTRAITS" in text.upper()
            
            print(f"\n🔍 VALIDATION CHECKS:")
            print(f"  Field Order File: {'✅' if has_field_order else '❌'}")
            print(f"  Master Order File: {'✅' if has_master_order else '❌'}")
            print(f"  Item Entry: {'✅' if has_item_entry else '❌'}")
            print(f"  Wish List: {'✅' if has_wish_list else '❌'}")
            print(f"  PORTRAITS section: {'✅' if has_portraits else '❌'}")
            
            # Look for numbers that might be codes
            import re
            four_digit_codes = re.findall(r'\b(\d{4})\b', text)
            three_digit_codes = re.findall(r'\b(\d{3})\b', text)
            
            print(f"\n🔢 FOUND CODES:")
            print(f"  4-digit codes: {four_digit_codes}")
            print(f"  3-digit codes: {three_digit_codes}")
            
            # Look for product descriptions
            product_keywords = ['basic', 'prestige', 'keepsake', 'trio', 'portrait', 'wallet', 'frame']
            found_keywords = [kw for kw in product_keywords if kw.lower() in text.lower()]
            print(f"  Product keywords: {found_keywords}")
            
        else:
            print("❌ OCR failed - no text extracted")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ocr_extraction()
    input("\nPress Enter to exit...") 