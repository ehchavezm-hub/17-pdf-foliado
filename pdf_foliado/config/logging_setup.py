"""Rotating log handler — datos/errores.log, max 1 MB, 1 backup."""
from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(base_dir: Path) -> None:
    datos = base_dir / "datos"
    datos.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        datos / "errores.log",
        maxBytes=1 * 1024 * 1024,
        backupCount=1,
        encoding="utf-8",
    )
    handler.setLevel(logging.WARNING)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.WARNING)
