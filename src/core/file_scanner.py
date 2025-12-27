"""Scan for video files in directories"""

from pathlib import Path
from typing import List, Set


class FileScanner:
    """Scans directories for video files"""
    
    # Supported video file extensions
    VIDEO_EXTENSIONS: Set[str] = {
        ".mkv", ".mp4", ".mov", ".avi", ".m4v",
        ".flv", ".wmv", ".webm", ".ts", ".mts",
        ".m2ts", ".vob", ".3gp", ".3g2"
    }
    
    def __init__(self):
        self.found_files: List[Path] = []
    
    def scan_directory(self, directory: Path, recursive: bool = True) -> List[Path]:
        """Scan a directory for video files"""
        self.found_files = []
        
        if not directory.exists() or not directory.is_dir():
            return self.found_files
        
        if recursive:
            for ext in self.VIDEO_EXTENSIONS:
                self.found_files.extend(directory.rglob(f"*{ext}"))
                self.found_files.extend(directory.rglob(f"*{ext.upper()}"))
        else:
            for ext in self.VIDEO_EXTENSIONS:
                self.found_files.extend(directory.glob(f"*{ext}"))
                self.found_files.extend(directory.glob(f"*{ext.upper()}"))
        
        # Remove duplicates and sort
        self.found_files = sorted(set(self.found_files))
        return self.found_files
    
    def is_video_file(self, file_path: Path) -> bool:
        """Check if a file is a video file"""
        return file_path.suffix.lower() in self.VIDEO_EXTENSIONS
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes"""
        try:
            return file_path.stat().st_size
        except Exception:
            return 0
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size as human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

