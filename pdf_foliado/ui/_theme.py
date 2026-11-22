"""Single source of truth for colour tokens and QSS stylesheet."""
from __future__ import annotations

APP_NAME = "PDF Foliado"
APP_VERSION = "0.2.0"

PALETTE_TOKENS: dict[str, dict[str, str]] = {
    "rojo":   {"accent": "#E4002B", "accent_h": "#b80022", "accent_bg": "#fff0f2", "label": "Rojo"},
    "azul":   {"accent": "#005EB8", "accent_h": "#004a92", "accent_bg": "#f0f4ff", "label": "Azul"},
    "bosque": {"accent": "#1B7A4A", "accent_h": "#155f39", "accent_bg": "#f0fff6", "label": "Verde bosque"},
}

# Neutral tokens shared by every skin
INK = "#231F20"
MUTED = "#6B6B6B"
LINE = "#E0E0E0"
SURFACE = "#FAFAFA"
CARD = "#FFFFFF"
OK = "#1B7A4A"
WARN = "#B26A00"
ERROR = "#C62828"


def apply_light_palette(app) -> None:
    """Force a light look even when Windows is in dark mode.

    Without this, Qt follows the OS colour scheme and native dialogs, menus,
    scroll bars and any widget not covered by the stylesheet turn dark.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPalette

    try:  # Qt >= 6.8
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except AttributeError:
        pass
    app.setStyle("Fusion")
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: SURFACE,
        QPalette.ColorRole.WindowText: INK,
        QPalette.ColorRole.Base: CARD,
        QPalette.ColorRole.AlternateBase: "#F7F7F7",
        QPalette.ColorRole.Text: INK,
        QPalette.ColorRole.Button: "#F0F0F0",
        QPalette.ColorRole.ButtonText: INK,
        QPalette.ColorRole.ToolTipBase: INK,
        QPalette.ColorRole.ToolTipText: "#FFFFFF",
        QPalette.ColorRole.PlaceholderText: "#9E9E9E",
        QPalette.ColorRole.Highlight: "#D6E4F5",
        QPalette.ColorRole.HighlightedText: INK,
        QPalette.ColorRole.Light: "#FFFFFF",
        QPalette.ColorRole.Mid: "#BDBDBD",
        QPalette.ColorRole.Dark: "#9E9E9E",
    }
    for role, color in roles.items():
        pal.setColor(role, QColor(color))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#9E9E9E"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#9E9E9E"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#9E9E9E"))
    app.setPalette(pal)


_ARROW_DIR: str | None = None


def _arrow_images() -> tuple[str, str]:
    """Small arrow PNGs for spin boxes / combos.

    Once a QSpinBox frame is styled with QSS, Qt stops drawing its native
    arrows, so we render our own once per process into a temp folder (no
    extra files to ship with the portable/exe builds).
    """
    global _ARROW_DIR
    import tempfile
    from pathlib import Path
    if _ARROW_DIR is None or not Path(_ARROW_DIR, "up.png").exists():
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QColor, QPainter, QPixmap, QPolygonF
        _ARROW_DIR = tempfile.mkdtemp(prefix="pdf_foliado_ui_")
        for name, pts in (("up", [(1, 6), (5, 2), (9, 6)]),
                          ("down", [(1, 2), (5, 6), (9, 2)])):
            pix = QPixmap(10, 8)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#555555"))
            p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))
            p.end()
            pix.save(str(Path(_ARROW_DIR, f"{name}.png")))
    up = (Path(_ARROW_DIR) / "up.png").as_posix()
    down = (Path(_ARROW_DIR) / "down.png").as_posix()
    return up, down


def build_stylesheet(skin: str) -> str:
    t = PALETTE_TOKENS.get(skin, PALETTE_TOKENS["rojo"])
    try:
        up_png, down_png = _arrow_images()
    except Exception:  # never block the UI over an icon
        up_png = down_png = ""
    return f"""
QMainWindow, QDialog, QMessageBox, QInputDialog {{ background-color: {SURFACE}; }}
QWidget {{
    color: {INK};
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 13px;
}}
QToolTip {{
    background-color: {INK};
    color: white;
    border: none;
    padding: 4px 8px;
}}
QPushButton {{
    background-color: {t["accent"]};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: {t["accent_h"]}; }}
