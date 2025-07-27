#!/usr/bin/env python3
"""
Test the FileMaker parsing functionality with the updated configuration
"""

import sys
from pathlib import Path
from PIL import Image
import winocr

def test_parsing_logic():
    """Test the parsing logic with known OCR text"""
    
    # Sample OCR text based on what we detected
    sample_ocr_text = """Field Order File 1 10 25 File Edit View Insert Format Records 1/ 10 Found (Unsorted) Records Scripts Window Help Show All New Record Delete Record Find Layout: Item Entry, Wish List Virtual C uanfity 12 3 3 Receipt View As: Touchup Frames Item Entry Directory Pose Sort 1555 001 200 570 350 810 1020.5 510B 013 1620 2024 Complimentary 8x10 BASIC COLOR PORTRAITS heet of 8 wallets air 5x7 BASIC 5" x 5" BASIC 1 sheet of 4 XIO BASIC ox20 TRIO PORTRAIT black digital mat, cherry frame x 10 triple opening with BLACK digital mat and cherry frame images and sequence 1555 1555 1555 1555 1555, 9198, 5615 1555, 9198 1555 9999 toolbar DIGITAL IMAGES? quantity frame FRAMES number re WITHOUT GLASS 5615, 9198 x 7 cherry frame P360CHRsn-GVEBHB x 10 black frame P360BLK8x10-GVE8Ha 10 13 black frame 360BLK1dÅ13-MBTS ox13 BASIC 6x20 BASIC ox24 BASIC Q Search x 11:50 AM 7/16/2025"""
    
    print("🔧 Testing FileMaker parsing logic...")
    print("=" * 60)
    
    try:
        # Load our modules
        sys.path.insert(0, str(Path(__file__).parent))
        from app.parse import FileMakerParser
        from app.config import load_product_config
        
        # Load product configurations directly
        products = load_product_config()
        print(f"✅ Loaded {len(products)} product configurations")
        
        # Print some product configurations
        print("\n📋 Available products:")
        for slug, product in list(products.items())[:5]:  # Show first 5
            print(f"  - {slug}: {getattr(product, 'name', 'No name')} (code: {getattr(product, 'code', 'No code')})")
        
        # Initialize parser
        parser = FileMakerParser(products)
        
        # Parse the OCR text
        print(f"\n🔧 Parsing OCR text...")
        parsed_items = parser.parse_ocr_lines([sample_ocr_text])
        
        print(f"\n✅ Parser found {len(parsed_items)} items:")
        for item in parsed_items:
            print(f"  - {item.product_slug}: qty={item.quantity}, codes={item.codes}")
            if item.warnings:
                print(f"    Warnings: {item.warnings}")
        
        # Test specific patterns that should be in the text
        print(f"\n🎯 Testing specific patterns:")
        
        # Look for the product codes we know are in the screenshot
        expected_items = [
            ("12", "200", "wallets"),  # 12 200 sheet of 8 wallets - 1555
            ("1", "570", "5x7 basic"),   # 1 570 pair 5x7 BASIC - 1555  
            ("3", "350", "3.5x5"),       # 3 350 3.5" x 5" BASIC 1 sheet of 4 - 1555
            ("1", "810", "8x10 basic"),  # 1 810 8x10 BASIC - 1555
            ("1", "1020.5", "trio"),     # 1 1020.5 10x20 TRIO PORTRAIT - 1555, 9198, 5615
            ("3", "510", "triple"),      # 3 510.3 5x10 triple opening - 5615, 1555, 9198
            ("1", "1013", "10x13"),      # 1 1013 10x13 BASIC - 9198
            ("1", "1620", "16x20"),      # 1 1620 16x20 BASIC - 1555
            ("1", "2024", "20x24"),      # 1 2024 20x24 BASIC - 9999
        ]
        
        for qty, code, description in expected_items:
            found = any(item.product_slug.find(code.replace(".", "_")) >= 0 for item in parsed_items)
            print(f"  {qty} x {code} ({description}): {'✅ Found' if found else '❌ Missing'}")
        
        # Also test for the specific codes in the OCR text
        print(f"\n🔍 Looking for image codes in OCR text...")
        import re
        codes_in_text = re.findall(r'\b(\d{4})\b', sample_ocr_text)
        print(f"Found codes: {list(set(codes_in_text))}")
        
        return len(parsed_items) > 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_image_folder_scanning():
    """Test image folder scanning functionality"""
    print(f"\n📁 Testing image folder scanning...")
    
    # Test the Dropbox folder path
    dropbox_path = Path("C:/Users/remem/Re MEMBER Dropbox/PHOTOGRAPHY PROOFING/PHOTOGRAPHER UPLOADS (1)/Ethan/From/8017 Lab Order/Lab Order TU Only")
    
    if dropbox_path.exists():
        print(f"✅ Dropbox folder found: {dropbox_path}")
        
        # Look for images with specific codes
        test_codes = ["1555", "9198", "5615", "9999"]
        
        for code in test_codes:
            matching_files = []
            for ext in [".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
                pattern = f"*{code}*{ext}"
                matches = list(dropbox_path.rglob(pattern))
                matching_files.extend(matches)
            
            if matching_files:
                print(f"  Code {code}: ✅ Found {len(matching_files)} images")
                for img in matching_files[:2]:  # Show first 2
                    print(f"    - {img.name}")
            else:
                print(f"  Code {code}: ❌ No images found")
    else:
        print(f"❌ Dropbox folder not found: {dropbox_path}")
        print("This may be expected if running on a different machine")

if __name__ == "__main__":
    print("🎨 FileMaker Parsing Test Suite")
    print("=" * 60)
    
    success = test_parsing_logic()
    test_image_folder_scanning()
    
    print(f"\n{'✅ Test completed successfully' if success else '❌ Test failed'}")
    input("\nPress Enter to exit...") 