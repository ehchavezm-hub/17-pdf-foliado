"""Left pane — drag-reorderable file list with external drop support."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QListWidget, QAbstractItemView, QListWidgetItem


class FileListWidget(QListWidget):
    files_changed = Signal(list)   # list[Path]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if event.mimeData().hasUrls():
            paths = [
                Path(u.toLocalFile())
                for u in event.mimeData().urls()
                if u.isLocalFile() and u.toLocalFile().lower().endswith(".pdf")
            ]
            if paths:
                self.add_files(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

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

    def mark_done(self, path: str) -> None:
        """Mark an item as folioed with a green checkmark."""
        name = Path(path).name
        for i in range(self.count()):
            item = self.item(i)
            if item.data(0x0100) == path or item.text().lstrip("✓ ") == name:
                item.setText(f"✓ {name}")
                item.setForeground(__import__('PySide6.QtGui', fromlist=['QColor']).QColor("#1B7A4A"))
                break

    def reset_marks(self) -> None:
        """Remove done marks (called before a new batch)."""
        for i in range(self.count()):
            item = self.item(i)
            text = item.text().lstrip("✓ ")
            item.setText(text)
            item.setForeground(__import__('PySide6.QtGui', fromlist=['QColor']).QColor("#231F20"))

    def remove_selected(self) -> None:
        for item in self.selectedItems():
            self.takeItem(self.row(item))
        self.files_changed.emit(self.get_ordered_files())

    def clear_all(self) -> None:
        self.clear()
        self.files_changed.emit([])

    def get_ordered_files(self) -> list[Path]:
        return [Path(self.item(i).data(0x0100)) for i in range(self.count())]
