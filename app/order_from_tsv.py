"""Helpers to convert TSV parsed rows to preview order items."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Iterable

import csv
import re
from pathlib import Path

from .fm_dump_parser import RowTSV, FrameReq


@dataclass
class ProductMeta:
    code: str
    type: str
    name: str
    finish: str | None = None
    size: str | None = None
    frame: str | None = None
    mat: str | None = None


def _parse_products_csv(csv_path: Path) -> Dict[str, ProductMeta]:
    """Build minimal product info table from the spreadsheet exported CSV."""
    products: Dict[str, ProductMeta] = {}
    if not csv_path.exists():
        return products

    with open(csv_path, newline='', encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            if not row:
                continue
            code = row[0].strip()
            if not code:
                continue
            desc = row[1].strip() if len(row) > 1 else ""
            meta = ProductMeta(code=code, type="", name=desc)

            dlow = desc.lower()

            # Determine finish
            if "keepsake" in dlow:
                meta.finish = "KEEPSAKE"
            elif "prestige" in dlow:
                meta.finish = "PRESTIGE"
            else:
                meta.finish = "BASIC"

            # Determine general type/size
            if "wallet" in dlow:
                meta.type = "wallet_sheet"
                meta.size = "wallet"
            elif "3.5x5" in dlow:
                meta.type = "3x5_sheet"
                meta.size = "3.5x5"
            elif "pair 5x7" in dlow:
                meta.type = "5x7_pair"
                meta.size = "5x7"
            elif "5x10" in dlow or desc.startswith("510"):
                meta.type = "trio_5x10"
                meta.size = "5x10"
            elif "10x20" in dlow:
                meta.type = "trio_10x20"
                meta.size = "10x20"
            elif "8x10" in dlow:
                meta.type = "large_print"
                meta.size = "8x10"
            elif "10x13" in dlow:
                meta.type = "large_print"
                meta.size = "10x13"
            elif "16x20" in dlow:
                meta.type = "large_print"
                meta.size = "16x20"
            elif "20x24" in dlow:
                meta.type = "large_print"
                meta.size = "20x24"

            # frame/mat colors for composites
            if "frame" in dlow:
                if "cherry" in dlow:
                    meta.frame = "cherry"
                elif "black" in dlow:
                    meta.frame = "black"
            if "mat" in dlow:
                if "white" in dlow:
                    meta.mat = "white"
                elif "gray" in dlow:
                    meta.mat = "gray"
                elif "creme" in dlow:
                    meta.mat = "creme"
                elif "black" in dlow and "frame" not in dlow:
                    meta.mat = "black"

            products[code] = meta

    return products


# Build PRODUCT table on import
PRODUCTS = _parse_products_csv(Path("POINTS SHEET & CODES.csv"))


def _img_list_contains(imgs: Iterable[str], search: Iterable[str]) -> bool:
    lookup = set(search)
    return any(img in lookup for img in imgs)


def rows_to_order_items(
    rows: List[RowTSV],
    frames: List[FrameReq],
    products_cfg: Dict[str, ProductMeta] | Dict[str, Dict],
    retouch_imgs: List[str],
) -> List[Dict]:
    """Convert TSV rows to simplified order item dicts used by the preview."""

    items: List[Dict] = []
    retouch_set = set(retouch_imgs)

    for r in rows:
        if not r.code:
            continue

        meta = PRODUCTS.get(r.code)
        if not meta:
            # unknown code - skip
            continue

        qty = r.qty or 1

        base = {
            "code": r.code,
            "product_code": r.code,
            "product_slug": r.code,
            "product_name": meta.name,
            "display_name": meta.name,
            "qty": qty,
            "codes": r.imgs,
            "artist_series": bool(r.artist_series),
            "artist_series_label": r.artist_series,
            "retouch": _img_list_contains(r.imgs, retouch_set),
            "finish": meta.finish or "BASIC",
        }

        if meta.type.startswith("trio_"):
            imgs = (r.imgs + ["", "", ""])[:3]
            base.update(
                {
                    "category": "trio_composite",
                    "size": meta.size,
                    "frame_color": meta.frame,
                    "mat_color": meta.mat,
                    "codes": imgs,
                }
            )
            items.append(base)
        elif meta.type == "wallet_sheet":
            base.update({"category": "WALLET8", "size": "wallet"})
            for _ in range(qty):
                items.append(base.copy())
        elif meta.type == "3x5_sheet":
            base.update({"category": "SHEET3x5", "size": "3.5x5"})
            for _ in range(qty):
                items.append(base.copy())
        elif meta.type == "5x7_pair":
            base.update({"category": "ALL_5x7", "size": "5x7"})
            for _ in range(qty):
                items.append(base.copy())
        elif meta.type == "large_print":
            base.update({"category": "large_print", "size": meta.size})
            for _ in range(qty):
                items.append(base.copy())
        else:
            # Unknown type fallback
            base.update({"category": "other", "size": meta.size})
            for _ in range(qty):
                items.append(base.copy())

    # Apply frame information from FrameReq
    _apply_frame_requirements(items, frames)

    return items


def _apply_frame_requirements(items: List[Dict], frames: List[FrameReq]):
    """Mark items with frame information based on frame table from TSV."""
    if not frames:
        return

    # Build simple map size->color->qty
    counts: Dict[str, Dict[str, int]] = {}
    for fr in frames:
        d = fr.desc.lower()
        m = re.search(r"(\d+\s*x\s*\d+)", d)
        if not m:
            continue
        size = m.group(1).replace(" ", "")
        color = "black"
        if "cherry" in d:
            color = "cherry"
        counts.setdefault(size, {}).setdefault(color, 0)
        counts[size][color] += fr.qty

    for it in items:
        if it.get("category") not in {"large_print", "ALL_5x7"}:
            continue
        size_key = it.get("size", "")
        pools = counts.get(size_key)
        if not pools:
            continue
        preferred = None
        if "cherry" in it.get("code", ""):
            preferred = "cherry"
        for color in ([preferred] if preferred else ["cherry", "black"]):
            if pools.get(color, 0) > 0:
                it["has_frame"] = True
                it["frame_color"] = color
                pools[color] -= 1
                break


def sort_large_print(items: List[Dict]) -> List[Dict]:
    """Ensure complimentary 8x10 items appear last in the list."""

    def _code(obj: Dict) -> str:
        if "code" in obj:
            return obj["code"]
        if "item" in obj and isinstance(obj["item"], dict):
            return obj["item"].get("code") or obj["item"].get("product_code")
        return ""

    comp_codes = {"001", "002", "003", "9111", "9112", "9113"}
    comp = [o for o in items if _code(o) in comp_codes]
    normal = [o for o in items if _code(o) not in comp_codes]
    return normal + comp



