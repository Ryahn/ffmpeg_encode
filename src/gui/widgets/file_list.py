"""File list: QTableWidget with sortable columns, checkboxes, path tooltips."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem, QWidget

from core.file_scanner import FileScanner


def _truncate_path(path_str: str, max_chars: int, show_end: bool = True) -> str:
    if len(path_str) <= max_chars:
        return path_str
    if show_end:
        return "..." + path_str[-(max_chars - 3) :]
    return path_str[: max_chars - 3] + "..."


class FileListWidget(QWidget):
    STATUS_PENDING = "Pending"
    STATUS_ENCODING = "Encoding"
    STATUS_COMPLETE = "Complete"
    STATUS_ERROR = "Error"
    STATUS_SKIPPED = "Skipped"

    COL_SEL = 0
    COL_PATH = 1
    COL_SIZE = 2
    COL_TRACKS = 3
    COL_STATUS = 4

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.scanner = FileScanner()
        self.files: List[Dict] = []
        self.on_file_selected: Optional[Callable] = None
        self._sort_column: Optional[int] = None
        self._sort_reverse = False
        self._refresh_timer: Optional[QTimer] = None

        self._table = QTableWidget(0, 5, self)
        self._table.setHorizontalHeaderLabels(["", "Source Path", "Size", "Tracks", "Status"])
        self._table.horizontalHeader().setSectionResizeMode(self.COL_PATH, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(self.COL_SEL, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(self.COL_SEL, 36)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(True)
        self._table.itemChanged.connect(self._on_item_changed)
        self._table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)

        from PyQt6.QtWidgets import QVBoxLayout

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._table)

    def _path_column_max_chars(self) -> int:
        w = self._table.columnWidth(self.COL_PATH)
        return max(15, w // 8)

    def _row_values(self, file_data: Dict) -> tuple:
        path_str = str(file_data["display_path"])
        max_chars = self._path_column_max_chars()
        display_path = _truncate_path(path_str, max_chars, show_end=True)
        track_str = ""
        if file_data.get("audio_track"):
            track_str += f"Audio: {file_data['audio_track']}"
        if file_data.get("subtitle_track") is not None:
            if track_str:
                track_str += ", "
            track_str += f"Sub: {file_data['subtitle_track']}"
        if not track_str:
            track_str = "Not analyzed"
        size_str = file_data.get("size_str", "")
        if file_data.get("output_size") is not None:
            size_str = f"{size_str} → {self.scanner.format_file_size(file_data['output_size'])}"
        status = file_data.get("status", self.STATUS_PENDING)
        if file_data.get("reencode"):
            status = f"{status} (re-encode)"
        return display_path, size_str, track_str, status, path_str

    def _set_row(self, row: int, file_data: Dict) -> None:
        display_path, size_str, track_str, status, full_path = self._row_values(file_data)
        self._table.blockSignals(True)
        chk = QTableWidgetItem()
        chk.setFlags(
            Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )
        chk.setCheckState(
            Qt.CheckState.Checked if file_data.get("selected") else Qt.CheckState.Unchecked
        )
        self._table.setItem(row, self.COL_SEL, chk)

        it_path = QTableWidgetItem(display_path)
        it_path.setToolTip(full_path)
        it_path.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(row, self.COL_PATH, it_path)

        it_size = QTableWidgetItem(size_str)
        it_size.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(row, self.COL_SIZE, it_size)

        it_tr = QTableWidgetItem(track_str)
        it_tr.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(row, self.COL_TRACKS, it_tr)

        it_st = QTableWidgetItem(status)
        it_st.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(row, self.COL_STATUS, it_st)
        self._table.blockSignals(False)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != self.COL_SEL:
            return
        row = item.row()
        if row < 0 or row >= len(self.files):
            return
        self.files[row]["selected"] = item.checkState() == Qt.CheckState.Checked

    def _on_header_clicked(self, logical_index: int) -> None:
        if logical_index == self.COL_SEL:
            return
        self._sort_reverse = self._sort_column == logical_index and not self._sort_reverse
        self._sort_column = logical_index
        self._reapply_sort()

    def _reapply_sort(self) -> None:
        if self._sort_column is None or not self.files:
            return

        def key_row(i: int):
            f = self.files[i]
            c = self._sort_column
            if c == self.COL_PATH:
                return str(f["display_path"]).lower()
            if c == self.COL_SIZE:
                return f.get("size", 0)
            if c == self.COL_TRACKS:
                return (str(f.get("audio_track", "")), str(f.get("subtitle_track", "")))
            if c == self.COL_STATUS:
                return f.get("status", "").lower()
            return i

        order = list(range(len(self.files)))
        order.sort(key=key_row, reverse=self._sort_reverse)
        new_files = [self.files[i] for i in order]
        self.files = new_files
        self._rebuild_table()

    def _rebuild_table(self) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(len(self.files))
        for idx, fd in enumerate(self.files):
            self._set_row(idx, fd)
        self._table.blockSignals(False)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._refresh_timer:
            self._refresh_timer.stop()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh_path_cells)
        self._refresh_timer.start(50)

    def _refresh_path_cells(self) -> None:
        for idx, fd in enumerate(self.files):
            display_path, _, _, _, full_path = self._row_values(fd)
            it = self._table.item(idx, self.COL_PATH)
            if it:
                it.setText(display_path)
                it.setToolTip(full_path)

    def add_file(
        self,
        file_path: Path,
        relative_to: Optional[Path] = None,
        root: Optional[Path] = None,
    ) -> Dict:
        if relative_to:
            try:
                display_path = file_path.relative_to(relative_to)
            except ValueError:
                display_path = file_path
        else:
            display_path = file_path
        if root is None:
            root = relative_to if relative_to else file_path.parent
        file_size = self.scanner.get_file_size(file_path)
        size_str = self.scanner.format_file_size(file_size)
        file_data: Dict = {
            "path": file_path,
            "display_path": display_path,
            "root": root,
            "size": file_size,
            "size_str": size_str,
            "audio_track": None,
            "subtitle_track": None,
            "status": self.STATUS_PENDING,
            "output_path": None,
            "output_size": None,
            "selected": False,
            "reencode": False,
            "tracks_from_user": False,
        }
        self.files.append(file_data)
        row = len(self.files) - 1
        self._table.insertRow(row)
        self._set_row(row, file_data)
        return file_data

    def update_file(self, index: int, **kwargs):
        path = kwargs.get("path")
        idx = index
        if path is not None:
            for i, fd in enumerate(self.files):
                if fd.get("path") == path:
                    idx = i
                    break
        if 0 <= idx < len(self.files):
            self.files[idx].update(kwargs)
            self._set_row(idx, self.files[idx])

    def remove_file(self, index: int) -> None:
        if 0 <= index < len(self.files):
            self.files.pop(index)
            self._rebuild_table()

    def clear(self) -> None:
        self.files.clear()
        self._table.setRowCount(0)

    def get_files(self) -> List[Dict]:
        return self.files

    def get_file_count(self) -> int:
        return len(self.files)

    def get_selected_indices(self) -> List[int]:
        return [i for i, fd in enumerate(self.files) if fd.get("selected", False)]

    def _selected_row_indices(self) -> List[int]:
        return sorted({idx.row() for idx in self._table.selectedIndexes()})

    def remove_selected_files(self) -> int:
        selected_indices = self._selected_row_indices()
        if not selected_indices:
            selected_indices = self.get_selected_indices()
        if not selected_indices:
            return 0
        for index in sorted(selected_indices, reverse=True):
            self.remove_file(index)
        return len(selected_indices)

    def select_all(self) -> None:
        for fd in self.files:
            fd["selected"] = True
        self._rebuild_table()

    def deselect_all(self) -> None:
        for fd in self.files:
            fd["selected"] = False
        self._rebuild_table()

    def get_action_target_indices(self) -> List[int]:
        indices = self._selected_row_indices()
        if indices:
            return sorted(set(indices))
        return sorted(self.get_selected_indices())

    def set_reencode_for_indices(self, indices: List[int], value: bool) -> int:
        count = 0
        for idx in indices:
            if 0 <= idx < len(self.files):
                self.files[idx]["reencode"] = value
                self._set_row(idx, self.files[idx])
                count += 1
        return count
