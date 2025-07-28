from dataclasses import dataclass
from typing import List, Optional, Dict
import csv
import re

@dataclass
class Row:
    qty: Optional[int]
    code: Optional[str]
    desc: str
    imgs: List[str]
    artist_series: Optional[str]

@dataclass
class Frame:
    number: str
    qty: int
    desc: str

@dataclass
class ParsedOrder:
    rows: List[Row]
    frames: List[Frame]
    retouch_images: List[str]
    directory_pose_order: Optional[str]
    directory_pose_image: Optional[str]
    artist_series_flags: Dict[int, str]


def _to_int(val: str) -> Optional[int]:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _split_imgs(val: str) -> List[str]:
    if not val:
        return []
    parts = re.split(r'[\s,]+', val)
    return [p for p in parts if p]


def parse_fm_dump(tsv_path: str) -> ParsedOrder:
    with open(tsv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        rows = list(reader)

    by_label = {r['Label']: r['Value'] for r in rows if r.get('Label')}

    # retouch images
    retouch_images = [by_label.get(f'ReTOUCH Img #{i}', by_label.get(f'RETOUCH Img #{i}', '')).strip() for i in range(1,9)]
    retouch_images = [v for v in retouch_images if v]

    frames: List[Frame] = []
    for i in range(1,7):
        num = by_label.get(f'Frame# F{i}', '').strip()
        qty = _to_int(by_label.get(f'Frame Qty F{i}', '').strip()) or 0
        desc = by_label.get(f'Frame Desc F{i}', '').strip()
        if num or desc or qty:
            frames.append(Frame(num, qty, desc))

    order_rows: List[Row] = []
    artist_flags: Dict[int, str] = {}
    for i in range(1,19):
        qty = _to_int(by_label.get(f'Qty R{i}', '').strip())
        code = by_label.get(f'Prod R{i}', '').strip() or None
        desc = by_label.get(f'Desc R{i}', '').strip()
        imgs = _split_imgs(by_label.get(f'Img # R{i}', '').strip())
        artist = by_label.get(f'Artist Series R{i}', '').strip() or None
        if not any([qty, code, desc, imgs, artist]):
            continue
        if artist:
            artist_flags[i] = artist
        order_rows.append(Row(qty, code, desc, imgs, artist))

    parsed = ParsedOrder(
        rows=order_rows,
        frames=frames,
        retouch_images=retouch_images,
        directory_pose_order=by_label.get('Directory Pose Order #', '').strip() or None,
        directory_pose_image=by_label.get('Directory Pose Image #', '').strip() or None,
        artist_series_flags=artist_flags
    )
    return parsed
