#!/usr/bin/env python3
"""
Test Enhanced Preview Generator - Corrected User Data V2 WITH FRAMES
Fixed wallet quantity and spacing issues with proper sheet structure
Added frame overlay support for individual portraits
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_corrected_preview_v2():
    """Test with the CORRECTED data - proper sheet structure with FRAME OVERLAYS"""
    print("🎨 Enhanced Portrait Preview - Corrected User Data V2 WITH FRAME OVERLAYS")
    print("=" * 80)
    
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
        
        # FRAME REQUIREMENTS - Testing with 3 sheets of 5x7s and 3 frames
        frame_requirements = {
            "5x7": 3,    # 3 frames for 5x7 portraits (testing with 6 photos total)
            "8x10": 1,   # 1 frame for 8x10
            "10x13": 1,  # 1 frame for 10x13
            "16x20": 0,  # No 16x20 frames in this order
            "20x24": 0   # No 20x24 frames in this order
        }
        
        print(f"\n🖼️ FRAME REQUIREMENTS:")
        print(f"=" * 40)
        for size, qty in frame_requirements.items():
            if qty > 0:
                print(f"   • {qty}x {size} frames")
        
        # Create order items based on USER'S CORRECTED BREAKDOWN with proper sheet structure:
        order_items = []
        
        print(f"\n📋 CORRECTED USER BREAKDOWN (PROPER SHEET STRUCTURE WITH FRAMES):")
        print(f"=" * 60)
        
        # 1. 96 individual wallets = 12 sheets of 2x4 (8 wallets per sheet)
        print(f"1. 96 individual wallets = 12 wallet sheets (2x4 grid = 8 wallets per sheet) of 0033")
        for sheet_num in range(12):  # 12 sheets × 8 wallets = 96 total wallets
            order_items.append({
                'product_slug': 'wallet_sheet_2x4', 
                'product_code': '200_sheet', 
                'quantity': 1, 
                'image_codes': ['0033'] * 8,  # 8 images per sheet, all same
                'size_category': 'wallet_sheet',
                'sheet_type': '2x2',  # Keep same handler name
                'sheet_number': sheet_num + 1,
                'display_name': f'Wallet Sheet {sheet_num + 1} (2x4)'
            })
        
        # 2. 3 pairs of 5x7's = 3 landscape sheets with 2 portrait 5x7s side by side (6 photos total)
        # NOTE: These will be automatically split into individual 5x7s with frames applied
        print(f"2. 3 5x7 pairs = 3 landscape sheets, each with SAME image repeated (2 per sheet)")
        print(f"   Sheet 1: 2 copies of 0033 (BASIC), Sheet 2: 2 copies of 0039 (PRESTIGE), Sheet 3: 2 copies of 0044 (KEEPSAKE)")
        print(f"   Total: 6 individual 5x7 photos, 3 frames available")
        print(f"   Expected result: 3 individual framed 5x7s + 1 individual unframed 5x7 + 1 pair of 5x7s")
        
        # Create 3 separate 5x7 pair items - each sheet has same image repeated with different finishes
        sheet_images = ['0033', '0039', '0044']  # Different images for different sheets
        sheet_finishes = ['Basic', 'Prestige', 'Keepsake']  # Different finishes to showcase hierarchy
        for sheet_num in range(3):
            sheet_image = sheet_images[sheet_num]  # Each sheet uses one specific image
            finish_type = sheet_finishes[sheet_num]  # Each sheet gets a different finish
            order_items.append({
                'product_slug': '5x7_sheet_landscape', 
                'product_code': '570_sheet', 
                'quantity': 1, 
                'image_codes': [sheet_image, sheet_image],  # Same image repeated on each sheet
                'size_category': 'medium_sheet',
                'sheet_type': 'landscape_2x1',
                'sheet_number': sheet_num + 1,
                'finish_type': finish_type,
                'display_name': f'5x7 Landscape Sheet {sheet_num + 1} (2 of {sheet_image}) - {finish_type.upper()}'
            })
        
        # 3. 12 individual 3.5x5s = 3 portrait sheets with 2x2 grid (4 images per sheet)
        print(f"3. 12 individual 3.5x5s = 3 portrait sheets with 2x2 grid (4 images per sheet) of 0039")
        for sheet_num in range(3):  # 3 sheets × 4 images = 12 total 3.5x5s
            order_items.append({
                'product_slug': '3x5_sheet_portrait', 
                'product_code': '350_sheet', 
                'quantity': 1, 
                'image_codes': ['0039'] * 4,  # 4 images per sheet, all same
                'size_category': 'small_sheet',
                'sheet_type': 'portrait_2x2',
                'sheet_number': sheet_num + 1,
                'display_name': f'3.5x5 Portrait Sheet {sheet_num + 1} (2x2)'
            })
        
        # 4. Individual large prints (NO sheet_type - these are single images)
        # These will have frames applied based on frame_requirements
        print(f"4. 1 8x10 of 0033 (individual image) - WILL HAVE FRAME - PRESTIGE FINISH - ARTIST SERIES")
        order_items.append({
            'product_slug': '8x10_basic_810', 
            'product_code': '810', 
            'quantity': 1, 
            'image_codes': ['0033'],
            'size_category': 'large',
            'finish_type': 'Prestige',
            'artist_series': True,  # Artist Series flag
            'display_name': '8x10 Portrait (0033) - PRESTIGE - Artist Series'
            # NO sheet_type - this is an individual image
        })
        
        print(f"5. 1 10x13 of 0102 (individual image) - WILL HAVE FRAME - KEEPSAKE FINISH")
        order_items.append({
            'product_slug': '10x13_basic_1013', 
            'product_code': '1013', 
            'quantity': 1, 
            'image_codes': ['0102'],
            'size_category': 'large',
            'finish_type': 'Keepsake',
            'display_name': '10x13 Portrait (0102) - KEEPSAKE'
            # NO sheet_type - this is an individual image
        })
        
        print(f"6. 1 16x20 of 0033 (individual image) - NO FRAME (none available) - PRESTIGE FINISH - ARTIST + RETOUCH")
        order_items.append({
            'product_slug': '16x20_basic_1620', 
            'product_code': '1620', 
            'quantity': 1, 
            'image_codes': ['0033'],  # 0033 is in retouch list
            'size_category': 'large',
            'finish_type': 'Prestige',
            'display_name': '16x20 Portrait (0033) - PRESTIGE - Artist Brush Strokes'  # Artist keyword in name
            # NO sheet_type - this is an individual image
        })
        
        print(f"7. 1 20x24 of 0102 (individual image) - NO FRAME (none available) - KEEPSAKE FINISH")
        order_items.append({
            'product_slug': '20x24_basic_2024', 
            'product_code': '2024', 
            'quantity': 1, 
            'image_codes': ['0102'],
            'size_category': 'large',
            'finish_type': 'Keepsake',
            'display_name': '20x24 Portrait (0102) - KEEPSAKE'
            # NO sheet_type - this is an individual image
        })
        
        # Add one more test item to show RETOUCH only
        print(f"7.5. 1 additional 8x10 of 0039 (individual image) - RETOUCH ONLY")
        order_items.append({
            'product_slug': '8x10_basic_810', 
            'product_code': '810', 
            'quantity': 1, 
            'image_codes': ['0039'],  # 0039 is in retouch list
            'size_category': 'large',
            'finish_type': 'Basic',
            'display_name': '8x10 Portrait (0039) - BASIC - Retouch Only'
            # NO sheet_type - this is an individual image
        })
        
        # 8. ADD TRIO COMPOSITES - Using same images for testing
        print(f"8. 2 Trio 5x10 composites with different frame/matte combinations")
        order_items.append({
            'product_slug': 'trio_5x10_black_white',
            'product_code': '510.3',
            'quantity': 1,
            'image_codes': ['0033', '0039', '0044'],  # 3 different images
            'size_category': 'trio_composite',
            'template': 'trio_horizontal',
            'count_images': 3,
            'frame_color': 'Black',
            'matte_color': 'White',
            'display_name': 'Trio 5x10 - Black Frame, White Matte'
        })
        
        order_items.append({
            'product_slug': 'trio_5x10_cherry_gray',
            'product_code': '510.3',
            'quantity': 1,
            'image_codes': ['0102', '0033', '0039'],  # 3 different images
            'size_category': 'trio_composite',
            'template': 'trio_horizontal',
            'count_images': 3,
            'frame_color': 'Cherry',
            'matte_color': 'Gray',
            'display_name': 'Trio 5x10 - Cherry Frame, Gray Matte'
        })
        
        print(f"9. 1 Trio 10x20 composite")
        order_items.append({
            'product_slug': 'trio_10x20_black_tan',
            'product_code': '1020.5',
            'quantity': 1,
            'image_codes': ['0044', '0102', '0033'],  # 3 different images
            'size_category': 'trio_composite',
            'template': 'trio_horizontal',
            'count_images': 3,
            'frame_color': 'Black',
            'matte_color': 'Tan',
            'display_name': 'Trio 10x20 - Black Frame, Tan Matte'
        })
        
        print(f"\n✅ CORRECTED TOTAL BREAKDOWN (WITH TRIO COMPOSITES AND FRAMES):")
        print(f"   • 12 wallet sheets (2x4) = 96 individual wallets (0033) - No finish options")
        print(f"   • 3 5x7 landscape sheets = 6 individual 5x7's total -> WILL SPLIT FOR FRAMES")
        print(f"     → Sheet 1: BASIC finish (0033)")
        print(f"     → Sheet 2: PRESTIGE finish (0039)")
        print(f"     → Sheet 3: KEEPSAKE finish (0044)")
        print(f"   • 3 3.5x5 portrait sheets (2x2) = 12 individual 3.5x5's (0039) - No finish options")
        print(f"   • 1 8x10 individual image (0033) -> WITH FRAME - PRESTIGE FINISH - ARTIST SERIES BANNER")
        print(f"   • 1 10x13 individual image (0102) -> WITH FRAME - KEEPSAKE FINISH - No Banner")
        print(f"   • 1 16x20 individual image (0033) -> NO FRAME - PRESTIGE FINISH - ARTIST SERIES + RETOUCH BANNER")
        print(f"   • 1 20x24 individual image (0102) -> NO FRAME - KEEPSAKE FINISH - No Banner")
        print(f"   • 1 additional 8x10 (0039) -> BASIC FINISH - RETOUCH BANNER ONLY")
        print(f"   • 2 Trio 5x10 composites (different frame/matte combinations)")
        print(f"   • 1 Trio 10x20 composite")
        print(f"   • Total order items: {len(order_items)}")
        
        print(f"\n🎨 FINISH OPTIONS SHOWCASE:")
        print(f"   • BASIC: Standard finish (5x7 Sheet 1)")
        print(f"   • PRESTIGE: Acid-free board mount (8x10, 16x20, 5x7 Sheet 2)")
        print(f"   • KEEPSAKE: Canvas + acid-free board (10x13, 20x24, 5x7 Sheet 3)")
        print(f"   • Only sizes 5x7, 8x10, 10x13, 16x20, 20x24 eligible for finish upgrades")
        
        print(f"\n🏷️ BANNER OVERLAY DEMONSTRATION:")
        print(f"   • ARTIST SERIES: 8x10 (0033) - Shows 'ARTIST SERIES' banner")
        print(f"   • RETOUCH ONLY: 8x10 (0039) - Shows 'RETOUCH' banner")
        print(f"   • ARTIST + RETOUCH: 16x20 (0033) - Shows 'ARTIST SERIES + RETOUCH' banner")
        print(f"   • NO BANNER: 10x13 (0102), 20x24 (0102) - No special options")
        print(f"   • Retouch List: 0033, 0039 (all instances of these images get retouch banner)")
        print(f"   • Artist Series: Items with artist_series flag or 'artist' keywords in name")
        
        print(f"\n🖼️ FRAME APPLICATION STRATEGY (6 PHOTOS, 3 FRAMES):")
        print(f"   • 3x 5x7 frames available for 6 total 5x7 photos")
        print(f"   • Expected: 3 individual framed 5x7s + 1 individual unframed + 1 pair remaining")
        print(f"   • 1x 8x10 frame available -> Will frame the 8x10 print")
        print(f"   • 1x 10x13 frame available -> Will frame the 10x13 print")
        print(f"   • 16x20 and 20x24 will remain unframed (no frames available)")
        print(f"   • Wallets and 3.5x5s cannot have frames")
        print(f"   • Trio composites have their own built-in frames")
        
        # Create enhanced generator
        output_dir = Path("app/static/previews")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generator = EnhancedPortraitPreviewGenerator(products_config, existing_images, output_dir)
        
        # Generate preview with frames
        output_path = output_dir / "corrected_user_preview_v2_with_frames.png"
        print(f"\n🚀 Generating corrected user preview V2 WITH FRAMES AND TRIO COMPOSITES...")
        print(f"📐 LEFT SIDE (2/3 width): Regular prints in sections WITH FRAMES")
        print(f"   • SECTION 1 (TOP): Large prints - 20x24, 16x20, 10x13 (FRAMED), 8x10 (FRAMED)")
        print(f"   • SECTION 2: 5x7 unified section - ALL 5x7 types in same rows/columns")
        print(f"   • SECTION 3: 3.5x5 sheets - 3 portrait sheets × 4 images = 12 total") 
        print(f"   • SECTION 4 (BOTTOM): Wallet sheets - 12 sheets × 8 wallets = 96 total")
        print(f"📐 RIGHT SIDE (1/3 width): Trio Composites - RIGHT-JUSTIFIED")
        print(f"   • 2 Trio 5x10 composites (Black/White, Cherry/Gray)")
        print(f"   • 1 Trio 10x20 composite (Black/Tan)")
        print(f"🎨 Customer images (0033, 0039, 0044, 0102) in composite frame openings")
        print(f"🖼️ FRAMES: Black frames around 8x10, 10x13, and individual 5x7s")
        print(f"🏷️ BANNERS: Semi-transparent overlay banners for Artist Series and Retouch options")
        
        success = generator.generate_size_based_preview_with_composites(
            order_items, output_path, frame_requirements
        )
        
        if success:
            print(f"✅ Corrected preview V2 WITH FRAMES AND TRIO COMPOSITES created successfully!")
            print(f"📁 Saved to: {output_path}")
            print(f"📏 Canvas size: 2400x1600 pixels")
            print(f"🎯 Left side: Regular prints with fixed sheet structure AND FRAMES")
            print(f"🎯 Right side: Trio composites with customer images in frame openings")
            print(f"🖼️ Frames applied: 8x10, 10x13, and 3 individual 5x7s have Black frames")
            print(f"🔄 3 5x7 pairs intelligently split: 3 framed individuals + 1 unframed + 1 pair")
            print(f"🏷️ Banners demonstrated: ARTIST SERIES, RETOUCH, and ARTIST SERIES + RETOUCH overlays")
            
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
    test_corrected_preview_v2() 