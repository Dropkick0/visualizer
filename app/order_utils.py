from typing import Dict, List
import re

from .fm_dump_parser import RowTSV as Row, FrameReq as Frame


def expand_row_to_items(row: Dict, products_cfg: Dict[str, Dict]) -> List[Dict]:
    """Expand ONE PORTRAIT row (qty/code/imgs) to concrete items the preview expects."""
    qty = int(row.get("qty") or 0)
    if qty <= 0:
        return []

    code = (row.get("code") or "").strip()
    if code not in products_cfg:
        raise KeyError(f"Unknown product code '{code}'")

    spec = products_cfg[code]
    imgs = [c.strip() for c in (row.get("imgs") or "").split(',') if c.strip()]

    items: List[Dict] = []
    for _ in range(qty):
        item = {
            "product_code": code,
            "product_name": spec.get("name", code),
            "display_name": spec.get("display_name", spec.get("name", code)),
            # generator uses .size and .category to group
            "size": spec.get("size") or spec.get("dimensions", ""),
            "size_category": spec.get("size_category") or spec.get("category", ""),
            "category": spec.get("category") or spec.get("size_category", ""),
            "images": imgs.copy(),
            "frame_eligible": spec.get("frame_eligible", spec.get("category") in ("print", "large_print")),
            "frame_qty": spec.get("frame_qty", 1),
            "quantity": 1,
        }
        items.append(item)
    return items


def apply_frames_to_items(items: List[Dict], frame_counts: Dict[str, Dict[str, int]]):
    """Consume frame_counts (size->color->qty) and tag items with frame_color."""
    for it in items:
        if not it.get("frame_eligible"):
            continue
        size_key = it.get("size", "").replace(" ", "")
        pool = frame_counts.get(size_key)
        if not pool:
            continue

        needed = it.get("frame_qty", 1)
        preferred = None
        name_l = it.get("product_name", "").lower()
        if "cherry" in name_l:
            preferred = "cherry"
        elif "black" in name_l:
            preferred = "black"

        for color in ([preferred] if preferred else ["cherry", "black"]):
            if pool.get(color, 0) >= needed:
                it["frame_color"] = color.capitalize()
                pool[color] -= needed
                break

    return items


def rows_to_products(rows: List[Row], products_cfg: Dict[str, Dict], retouch_codes: List[str] | None = None, artist_flags: Dict[int, str] | None = None) -> List[Dict]:
    """Convert parsed rows to order items using product config."""
    items: List[Dict] = []
    retouch_set = set(retouch_codes or [])
    artist_flags = artist_flags or {}

    for idx, row in enumerate(rows, 1):
        row_dict = {
            "qty": row.qty,
            "code": row.code,
            "imgs": ",".join(row.imgs),
        }
        try:
            row_items = expand_row_to_items(row_dict, products_cfg)
        except KeyError:
            continue

        for it in row_items:
            it["retouch"] = bool(set(row.imgs) & retouch_set)
            it["artist_series"] = bool(row.artist_series or artist_flags.get(idx))
        items.extend(row_items)

    return items


def frames_to_counts(frames: List[Frame]) -> Dict[str, Dict[str, int]]:
    """Convert Frame entries to size/color counts for apply_frames_to_items."""
    counts: Dict[str, Dict[str, int]] = {}
    for fr in frames:
        desc_l = fr.desc.lower()
        m = re.search(r"(\d+\s*x\s*\d+)", desc_l)
        if not m:
            continue
        size = m.group(1).replace(" ", "")
        color = "black"
        if "cherry" in desc_l:
            color = "cherry"
        elif "white" in desc_l:
            color = "white"
        counts.setdefault(size, {}).setdefault(color, 0)
        counts[size][color] += fr.qty
    return counts
