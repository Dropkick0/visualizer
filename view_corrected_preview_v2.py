#!/usr/bin/env python3
"""
View the corrected enhanced preview V2 - Fixed wallet count and spacing
"""

import sys
import os
from pathlib import Path

def view_corrected_preview_v2():
    """Open the corrected enhanced preview V2"""
    
    preview_path = Path("app/static/previews/corrected_user_preview_v2.png")
    
    if not preview_path.exists():
        print(f"❌ Preview V2 not found: {preview_path}")
        print("Run test_corrected_preview_v2.py first to generate the preview")
        return False
    
    print(f"🖼️ Opening corrected preview V2: {preview_path}")
    print()
    print("📊 This preview shows your CORRECTED breakdown:")
    print("✅ 12 individual wallets (not 96!) using image 0033")
    print("✅ 2 total 5x7's (1 pair) using image 0033") 
    print("✅ 1 8x10 using image 0033")
    print("✅ 1 10x13 using image 0102")
    print("✅ 1 16x20 using image 0033")
    print("✅ 1 20x24 using image 0102")
    print()
    print("🔧 FIXED ISSUES:")
    print("• Correct wallet quantity (12 individual, not 96)")
    print("• Proper spacing between large images")
    print("• No more overlapping of different sized products")
    print("• Improved layout algorithm for mixed sizes")
    print()
    
    try:
        # Try to open with default image viewer
        if sys.platform.startswith('win'):
            os.startfile(str(preview_path))
        elif sys.platform.startswith('darwin'):  # macOS
            os.system(f'open "{preview_path}"')
        else:  # Linux
            os.system(f'xdg-open "{preview_path}"')
        
        print(f"✅ Preview V2 opened successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to open preview: {e}")
        print(f"You can manually open: {preview_path.absolute()}")
        return False

if __name__ == "__main__":
    view_corrected_preview_v2()
    input("Press Enter to exit...") 