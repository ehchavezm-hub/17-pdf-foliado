"""PDF metadata extraction — no UI dependencies."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

import pikepdf


@dataclass
class PdfInfo:
    page_count: int = 0
    is_encrypted: bool = False
    has_signature: bool = False
    is_pdfa: bool = False


def get_pdf_info(path: Path, password: str | None = None) -> PdfInfo:
    """Read metadata without decrypting content; safe for large files."""
    info = PdfInfo()
    try:
        pdf = pikepdf.open(path, password=password or "", suppress_warnings=True)
    except pikepdf.PasswordError:
        info.is_encrypted = True
        return info
    except Exception:
        return info

    with pdf:
        info.page_count = len(pdf.pages)
        info.has_signature = _has_signature(pdf)
        info.is_pdfa = _is_pdfa(pdf)
    return info


def _has_signature(pdf: pikepdf.Pdf) -> bool:
    for page in pdf.pages:
        annots = page.get("/Annots")
        if annots is None:
            continue
        for annot in annots:
            try:
                obj = annot.get_object() if hasattr(annot, "get_object") else annot
                if obj.get("/FT") == pikepdf.Name("/Sig"):
                    return True
                if obj.get("/Subtype") == pikepdf.Name("/Widget"):
                    if obj.get("/FT") == pikepdf.Name("/Sig"):
                        return True
            except Exception:
                continue
    return False


def _is_pdfa(pdf: pikepdf.Pdf) -> bool:
    try:
        meta = pdf.open_metadata()
        ns = "http://www.aiim.org/pdfa/ns/id/"
        return bool(meta.get(f"{{{ns}}}conformance"))
    except Exception:
        return False


def get_page_box(page: pikepdf.Page) -> tuple[float, float, float, float]:
    """Return (x0, y0, width, height) using CropBox, fallback to MediaBox."""
    box = page.get("/CropBox") or page.get("/MediaBox")
    if box is None:
        return (0.0, 0.0, 595.0, 842.0)
    coords = [float(v) for v in box]
    x0, y0, x1, y1 = coords
    return (x0, y0, x1 - x0, y1 - y0)


def get_page_rotation(page: pikepdf.Page) -> int:
    """Return /Rotate value (0, 90, 180, 270)."""
    rot = page.get("/Rotate")
    if rot is None:
        return 0
    return int(rot) % 360
