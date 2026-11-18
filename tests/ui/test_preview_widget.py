import pytest
from pdf_foliado.engine.stamper import StampParams


def test_preview_loads(qtbot, pdf_1p):
    from pdf_foliado.ui.preview_widget import PreviewWidget
    pw = PreviewWidget()
    qtbot.addWidget(pw)
    pw.load_pdf(pdf_1p)
    pw.update_folio("0001", StampParams(corner="BR", d1_mm=10, d2_mm=15,
                    font_name="Helvetica", font_size_pt=12, color_hex="#231F20"))


def test_preview_no_crash_on_empty(qtbot):
    from pdf_foliado.ui.preview_widget import PreviewWidget
    pw = PreviewWidget()
    qtbot.addWidget(pw)
    # calling update_folio without loading a PDF should not crash
    pw.update_folio("0001", StampParams(corner="BR", d1_mm=10, d2_mm=15,
                    font_name="Helvetica", font_size_pt=12, color_hex="#231F20"))
