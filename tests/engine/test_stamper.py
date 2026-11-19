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


def test_folio_uses_xobject_overlay(tmp_path):
    """After stamping, the folio must be embedded as a Form XObject overlay.

    The add_overlay approach stores the folio font in the XObject's own
    /Resources, completely isolated from the page's existing fonts.
    This is the invariant that prevents invisible/garbled folios on complex PDFs.
    """
    p = tmp_path / "pikepdf_only.pdf"
    _make_pikepdf_only_pdf(p, with_contents=True)

    out = tmp_path / "pikepdf_only_stamped.pdf"
    with pikepdf.open(p) as pdf:
        stamp_page(pdf.pages[0], "0001", _default_params(), owning_pdf=pdf)
        pdf.save(out)

    with pikepdf.open(out) as pdf:
        page = pdf.pages[0]
        # Page resources must have an XObject (the folio overlay)
        assert "/XObject" in page.resources, \
            "Page must have /XObject resources after stamping (add_overlay)"

        # The XObject must be a Form XObject with Helvetica font in its resources
        found_helvetica = _xobject_has_helvetica(page)
        assert found_helvetica, \
            "Folio XObject must contain a Helvetica /Type1 font resource"


def test_stamp_pdf_with_preexisting_f1_font(tmp_path):
    """Stamping a PDF with existing /F1 must preserve it and add an isolated XObject.

    The add_overlay approach never modifies the page's existing font resources.
    The folio font lives only inside the XObject — zero collision risk.
    """
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    p = tmp_path / "rl_has_f1.pdf"
    c = rl_canvas.Canvas(str(p), pagesize=A4)
    c.setFont("Helvetica", 10)
    c.drawString(50, 700, "Document with /F1 already set")
    c.save()

    out = tmp_path / "rl_has_f1_stamped.pdf"
    with pikepdf.open(p) as pdf:
        stamp_page(pdf.pages[0], "fox_0001", _default_params(), owning_pdf=pdf)
        pdf.save(out)

    with pikepdf.open(out) as pdf:
        page = pdf.pages[0]
        # Original page fonts must be preserved
        font_keys = set(str(k) for k in page.resources.get("/Font", {}).keys())
        assert len(font_keys) > 0, \
            "Original document fonts must still be in page resources"

        # An XObject must have been added (the folio overlay)
        assert "/XObject" in page.resources, \
            "Page must have /XObject resources after stamping (add_overlay)"

        # The XObject must have its own Helvetica font (not in the page's Font dict)
        found_helvetica = _xobject_has_helvetica(page)
        assert found_helvetica, \
            "Folio XObject must contain an isolated Helvetica font resource"


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


def _xobject_has_helvetica(page: pikepdf.Page) -> bool:
    """Return True if any Form XObject in the page's resources has a Helvetica font."""
    xobjects = page.resources.get("/XObject", {})
    for xobj in xobjects.values():
        if not isinstance(xobj, pikepdf.Stream):
            continue
        xobj_res = xobj.stream_dict.get("/Resources")
        if xobj_res is None:
            continue
        fonts = xobj_res.get("/Font", {})
        if not hasattr(fonts, "values"):
            continue
        for font_val in fonts.values():
            if not hasattr(font_val, "get"):
                continue
            base_font = font_val.get("/BaseFont")
            if base_font is not None and str(base_font) == "/Helvetica":
                return True
    return False
