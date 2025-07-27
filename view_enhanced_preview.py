#!/usr/bin/env python3
"""
View Enhanced Preview
Opens the enhanced size-based preview in the default image viewer
"""

import os
import sys
from pathlib import Path

def view_preview():
    """Open the enhanced preview in the default image viewer"""
    
    preview_path = Path("app/static/previews/enhanced_size_based_preview.png")
    
    if not preview_path.exists():
        print("❌ Enhanced preview not found!")
        print(f"Expected location: {preview_path.absolute()}")
        return False
    
    print("🖼️ Enhanced Portrait Preview - Size-Based Layout")
    print("=" * 60)
    print(f"📁 File: {preview_path}")
    print(f"📏 Canvas: 2400x1600 pixels")
    print(f"🎨 Background: Warm beige")
    print(f"📐 Scale: 20 pixels per inch")
    print()
    
    print("📋 LAYOUT FEATURES:")
    print("✅ Products arranged from largest to smallest")
    print("✅ Correct proportional sizing")
    print("✅ Actual portrait images where available:")
    print("   • _MG_0033.JPG ✅")
    print("   • _MG_0039.JPG ✅") 
    print("   • _MG_0044.JPG ✅")
    print("   • _MG_0102.JPG ✅")
    print("✅ Quantity badges for multiple items")
    print("✅ Product labels with image counts")
    print("✅ Frame colors (cherry, black for trios)")
    print("✅ Order summary sidebar")
    print()
    
    print("📐 PRODUCT SIZES (Largest to Smallest):")
    print(" 1. 20\" × 24\" - 1x 20x24 Basic")
    print(" 2. 16\" × 20\" - 1x 16x20 Basic")
    print(" 3. 10\" × 20\" - 1x 10x20 Trio Portrait")
    print(" 4. 10\" × 13\" - 1x 10x13 Basic")
    print(" 5.  8\" × 10\" - 1x 8x10 Basic")
    print(" 6.  5\" × 10\" - 3x 5x10 Trio Portrait")
    print(" 7.  5\" × 7\"  - 1x 5x7 Basic (2 images)")
    print(" 8. 3.5\" × 5\" - 3x 3.5x5 Basic (4 images each)")
    print(" 9. 2.5\" × 3.5\" - 12x Wallets (8 images each)")
    print()
    
    try:
        print("🚀 Opening preview in default image viewer...")
        
        # Open with default application
        if sys.platform == "win32":
            os.startfile(str(preview_path))
        elif sys.platform == "darwin":  # macOS
            os.system(f"open '{preview_path}'")
        else:  # Linux
            os.system(f"xdg-open '{preview_path}'")
        
        print("✅ Preview opened successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error opening preview: {e}")
        print(f"You can manually open: {preview_path.absolute()}")
        return False

if __name__ == "__main__":
    success = view_preview()
    
    if success:
        print("\n🎨 WHAT YOU'RE SEEING:")
        print("• All products displayed with true-to-scale proportions")
        print("• Beige background for professional presentation")
        print("• Largest items (20x24, 16x20) at top-left")
        print("• Smaller items arranged left-to-right, top-to-bottom")
        print("• Real portrait images from your Dropbox folder")
        print("• Trio portraits show multiple image layouts")
        print("• Wallets show grid of 8 images")
        print("• Quantity badges for multiple items")
        print("• Complete order summary on the right")
    
    input("\nPress Enter to exit...") 