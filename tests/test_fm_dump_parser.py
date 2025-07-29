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


def test_single_complimentary_item():
    tsv_path = Path(__file__).resolve().parents[1] / "fm_dump.tsv"
    parsed = parse_fm_dump(str(tsv_path))

    from app.order_from_tsv import rows_to_order_items
    from app.config import load_product_config

    products_cfg = load_product_config()
    items = rows_to_order_items(
        parsed.rows,
        parsed.frames,
        products_cfg,
        parsed.retouch_imgs,
        parsed,
    )
    comps = [it for it in items if it.get("complimentary")]
    assert len(comps) == 1


def test_prestige_not_marked_retouch():
    """Complimentary 8x10 in PRESTIGE finish should not set retouch flag."""
    from app.fm_dump_parser import RowTSV, ParsedOrder
    from app.order_from_tsv import rows_to_order_items
    from app.config import load_product_config

    row = RowTSV(idx=1, qty=1, code="002", desc="Complimentary 8x10", imgs=["0517"], artist_series=False, complimentary=True)
    parsed = ParsedOrder(rows=[row], frames=[], retouch_imgs=[], directory_pose_no=None, directory_pose_img=None)

    products_cfg = load_product_config()
    items = rows_to_order_items(parsed.rows, parsed.frames, products_cfg, parsed.retouch_imgs, parsed)

    comp = next(it for it in items if it.get("complimentary"))
    assert comp["finish"] == "PRESTIGE"
    assert not comp.get("retouch")

def test_no_false_retouch():
    """Ensure complimentary 8x10 items never get retouch flag by finish."""
    tsv_path = Path(__file__).resolve().parents[1] / "fm_dump.tsv"
    parsed = parse_fm_dump(str(tsv_path))

    from app.order_from_tsv import rows_to_order_items
    from app.config import load_product_config

    products_cfg = load_product_config()
    items = rows_to_order_items(parsed.rows, parsed.frames, products_cfg, parsed.retouch_imgs, parsed)

    bogus = [
        it for it in items
        if it.get("display_name", "").startswith("Complimentary 8x10")
        and it.get("retouch")
    ]
    assert not bogus, "Complimentary 8x10 incorrectly marked retouch"
