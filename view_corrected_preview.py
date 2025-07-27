#!/usr/bin/env python3
"""
View the corrected enhanced preview
"""

import sys
import os
from pathlib import Path

def view_corrected_preview():
    """Open the corrected enhanced preview"""
    
    preview_path = Path("app/static/previews/corrected_user_preview.png")
    
    if not preview_path.exists():
        print(f"❌ Preview not found: {preview_path}")
        print("Run test_corrected_preview.py first to generate the preview")
        return False
    
    print(f"🖼️ Opening corrected preview: {preview_path}")
    print()
    print("📊 This preview shows your EXACT breakdown:")
    print("• 96 total wallets (12 sheets × 8 per sheet) using image 0033")
    print("• 2 total 5x7's (1 pair sheet) using image 0033") 
    print("• 1 8x10 using image 0033")
    print("• 1 10x13 using image 0102")
    print("• 1 16x20 using image 0033")
    print("• 1 20x24 using image 0102")
    print()
    
    try:
        # Try to open with default image viewer
        if sys.platform.startswith('win'):
            os.startfile(str(preview_path))
        elif sys.platform.startswith('darwin'):  # macOS
            os.system(f'open "{preview_path}"')
        else:  # Linux
            os.system(f'xdg-open "{preview_path}"')
        
        print(f"✅ Preview opened successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to open preview: {e}")
        print(f"You can manually open: {preview_path.absolute()}")
        return False

if __name__ == "__main__":
    view_corrected_preview()
    input("Press Enter to exit...") 