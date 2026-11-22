"""Right pane — all stamping controls."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Signal, QSize
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QButtonGroup, QSpinBox, QDoubleSpinBox,
    QLineEdit,
)

from pdf_foliado.config.preferences import Preferences
from pdf_foliado.engine.batch import BatchConfig
from pdf_foliado.engine.stamper import StampParams

# The stamper writes the folio with the PDF standard font Helvetica, which
# every PDF viewer renders identically without embedding anything.
_STAMP_FONT = "Helvetica"

_FOLIO_COLORS = [
    ("Negro", "#231F20"), ("Blanco", "#FFFFFF"), ("Rojo", "#E4002B"),
    ("Azul", "#005EB8"), ("Verde", "#1B7A4A"),
]


def _swatch_icon(hex_color: str) -> QIcon:
    pix = QPixmap(14, 14)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor("#9E9E9E"))
    p.setBrush(QColor(hex_color))
    p.drawEllipse(1, 1, 12, 12)
    p.end()
    return QIcon(pix)


def _hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("hint")
    lbl.setWordWrap(True)
    return lbl


class _ToggleButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setObjectName("secondary")


class ConfigPanel(QWidget):
    config_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(8)

        # --- Modo ---
        lay.addWidget(self._section("Modo de foliado"))
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        mode_row = QHBoxLayout()
        self._btn_por_doc = _ToggleButton("Por documento")
        self._btn_correlativo = _ToggleButton("Correlativo")
        self._btn_por_doc.setChecked(True)
        self._mode_group.addButton(self._btn_por_doc, 0)
        self._mode_group.addButton(self._btn_correlativo, 1)
        mode_row.addWidget(self._btn_por_doc)
        mode_row.addWidget(self._btn_correlativo)
        mode_row.addStretch()
        lay.addLayout(mode_row)
        self._btn_por_doc.setToolTip("Cada PDF empieza su propia numeración")
        self._btn_correlativo.setToolTip(
            "La numeración continúa de un PDF al siguiente, en el orden de la lista")
        self._mode_example = _hint("")
        lay.addWidget(self._mode_example)
        self._mode_group.idToggled.connect(self._on_mode_toggled)

        # --- Orden ---
        lay.addWidget(self._section("Orden de folios"))
        self._order_group = QButtonGroup(self)
        self._order_group.setExclusive(True)
        order_row = QHBoxLayout()
        self._btn_asc = _ToggleButton("0001 → N")
        self._btn_desc = _ToggleButton("N → 0001")
        self._btn_asc.setToolTip("La primera página lleva el folio más bajo")
        self._btn_desc.setToolTip(
            "La última página lleva el folio más bajo (foliado de atrás hacia adelante)")
        self._btn_asc.setChecked(True)
        self._order_group.addButton(self._btn_asc, 0)
        self._order_group.addButton(self._btn_desc, 1)
        order_row.addWidget(self._btn_asc)
        order_row.addWidget(self._btn_desc)
        order_row.addStretch()
        lay.addLayout(order_row)

        # --- Iniciar / Prefijo ---
        form1 = QFormLayout()
        form1.setVerticalSpacing(6)
        self._spin_start = QSpinBox()
        self._spin_start.setRange(1, 999999)
        self._spin_start.setValue(1)
        form1.addRow("Iniciar desde:", self._spin_start)
        self._edit_prefix = QLineEdit()
        self._edit_prefix.setPlaceholderText("ej. Folio ")
        self._edit_prefix.setMaxLength(50)
        self._edit_prefix.setToolTip("Texto que va antes del número, por ejemplo «Folio »")
        form1.addRow("Prefijo:", self._edit_prefix)
        lay.addLayout(form1)
        self._folio_example = QLabel()
        self._folio_example.setObjectName("accent")
        lay.addWidget(self._folio_example)

        # --- Posición ---
        lay.addWidget(self._section("Posición del folio"))
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

        form2 = QFormLayout()
        form2.setVerticalSpacing(6)
        self._spin_d1 = QDoubleSpinBox()
        self._spin_d1.setRange(1.0, 50.0)
        self._spin_d1.setValue(10.0)
        self._spin_d1.setSuffix(" mm")
        self._spin_d1.setToolTip("Distancia al borde superior o inferior de la página")
        form2.addRow("Distancia borde (d1):", self._spin_d1)
        self._spin_d2 = QDoubleSpinBox()
        self._spin_d2.setRange(1.0, 50.0)
        self._spin_d2.setValue(15.0)
        self._spin_d2.setSuffix(" mm")
        self._spin_d2.setToolTip(
            "Distancia al borde izquierdo o derecho (no se usa en posiciones centradas)")
        form2.addRow("Distancia lateral (d2):", self._spin_d2)
        lay.addLayout(form2)

        # --- Tipografía ---
        lay.addWidget(self._section("Tipografía"))
        typo_row = QHBoxLayout()
        typo_row.setSpacing(6)
        typo_row.addWidget(QLabel("Tamaño:"))
        self._spin_size = QSpinBox()
        self._spin_size.setRange(6, 48)
        self._spin_size.setValue(12)
        self._spin_size.setSuffix(" pt")
        typo_row.addWidget(self._spin_size)
        typo_row.addSpacing(8)
        self._btn_bold = _ToggleButton("N")  # Negrita
        self._btn_bold.setFixedSize(36, 30)
        self._btn_bold.setToolTip("Negrita")
        bold_font = self._btn_bold.font()
        bold_font.setBold(True)
        self._btn_bold.setFont(bold_font)
        self._btn_italic = _ToggleButton("I")
        self._btn_italic.setFixedSize(36, 30)
        self._btn_italic.setToolTip("Cursiva")
        italic_font = self._btn_italic.font()
        italic_font.setItalic(True)
        self._btn_italic.setFont(italic_font)
        typo_row.addWidget(self._btn_bold)
        typo_row.addWidget(self._btn_italic)
        typo_row.addStretch()
        lay.addLayout(typo_row)
        lay.addWidget(_hint(
            "Fuente: Helvetica (estándar PDF, se ve igual en cualquier equipo)."))

        # Folio color
        self._color_group = QButtonGroup(self)
        self._color_group.setExclusive(True)
        color_row = QHBoxLayout()
        color_row.setSpacing(4)
        for label, hex_val in _FOLIO_COLORS:
            btn = _ToggleButton(label)
            btn.setIcon(_swatch_icon(hex_val))
            btn.setIconSize(QSize(12, 12))
            btn.setProperty("color_hex", hex_val)
            btn.setToolTip(f"Color del folio: {label.lower()}")
            self._color_group.addButton(btn)
            color_row.addWidget(btn)
            if label == "Negro":
                btn.setChecked(True)
        color_row.addStretch()
        lay.addLayout(color_row)

        # --- Sufijo ---
        lay.addWidget(self._section("Archivo de salida"))
        form4 = QFormLayout()
        self._edit_suffix = QLineEdit("_fol")
        self._edit_suffix.setToolTip(
            "Se agrega al nombre del archivo nuevo. El original nunca se modifica.")
        form4.addRow("Sufijo:", self._edit_suffix)
        lay.addLayout(form4)
        self._suffix_example = _hint("")
        lay.addWidget(self._suffix_example)

        lay.addStretch()

        # Connect all controls so preview refreshes on every change
        self._corner_group.buttonClicked.connect(lambda _: self.config_changed.emit())
        self._order_group.buttonClicked.connect(lambda _: self.config_changed.emit())
        self._color_group.buttonClicked.connect(lambda _: self.config_changed.emit())
        self._spin_start.valueChanged.connect(lambda _: self.config_changed.emit())
        self._edit_prefix.textChanged.connect(lambda _: self.config_changed.emit())
        self._spin_d1.valueChanged.connect(lambda _: self.config_changed.emit())
        self._spin_d2.valueChanged.connect(lambda _: self.config_changed.emit())
        self._spin_size.valueChanged.connect(lambda _: self.config_changed.emit())
        self._edit_suffix.textChanged.connect(lambda _: self.config_changed.emit())
        self.config_changed.connect(self._update_examples)
        self._update_examples()
        self._btn_bold.toggled.connect(lambda _: self.config_changed.emit())
        self._btn_italic.toggled.connect(lambda _: self.config_changed.emit())

    # ------------------------------------------------------------------
    @staticmethod
    def _section(title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setObjectName("sectionTitle")
        return lbl

    def _on_mode_toggled(self, btn_id: int, checked: bool) -> None:
        if not checked:
            return
        self.config_changed.emit()

    def _update_examples(self) -> None:
        start = self._spin_start.value()
        prefix = self._edit_prefix.text()
        first = f"{prefix}{str(start).zfill(4)}"
        if self._btn_por_doc.isChecked():
            self._mode_example.setText(
                f"Cada PDF se folia por separado, empezando en {str(start).zfill(4)}.")
        else:
            self._mode_example.setText(
                "Un solo expediente: la numeración continúa de un PDF al siguiente.")
        self._folio_example.setText(f"Así se verá: {first}")
        suffix = self._edit_suffix.text()
        self._suffix_example.setText(
            f"Ejemplo: Contrato.pdf → Contrato{suffix}.pdf  (el original no se toca)")

    def get_preferences(self) -> Preferences:
        corner = "BR"
        for c, btn in self._corner_btns.items():
            if btn.isChecked():
                corner = c
                break

        color_hex = "#231F20"
        checked_color = self._color_group.checkedButton()
        if checked_color:
            color_hex = checked_color.property("color_hex")

        return Preferences(
            mode="por_documento" if self._btn_por_doc.isChecked() else "correlativo",
            order="asc" if self._btn_asc.isChecked() else "desc",
            start=self._spin_start.value(),
            prefix=self._edit_prefix.text(),
            corner=corner,
            d1_mm=self._spin_d1.value(),
            d2_mm=self._spin_d2.value(),
            font_name=_STAMP_FONT,
            font_size_pt=self._spin_size.value(),
            font_bold=self._btn_bold.isChecked(),
            font_italic=self._btn_italic.isChecked(),
            color_hex=color_hex,
            suffix_file=self._edit_suffix.text(),
        )

    def set_preferences(self, prefs: Preferences) -> None:
        if prefs.mode == "correlativo":
            self._btn_correlativo.setChecked(True)
        else:
            self._btn_por_doc.setChecked(True)
        if prefs.order == "desc":
            self._btn_desc.setChecked(True)
        else:
            self._btn_asc.setChecked(True)
        self._spin_start.setValue(prefs.start)
        self._edit_prefix.setText(prefs.prefix)
        if prefs.corner in self._corner_btns:
            self._corner_btns[prefs.corner].setChecked(True)
        self._spin_d1.setValue(prefs.d1_mm)
        self._spin_d2.setValue(prefs.d2_mm)
        self._spin_size.setValue(int(prefs.font_size_pt))
        self._btn_bold.setChecked(prefs.font_bold)
        self._btn_italic.setChecked(prefs.font_italic)
        for btn in self._color_group.buttons():
            if btn.property("color_hex") == prefs.color_hex:
                btn.setChecked(True)
                break
        self._edit_suffix.setText(prefs.suffix_file)
        self._update_examples()

    def get_config(self, files: list[Path]) -> BatchConfig:
        prefs = self.get_preferences()
        return BatchConfig(
            files=files,
            mode=prefs.mode,
            order=prefs.order,
            start=prefs.start,
            prefix=prefs.prefix,
            suffix_file=prefs.suffix_file,
            stamp=StampParams(
                corner=prefs.corner,
                d1_mm=prefs.d1_mm,
                d2_mm=prefs.d2_mm,
                font_name=prefs.font_name,
                font_size_pt=prefs.font_size_pt,
                font_bold=prefs.font_bold,
                font_italic=prefs.font_italic,
                color_hex=prefs.color_hex,
            ),
        )
