"""File-level validation before stamping."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

import pikepdf

from pdf_foliado.utils.pdf_info import get_pdf_info, PdfInfo


@dataclass
class ValidationResult:
    ok: bool = True
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


def validate_file(path: Path, password: str | None = None) -> ValidationResult:
    """Validate a PDF file. Returns ValidationResult with ok/error/warnings."""
    result = ValidationResult()

    info = get_pdf_info(path, password=password)

    if info.is_encrypted:
        if password is None:
            result.ok = False
            result.error = "El PDF requiere contraseña. Proporciona la contraseña para continuar."
            return result
        # Password was provided but still encrypted means it was wrong
        # get_pdf_info returns is_encrypted=True if PasswordError was raised
        result.ok = False
        result.error = "Contraseña incorrecta para este PDF."
        return result

    if info.page_count == 0:
        result.ok = False
        result.error = "El PDF tiene 0 páginas y no puede foliarse."
        return result

    if info.has_signature:
        result.warnings.append(
            "Este PDF contiene una firma digital. Al foliarlo se generará una "
            "copia con la firma invalidada. El archivo original no se modifica."
        )

    if info.is_pdfa:
        result.warnings.append(
            "Este PDF cumple el estándar PDF/A. Al estamparlo puede dejar de "
            "cumplirlo. El archivo original no se modifica."
        )

    return result
