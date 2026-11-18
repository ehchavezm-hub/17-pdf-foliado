"""PDF page stamper — reportlab overlay + pikepdf merge."""
from __future__ import annotations
import io
from dataclasses import dataclass

import pikepdf
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.colors import HexColor

from pdf_foliado.utils.pdf_info import get_page_box, get_page_rotation

MM_TO_PT = 72 / 25.4

# Rotation compensation: visual corner -> PDF-space corner after /Rotate
_CORNER_ROTATE: dict[tuple[str, int], str] = {
    ("TL", 0): "TL",   ("TL", 90): "BL",  ("TL", 180): "BR", ("TL", 270): "TR",
    ("TR", 0): "TR",   ("TR", 90): "TL",  ("TR", 180): "BL", ("TR", 270): "BR",
    ("BL", 0): "BL",   ("BL", 90): "BR",  ("BL", 180): "TR", ("BL", 270): "TL",
    ("BR", 0): "BR",   ("BR", 90): "TR",  ("BR", 180): "TL", ("BR", 270): "BL",
}

# Standard PDF Type1 fonts available without embedding
_STANDARD_FONTS = {
    "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique",
    "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic",
    "Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique",
    "Symbol", "ZapfDingbats",
}


@dataclass
class StampParams:
    corner: str          # "TL" | "TR" | "BL" | "BR"
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
    """Stamp folio_text onto page in-place. Returns the same page object.

    owning_pdf must be provided when the page may have no /Contents (blank pages).
    """
    x0, y0, w, h = get_page_box(page)
    rot = get_page_rotation(page)

    pdf_corner = _CORNER_ROTATE.get((params.corner, rot), params.corner)
    d1 = params.d1_mm * MM_TO_PT
    d2 = params.d2_mm * MM_TO_PT
    fs = params.font_size_pt
    rl_font = _rl_font_name(params.font_name)

    # Build overlay PDF via reportlab (page sized to full media box)
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(x0 + w, y0 + h))
    c.setFont(rl_font, fs)
    c.setFillColor(HexColor(params.color_hex))

    # Compute anchor position in PDF-space
    text_width = c.stringWidth(folio_text, rl_font, fs)
    if pdf_corner == "BL":
        tx, ty = x0 + d2, y0 + d1
    elif pdf_corner == "BR":
        tx, ty = x0 + w - d2 - text_width, y0 + d1
    elif pdf_corner == "TL":
        tx, ty = x0 + d2, y0 + h - d1 - fs
    else:  # TR
        tx, ty = x0 + w - d2 - text_width, y0 + h - d1 - fs

    c.drawString(tx, ty, folio_text)
    c.save()
    buf.seek(0)

    # Extract overlay content and copy font resources while overlay_pdf is open
    with pikepdf.open(buf) as overlay_pdf:
        overlay_page = overlay_pdf.pages[0]
        overlay_content = _get_content_bytes(overlay_page)
        # Copy fonts under their original keys (preserves /F1, etc.)
        _copy_overlay_fonts(page, overlay_page)

    # Coalesce page content to a single stream, then append overlay
    page.contents_coalesce()
    if "/Contents" not in page:
        if owning_pdf is None:
            raise ValueError(
                "stamp_page: page has no /Contents — pass owning_pdf to stamp blank pages"
            )
        _write_fresh_content(page, overlay_content, owning_pdf)
    else:
        content_obj = page["/Contents"]
        existing = bytes(content_obj.read_raw_bytes())
        try:
            existing = bytes(content_obj.read_bytes())
        except Exception:
            pass
        new_data = existing + b"\nq\n" + overlay_content + b"\nQ\n"
        content_obj.write(new_data)

    return page


def _get_content_bytes(page: pikepdf.Page) -> bytes:
    """Return decompressed content stream bytes of page."""
    if "/Contents" not in page:
        return b""
    cs = page["/Contents"]
    if isinstance(cs, pikepdf.Array):
        return b"".join(bytes(s.read_raw_bytes()) for s in cs)
    try:
        return bytes(cs.read_bytes())
    except Exception:
        return bytes(cs.read_raw_bytes())


def _copy_overlay_fonts(target_page: pikepdf.Page, overlay_page: pikepdf.Page) -> None:
    """Copy font resources from overlay page to target page under original keys.

    This preserves the key (/F1, etc.) that the overlay content stream references,
    avoiding a mismatch between resource keys and content stream font references.
    """
    try:
        overlay_fonts = overlay_page["/Resources"]["/Font"]
    except KeyError:
        return

    if "/Resources" not in target_page:
        target_page["/Resources"] = pikepdf.Dictionary()
    res = target_page["/Resources"]
    if "/Font" not in res:
        res["/Font"] = pikepdf.Dictionary()
    font_dict = res["/Font"]

    for key in overlay_fonts.keys():
        if key not in font_dict:
            src = overlay_fonts[key]
            # Create a standalone font dict (no dependency on overlay_pdf after close)
            new_font = pikepdf.Dictionary(
                Type=pikepdf.Name("/Font"),
                Subtype=src.get("/Subtype", pikepdf.Name("/Type1")),
                BaseFont=src["/BaseFont"],
            )
            if "/Encoding" in src:
                new_font["/Encoding"] = src["/Encoding"]
            font_dict[key] = new_font


def _write_fresh_content(
    page: pikepdf.Page, content: bytes, owning_pdf: pikepdf.Pdf
) -> None:
    """Write content to a page that has no /Contents yet."""
    page["/Contents"] = pikepdf.Stream(owning_pdf, b"q\n" + content + b"\nQ\n")


def _rl_font_name(font_name: str) -> str:
    """Map UI font name to a reportlab/PDF standard font name."""
    return "Helvetica"  # all 13 UI fonts fall back to Helvetica for stamping
