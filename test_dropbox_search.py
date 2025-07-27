#!/usr/bin/env python3
"""
Test Dropbox image search with common codes
"""

from pathlib import Path
import sys

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.image_search import create_image_searcher
from app.config import load_config

def test_dropbox_search():
    """Test image search with various codes"""
    print("🔍 Testing Dropbox Image Search")
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
        
        # Test with various 4-digit codes that might be in the folder
        test_codes = [
            "1020", "1013",  # Codes from OCR
            "1555", "9198", "5615", "9999",  # Previous test codes
            "0001", "0002", "0003",  # Leading zeros
            "1000", "2000", "3000",  # Round numbers
            "1234", "5678", "9876"   # Common patterns
        ]
        
        print(f"🔍 Testing {len(test_codes)} different codes...")
        
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
        
        if found_any:
            print(f"\n🎉 SUCCESS! Image search is working and found images!")
        else:
            print(f"\n🤔 No images found with test codes.")
            print("This could mean:")
            print("  1. Different naming convention used")
            print("  2. Images in different subfolders")
            print("  3. Different file extensions")
            
            # Let's check what files actually exist
            print(f"\n📂 Scanning folder structure...")
            file_count = 0
            for ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
                pattern = f"*{ext}"
                files = list(dropbox_path.rglob(pattern))
                if files:
                    file_count += len(files)
                    print(f"  {ext.upper()}: {len(files)} files")
                    # Show a few examples
                    for f in files[:3]:
                        print(f"    - {f.name}")
            
            print(f"\n📊 Total image files found: {file_count}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dropbox_search()
    input("\nPress Enter to exit...") 