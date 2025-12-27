"""Files tab for managing video files"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
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
        
        # Top controls
        controls_frame = ctk.CTkFrame(self)
        controls_frame.pack(fill="x", padx=10, pady=10)
        
        # Scan folder
        scan_frame = ctk.CTkFrame(controls_frame)
        scan_frame.pack(side="left", padx=5)
        
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
        
        # Output folder
        output_frame = ctk.CTkFrame(controls_frame)
        output_frame.pack(side="left", padx=5)
        
        ctk.CTkLabel(output_frame, text="Output Folder:").pack(side="left", padx=5)
        self.output_folder_label = ctk.CTkLabel(
            output_frame,
            text="Not selected",
            width=300,
            anchor="w"
        )
        self.output_folder_label.pack(side="left", padx=5)
        
        ctk.CTkButton(
            output_frame,
            text="Browse",
            command=self._browse_output_folder,
            width=100
        ).pack(side="left", padx=5)
        
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
        
        # Load saved output folder
        output_folder = config.get_default_output_folder()
        if output_folder and Path(output_folder).exists():
            self.output_folder = Path(output_folder)
            self.output_folder_label.configure(text=str(self.output_folder))
    
    def _browse_scan_folder(self):
        """Browse for scan folder"""
        folder = filedialog.askdirectory(title="Select folder to scan for video files")
        if folder:
            self.scan_folder = Path(folder)
            self.scan_folder_label.configure(text=str(self.scan_folder))
            config.set_last_scan_folder(str(self.scan_folder))
    
    def _browse_output_folder(self):
        """Browse for output folder"""
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_folder = Path(folder)
            self.output_folder_label.configure(text=str(self.output_folder))
            config.set_default_output_folder(str(self.output_folder))
    
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
    
    def _remove_selected(self):
        """Remove selected files"""
        # For now, remove all (selection not implemented)
        messagebox.showinfo("Info", "Selection not yet implemented. Use Clear All.")
    
    def _clear_all(self):
        """Clear all files"""
        self.file_list.clear()
        if self.on_files_changed:
            self.on_files_changed()
    
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
        if not self.output_folder:
            # If no output folder, use same directory as source
            return source_file.parent
        
        if not self.scan_folder:
            # If no scan folder, just use output folder
            return self.output_folder
        
        # Preserve relative structure
        try:
            relative_path = source_file.relative_to(self.scan_folder)
            output_path = self.output_folder / relative_path.parent
            output_path.mkdir(parents=True, exist_ok=True)
            return output_path
        except ValueError:
            # Files not under scan folder, use output folder root
            return self.output_folder

