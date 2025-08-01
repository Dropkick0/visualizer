#!/usr/bin/env python3
"""Generate a preview using the AHK TSV dump instead of OCR.

Optional command line usage::
    python test_preview_with_fm_dump.py [tsv_path] [dropbox_root] [--extreme] [--debug]

If ``dropbox_root`` is provided, it overrides the ``DROPBOX_ROOT`` environment
variable.
"""

import sys
import os
import json
from pathlib import Path
from typing import List

# Ensure local app imports
sys.path.insert(0, str(Path(__file__).parent))

from app.fm_dump_parser import parse_fm_dump
from app.config import load_product_config, load_config
from app.image_search import create_image_searcher
from app.enhanced_preview import EnhancedPortraitPreviewGenerator
from app.order_from_tsv import rows_to_order_items
from app.resource_utils import ensure_resource_dirs

# Handle config files saved with a UTF-8 BOM
with open(Path(__file__).with_name("config.json"), "r", encoding="utf-8-sig") as f:
    CONFIG = json.load(f)
os.environ.setdefault("DROPBOX_ROOT", CONFIG.get("photo_root", ""))
ensure_resource_dirs()


def _expand_extremes(order_items: List[dict]) -> List[dict]:
    """Return a new list of order items with counts amplified for stress tests."""
    extreme_items: List[dict] = []
    for item in order_items:
        extreme_items.append(item)
        if item.get("size_category") == "wallet_sheet":
            extreme_items.extend([item.copy() for _ in range(5)])  # 6x wallets
        elif item.get("size_category") == "trio_composite":
            extreme_items.extend([item.copy() for _ in range(9)])  # 10x trios
        elif item.get("size_category") == "medium_sheet":
            extreme_items.extend([item.copy() for _ in range(3)])  # 4x 5x7s
        elif item.get("size_category") == "large_print":
            extreme_items.extend([item.copy() for _ in range(2)])  # 3x prints

    return extreme_items


from typing import Optional, Dict


def determine_frame_requirements_from_items(order_items: List[dict]) -> Dict[str, int]:
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
        if size_category == 'large_print':
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
    
    # Limit frames to reasonable numbers
    frame_requirements["5x7"] = min(frame_requirements["5x7"], 3)
    frame_requirements["8x10"] = min(frame_requirements["8x10"], 1) 
    frame_requirements["10x13"] = min(frame_requirements["10x13"], 1)
    
    return frame_requirements


