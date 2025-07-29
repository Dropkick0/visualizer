from pathlib import Path
from app.fm_dump_parser import parse_fm_dump


def test_parse_fm_dump_basic():
    tsv_path = Path(__file__).resolve().parents[1] / "fm_dump.tsv"
    parsed = parse_fm_dump(str(tsv_path))

    assert len(parsed.rows) >= 4
    first = parsed.rows[0]
    assert first.qty == 1
    assert first.code == "1013"
    assert first.imgs == ["0033"]
    assert parsed.frames[0].frame_no == "229"
