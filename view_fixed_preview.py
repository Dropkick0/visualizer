#!/usr/bin/env python3
"""
View the final FIXED sheet-based preview
"""

import sys
import os
from pathlib import Path

def view_fixed_preview():
    """Open the fixed sheet-based preview"""
    
    preview_path = Path("app/static/previews/sheet_based_preview_fixed.png")
    
    if not preview_path.exists():
        print(f"❌ Fixed preview not found: {preview_path}")
        print("Run test_sheet_based_preview_fixed.py first to generate the preview")
        return False
    
    print(f"🖼️ Opening FIXED sheet-based preview: {preview_path}")
    print()
    print("📊 This preview shows your FULLY CORRECTED layout:")
    print()
    print("✅ WALLET SHEETS:")
    print("   • 12 wallet sheets (not 3!)")
    print("   • Each sheet: 2x2 grid = 4 wallets per sheet")
    print("   • Total: 12 × 4 = 48 individual wallets using image 0033")
    print()
    print("✅ 5x7 SHEET:")
    print("   • 1 landscape sheet")
    print("   • 2 portrait images side by side (both using image 0033)")
    print("   • Total: 2 individual 5x7s")
    print()
    print("✅ LARGE INDIVIDUAL PRINTS:")
    print("   • 1 8x10 using image 0033")
    print("   • 1 10x13 using image 0102")
    print("   • 1 16x20 using image 0033")
    print("   • 1 20x24 using image 0102")
    print()
    print("🔧 FIXES APPLIED:")
    print("   • Correct wallet interpretation: quantity 12 = 12 sheets")
    print("   • 5x7 sheet now shows 2 images side by side")
    print("   • Proper spacing between all items")
    print("   • Realistic sheet-based layout matching actual printing")
    print()
    
    try:
        # Try to open with default image viewer
        if sys.platform.startswith('win'):
            os.startfile(str(preview_path))
        elif sys.platform.startswith('darwin'):  # macOS
            os.system(f'open "{preview_path}"')
        else:  # Linux
            os.system(f'xdg-open "{preview_path}"')
        
        print(f"✅ Fixed preview opened successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to open preview: {e}")
        print(f"You can manually open: {preview_path.absolute()}")
        return False

if __name__ == "__main__":
    view_fixed_preview()
    input("Press Enter to exit...") 