#!/usr/bin/env python3
"""
Test OCR on the actual FileMaker screenshot
"""

import sys
from pathlib import Path
from PIL import Image
import winocr

def test_filemaker_screenshot():
    """Test OCR on the actual FileMaker screenshot"""
    
    screenshot_path = Path("Test_Full_Screenshot.png")
    if not screenshot_path.exists():
        print(f"❌ Screenshot not found: {screenshot_path}")
        return False
    
    print("🔍 Testing OCR on FileMaker screenshot...")
    print("=" * 60)
    
    try:
        # Load the image
        image = Image.open(screenshot_path)
        print(f"✅ Loaded image: {image.size}")
        
        # Run Windows OCR
        result = winocr.recognize_pil_sync(image, 'en-US')
        
        print("\n📝 Raw OCR Text:")
        print("-" * 40)
        print(result['text'])
        print("-" * 40)
        
        # Split into lines
        lines = [line.strip() for line in result['text'].split('\n') if line.strip()]
        print(f"\n📋 Detected {len(lines)} text lines:")
        
        # Look for PORTRAITS table data
        portraits_section = False
        portrait_lines = []
        
        for i, line in enumerate(lines):
            print(f"{i+1:2d}: {line}")
            
            if 'PORTRAITS' in line.upper():
                portraits_section = True
                print("    ↑ PORTRAITS header found")
            
            elif portraits_section and any(char.isdigit() for char in line):
                # Check if this looks like a portrait line (has numbers)
                if any(keyword in line.lower() for keyword in ['basic', 'trio', 'wallet', 'x', 'portrait']):
                    portrait_lines.append(line)
                    print(f"    ↑ Portrait line detected")
        
        print(f"\n🎯 Found {len(portrait_lines)} potential portrait lines:")
        for i, line in enumerate(portrait_lines):
            print(f"  {i+1}: {line}")
        
        # Test parsing with our parser
        print(f"\n🔧 Testing with FileMaker parser...")
        
        sys.path.insert(0, str(Path(__file__).parent))
        from app.parse import FileMakerParser
        from app.config import load_config
        
        # Load config
        config = load_config()
        parser = FileMakerParser(config.products)
        
        # Try parsing the lines
        parsed_items = parser.parse_ocr_lines(lines)
        
        print(f"✅ Parser processed {len(parsed_items)} items:")
        for item in parsed_items:
            print(f"  - {item.product_slug}: qty={item.quantity}, codes={item.codes}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_filemaker_screenshot()
    print(f"\n{'✅ Test completed successfully' if success else '❌ Test failed'}")
    input("\nPress Enter to exit...") 