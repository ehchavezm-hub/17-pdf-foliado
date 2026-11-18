"""Batch processing orchestrator — 3-phase pipeline with Qt signals."""
from __future__ import annotations
import tempfile
import os
from dataclasses import dataclass
from pathlib import Path

import pikepdf
from PySide6.QtCore import QThread, Signal

from pdf_foliado.engine.stamper import StampParams, stamp_page
from pdf_foliado.engine.validator import validate_file
from pdf_foliado.utils.pdf_info import get_pdf_info
from pdf_foliado.utils.path_utils import safe_output_path


@dataclass
class BatchConfig:
    files: list[Path]
    mode: str          # "por_documento" | "correlativo"
    order: str         # "asc" | "desc"
    start: int
    prefix: str
    suffix_file: str
    stamp: StampParams


class BatchWorker(QThread):
    progress = Signal(int, int)        # (current_index, total)
    file_done = Signal(str, str)       # (input_path, output_path)
    file_error = Signal(str, str)      # (input_path, error_message)
    password_needed = Signal(str)      # (input_path) — emitted during pre-scan
    finished = Signal()

    def __init__(self, config: BatchConfig, output_dir: Path | None = None):
        super().__init__()
        self._cfg = config
        self._output_dir = output_dir
        self._passwords: dict[str, str] = {}  # path → password
        self._cancelled = False

    def provide_password(self, path: str, password: str) -> None:
        """Called from UI thread when user provides a password."""
        self._passwords[path] = password

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        cfg = self._cfg
        files = [Path(f) for f in cfg.files]
        total = len(files)

        # Phase 0: validate all files
        valid_files: list[Path] = []
        for path in files:
            if self._cancelled:
                break
            pwd = self._passwords.get(str(path))
            result = validate_file(path, password=pwd)
            if not result.ok:
                self.file_error.emit(str(path), result.error or "Error desconocido")
            else:
                valid_files.append(path)

        # Phase 1: pre-scan for correlativo (get page counts)
        page_counts: dict[str, int] = {}
        if cfg.mode == "correlativo":
            for path in valid_files:
                if self._cancelled:
                    break
                pwd = self._passwords.get(str(path))
                info = get_pdf_info(path, password=pwd)
                page_counts[str(path)] = info.page_count

        # Phase 2: stamp
        folio_counter = cfg.start
        for idx, path in enumerate(valid_files):
            if self._cancelled:
                break
            self.progress.emit(idx, len(valid_files))
            try:
                self._stamp_file(path, folio_counter)
                # Advance counter
                if cfg.mode == "correlativo":
                    folio_counter += page_counts.get(str(path), 0)
                # por_documento: counter resets per file (stays at cfg.start)
            except PermissionError as exc:
                self.file_error.emit(str(path),
                    f"Archivo bloqueado por otro proceso: {exc}")
            except Exception as exc:
                self.file_error.emit(str(path), str(exc))

        self.finished.emit()

    def _stamp_file(self, path: Path, start_folio: int) -> None:
        cfg = self._cfg
        pwd = self._passwords.get(str(path))
        open_kwargs = {"password": pwd} if pwd else {}

        with pikepdf.open(path, **open_kwargs) as pdf:
            n_pages = len(pdf.pages)
            if cfg.order == "asc":
                folios = range(start_folio, start_folio + n_pages)
            else:
                folios = range(start_folio + n_pages - 1, start_folio - 1, -1)

            for page, folio_num in zip(pdf.pages, folios):
                folio_text = cfg.prefix + str(folio_num).zfill(4)
                stamp_page(page, folio_text, cfg.stamp)

            # Atomic write
            if self._output_dir:
                out_path = self._output_dir / (path.stem + cfg.suffix_file + ".pdf")
                # Avoid overwrite
                counter = 1
                while out_path.exists():
                    out_path = self._output_dir / (
                        f"{path.stem}{cfg.suffix_file} ({counter}).pdf")
                    counter += 1
            else:
                out_path = safe_output_path(path, cfg.suffix_file)

            # Atomic write via temp file
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                    dir=out_path.parent, suffix=".tmp", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                pdf.save(str(tmp_path))
                os.replace(tmp_path, out_path)
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise

        self.file_done.emit(str(path), str(out_path))
