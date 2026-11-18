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
from pdf_foliado.ui._theme import PALETTE_TOKENS, build_stylesheet
from pdf_foliado.config.preferences import Preferences


class MainWindow(QMainWindow):
    def __init__(self, base_dir: Path | None = None,
                 prefs: Preferences | None = None, parent=None):
        super().__init__(parent)
        self._base_dir = base_dir or Path.cwd()
        self._prefs = prefs or Preferences()
        self._worker = None

        self.setWindowTitle("PDF Foliado")
        self.setMinimumSize(900, 600)
        self._build_ui()
        # Apply skin after build so config_panel exists
        self._apply_skin(self._prefs.skin)

    # ------------------------------------------------------------------
    def _apply_skin(self, skin: str) -> None:
        """Apply stylesheet and keep config panel in sync."""
        self._prefs.skin = skin
        QApplication.instance().setStyleSheet(build_stylesheet(skin))
        # Sync config panel skin state so get_preferences() returns the right value
        if hasattr(self, "_config_panel"):
            self._config_panel.sync_skin(skin)

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
        for skin_name in ("rojo", "azul", "bosque"):
            t = PALETTE_TOKENS[skin_name]
            btn = QPushButton("●")
            btn.setFixedSize(24, 24)
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

        # Right pane — real config panel
        from pdf_foliado.ui.config_panel import ConfigPanel
        self._config_panel = ConfigPanel()
        self._config_panel.set_preferences(self._prefs)
        self._config_panel.config_changed.connect(self._on_config_changed)
        self._config_panel.skin_changed.connect(self._apply_skin)
        cols.addWidget(self._config_panel, 3)

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
    def _on_config_changed(self):
        self._prefs = self._config_panel.get_preferences()

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
        from pdf_foliado.engine.batch import BatchWorker
        cfg = self._config_panel.get_config(files)
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
        # Sync range to actual valid-file count in case some were rejected
        self._progress.setRange(0, total)
        self._progress.setValue(current)

    @Slot(str, str)
    def _on_file_done(self, src: str, dst: str):
        self._status_label.setText(f"OK: {Path(dst).name}")

    @Slot(str, str)
    def _on_file_error(self, src: str, err: str):
        self._status_label.setText(f"Error: {err}")

    @Slot()
    def _on_finished(self):
        # Push progress to 100%
        self._progress.setValue(self._progress.maximum())
        self._progress.setVisible(False)
        self._btn_cancel.setVisible(False)
        self._btn_foliar.setEnabled(True)
        self._status_label.setText("Completado.")
        self._worker = None

    def get_preferences(self) -> Preferences:
        return self._config_panel.get_preferences()
