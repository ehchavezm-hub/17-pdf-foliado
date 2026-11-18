"""Main application window — two-column layout."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QProgressBar, QLabel, QFileDialog,
    QSizePolicy, QApplication,
)

from pdf_foliado.ui.file_list import FileListWidget
from pdf_foliado.config.preferences import Preferences


_PALETTE_TOKENS = {
    "rojo":  {"accent": "#E4002B", "accent_h": "#b80022", "accent_bg": "#fff0f2"},
    "azul":  {"accent": "#005EB8", "accent_h": "#004a92", "accent_bg": "#f0f4ff"},
    "bosque": {"accent": "#1B7A4A", "accent_h": "#155f39", "accent_bg": "#f0fff6"},
}


def _build_stylesheet(skin: str) -> str:
    t = _PALETTE_TOKENS.get(skin, _PALETTE_TOKENS["rojo"])
    return f"""
QMainWindow, QWidget {{
    background-color: #FAFAFA;
    color: #231F20;
    font-family: "Roboto", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QPushButton {{
    background-color: {t["accent"]};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: {t["accent_h"]}; }}
QPushButton:disabled {{ background-color: #BDBDBD; }}
QPushButton#secondary {{
    background-color: transparent;
    color: {t["accent"]};
    border: 1px solid {t["accent"]};
}}
QPushButton#secondary:hover {{ background-color: {t["accent_bg"]}; }}
QProgressBar {{
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{ background-color: {t["accent"]}; border-radius: 4px; }}
QListWidget {{
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    background: white;
}}
QListWidget::item:selected {{ background-color: {t["accent_bg"]}; color: #231F20; }}
"""


class MainWindow(QMainWindow):
    def __init__(self, base_dir: Path | None = None,
                 prefs: Preferences | None = None, parent=None):
        super().__init__(parent)
        self._base_dir = base_dir or Path.cwd()
        self._prefs = prefs or Preferences()
        self._worker = None

        self.setWindowTitle("PDF Foliado")
        self.setMinimumSize(900, 600)
        self._apply_skin(self._prefs.skin)
        self._build_ui()

    # ------------------------------------------------------------------
    def _apply_skin(self, skin: str) -> None:
        self._prefs.skin = skin
        QApplication.instance().setStyleSheet(_build_stylesheet(skin))

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # --- header ---
        header = QWidget()
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(0, 0, 0, 0)
        title = QLabel("PDF Foliado")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        h_lay.addWidget(title)
        h_lay.addStretch()
        for skin_name, label in [("rojo", "●"), ("azul", "●"), ("bosque", "●")]:
            btn = QPushButton(label)
            btn.setFixedSize(24, 24)
            t = _PALETTE_TOKENS[skin_name]
            btn.setStyleSheet(
                f"QPushButton{{background:{t['accent']};border-radius:12px;"
                f"color:white;font-size:10px;padding:0;}}"
                f"QPushButton:hover{{background:{t['accent_h']};}}"
            )
            btn.clicked.connect(lambda checked=False, s=skin_name: self._apply_skin(s))
            h_lay.addWidget(btn)
        root.addWidget(header)

        # --- columns ---
        cols = QHBoxLayout()
        cols.setSpacing(12)

        # Left pane
        left = QVBoxLayout()
        left.setSpacing(6)
        btn_add = QPushButton("+ Agregar PDFs")
        btn_add.setObjectName("secondary")
        btn_add.clicked.connect(self._on_add_files)
        left.addWidget(btn_add)

        self._file_list = FileListWidget()
        self._file_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left.addWidget(self._file_list)

        btn_remove = QPushButton("Quitar seleccionados")
        btn_remove.setObjectName("secondary")
        btn_remove.clicked.connect(self._file_list.remove_selected)
        left.addWidget(btn_remove)

        left_w = QWidget()
        left_w.setLayout(left)
        cols.addWidget(left_w, 2)

        # Right pane — config panel stub (Task 8 fills this in)
        self._right_pane = QLabel("Panel de configuración\n(próximamente)")
        self._right_pane.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._right_pane.setStyleSheet(
            "border: 1px dashed #BDBDBD; border-radius: 4px; color: #757575;")
        cols.addWidget(self._right_pane, 3)

        root.addLayout(cols, 1)

        # --- bottom bar ---
        bottom = QHBoxLayout()
        self._status_label = QLabel("Listo")
        self._status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bottom.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedWidth(200)
        self._progress.setVisible(False)
        bottom.addWidget(self._progress)

        self._btn_cancel = QPushButton("Cancelar")
        self._btn_cancel.setObjectName("secondary")
        self._btn_cancel.setVisible(False)
        self._btn_cancel.clicked.connect(self._on_cancel)
        bottom.addWidget(self._btn_cancel)

        self._btn_foliar = QPushButton("Foliar")
        self._btn_foliar.clicked.connect(self._on_foliar)
        bottom.addWidget(self._btn_foliar)

        root.addLayout(bottom)

    # ------------------------------------------------------------------
    @Slot()
    def _on_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar PDFs", "", "PDF (*.pdf)")
        if paths:
            self._file_list.add_files([Path(p) for p in paths])

    @Slot()
    def _on_foliar(self):
        files = self._file_list.get_ordered_files()
        if not files:
            self._status_label.setText("No hay archivos para foliar.")
            return
        self._run_batch(files)

    @Slot()
    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()

    def _run_batch(self, files: list[Path]) -> None:
        from pdf_foliado.engine.batch import BatchWorker, BatchConfig
        from pdf_foliado.engine.stamper import StampParams
        p = self._prefs
        cfg = BatchConfig(
            files=files,
            mode=p.mode,
            order=p.order,
            start=p.start,
            prefix=p.prefix,
            suffix_file=p.suffix_file,
            stamp=StampParams(
                corner=p.corner,
                d1_mm=p.d1_mm,
                d2_mm=p.d2_mm,
                font_name=p.font_name,
                font_size_pt=p.font_size_pt,
                color_hex=p.color_hex,
            ),
        )
        self._worker = BatchWorker(cfg)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.file_error.connect(self._on_file_error)
        self._worker.finished.connect(self._on_finished)
        self._progress.setValue(0)
        self._progress.setRange(0, len(files))
        self._progress.setVisible(True)
        self._btn_cancel.setVisible(True)
        self._btn_foliar.setEnabled(False)
        self._status_label.setText("Foliando…")
        self._worker.start()

    @Slot(int, int)
    def _on_progress(self, current: int, total: int):
        self._progress.setValue(current)

    @Slot(str, str)
    def _on_file_done(self, src: str, dst: str):
        self._status_label.setText(f"OK: {Path(dst).name}")

    @Slot(str, str)
    def _on_file_error(self, src: str, err: str):
        self._status_label.setText(f"Error: {err}")

    @Slot()
    def _on_finished(self):
        self._progress.setVisible(False)
        self._btn_cancel.setVisible(False)
        self._btn_foliar.setEnabled(True)
        self._status_label.setText("Completado.")
        self._worker = None

    def get_preferences(self) -> Preferences:
        return self._prefs
