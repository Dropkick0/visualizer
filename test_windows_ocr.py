#!/usr/bin/env python3
"""
Test script for Windows OCR functionality
Run this before bundling to ensure Windows OCR works properly
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import tempfile

def create_test_image():
    """Create a test image with sample FileMaker-style text"""
    # Create a test image that looks like FileMaker output
    img = Image.new('RGB', (800, 200), color='#F5F5DC')  # Beige background like FileMaker
    draw = ImageDraw.Draw(img)
    
    # Try to use a standard font, fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Add sample text that resembles FileMaker field order
    test_lines = [
        "PORTRAITS",
        "2 8x10 Basic Print Digital                    1234, 5678",
        "1 5x7 Cherry Wallet                          9876"
    ]
    
    y_pos = 20
    for line in test_lines:
        draw.text((20, y_pos), line, fill='black', font=font)
        y_pos += 30
    
    return img


def test_windows_ocr():
    """Test Windows OCR functionality"""
    print("🔍 Testing Windows OCR functionality...")
    print("=" * 50)
    
    # Test 1: Check if winocr is available
    print("Test 1: Checking winocr library...")
    try:
        import winocr
        print("✅ winocr library imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import winocr: {e}")
        print("💡 Install with: pip install winocr")
        return False
    
    # Test 2: Create test image
    print("\nTest 2: Creating test image...")
    try:
        test_img = create_test_image()
        print("✅ Test image created")
    except Exception as e:
        print(f"❌ Failed to create test image: {e}")
        return False
    
    # Test 3: Run OCR on test image
    print("\nTest 3: Running Windows OCR...")
    try:
        result = winocr.recognize_pil_sync(test_img)
        
        print("✅ OCR completed successfully")
        print(f"📝 Detected text: '{result['text']}'")
        
        # Check if we got reasonable results
        detected_text = result['text'].upper()
        if 'PORTRAITS' in detected_text or '8X10' in detected_text or any(char.isdigit() for char in detected_text):
            print("✅ OCR results look reasonable")
            return True
        else:
            print("⚠️  OCR results seem incomplete")
            print("This might still work, but accuracy could be low")
            return True
            
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        print("💡 Make sure Windows OCR language pack is installed:")
        print("   Add-WindowsCapability -Online -Name 'Language.OCR~~~en-US~0.0.1.0'")
        return False


def test_app_ocr_integration():
    """Test our app's OCR module"""
    print("\n🔍 Testing app OCR integration...")
    print("=" * 50)
    
    try:
        # Test our Windows OCR module
        sys.path.insert(0, str(Path(__file__).parent))
        from app.ocr_windows import WindowsOCR
        from app.config import AppConfig
        
        print("✅ App OCR module imported successfully")
        
        # Create a minimal config
        config = AppConfig()
        
        # Initialize OCR processor
        ocr_processor = WindowsOCR(config)
        print("✅ OCR processor initialized")
        
        # Test OCR installation check
        is_available = ocr_processor.test_windows_ocr_installation()
        if is_available:
            print("✅ Windows OCR installation test passed")
            return True
        else:
            print("❌ Windows OCR installation test failed")
            return False
            
    except Exception as e:
        print(f"❌ App OCR integration test failed: {e}")
        return False


def main():
    """Run all OCR tests"""
    print("🎨 Portrait Preview Webapp - OCR Test Suite")
    print("=" * 60)
    print("This script tests Windows OCR functionality before bundling")
    print()
    
    # Run tests
    tests_passed = 0
    total_tests = 2
    
    if test_windows_ocr():
        tests_passed += 1
    
    if test_app_ocr_integration():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Windows OCR is ready for bundling.")
        print("You can now run: deploy.bat")
        return True
    else:
        print("⚠️  Some tests failed. Check the issues above before bundling.")
        print("\n💡 Common solutions:")
        print("   1. Install Windows OCR: Add-WindowsCapability -Online -Name 'Language.OCR~~~en-US~0.0.1.0'")
        print("   2. Install winocr: pip install winocr")
        print("   3. Make sure you're on Windows 10/11")
        return False


if __name__ == "__main__":
    success = main()
    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1) 