import pytest
from app.ocr_extractor import OCRExtractor, parse_frames, parse_retouch


def test_row_reconstruction_count():
    ex = OCRExtractor()
    rows = ex.extract_rows("Test_Full_Screenshot.png")
    assert len(rows) == 9


def test_parse_frames_fallback():
    lines = [
        "2 101 8 x 10 black frame P360BLK8x10-GVEBHB",
        "2 5x7 cherry frame",
        "1 202 10 x 13 black frame"
    ]
    counts = parse_frames(lines)
    assert counts == {
        '8x10': {'black': 2},
        '5x7': {'cherry': 2},
        '10x13': {'black': 1}
    }


def test_parse_retouch_codes_artist():
    lines = ["1 Retouch lines 0033", "1 Artist Brush Strokes 0033"]
    items, artist, retouch_codes, artist_codes = parse_retouch(lines)
    assert artist is True
    assert retouch_codes == {'0033'}
    assert artist_codes == {'0033'}
