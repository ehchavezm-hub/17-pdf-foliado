"""Live preview widget — renders first page via pypdfium2 + folio overlay."""
from __future__ import annotations
import io
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy

from pdf_foliado.engine.stamper import StampParams
from pdf_foliado.utils.pdf_info import get_page_box, get_page_rotation

MM_TO_PT = 72 / 25.4

_CORNER_ROTATE = {
    ("TL", 0): "TL",   ("TL", 90): "BL",  ("TL", 180): "BR", ("TL", 270): "TR",
    ("TR", 0): "TR",   ("TR", 90): "TL",  ("TR", 180): "BL", ("TR", 270): "BR",
    ("BL", 0): "BL",   ("BL", 90): "BR",  ("BL", 180): "TR", ("BL", 270): "TL",
    ("BR", 0): "BR",   ("BR", 90): "TR",  ("BR", 180): "TL", ("BR", 270): "BL",
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

    # ------------------------------------------------------------------
    def load_pdf(self, path: Path) -> None:
        self._pdf_path = path
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(str(path))
            page = doc[0]
            bmp = page.render(scale=self._scale)
            img = bmp.to_pil()
            doc.close()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            self._base_pixmap = QPixmap()
            self._base_pixmap.loadFromData(buf.read(), "PNG")
            self.setPixmap(
                self._base_pixmap.scaled(
                    self.width() or 400, self.height() or 600,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        except Exception as exc:
            self.setText(f"Error al cargar: {exc}")
            self._base_pixmap = None

    def update_folio(self, folio_text: str, params: StampParams) -> None:
        if self._base_pixmap is None:
            return
        # Overlay folio text on a copy of the base pixmap using QPainter
        pix = self._base_pixmap.copy()
        painter = QPainter(pix)
        try:
            # Determine color
            color = QColor(params.color_hex)
            painter.setPen(color)
            font = QFont("Helvetica")
            font.setPointSizeF(params.font_size_pt * self._scale)
            painter.setFont(font)

            w = pix.width()
            h = pix.height()
            d1 = params.d1_mm * MM_TO_PT * self._scale
            d2 = params.d2_mm * MM_TO_PT * self._scale
            fs = params.font_size_pt * self._scale
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(folio_text)

            # Try to get rotation if we have the PDF available
            rot = 0
            if self._pdf_path:
                try:
                    import pikepdf
                    with pikepdf.open(self._pdf_path) as pdf:
                        rot = get_page_rotation(pdf.pages[0])
                except Exception:
                    pass

            pdf_corner = _CORNER_ROTATE.get((params.corner, rot), params.corner)

            if pdf_corner == "BL":
                tx, ty = d2, h - d1
            elif pdf_corner == "BR":
                tx, ty = w - d2 - text_w, h - d1
            elif pdf_corner == "TL":
                tx, ty = d2, d1 + fs
            else:  # TR
                tx, ty = w - d2 - text_w, d1 + fs

            painter.drawText(int(tx), int(ty), folio_text)
        finally:
            painter.end()

        scaled = pix.scaled(
            self.width() or 400, self.height() or 600,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
