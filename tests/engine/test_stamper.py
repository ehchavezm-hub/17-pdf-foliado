import re
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
    assert out.exists()


def _make_pikepdf_only_pdf(path: Path, with_contents: bool = True) -> None:
    """Create a minimal PDF using only pikepdf (no reportlab) so /F1 is not pre-existing."""
    pdf = pikepdf.Pdf.new()
    if with_contents:
        contents = pdf.make_indirect(pikepdf.Stream(pdf, b""))
        page_dict = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/Page"),
            MediaBox=[0, 0, 595, 842],
            Contents=contents,
        ))
    else:
        page_dict = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/Page"),
            MediaBox=[0, 0, 595, 842],
        ))
    pdf.pages.append(pikepdf.Page(page_dict))
    pdf.save(path)
    pdf.close()


def test_font_resource_key_matches_content_stream(tmp_path):
    """Font resource keys must match what the overlay content stream references.

    For a pikepdf-only PDF (no reportlab pre-existing /F1), after stamping the
    font resource key added to the page must be /F1 (the key the overlay uses),
    not a different key like /Fol1.
    """
    p = tmp_path / "pikepdf_only.pdf"
    _make_pikepdf_only_pdf(p, with_contents=True)

    out = tmp_path / "pikepdf_only_stamped.pdf"
    with pikepdf.open(p) as pdf:
        stamp_page(pdf.pages[0], "0001", _default_params(), owning_pdf=pdf)
        pdf.save(out)

    with pikepdf.open(out) as pdf:
        page = pdf.pages[0]
        content = bytes(page["/Contents"].read_bytes()).decode("latin-1")
        font_refs = set(re.findall(r'(/\w+)\s+[\d.]+\s+Tf', content))
        font_keys = set(str(k) for k in page["/Resources"]["/Font"].keys())
        for ref in font_refs:
            assert ref in font_keys, (
                f"Font {ref} referenced in content stream but not in /Resources/Font. "
                f"Available keys: {font_keys}"
            )


def test_blank_page_no_contents_stamps_successfully(tmp_path):
    """Stamping a page with no /Contents must not crash on pdf.save()."""
    p = tmp_path / "blank.pdf"
    _make_pikepdf_only_pdf(p, with_contents=False)

    out = tmp_path / "blank_stamped.pdf"
    with pikepdf.open(p) as pdf:
        assert "/Contents" not in pdf.pages[0], "fixture must have no /Contents"
        stamp_page(pdf.pages[0], "0001", _default_params(), owning_pdf=pdf)
        pdf.save(out)

    assert out.exists()
    with pikepdf.open(out) as pdf:
        assert len(pdf.pages) == 1
        assert "/Contents" in pdf.pages[0]
