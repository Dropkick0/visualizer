#!/usr/bin/env python3
"""Generate a preview using the AHK TSV dump instead of OCR."""

import sys
from pathlib import Path
from typing import List

# Ensure local app imports
sys.path.insert(0, str(Path(__file__).parent))

from app.fm_dump_parser import parse_fm_dump
from app.order_utils import rows_to_products, apply_frames_to_items, frames_to_counts
from app.config import load_product_config, load_config
from app.image_search import create_image_searcher
from app.enhanced_preview import EnhancedPortraitPreviewGenerator


def run_preview(tsv_path: str = "fm_dump.tsv") -> bool:
    products_cfg = load_product_config()
    product_specs = products_cfg["products_by_code"]

    print("\n🔍 Step 1: Load AHK TSV Export")
    parsed = parse_fm_dump(tsv_path)
    rows = parsed.rows
    frames = parsed.frames
    print(f"✅ Loaded {len(rows)} rows from TSV")
    for i, r in enumerate(rows, 1):
        print(f"  Row {i}: Qty:{r.qty} Code:{r.code} Imgs:{','.join(r.imgs)}")

    order_items = rows_to_products(rows, product_specs, parsed.retouch_images, parsed.artist_series_flags)
    frame_counts = frames_to_counts(frames)
    apply_frames_to_items(order_items, frame_counts)
    print(f"✅ Created {len(order_items)} order items")

    config = load_config()
    searcher = create_image_searcher(config)
    existing_images = {}
    if searcher:
        codes: List[str] = list({c for r in rows for c in r.imgs})
        results = searcher.find_images_by_codes(codes)
        existing_images = {k: v for k, v in results.items() if v}
        print(f"🔍 Found images for {len(existing_images)} codes")
    else:
        print("⚠️ Image searcher not available")

    output_dir = Path("app/static/previews")
    output_dir.mkdir(parents=True, exist_ok=True)
    generator = EnhancedPortraitPreviewGenerator(products_cfg, existing_images, output_dir)
    output_path = output_dir / "fm_dump_preview.png"
    success = generator.generate_size_based_preview_with_composites(order_items, output_path, frame_counts)

    if success:
        print(f"✅ Preview saved to {output_path}")
    else:
        print("❌ Failed to generate preview")
    return success


if __name__ == "__main__":
    tsv = sys.argv[1] if len(sys.argv) > 1 else "fm_dump.tsv"
    run_preview(tsv)
