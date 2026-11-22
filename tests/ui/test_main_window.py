import pytest
from pathlib import Path


def test_main_window_opens(qtbot):
    from pdf_foliado.ui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    assert win.isVisible()


def test_file_list_add_files(qtbot, pdf_1p, pdf_5p):
    from pdf_foliado.ui.file_list import FileListWidget
    widget = FileListWidget()
    qtbot.addWidget(widget)
    widget.add_files([pdf_1p, pdf_5p])
    assert len(widget.get_ordered_files()) == 2


def test_file_list_remove_selected(qtbot, pdf_1p, pdf_5p):
    from pdf_foliado.ui.file_list import FileListWidget
    widget = FileListWidget()
    qtbot.addWidget(widget)
    widget.add_files([pdf_1p, pdf_5p])
    widget.setCurrentRow(0)
    widget.remove_selected()
    assert len(widget.get_ordered_files()) == 1


def test_file_list_clear_all(qtbot, pdf_1p, pdf_5p):
    from pdf_foliado.ui.file_list import FileListWidget
    widget = FileListWidget()
    qtbot.addWidget(widget)
    widget.add_files([pdf_1p, pdf_5p])
    widget.clear_all()
    assert len(widget.get_ordered_files()) == 0


def test_preview_folio_follows_mode_and_order(qtbot, pdf_1p, pdf_5p):
    from pdf_foliado.ui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    win._file_list.add_files([pdf_5p, pdf_1p])
    # por documento: each file restarts at 0001
    assert win._folio_for(pdf_1p, 0) == "0001"
    # correlativo: second file continues after the 5 pages of the first
    win._config_panel._btn_correlativo.setChecked(True)
    assert win._folio_for(pdf_1p, 0) == "0006"
    # descending order: first page of a 5-page file gets the highest folio
    win._config_panel._btn_desc.setChecked(True)
    assert win._folio_for(pdf_5p, 0) == "0005"


def test_foliar_button_reflects_checked_files(qtbot, pdf_1p, pdf_5p):
    from pdf_foliado.ui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    assert not win._btn_foliar.isEnabled()
    win._file_list.add_files([pdf_1p, pdf_5p])
    assert win._btn_foliar.isEnabled()
    assert win._btn_foliar.text() == "Foliar 2 archivos"
    win._folio_card.set_checked(False)
    win._sello_card.set_checked(False)
    assert not win._btn_foliar.isEnabled()


def test_preview_page_navigation(qtbot, pdf_5p):
    from pdf_foliado.ui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    win._file_list.add_files([pdf_5p])
    win._step_page(2)
    assert win._preview.current_source() == (pdf_5p, 2)
    win._step_page(10)  # clamps to the last page
    assert win._preview.current_source() == (pdf_5p, 4)
