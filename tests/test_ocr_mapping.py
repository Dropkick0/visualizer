from pathlib import Path

import pytest

from app.order_utils import expand_row_to_items, apply_frames_to_items

EXPECTED = {
    '0033': {
        'Wallet Sheet of 8': 12,
        '5x7 Pair': 1,
        '3.5x5 Sheet of 4': 3,
        '8x10 Basic': 1,
        '16x20 Basic': 1,
        'retouch': True,
        'artist': True,
    },
    '0102': {
        '10x13 Basic': 1,
        '20x24 Basic': 1,
        'retouch': False,
        'artist': False,
    },
    '0044': {'retouch': False, 'artist': False},
    '0039': {'retouch': False, 'artist': False},
}

EXPECTED_FRAMES_START = {
    '5x7': {'cherry': 2},
    '8x10': {'black': 2},
    '10x13': {'black': 1},
}

EXPECTED_FRAMES_LEFT = {
    '5x7': {'cherry': 0},
    '8x10': {'black': 1},
    '10x13': {'black': 0},
}

EXPECTED_COMPOSITES = {
    '10x20 Trio': ['0033', '0044', '0039'],
    '5x10 Trio #1': ['0039', '0033', '0044'],
    '5x10 Trio #2': ['0039', '0033', '0044'],
    '5x10 Trio #3': ['0039', '0033', '0044'],
}


def test_row_extraction_count():
    pytest.importorskip("cv2")
    from app.ocr_extractor import OCRExtractor
    extractor = OCRExtractor()
    rows = extractor.extract_rows(Path("Test_Full_Screenshot.png"))
    assert len(rows) == 9

# Sample rows based on OCR extraction
ROWS = [
    {'code': 'wallets_8_sheet', 'qty': 12, 'imgs': '0033'},
    {'code': '5x7_pair', 'qty': 1, 'imgs': '0033'},
    {'code': '3.5x5_sheet4', 'qty': 3, 'imgs': '0033'},
    {'code': '8x10_basic', 'qty': 1, 'imgs': '0033'},
    {'code': '16x20_basic', 'qty': 1, 'imgs': '0033'},
    {'code': '10x13_basic', 'qty': 1, 'imgs': '0102'},
    {'code': '20x24_basic', 'qty': 1, 'imgs': '0102'},
]

COMPOSITES = [
    {'product_code': '10x20_trio', 'product_name': '10x20 Trio', 'size': '10x20', 'images': ['0033', '0044', '0039'], 'category': 'trio_composite'},
    {'product_code': '5x10_trio', 'product_name': '5x10 Trio #1', 'size': '5x10', 'images': ['0039', '0033', '0044'], 'category': 'trio_composite'},
    {'product_code': '5x10_trio', 'product_name': '5x10 Trio #2', 'size': '5x10', 'images': ['0039', '0033', '0044'], 'category': 'trio_composite'},
    {'product_code': '5x10_trio', 'product_name': '5x10 Trio #3', 'size': '5x10', 'images': ['0039', '0033', '0044'], 'category': 'trio_composite'},
]

FRAME_COUNTS = {
    '5x7': {'cherry': 2},
    '8x10': {'black': 2},
    '10x13': {'black': 1},
}

ARTIST_CODES = {'0033'}
RETOUCH_CODES = {'0033'}


def count_items_by_image(items):
    out = {}
    for it in items:
        name = it['product_name']
        for code in it['images']:
            out.setdefault(code, {}).setdefault(name, 0)
            out[code][name] += 1
    return out


def test_mapping():
    items = []
    for row in ROWS:
        items.extend(expand_row_to_items(row))
    items.extend(COMPOSITES)

    import copy
    start = copy.deepcopy(FRAME_COUNTS)
    apply_frames_to_items(items, FRAME_COUNTS)
    assert start == EXPECTED_FRAMES_START

    for it in items:
        codes = set(it['images'])
        it['artist_series'] = bool(codes & ARTIST_CODES)
        it['retouch'] = bool(codes & RETOUCH_CODES)
        if it.get('category') == 'trio_composite':
            it['artist_series'] = False
            it['retouch'] = False

    got = count_items_by_image(items)
    # ensure certain images only appear in trios
    for leak_code in ('0039', '0044'):
        for name in got.get(leak_code, {}):
            assert 'Trio' in name, f"{leak_code} used in single item {name}"
    for code, spec in EXPECTED.items():
        for prod, qty in spec.items():
            if prod in ('retouch', 'artist'):
                continue
            assert got.get(code, {}).get(prod, 0) == qty, f"{code} {prod} wrong"

    # check retouch and artist flags
    for it in items:
        codes = set(it['images'])
        if it.get('category') == 'trio_composite':
            assert not it.get('retouch', False)
            assert not it.get('artist_series', False)
        elif codes & {'0033'}:
            assert it['retouch'] is True
            assert it['artist_series'] is True
        else:
            assert not it.get('retouch', False)
            assert not it.get('artist_series', False)

    assert FRAME_COUNTS == EXPECTED_FRAMES_LEFT

    for comp in COMPOSITES:
        name = comp['product_name']
        assert EXPECTED_COMPOSITES[name] == comp['images']
