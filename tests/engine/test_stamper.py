import pytest
import pikepdf
from pathlib import Path
from pdf_foliado.engine.stamper import stamp_page, StampParams
from pdf_foliado.utils.pdf_info import get_page_box


def _default_params(**kw) -> StampParams:
    defaults = dict(corner="BR", d1_mm=10.0, d2_mm=15.0,
                    font_name="Helvetica", font_size_pt=12.0, color_hex="#000000")
    defaults.update(kw)
    return StampParams(**defaults)


def test_stamp_does_not_raise(pdf_1p):
    with pikepdf.open(pdf_1p) as pdf:
        stamp_page(pdf.pages[0], "0001", _default_params())


def test_stamp_all_corners(pdf_1p):
    for corner in ("TL", "TR", "BL", "BR"):
        with pikepdf.open(pdf_1p) as pdf:
            stamp_page(pdf.pages[0], "0001", _default_params(corner=corner))


def test_rotated_page_no_raise(pdf_rotated_90):
    with pikepdf.open(pdf_rotated_90) as pdf:
        stamp_page(pdf.pages[0], "0001", _default_params())


def test_rotated_180_no_raise(pdf_rotated_180):
    with pikepdf.open(pdf_rotated_180) as pdf:
        stamp_page(pdf.pages[0], "0001", _default_params())


def test_rotated_270_no_raise(pdf_rotated_270):
    with pikepdf.open(pdf_rotated_270) as pdf:
        stamp_page(pdf.pages[0], "0001", _default_params())


def test_mixed_size_each_page(pdf_mixed_size):
    with pikepdf.open(pdf_mixed_size) as pdf:
        for i, page in enumerate(pdf.pages):
            stamp_page(page, str(i + 1).zfill(4), _default_params())


def test_stamp_produces_valid_pdf(pdf_10p, tmp_path):
    out = tmp_path / "out.pdf"
    with pikepdf.open(pdf_10p) as pdf:
        for i, page in enumerate(pdf.pages):
            stamp_page(page, str(i + 1).zfill(4), _default_params())
        pdf.save(out)
    with pikepdf.open(out) as check:
        assert len(check.pages) == 10


def test_color_red(pdf_1p):
    with pikepdf.open(pdf_1p) as pdf:
        stamp_page(pdf.pages[0], "0001", _default_params(color_hex="#E4002B"))


def test_prefix_in_folio(pdf_1p, tmp_path):
    out = tmp_path / "prefix_out.pdf"
    with pikepdf.open(pdf_1p) as pdf:
        stamp_page(pdf.pages[0], "Folio 0001", _default_params())
        pdf.save(out)
    # just verify it saves without error
    assert out.exists()


def test_font_resource_key_matches_content_stream(pdf_1p, tmp_path):
    """Font resource keys must match what the overlay content stream references."""
    import re
    out = tmp_path / "stamped.pdf"
    with pikepdf.open(pdf_1p) as pdf:
        stamp_page(pdf.pages[0], "0001", _default_params(), owner=pdf)
        pdf.save(out)

    with pikepdf.open(out) as pdf:
        page = pdf.pages[0]
        content = bytes(page["/Contents"].read_bytes()).decode("latin-1")
        font_refs = set(re.findall(r'(/\w+)\s+[\d.]+\s+Tf', content))
        font_keys = set(str(k) for k in page["/Resources"]["/Font"].keys())
        for ref in font_refs:
            assert ref in font_keys, (
                f"Font {ref} referenced in content stream but missing from /Resources/Font"
            )


def test_blank_page_no_contents_stamps_successfully(pdf_1p, tmp_path):
    """Stamping a page with no /Contents must not crash on save."""
    # Strip /Contents from an existing page to simulate a blank page
    p = tmp_path / "blank.pdf"
    with pikepdf.open(pdf_1p) as pdf_src:
        with pikepdf.open(pdf_1p) as pdf_blank:
            if "/Contents" in pdf_blank.pages[0]:
                del pdf_blank.pages[0]["/Contents"]
            pdf_blank.save(p)

    out = tmp_path / "blank_stamped.pdf"
    with pikepdf.open(p) as pdf:
        stamp_page(pdf.pages[0], "0001", _default_params(), owner=pdf)
        pdf.save(out)

    assert out.exists()
    with pikepdf.open(out) as pdf:
        assert len(pdf.pages) == 1
        assert "/Contents" in pdf.pages[0]
