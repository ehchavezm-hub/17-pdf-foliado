import pytest
import pikepdf
from pdf_foliado.utils.pdf_info import get_pdf_info, get_page_box, get_page_rotation


def test_page_count_10(pdf_10p):
    info = get_pdf_info(pdf_10p)
    assert info.page_count == 10


def test_page_count_1(pdf_1p):
    info = get_pdf_info(pdf_1p)
    assert info.page_count == 1


def test_zero_pages(pdf_0p):
    info = get_pdf_info(pdf_0p)
    assert info.page_count == 0


def test_encrypted_detected(pdf_encrypted):
    info = get_pdf_info(pdf_encrypted)
    assert info.is_encrypted is True


def test_not_encrypted(pdf_1p):
    info = get_pdf_info(pdf_1p)
    assert info.is_encrypted is False


def test_signature_detected(pdf_signed):
    info = get_pdf_info(pdf_signed)
    assert info.has_signature is True


def test_no_signature(pdf_1p):
    info = get_pdf_info(pdf_1p)
    assert info.has_signature is False


def test_cropbox_used(pdf_cropbox):
    with pikepdf.open(pdf_cropbox) as pdf:
        x0, y0, w, h = get_page_box(pdf.pages[0])
    assert w == pytest.approx(400, abs=1)
    assert h == pytest.approx(500, abs=1)


def test_mediabox_fallback(pdf_1p):
    # Normal A4 has no CropBox, should fall back to MediaBox (595 x 842)
    with pikepdf.open(pdf_1p) as pdf:
        x0, y0, w, h = get_page_box(pdf.pages[0])
    assert w == pytest.approx(595, abs=2)
    assert h == pytest.approx(842, abs=2)


def test_rotation_90(pdf_rotated_90):
    with pikepdf.open(pdf_rotated_90) as pdf:
        assert get_page_rotation(pdf.pages[0]) == 90


def test_rotation_zero(pdf_1p):
    with pikepdf.open(pdf_1p) as pdf:
        assert get_page_rotation(pdf.pages[0]) == 0
