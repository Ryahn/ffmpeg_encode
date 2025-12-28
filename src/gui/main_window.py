"""Main application window"""

import sys
import customtkinter as ctk
from pathlib import Path
from typing import Optional

from .tabs.files_tab import FilesTab
from .tabs.handbrake_tab import HandBrakeTab
from .tabs.ffmpeg_tab import FFmpegTab
from .tabs.settings_tab import SettingsTab
from .tabs.debug_tab import DebugTab
from .tabs.about_tab import AboutTab
from core.package_manager import PackageManager
from utils.config import config
from utils.logger import logger


class MainWindow(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("Video Encoder")
        self.geometry("1200x800")
        
        # Set window icon
        self._set_icon()
        
        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize package manager
        self.package_manager = PackageManager()
        
        # Check for required tools
        self._check_dependencies()
        
        # Create tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Files tab
        self.tabview.add("Files")
        tab_frame = self.tabview.tab("Files")
        self.files_tab = FilesTab(tab_frame)
        self.files_tab.pack(fill="both", expand=True)
        self.files_tab.on_files_changed = self._on_files_changed
        
        # HandBrake tab
        self.tabview.add("HandBrake")
        tab_frame = self.tabview.tab("HandBrake")
        self.handbrake_tab = HandBrakeTab(tab_frame)
        self.handbrake_tab.pack(fill="both", expand=True)
        self.handbrake_tab.get_files_callback = self._get_files
        self.handbrake_tab.update_file_callback = self._update_file
        self.handbrake_tab.get_output_path_callback = self._get_output_path
        
        # FFmpeg tab
        self.tabview.add("FFmpeg")
        tab_frame = self.tabview.tab("FFmpeg")
        self.ffmpeg_tab = FFmpegTab(tab_frame)
        self.ffmpeg_tab.pack(fill="both", expand=True)
        self.ffmpeg_tab.get_files_callback = self._get_files
        self.ffmpeg_tab.update_file_callback = self._update_file
        self.ffmpeg_tab.get_output_path_callback = self._get_output_path
        
        # Settings tab
        self.tabview.add("Settings")
        tab_frame = self.tabview.tab("Settings")
        self.settings_tab = SettingsTab(tab_frame)
        self.settings_tab.pack(fill="both", expand=True)
        
        # Debug tab
        self.tabview.add("Debug")
        tab_frame = self.tabview.tab("Debug")
        self.debug_tab = DebugTab(tab_frame)
        self.debug_tab.pack(fill="both", expand=True)
        
        # About tab
        self.tabview.add("About")
        tab_frame = self.tabview.tab("About")
        self.about_tab = AboutTab(tab_frame)
        self.about_tab.pack(fill="both", expand=True)
        
        # Status bar
        self.status_bar = ctk.CTkLabel(
            self,
            text="Ready",
            anchor="w"
        )
        self.status_bar.pack(fill="x", side="bottom", padx=10, pady=5)
        
        # Update status
        self._update_status()
    
    def _set_icon(self):
        """Set the window icon"""
        try:
            if getattr(sys, 'frozen', False):
                # Running as a bundled executable
                icon_path = Path(sys._MEIPASS) / 'gui' / 'icon.ico'
            else:
                # Running as a normal Python script
                icon_path = Path(__file__).parent / 'icon.ico'
            
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception as e:
            logger.warning(f"Could not set window icon: {e}")
    
    def _check_dependencies(self):
        """Check for required dependencies"""
        missing = []
        
        # Check FFmpeg
        found, path = self.package_manager.check_ffmpeg()
        if not found:
            missing.append("FFmpeg")
        else:
            if not config.get_ffmpeg_path():
                config.set_ffmpeg_path(path)
        
        # Check HandBrake
        found, path = self.package_manager.check_handbrake()
        if not found:
            missing.append("HandBrake CLI")
        else:
            if not config.get_handbrake_path():
                config.set_handbrake_path(path)
        
        # Check mkvinfo
        found, path = self.package_manager.check_mkvinfo()
        if not found:
            missing.append("mkvinfo (MKVToolNix)")
        else:
            if not config.get_mkvinfo_path():
                config.set_mkvinfo_path(path)
        
        if missing:
            logger.warning(f"Missing dependencies: {', '.join(missing)}")
            # TODO: Show dialog offering to install
    
    def _get_files(self):
        """Get files from files tab"""
        return self.files_tab.get_files()
    
    def _update_file(self, index: int, file_data: dict):
        """Update file in file list"""
        self.files_tab.file_list.update_file(index, **file_data)
    
    def _get_output_path(self, source_file: Path) -> Path:
        """Get output path for a source file"""
        return self.files_tab.get_output_path(source_file)
    
    def _on_files_changed(self):
        """Handle files list change"""
        files = self.files_tab.get_files()
        count = len(files)
        self._update_status(f"{count} file(s) ready")
        # Notify FFmpeg tab to update preview
        if hasattr(self.ffmpeg_tab, 'on_files_changed'):
            self.ffmpeg_tab.on_files_changed()
    
    def _update_status(self, message: Optional[str] = None):
        """Update status bar"""
        if message:
            self.status_bar.configure(text=message)
        else:
            files = self.files_tab.get_files()
            count = len(files)
            self.status_bar.configure(text=f"Ready - {count} file(s) in queue")
    
    def run(self):
        """Run the application"""
        self.mainloop()

