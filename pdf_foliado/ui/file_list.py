"""Left pane — file list with checkboxes, page counts and ↑↓ reorder."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QListWidget, QAbstractItemView, QListWidgetItem

_ROLE_PATH  = 0x0100
_ROLE_PAGES = 0x0101
_ROLE_DONE  = 0x0102


class FileListWidget(QListWidget):
    files_changed   = Signal(list)      # list[Path] — all files in order
    summary_changed = Signal(int, int)  # (checked_count, total_pages)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Accept external drops from Explorer; reordering via ↑↓ buttons only
        # (internal drag would lose custom data roles on Qt's item copy).
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.itemChanged.connect(self._on_item_changed)

    # ------------------------------------------------------------------
    # External drop (Windows Explorer → list)
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

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
            event.ignore()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_files(self, paths: list[Path]) -> None:
        from pdf_foliado.utils.pdf_info import get_pdf_info
        existing = {Path(self.item(i).data(_ROLE_PATH)) for i in range(self.count())}
        added = False
        self.blockSignals(True)
        for p in paths:
            p = Path(p)
            if p not in existing:
                info = get_pdf_info(p)
                item = QListWidgetItem()
                item.setData(_ROLE_PATH, str(p))
                item.setData(_ROLE_PAGES, info.page_count)
                item.setData(_ROLE_DONE, False)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                item.setToolTip(str(p))
                _update_text(item)
                self.addItem(item)
                existing.add(p)
                added = True
        self.blockSignals(False)
        if added:
            self.files_changed.emit(self.get_ordered_files())
            self._emit_summary()

    def move_up(self) -> None:
        row = self.currentRow()
        if row <= 0:
            return
        item = self.takeItem(row)
        self.insertItem(row - 1, item)
        self.setCurrentRow(row - 1)
        self.files_changed.emit(self.get_ordered_files())

    def move_down(self) -> None:
        row = self.currentRow()
        if row < 0 or row >= self.count() - 1:
            return
        item = self.takeItem(row)
        self.insertItem(row + 1, item)
        self.setCurrentRow(row + 1)
        self.files_changed.emit(self.get_ordered_files())

    def mark_done(self, path: str) -> None:
        self.blockSignals(True)
        for i in range(self.count()):
            item = self.item(i)
            if item.data(_ROLE_PATH) == path:
                item.setData(_ROLE_DONE, True)
                _update_text(item)
                item.setForeground(QColor("#1B7A4A"))
                break
        self.blockSignals(False)

    def reset_marks(self) -> None:
        self.blockSignals(True)
        for i in range(self.count()):
            item = self.item(i)
            item.setData(_ROLE_DONE, False)
            _update_text(item)
            item.setForeground(QColor("#231F20"))
        self.blockSignals(False)

    def remove_selected(self) -> None:
        for item in self.selectedItems():
            self.takeItem(self.row(item))
        self.files_changed.emit(self.get_ordered_files())
        self._emit_summary()

    def clear_all(self) -> None:
        self.clear()
        self.files_changed.emit([])
        self._emit_summary()

    def get_ordered_files(self) -> list[Path]:
        """All files in display order (regardless of check state)."""
        return [Path(self.item(i).data(_ROLE_PATH)) for i in range(self.count())]

    def get_checked_files(self) -> list[Path]:
        """Only checked files, in display order."""
        return [
            Path(self.item(i).data(_ROLE_PATH))
            for i in range(self.count())
            if self.item(i).checkState() == Qt.CheckState.Checked
        ]

    def total_checked_pages(self) -> int:
        return sum(
            self.item(i).data(_ROLE_PAGES) or 0
            for i in range(self.count())
            if self.item(i).checkState() == Qt.CheckState.Checked
        )

    # ------------------------------------------------------------------
    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        self._emit_summary()

    def _emit_summary(self) -> None:
        checked = sum(
            1 for i in range(self.count())
            if self.item(i).checkState() == Qt.CheckState.Checked
        )
        self.summary_changed.emit(checked, self.total_checked_pages())


# ------------------------------------------------------------------
def _update_text(item: QListWidgetItem) -> None:
    name   = Path(item.data(_ROLE_PATH)).name
    pages  = item.data(_ROLE_PAGES) or 0
    done   = item.data(_ROLE_DONE) or False
    prefix = "✓ " if done else ""
    pstr   = f"{pages} pág" + ("s" if pages != 1 else "")
    item.setText(f"{prefix}{name}  —  {pstr}")
