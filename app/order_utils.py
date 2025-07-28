from typing import Dict, List


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
