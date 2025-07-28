#!/usr/bin/env python3
"""
Test Enhanced Preview Generator - OCR-based V3 WITH FRAMES (FIXED VERSION)
Uses our working OCRExtractor with precise bounding boxes to automatically detect order items
"""

import sys
from pathlib import Path
import re
from typing import Dict, List

from app.order_utils import expand_row_to_items, apply_frames_to_items

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

def extract_image_codes_from_text(text: str) -> List[str]:
    """Extract 4-digit image codes from text"""
    codes = re.findall(r'\b(\d{4})\b', text)
    return list(set(codes))  # Remove duplicates


def determine_frame_requirements_from_items(order_items: List[Dict]) -> Dict[str, int]:
    """Determine frame requirements based on order items"""
    frame_requirements = {
        "5x7": 0,
        "8x10": 0,
        "10x13": 0,
        "16x20": 0,
        "20x24": 0
    }
    
    for item in order_items:
        size_category = item.get('size_category', '')
        if size_category == 'large':
            # Individual prints can have frames
            if '8x10' in item.get('display_name', ''):
                frame_requirements["8x10"] += item.get('quantity', 1)
            elif '10x13' in item.get('display_name', ''):
                frame_requirements["10x13"] += item.get('quantity', 1)
            elif '16x20' in item.get('display_name', ''):
                frame_requirements["16x20"] += item.get('quantity', 1)
            elif '20x24' in item.get('display_name', ''):
                frame_requirements["20x24"] += item.get('quantity', 1)
        elif size_category == 'medium_sheet':
            # 5x7 pairs can be split for framing
            frame_requirements["5x7"] += item.get('quantity', 1) * 2  # Each pair = 2 individual 5x7s
    
    # Limit frames to reasonable numbers (based on typical order)
    frame_requirements["5x7"] = min(frame_requirements["5x7"], 3)  # Max 3 frames for 5x7s
    frame_requirements["8x10"] = min(frame_requirements["8x10"], 1)  # Max 1 frame for 8x10
    frame_requirements["10x13"] = min(frame_requirements["10x13"], 1)  # Max 1 frame for 10x13
    
    return frame_requirements

