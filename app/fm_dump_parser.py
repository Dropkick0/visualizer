from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
import csv
import re
import json
from pathlib import Path

@dataclass
class RowTSV:
    idx: int
    qty: Optional[int]
    code: Optional[str]
    desc: Optional[str]
    imgs: List[str]
    artist_series: Optional[str]
    complimentary: bool = False

@dataclass
class FrameReq:
    frame_no: str
    qty: int
    desc: str

@dataclass
class ParsedOrder:
    rows: List[RowTSV]
    frames: List[FrameReq]
    retouch_imgs: List[str]
    directory_pose_no: Optional[str]
    directory_pose_img: Optional[str]
    dir_pose_code: Optional[str] = None
    dir_pose_img: Optional[str] = None


def _to_int(val: str) -> Optional[int]:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _split_imgs(val: str) -> List[str]:
    if not val:
        return []
    parts = re.split(r'[\s,]+', val)
    return [p.zfill(4) for p in parts if p]


def parse_fm_dump(tsv_path: str) -> ParsedOrder:
    with open(tsv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter='\t')
        rows = list(reader)

    by_label = {r['Label']: r['Value'] for r in rows if r.get('Label')}

    # retouch images
    retouch_images = []
    for i in range(1, 9):
        for key in (f'RETOUCH Img #{i}', f'Retouch Img #{i}', f'ReTOUCH Img #{i}'):
            val = by_label.get(key)
            if val is not None:
                val = val.strip()
                if val:
                    retouch_images.append(val)
                break
    retouch_images = [v for v in retouch_images if v]

    frames: List[FrameReq] = []
    for i in range(1,7):
        num = by_label.get(f'Frame# F{i}', '').strip()
        qty = _to_int(by_label.get(f'Frame Qty F{i}', '').strip()) or 0
        desc = by_label.get(f'Frame Desc F{i}', '').strip()
        if num or desc or qty:
            frames.append(FrameReq(frame_no=num, qty=qty, desc=desc))

    order_rows: List[RowTSV] = []
    for i in range(1,19):
        qty = _to_int(by_label.get(f'Qty R{i}', '').strip())
        code = by_label.get(f'Prod R{i}', '').strip() or None
        desc = by_label.get(f'Desc R{i}', '').strip()
        imgs = _split_imgs(by_label.get(f'Img # R{i}', '').strip())
        artist = by_label.get(f'Artist Series R{i}', '').strip() or None
        if not any([qty, code, desc, imgs, artist]):
            continue
        order_rows.append(RowTSV(idx=i, qty=qty, code=code, desc=desc or None, imgs=imgs, artist_series=artist))

    pose_img = by_label.get('Directory Pose Image #', '').strip()
    if pose_img:
        pose_code = by_label.get('Directory Pose Order #', '').strip() or '002'
        order_rows.append(
            RowTSV(
                idx=0,
                qty=1,
                code=pose_code,
                desc='Complimentary 8x10',
                imgs=[pose_img.zfill(4)],
                artist_series=None,
                complimentary=True,
            )
        )

    parsed = ParsedOrder(
        rows=order_rows,
        frames=frames,
        retouch_imgs=retouch_images,
        directory_pose_no=by_label.get('Directory Pose Order #', '').strip() or None,
        directory_pose_img=by_label.get('Directory Pose Image #', '').strip() or None,
    )

    # also expose as dir_pose_* for downstream helpers
    parsed.dir_pose_code = by_label.get('Directory Pose Order #', '').strip() or None
    parsed.dir_pose_img = by_label.get('Directory Pose Image #', '').strip() or None
    try:
        tmp = Path('tmp')
        tmp.mkdir(exist_ok=True)
        with open(tmp / 'fm_dump_parsed.json', 'w', encoding='utf-8') as jf:
            json.dump(asdict(parsed), jf, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return parsed
