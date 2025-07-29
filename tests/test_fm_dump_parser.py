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


def test_complimentary_deduplicated():
    tsv_path = Path(__file__).resolve().parents[1] / "fm_dump.tsv"
    parsed = parse_fm_dump(str(tsv_path))
    from app.order_from_tsv import rows_to_order_items
    from app.config import load_product_config

    products_cfg = load_product_config()
    items = rows_to_order_items(parsed.rows, parsed.frames, products_cfg, parsed.retouch_imgs, None)
    comp_count = sum(
        1
        for it in items
        if it.get("complimentary") and "8x10" in it["display_name"]
    )
    assert comp_count == 1
