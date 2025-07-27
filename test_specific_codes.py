#!/usr/bin/env python3
"""
Test search for specific codes found in OCR: 1020, 1013
Try variations to match the actual image naming convention
"""

from pathlib import Path
import sys

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.image_search import create_image_searcher
from app.config import load_config

def test_specific_codes():
    """Test search for the specific codes found in OCR"""
    print("🔍 Testing Specific Codes: 1020, 1013")
    print("=" * 50)
    
    try:
        config = load_config()
        searcher = create_image_searcher(config)
        
        if not searcher:
            print("❌ Could not create image searcher")
            return
        
        dropbox_path = searcher.dropbox_root
        print(f"📁 Searching in: {dropbox_path}")
        
        if not dropbox_path.exists():
            print(f"❌ Dropbox folder not found: {dropbox_path}")
            return
        
        # Test the exact codes from OCR and their variations
        test_codes = [
            "1020", "1013",  # Exact codes from OCR
            "0033", "0039",  # From the _MG_ files we saw
            "33", "39",      # Without leading zeros
            "1033", "1039",  # With leading 1
            "2020", "2013",  # Alternative year patterns
        ]
        
        print(f"🔍 Testing codes and variations: {test_codes}")
        
        results = searcher.find_images_by_codes(test_codes)
        
        found_any = False
        for code, images in results.items():
            if images:
                found_any = True
                print(f"  Code {code}: ✅ Found {len(images)} images")
                for img in images[:3]:  # Show first 3
                    print(f"    - {img.name}")
            else:
                print(f"  Code {code}: ❌ No images")
        
        if not found_any:
            print(f"\n🔍 Let's check the actual file names in detail...")
            
            # Get all image files and analyze their naming patterns
            all_images = []
            for ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
                pattern = f"*{ext}"
                files = list(dropbox_path.rglob(pattern))
                all_images.extend(files)
            
            print(f"\n📂 Found {len(all_images)} total image files:")
            for img in all_images:
                print(f"  - {img.name}")
                
                # Extract numbers from filename
                import re
                numbers = re.findall(r'\d+', img.name)
                if numbers:
                    print(f"    Numbers found: {numbers}")
                    
                    # Check for last 4 digits
                    for num in numbers:
                        if len(num) >= 4:
                            last_4 = num[-4:]
                            print(f"    Last 4 digits: {last_4}")
                            
                            # Check if this matches our target codes
                            if last_4 in ["1020", "1013", "0033", "0039"]:
                                print(f"    🎯 POTENTIAL MATCH for code {last_4}!")
        
        if found_any:
            print(f"\n🎉 SUCCESS! Found matching images!")
        else:
            print(f"\n💡 No exact matches found. This suggests:")
            print("  1. The image codes in FileMaker might be different from filename numbers")
            print("  2. The screenshot might need to show the complete 'Images and Sequence' column")
            print("  3. There might be a mapping between order codes and file numbers")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_specific_codes()
    input("\nPress Enter to exit...") 