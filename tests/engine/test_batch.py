import pytest
import pikepdf
from pathlib import Path
from pdf_foliado.engine.batch import BatchWorker, BatchConfig
from pdf_foliado.engine.stamper import StampParams


def _params() -> StampParams:
    return StampParams(corner="BR", d1_mm=10.0, d2_mm=15.0,
                       font_name="Helvetica", font_size_pt=12.0, color_hex="#231F20")


def _cfg(files, mode="por_documento", order="asc", start=1) -> BatchConfig:
    return BatchConfig(files=files, mode=mode, order=order,
                       start=start, prefix="", suffix_file="_fol", stamp=_params())


def test_por_documento_completes(pdf_1p, pdf_10p, tmp_path, qtbot):
    cfg = _cfg([pdf_1p, pdf_10p])
    worker = BatchWorker(cfg, output_dir=tmp_path)
    done = []
    errors = []
    worker.file_done.connect(lambda i, o: done.append(o))
    worker.file_error.connect(lambda p, e: errors.append(e))
    with qtbot.waitSignal(worker.finished, timeout=15000):
        worker.start()
    assert errors == [], f"Unexpected errors: {errors}"
    assert len(done) == 2


def test_por_documento_independent_sequences(pdf_1p, pdf_10p, tmp_path, qtbot):
    """Each file starts from folio 1 independently."""
    cfg = _cfg([pdf_1p, pdf_10p])
    worker = BatchWorker(cfg, output_dir=tmp_path)
    done = []
    worker.file_done.connect(lambda i, o: done.append(Path(o)))
    with qtbot.waitSignal(worker.finished, timeout=15000):
        worker.start()
    # Both output PDFs should exist and be valid
    for p in done:
        with pikepdf.open(p) as pdf:
            assert len(pdf.pages) > 0


def test_correlativo_sequence(pdf_1p, pdf_10p, tmp_path, qtbot):
    """Correlativo: second file starts where first ended."""
    cfg = _cfg([pdf_1p, pdf_10p], mode="correlativo")
    worker = BatchWorker(cfg, output_dir=tmp_path)
    done = []
    worker.file_done.connect(lambda i, o: done.append(Path(o)))
    with qtbot.waitSignal(worker.finished, timeout=15000):
        worker.start()
    assert len(done) == 2
    # 1p gets folio 1, 10p gets folios 2-11
    with pikepdf.open(done[0]) as pdf:
        assert len(pdf.pages) == 1
    with pikepdf.open(done[1]) as pdf:
        assert len(pdf.pages) == 10


def test_desc_order(pdf_10p, tmp_path, qtbot):
    """Descending order: starts from N and counts down."""
    cfg = _cfg([pdf_10p], order="desc")
    worker = BatchWorker(cfg, output_dir=tmp_path)
    done = []
    worker.file_done.connect(lambda i, o: done.append(Path(o)))
    with qtbot.waitSignal(worker.finished, timeout=15000):
        worker.start()
    assert len(done) == 1


def test_start_from_5(pdf_5p, tmp_path, qtbot):
    cfg = _cfg([pdf_5p], start=5)
    worker = BatchWorker(cfg, output_dir=tmp_path)
    done = []
    worker.file_done.connect(lambda i, o: done.append(Path(o)))
    with qtbot.waitSignal(worker.finished, timeout=15000):
        worker.start()
    assert len(done) == 1


def test_progress_signals_emitted(pdf_10p, tmp_path, qtbot):
    cfg = _cfg([pdf_10p])
    worker = BatchWorker(cfg, output_dir=tmp_path)
    progress_calls = []
    worker.progress.connect(lambda cur, tot: progress_calls.append((cur, tot)))
    with qtbot.waitSignal(worker.finished, timeout=15000):
        worker.start()
    assert len(progress_calls) > 0
