import pytest


def test_config_panel_defaults(qtbot):
    from pdf_foliado.ui.config_panel import ConfigPanel
    panel = ConfigPanel()
    qtbot.addWidget(panel)
    cfg = panel.get_preferences()
    assert cfg.mode in ("por_documento", "correlativo")
    assert 1 <= cfg.start <= 9999


def test_config_panel_set_preferences(qtbot):
    from pdf_foliado.ui.config_panel import ConfigPanel
    from pdf_foliado.config.preferences import Preferences
    panel = ConfigPanel()
    qtbot.addWidget(panel)
    prefs = Preferences(mode="correlativo", start=5, corner="TL",
                        skin="azul", order="desc")
    panel.set_preferences(prefs)
    out = panel.get_preferences()
    assert out.mode == "correlativo"
    assert out.start == 5
    assert out.corner == "TL"
    assert out.order == "desc"


def test_get_config_returns_batch_config(qtbot, pdf_1p):
    from pdf_foliado.ui.config_panel import ConfigPanel
    from pathlib import Path
    panel = ConfigPanel()
    qtbot.addWidget(panel)
    cfg = panel.get_config(files=[pdf_1p])
    assert cfg.mode in ("por_documento", "correlativo")
    assert len(cfg.files) == 1
