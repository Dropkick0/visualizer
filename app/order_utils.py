from typing import Dict, List
import re
from copy import deepcopy

from .fm_dump_parser import RowTSV as Row, FrameReq as Frame
from .frame_overlay import FrameSpec


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


def _extract_size_from_item(item: Dict) -> str | None:
    """Return size like '8x10' from item fields if possible."""
    ps = item.get("product_slug", "")
    m = re.search(r"(\d+x\d+)", ps)
    if m:
        return m.group(1)
    dn = item.get("display_name", "")
    m = re.search(r"(\d+x\d+)", dn)
    if m:
        return m.group(1)
    return None


def apply_frames_to_items_from_meta(items: List[Dict], frame_reqs: List[Frame], meta: Dict[str, Dict[str, str]]):
    """Assign frames to items based on frame metadata."""
    size_buckets: Dict[str, List[Dict]] = {}
    for it in items:
        if it.get("size_category") not in ("large_print", "medium_print"):
            continue
        if it.get("frame_color") or it.get("sheet_type") == "landscape_2x1":
            # skip already framed or 5x7 pair sheets
            continue
        size = _extract_size_from_item(it)
        if not size:
            continue
        size_buckets.setdefault(size, []).append(it)

    for fr in frame_reqs:
        info = meta.get(fr.frame_no)
        if not info:
            continue
        needed = fr.qty or 0
        bucket = size_buckets.get(info["size"], [])
        for it in bucket:
            if needed <= 0:
                break
            if not it.get("frame_color"):
                it["frame_color"] = info["color"]
                it["framed"] = True
                it["has_frame"] = True
                it["frame_spec"] = FrameSpec(info["size"], info["color"].capitalize())
                needed -= 1
        fr.qty = needed

    return items


def normalize_5x7_for_frames(items: List[Dict], frame_reqs: List[Frame], frame_meta: Dict[str, Dict[str, str]]) -> List[Dict]:
    """Convert 5x7 pairs to singles, assign frames, and re-pack leftovers into pairs."""

    frames_needed = 0
    for fr in frame_reqs:
        info = frame_meta.get(fr.frame_no)
        if info and info["size"] == "5x7":
            frames_needed += fr.qty or 0

    if frames_needed == 0:
        return items

    singles: List[Dict] = []
    others: List[Dict] = []

    # explode all 5x7 pairs into singles
    for it in items:
        if it.get("group_hint") == "ALL_5x7" and it.get("sheet_type") == "landscape_2x1":
            img = it["image_codes"][0] if it.get("image_codes") else ""
            for _ in range(2):
                s = deepcopy(it)
                s["product_code"] = "570_individual"
                s["sheet_type"] = "single"
                s["display_name"] = f"5x7 ({s['finish'].title()})"
                s["quantity"] = 1
                s["image_codes"] = [img]
                s.pop("pair_id", None)
                singles.append(s)
        else:
            others.append(it)

    # assign frames to first F singles
    for s in singles:
        if frames_needed <= 0:
            break
        if not s.get("framed"):
            s["framed"] = True
            for fr in frame_reqs:
                info = frame_meta.get(fr.frame_no)
                if not info or info["size"] != "5x7":
                    continue
                if fr.qty and fr.qty > 0:
                    s["frame_color"] = info["color"]
                    fr.qty -= 1
                    frames_needed -= 1
                    break

    framed_singles = [s for s in singles if s.get("framed")]
    unframed_singles = [s for s in singles if not s.get("framed")]

    repacked_pairs: List[Dict] = []
    while len(unframed_singles) >= 2:
        a = unframed_singles.pop(0)
        b = unframed_singles.pop(0)
        pair = deepcopy(a)
        pair["product_code"] = "570_sheet"
        pair["sheet_type"] = "landscape_2x1"
        pair["display_name"] = f"5x7 Pair ({pair['finish'].title()})"
        pair["image_codes"] = [a["image_codes"][0]]
        pair.pop("framed", None)
        pair.pop("frame_color", None)
        repacked_pairs.append(pair)

    final_items = others + framed_singles + repacked_pairs + unframed_singles
    return final_items