def test_ocr_based_preview_fixed(screenshot_path: str):
    """Test with our working OCRExtractor and precise bounding boxes"""
    print("🎨 Enhanced Portrait Preview - OCR-based Detection V3 (FIXED VERSION)")
    print("=" * 80)
    
    try:
        from app.ocr_extractor import OCRExtractor
        from app.enhanced_preview import EnhancedPortraitPreviewGenerator
        from app.config import load_product_config

        # Load configuration
        products_config = load_product_config()
        products_cfg = products_config["products_by_code"]
        print(f"✅ Loaded {len(products_config.get('products', []))} product configurations")
        
        # Step 1: OCR Extraction with our working system
        print("\n🔍 Step 1: OCR Extraction with Production OCRExtractor")
        print("=" * 60)
        
        screenshot_file = Path(screenshot_path)
        if not screenshot_file.exists():
            print(f"❌ Screenshot not found: {screenshot_file}")
            return False
        
        # Initialize our working OCR extractor
        extractor = OCRExtractor()
        
        # Extract rows using our proven bounding boxes
        print(f"📸 Extracting from: {screenshot_file}")
        try:
            rows = extractor.extract_rows(str(screenshot_file))
        except Exception as e:
            print(f"❌ OCR extraction failed: {e}")
            return False

        if not rows:
            print("❌ No rows extracted from OCR")
            return False

        print("✅ OCR extraction successful:")
        print(f"   • Rows extracted: {len(rows)}")
        for i, row in enumerate(rows, 1):
            print(f"   Row {i}: Qty:{row.qty} Code:{row.code} Imgs:{row.imgs}")

        # Merge all row text for parsing
        all_codes = " ".join(r.code for r in rows)
        all_desc = " ".join(r.desc for r in rows)
        all_imgs = " ".join(r.imgs for r in rows)

        # Step 2: Parse extracted data
        print("\n📋 Step 2: Parsing Extracted Data")
        print("=" * 60)
        
        # Extract product codes from the code column
        product_codes = re.findall(r'\b(\d+(?:\.\d+)?)\b', all_codes)
        product_codes = [c for c in product_codes if len(c) >= 3]

        # Extract image codes from the images column and description
        all_text = f"{all_imgs} {all_desc}"
        print(f"   • OCR text for codes: '{all_text[:100]}...'")
        image_codes = extract_image_codes_from_text(all_text)


        if not image_codes:
            print("   • No image codes detected in OCR")
        
        print(f"   • Found product codes: {product_codes}")
        print(f"   • Found image codes: {image_codes}")
        
        # Step 3: Map to order items
        print("\n🔄 Step 3: Mapping to Order Items")
        print("=" * 60)

        order_items = []
        for r in rows:
            base = {"qty": r.qty or 0, "code": r.code, "imgs": r.imgs}
            try:
                order_items.extend(expand_row_to_items(base, products_cfg))
            except KeyError as e:
                print(f"❌ {e} in {base}")
                return False

        order_items = apply_frames_to_items(order_items, extractor.frame_counts.copy())
        
        if not order_items:
            print("❌ No order items created")
            return False
        
        print(f"✅ Created {len(order_items)} order items")
        
        # Step 4: Image Discovery
        print("\n📸 Step 4: Image Discovery")
        print("=" * 60)
        

        # Use proper image search functionality
        from app.image_search import create_image_searcher
        from app.config import load_config
        
        config = load_config()

        # If DROPBOX_ROOT not configured, try local '8017_Lab_Order' folder
        if not getattr(config, 'DROPBOX_ROOT', None):
            local_dropbox = Path(__file__).parent / '8017_Lab_Order'
            print(f"   • Looking for local Dropbox folder: {local_dropbox}")
            if local_dropbox.exists():
                config.DROPBOX_ROOT = str(local_dropbox)
                print(f"   • Using local Dropbox folder: {local_dropbox}")
            else:
                print("   ⚠️ Local Dropbox folder not found")

        searcher = create_image_searcher(config)

        
        if searcher:
            print(f"   • Searching in: {searcher.dropbox_root}")
            
            # Use the actual image search system with subfolder support
            image_search_results = searcher.find_images_by_codes(image_codes)
            
            existing_images = {}
            total_found = 0
            for code, image_paths in image_search_results.items():
                if image_paths:
                    existing_images[code] = image_paths  # Keep as list of Path objects
                    total_found += len(image_paths)
            
            print(f"   • Found {total_found} total images for {len(existing_images)} codes:")
            for code, paths in existing_images.items():
                # Show relative path from Dropbox root for better readability
                try:
                    relative_path = paths[0].relative_to(searcher.dropbox_root)
                    print(f"     - {code}: {relative_path} (and {len(paths)-1} more)" if len(paths) > 1 else f"     - {code}: {relative_path}")
                except Exception:
                    print(f"     - {code}: {paths[0].name} (and {len(paths)-1} more)" if len(paths) > 1 else f"     - {code}: {paths[0].name}")
        else:
            print("   ⚠️ Image searcher not available - check Dropbox configuration")
            existing_images = {}
        
        # Step 5: Frame Requirements
        print("\n🖼️ Step 5: Determining Frame Requirements")
        print("=" * 60)
        
        frame_requirements = determine_frame_requirements_from_items(order_items)
        print(f"   • Frame requirements: {frame_requirements}")
        
        # Step 6: Generate Preview
        print("\n🚀 Step 6: Generating Preview")
        print("=" * 60)
        
        # Create output directory
        output_dir = Path("app/static/previews")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize generator
        generator = EnhancedPortraitPreviewGenerator(products_config, existing_images, output_dir)
        
        # Generate preview
        output_path = output_dir / "ocr_extracted_preview_with_frames.png"
        
        print("🎨 Generating preview from OCR-extracted data...")
        print(f"   • Order items: {len(order_items)}")
        print(f"   • Images: {len(existing_images)}")
        print(f"   • Output: {output_path}")
        
        success = generator.generate_size_based_preview_with_composites(
            order_items, output_path, frame_requirements
        )
        
        if success:
            print("✅ OCR-based preview created successfully!")
            print(f"📁 Saved to: {output_path}")
            print("🎯 Successfully used working OCR to extract and render actual FileMaker order")
            print("📊 Order contained:")
            for item in order_items:
                print(f"   • {item.get('display_name', item['product_name'])}")
            return True
        else:
            print("❌ Failed to create preview")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_corrected_preview_v2_with_ocr_FIXED.py <screenshot_path>")
        sys.exit(1)

    screenshot_path = sys.argv[1]
    success = test_ocr_based_preview_fixed(screenshot_path)

    if not success:
        print("\nPress Enter to exit...")
        input()