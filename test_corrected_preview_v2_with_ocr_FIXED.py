#!/usr/bin/env python3
"""
Test Enhanced Preview Generator using FileMaker TSV input.
Parses the TSV dump instead of performing OCR to build order items.
"""

import sys
from pathlib import Path
from typing import Dict, List

from app.order_utils import expand_row_to_items, apply_frames_to_items
from app.fm_dump_parser import parse_fm_dump, ParsedOrder

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))


def determine_frame_requirements_from_items(order_items: List[Dict]) -> Dict[str, int]:
    """Determine frame requirements based on order items"""
    frame_requirements = {"5x7":0,"8x10":0,"10x13":0,"16x20":0,"20x24":0}
    for it in order_items:
        if not it.get("frame_eligible"):
            continue
        size = it.get("size", "").replace(" ", "")
        if size in frame_requirements:
            frame_requirements[size] += it.get("quantity",1)
        elif it.get("product_code") in ("570",):
            frame_requirements["5x7"] += it.get("quantity",1)*2
    return frame_requirements

def test_fm_dump_preview(tsv_path: str):
    """Generate preview solely from FileMaker TSV dump"""
    print("🎨 Portrait Preview - TSV Input")
    print("=" * 80)

    try:
        from app.enhanced_preview import EnhancedPortraitPreviewGenerator
        from app.config import load_product_config

        # Load configuration
        products_config = load_product_config()
        products_cfg = products_config["products_by_code"]
        print(f"✅ Loaded {len(products_config.get('products', []))} product configurations")

        # Step 1: Parse TSV dump
        print("\n🔍 Step 1: Parse FileMaker TSV dump")
        print("=" * 60)

        tsv_file = Path(tsv_path)
        if not tsv_file.exists():
            print(f"❌ TSV file not found: {tsv_file}")
            return False

        parsed: ParsedOrder = parse_fm_dump(str(tsv_file))
        rows = [
            {"qty": r.qty or 0, "code": r.code or "", "imgs": ",".join(r.imgs)}
            for r in parsed.rows
        ]

        print(f"✅ Parsed {len(rows)} rows from TSV")
        for i, r in enumerate(parsed.rows, 1):
            print(f"   Row {i}: Qty:{r.qty} Code:{r.code} Imgs:{' '.join(r.imgs)}")

        # Step 2: Parse extracted data
        print("\n📋 Step 2: Parsing Extracted Data")
        print("=" * 60)
        
        # Extract product codes from the code column
        product_codes = [r.code for r in parsed.rows if r.code]
        image_codes: List[str] = []
        for r in parsed.rows:
            image_codes.extend(r.imgs)
        image_codes = sorted(set(image_codes))

        if not image_codes:
            print("   • No image codes detected in TSV")

        print(f"   • Found product codes: {product_codes}")
        print(f"   • Found image codes: {image_codes}")
        
        # Step 3: Map to order items
        print("\n🔄 Step 3: Mapping to Order Items")
        print("=" * 60)

        from app.ocr_extractor import parse_frames

        order_items = []
        for r in rows:
            try:
                order_items.extend(expand_row_to_items(r, products_cfg))
            except KeyError as e:
                print(f"❌ {e} in {r}")
                return False

        frame_lines = [f"{f.qty} {f.desc}" for f in parsed.frames]
        frame_counts = parse_frames(frame_lines)
        order_items = apply_frames_to_items(order_items, frame_counts)

        # Ensure items have at least one image before preview generation
        order_items = [it for it in order_items if it.get("images")]
        
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
        output_path = output_dir / "tsv_preview_with_frames.png"

        print("🎨 Generating preview from TSV data...")
        print(f"   • Order items: {len(order_items)}")
        print(f"   • Images: {len(existing_images)}")
        print(f"   • Output: {output_path}")
        
        success = generator.generate_size_based_preview_with_composites(
            order_items, output_path, frame_requirements
        )
        
        if success:
            print("✅ TSV-based preview created successfully!")
            print(f"📁 Saved to: {output_path}")
            print("🎯 Successfully parsed TSV dump and rendered FileMaker order")
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
    if len(sys.argv) < 2:
        print("Usage: python test_corrected_preview_v2_with_ocr_FIXED.py <fm_dump.tsv>")
        sys.exit(1)

    tsv_path = sys.argv[1]
    success = test_fm_dump_preview(tsv_path)

    if not success:
        print("\nPress Enter to exit...")
        input()