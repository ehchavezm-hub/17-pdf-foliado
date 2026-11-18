"""Single source of truth for colour tokens and QSS stylesheet."""
from __future__ import annotations

PALETTE_TOKENS: dict[str, dict[str, str]] = {
    "rojo":   {"accent": "#E4002B", "accent_h": "#b80022", "accent_bg": "#fff0f2"},
    "azul":   {"accent": "#005EB8", "accent_h": "#004a92", "accent_bg": "#f0f4ff"},
    "bosque": {"accent": "#1B7A4A", "accent_h": "#155f39", "accent_bg": "#f0fff6"},
}


def build_stylesheet(skin: str) -> str:
    t = PALETTE_TOKENS.get(skin, PALETTE_TOKENS["rojo"])
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
