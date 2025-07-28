from typing import List, Dict

from .fm_dump_parser import RowTSV, FrameReq
from .order_utils import apply_frames_to_items, frames_to_counts

# Product metadata mapping based on POINTS SHEET & CODES.csv
# Only the subset relevant for preview generation is included.
PRODUCTS: Dict[str, Dict] = {
    "001": {"type": "complimentary_8x10", "finish": "BASIC"},
    "002": {"type": "complimentary_8x10", "finish": "PRESTIGE"},
    "003": {"type": "complimentary_8x10", "finish": "KEEPSAKE"},
    "200": {"type": "wallet_sheet", "finish": "BASIC", "group": "WALLET8"},
    "350": {"type": "3x5_sheet", "finish": "BASIC", "group": "SHEET3x5"},
    "510": {"type": "trio_5x10", "mat": "creme", "frame": "cherry"},
    "510.1": {"type": "trio_5x10", "mat": "white", "frame": "cherry"},
    "510.2": {"type": "trio_5x10", "mat": "gray", "frame": "cherry"},
    "510.3": {"type": "trio_5x10", "mat": "black", "frame": "cherry"},
    "511": {"type": "trio_5x10", "mat": "creme", "frame": "black"},
    "511.1": {"type": "trio_5x10", "mat": "white", "frame": "black"},
    "511.2": {"type": "trio_5x10", "mat": "gray", "frame": "black"},
    "511.3": {"type": "trio_5x10", "mat": "black", "frame": "black"},
    "570": {"type": "5x7_pair", "finish": "BASIC", "group": "ALL_5x7"},
    "571": {"type": "5x7_pair", "finish": "PRESTIGE", "group": "ALL_5x7"},
    "572": {"type": "5x7_pair", "finish": "KEEPSAKE", "group": "ALL_5x7"},
    "810": {"type": "8x10", "finish": "BASIC"},
    "811": {"type": "8x10", "finish": "PRESTIGE"},
    "812": {"type": "8x10", "finish": "KEEPSAKE"},
    "9111": {"type": "complimentary_8x10", "finish": "BASIC"},
    "9112": {"type": "complimentary_8x10", "finish": "PRESTIGE"},
    "9113": {"type": "complimentary_8x10", "finish": "KEEPSAKE"},
    "1013": {"type": "10x13", "finish": "BASIC"},
    "1014": {"type": "10x13", "finish": "PRESTIGE"},
    "1015": {"type": "10x13", "finish": "KEEPSAKE"},
    "1020": {"type": "trio_10x20", "mat": "white", "frame": "black"},
    "1020.1": {"type": "trio_10x20", "mat": "white", "frame": "cherry"},
    "1020.2": {"type": "trio_10x20", "mat": "gray", "frame": "black"},
    "1020.3": {"type": "trio_10x20", "mat": "gray", "frame": "cherry"},
    "1020.4": {"type": "trio_10x20", "mat": "black", "frame": "black"},
    "1020.5": {"type": "trio_10x20", "mat": "black", "frame": "cherry"},
    "1020.6": {"type": "trio_10x20", "mat": "creme", "frame": "black"},
    "1020.7": {"type": "trio_10x20", "mat": "creme", "frame": "cherry"},
    "1620": {"type": "16x20", "finish": "BASIC"},
    "1621": {"type": "16x20", "finish": "PRESTIGE"},
    "1622": {"type": "16x20", "finish": "KEEPSAKE"},
    "2024": {"type": "20x24", "finish": "BASIC"},
    "2025": {"type": "20x24", "finish": "PRESTIGE"},
    "2026": {"type": "20x24", "finish": "KEEPSAKE"},
}


def _sort_large_print(items: List[Dict]) -> List[Dict]:
    normal = [i for i in items if not i.get("complimentary")]
    comp = [i for i in items if i.get("complimentary")]
    return normal + comp


def rows_to_order_items(rows: List[RowTSV], frames: List[FrameReq], products_cfg: Dict, retouch_imgs: List[str]) -> List[Dict]:
    """Convert TSV rows to order item dictionaries."""
    items: List[Dict] = []
    retouch_set = set(retouch_imgs or [])

    for row in rows:
        if not row.code:
            continue
        meta = PRODUCTS.get(row.code)
        if not meta:
            continue
        qty = row.qty or 1
        for _ in range(qty):
            base = {
                "product_code": row.code,
                "image_codes": row.imgs[:],
                "quantity": 1,
                "retouch": any(img in retouch_set for img in row.imgs),
                "artist_series": bool(row.artist_series),
                "finish": meta.get("finish", "BASIC"),
            }
            t = meta["type"]
            if t.startswith("trio_"):
                size = t.split("_")[1]     # "10x20" or "5x10"
                imgs = (row.imgs + ["", "", ""])[:3]
                item = {
                    **base,
                    "product_code": "510.3" if size == "5x10" else "1020.5",
                    "product_slug": f"trio_{size}_composite",
                    "size_category": "trio_composite",
                    "template": "trio_horizontal",
                    "count_images": 3,
                    "image_codes": imgs,
                    "retouch_flags": [img in retouch_set for img in imgs],
                    "frame_color": meta.get("frame", ""),
                    "matte_color": meta.get("mat", ""),
                    "display_name": f"Trio {size} ({meta.get('frame','')})",
                }
                items.append(item)
            elif t == "wallet_sheet":
                item = {
                    **base,
                    "product_code": "200_sheet",
                    "product_slug": "WALLET8",
                    "size_category": "wallet_sheet",
                    "group_hint": "WALLET8",
                    "sheet_type": "2x2",
                    "display_name": "Wallet Sheet",
                }
                items.append(item)
            elif t == "3x5_sheet":
                item = {
                    **base,
                    "product_code": "350_sheet",
                    "product_slug": "SHEET3x5",
                    "size_category": "small_sheet",
                    "group_hint": "SHEET3x5",
                    "sheet_type": "2x2",
                    "display_name": "3.5x5 Sheet",
                }
                items.append(item)
            elif t == "5x7_pair":
                item = {
                    **base,
                    "product_code": "570_sheet",
                    "product_slug": "ALL_5x7",
                    "size_category": "medium_sheet",
                    "group_hint": "ALL_5x7",
                    "sheet_type": "landscape_2x1",
                    "display_name": "5x7 Pair",
                }
                items.append(item)
            elif t == "complimentary_8x10":
                item = {
                    **base,
                    "product_slug": f"8x10_{base['finish'].lower()}_{row.code}",
                    "size_category": "large_print",
                    "complimentary": True,
                    "display_name": "Complimentary 8x10",
                }
                items.append(item)
            else:
                # Large prints
                size = t
                item = {
                    **base,
                    "product_slug": f"{size}_{base['finish'].lower()}_{row.code}",
                    "size_category": "large_print",
                    "display_name": f"{size} {base['finish'].title()}",
                }
                items.append(item)

    # apply frames
    counts = frames_to_counts(frames)
    apply_frames_to_items(items, counts)

    # ensure complimentary last in large print section
    large = [i for i in items if i.get("size_category") == "large_print"]
    others = [i for i in items if i.get("size_category") != "large_print"]
    sorted_large = _sort_large_print(large)
    return others + sorted_large
