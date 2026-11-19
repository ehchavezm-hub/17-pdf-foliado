"""Main application window — two-column layout."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QProgressBar, QLabel, QFileDialog,
    QSizePolicy, QApplication, QInputDialog, QLineEdit, QTabWidget,
)

from pdf_foliado.ui.file_list import FileListWidget
from pdf_foliado.ui._theme import PALETTE_TOKENS, build_stylesheet
from pdf_foliado.ui.preview_widget import PreviewWidget
from pdf_foliado.config.preferences import Preferences


class MainWindow(QMainWindow):
    def __init__(self, base_dir: Path | None = None,
                 prefs: Preferences | None = None, parent=None):
        super().__init__(parent)
        self._base_dir = base_dir or Path.cwd()
        self._prefs = prefs or Preferences()
        self._worker = None
        self._last_output_dir: Path | None = None

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
        self._file_list.currentItemChanged.connect(self._on_file_selected)
        self._file_list.summary_changed.connect(self._on_summary_changed)

        # List + ↑↓ buttons side by side
        list_row = QHBoxLayout()
        list_row.setSpacing(4)
        list_row.addWidget(self._file_list)
        move_col = QVBoxLayout()
        move_col.setSpacing(4)
        self._btn_up = QPushButton("↑")
        self._btn_up.setObjectName("secondary")
        self._btn_up.setFixedSize(36, 36)
        self._btn_up.setToolTip("Subir archivo")
        self._btn_up.clicked.connect(self._file_list.move_up)
        self._btn_down = QPushButton("↓")
        self._btn_down.setObjectName("secondary")
        self._btn_down.setFixedSize(36, 36)
        self._btn_down.setToolTip("Bajar archivo")
        self._btn_down.clicked.connect(self._file_list.move_down)
        move_col.addWidget(self._btn_up)
        move_col.addWidget(self._btn_down)
        move_col.addStretch()
        list_row.addLayout(move_col)
        left.addLayout(list_row, 1)

        self._summary_label = QLabel("Sin archivos")
        self._summary_label.setStyleSheet("color: #757575; font-size: 11px;")
        left.addWidget(self._summary_label)

        btn_remove = QPushButton("Quitar seleccionados")
        btn_remove.setObjectName("secondary")
        btn_remove.clicked.connect(self._file_list.remove_selected)
        left.addWidget(btn_remove)

        self._preview = PreviewWidget()
        self._preview.setMinimumHeight(180)
        self._preview.setMaximumHeight(240)
        left.addWidget(self._preview)

        left_w = QWidget()
        left_w.setLayout(left)
        cols.addWidget(left_w, 2)

        # Right pane — tabs: Folio + Sello
        from pdf_foliado.ui.config_panel import ConfigPanel
        from pdf_foliado.ui.sello_panel import SelloPanel
        self._config_panel = ConfigPanel()
        self._config_panel.set_preferences(self._prefs)
        self._config_panel.config_changed.connect(self._on_config_changed)
        self._config_panel.skin_changed.connect(self._apply_skin)

        self._sello_panel = SelloPanel()
        self._sello_panel.set_image_params(self._prefs_to_image_params(self._prefs))
        self._sello_panel.config_changed.connect(self._on_config_changed)

        self._right_tabs = QTabWidget()
        self._right_tabs.addTab(self._config_panel, "Folio")
        self._right_tabs.addTab(self._sello_panel, "Sello")
        cols.addWidget(self._right_tabs, 3)

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

        self._btn_open_output = QPushButton("Abrir carpeta")
        self._btn_open_output.setObjectName("secondary")
        self._btn_open_output.setVisible(False)
        self._btn_open_output.setToolTip("Abrir carpeta de archivos foliados")
        self._btn_open_output.clicked.connect(self._on_open_output)
        bottom.addWidget(self._btn_open_output)

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
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        item = self._file_list.currentItem()
        if item is None:
            return
        path = Path(item.data(0x0100))
        prefs = self._config_panel.get_preferences()
        folio_text = f"{prefs.prefix}{prefs.start:04d}"
        self._preview.load_pdf(path)
        self._preview.update_folio(folio_text, self._config_panel.get_config([path]).stamp)

    @Slot()
    def _on_file_selected(self, current, previous) -> None:
        if current is None:
            return
        self._refresh_preview()

    @Slot()
    def _on_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar PDFs", "", "PDF (*.pdf)")
        if paths:
            self._file_list.add_files([Path(p) for p in paths])

    @Slot(int, int)
    def _on_summary_changed(self, checked: int, pages: int) -> None:
        if checked == 0:
            self._summary_label.setText("Sin archivos seleccionados (✓)")
        elif checked == 1:
            pstr = f"{pages} pág" + ("s" if pages != 1 else "")
            self._summary_label.setText(f"1 archivo  ·  {pstr}")
        else:
            self._summary_label.setText(f"{checked} archivos  ·  {pages} págs")

    @Slot()
    def _on_foliar(self):
        files = self._file_list.get_checked_files()
        if not files:
            self._status_label.setText("No hay archivos con ✓ para foliar.")
            return
        self._file_list.reset_marks()
        self._btn_open_output.setVisible(False)
        self._run_batch(files)

    @Slot()
    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()

    # ------------------------------------------------------------------
    @staticmethod
    def _prefs_to_image_params(prefs):
        from pdf_foliado.engine.image_stamper import ImageStampParams
        return ImageStampParams(
            image_path=prefs.image_stamp_path,
            corner=prefs.image_stamp_corner,
            d1_mm=prefs.image_stamp_d1_mm,
            d2_mm=prefs.image_stamp_d2_mm,
            angle_deg=prefs.image_stamp_angle_deg,
            width_mm=prefs.image_stamp_width_mm,
            pages=prefs.image_stamp_pages,
            enabled=prefs.image_stamp_enabled,
        )

    def _get_full_config(self, files):
        cfg = self._config_panel.get_config(files)
        cfg.image_stamp = self._sello_panel.get_image_params()
        return cfg

    def _run_batch(self, files: list[Path]) -> None:
        from pdf_foliado.engine.batch import BatchWorker
        cfg = self._get_full_config(files)
        self._worker = BatchWorker(cfg)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.file_error.connect(self._on_file_error)
        self._worker.finished.connect(self._on_finished)
        self._worker.password_needed.connect(self._on_password_needed)
        self._worker.file_warning.connect(self._on_file_warning)
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
        self._file_list.mark_done(src)
        self._last_output_dir = Path(dst).parent

    @Slot(str, str)
    def _on_file_error(self, src: str, err: str):
        self._status_label.setText(f"Error: {err}")

    @Slot()
    def _on_finished(self):
        self._progress.setValue(self._progress.maximum())
        self._progress.setVisible(False)
        self._btn_cancel.setVisible(False)
        self._btn_foliar.setEnabled(True)
        self._status_label.setText("Completado.")
        self._worker = None
        if self._last_output_dir and self._last_output_dir.exists():
            self._btn_open_output.setVisible(True)

    @Slot()
    def _on_open_output(self) -> None:
        if self._last_output_dir and self._last_output_dir.exists():
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self._last_output_dir))
            )

    @Slot(str, str)
    def _on_file_warning(self, src_path: str, msg: str) -> None:
        self._status_label.setText(f"⚠ {msg}")

    @Slot(str)
    def _on_password_needed(self, path: str) -> None:
        name = Path(path).name
        pwd, ok = QInputDialog.getText(
            self,
            "Contraseña requerida",
            f"El archivo '{name}' está protegido.\nIngrese la contraseña:",
            QLineEdit.EchoMode.Password,
        )
        if self._worker:
            self._worker.provide_password(path, pwd if ok else "")

    def get_preferences(self) -> Preferences:
        prefs = self._config_panel.get_preferences()
        ip = self._sello_panel.get_image_params()
        prefs.image_stamp_path = ip.image_path
        prefs.image_stamp_corner = ip.corner
        prefs.image_stamp_d1_mm = ip.d1_mm
        prefs.image_stamp_d2_mm = ip.d2_mm
        prefs.image_stamp_angle_deg = ip.angle_deg
        prefs.image_stamp_width_mm = ip.width_mm
        prefs.image_stamp_pages = ip.pages
        prefs.image_stamp_enabled = ip.enabled
        return prefs
