#!/usr/bin/env python3
"""Generate a preview using the AHK TSV dump instead of OCR."""

import sys
from pathlib import Path
from typing import List

# Ensure local app imports
sys.path.insert(0, str(Path(__file__).parent))

from app.fm_dump_parser import parse_fm_dump
from app.config import load_product_config, load_config
from app.image_search import create_image_searcher
from app.enhanced_preview import EnhancedPortraitPreviewGenerator
from test_corrected_preview_v2_with_ocr_FIXED import (
    determine_frame_requirements_from_items,
)
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


def run_preview(tsv_path: str = "fm_dump.tsv", extreme: bool = False, debug: bool = False) -> bool:
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
    assert any("8x10" in it["display_name"] for it in order_items)
    large_prints = [it for it in order_items if it["size_category"] == "large_print"]
    if any(lp.get("has_frame") for lp in large_prints):
        assert all(lp.get("frame_color") for lp in large_prints if lp.get("has_frame")), "Framed print missing frame_color"
    trio = next(it for it in order_items if it["size_category"] == "trio_composite")
    assert trio["frame_color"].lower() == "cherry"
    assert trio["matte_color"].lower() == "black"

    cfg = load_config()
    if not getattr(cfg, "DROPBOX_ROOT", None):
        cfg.DROPBOX_ROOT = str(Path(__file__).parent / "8017_Lab_Order")
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
    gen.generate_size_based_preview_with_composites(order_items, out, frame_requirements, debug=debug)
    print(f"✅ Preview saved to {out}")
    return True


if __name__ == "__main__":
    tsv = "fm_dump.tsv"
    extreme = False

    debug = False

    if len(sys.argv) > 1:
        if sys.argv[1] == "--extreme":
            extreme = True
        else:
            tsv = sys.argv[1]
            if len(sys.argv) > 2 and sys.argv[2] == "--extreme":
                extreme = True
        if "--debug" in sys.argv:
            debug = True

    run_preview(tsv, extreme, debug)
