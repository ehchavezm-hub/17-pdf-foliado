from pathlib import Path
from pdf_foliado.utils.path_utils import safe_output_path


def test_basic_suffix(tmp_path):
    src = tmp_path / "doc.pdf"
    src.touch()
    out = safe_output_path(src, "_fol")
    assert out.name == "doc_fol.pdf"
    assert out.parent == tmp_path


def test_avoids_overwrite(tmp_path):
    src = tmp_path / "doc.pdf"
    src.touch()
    (tmp_path / "doc_fol.pdf").touch()
    out = safe_output_path(src, "_fol")
    assert out.name == "doc_fol (1).pdf"


def test_avoids_overwrite_multiple(tmp_path):
    src = tmp_path / "doc.pdf"
    src.touch()
    (tmp_path / "doc_fol.pdf").touch()
    (tmp_path / "doc_fol (1).pdf").touch()
    out = safe_output_path(src, "_fol")
    assert out.name == "doc_fol (2).pdf"


def test_long_path_fallback(tmp_path, monkeypatch):
    # Simulate a path that would exceed 260 chars
    long_name = "a" * 240
    src = tmp_path / f"{long_name}.pdf"
    src.touch()
    # monkeypatch home so fallback goes to tmp
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    import pdf_foliado.utils.path_utils as pu
    monkeypatch.setattr(pu.Path, "home", staticmethod(lambda: tmp_path))
    out = safe_output_path(src, "_fol")
    assert len(str(out)) <= 260 or "pdf-foliado" in str(out)


def test_no_source_file_ok(tmp_path):
    # source doesn't have to exist for path calculation
    src = tmp_path / "new.pdf"
    out = safe_output_path(src, "_fol")
    assert out.name == "new_fol.pdf"
