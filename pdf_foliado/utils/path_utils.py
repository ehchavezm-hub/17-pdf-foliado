"""Path helpers — 260-char limit, atomic overwrite avoidance."""
from __future__ import annotations
from pathlib import Path

_MAX_PATH = 259  # Windows limit minus 1 for safety


def safe_output_path(input_path: Path, suffix: str) -> Path:
    """Return a safe output Path: suffix applied, 260-char checked, no overwrite."""
    stem = input_path.stem
    candidate = input_path.parent / f"{stem}{suffix}.pdf"

    if len(str(candidate)) > _MAX_PATH:
        fallback_dir = Path.home() / "Documents" / "pdf-foliado"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        candidate = fallback_dir / f"{stem}{suffix}.pdf"

    # Avoid overwriting existing file
    if not candidate.exists():
        return candidate

    counter = 1
    while True:
        name = f"{stem}{suffix} ({counter}).pdf"
        alt = candidate.parent / name
        if not alt.exists():
            return alt
        counter += 1
