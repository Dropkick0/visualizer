from typing import Dict, List

# Simple product specification used for tests
PRODUCT_SPECS = {
    'wallets_8_sheet': {
        'name': 'Wallet Sheet of 8',
        'size': '5x7',
        'category': 'sheet',
    },
    '5x7_pair': {
        'name': '5x7 Pair',
        'size': '5x7',
        'category': 'sheet',
        'frame_eligible': True,
        'frame_qty': 2,
    },
    '3.5x5_sheet4': {
        'name': '3.5x5 Sheet of 4',
        'size': '3.5x5',
        'category': 'sheet',
    },
    '8x10_basic': {
        'name': '8x10 Basic',
        'size': '8x10',
        'category': 'print',
    },
    '16x20_basic': {
        'name': '16x20 Basic',
        'size': '16x20',
        'category': 'print',
    },
    '10x13_basic': {
        'name': '10x13 Basic',
        'size': '10x13',
        'category': 'print',
    },
    '20x24_basic': {
        'name': '20x24 Basic',
        'size': '20x24',
        'category': 'print',
    },
    '10x20_trio': {
        'name': '10x20 Trio',
        'size': '10x20',
        'category': 'trio_composite',
    },
    '5x10_trio': {
        'name': '5x10 Trio',
        'size': '5x10',
        'category': 'trio_composite',
    },
}

def expand_row_to_items(row: Dict, product_specs: Dict[str, Dict] = PRODUCT_SPECS) -> List[Dict]:
    """Expand a row definition into individual items preserving image order."""
    imgs = [c.strip() for c in row.get('imgs', '').split(',') if c.strip()]
    qty = int(row.get('qty', 0))
    code = row.get('code')
    spec = product_specs.get(code, {})
    items: List[Dict] = []
    if not imgs:
        # Skip items with no images; attach warning if row is a RowRecord-like
        if isinstance(row.get('warnings'), list):
            row['warnings'].append("No image codes for row; skipping item")
        return items
    for _ in range(qty):
        item = {
            'product_code': code,
            'product_name': spec.get('name', code),
            'size': spec.get('size', ''),
            'images': imgs.copy(),
            'category': spec.get('category', ''),
        }
        if 'frame_eligible' in spec:
            item['frame_eligible'] = spec['frame_eligible']
        if 'frame_qty' in spec:
            item['frame_qty'] = spec['frame_qty']
        items.append(item)
    return items

def apply_frames_to_items(items: List[Dict], frame_counts: Dict[str, Dict[str, int]]):
    """Assign frames to items consuming counts and preferring labeled colors."""
    for it in items:
        # Skip composites; respect frame_eligible flag (default True for prints).
        if it.get('category') == 'trio_composite':
            continue
        if not it.get('frame_eligible', it.get('category') == 'print'):
            continue
        key = it.get('size', '').replace(' ', '')
        pool = frame_counts.get(key)
        if not pool:
            continue
        desired = None
        name = it.get('product_name', '').lower()
        if 'cherry' in name:
            desired = 'cherry'
        elif 'black' in name:
            desired = 'black'
        qty = it.get('frame_qty', 1)
        for color in ([desired] if desired else ['cherry', 'black']):
            if pool.get(color, 0) >= qty:
                it['frame_color'] = color.capitalize()
                pool[color] -= qty
                break
    return items
