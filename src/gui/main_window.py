"""Main application window (PyQt6)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QWidget,
    QVBoxLayout,
)

from core.notifications import BatchNotification
from core.package_manager import PackageManager
from utils.config import config
from utils.logger import logger

from .tabs.about_tab import AboutTab
from .tabs.debug_tab import DebugTab
from .tabs.files_tab import FilesTab
from .tabs.ffmpeg_tab import FFmpegTab
from .tabs.handbrake_tab import HandBrakeTab
from .tabs.settings_tab import SettingsTab
from .widgets.toast import ToastManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Encoder")
        self.resize(1200, 800)
        self._set_icon()

        self.toast_manager = ToastManager(self)
        BatchNotification.set_toast_manager(self.toast_manager)

        self.package_manager = PackageManager()
        self._check_dependencies()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 14, 14, 0)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        self.files_tab = FilesTab()
        self.tab_widget.addTab(self.files_tab, "Files")
        self.files_tab.on_files_changed = self._on_files_changed
        self.files_tab.on_status = self._update_status

        self.handbrake_tab = HandBrakeTab()
        self.tab_widget.addTab(self.handbrake_tab, "HandBrake")
        self.handbrake_tab.get_files_callback = self._get_files
        self.handbrake_tab.update_file_callback = self._update_file
        self.handbrake_tab.get_output_path_callback = self._get_output_path
        self.handbrake_tab.main_window = self

        self.ffmpeg_tab = FFmpegTab()
        self.tab_widget.addTab(self.ffmpeg_tab, "FFmpeg")
        self.ffmpeg_tab.get_files_callback = self._get_files
        self.ffmpeg_tab.update_file_callback = self._update_file
        self.ffmpeg_tab.get_output_path_callback = self._get_output_path
        self.ffmpeg_tab.main_window = self

        self.settings_tab = SettingsTab()
        self.tab_widget.addTab(self.settings_tab, "Settings")

        self.debug_tab = DebugTab()
        self.tab_widget.addTab(self.debug_tab, "Debug")

        self.about_tab = AboutTab()
        self.tab_widget.addTab(self.about_tab, "About")

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._update_status()

    def _set_icon(self) -> None:
        try:
            if getattr(sys, "frozen", False):
                icon_path = Path(sys._MEIPASS) / "gui" / "icon.ico"
            else:
                icon_path = Path(__file__).parent / "icon.ico"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception as e:
            logger.warning(f"Could not set window icon: {e}")

    def _check_dependencies(self) -> None:
        missing = []
        found, path = self.package_manager.check_ffmpeg()
        if not found:
            missing.append("FFmpeg")
        elif not config.get_ffmpeg_path():
            config.set_ffmpeg_path(path)
        found, path = self.package_manager.check_handbrake()
        if not found:
            missing.append("HandBrake CLI")
        elif not config.get_handbrake_path():
            config.set_handbrake_path(path)
        found, path = self.package_manager.check_mkvinfo()
        if not found:
            missing.append("mkvinfo (MKVToolNix)")
        elif not config.get_mkvinfo_path():
            config.set_mkvinfo_path(path)
        if missing:
            logger.warning(f"Missing dependencies: {', '.join(missing)}")

    def _get_files(self):
        return self.files_tab.get_files()

    def _update_file(self, index: int, file_data: dict) -> None:
        self.files_tab.file_list.update_file(index, **file_data)

    def _get_output_path(self, source_file: Path) -> Path:
        return self.files_tab.get_output_path(source_file)

    def _on_files_changed(self) -> None:
        files = self.files_tab.get_files()
        self._update_status(f"{len(files)} file(s) ready")
        if hasattr(self.handbrake_tab, "on_files_changed"):
            self.handbrake_tab.on_files_changed()
        if hasattr(self.ffmpeg_tab, "on_files_changed"):
            self.ffmpeg_tab.on_files_changed()

    def _update_status(self, message: Optional[str] = None) -> None:
        if message:
            self._status.showMessage(message)
        else:
            n = len(self.files_tab.get_files())
            self._status.showMessage(f"Ready - {n} file(s) in queue")

    def closeEvent(self, event: QCloseEvent) -> None:
        try:
            if self.ffmpeg_tab and getattr(self.ffmpeg_tab, "is_encoding", False):
                enc = getattr(self.ffmpeg_tab, "encoder", None)
                if enc:
                    logger.info("Stopping FFmpeg encoder on window close")
                    enc.stop()
        except Exception as e:
            logger.warning(f"Error stopping FFmpeg encoder: {e}")
        try:
            if self.handbrake_tab and getattr(self.handbrake_tab, "is_encoding", False):
                enc = getattr(self.handbrake_tab, "encoder", None)
                if enc:
                    logger.info("Stopping HandBrake encoder on window close")
                    enc.stop()
        except Exception as e:
            logger.warning(f"Error stopping HandBrake encoder: {e}")
        config.flush()
        event.accept()
