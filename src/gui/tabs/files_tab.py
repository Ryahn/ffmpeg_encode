"""Files tab for managing video files"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar
from pathlib import Path
from typing import Optional, Callable
from ..widgets.file_list import FileListWidget
from core.file_scanner import FileScanner
from utils.config import config


class FilesTab(ctk.CTkFrame):
    """Tab for managing files to encode"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.scanner = FileScanner()
        self.scan_folder: Optional[Path] = None
        self.output_folder: Optional[Path] = None
        self.on_files_changed: Optional[Callable] = None
        
        # Top controls: two rows so output section has full width and buttons stay visible
        controls_frame = ctk.CTkFrame(self)
        controls_frame.pack(fill="x", padx=10, pady=10)

        # Row 1: Scan folder
        scan_frame = ctk.CTkFrame(controls_frame)
        scan_frame.pack(fill="x", padx=0, pady=(0, 5))
        
        ctk.CTkLabel(scan_frame, text="Scan Folder:").pack(side="left", padx=5)
        self.scan_folder_label = ctk.CTkLabel(
            scan_frame,
            text="Not selected",
            width=300,
            anchor="w"
        )
        self.scan_folder_label.pack(side="left", padx=5)
        
        ctk.CTkButton(
            scan_frame,
            text="Browse",
            command=self._browse_scan_folder,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            scan_frame,
            text="Scan",
            command=self._scan_folder,
            width=100
        ).pack(side="left", padx=5)
        
        # Row 2: Save to + output path (path shrinks so buttons stay in view)
        output_section = ctk.CTkFrame(controls_frame)
        output_section.pack(fill="x", padx=0, pady=0)
        
        self.output_destination_var = StringVar(value=config.get_output_destination())
        self.output_destination_var.trace_add("write", self._on_output_destination_changed)
        
        ctk.CTkLabel(output_section, text="Save to:").pack(side="left", padx=5)
        ctk.CTkRadioButton(
            output_section,
            variable=self.output_destination_var,
            value="input_folder",
            text="Same folder as input file",
            command=self._on_output_destination_choice
        ).pack(side="left", padx=5)
        ctk.CTkRadioButton(
            output_section,
            variable=self.output_destination_var,
            value="custom_folder",
            text="Output folder",
            command=self._on_output_destination_choice
        ).pack(side="left", padx=5)
        
        self.output_path_frame = ctk.CTkFrame(output_section)
        self.output_path_frame.pack(side="left", fill="x", expand=True, padx=5)
        self.output_folder_label = ctk.CTkLabel(
            self.output_path_frame,
            text="Not selected",
            anchor="w"
        )
        self.output_folder_label.pack(side="left", fill="x", expand=True, padx=(5, 2))
        self.browse_output_btn = ctk.CTkButton(
            self.output_path_frame,
            text="Select output folder",
            command=self._browse_output_folder,
            width=140
        )
        self.browse_output_btn.pack(side="right", padx=2)
        self.clear_output_btn = ctk.CTkButton(
            self.output_path_frame,
            text="Clear",
            command=self._clear_output_folder,
            width=60
        )
        self.clear_output_btn.pack(side="right", padx=2)
        
        # Row 3: Strip leading path segments (only when Output folder is selected)
        self.strip_frame = ctk.CTkFrame(controls_frame)
        self.strip_frame.pack(fill="x", padx=0, pady=(5, 0))
        ctk.CTkLabel(self.strip_frame, text="Strip leading path segments:").pack(side="left", padx=5, pady=5)
        self.strip_entry = ctk.CTkEntry(self.strip_frame, width=50)
        self.strip_entry.insert(0, str(config.get_strip_leading_path_segments()))
        self.strip_entry.pack(side="left", padx=(0, 10), pady=5)
        self.strip_entry.bind("<KeyRelease>", self._on_strip_changed)
        self.strip_entry.bind("<FocusOut>", self._on_strip_focus_out)
        self.preview_label = ctk.CTkLabel(
            self.strip_frame,
            text="Result: (select Output folder to see preview)",
            anchor="w"
        )
        self.preview_label.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        # File list
        self.file_list = FileListWidget(self)
        self.file_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Bottom controls
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            bottom_frame,
            text="Add Files",
            command=self._add_files,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            bottom_frame,
            text="Remove Selected",
            command=self._remove_selected,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            bottom_frame,
            text="Clear All",
            command=self._clear_all,
            width=100
        ).pack(side="left", padx=5)
        
        # Load saved scan folder
        last_scan = config.get_last_scan_folder()
        if last_scan and Path(last_scan).exists():
            self.scan_folder = Path(last_scan)
            self.scan_folder_label.configure(text=str(self.scan_folder))
        
        # Load saved output destination and folder
        dest = config.get_output_destination()
        self.output_destination_var.set(dest)
        if dest == "custom_folder":
            output_folder = config.get_default_output_folder()
            if output_folder and Path(output_folder).exists():
                self.output_folder = Path(output_folder)
                self.output_folder_label.configure(text=str(self.output_folder))
            else:
                self.output_folder = None
                self.output_folder_label.configure(text="Not selected")
        else:
            self.output_folder = None
            self.output_folder_label.configure(text="Not selected")
        self._update_output_path_visibility()
        self._update_preview()
    
    def _on_strip_changed(self, event=None):
        self._apply_strip_value()
    
    def _on_strip_focus_out(self, event=None):
        self._apply_strip_value()
    
    def _apply_strip_value(self):
        try:
            raw = self.strip_entry.get().strip()
            n = int(raw) if raw else 0
            n = max(0, min(99, n))
            config.set_strip_leading_path_segments(n)
            if raw != str(n):
                self.strip_entry.delete(0, "end")
                self.strip_entry.insert(0, str(n))
        except ValueError:
            pass
        self._update_preview()
    
    def _compute_preview_path(self) -> Optional[str]:
        if self.output_destination_var.get() != "custom_folder" or not self.output_folder:
            return None
        suffix = config.get_default_output_suffix()
        strip_n = config.get_strip_leading_path_segments()
        files = self.file_list.get_files()
        if files:
            source_file = Path(files[0]["path"])
            if self.scan_folder:
                try:
                    relative_path = source_file.relative_to(self.scan_folder)
                    relative_dir = relative_path.parent
                    parts = relative_dir.parts
                    remaining = parts[strip_n:]
                    if remaining:
                        output_dir = self.output_folder / Path(*remaining)
                    else:
                        output_dir = self.output_folder
                    result_path = output_dir / f"{source_file.stem}{suffix}.mp4"
                    return str(result_path)
                except ValueError:
                    result_path = self.output_folder / f"{source_file.stem}{suffix}.mp4"
                    return str(result_path)
            result_path = self.output_folder / f"{source_file.stem}{suffix}.mp4"
            return str(result_path)
        parts = ["Subfolder", "Another"]
        remaining = parts[strip_n:] if strip_n < len(parts) else []
        if remaining:
            example = self.output_folder / Path(*remaining) / f"file{suffix}.mp4"
        else:
            example = self.output_folder / f"file{suffix}.mp4"
        return str(example) + " (example)"
    
    def _update_preview(self):
        path_str = self._compute_preview_path()
        if path_str is not None:
            self.preview_label.configure(text=f"Result: {path_str}")
        else:
            self.preview_label.configure(text="Result: (select Output folder to see preview)")
    
    def _browse_scan_folder(self):
        """Browse for scan folder"""
        folder = filedialog.askdirectory(title="Select folder to scan for video files")
        if folder:
            self.scan_folder = Path(folder)
            self.scan_folder_label.configure(text=str(self.scan_folder))
            config.set_last_scan_folder(str(self.scan_folder))
            self._update_preview()
    
    def _on_output_destination_changed(self, *args):
        """Update visibility and persist when destination radio changes"""
        val = self.output_destination_var.get()
        self._update_output_path_visibility()
        if val in ("input_folder", "custom_folder"):
            config.set_output_destination(val)

    def _on_output_destination_choice(self):
        """Called when user selects a destination radio button"""
        if self.output_destination_var.get() == "custom_folder":
            config.set_output_destination("custom_folder")

    def _update_output_path_visibility(self):
        """Enable or disable Clear button and strip control based on destination"""
        is_custom = self.output_destination_var.get() == "custom_folder"
        self.clear_output_btn.configure(state="normal" if is_custom else "disabled")
        self.strip_entry.configure(state="normal" if is_custom else "disabled")
        self._update_preview()

    def _browse_output_folder(self):
        """Browse for output folder; switches to Output folder mode if needed"""
        if self.output_destination_var.get() != "custom_folder":
            self.output_destination_var.set("custom_folder")
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_folder = Path(folder)
            self.output_folder_label.configure(text=str(self.output_folder))
            config.set_output_destination("custom_folder")
            config.set_default_output_folder(str(self.output_folder))
            self._update_preview()

    def _clear_output_folder(self):
        """Clear the chosen output folder; encodes fall back to input location until Browse again"""
        self.output_folder = None
        self.output_folder_label.configure(text="Not selected")
        config.set_default_output_folder("")
        self._update_preview()
    
    def _scan_folder(self):
        """Scan folder for video files"""
        if not self.scan_folder:
            messagebox.showwarning("No Folder", "Please select a scan folder first")
            return
        
        # Clear existing files
        self.file_list.clear()
        
        # Scan for files
        files = self.scanner.scan_directory(self.scan_folder, recursive=True)
        
        # Add files to list
        for file_path in files:
            self.file_list.add_file(file_path, relative_to=self.scan_folder)
        
        if self.on_files_changed:
            self.on_files_changed()
        self._update_preview()
        messagebox.showinfo(
            "Scan Complete",
            f"Found {len(files)} video file(s)"
        )
    
    def _add_files(self):
        """Add individual files"""
        files = filedialog.askopenfilenames(
            title="Select video files",
            filetypes=[
                ("Video files", "*.mkv *.mp4 *.mov *.avi *.m4v *.flv *.wmv *.webm"),
                ("All files", "*.*")
            ]
        )
        
        for file_path in files:
            self.file_list.add_file(Path(file_path))
        
        if self.on_files_changed:
            self.on_files_changed()
        self._update_preview()
    
    def _remove_selected(self):
        """Remove selected files"""
        selected_count = self.file_list.remove_selected_files()
        if selected_count > 0:
            if self.on_files_changed:
                self.on_files_changed()
            self._update_preview()
            messagebox.showinfo("Files Removed", f"Removed {selected_count} file(s) from the list.")
        else:
            messagebox.showwarning("No Selection", "Please select one or more files to remove.")
    
    def _clear_all(self):
        """Clear all files"""
        self.file_list.clear()
        if self.on_files_changed:
            self.on_files_changed()
        self._update_preview()
    
    def get_files(self):
        """Get list of files"""
        return self.file_list.get_files()
    
    def get_scan_folder(self) -> Optional[Path]:
        """Get scan folder"""
        return self.scan_folder
    
    def get_output_folder(self) -> Optional[Path]:
        """Get output folder"""
        return self.output_folder
    
    def get_output_path(self, source_file: Path) -> Path:
        """Get output path for a source file, preserving folder structure"""
        use_custom = (
            self.output_destination_var.get() == "custom_folder" and self.output_folder
        )
        if not use_custom:
            return source_file.parent

        if not self.scan_folder:
            return self.output_folder

        try:
            relative_path = source_file.relative_to(self.scan_folder)
            relative_dir = relative_path.parent
            parts = relative_dir.parts
            strip_n = config.get_strip_leading_path_segments()
            remaining = parts[strip_n:]
            if remaining:
                output_dir = self.output_folder / Path(*remaining)
            else:
                output_dir = self.output_folder
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_dir
        except ValueError:
            return self.output_folder

