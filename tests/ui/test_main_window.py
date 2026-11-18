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
