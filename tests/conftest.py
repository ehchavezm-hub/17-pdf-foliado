"""Programmatic PDF fixtures — no binary files committed to repo."""
import os
import pytest
from pathlib import Path

# Ensure Qt uses offscreen rendering in CI and in environments without a display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3
import pikepdf

TMP = Path(__file__).parent / "_generated"


def _make_pdf(name: str, pages: int = 1, pagesize=A4,
              rotate: int = 0, cropbox=None) -> Path:
    TMP.mkdir(exist_ok=True)
    p = TMP / name
    c = canvas.Canvas(str(p), pagesize=pagesize)
    for i in range(pages):
        c.drawString(50, 700, f"Page {i + 1}")
        c.showPage()
    c.save()
    if rotate or cropbox:
        with pikepdf.open(p, allow_overwriting_input=True) as pdf:
            for page in pdf.pages:
                if rotate:
                    page["/Rotate"] = rotate
                if cropbox:
                    page["/CropBox"] = cropbox
            pdf.save(p)
    return p


@pytest.fixture(scope="session")
def pdf_1p():
    return _make_pdf("1p.pdf", pages=1)


@pytest.fixture(scope="session")
def pdf_10p():
    return _make_pdf("10p.pdf", pages=10)


@pytest.fixture(scope="session")
def pdf_5p():
    return _make_pdf("5p.pdf", pages=5)


@pytest.fixture(scope="session")
def pdf_0p():
    TMP.mkdir(exist_ok=True)
    p = TMP / "0p.pdf"
    # A PDF with 0 pages: create a minimal valid PDF with no page tree children
    c = canvas.Canvas(str(p))
    # Don't call showPage — but Canvas always adds one page on save.
    # Use pikepdf to remove it after.
    c.save()
    with pikepdf.open(p, allow_overwriting_input=True) as pdf:
        while len(pdf.pages) > 0:
            del pdf.pages[0]
        pdf.save(p)
    return p


@pytest.fixture(scope="session")
def pdf_rotated_90():
    return _make_pdf("rot90.pdf", pages=1, rotate=90)


@pytest.fixture(scope="session")
def pdf_rotated_180():
    return _make_pdf("rot180.pdf", pages=1, rotate=180)


@pytest.fixture(scope="session")
def pdf_rotated_270():
    return _make_pdf("rot270.pdf", pages=1, rotate=270)


@pytest.fixture(scope="session")
def pdf_cropbox():
    return _make_pdf("cropbox.pdf", pages=1, cropbox=[0, 0, 400, 500])


@pytest.fixture(scope="session")
def pdf_mixed_size():
    TMP.mkdir(exist_ok=True)
    p = TMP / "mixed.pdf"
    c = canvas.Canvas(str(p), pagesize=A4)
    c.drawString(50, 700, "A4 page")
    c.showPage()
    c.setPageSize(A3)
    c.drawString(50, 700, "A3 page")
    c.showPage()
    c.save()
    return p


@pytest.fixture(scope="session")
def pdf_encrypted():
    src = _make_pdf("enc_src.pdf", pages=3)
    p = TMP / "enc.pdf"
    with pikepdf.open(src) as pdf:
        pdf.save(p, encryption=pikepdf.Encryption(owner="owner", user="user123"))
    return p


@pytest.fixture(scope="session")
def pdf_signed():
    """PDF with a /Sig annotation (simulated — no real crypto)."""
    src = _make_pdf("signed_src.pdf", pages=2)
    p = TMP / "signed.pdf"
    with pikepdf.open(src, allow_overwriting_input=False) as pdf:
        page = pdf.pages[0]
        # Add a minimal /Sig dictionary to the page's /Annots
        sig_dict = pikepdf.Dictionary(
            Type=pikepdf.Name("/Annot"),
            Subtype=pikepdf.Name("/Widget"),
            FT=pikepdf.Name("/Sig"),
            Rect=[0, 0, 0, 0],
        )
        page["/Annots"] = pikepdf.Array([pdf.make_indirect(sig_dict)])
        pdf.save(p)
    return p
