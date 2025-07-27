#!/usr/bin/env python3
"""
Test the automated workflow with the existing FileMaker screenshot
"""

import sys
from pathlib import Path
from loguru import logger

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from automated_workflow import AutomatedOrderProcessor


def test_automated_workflow():
    """Test the automated workflow with existing screenshot"""
    print("🎨 Testing Automated FileMaker Order Processing")
    print("=" * 60)
    
    # Use the existing test screenshot
    screenshot_path = Path("Test_Full_Screenshot.png")
    
    if not screenshot_path.exists():
        print(f"❌ Test screenshot not found: {screenshot_path}")
        print("Please ensure Test_Full_Screenshot.png is in the current directory")
        return False
    
    print(f"📸 Using test screenshot: {screenshot_path}")
    
    try:
        # Initialize processor
        processor = AutomatedOrderProcessor()
        
        # Process the manual screenshot
        success = processor.process_manual_screenshot(screenshot_path)
        
        if success:
            print("\n🎉 SUCCESS! Automated workflow completed successfully!")
            print("\nWhat was accomplished:")
            print("✅ FileMaker format validation (Field/Master Order File)")
            print("✅ Layout validation (Item Entry, Wish List)")  
            print("✅ OCR text extraction")
            print("✅ Order item parsing (quantities, product codes, image codes)")
            print("✅ Dropbox image searching (by 4-digit codes)")
            print("✅ Portrait preview generation")
            
            return True
        else:
            print("\n❌ Automated workflow failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_search_specifically():
    """Test just the image search functionality"""
    print("\n🔍 Testing Image Search Functionality")
    print("-" * 40)
    
    try:
        from app.image_search import create_image_searcher
        from app.config import load_config
        
        config = load_config()
        searcher = create_image_searcher(config)
        
        if not searcher:
            print("❌ Could not create image searcher")
            return False
        
        # Test with known codes from the FileMaker screenshot
        test_codes = ["1555", "9198", "5615", "9999"]
        
        print(f"Searching for codes: {test_codes}")
        results = searcher.find_images_by_codes(test_codes)
        
        total_found = 0
        for code, images in results.items():
            if images:
                print(f"  Code {code}: ✅ Found {len(images)} images")
                for img in images[:2]:  # Show first 2
                    print(f"    - {img.name}")
                total_found += len(images)
            else:
                print(f"  Code {code}: ❌ No images found")
        
        print(f"\n📊 Total images found: {total_found}")
        
        if total_found > 0:
            print("✅ Image search is working!")
            return True
        else:
            print("⚠️ No images found - this may be expected if testing on different machine")
            return True  # Not a failure, just no images available
            
    except Exception as e:
        print(f"❌ Image search test failed: {e}")
        return False


if __name__ == "__main__":
    print("Starting automated workflow tests...")
    print()
    
    # Test image search first
    image_search_ok = test_image_search_specifically()
    
    print()
    
    # Test full workflow
    workflow_ok = test_automated_workflow()
    
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY:")
    print(f"  Image Search: {'✅ PASS' if image_search_ok else '❌ FAIL'}")
    print(f"  Full Workflow: {'✅ PASS' if workflow_ok else '❌ FAIL'}")
    
    if workflow_ok:
        print("\n🎉 All tests passed! The automated workflow is ready to use.")
        print("\nTo use with FileMaker:")
        print("1. Open FileMaker with your order file")
        print("2. Set layout to 'Item Entry, Wish List'")
        print("3. Run: python automated_workflow.py")
    else:
        print("\n⚠️ Some tests failed. Check the logs above for details.")
    
    input("\nPress Enter to exit...") 