"""PDF page image stamper — embeds an image as Form XObject overlay."""
from __future__ import annotations
import io
import math
import zlib
from dataclasses import dataclass
from pathlib import Path

import pikepdf
from PIL import Image as PILImage

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
class ImageStampParams:
    image_path: str = ""
    corner: str = "BR"
    d1_mm: float = 10.0
    d2_mm: float = 15.0
    angle_deg: float = 0.0
    width_mm: float = 30.0
    pages: str = "todas"    # "primera" | "todas"
    enabled: bool = False


def stamp_image_page(
    page: pikepdf.Page,
    params: ImageStampParams,
    page_index: int = 0,
) -> pikepdf.Page:
    """Embed an image on the page using add_overlay.

    page_index is 0-based: used to skip non-first pages when pages=="primera".
    """
    if not params.enabled or not params.image_path:
        return page
    if params.pages == "primera" and page_index > 0:
        return page
    if not Path(params.image_path).is_file():
        return page

    img = _prepare_image(params.image_path)
    img_w, img_h = img.size
    aspect = img_h / img_w if img_w > 0 else 1.0

    x0, y0, w, h = get_page_box(page)
    rot = get_page_rotation(page)
    pdf_corner = _CORNER_ROTATE.get((params.corner, rot), params.corner)

    d1 = params.d1_mm * MM_TO_PT
    d2 = params.d2_mm * MM_TO_PT
    width_pt = params.width_mm * MM_TO_PT
    height_pt = width_pt * aspect

    if pdf_corner == "BL":
        tx, ty = x0 + d2, y0 + d1
    elif pdf_corner == "BR":
        tx, ty = x0 + w - d2 - width_pt, y0 + d1
    elif pdf_corner == "BC":
        tx, ty = x0 + (w - width_pt) / 2, y0 + d1
    elif pdf_corner == "TL":
        tx, ty = x0 + d2, y0 + h - d1 - height_pt
    elif pdf_corner == "TC":
        tx, ty = x0 + (w - width_pt) / 2, y0 + h - d1 - height_pt
    else:  # TR
        tx, ty = x0 + w - d2 - width_pt, y0 + h - d1 - height_pt

    stamp = _make_image_stamp_pdf(img, tx, ty, width_pt, height_pt,
                                   params.angle_deg, x0, y0, w, h)
    page.add_overlay(stamp.pages[0])
    return page


# ---------------------------------------------------------------------------
# Image preparation
# ---------------------------------------------------------------------------

def _prepare_image(image_path: str) -> PILImage.Image:
    """Load and normalize image; preserve RGBA transparency, convert others to RGB."""
    img = PILImage.open(image_path)
    # Preserve RGBA (transparent PNG) as-is
    if img.mode == "RGBA":
        return img
    # Convert palette / LA / CMYK / etc. to RGB
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


# ---------------------------------------------------------------------------
# Stamp PDF builder
# ---------------------------------------------------------------------------

def _make_image_stamp_pdf(
    img: PILImage.Image,
    tx: float, ty: float,
    width_pt: float, height_pt: float,
    angle_deg: float,
    x0: float, y0: float, page_w: float, page_h: float,
) -> pikepdf.Pdf:
    """Build a minimal single-page PDF containing just the image stamp."""
    stamp = pikepdf.new()
    img_ref = _embed_image_xobject(stamp, img)

    # PDF image CTM: images are defined in a 1×1 unit square, so the matrix
    # scales to (width_pt × height_pt), rotates by angle_deg, then translates
    # to (tx, ty).
    θ = math.radians(angle_deg)
    cosθ = math.cos(θ)
    sinθ = math.sin(θ)
    a = cosθ * width_pt
    b = sinθ * width_pt
    c = -sinθ * height_pt
    d = cosθ * height_pt

    content = (
        f"q\n"
        f"{a:.5f} {b:.5f} {c:.5f} {d:.5f} {tx:.4f} {ty:.4f} cm\n"
        f"/Im0 Do\n"
        f"Q\n"
    ).encode("latin-1")

    contents = stamp.make_indirect(pikepdf.Stream(stamp, content))
    page_obj = stamp.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([x0, y0, x0 + page_w, y0 + page_h]),
        Resources=pikepdf.Dictionary(
            XObject=pikepdf.Dictionary(Im0=img_ref)
        ),
        Contents=contents,
    ))
    stamp.pages.append(pikepdf.Page(page_obj))
    return stamp


def _embed_image_xobject(stamp: pikepdf.Pdf, img: PILImage.Image) -> pikepdf.Object:
    """Create a pikepdf Image XObject, with SMask for RGBA transparency."""
    if img.mode == "RGBA":
        r, g, b, alpha = img.split()
        rgb = PILImage.merge("RGB", (r, g, b))

        # Alpha channel → DeviceGray XObject with FlateDecode (lossless)
        alpha_raw = bytes(alpha.tobytes())
        smask_stream = pikepdf.Stream(stamp, zlib.compress(alpha_raw, level=6))
        smask_stream.stream_dict.update({
            "/Type": pikepdf.Name("/XObject"),
            "/Subtype": pikepdf.Name("/Image"),
            "/Width": alpha.width,
            "/Height": alpha.height,
            "/ColorSpace": pikepdf.Name("/DeviceGray"),
            "/BitsPerComponent": 8,
            "/Filter": pikepdf.Name("/FlateDecode"),
        })
        smask_ref = stamp.make_indirect(smask_stream)

        # RGB channels → DCTDecode (JPEG)
        rgb_buf = io.BytesIO()
        rgb.save(rgb_buf, format="JPEG", quality=90)
        main_stream = pikepdf.Stream(stamp, rgb_buf.getvalue())
        main_stream.stream_dict.update({
            "/Type": pikepdf.Name("/XObject"),
            "/Subtype": pikepdf.Name("/Image"),
            "/Width": rgb.width,
            "/Height": rgb.height,
            "/ColorSpace": pikepdf.Name("/DeviceRGB"),
            "/BitsPerComponent": 8,
            "/Filter": pikepdf.Name("/DCTDecode"),
            "/SMask": smask_ref,
        })
        return stamp.make_indirect(main_stream)

    # RGB or L (grayscale) — use JPEG
    color_space = "/DeviceRGB" if img.mode == "RGB" else "/DeviceGray"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    main_stream = pikepdf.Stream(stamp, buf.getvalue())
    main_stream.stream_dict.update({
        "/Type": pikepdf.Name("/XObject"),
        "/Subtype": pikepdf.Name("/Image"),
        "/Width": img.width,
        "/Height": img.height,
        "/ColorSpace": pikepdf.Name(color_space),
        "/BitsPerComponent": 8,
        "/Filter": pikepdf.Name("/DCTDecode"),
    })
    return stamp.make_indirect(main_stream)
