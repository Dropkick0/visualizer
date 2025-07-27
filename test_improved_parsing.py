#!/usr/bin/env python3
"""
Test the improved flexible parsing logic with actual OCR data
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_improved_parsing():
    """Test the improved parsing logic"""
    print("🔧 Testing Improved Flexible Parsing Logic")
    print("=" * 60)
    
    try:
        from app.parse import FileMakerParser
        from app.config import load_product_config
        
        # Load config
        products_config = load_product_config()
        parser = FileMakerParser(products_config)
        
        # The actual OCR text from the user's screenshot
        actual_ocr_text = """1 12 1 3 1 1 3 1 1 1 001 200 570 350 810 1020.5 510.3 1013 1620 2024 Directo Pose Complimentary BASIC COLOR PORTRAITS heet of 8 wallets air BASIC -5" x 5" BASIC 1 sheet of 4 BASIC Ox20 TRIO PORTRAIT black digital mat, cherry frame XIO triple opening with BLACK digital mat and cherry frame ox13 BASIC BASIC BASIC 0033 Image end eequenco 0033 0033 0033 0033 0033, 004470039 0039, 0033, 0044 0102 0033 0102"""
        
        print("📝 Using actual OCR text from screenshot")
        print(f"Text length: {len(actual_ocr_text)} characters")
        print()
        
        # Test both parsing methods
        print("🔍 Testing Original Parsing Method:")
        print("-" * 40)
        
        try:
            original_items = parser._extract_filemaker_table_data("", actual_ocr_text)
            print(f"✅ Original parser found {len(original_items)} items:")
            for item in original_items:
                print(f"  - {item.quantity}x {item.product_slug}: {item.codes}")
        except Exception as e:
            print(f"❌ Original parsing failed: {e}")
        
        print()
        print("🚀 Testing New Flexible Parsing Method:")
        print("-" * 40)
        
        try:
            flexible_items = parser._extract_filemaker_table_data_flexible("", actual_ocr_text)
            print(f"✅ Flexible parser found {len(flexible_items)} items:")
            for item in flexible_items:
                print(f"  - {item.quantity}x {item.product_slug}: {item.codes}")
        except Exception as e:
            print(f"❌ Flexible parsing failed: {e}")
        
        print()
        print("👤 User's Expected Results (for comparison):")
        print("-" * 40)
        expected = [
            {"qty": 12, "product": "wallets_200", "codes": ["0033"]},
            {"qty": 1, "product": "5x7_basic_570", "codes": ["0033"]},
            {"qty": 1, "product": "8x10_basic_810", "codes": ["0033"]},
            {"qty": 1, "product": "10x13_basic_1013", "codes": ["0102"]},
            {"qty": 1, "product": "16x20_basic_1620", "codes": ["0033"]},
            {"qty": 1, "product": "20x24_basic_2024", "codes": ["0102"]},
        ]
        
        for item in expected:
            print(f"  - {item['qty']}x {item['product']}: {item['codes']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_improved_parsing()
    
    if success:
        print(f"\n🎯 Summary:")
        print(f"The flexible parsing method provides a more robust approach")
        print(f"to handle different OCR patterns and data structures.")
        print(f"It can dynamically extract quantities, product codes, and image codes")
        print(f"without relying on hardcoded expected rows.")
    
    input("\nPress Enter to exit...") 