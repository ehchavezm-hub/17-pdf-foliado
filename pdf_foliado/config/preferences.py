"""User preferences — persisted as JSON in datos/preferencias.json."""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Preferences:
    mode: str = "por_documento"       # "por_documento" | "correlativo"
    order: str = "asc"                # "asc" | "desc"
    start: int = 1
    prefix: str = ""
    corner: str = "BR"                # "TL" | "TR" | "BL" | "BR"
    d1_mm: float = 10.0
    d2_mm: float = 15.0
    font_name: str = "Roboto"
    font_size_pt: int = 12
    color_hex: str = "#231F20"
    suffix_file: str = "_fol"
    skin: str = "rojo"                # "rojo" | "azul" | "bosque"


def save(prefs: Preferences, base_dir: Path) -> None:
    datos = base_dir / "datos"
    datos.mkdir(parents=True, exist_ok=True)
    (datos / "preferencias.json").write_text(
        json.dumps(asdict(prefs), indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load(base_dir: Path) -> Preferences:
    path = base_dir / "datos" / "preferencias.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Preferences(**{k: v for k, v in data.items()
                               if k in Preferences.__dataclass_fields__})
    except Exception:
        return Preferences()
