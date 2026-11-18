"""Application entry point."""
from __future__ import annotations
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from pdf_foliado.config.preferences import load, save
from pdf_foliado.config.logging_setup import setup_logging
from pdf_foliado.ui.main_window import MainWindow


def run() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("pdf-foliado")
    app.setOrganizationName("pdf-foliado")

    # Base dir: next to the .exe when frozen, repo root when running from source
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent

    setup_logging(base_dir)
    prefs = load(base_dir)

    win = MainWindow(base_dir=base_dir, prefs=prefs)
    win.show()

    code = app.exec()
    save(win.get_preferences(), base_dir)
    sys.exit(code)


if __name__ == "__main__":
    run()
