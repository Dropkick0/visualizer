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
    rows_to_order_items,
    determine_frame_requirements_from_items,
)


def run_preview(tsv_path: str = "fm_dump.tsv") -> bool:
    products_cfg = load_product_config()

    print("\n🔍 Step 1: Load AHK TSV Export")
    parsed = parse_fm_dump(tsv_path)
    rows = parsed.rows
    print(f"✅ Loaded {len(rows)} rows from TSV")

    print("\n🔄 Step 2: Map TSV rows")
    order_items = rows_to_order_items(parsed.rows, parsed.frames, products_cfg, parsed.retouch_imgs)
    image_codes = [c for r in rows for c in r.imgs]
    print(f"✅ Created {len(order_items)} order items")

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

    frame_requirements = determine_frame_requirements_from_items(order_items)

    outdir = Path("app/static/previews")
    outdir.mkdir(parents=True, exist_ok=True)
    gen = EnhancedPortraitPreviewGenerator(products_cfg, existing_images, outdir)
    out = outdir / "fm_dump_preview.png"
    gen.generate_size_based_preview_with_composites(order_items, out, frame_requirements)
    print(f"✅ Preview saved to {out}")
    return True


if __name__ == "__main__":
    tsv = sys.argv[1] if len(sys.argv) > 1 else "fm_dump.tsv"
    run_preview(tsv)
