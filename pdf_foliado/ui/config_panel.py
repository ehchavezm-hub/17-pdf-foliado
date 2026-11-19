"""Right pane — all stamping controls."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QButtonGroup, QSpinBox, QDoubleSpinBox,
    QLineEdit, QComboBox, QScrollArea, QFrame, QApplication,
)

from pdf_foliado.config.preferences import Preferences
from pdf_foliado.engine.batch import BatchConfig
from pdf_foliado.engine.stamper import StampParams
from pdf_foliado.ui._theme import PALETTE_TOKENS, build_stylesheet

_FONTS = [
    "Figtree", "Urbanist", "Jost", "Manrope", "Montserrat",
    "Plus Jakarta Sans", "IBM Plex Sans", "Epilogue", "Syne",
    "Tenor Sans", "Roboto", "Arial", "Calibri",
]


class _ToggleButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setObjectName("secondary")


class ConfigPanel(QWidget):
    config_changed = Signal()
    skin_changed = Signal(str)   # emitted when user picks a skin

    def __init__(self, parent=None):
        super().__init__(parent)
        self._skin = "rojo"
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

        # --- Skin ---
        lay.addWidget(self._section("Diseño de color"))
        skin_row = QHBoxLayout()
        self._skin_group = QButtonGroup(self)
        self._skin_group.setExclusive(True)
        self._skin_btns: dict[str, QPushButton] = {}
        for skin_name in ("rojo", "azul", "bosque"):
            t = PALETTE_TOKENS[skin_name]
            btn = QPushButton("●")
            btn.setCheckable(True)
            btn.setFixedSize(28, 28)
            btn.setProperty("skin_name", skin_name)
            btn.setStyleSheet(
                f"QPushButton{{background:{t['accent']};border-radius:14px;"
                f"color:white;font-size:12px;padding:0;border:2px solid transparent;}}"
                f"QPushButton:checked{{border:2px solid #231F20;}}"
                f"QPushButton:hover{{background:{t['accent_h']};}}"
            )
            btn.toggled.connect(self._on_skin_toggled)
            self._skin_group.addButton(btn)
            self._skin_btns[skin_name] = btn
            skin_row.addWidget(btn)
            if skin_name == "rojo":
                btn.setChecked(True)
        skin_row.addStretch()
        lay.addLayout(skin_row)

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
        self._mode_example = QLabel("Cada PDF se folia desde 1")
        self._mode_example.setStyleSheet("color: #757575; font-size: 11px;")
        lay.addWidget(self._mode_example)
        self._mode_group.idToggled.connect(self._on_mode_toggled)

        # --- Orden ---
        lay.addWidget(self._section("Orden de folios"))
        self._order_group = QButtonGroup(self)
        self._order_group.setExclusive(True)
        order_row = QHBoxLayout()
        self._btn_asc = _ToggleButton("0001 → N")
        self._btn_desc = _ToggleButton("N → 0001")
        self._btn_asc.setChecked(True)
        self._order_group.addButton(self._btn_asc, 0)
        self._order_group.addButton(self._btn_desc, 1)
        order_row.addWidget(self._btn_asc)
        order_row.addWidget(self._btn_desc)
        order_row.addStretch()
        lay.addLayout(order_row)

        # --- Iniciar / Prefijo ---
        form1 = QFormLayout()
        self._spin_start = QSpinBox()
        self._spin_start.setRange(1, 9999)
        self._spin_start.setValue(1)
        form1.addRow("Iniciar desde:", self._spin_start)
        self._edit_prefix = QLineEdit()
        self._edit_prefix.setPlaceholderText("ej. Folio ")
        self._edit_prefix.setMaxLength(50)
        form1.addRow("Prefijo:", self._edit_prefix)
        lay.addLayout(form1)

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
        self._spin_d1 = QDoubleSpinBox()
        self._spin_d1.setRange(1.0, 50.0)
        self._spin_d1.setValue(10.0)
        self._spin_d1.setSuffix(" mm")
        form2.addRow("Distancia borde (d1):", self._spin_d1)
        self._spin_d2 = QDoubleSpinBox()
        self._spin_d2.setRange(1.0, 50.0)
        self._spin_d2.setValue(15.0)
        self._spin_d2.setSuffix(" mm")
        form2.addRow("Distancia lateral (d2):", self._spin_d2)
        lay.addLayout(form2)

        # --- Tipografía ---
        lay.addWidget(self._section("Tipografía"))
        form3 = QFormLayout()
        self._combo_font = QComboBox()
        self._combo_font.addItems(_FONTS)
        self._combo_font.setCurrentText("Roboto")
        form3.addRow("Fuente:", self._combo_font)
        self._combo_size = QComboBox()
        self._combo_size.addItems(["10", "12", "14", "16", "18", "20", "22", "24", "26", "28", "30"])
        self._combo_size.setCurrentText("12")
        form3.addRow("Tamaño:", self._combo_size)
        lay.addLayout(form3)

        style_row = QHBoxLayout()
        from PySide6.QtGui import QFont
        self._btn_bold = _ToggleButton("N")  # Negrita
        self._btn_bold.setFixedSize(44, 30)
        bold_font = self._btn_bold.font()
        bold_font.setBold(True)
        bold_font.setPointSize(13)
        self._btn_bold.setFont(bold_font)
        self._btn_italic = _ToggleButton("I")
        self._btn_italic.setFixedSize(44, 30)
        italic_font = self._btn_italic.font()
        italic_font.setItalic(True)
        italic_font.setPointSize(13)
        self._btn_italic.setFont(italic_font)
        style_row.addWidget(self._btn_bold)
        style_row.addWidget(self._btn_italic)
        style_row.addStretch()
        lay.addLayout(style_row)

        # Folio color
        self._color_group = QButtonGroup(self)
        self._color_group.setExclusive(True)
        color_row = QHBoxLayout()
        for label, hex_val in [("Negro", "#231F20"), ("Blanco", "#FFFFFF"), ("Rojo", "#E4002B"), ("Azul", "#005EB8"), ("Verde", "#1B7A4A")]:
            btn = _ToggleButton(label)
            btn.setProperty("color_hex", hex_val)
            self._color_group.addButton(btn)
            color_row.addWidget(btn)
            if label == "Negro":
                btn.setChecked(True)
        color_row.addStretch()
        lay.addLayout(color_row)

        # --- Sufijo ---
        form4 = QFormLayout()
        self._edit_suffix = QLineEdit("_fol")
        form4.addRow("Sufijo archivo:", self._edit_suffix)
        lay.addLayout(form4)

        lay.addStretch()

        # Connect all controls so preview refreshes on every change
        self._corner_group.buttonClicked.connect(lambda _: self.config_changed.emit())
        self._order_group.buttonClicked.connect(lambda _: self.config_changed.emit())
        self._color_group.buttonClicked.connect(lambda _: self.config_changed.emit())
        self._spin_start.valueChanged.connect(lambda _: self.config_changed.emit())
        self._edit_prefix.textChanged.connect(lambda _: self.config_changed.emit())
        self._spin_d1.valueChanged.connect(lambda _: self.config_changed.emit())
        self._spin_d2.valueChanged.connect(lambda _: self.config_changed.emit())
        self._combo_font.currentIndexChanged.connect(lambda _: self.config_changed.emit())
        self._combo_size.currentIndexChanged.connect(lambda _: self.config_changed.emit())
        self._btn_bold.toggled.connect(lambda _: self.config_changed.emit())
        self._btn_italic.toggled.connect(lambda _: self.config_changed.emit())

    # ------------------------------------------------------------------
    @staticmethod
    def _section(title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            "font-weight: 700; font-size: 12px; color: #616161;"
            "border-bottom: 1px solid #E0E0E0; padding-bottom: 2px;"
        )
        return lbl

    def _on_mode_toggled(self, btn_id: int, checked: bool) -> None:
        if not checked:
            return
        if btn_id == 0:
            self._mode_example.setText("Cada PDF se folia desde 1")
        else:
            self._mode_example.setText("Los folios continúan entre PDFs")
        self.config_changed.emit()

    def _on_skin_toggled(self, checked: bool) -> None:
        if not checked:
            return
        btn = self.sender()
        skin = btn.property("skin_name")
        if skin:
            self._skin = skin
            app = QApplication.instance()
            if app:
                app.setStyleSheet(build_stylesheet(skin))
            self.skin_changed.emit(skin)

    # ------------------------------------------------------------------
    def sync_skin(self, skin: str) -> None:
        """Update internal skin state without emitting skin_changed (avoids loops)."""
        self._skin = skin
        btn = self._skin_btns.get(skin)
        if btn and not btn.isChecked():
            btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(False)

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
            font_name=self._combo_font.currentText(),
            font_size_pt=int(self._combo_size.currentText()),
            font_bold=self._btn_bold.isChecked(),
            font_italic=self._btn_italic.isChecked(),
            color_hex=color_hex,
            suffix_file=self._edit_suffix.text(),
            skin=self._skin,
        )

    def set_preferences(self, prefs: Preferences) -> None:
        self.sync_skin(prefs.skin)
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
        idx = self._combo_font.findText(prefs.font_name)
        if idx >= 0:
            self._combo_font.setCurrentIndex(idx)
        idx2 = self._combo_size.findText(str(prefs.font_size_pt))
        if idx2 >= 0:
            self._combo_size.setCurrentIndex(idx2)
        self._btn_bold.setChecked(prefs.font_bold)
        self._btn_italic.setChecked(prefs.font_italic)
        for btn in self._color_group.buttons():
            if btn.property("color_hex") == prefs.color_hex:
                btn.setChecked(True)
                break
        self._edit_suffix.setText(prefs.suffix_file)

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
