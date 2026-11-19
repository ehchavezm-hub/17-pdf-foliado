"""Right pane — Sello de imagen tab."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QButtonGroup, QDoubleSpinBox,
    QComboBox, QScrollArea, QFrame, QFileDialog,
)

from pdf_foliado.engine.image_stamper import ImageStampParams

_ANGLE_PRESETS = ["0", "15", "30", "45", "60", "90", "135", "180", "270"]


class _ToggleButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setObjectName("secondary")


class SelloPanel(QWidget):
    config_changed = Signal()
    image_selected = Signal()   # emitted when user picks an image file

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_path = ""
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(14)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # --- Imagen ---
        lay.addWidget(self._section("Archivo de imagen"))
        img_row = QHBoxLayout()
        self._btn_browse = QPushButton("Seleccionar…")
        self._btn_browse.setObjectName("secondary")
        self._btn_browse.setFixedWidth(110)
        self._btn_browse.clicked.connect(self._on_browse)
        self._lbl_file = QLabel("(ninguno)")
        self._lbl_file.setStyleSheet("color: #757575; font-size: 11px;")
        self._lbl_file.setWordWrap(True)
        img_row.addWidget(self._btn_browse)
        img_row.addWidget(self._lbl_file, 1)
        lay.addLayout(img_row)

        # --- Posición ---
        lay.addWidget(self._section("Posición del sello"))
        self._corner_group = QButtonGroup(self)
        self._corner_group.setExclusive(True)
        self._corner_btns: dict[str, QPushButton] = {}
        _labels = {
            "TL": "↖ Sup-Izq", "TC": "↑ Sup-Cen", "TR": "↗ Sup-Der",
            "BL": "↙ Inf-Izq", "BC": "↓ Inf-Cen", "BR": "↘ Inf-Der",
        }
        grid_w = QWidget()
        grid_v = QVBoxLayout(grid_w)
        grid_v.setContentsMargins(0, 0, 0, 0)
        grid_v.setSpacing(4)
        for row_corners in (("TL", "TC", "TR"), ("BL", "BC", "BR")):
            row = QHBoxLayout()
            row.setSpacing(4)
            for corner in row_corners:
                btn = _ToggleButton(_labels[corner])
                btn.setProperty("corner", corner)
                self._corner_group.addButton(btn)
                self._corner_btns[corner] = btn
                row.addWidget(btn)
            grid_v.addLayout(row)
        self._corner_btns["BR"].setChecked(True)
        lay.addWidget(grid_w)

        form1 = QFormLayout()
        self._spin_d1 = QDoubleSpinBox()
        self._spin_d1.setRange(0.0, 100.0)
        self._spin_d1.setValue(10.0)
        self._spin_d1.setSuffix(" mm")
        form1.addRow("Distancia borde (d1):", self._spin_d1)
        self._spin_d2 = QDoubleSpinBox()
        self._spin_d2.setRange(0.0, 100.0)
        self._spin_d2.setValue(15.0)
        self._spin_d2.setSuffix(" mm")
        form1.addRow("Distancia lateral (d2):", self._spin_d2)
        lay.addLayout(form1)

        # --- Ángulo ---
        lay.addWidget(self._section("Ángulo de rotación"))
        angle_row = QHBoxLayout()
        self._combo_angle = QComboBox()
        self._combo_angle.setEditable(True)
        self._combo_angle.addItems(_ANGLE_PRESETS)
        self._combo_angle.setCurrentText("0")
        self._combo_angle.lineEdit().setPlaceholderText("ej. 37")
        angle_row.addWidget(self._combo_angle, 1)
        angle_row.addWidget(QLabel("°"))
        lay.addLayout(angle_row)

        # --- Tamaño ---
        lay.addWidget(self._section("Tamaño de la imagen"))
        form2 = QFormLayout()
        self._spin_width = QDoubleSpinBox()
        self._spin_width.setRange(5.0, 500.0)
        self._spin_width.setValue(30.0)
        self._spin_width.setSuffix(" mm")
        form2.addRow("Ancho:", self._spin_width)
        self._lbl_height_note = QLabel("Alto: proporcional al archivo")
        self._lbl_height_note.setStyleSheet("color: #757575; font-size: 11px;")
        form2.addRow("", self._lbl_height_note)
        lay.addLayout(form2)

        # --- Páginas ---
        lay.addWidget(self._section("Aplicar en"))
        self._pages_group = QButtonGroup(self)
        self._pages_group.setExclusive(True)
        pages_row = QHBoxLayout()
        self._btn_primera = _ToggleButton("Primera página")
        self._btn_todas = _ToggleButton("Todas las páginas")
        self._btn_todas.setChecked(True)
        self._pages_group.addButton(self._btn_primera, 0)
        self._pages_group.addButton(self._btn_todas, 1)
        pages_row.addWidget(self._btn_primera)
        pages_row.addWidget(self._btn_todas)
        pages_row.addStretch()
        lay.addLayout(pages_row)

        lay.addStretch()

        # --- Señales ---
        self._corner_group.buttonClicked.connect(lambda _: self.config_changed.emit())
        self._spin_d1.valueChanged.connect(lambda _: self.config_changed.emit())
        self._spin_d2.valueChanged.connect(lambda _: self.config_changed.emit())
        self._combo_angle.currentTextChanged.connect(lambda _: self.config_changed.emit())
        self._spin_width.valueChanged.connect(lambda _: self.config_changed.emit())
        self._pages_group.buttonClicked.connect(lambda _: self.config_changed.emit())

    # ------------------------------------------------------------------
    @staticmethod
    def _section(title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            "font-weight: 700; font-size: 12px; color: #616161;"
            "border-bottom: 1px solid #E0E0E0; padding-bottom: 2px;"
        )
        return lbl

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen",
            str(Path(self._image_path).parent) if self._image_path else "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)",
        )
        if path:
            self._image_path = path
            self._lbl_file.setText(Path(path).name)
            self.image_selected.emit()
            self.config_changed.emit()

    # ------------------------------------------------------------------
    def _angle_value(self) -> float:
        try:
            return float(self._combo_angle.currentText().strip().rstrip("°"))
        except ValueError:
            return 0.0

    def get_image_params(self) -> ImageStampParams:
        corner = "BR"
        for c, btn in self._corner_btns.items():
            if btn.isChecked():
                corner = c
                break
        return ImageStampParams(
            image_path=self._image_path,
            corner=corner,
            d1_mm=self._spin_d1.value(),
            d2_mm=self._spin_d2.value(),
            angle_deg=self._angle_value(),
            width_mm=self._spin_width.value(),
            pages="primera" if self._btn_primera.isChecked() else "todas",
            enabled=True,  # enabled state controlled by outer toggle in main window
        )

    def set_image_params(self, params: ImageStampParams) -> None:
        self._image_path = params.image_path
        self._lbl_file.setText(Path(params.image_path).name if params.image_path else "(ninguno)")
        if params.corner in self._corner_btns:
            self._corner_btns[params.corner].setChecked(True)
        self._spin_d1.setValue(params.d1_mm)
        self._spin_d2.setValue(params.d2_mm)
        self._combo_angle.setCurrentText(str(params.angle_deg))
        self._spin_width.setValue(params.width_mm)
        if params.pages == "primera":
            self._btn_primera.setChecked(True)
        else:
            self._btn_todas.setChecked(True)
