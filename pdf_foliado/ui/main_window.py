"""Main application window — two-column layout, light theme."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt, Slot, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QProgressBar, QLabel, QFileDialog,
    QSizePolicy, QApplication, QInputDialog, QLineEdit,
    QCheckBox, QScrollArea, QFrame, QSplitter, QMessageBox,
)

from pdf_foliado.config.preferences import Preferences
from pdf_foliado.ui._theme import (
    APP_NAME, APP_VERSION, PALETTE_TOKENS, build_stylesheet,
    OK, WARN, ERROR, MUTED,
)
from pdf_foliado.ui.file_list import FileListWidget, _ROLE_PATH
from pdf_foliado.ui.preview_widget import PreviewWidget


class _CollapsibleCard(QWidget):
    """Light accordion card: header checkbox enables the feature and expands it."""
    state_changed = Signal(bool)

    def __init__(self, title: str, subtitle: str, content: QWidget,
                 checked: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header band
        self._hdr = QWidget()
        self._hdr.setObjectName("cardHdr")
        self._hdr.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hdr_lay = QHBoxLayout(self._hdr)
        hdr_lay.setContentsMargins(12, 8, 12, 8)
        hdr_lay.setSpacing(8)

        self._chk = QCheckBox(title)
        self._chk.setChecked(checked)
        self._chk.setToolTip(f"Activar o desactivar: {title.lower()}")
        hdr_lay.addWidget(self._chk)
        self._subtitle = QLabel(subtitle)
        hdr_lay.addWidget(self._subtitle)
        hdr_lay.addStretch()
        self._state = QLabel()
        self._state.setObjectName("cardState")
        hdr_lay.addWidget(self._state)
        lay.addWidget(self._hdr)

        # Body
        self._body = QWidget()
        body_lay = QVBoxLayout(self._body)
        body_lay.setContentsMargins(14, 10, 14, 12)
        body_lay.setSpacing(0)
        body_lay.addWidget(content)
        lay.addWidget(self._body)

        self._chk.toggled.connect(self._on_toggled)
        self._apply_state(checked)

    def _apply_state(self, checked: bool) -> None:
        self._body.setVisible(checked)
        self._state.setText("Activado" if checked else "Desactivado")
        self._hdr.setProperty("expanded", "true" if checked else "false")
        self._hdr.style().unpolish(self._hdr)
        self._hdr.style().polish(self._hdr)

    def _on_toggled(self, checked: bool) -> None:
        self._apply_state(checked)
        self.state_changed.emit(checked)

    def is_checked(self) -> bool:
        return self._chk.isChecked()

    def set_checked(self, v: bool) -> None:
        self._chk.setChecked(v)


class MainWindow(QMainWindow):
    def __init__(self, base_dir: Path | None = None,
                 prefs: Preferences | None = None, parent=None):
        super().__init__(parent)
        self._base_dir = base_dir or Path.cwd()
        self._prefs = prefs or Preferences()
        self._worker = None
        self._last_output_dir: Path | None = None
        self._preview_page = 0
        self._run_ok = 0
        self._run_errors: list[tuple[str, str]] = []
        self._run_warnings: list[tuple[str, str]] = []

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(980, 640)
        self._build_ui()
        self._install_shortcuts()
        # Apply skin after build so every widget exists
        self._apply_skin(self._prefs.skin)
        self._fit_right_pane()
        self._update_foliar_button()

    def _fit_right_pane(self) -> None:
        need = self._scroll_inner.minimumSizeHint().width() + 6 + 16 + 22
        self._right_pane.setMinimumWidth(max(420, need))

    # ------------------------------------------------------------------
    def _apply_skin(self, skin: str) -> None:
        """Apply stylesheet and store current skin."""
        if skin not in PALETTE_TOKENS:
            skin = "rojo"
        self._prefs.skin = skin
        QApplication.instance().setStyleSheet(build_stylesheet(skin))
        for name, btn in self._skin_btns.items():
            btn.setChecked(name == skin)
        if hasattr(self, "_right_pane"):
            self._fit_right_pane()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- top bar ---
        header = QWidget()
        header.setObjectName("topBar")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 12, 16, 4)
        h_lay.setSpacing(8)
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        h_lay.addWidget(title)
        version = QLabel(f"v{APP_VERSION}")
        version.setObjectName("appVersion")
        h_lay.addWidget(version)
        h_lay.addStretch()
        skin_lbl = QLabel("Color:")
        skin_lbl.setObjectName("hint")
        h_lay.addWidget(skin_lbl)
        self._skin_btns: dict[str, QPushButton] = {}
        for skin_name, t in PALETTE_TOKENS.items():
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(22, 22)
            btn.setToolTip(f"Color de la interfaz: {t['label']}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton{{background:{t['accent']};border-radius:11px;"
                f"border:2px solid white;padding:0;}}"
                f"QPushButton:hover{{background:{t['accent_h']};}}"
                f"QPushButton:checked{{border:2px solid {t['accent']};"
                f"background:qradialgradient(cx:0.5,cy:0.5,radius:0.5,fx:0.5,fy:0.5,"
                f"stop:0 {t['accent']},stop:0.55 {t['accent']},stop:0.6 white,stop:1 white);}}"
            )
            btn.clicked.connect(lambda checked=False, s=skin_name: self._apply_skin(s))
            self._skin_btns[skin_name] = btn
            h_lay.addWidget(btn)
        root.addWidget(header)

        # --- columns ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ============ Left pane: files + preview ============
        left_w = QWidget()
        left = QVBoxLayout(left_w)
        left.setContentsMargins(16, 8, 6, 8)
        left.setSpacing(6)

        files_title = QLabel("1 · Archivos PDF")
        files_title.setObjectName("sectionTitle")
        left.addWidget(files_title)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self._btn_add = QPushButton("+ Agregar PDFs")
        self._btn_add.setToolTip("Agregar archivos PDF (Ctrl+O)")
        self._btn_add.clicked.connect(self._on_add_files)
        toolbar.addWidget(self._btn_add)
        self._btn_remove = QPushButton("Quitar")
        self._btn_remove.setObjectName("secondary")
        self._btn_remove.setToolTip("Quitar el archivo seleccionado de la lista (Supr)")
        self._btn_remove.clicked.connect(self._file_list_remove)
        toolbar.addWidget(self._btn_remove)
        self._btn_clear = QPushButton("Vaciar lista")
        self._btn_clear.setObjectName("ghost")
        self._btn_clear.setToolTip("Quitar todos los archivos de la lista")
        self._btn_clear.clicked.connect(self._on_clear_list)
        toolbar.addWidget(self._btn_clear)
        toolbar.addStretch()
        self._btn_up = QPushButton("↑ Subir")
        self._btn_up.setObjectName("secondary")
        self._btn_up.setToolTip("Subir el archivo seleccionado (Ctrl+↑)")
        self._btn_down = QPushButton("↓ Bajar")
        self._btn_down.setObjectName("secondary")
        self._btn_down.setToolTip("Bajar el archivo seleccionado (Ctrl+↓)")
        toolbar.addWidget(self._btn_up)
        toolbar.addWidget(self._btn_down)
        left.addLayout(toolbar)

        self._file_list = FileListWidget()
        self._file_list.setMinimumHeight(120)
        self._file_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._file_list.currentItemChanged.connect(self._on_file_selected)
        self._file_list.summary_changed.connect(self._on_summary_changed)
        self._file_list.files_changed.connect(lambda _: self._on_list_changed())
        self._btn_up.clicked.connect(self._file_list.move_up)
        self._btn_down.clicked.connect(self._file_list.move_down)
        left.addWidget(self._file_list, 2)

        self._summary_label = QLabel("Sin archivos")
        self._summary_label.setObjectName("hint")
        left.addWidget(self._summary_label)

        # Preview header with page navigation
        prev_hdr = QHBoxLayout()
        prev_hdr.setSpacing(6)
        prev_title = QLabel("Vista previa")
        prev_title.setObjectName("sectionTitle")
        prev_hdr.addWidget(prev_title, 1)
        self._btn_prev_page = QPushButton("←")
        self._btn_prev_page.setObjectName("ghost")
        self._btn_prev_page.setFixedWidth(40)
        self._btn_prev_page.setStyleSheet("padding: 4px 0;")
        self._btn_prev_page.setToolTip("Página anterior (Re Pág)")
        self._btn_prev_page.clicked.connect(lambda: self._step_page(-1))
        self._page_label = QLabel("")
        self._page_label.setObjectName("hint")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setMinimumWidth(180)
        self._btn_next_page = QPushButton("→")
        self._btn_next_page.setObjectName("ghost")
        self._btn_next_page.setFixedWidth(40)
        self._btn_next_page.setStyleSheet("padding: 4px 0;")
        self._btn_next_page.setToolTip("Página siguiente (Av Pág)")
        self._btn_next_page.clicked.connect(lambda: self._step_page(1))
        prev_hdr.addWidget(self._btn_prev_page)
        prev_hdr.addWidget(self._page_label)
        prev_hdr.addWidget(self._btn_next_page)
        left.addLayout(prev_hdr)

        self._preview = PreviewWidget()
        left.addWidget(self._preview, 5)

        splitter.addWidget(left_w)

        # ============ Right pane: settings cards ============
        from pdf_foliado.ui.config_panel import ConfigPanel
        from pdf_foliado.ui.sello_panel import SelloPanel
        self._config_panel = ConfigPanel()
        self._config_panel.set_preferences(self._prefs)
        self._config_panel.config_changed.connect(self._on_config_changed)

        self._sello_panel = SelloPanel()
        self._sello_panel.set_image_params(self._prefs_to_image_params(self._prefs))
        self._sello_panel.config_changed.connect(self._on_config_changed)

        self._folio_card = _CollapsibleCard(
            "Folio", "número en cada página", self._config_panel,
            self._prefs.folio_enabled)
        self._folio_card.state_changed.connect(self._on_card_toggle)

        self._sello_card = _CollapsibleCard(
            "Sello", "imagen: firma, logo, timbre", self._sello_panel,
            self._prefs.image_stamp_enabled)
        self._sello_card.state_changed.connect(self._on_card_toggle)
        self._sello_panel.image_selected.connect(
            lambda: self._sello_card.set_checked(True))

        right_w = QWidget()
        right_vlay = QVBoxLayout(right_w)
        right_vlay.setContentsMargins(6, 8, 16, 8)
        right_vlay.setSpacing(6)
        cfg_title = QLabel("2 · Configuración")
        cfg_title.setObjectName("sectionTitle")
        right_vlay.addWidget(cfg_title)

        outer_scroll = QScrollArea()
        outer_scroll.setWidgetResizable(True)
        outer_scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_inner = QWidget()
        scroll_lay = QVBoxLayout(scroll_inner)
        scroll_lay.setContentsMargins(0, 0, 6, 0)
        scroll_lay.setSpacing(10)
        scroll_lay.addWidget(self._folio_card)
        scroll_lay.addWidget(self._sello_card)
        scroll_lay.addStretch()
        outer_scroll.setWidget(scroll_inner)
        right_vlay.addWidget(outer_scroll, 1)
        # The scroll area hides its content's minimum width from the splitter;
        # without this the settings get clipped on narrow windows.
        self._right_pane = right_w
        self._scroll_inner = scroll_inner

        splitter.addWidget(right_w)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([760, 480])

        root.addWidget(splitter, 1)

        # --- bottom bar ---
        bottom_w = QWidget()
        bottom_w.setObjectName("bottomBar")
        bottom_w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bottom = QHBoxLayout(bottom_w)
        bottom.setContentsMargins(16, 10, 16, 10)
        bottom.setSpacing(8)
        self._status_label = QLabel("Listo. Agrega PDFs para empezar.")
        self._status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._status_label.setWordWrap(True)
        bottom.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedWidth(220)
        self._progress.setFormat("%v de %m")
        self._progress.setVisible(False)
        bottom.addWidget(self._progress)

        self._btn_open_output = QPushButton("Abrir carpeta")
        self._btn_open_output.setObjectName("secondary")
        self._btn_open_output.setVisible(False)
        self._btn_open_output.setToolTip("Abrir la carpeta con los archivos foliados")
        self._btn_open_output.clicked.connect(self._on_open_output)
        bottom.addWidget(self._btn_open_output)

        self._btn_cancel = QPushButton("Cancelar")
        self._btn_cancel.setObjectName("secondary")
        self._btn_cancel.setVisible(False)
        self._btn_cancel.setToolTip("Detener después del archivo en curso (Esc)")
        self._btn_cancel.clicked.connect(self._on_cancel)
        bottom.addWidget(self._btn_cancel)

        self._btn_foliar = QPushButton("Foliar")
        self._btn_foliar.setObjectName("primary")
        self._btn_foliar.setToolTip("Generar los PDFs foliados (Ctrl+Enter)")
        self._btn_foliar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_foliar.clicked.connect(self._on_foliar)
        bottom.addWidget(self._btn_foliar)

        root.addWidget(bottom_w)
        self._update_page_nav(0)

    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence.StandardKey.Open, self, activated=self._on_add_files)
        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            QShortcut(QKeySequence(seq), self, activated=self._on_foliar)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self._on_cancel)
        QShortcut(QKeySequence(Qt.Key.Key_PageUp), self,
                  activated=lambda: self._step_page(-1))
        QShortcut(QKeySequence(Qt.Key.Key_PageDown), self,
                  activated=lambda: self._step_page(1))

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------
    def _set_status(self, text: str, kind: str = "info") -> None:
        color = {"ok": OK, "warn": WARN, "error": ERROR}.get(kind, MUTED)
        weight = "600" if kind in ("ok", "warn", "error") else "400"
        self._status_label.setStyleSheet(f"color:{color}; font-weight:{weight};")
        self._status_label.setText(text)

    def _update_foliar_button(self) -> None:
        files = self._file_list.get_checked_files()
        n = len(files)
        busy = self._worker is not None
        if n == 0:
            self._btn_foliar.setText("Foliar")
        elif n == 1:
            self._btn_foliar.setText("Foliar 1 archivo")
        else:
            self._btn_foliar.setText(f"Foliar {n} archivos")
        nothing_on = not (self._folio_card.is_checked() or self._sello_card.is_checked())
        self._btn_foliar.setEnabled(n > 0 and not busy and not nothing_on)
        if nothing_on:
            self._btn_foliar.setToolTip("Activa Folio o Sello para poder foliar")
        else:
            self._btn_foliar.setToolTip("Generar los PDFs foliados (Ctrl+Enter)")
        has_rows = self._file_list.count() > 0
        self._btn_remove.setEnabled(has_rows and not busy)
        self._btn_clear.setEnabled(has_rows and not busy)
        self._btn_up.setEnabled(self._file_list.count() > 1 and not busy)
        self._btn_down.setEnabled(self._file_list.count() > 1 and not busy)
        self._btn_add.setEnabled(not busy)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------
    def _current_path(self) -> Path | None:
        item = self._file_list.currentItem()
        if item is None:
            return None
        return Path(item.data(_ROLE_PATH))

    def _folio_for(self, path: Path, page_idx: int) -> str:
        prefs = self._config_panel.get_preferences()
        n = self._file_list.page_count(path) or 1
        base = prefs.start
        if prefs.mode == "correlativo":
            base += self._file_list.folio_offset(path)
        num = base + page_idx if prefs.order == "asc" else base + (n - 1 - page_idx)
        return prefs.prefix + str(num).zfill(4)

    def _update_page_nav(self, n_pages: int) -> None:
        path = self._current_path()
        if path is None or n_pages <= 0:
            self._page_label.setText("")
            self._btn_prev_page.setEnabled(False)
            self._btn_next_page.setEnabled(False)
            return
        text = f"Página {self._preview_page + 1} de {n_pages}"
        if self._folio_card.is_checked():
            text += f"  ·  folio {self._folio_for(path, self._preview_page)}"
        self._page_label.setText(text)
        self._btn_prev_page.setEnabled(self._preview_page > 0)
        self._btn_next_page.setEnabled(self._preview_page < n_pages - 1)

    def _step_page(self, delta: int) -> None:
        path = self._current_path()
        if path is None:
            return
        n = self._file_list.page_count(path)
        new = max(0, min(self._preview_page + delta, n - 1))
        if new != self._preview_page:
            self._preview_page = new
            self._refresh_preview()

    def _refresh_preview(self) -> None:
        path = self._current_path()
        if path is None:
            self._preview.clear_preview()
            self._update_page_nav(0)
            return
        n_pages = self._file_list.page_count(path)
        if n_pages and self._preview_page >= n_pages:
            self._preview_page = n_pages - 1
        self._preview.load_pdf(path, self._preview_page)
        if self._folio_card.is_checked():
            folio_text = self._folio_for(path, self._preview_page)
            self._preview.update_folio(
                folio_text, self._config_panel.get_config([path]).stamp)
        else:
            self._preview.update_folio("", None)
        image_params = self._sello_panel.get_image_params()
        image_params.enabled = self._sello_card.is_checked()
        if image_params.pages == "primera" and self._preview_page > 0:
            image_params.enabled = False
        self._preview.update_image_stamp(image_params)
        self._update_page_nav(n_pages)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    @Slot(bool)
    def _on_card_toggle(self, checked: bool) -> None:
        self._refresh_preview()
        self._update_foliar_button()

    @Slot()
    def _on_config_changed(self):
        old_skin = self._prefs.skin
        self._prefs = self._config_panel.get_preferences()
        self._prefs.skin = old_skin
        self._refresh_preview()

    @Slot()
    def _on_file_selected(self, current, previous) -> None:
        self._preview_page = 0
        self._refresh_preview()

    def _on_list_changed(self) -> None:
        self._refresh_preview()
        self._update_foliar_button()

    def _file_list_remove(self) -> None:
        self._file_list.remove_selected()

    @Slot()
    def _on_clear_list(self) -> None:
        if self._file_list.count() == 0:
            return
        resp = QMessageBox.question(
            self, "Vaciar lista",
            "¿Quitar todos los archivos de la lista?\n"
            "(Los archivos no se borran del disco.)")
        if resp == QMessageBox.StandardButton.Yes:
            self._file_list.clear_all()
            self._set_status("Lista vacía. Agrega PDFs para empezar.")

    @Slot()
    def _on_add_files(self):
        if self._worker is not None:
            return
        start_dir = str(self._last_output_dir) if self._last_output_dir else ""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar PDFs", start_dir, "PDF (*.pdf)")
        if paths:
            self._file_list.add_files([Path(p) for p in paths])

    @Slot(int, int)
    def _on_summary_changed(self, checked: int, pages: int) -> None:
        total = self._file_list.count()
        if total == 0:
            self._summary_label.setText("Sin archivos")
        elif checked == 0:
            self._summary_label.setText(
                f"{total} en la lista · ninguno marcado ✓ para foliar")
        else:
            arch = "archivo" if checked == 1 else "archivos"
            pstr = f"{pages} pág" + ("s" if pages != 1 else "")
            extra = f" de {total}" if checked != total else ""
            self._summary_label.setText(
                f"{checked}{extra} {arch} marcados para foliar  ·  {pstr}")
        self._update_foliar_button()
        if self._worker is None and total and checked:
            self._set_status("Revisa la configuración y la vista previa; luego pulsa «Foliar».")
        elif self._worker is None and total == 0:
            self._set_status("Listo. Agrega PDFs para empezar.")
        # Correlativo folios depend on which files are checked
        self._refresh_preview()

    @Slot()
    def _on_foliar(self):
        if self._worker is not None:
            return
        files = self._file_list.get_checked_files()
        if not files:
            self._set_status("Marca con ✓ al menos un archivo para foliar.", "warn")
            return
        if not (self._folio_card.is_checked() or self._sello_card.is_checked()):
            self._set_status("Activa «Folio» o «Sello» para poder foliar.", "warn")
            return
        if self._sello_card.is_checked() and not self._sello_panel.has_image():
            resp = QMessageBox.question(
                self, "Sello sin imagen",
                "El sello está activado pero no hay una imagen válida elegida.\n\n"
                "¿Continuar solo con el folio?")
            if resp != QMessageBox.StandardButton.Yes:
                return
            self._sello_card.set_checked(False)
        self._file_list.reset_marks()
        self._btn_open_output.setVisible(False)
        self._run_batch(files)

    @Slot()
    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()
            self._set_status("Cancelando… se detendrá al terminar el archivo en curso.", "warn")

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
        cfg.folio_enabled = self._folio_card.is_checked()
        image_params = self._sello_panel.get_image_params()
        image_params.enabled = self._sello_card.is_checked()
        cfg.image_stamp = image_params
        return cfg

    def _run_batch(self, files: list[Path]) -> None:
        from pdf_foliado.engine.batch import BatchWorker
        cfg = self._get_full_config(files)
        self._run_ok = 0
        self._run_errors = []
        self._run_warnings = []
        self._worker = BatchWorker(cfg)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.file_error.connect(self._on_file_error)
        self._worker.finished.connect(self._on_finished)
        self._worker.password_needed.connect(self._on_password_needed)
        self._worker.file_warning.connect(self._on_file_warning)
        self._progress.setRange(0, len(files))
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._btn_cancel.setVisible(True)
        self._update_foliar_button()
        self._set_status(f"Foliando {len(files)} archivo(s)…")
        self._worker.start()

    @Slot(int, int)
    def _on_progress(self, current: int, total: int):
        # Sync range to actual valid-file count in case some were rejected
        self._progress.setRange(0, total)
        self._progress.setValue(current)

    @Slot(str, str)
    def _on_file_done(self, src: str, dst: str):
        self._run_ok += 1
        self._progress.setValue(self._run_ok)
        self._set_status(f"Listo: {Path(dst).name}")
        self._file_list.mark_done(src)
        self._last_output_dir = Path(dst).parent

    @Slot(str, str)
    def _on_file_error(self, src: str, err: str):
        self._run_errors.append((src, err))
        self._file_list.mark_error(src, err)
        self._set_status(f"Error en {Path(src).name}: {err}", "error")

    @Slot()
    def _on_finished(self):
        self._progress.setVisible(False)
        self._btn_cancel.setVisible(False)
        self._worker = None
        self._update_foliar_button()
        ok, n_err = self._run_ok, len(self._run_errors)
        if n_err == 0 and ok > 0:
            msg = f"✓ Completado: {ok} archivo(s) foliado(s)."
            if self._run_warnings:
                msg += f"  ⚠ {len(self._run_warnings)} aviso(s)."
            self._set_status(msg, "warn" if self._run_warnings else "ok")
        elif ok == 0 and n_err == 0:
            self._set_status("Proceso cancelado. No se generaron archivos.", "warn")
        else:
            self._set_status(
                f"Terminado: {ok} correcto(s), {n_err} con error.", "error")
            detail = "\n".join(f"• {Path(p).name}: {e}" for p, e in self._run_errors)
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("Archivos con error")
            box.setText(f"{n_err} archivo(s) no se pudieron foliar.")
            box.setInformativeText("Los demás se generaron normalmente.")
            box.setDetailedText(detail)
            box.open()
        if self._last_output_dir and self._last_output_dir.exists() and ok:
            self._btn_open_output.setVisible(True)

    @Slot()
    def _on_open_output(self) -> None:
        if self._last_output_dir and self._last_output_dir.exists():
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self._last_output_dir))
            )

    @Slot(str, str)
    def _on_file_warning(self, src_path: str, msg: str) -> None:
        self._run_warnings.append((src_path, msg))
        self._set_status(f"⚠ {Path(src_path).name}: {msg}", "warn")

    @Slot(str)
    def _on_password_needed(self, path: str) -> None:
        name = Path(path).name
        pwd, ok = QInputDialog.getText(
            self,
            "Contraseña requerida",
            f"El archivo «{name}» está protegido.\nIngresa la contraseña:",
            QLineEdit.EchoMode.Password,
        )
        if self._worker:
            self._worker.provide_password(path, pwd if ok else "")

    def get_preferences(self) -> Preferences:
        prefs = self._config_panel.get_preferences()
        prefs.skin = self._prefs.skin
        prefs.folio_enabled = self._folio_card.is_checked()
        ip = self._sello_panel.get_image_params()
        prefs.image_stamp_path = ip.image_path
        prefs.image_stamp_corner = ip.corner
        prefs.image_stamp_d1_mm = ip.d1_mm
        prefs.image_stamp_d2_mm = ip.d2_mm
        prefs.image_stamp_angle_deg = ip.angle_deg
        prefs.image_stamp_width_mm = ip.width_mm
        prefs.image_stamp_pages = ip.pages
        prefs.image_stamp_enabled = self._sello_card.is_checked()
        return prefs
