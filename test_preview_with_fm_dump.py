#!/usr/bin/env python3
"""Generate a preview using the AHK TSV dump instead of OCR.

Optional command line usage::
    python test_preview_with_fm_dump.py [tsv_path] [dropbox_root] [--extreme] [--debug]

If ``dropbox_root`` is provided, it overrides the ``DROPBOX_ROOT`` environment
variable.
"""

import sys
from pathlib import Path
from typing import List

# Ensure local app imports
sys.path.insert(0, str(Path(__file__).parent))

from app.fm_dump_parser import parse_fm_dump
from app.config import load_product_config, load_config
from app.image_search import create_image_searcher
from app.enhanced_preview import EnhancedPortraitPreviewGenerator
from app.order_from_tsv import rows_to_order_items


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
    if dropbox_root:
        cfg.DROPBOX_ROOT = dropbox_root
        print(f"🔧 Using Dropbox path from AHK: {dropbox_root}")

    if not getattr(cfg, "DROPBOX_ROOT", None):
        print("⚠️  No Dropbox root configured - image search will be unavailable")
        searcher = None
    else:
        searcher = create_image_searcher(cfg)

    existing_images = {}
    if searcher:
        codes = sorted(set(image_codes))
        res = searcher.find_images_by_codes(codes)
        existing_images = {k: v for k, v in res.items() if v}
        missing = [c for c in codes if c not in existing_images]
        print(f"🔍 Found {len(existing_images)} / {len(codes)} codes. Missing: {missing}")
    else:
        print("⚠️ No image searcher – previews will be blank.")

    if extreme:
        order_items = _expand_extremes(order_items)
        print(f"🚨 Extreme test mode: {len(order_items)} items after expansion")

    frame_requirements = determine_frame_requirements_from_items(order_items)

    outdir = Path("app/static/previews")
    outdir.mkdir(parents=True, exist_ok=True)
    gen = EnhancedPortraitPreviewGenerator(products_cfg, existing_images, outdir)
    out = outdir / "fm_dump_preview.png"
    success = gen.generate_size_based_preview_with_composites(order_items, out, frame_requirements, debug=debug)
    
    if success:
        print(f"✅ Preview saved to {out}")
        return True
    else:
        print(f"❌ Failed to generate preview")
        return False


if __name__ == "__main__":
    tsv = "fm_dump.tsv"
    dropbox_arg: Optional[str] = None
    extreme = False
    debug = False

    args = sys.argv[1:]
    if args:
        tsv = args[0]
        if len(args) > 1 and not args[1].startswith("--"):
            dropbox_arg = args[1]
            args = args[2:]
        else:
            args = args[1:]

        if "--extreme" in args:
            extreme = True
        if "--debug" in args:
            debug = True

    run_preview(tsv, extreme, debug, dropbox_arg)
