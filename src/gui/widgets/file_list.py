"""File list widget using ttk.Treeview for resizable columns, sorting, and tooltips"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Callable, List, Dict

import customtkinter as ctk
from core.file_scanner import FileScanner


def _truncate_path(path_str: str, max_chars: int, show_end: bool = True) -> str:
    if len(path_str) <= max_chars:
        return path_str
    if show_end:
        return "..." + path_str[-(max_chars - 3) :]
    return path_str[: max_chars - 3] + "..."


class FileListWidget(ctk.CTkFrame):
    """File list with resizable columns, sortable headers, path tooltip, and selection."""

    STATUS_PENDING = "Pending"
    STATUS_ENCODING = "Encoding"
    STATUS_COMPLETE = "Complete"
    STATUS_ERROR = "Error"
    STATUS_SKIPPED = "Skipped"

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.scanner = FileScanner()
        self.files: List[Dict] = []
        self.on_file_selected: Optional[Callable] = None
        self._sort_column: Optional[str] = None
        self._sort_reverse = False
        self._path_refresh_after_id: Optional[str] = None

        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=10, pady=10)

        tree_scroll_y = ttk.Scrollbar(tree_container)
        tree_scroll_y.pack(side="right", fill="y")

        self._tree = ttk.Treeview(
            tree_container,
            columns=("path", "size", "tracks", "status"),
            show="tree headings",
            selectmode="extended",
            yscrollcommand=tree_scroll_y.set,
            height=20,
        )
        tree_scroll_y.config(command=self._tree.yview)

        self._tree.heading("#0", text="")
        self._tree.column("#0", width=36, minwidth=30, stretch=False)
        self._tree.heading("path", text="Source Path", command=lambda: self._sort_by("path"))
        self._tree.column("path", width=300, minwidth=80, stretch=True)
        self._tree.heading("size", text="Size", command=lambda: self._sort_by("size"))
        self._tree.column("size", width=100, minwidth=60, stretch=False)
        self._tree.heading("tracks", text="Tracks", command=lambda: self._sort_by("tracks"))
        self._tree.column("tracks", width=100, minwidth=60, stretch=False)
        self._tree.heading("status", text="Status", command=lambda: self._sort_by("status"))
        self._tree.column("status", width=100, minwidth=60, stretch=False)

        self._tree.pack(side="left", fill="both", expand=True)

        self._tooltip = None
        self._tooltip_label = None
        self._tree.bind("<Motion>", self._on_motion)
        self._tree.bind("<Leave>", self._on_leave)
        self._tree.bind("<Button-1>", self._on_click, add=True)
        self._tree.bind("<ButtonRelease-1>", self._on_tree_after_click_or_resize, add=True)
        self._tree.bind("<Configure>", self._on_tree_configure, add=True)

        self._style_tree()

    def _style_tree(self):
        try:
            style = ttk.Style()
            treeview_font = ("TkDefaultFont", 16)
            if ctk.get_appearance_mode() == "Dark":
                style.theme_use("clam")
                style.configure(
                    "Treeview",
                    background="#2b2b2b",
                    foreground="white",
                    fieldbackground="#2b2b2b",
                    font=treeview_font,
                )
                style.configure(
                    "Treeview.Heading",
                    background="#3b3b3b",
                    foreground="white",
                    font=treeview_font,
                )
                style.map("Treeview", background=[("selected", "#1f538d")])
            else:
                style.configure("Treeview", font=treeview_font)
                style.configure("Treeview.Heading", font=treeview_font)
        except Exception:
            pass

    def _on_motion(self, event):
        region = self._tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self._tree.identify_row(event.y)
            col = self._tree.identify_column(event.x)
            if item and col == "#1":
                idx = self._tree.index(item)
                if 0 <= idx < len(self.files):
                    full_path = str(self.files[idx]["path"])
                    self._show_tooltip(event.x_root, event.y_root, full_path)
                    return
        self._hide_tooltip()

    def _on_leave(self, event):
        self._hide_tooltip()

    def _show_tooltip(self, x: int, y: int, text: str):
        self._hide_tooltip()
        self._tooltip = tk.Toplevel(self)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{x + 12}+{y + 12}")
        self._tooltip_label = tk.Label(
            self._tooltip,
            text=text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("TkDefaultFont", 9),
            padx=4,
            pady=2,
        )
        self._tooltip_label.pack()
        self._tooltip.after(5000, self._hide_tooltip)

    def _hide_tooltip(self):
        if self._tooltip:
            try:
                self._tooltip.destroy()
            except Exception:
                pass
            self._tooltip = None
            self._tooltip_label = None

    def _on_click(self, event):
        region = self._tree.identify_region(event.x, event.y)
        if region == "cell":
            col = self._tree.identify_column(event.x)
            if col == "#0":
                item = self._tree.identify_row(event.y)
                if item:
                    idx = self._tree.index(item)
                    if 0 <= idx < len(self.files):
                        self.files[idx]["selected"] = not self.files[idx].get("selected", False)
                        self._refresh_row_display(idx)

    def _path_column_max_chars(self) -> int:
        try:
            width_px = self._tree.column("path", "width") or 300
        except Exception:
            width_px = 300
        char_width_approx = 9
        return max(15, int(width_px) // char_width_approx)

    def _on_tree_after_click_or_resize(self, event):
        self._refresh_all_path_displays()

    def _on_tree_configure(self, event):
        if self._path_refresh_after_id:
            self.after_cancel(self._path_refresh_after_id)
        self._path_refresh_after_id = self.after(50, self._deferred_refresh_paths)

    def _deferred_refresh_paths(self):
        self._path_refresh_after_id = None
        self._refresh_all_path_displays()

    def _refresh_all_path_displays(self):
        for idx in range(len(self.files)):
            self._refresh_row_display(idx)

    def _row_values(self, file_data: Dict) -> tuple:
        path_str = str(file_data["display_path"])
        max_chars = self._path_column_max_chars()
        display_path = _truncate_path(path_str, max_chars, show_end=True)
        sel = "Yes" if file_data.get("selected", False) else ""
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
        return (sel, display_path, size_str, track_str, file_data.get("status", self.STATUS_PENDING))

    def _refresh_row_display(self, index: int):
        if index < 0 or index >= len(self.files):
            return
        file_data = self.files[index]
        iid = str(index)
        if self._tree.exists(iid):
            sel, path_disp, size_str, track_str, status = self._row_values(file_data)
            self._tree.item(iid, values=(path_disp, size_str, track_str, status))
            self._tree.item(iid, text=sel)

    def _sort_by(self, column: str):
        if column not in ("path", "size", "tracks", "status"):
            return
        self._sort_reverse = self._sort_column == column and not self._sort_reverse
        self._sort_column = column
        self._reapply_sort()

    def _reapply_sort(self):
        if not self._sort_column or not self.files:
            return
        key_map = {
            "selected": lambda f: (0 if f.get("selected") else 1),
            "path": lambda f: str(f["display_path"]).lower(),
            "size": lambda f: f.get("size", 0),
            "tracks": lambda f: (
                str(f.get("audio_track", "")),
                str(f.get("subtitle_track", "")),
            ),
            "status": lambda f: f.get("status", "").lower(),
        }
        key_fn = key_map.get(self._sort_column, lambda f: str(f.get("display_path", "")))
        self.files.sort(key=key_fn, reverse=self._sort_reverse)
        self._rebuild_tree()

    def _rebuild_tree(self):
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        for idx, file_data in enumerate(self.files):
            sel, path_disp, size_str, track_str, status = self._row_values(file_data)
            self._tree.insert("", "end", iid=str(idx), text=sel, values=(path_disp, size_str, track_str, status))

    def add_file(self, file_path: Path, relative_to: Optional[Path] = None) -> Dict:
        if relative_to:
            try:
                display_path = file_path.relative_to(relative_to)
            except ValueError:
                display_path = file_path
        else:
            display_path = file_path

        file_size = self.scanner.get_file_size(file_path)
        size_str = self.scanner.format_file_size(file_size)

        file_data = {
            "path": file_path,
            "display_path": display_path,
            "size": file_size,
            "size_str": size_str,
            "audio_track": None,
            "subtitle_track": None,
            "status": self.STATUS_PENDING,
            "output_path": None,
            "output_size": None,
            "selected": False,
        }

        self.files.append(file_data)
        idx = len(self.files) - 1
        sel, path_disp, size_str, track_str, status = self._row_values(file_data)
        self._tree.insert("", "end", iid=str(idx), text=sel, values=(path_disp, size_str, track_str, status))
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
            self._update_file_row(self.files[idx], idx)

    def _update_file_row(self, file_data: Dict, index: int):
        self._refresh_row_display(index)

    def remove_file(self, index: int):
        if 0 <= index < len(self.files):
            self.files.pop(index)
            self._rebuild_tree()

    def clear(self):
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        self.files.clear()

    def get_files(self) -> List[Dict]:
        return self.files

    def get_file_count(self) -> int:
        return len(self.files)

    def get_selected_indices(self) -> List[int]:
        return [i for i, fd in enumerate(self.files) if fd.get("selected", False)]

    def remove_selected_files(self) -> int:
        selected_indices = self.get_selected_indices()
        if not selected_indices:
            return 0
        for index in sorted(selected_indices, reverse=True):
            self.remove_file(index)
        return len(selected_indices)

    def select_all(self):
        for file_data in self.files:
            file_data["selected"] = True
        for idx in range(len(self.files)):
            self._refresh_row_display(idx)

    def deselect_all(self):
        for file_data in self.files:
            file_data["selected"] = False
        for idx in range(len(self.files)):
            self._refresh_row_display(idx)