def run_preview(tsv_path: str = "fm_dump.tsv", extreme: bool = False, debug: bool = False,
                dropbox_root: Optional[str] = None) -> bool:
    products_cfg = load_product_config()

    print("\n🔍 Step 1: Load AHK TSV Export")
    parsed = parse_fm_dump(tsv_path)
    rows = parsed.rows
    print(f"✅ Loaded {len(rows)} rows from TSV")

    product_codes = [r.code for r in rows if r.code]
    image_codes = [c for r in rows for c in r.imgs]

    print("\n🔄 Step 2: Convert rows to order items")
    order_items = rows_to_order_items(rows, parsed.frames, products_cfg, parsed.retouch_imgs, parsed)
    print(f"✅ Created {len(order_items)} order items")
    from pprint import pprint
    print("\n🔎 ORDER ITEM SNAPSHOT (first 15)")
    pprint([{k: v for k, v in it.items() if k in (
        "product_code","display_name","size_category","complimentary",
        "frame_color","matte_color","finish","image_codes")}
        for it in order_items[:15]])

    # Basic sanity checks on mapped items
    print(f"📊 Order summary:")
    print(f"   • Large prints: {len([it for it in order_items if it['size_category'] == 'large_print'])}")
    print(f"   • Trio composites: {len([it for it in order_items if it['size_category'] == 'trio_composite'])}")
    print(f"   • Medium sheets: {len([it for it in order_items if it['size_category'] == 'medium_sheet'])}")
    print(f"   • Small sheets: {len([it for it in order_items if it['size_category'] == 'small_sheet'])}")
    print(f"   • Wallet sheets: {len([it for it in order_items if it['size_category'] == 'wallet_sheet'])}")

    cfg = load_config()

    # Allow command line to override DROPBOX_ROOT (this is how AHK passes the folder)
    print("\n📁 Step 3: Set up image search")
    if dropbox_root:
        cfg.DROPBOX_ROOT = dropbox_root
        print(f"🔧 Using Dropbox path from AHK: {dropbox_root}")
    
    print(f"📂 Dropbox root: {getattr(cfg, 'DROPBOX_ROOT', 'NOT SET')}")
    
    # Check if the path exists and show what's in it
    from pathlib import Path
    if getattr(cfg, "DROPBOX_ROOT", None):
        dropbox_path = Path(cfg.DROPBOX_ROOT)
        print(f"📁 Dropbox path exists: {dropbox_path.exists()}")
        if dropbox_path.exists():
            try:
                # Show directory structure
                all_files = list(dropbox_path.rglob("*"))
                image_files = [f for f in all_files if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}]
                total_files = len(all_files)
                total_images = len(image_files)
                print(f"📊 Directory contains: {total_files} total files, {total_images} image files")
                
                # Show some example filenames
                if image_files:
                    print("🖼️  Example image files found:")
                    for img in image_files[:10]:  # Show first 10
                        print(f"   • {img.name}")
                    if len(image_files) > 10:
                        print(f"   ... and {len(image_files) - 10} more")
                else:
                    print("⚠️  No image files found in directory!")
                    # Show what IS there
                    print("📁 Directory contents (first 20 items):")
                    for item in all_files[:20]:
                        print(f"   • {item.name} ({'DIR' if item.is_dir() else 'FILE'})")
                        
            except Exception as e:
                print(f"❌ Error scanning directory: {e}")

    if not getattr(cfg, "DROPBOX_ROOT", None):
        print("⚠️  No Dropbox root configured - image search will be unavailable")
        searcher = None
    else:
        searcher = create_image_searcher(cfg)

    print(f"\n🔍 Step 4: Search for images")
    print(f"📝 Image codes to search for: {len(image_codes)} codes")
    print(f"🎯 First 10 codes: {image_codes[:10]}")
    
    existing_images = {}
    if searcher:
        codes = sorted(set(image_codes))
        print(f"🔍 Searching for {len(codes)} unique codes...")
        res = searcher.find_images_by_codes(codes)
        existing_images = {k: v for k, v in res.items() if v}
        missing = [c for c in codes if c not in existing_images]
        
        print(f"✅ Found images for {len(existing_images)} codes")
        print(f"❌ Missing images for {len(missing)} codes")
        
        if existing_images:
            print("\n🖼️  Successfully found images for codes:")
            for code, paths in existing_images.items():
                print(f"   • {code}: {len(paths)} images")
                for path in paths[:2]:  # Show first 2 paths per code
                    print(f"     - {path.name}")
        
        if missing:
            print(f"\n⚠️  Missing images for codes: {missing[:20]}")  # Show first 20 missing
            if len(missing) > 20:
                print(f"     ... and {len(missing) - 20} more")
    else:
        print("⚠️ No image searcher – previews will be blank.")

    if extreme:
        order_items = _expand_extremes(order_items)
        print(f"🚨 Extreme test mode: {len(order_items)} items after expansion")

    frame_requirements = determine_frame_requirements_from_items(order_items)
    print(f"\n🖼️  Step 5: Generate preview")
    print(f"🎨 Frame requirements: {frame_requirements}")

    # Use preview_output directory for compiled exe compatibility
    outdir = Path("preview_output")
    print(f"📁 Output directory: {outdir.absolute()}")
    print(f"📁 Output dir exists before mkdir: {outdir.exists()}")
    
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Output dir exists after mkdir: {outdir.exists()}")
    except Exception as e:
        print(f"❌ Error creating output directory: {e}")
        return False
    
    out = outdir / "fm_dump_preview.png"
    print(f"🎯 Target preview file: {out.absolute()}")
    print(f"📄 Target file exists before generation: {out.exists()}")
    
    print(f"🎨 Creating preview generator...")
    print(f"   • Products config: {type(products_cfg)}")
    print(f"   • Existing images: {len(existing_images)} codes with images")
    print(f"   • Output dir: {outdir}")
    
    try:
        gen = EnhancedPortraitPreviewGenerator(products_cfg, existing_images, outdir)
        print(f"✅ Preview generator created successfully")
    except Exception as e:
        print(f"❌ Error creating preview generator: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"🚀 Starting preview generation...")
    print(f"   • Order items: {len(order_items)}")
    print(f"   • Output file: {out}")
    print(f"   • Frame requirements: {frame_requirements}")
    print(f"   • Debug mode: {debug}")
    
    try:
        success = gen.generate_size_based_preview_with_composites(order_items, out, frame_requirements, debug=debug)
        print(f"🎨 Preview generation completed with success={success}")
    except Exception as e:
        print(f"❌ Error during preview generation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"📄 Target file exists after generation: {out.exists()}")
    if out.exists():
        try:
            file_size = out.stat().st_size
            print(f"📊 Generated file size: {file_size} bytes")
        except Exception as e:
            print(f"⚠️  Error checking file size: {e}")
    
    if success:
        print(f"✅ Preview saved to {out}")
        print(f"🔍 Working directory was: {Path.cwd()}")
        return True
    else:
        print(f"❌ Failed to generate preview")
        print(f"🔍 Working directory was: {Path.cwd()}")
        return False


if __name__ == "__main__":
    # Create a log file to capture what's happening
    import datetime
    log_file = Path("debug_log.txt")
    
    def log_and_print(msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        
        # Write to log file
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
                f.flush()
        except:
            pass  # Don't let logging break the script
        
        # Print to console
        print(log_msg, flush=True)
    
    # Force output to be immediately visible
    import sys
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    log_and_print("🚀 PORTRAIT VISUALIZER STARTING")
    log_and_print("=" * 50)
    log_and_print(f"📝 Command line args: {sys.argv}")
    log_and_print(f"📁 Current working directory: {Path.cwd()}")
    log_and_print(f"🐍 Python version: {sys.version}")
    log_and_print(f"📦 Script location: {Path(__file__).absolute()}")
    
    tsv = "fm_dump.tsv"
    dropbox_arg: Optional[str] = None
    extreme = False
    debug = False

    args = sys.argv[1:]
    log_and_print(f"🔧 Processing args: {args}")
    
    if args:
        tsv = args[0]
        log_and_print(f"📄 TSV file: {tsv}")
        if len(args) > 1 and not args[1].startswith("--"):
            dropbox_arg = args[1]
            log_and_print(f"📁 Dropbox folder: {dropbox_arg}")
            args = args[2:]
        else:
            args = args[1:]

        if "--extreme" in args:
            extreme = True
            log_and_print("🚨 Extreme mode enabled")
        if "--debug" in args:
            debug = True
            log_and_print("🐛 Debug mode enabled")
    
    log_and_print(f"📋 Final parameters:")
    log_and_print(f"   • TSV: {tsv}")
    log_and_print(f"   • Dropbox: {dropbox_arg}")
    log_and_print(f"   • Extreme: {extreme}")
    log_and_print(f"   • Debug: {debug}")
    log_and_print("=" * 50)
    
    try:
        log_and_print("🔄 Starting run_preview function...")
        result = run_preview(tsv, extreme, debug, dropbox_arg)
        log_and_print("=" * 50)
        log_and_print(f"🏁 FINAL RESULT: {'SUCCESS' if result else 'FAILED'}")
        log_and_print("=" * 50)
        
        # Force proper exit code so AHK can detect failure via ErrorLevel
        sys.exit(0 if result else 1)
        
    except Exception as e:
        log_and_print("=" * 50)
        log_and_print(f"💥 FATAL ERROR: {e}")
        import traceback
        error_details = traceback.format_exc()
        log_and_print(f"💥 Stack trace: {error_details}")
        log_and_print("=" * 50)
        
        # Exit with error code on exception
        sys.exit(1)
