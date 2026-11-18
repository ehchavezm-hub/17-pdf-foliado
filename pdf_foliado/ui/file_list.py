"""Left pane — drag-reorderable file list."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QAbstractItemView, QListWidgetItem


class FileListWidget(QListWidget):
    files_changed = Signal(list)   # list[Path]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)

    def add_files(self, paths: list[Path]) -> None:
        existing = {Path(self.item(i).data(0x0100)) for i in range(self.count())}
        added = False
        for p in paths:
            p = Path(p)
            if p not in existing:
                item = QListWidgetItem(p.name)
                item.setData(0x0100, str(p))
                item.setToolTip(str(p))
                self.addItem(item)
                existing.add(p)
                added = True
        if added:
            self.files_changed.emit(self.get_ordered_files())

    def remove_selected(self) -> None:
        for item in self.selectedItems():
            self.takeItem(self.row(item))
        self.files_changed.emit(self.get_ordered_files())

    def clear_all(self) -> None:
        self.clear()
        self.files_changed.emit([])

    def get_ordered_files(self) -> list[Path]:
        return [Path(self.item(i).data(0x0100)) for i in range(self.count())]
