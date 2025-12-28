"""File list widget"""

import customtkinter as ctk
from pathlib import Path
from typing import Optional, Callable, List, Dict
from core.file_scanner import FileScanner


class FileListWidget(ctk.CTkFrame):
    """File list widget with status, track info, and file size"""
    
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
        
        # Create treeview-like structure using CTkScrollableFrame
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ctk.CTkFrame(self.scrollable_frame)
        header_frame.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(header_frame, text="", width=30, anchor="w").pack(side="left", padx=5)  # Checkbox column
        ctk.CTkLabel(header_frame, text="Source Path", width=300, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Size", width=100, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Tracks", width=100, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Status", width=100, anchor="w").pack(side="left", padx=5)
        
        self.file_frames: List[ctk.CTkFrame] = []
    
    def add_file(self, file_path: Path, relative_to: Optional[Path] = None) -> Dict:
        """Add a file to the list"""
        # Calculate relative path if needed
        if relative_to:
            try:
                display_path = file_path.relative_to(relative_to)
            except ValueError:
                display_path = file_path
        else:
            display_path = file_path
        
        # Get file size
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
            "selected": False
        }
        
        self.files.append(file_data)
        self._add_file_row(file_data, len(self.files) - 1)
        return file_data
    
    def _add_file_row(self, file_data: Dict, index: int):
        """Add a file row to the display"""
        row_frame = ctk.CTkFrame(self.scrollable_frame)
        row_frame.pack(fill="x", pady=2)
        
        # Checkbox for selection
        checkbox_var = ctk.BooleanVar(value=file_data.get("selected", False))
        # Use a lambda with default argument to properly capture the index
        checkbox = ctk.CTkCheckBox(
            row_frame,
            text="",
            variable=checkbox_var,
            width=30,
            command=lambda idx=index, var=checkbox_var: self._on_checkbox_toggle(idx, var)
        )
        checkbox.pack(side="left", padx=5)
        
        # Source path
        path_label = ctk.CTkLabel(
            row_frame,
            text=str(file_data["display_path"]),
            width=300,
            anchor="w"
        )
        path_label.pack(side="left", padx=5)
        
        # File size
        size_label = ctk.CTkLabel(
            row_frame,
            text=file_data["size_str"],
            width=100,
            anchor="w"
        )
        size_label.pack(side="left", padx=5)
        
        # Track info
        track_str = ""
        if file_data["audio_track"]:
            track_str += f"Audio: {file_data['audio_track']}"
        if file_data["subtitle_track"]:
            if track_str:
                track_str += ", "
            track_str += f"Sub: {file_data['subtitle_track']}"
        if not track_str:
            track_str = "Not analyzed"
        
        track_label = ctk.CTkLabel(
            row_frame,
            text=track_str,
            width=100,
            anchor="w"
        )
        track_label.pack(side="left", padx=5)
        
        # Status
        status_label = ctk.CTkLabel(
            row_frame,
            text=file_data["status"],
            width=100,
            anchor="w"
        )
        status_label.pack(side="left", padx=5)
        
        # Store references
        file_data["_row_frame"] = row_frame
        file_data["_checkbox"] = checkbox
        file_data["_checkbox_var"] = checkbox_var
        file_data["_path_label"] = path_label
        file_data["_size_label"] = size_label
        file_data["_track_label"] = track_label
        file_data["_status_label"] = status_label
        
        self.file_frames.append(row_frame)
    
    def _on_checkbox_toggle(self, index: int, checkbox_var: ctk.BooleanVar):
        """Handle checkbox toggle"""
        if 0 <= index < len(self.files):
            self.files[index]["selected"] = checkbox_var.get()
    
    def update_file(self, index: int, **kwargs):
        """Update file data"""
        if 0 <= index < len(self.files):
            file_data = self.files[index]
            file_data.update(kwargs)
            self._update_file_row(file_data)
    
    def _update_file_row(self, file_data: Dict):
        """Update file row display"""
        # Update track info
        track_str = ""
        if file_data["audio_track"]:
            track_str += f"Audio: {file_data['audio_track']}"
        if file_data["subtitle_track"]:
            if track_str:
                track_str += ", "
            track_str += f"Sub: {file_data['subtitle_track']}"
        if not track_str:
            track_str = "Not analyzed"
        
        if "_track_label" in file_data:
            file_data["_track_label"].configure(text=track_str)
        
        # Update status
        if "_status_label" in file_data:
            file_data["_status_label"].configure(text=file_data["status"])
            
            # Color code status
            status = file_data["status"]
            if status == self.STATUS_COMPLETE:
                file_data["_status_label"].configure(text_color="green")
            elif status == self.STATUS_ERROR:
                file_data["_status_label"].configure(text_color="red")
            elif status == self.STATUS_ENCODING:
                file_data["_status_label"].configure(text_color="blue")
            elif status == self.STATUS_SKIPPED:
                file_data["_status_label"].configure(text_color="yellow")
            else:
                file_data["_status_label"].configure(text_color="white")
        
        # Update size if output exists
        if file_data.get("output_size") is not None:
            size_str = f"{file_data['size_str']} → {self.scanner.format_file_size(file_data['output_size'])}"
            if "_size_label" in file_data:
                file_data["_size_label"].configure(text=size_str)
    
    def remove_file(self, index: int):
        """Remove a file from the list"""
        if 0 <= index < len(self.files):
            file_data = self.files[index]
            if "_row_frame" in file_data:
                file_data["_row_frame"].destroy()
            self.files.pop(index)
            self.file_frames.pop(index)
            # Rebuild indices for remaining checkboxes
            self._rebuild_checkbox_commands()
    
    def _rebuild_checkbox_commands(self):
        """Rebuild checkbox commands after files are removed"""
        for index, file_data in enumerate(self.files):
            if "_checkbox" in file_data and "_checkbox_var" in file_data:
                # Capture index and var in lambda default arguments to avoid closure issues
                checkbox_var = file_data["_checkbox_var"]
                file_data["_checkbox"].configure(
                    command=lambda idx=index, var=checkbox_var: self._on_checkbox_toggle(idx, var)
                )
    
    def clear(self):
        """Clear all files"""
        for file_data in self.files:
            if "_row_frame" in file_data:
                file_data["_row_frame"].destroy()
        self.files.clear()
        self.file_frames.clear()
    
    def get_files(self) -> List[Dict]:
        """Get all files"""
        return self.files
    
    def get_file_count(self) -> int:
        """Get number of files"""
        return len(self.files)
    
    def get_selected_indices(self) -> List[int]:
        """Get indices of selected files"""
        return [i for i, file_data in enumerate(self.files) if file_data.get("selected", False)]
    
    def remove_selected_files(self) -> int:
        """Remove all selected files from the list. Returns number of files removed."""
        selected_indices = self.get_selected_indices()
        if not selected_indices:
            return 0
        
        # Remove in reverse order to preserve indices
        for index in sorted(selected_indices, reverse=True):
            self.remove_file(index)
        
        return len(selected_indices)
    
    def select_all(self):
        """Select all files"""
        for file_data in self.files:
            file_data["selected"] = True
            if "_checkbox_var" in file_data:
                file_data["_checkbox_var"].set(True)
    
    def deselect_all(self):
        """Deselect all files"""
        for file_data in self.files:
            file_data["selected"] = False
            if "_checkbox_var" in file_data:
                file_data["_checkbox_var"].set(False)

