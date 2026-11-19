"""PDF page stamper — pure pikepdf content stream (no reportlab canvas)."""
from __future__ import annotations
import io
from dataclasses import dataclass

import pikepdf
from reportlab.pdfbase.pdfmetrics import stringWidth

from pdf_foliado.utils.pdf_info import get_page_box, get_page_rotation

MM_TO_PT = 72 / 25.4

# Rotation compensation: visual corner -> PDF-space corner after /Rotate
_CORNER_ROTATE: dict[tuple[str, int], str] = {
    ("TL", 0): "TL",   ("TL", 90): "BL",  ("TL", 180): "BR", ("TL", 270): "TR",
    ("TR", 0): "TR",   ("TR", 90): "TL",  ("TR", 180): "BL", ("TR", 270): "BR",
    ("BL", 0): "BL",   ("BL", 90): "BR",  ("BL", 180): "TR", ("BL", 270): "TL",
    ("BR", 0): "BR",   ("BR", 90): "TR",  ("BR", 180): "TL", ("BR", 270): "BL",
    ("TC", 0): "TC",   ("TC", 90): "TC",  ("TC", 180): "BC", ("TC", 270): "BC",
    ("BC", 0): "BC",   ("BC", 90): "BC",  ("BC", 180): "TC", ("BC", 270): "TC",
}

# Folio font key — deliberately unique to avoid collision with any document font.
_FOLIO_FONT_KEY = "/FolioF"


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
    """Stamp folio_text onto page in-place using a direct PDF content stream.

    Builds the content stream directly (no reportlab canvas) so the font
    selector and text draw are always in the same BT block, regardless of
    what fonts the target PDF already uses.
    """
    x0, y0, w, h = get_page_box(page)
    rot = get_page_rotation(page)

    pdf_corner = _CORNER_ROTATE.get((params.corner, rot), params.corner)
    d1 = params.d1_mm * MM_TO_PT
    d2 = params.d2_mm * MM_TO_PT
    fs = params.font_size_pt

    # Measure text width using Helvetica metrics (the font we will embed)
    text_width = stringWidth(folio_text, "Helvetica", fs)

    # Compute anchor position in PDF-space
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

    # Ensure /FolioF (Helvetica) is registered on this page
    _ensure_folio_font(page)

    # Build the folio content stream: color + BT…ET with font set inside
    r, g, b = _parse_hex_color(params.color_hex)
    folio_stream = _build_folio_stream(tx, ty, fs, r, g, b, folio_text)

    # Append to page content
    page.contents_coalesce()
    cs_ref = page.get("/Contents")
    if cs_ref is None:
        if owning_pdf is None:
            raise ValueError(
                "stamp_page: page has no /Contents — pass owning_pdf to stamp blank pages"
            )
        page["/Contents"] = pikepdf.Stream(owning_pdf, folio_stream)
    elif isinstance(cs_ref, pikepdf.Array):
        # contents_coalesce() failed; merge manually
        parts = []
        for s in cs_ref:
            try:
                parts.append(bytes(s.read_bytes()))
            except Exception:
                parts.append(bytes(s.read_raw_bytes()))
        existing = b"".join(parts)
        try:
            cs_ref[0].write(existing + b"\n" + folio_stream)
            # Coalesce again now that it's one stream
            page.contents_coalesce()
        except Exception:
            # Last resort: replace /Contents with a new merged stream
            if owning_pdf:
                page["/Contents"] = pikepdf.Stream(owning_pdf, existing + b"\n" + folio_stream)
    else:
        try:
            existing = bytes(cs_ref.read_bytes())
        except Exception:
            existing = bytes(cs_ref.read_raw_bytes())
        cs_ref.write(existing + b"\n" + folio_stream)

    return page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_folio_font(page: pikepdf.Page) -> None:
    """Add /FolioF → Helvetica/WinAnsiEncoding to the page's font resources."""
    if "/Resources" not in page:
        page["/Resources"] = pikepdf.Dictionary()
    res = page["/Resources"]
    if "/Font" not in res:
        res["/Font"] = pikepdf.Dictionary()
    font_dict = res["/Font"]
    if _FOLIO_FONT_KEY not in font_dict:
        font_dict[_FOLIO_FONT_KEY] = pikepdf.Dictionary(
            Type=pikepdf.Name("/Font"),
            Subtype=pikepdf.Name("/Type1"),
            BaseFont=pikepdf.Name("/Helvetica"),
            Encoding=pikepdf.Name("/WinAnsiEncoding"),
        )


def _build_folio_stream(
    tx: float, ty: float, fs: float,
    r: float, g: float, b: float,
    text: str,
) -> bytes:
    """Return a self-contained PDF content stream bytes for one folio stamp.

    The font selector (/FolioF Tf) is inside the BT…ET block so it is always
    active when the text is drawn, regardless of surrounding page state.
    """
    escaped = _pdf_escape(text)
    stream = (
        f"q\n"
        f"{r:.5f} {g:.5f} {b:.5f} rg\n"
        f"BT\n"
        f"{_FOLIO_FONT_KEY} {fs:.2f} Tf\n"
        f"1 0 0 1 {tx:.4f} {ty:.4f} Tm\n"
        f"({escaped}) Tj\n"
        f"ET\n"
        f"Q\n"
    )
    return stream.encode("cp1252", errors="replace")


def _pdf_escape(text: str) -> str:
    """Escape special characters for use inside a PDF string literal ( … )."""
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
    """'#RRGGBB' → (r, g, b) each in [0.0, 1.0]."""
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
