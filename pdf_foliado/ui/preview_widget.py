"""Live preview widget — renders first page via pypdfium2 + folio/image overlay."""
from __future__ import annotations
import io
import math
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QPixmap, QTransform
from PySide6.QtWidgets import QLabel, QSizePolicy

from pdf_foliado.engine.stamper import StampParams
from pdf_foliado.utils.pdf_info import get_page_box, get_page_rotation

MM_TO_PT = 72 / 25.4

_CORNER_ROTATE = {
    ("TL", 0): "TL",   ("TL", 90): "BL",  ("TL", 180): "BR", ("TL", 270): "TR",
    ("TR", 0): "TR",   ("TR", 90): "TL",  ("TR", 180): "BL", ("TR", 270): "BR",
    ("BL", 0): "BL",   ("BL", 90): "BR",  ("BL", 180): "TR", ("BL", 270): "TL",
    ("BR", 0): "BR",   ("BR", 90): "TR",  ("BR", 180): "TL", ("BR", 270): "BL",
    ("TC", 0): "TC",   ("TC", 90): "TC",  ("TC", 180): "BC", ("TC", 270): "BC",
    ("BC", 0): "BC",   ("BC", 90): "BC",  ("BC", 180): "TC", ("BC", 270): "TC",
}


class PreviewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Vista previa\n(selecciona un PDF)")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("border: 1px solid #E0E0E0; border-radius: 4px; color: #757575;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._base_pixmap: QPixmap | None = None
        self._pdf_path: Path | None = None
        self._scale = 1.5
        # Stored params for unified repaint
        self._folio_text: str = ""
        self._stamp_params: StampParams | None = None
        self._image_params = None   # ImageStampParams | None
        self._page_rot: int = 0

    # ------------------------------------------------------------------
    def load_pdf(self, path: Path) -> None:
        self._pdf_path = path
        self._page_rot = 0
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(str(path))
            try:
                bmp = doc[0].render(scale=self._scale)
                img = bmp.to_pil()
            finally:
                doc.close()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            self._base_pixmap = QPixmap()
            self._base_pixmap.loadFromData(buf.read(), "PNG")
            # Cache page rotation
            try:
                import pikepdf
                with pikepdf.open(str(path)) as pdf:
                    self._page_rot = get_page_rotation(pdf.pages[0])
            except Exception:
                pass
            self._repaint()
        except Exception as exc:
            self.setText(f"Error al cargar: {exc}")
            self._base_pixmap = None

    def update_folio(self, folio_text: str, params: StampParams) -> None:
        """Update folio overlay and repaint."""
        self._folio_text = folio_text
        self._stamp_params = params
        self._repaint()

    def update_image_stamp(self, params) -> None:
        """Update image stamp overlay and repaint."""
        self._image_params = params
        self._repaint()

    # ------------------------------------------------------------------
    def _repaint(self) -> None:
        if self._base_pixmap is None:
            return
        pix = self._base_pixmap.copy()
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        try:
            if self._image_params is not None:
                self._draw_image(painter, pix)
            if self._stamp_params is not None and self._folio_text:
                self._draw_folio(painter, pix)
        finally:
            painter.end()

        self.setPixmap(
            pix.scaled(
                self.width() or 400, self.height() or 600,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # ------------------------------------------------------------------
    def _draw_folio(self, painter: QPainter, pix: QPixmap) -> None:
        params = self._stamp_params
        color = QColor(params.color_hex)
        painter.setPen(color)
        font = QFont("Helvetica")
        font.setPointSizeF(params.font_size_pt * self._scale)
        font.setBold(params.font_bold)
        font.setItalic(params.font_italic)
        painter.setFont(font)

        w = pix.width()
        h = pix.height()
        d1 = params.d1_mm * MM_TO_PT * self._scale
        d2 = params.d2_mm * MM_TO_PT * self._scale
        fs = params.font_size_pt * self._scale
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(self._folio_text)

        pdf_corner = _CORNER_ROTATE.get((params.corner, self._page_rot), params.corner)

        if pdf_corner == "BL":
            tx, ty = d2, h - d1
        elif pdf_corner == "BR":
            tx, ty = w - d2 - text_w, h - d1
        elif pdf_corner == "BC":
            tx, ty = (w - text_w) / 2, h - d1
        elif pdf_corner == "TL":
            tx, ty = d2, d1 + fs
        elif pdf_corner == "TC":
            tx, ty = (w - text_w) / 2, d1 + fs
        else:  # TR
            tx, ty = w - d2 - text_w, d1 + fs

        painter.drawText(int(tx), int(ty), self._folio_text)

    def _draw_image(self, painter: QPainter, pix: QPixmap) -> None:
        params = self._image_params
        if not params.enabled or not params.image_path:
            return
        if not Path(params.image_path).is_file():
            return

        img_pix = QPixmap(params.image_path)
        if img_pix.isNull():
            return

        w = pix.width()
        h = pix.height()
        d1 = params.d1_mm * MM_TO_PT * self._scale
        d2 = params.d2_mm * MM_TO_PT * self._scale
        width_px = params.width_mm * MM_TO_PT * self._scale
        # Maintain aspect ratio
        if img_pix.width() > 0:
            height_px = width_px * img_pix.height() / img_pix.width()
        else:
            height_px = width_px

        img_scaled = img_pix.scaled(
            int(width_px), int(height_px),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        # Actual dimensions after scaling
        iw = img_scaled.width()
        ih = img_scaled.height()

        pdf_corner = _CORNER_ROTATE.get((params.corner, self._page_rot), params.corner)

        # Screen coords (Y=0 top): anchor is top-left of image rect
        if pdf_corner == "BL":
            tx, ty = d2, h - d1 - ih
        elif pdf_corner == "BR":
            tx, ty = w - d2 - iw, h - d1 - ih
        elif pdf_corner == "BC":
            tx, ty = (w - iw) / 2, h - d1 - ih
        elif pdf_corner == "TL":
            tx, ty = d2, d1
        elif pdf_corner == "TC":
            tx, ty = (w - iw) / 2, d1
        else:  # TR
            tx, ty = w - d2 - iw, d1

        angle = params.angle_deg
        if angle != 0.0:
            # Rotate around the image center
            cx = tx + iw / 2
            cy = ty + ih / 2
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(-angle)   # QPainter rotates CW; negate for CCW (PDF convention)
            painter.drawPixmap(int(-iw / 2), int(-ih / 2), img_scaled)
            painter.restore()
        else:
            painter.drawPixmap(int(tx), int(ty), img_scaled)
