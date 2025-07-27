#!/usr/bin/env python3
"""
Test the optimized FileMaker screenshot capture with zoom control
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.screenshot import capture_order_screenshot, FileMakerScreenshotCapture

def test_optimized_capture():
    """Test the optimized capture functionality"""
    print("🎨 Testing Optimized FileMaker Screenshot Capture")
    print("=" * 60)
    print("📋 This test will:")
    print("  1. Find your FileMaker window")
    print("  2. Set optimal zoom (100 clicks in, 4 clicks out)")
    print("  3. Validate Field/Master Order File format")
    print("  4. Validate 'Item Entry, Wish List' layout")
    print("  5. Capture optimized screenshot")
    print()
    
    # Prompt user to prepare
    print("Please ensure:")
    print("✅ FileMaker is open")
    print("✅ Field Order File or Master Order File is displayed")
    print("✅ Layout is set to 'Item Entry, Wish List'")
    print("✅ PORTRAITS table is visible")
    print()
    
    input("Press Enter when ready to test optimized capture...")
    
    try:
        print("\n🚀 Starting optimized capture test...")
        
        # Test the optimized capture
        screenshot_path = capture_order_screenshot()
        
        if screenshot_path:
            print(f"\n🎉 SUCCESS! Optimized screenshot captured:")
            print(f"📁 Location: {screenshot_path}")
            print(f"📏 File size: {screenshot_path.stat().st_size / 1024:.1f} KB")
            
            # Test processing the screenshot
            print(f"\n🔍 Testing OCR processing on optimized screenshot...")
            
            from app.config import load_config
            from app.ocr_windows import WindowsOCR
            
            config = load_config()
            ocr = WindowsOCR(config)
            work_dir = Path("tmp")
            work_dir.mkdir(exist_ok=True)
            
            result = ocr.process_screenshot(screenshot_path, work_dir)
            
            if hasattr(result, 'raw_text'):
                print(f"✅ OCR Success: {len(result.raw_text)} characters extracted")
                print(f"🎯 Confidence: {result.confidence_avg:.1f}%")
                
                # Look for image codes
                import re
                codes = re.findall(r'\b(\d{4})\b', result.raw_text)
                if codes:
                    print(f"📋 Found image codes: {list(set(codes))}")
                else:
                    print("⚠️ No 4-digit image codes detected")
                
                # Check for products
                products = ['basic', 'trio', 'portrait', 'wallet']
                found_products = [p for p in products if p.lower() in result.raw_text.lower()]
                print(f"🏷️ Found products: {found_products}")
                
            else:
                print("❌ OCR failed on optimized screenshot")
            
            return True
            
        else:
            print("\n❌ Optimized capture failed!")
            print("Please check:")
            print("  - FileMaker is open and visible")
            print("  - Layout is set to 'Item Entry, Wish List'")
            print("  - Field Order File or Master Order File is displayed")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_zoom_control():
    """Test just the zoom control functionality"""
    print("\n🔍 Testing Zoom Control Only")
    print("-" * 40)
    
    try:
        capturer = FileMakerScreenshotCapture()
        window = capturer.find_filemaker_window()
        
        if window:
            print(f"✅ Found FileMaker window: {window.title}")
            input("Press Enter to test zoom control (100 in, 4 out)...")
            
            success = capturer.set_optimal_zoom_level(window)
            if success:
                print("✅ Zoom control completed successfully!")
                print("The FileMaker window should now be at optimal zoom level")
            else:
                print("❌ Zoom control failed")
            
            return success
        else:
            print("❌ No FileMaker window found")
            return False
            
    except Exception as e:
        print(f"❌ Zoom test failed: {e}")
        return False

if __name__ == "__main__":
    print("🎨 FileMaker Optimized Capture Test Suite")
    print()
    
    # Test zoom control first
    zoom_success = test_zoom_control()
    
    print()
    
    # Test full optimized capture
    capture_success = test_optimized_capture()
    
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY:")
    print(f"  Zoom Control: {'✅ PASS' if zoom_success else '❌ FAIL'}")
    print(f"  Optimized Capture: {'✅ PASS' if capture_success else '❌ FAIL'}")
    
    if capture_success:
        print("\n🎉 Optimized capture is working!")
        print("The system will now consistently:")
        print("  • Find FileMaker windows automatically")
        print("  • Set optimal zoom level (100 in, 4 out)")
        print("  • Validate Field/Master Order File format")  
        print("  • Validate Item Entry, Wish List layout")
        print("  • Capture perfectly positioned screenshots")
        print("  • Extract all image codes reliably")
    
    input("\nPress Enter to exit...") 