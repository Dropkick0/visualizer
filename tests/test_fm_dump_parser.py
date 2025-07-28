from pathlib import Path
from app.fm_dump_parser import parse_fm_dump


def test_parse_sample_tsv():
    tsv_path = Path(__file__).resolve().parents[1] / "fm_dump.tsv"
    parsed = parse_fm_dump(str(tsv_path))

    assert len(parsed.rows) == 6
    # verify first row fields
    first = parsed.rows[0]
    assert first.qty == 1
    assert first.code == "1013"
    assert first.imgs == ["0033"]

    # check frame parsing
    assert len(parsed.frames) == 2
    assert parsed.frames[0].number == "229"
    assert parsed.frames[0].qty == 1

    # retouch images should capture first two codes
    assert parsed.retouch_images[:2] == ["0033", "0517"]
