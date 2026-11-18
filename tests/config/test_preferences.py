import pytest
from pdf_foliado.config.preferences import Preferences, load, save


def test_roundtrip(tmp_path):
    p = Preferences(mode="correlativo", start=5, prefix="Folio ", corner="TL",
                    d1_mm=8.0, d2_mm=12.0, font_name="Figtree", font_size_pt=10,
                    color_hex="#E4002B", suffix_file="_num", order="desc", skin="azul")
    save(p, tmp_path)
    loaded = load(tmp_path)
    assert loaded == p


def test_missing_file_returns_defaults(tmp_path):
    p = load(tmp_path / "nonexistent")
    assert p.mode == "por_documento"
    assert p.start == 1


def test_corrupt_file_returns_defaults(tmp_path):
    datos = tmp_path / "datos"
    datos.mkdir()
    (datos / "preferencias.json").write_text("{invalid json}")
    p = load(tmp_path)
    assert p.mode == "por_documento"


def test_defaults_all_fields():
    p = Preferences()
    assert p.mode == "por_documento"
    assert p.order == "asc"
    assert p.start == 1
    assert p.prefix == ""
    assert p.corner == "BR"
    assert p.d1_mm == 10.0
    assert p.d2_mm == 15.0
    assert p.font_name == "Roboto"
    assert p.font_size_pt == 12
    assert p.color_hex == "#231F20"
    assert p.suffix_file == "_fol"
    assert p.skin == "rojo"
