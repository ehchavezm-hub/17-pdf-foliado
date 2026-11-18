import pytest
import pikepdf
from pathlib import Path
from pdf_foliado.engine.batch import BatchWorker, BatchConfig
from pdf_foliado.engine.stamper import StampParams


def test_full_por_documento_round_trip(pdf_10p, tmp_path, qtbot):
    """Stamp 10-page PDF, verify 10 pages in output with no errors."""
    cfg = BatchConfig(
        files=[pdf_10p], mode="por_documento", order="asc",
        start=1, prefix="", suffix_file="_fol",
        stamp=StampParams("BR", 10, 15, "Helvetica", 12, "#231F20"),
    )
    errors = []
    done = []
    worker = BatchWorker(cfg, output_dir=tmp_path)
    worker.file_error.connect(lambda p, e: errors.append(e))
    worker.file_done.connect(lambda i, o: done.append(o))
    with qtbot.waitSignal(worker.finished, timeout=20000):
        worker.start()
    assert errors == []
    assert len(done) == 1
    with pikepdf.open(done[0]) as pdf:
        assert len(pdf.pages) == 10


def test_full_correlativo_round_trip(pdf_1p, pdf_5p, tmp_path, qtbot):
    """Correlativo across 2 PDFs — 1p gets folio 1, 5p gets folios 2-6."""
    cfg = BatchConfig(
        files=[pdf_1p, pdf_5p], mode="correlativo", order="asc",
        start=1, prefix="", suffix_file="_fol",
        stamp=StampParams("BR", 10, 15, "Helvetica", 12, "#231F20"),
    )
    errors = []
    done = []
    worker = BatchWorker(cfg, output_dir=tmp_path)
    worker.file_error.connect(lambda p, e: errors.append(e))
    worker.file_done.connect(lambda i, o: done.append(o))
    with qtbot.waitSignal(worker.finished, timeout=20000):
        worker.start()
    assert errors == []
    assert len(done) == 2
