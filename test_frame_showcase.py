#!/usr/bin/env python3

"""
Frame Showcase Test - Comprehensive demonstration of all frame types and sizes

This test creates a preview showing examples of both Black and Cherry frames
for each supported size: 5x7, 8x10, 10x13, 16x20, 20x24
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.enhanced_preview import EnhancedPortraitPreviewGenerator
from app.config import load_product_config


def main():
    print("🖼️ FRAME SHOWCASE - Black & Cherry Frames for All Sizes")
    print("=" * 80)
    
    # Load configurations and images
    try:
        products_config = load_product_config()
        print(f"✅ Loaded {len(products_config.get('products', []))} product configurations")
    except Exception as e:
        print(f"❌ Failed to load product config: {e}")
        return
    
    # Found images from Dropbox search (same as working test)
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
    
    if len(existing_images) < 4:
        print(f"❌ Need at least 4 demo images. Found: {list(existing_images.keys())}")
        return
    
    print(f"📸 Using {len(existing_images)} actual images")
    
    # Create preview generator
    output_dir = Path("app/static/previews")
    generator = EnhancedPortraitPreviewGenerator(products_config, existing_images, output_dir)
    
    print(f"\n🖼️ FRAME SHOWCASE SETUP:")
    print(f"========================================")
    print(f"BLACK FRAMES: 5x7, 8x10, 10x13, 16x20, 20x24 (one of each)")
    print(f"CHERRY FRAMES: 5x7, 8x10, 10x13, 16x20, 20x24 (one of each)")
    print(f"Total: 10 framed items demonstrating all frame types and sizes")
    
    # Create comprehensive order items showing all frame types and sizes
    order_items = []
    
    print(f"\n📋 FRAME SHOWCASE BREAKDOWN:")
    print(f"============================================")
    
    # BLACK FRAMES - One of each size
    print(f"🖤 BLACK FRAME EXAMPLES:")
    sizes_and_codes = [
        ("20x24", "2024", "0033", "20x24 with Black Frame"),
        ("16x20", "1620", "0039", "16x20 with Black Frame"),
        ("10x13", "1013", "0044", "10x13 with Black Frame"),
        ("8x10", "810", "0102", "8x10 with Black Frame"),
        ("5x7", "570_sheet", "0033", "5x7 with Black Frame (will be split to individual)")
    ]
    
    for size, product_code, image_code, description in sizes_and_codes:
        print(f"   • {description} using image {image_code}")
        
        if size == "5x7":
            # 5x7 pair that will be split to individual with black frame
            order_items.append({
                'product_slug': '5x7_sheet_landscape', 
                'product_code': product_code, 
                'quantity': 1, 
                'image_codes': [image_code, image_code],  # Same image repeated
                'size_category': 'medium_sheet',
                'sheet_type': 'landscape_2x1',
                'display_name': f'5x7 Landscape Sheet (2 of {image_code}) - BLACK FRAME'
            })
        else:
            order_items.append({
                'product_slug': f'{size.replace("x", "_")}_basic',
                'product_code': product_code,
                'quantity': 1,
                'image_codes': [image_code],
                'size_category': 'large_print',
                'display_name': f'{size} Basic - BLACK FRAME'
            })
    
    print(f"\n🌰 CHERRY FRAME EXAMPLES:")
    # CHERRY FRAMES - One of each size
    cherry_sizes_and_codes = [
        ("20x24", "2024", "0039", "20x24 with Cherry Frame"),
        ("16x20", "1620", "0044", "16x20 with Cherry Frame"),
        ("10x13", "1013", "0102", "10x13 with Cherry Frame"),
        ("8x10", "810", "0033", "8x10 with Cherry Frame"),
        ("5x7", "570_sheet", "0039", "5x7 with Cherry Frame (will be split to individual)")
    ]
    
    for size, product_code, image_code, description in cherry_sizes_and_codes:
        print(f"   • {description} using image {image_code}")
        
        if size == "5x7":
            # 5x7 pair that will be split to individual with cherry frame
            order_items.append({
                'product_slug': '5x7_sheet_landscape', 
                'product_code': product_code, 
                'quantity': 1, 
                'image_codes': [image_code, image_code],  # Same image repeated
                'size_category': 'medium_sheet',
                'sheet_type': 'landscape_2x1',
                'display_name': f'5x7 Landscape Sheet (2 of {image_code}) - CHERRY FRAME'
            })
        else:
            order_items.append({
                'product_slug': f'{size.replace("x", "_")}_basic',
                'product_code': product_code,
                'quantity': 1,
                'image_codes': [image_code],
                'size_category': 'large_print',
                'display_name': f'{size} Basic - CHERRY FRAME'
            })
    
    # Add some unframed items for comparison
    print(f"\n⚪ UNFRAMED EXAMPLES (for comparison):")
    print(f"   • 1 8x10 unframed")
    print(f"   • 1 5x7 pair unframed")
    order_items.extend([
        {
            'product_slug': '8x10_basic',
            'product_code': '810',
            'quantity': 1,
            'image_codes': ['0044'],
            'size_category': 'large_print',
            'display_name': '8x10 Basic - UNFRAMED'
        },
        {
            'product_slug': '5x7_sheet_landscape', 
            'product_code': '570_sheet', 
            'quantity': 1, 
            'image_codes': ['0044', '0044'],  # Same image repeated
            'size_category': 'medium_sheet',
            'sheet_type': 'landscape_2x1',
            'display_name': f'5x7 Landscape Sheet (2 of 0044) - UNFRAMED'
        }
    ])
    
    print(f"\n✅ TOTAL ORDER ITEMS: {len(order_items)}")
    
    # Define frame requirements - 2 of each size (one black, one cherry)
    frame_requirements = {
        "5x7": 2,    # 1 black + 1 cherry
        "8x10": 2,   # 1 black + 1 cherry  
        "10x13": 2,  # 1 black + 1 cherry
        "16x20": 2,  # 1 black + 1 cherry
        "20x24": 2   # 1 black + 1 cherry
    }
    
    # Define frame style preferences - alternate between black and cherry
    frame_style_preferences = {
        "5x7": "Black",    # First 5x7 gets black, second will get cherry automatically due to processing order
        "8x10": "Black",   # First 8x10 gets black, second will get cherry
        "10x13": "Black",  # First 10x13 gets black, second will get cherry  
        "16x20": "Black",  # First 16x20 gets black, second will get cherry
        "20x24": "Black"   # First 20x24 gets black, second will get cherry
    }
    
    print(f"\n🖼️ FRAME REQUIREMENTS:")
    print(f"========================================")
    for size, qty in frame_requirements.items():
        print(f"   • {qty}x {size} frames (1 Black + 1 Cherry each)")
    
    print(f"\n🚀 Generating Frame Showcase Preview...")
    print(f"📐 Layout will show:")
    print(f"   • Black and Cherry frames side by side for size comparison") 
    print(f"   • Frame thickness and positioning examples")
    print(f"   • Same image within each sheet (no mixed images)")
    print(f"   • All supported frame sizes: 5x7, 8x10, 10x13, 16x20, 20x24")
    
    try:
        success = generator.generate_frame_showcase_preview(
            order_items, 
            "app/static/previews/frame_showcase_black_and_cherry.png",
            frame_requirements
        )
        
        if success:
            print(f"\n✅ Frame Showcase created successfully!")
            print(f"📁 Saved to: app/static/previews/frame_showcase_black_and_cherry.png")
            print(f"🖼️ Preview shows all frame types with both Black and Cherry examples")
            print(f"📏 Perfect for dialing in frame thickness constants!")
        else:
            print(f"❌ Failed to create frame showcase")
            
    except Exception as e:
        print(f"❌ Error creating frame showcase: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 