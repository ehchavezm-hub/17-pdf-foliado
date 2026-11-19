"""PDF page stamper — Form XObject overlay via pikepdf.Page.add_overlay.

Root cause of the previous invisible/garbled folios:
  manual font-resource injection into complex pages failed silently — the
  modified resources dict was not always persisted when pikepdf saved.

Fix: build a minimal single-page stamp PDF and call page.add_overlay().
pikepdf handles XObject registration, font-resource isolation, and
content-stream appending internally, with no manual PDF manipulation.
"""
from __future__ import annotations
from dataclasses import dataclass

import pikepdf
from reportlab.pdfbase.pdfmetrics import stringWidth

from pdf_foliado.utils.pdf_info import get_page_box, get_page_rotation

MM_TO_PT = 72 / 25.4

_CORNER_ROTATE: dict[tuple[str, int], str] = {
    ("TL", 0): "TL",   ("TL", 90): "BL",  ("TL", 180): "BR", ("TL", 270): "TR",
    ("TR", 0): "TR",   ("TR", 90): "TL",  ("TR", 180): "BL", ("TR", 270): "BR",
    ("BL", 0): "BL",   ("BL", 90): "BR",  ("BL", 180): "TR", ("BL", 270): "TL",
    ("BR", 0): "BR",   ("BR", 90): "TR",  ("BR", 180): "TL", ("BR", 270): "BL",
    ("TC", 0): "TC",   ("TC", 90): "TC",  ("TC", 180): "BC", ("TC", 270): "BC",
    ("BC", 0): "BC",   ("BC", 90): "BC",  ("BC", 180): "TC", ("BC", 270): "TC",
}


@dataclass
class StampParams:
    corner: str          # "TL" | "TC" | "TR" | "BL" | "BC" | "BR"
    d1_mm: float
    d2_mm: float
    font_name: str
    font_size_pt: float
    color_hex: str       # e.g. "#231F20"


def stamp_page(
    page: pikepdf.Page,
    folio_text: str,
    params: StampParams,
    owning_pdf: "pikepdf.Pdf | None" = None,
) -> pikepdf.Page:
    """Stamp folio_text onto page using pikepdf.Page.add_overlay().

    Builds a temporary single-page PDF with the folio text and overlays it.
    The stamp PDF's MediaBox matches the original page so coordinates are
    preserved exactly (identity transform, no scaling).
    """
    x0, y0, w, h = get_page_box(page)
    rot = get_page_rotation(page)
    pdf_corner = _CORNER_ROTATE.get((params.corner, rot), params.corner)

    d1 = params.d1_mm * MM_TO_PT
    d2 = params.d2_mm * MM_TO_PT
    fs = params.font_size_pt
    text_width = stringWidth(folio_text, "Helvetica", fs)

    if pdf_corner == "BL":
        tx, ty = x0 + d2, y0 + d1
    elif pdf_corner == "BR":
        tx, ty = x0 + w - d2 - text_width, y0 + d1
    elif pdf_corner == "BC":
        tx, ty = x0 + (w - text_width) / 2, y0 + d1
    elif pdf_corner == "TL":
        tx, ty = x0 + d2, y0 + h - d1 - fs
    elif pdf_corner == "TC":
        tx, ty = x0 + (w - text_width) / 2, y0 + h - d1 - fs
    else:  # TR
        tx, ty = x0 + w - d2 - text_width, y0 + h - d1 - fs

    r, g, b = _parse_hex_color(params.color_hex)
    stamp = _make_stamp_pdf(tx, ty, fs, r, g, b, folio_text, x0, y0, w, h)
    page.add_overlay(stamp.pages[0])

    return page


def _make_stamp_pdf(
    tx: float, ty: float, fs: float,
    r: float, g: float, b: float,
    text: str,
    x0: float, y0: float, w: float, h: float,
) -> pikepdf.Pdf:
    """Build a minimal single-page PDF containing just the folio stamp.

    The MediaBox matches the original page (including non-zero x0/y0) so that
    add_overlay uses an identity transform and preserves the exact coordinates.
    """
    escaped = _pdf_escape(text)
    content = (
        f"q\n"
        f"{r:.5f} {g:.5f} {b:.5f} rg\n"
        f"BT\n"
        f"/Ff {fs:.2f} Tf\n"
        f"1 0 0 1 {tx:.4f} {ty:.4f} Tm\n"
        f"({escaped}) Tj\n"
        f"ET\n"
        f"Q\n"
    ).encode("latin-1", errors="replace")

    folio_font = pikepdf.Dictionary(
        Type=pikepdf.Name("/Font"),
        Subtype=pikepdf.Name("/Type1"),
        BaseFont=pikepdf.Name("/Helvetica"),
        Encoding=pikepdf.Name("/WinAnsiEncoding"),
    )

    stamp = pikepdf.new()
    contents = stamp.make_indirect(pikepdf.Stream(stamp, content))
    page_obj = stamp.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([x0, y0, x0 + w, y0 + h]),
        Resources=pikepdf.Dictionary(
            Font=pikepdf.Dictionary(Ff=folio_font)
        ),
        Contents=contents,
    ))
    stamp.pages.append(pikepdf.Page(page_obj))
    return stamp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pdf_escape(text: str) -> str:
    out = []
    for ch in text:
        if ch == "\\":
            out.append("\\\\")
        elif ch == "(":
            out.append("\\(")
        elif ch == ")":
            out.append("\\)")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\n":
            out.append("\\n")
        else:
            out.append(ch)
    return "".join(out)


def _parse_hex_color(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255


def folio_overflow_warning(
    page: pikepdf.Page,
    folio_text: str,
    params: StampParams,
) -> str | None:
    """Return a warning if folio text would overflow the page width, else None."""
    _x0, _y0, w, _h = get_page_box(page)
    text_width = stringWidth(folio_text, "Helvetica", params.font_size_pt)
    d2 = params.d2_mm * MM_TO_PT
    if d2 + text_width > w:
        return (
            f"El texto '{folio_text}' ({text_width:.0f} pt) "
            f"excede el ancho disponible ({w - d2:.0f} pt). "
            "El folio puede quedar fuera de la página."
        )
    return None
