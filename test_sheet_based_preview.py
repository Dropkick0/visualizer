#!/usr/bin/env python3
"""
Test Enhanced Preview Generator - Sheet-Based Layout
Shows wallets as 2x2 sheets and 5x7s as landscape sheets with portrait images
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_sheet_based_preview():
    """Test with sheet-based layout approach"""
    print("🎨 Enhanced Portrait Preview - Sheet-Based Layout")
    print("=" * 60)
    
    try:
        from app.enhanced_preview import EnhancedPortraitPreviewGenerator
        from app.config import load_product_config
        
        # Load products config
        products_config = load_product_config()
        print(f"✅ Loaded {len(products_config.get('products', []))} product configurations")
        
        # Found images from Dropbox search
        dropbox_base = Path("C:/Users/remem/Re MEMBER Dropbox/PHOTOGRAPHY PROOFING/PHOTOGRAPHER UPLOADS (1)/Ethan/From/8017 Lab Order/Lab Order TU Only")
        images_found = {
            '0033': [dropbox_base / "_MG_0033.JPG"],
            '0039': [dropbox_base / "_MG_0039.JPG"],
            '0044': [dropbox_base / "_MG_0044.JPG"],
            '0102': [dropbox_base / "_MG_0102.JPG"],
        }
        
        # Check which images actually exist
        existing_images = {}
        for code, paths in images_found.items():
            existing_paths = [p for p in paths if p.exists()]
            if existing_paths:
                existing_images[code] = existing_paths
                print(f"✅ Found image for code {code}: {existing_paths[0].name}")
            else:
                print(f"⚠️ Image not found for code {code}: {paths[0]}")
        
        print(f"📸 Using {len(existing_images)} actual images")
        
        # Create order items based on SHEET-BASED approach:
        order_items = []
        
        print(f"\n📋 SHEET-BASED LAYOUT:")
        print(f"=" * 40)
        
        # 1. Wallet sheets: 12 wallets = 3 sheets of 4 wallets each (2x2 grid)
        print(f"1. 3 wallet sheets (2x2 grid = 4 wallets per sheet) of 0033")
        for sheet_num in range(3):
            order_items.append({
                'product_slug': 'wallet_sheet_2x2', 
                'product_code': '200_sheet', 
                'quantity': 1, 
                'image_codes': ['0033'] * 4,  # 4 images per sheet, all same
                'size_category': 'wallet_sheet',
                'sheet_type': '2x2',
                'sheet_number': sheet_num + 1,
                'display_name': f'Wallet Sheet {sheet_num + 1} (2x2)'
            })
        
        # 2. 5x7 sheet: 1 landscape sheet with 2 portrait 5x7s side by side
        print(f"2. 1 landscape 5x7 sheet with 2 portrait images side by side of 0033")
        order_items.append({
            'product_slug': '5x7_sheet_landscape', 
            'product_code': '570_sheet', 
            'quantity': 1, 
            'image_codes': ['0033', '0033'],  # 2 images side by side, same image
            'size_category': 'medium_sheet',
            'sheet_type': 'landscape_2x1',
            'display_name': '5x7 Landscape Sheet (2 portraits)'
        })
        
        # 3. Individual large prints
        print(f"3. 1 8x10 of 0033")
        order_items.append({
            'product_slug': '8x10_basic_810', 
            'product_code': '810', 
            'quantity': 1, 
            'image_codes': ['0033'],
            'size_category': 'large'
        })
        
        print(f"4. 1 10x13 of 0102")
        order_items.append({
            'product_slug': '10x13_basic_1013', 
            'product_code': '1013', 
            'quantity': 1, 
            'image_codes': ['0102'],
            'size_category': 'large'
        })
        
        print(f"5. 1 16x20 of 0033")
        order_items.append({
            'product_slug': '16x20_basic_1620', 
            'product_code': '1620', 
            'quantity': 1, 
            'image_codes': ['0033'],
            'size_category': 'large'
        })
        
        print(f"6. 1 20x24 of 0102")
        order_items.append({
            'product_slug': '20x24_basic_2024', 
            'product_code': '2024', 
            'quantity': 1, 
            'image_codes': ['0102'],
            'size_category': 'large'
        })
        
        print(f"\n✅ SHEET-BASED BREAKDOWN:")
        print(f"   • 3 wallet sheets (2x2 = 4 per sheet) = 12 total wallets (0033)")
        print(f"   • 1 landscape 5x7 sheet (2 side by side) = 2 total 5x7s (0033)")
        print(f"   • 1 8x10 (0033)")
        print(f"   • 1 10x13 (0102)")
        print(f"   • 1 16x20 (0033)")
        print(f"   • 1 20x24 (0102)")
        print(f"   • Total sheet items: {len(order_items)}")
        
        # Create enhanced generator
        output_dir = Path("app/static/previews")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generator = EnhancedPortraitPreviewGenerator(products_config, images_found, output_dir)
        
        # Generate preview
        output_path = output_dir / "sheet_based_preview.png"
        print(f"\n🚀 Generating sheet-based preview...")
        print(f"📐 Wallets as 2x2 sheets (4 images per sheet)")
        print(f"🎨 5x7s as landscape sheet (2 portrait images side by side)")
        print(f"📏 Large prints as individual items")
        
        success = generator.generate_size_based_preview(order_items, output_path)
        
        if success:
            print(f"✅ Sheet-based preview created successfully!")
            print(f"📁 Saved to: {output_path}")
            print(f"📏 Canvas size: 2400x1600 pixels")
            print(f"🎯 Shows products as actual printed sheets")
            
            return True
            
        else:
            print(f"❌ Failed to create preview")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sheet_based_preview()
    
    if success:
        print(f"\n🎉 SUCCESS!")
        print(f"Your preview now shows:")
        print(f"• 3 wallet sheets with 2x2 grids (4 wallets each) using 0033")
        print(f"• 1 landscape 5x7 sheet with 2 portrait images using 0033") 
        print(f"• Individual large prints: 8x10, 10x13, 16x20, 20x24")
        print(f"• Realistic representation of how products are printed")
    else:
        print(f"\n⚠️ There were issues generating the preview")
    
    input("\nPress Enter to exit...") 