QPushButton:focus {{ outline: none; border: 2px solid {t["accent_h"]}; }}
QPushButton:disabled {{ background-color: #BDBDBD; color: #F5F5F5; }}
QPushButton#secondary {{
    background-color: {CARD};
    color: {t["accent"]};
    border: 1px solid {t["accent"]};
}}
QPushButton#secondary:hover {{ background-color: {t["accent_bg"]}; }}
QPushButton#secondary:checked {{
    background-color: {t["accent"]};
    color: white;
    border: 1px solid {t["accent"]};
}}
QPushButton#secondary:checked:hover {{ background-color: {t["accent_h"]}; }}
QPushButton#secondary:disabled {{
    background-color: {SURFACE};
    color: #BDBDBD;
    border: 1px solid {LINE};
}}
QPushButton#ghost {{
    background-color: transparent;
    color: {MUTED};
    border: 1px solid {LINE};
    font-weight: 500;
}}
QPushButton#ghost:hover {{ color: {INK}; background-color: #F0F0F0; }}
QPushButton#ghost:disabled {{ color: #C8C8C8; }}
QPushButton#primary {{
    font-size: 14px;
    padding: 10px 28px;
    border-radius: 6px;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {CARD};
    border: 1px solid #CFCFCF;
    border-radius: 4px;
    padding: 4px 6px;
    min-height: 20px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {t["accent"]};
}}
QSpinBox, QDoubleSpinBox {{ padding-right: 20px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid {LINE};
    border-top-right-radius: 4px;
    background: #F5F5F5;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid {LINE};
    border-top: 1px solid {LINE};
    border-bottom-right-radius: 4px;
    background: #F5F5F5;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {t["accent_bg"]};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{up_png}"); width: 10px; height: 8px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{down_png}"); width: 10px; height: 8px; }}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 20px;
    border: none;
}}
QComboBox::down-arrow {{ image: url("{down_png}"); width: 10px; height: 8px; }}
QComboBox QAbstractItemView {{
    background: {CARD};
    selection-background-color: {t["accent_bg"]};
    selection-color: {INK};
}}
QProgressBar {{
    border: 1px solid {LINE};
    border-radius: 4px;
    background: {CARD};
    height: 10px;
    text-align: center;
    font-size: 11px;
}}
QProgressBar::chunk {{ background-color: {t["accent"]}; border-radius: 3px; }}
QListWidget {{
    border: 1px solid {LINE};
    border-radius: 4px;
    background: {CARD};
    alternate-background-color: #F7F7F7;
    padding: 2px;
}}
QListWidget::item {{ padding: 4px 2px; }}
QListWidget::item:selected {{
    background-color: {t["accent_bg"]};
    color: {INK};
    border-left: 3px solid {t["accent"]};
}}
QLabel#sectionTitle {{
    font-weight: 700;
    font-size: 12px;
    color: #555555;
    border-bottom: 1px solid {LINE};
    padding-bottom: 2px;
    background: transparent;
}}
QLabel#hint {{ color: {MUTED}; font-size: 11px; background: transparent; }}
QLabel#appTitle {{ font-size: 18px; font-weight: 700; }}
QLabel#appVersion {{ color: {MUTED}; font-size: 11px; padding-top: 6px; }}
QLabel#accent {{ color: {t["accent"]}; font-weight: 600; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QWidget#card {{
    background: {CARD};
    border: 1px solid {LINE};
    border-radius: 6px;
}}
QWidget#cardHdr {{
    background: {t["accent_bg"]};
    border: none;
    border-bottom: 1px solid {LINE};
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QWidget#cardHdr[expanded="false"] {{
    border-bottom: none;
    border-bottom-left-radius: 6px;
    border-bottom-right-radius: 6px;
}}
QWidget#cardHdr QCheckBox {{
    color: {INK};
    font-weight: 700;
    font-size: 14px;
    background: transparent;
    spacing: 8px;
}}
QWidget#cardHdr QLabel {{ background: transparent; color: {MUTED}; }}
QWidget#cardHdr QLabel#cardState {{ color: {t["accent"]}; font-weight: 600; font-size: 11px; }}
QWidget#topBar {{ background: transparent; }}
QWidget#bottomBar {{
    background: {CARD};
    border-top: 1px solid {LINE};
}}
QWidget#bottomBar QLabel {{ background: transparent; }}
QSplitter::handle {{ background: transparent; width: 6px; }}
QSplitter::handle:hover {{ background: {LINE}; }}
"""
