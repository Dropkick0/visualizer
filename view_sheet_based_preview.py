#!/usr/bin/env python3
"""
View the sheet-based enhanced preview
Shows wallets as 2x2 sheets and 5x7s as landscape sheets
"""

import sys
import os
from pathlib import Path

def view_sheet_based_preview():
    """Open the sheet-based enhanced preview"""
    
    preview_path = Path("app/static/previews/sheet_based_preview.png")
    
    if not preview_path.exists():
        print(f"❌ Sheet-based preview not found: {preview_path}")
        print("Run test_sheet_based_preview.py first to generate the preview")
        return False
    
    print(f"🖼️ Opening sheet-based preview: {preview_path}")
    print()
    print("📊 This preview shows your SHEET-BASED layout:")
    print("✅ 3 wallet sheets with 2x2 grids (4 wallets each) using image 0033")
    print("✅ 1 landscape 5x7 sheet with 2 portrait images side by side using image 0033") 
    print("✅ 1 8x10 using image 0033")
    print("✅ 1 10x13 using image 0102")
    print("✅ 1 16x20 using image 0033")
    print("✅ 1 20x24 using image 0102")
    print()
    print("🎨 SHEET-BASED BENEFITS:")
    print("• Wallets shown as realistic 2x2 printing sheets")
    print("• 5x7s shown as landscape sheet with 2 portraits side by side")
    print("• Represents actual printing/delivery format")
    print("• Better space utilization and visual organization")
    print("• Matches how products are physically produced")
    print()
    
    try:
        # Try to open with default image viewer
        if sys.platform.startswith('win'):
            os.startfile(str(preview_path))
        elif sys.platform.startswith('darwin'):  # macOS
            os.system(f'open "{preview_path}"')
        else:  # Linux
            os.system(f'xdg-open "{preview_path}"')
        
        print(f"✅ Sheet-based preview opened successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to open preview: {e}")
        print(f"You can manually open: {preview_path.absolute()}")
        return False

if __name__ == "__main__":
    view_sheet_based_preview()
    input("Press Enter to exit...") 