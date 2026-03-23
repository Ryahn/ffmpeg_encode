"""About tab (PyQt6)."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.package_manager import PackageManager
from core.subprocess_utils import get_subprocess_kwargs
from gui.dialogs.update_dialog import show_update_dialog
from utils.app_version import get_app_version
from utils.config import config


def _get_version() -> str:
    return get_app_version()


class AboutTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.package_manager = PackageManager()
        self.tool_labels: dict = {}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        v = QVBoxLayout(inner)

        v.addWidget(QLabel("<h2>Video Encoder GUI</h2>"))
        v.addWidget(QLabel(f"<b>Version {_get_version()}</b>"))
        v.addWidget(
            QLabel(
                "Cross-platform GUI for encoding with HandBrake or FFmpeg, "
                "track detection, and presets."
            )
        )
        v.addWidget(QLabel("Copyright © 2025 Ryan Carr"))
        v.addWidget(QLabel("Licensed under the MIT License"))

        v.addWidget(QLabel("<h3>System</h3>"))
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        v.addWidget(QLabel(f"Python: {py_ver}"))
        v.addWidget(QLabel(f"Platform: {platform.system()} {platform.release()}"))
        v.addWidget(QLabel(f"Architecture: {platform.machine()}"))

        v.addWidget(QLabel("<h3>Dependencies</h3>"))
        v.addWidget(QLabel("<b>External tools</b>"))
        for name, fn in [
            ("FFmpeg", self.package_manager.check_ffmpeg),
            ("HandBrake CLI", self.package_manager.check_handbrake),
            ("mkvinfo (MKVToolNix)", self.package_manager.check_mkvinfo),
            ("MediaInfo", self._check_mediainfo),
        ]:
            info = self._tool_line(name, fn)
            lb = QLabel(f"<b>{name}:</b> {info}")
            lb.setWordWrap(True)
            v.addWidget(lb)
            self.tool_labels[name] = lb

        v.addWidget(QLabel("<b>Python packages</b>"))
        v.addWidget(QLabel(f"PyQt6: {PYQT_VERSION_STR} (Qt {QT_VERSION_STR})"))
        try:
            from PIL import __version__ as pil_v

            v.addWidget(QLabel(f"Pillow: {pil_v}"))
        except Exception:
            v.addWidget(QLabel("Pillow: not installed"))

        ref_row = QWidget()
        ref_l = QVBoxLayout(ref_row)
        ref_l.setContentsMargins(0, 0, 0, 0)
        h = QHBoxLayout()
        ref = QPushButton("Refresh dependencies")
        ref.clicked.connect(self._refresh)
        h.addWidget(ref)
        updates = QPushButton("Check for updates")
        updates.setToolTip("Compare this build to the latest GitHub release.")
        updates.clicked.connect(lambda: show_update_dialog(self))
        h.addWidget(updates)
        copy_diag = QPushButton("Copy diagnostics")
        copy_diag.setToolTip("Copy version and dependency summary for bug reports.")
        copy_diag.clicked.connect(self._copy_diagnostics)
        h.addWidget(copy_diag)
        h.addStretch()
        ref_l.addLayout(h)
        self._about_status = QLabel("")
        self._about_status.setStyleSheet("color: #888888; font-size: 12px;")
        ref_l.addWidget(self._about_status)
        v.addWidget(ref_row)
        v.addStretch()

        out = QVBoxLayout(self)
        out.addWidget(scroll)

    def _check_mediainfo(self) -> tuple[bool, str]:
        p = (config.get_mediainfo_path() or "").strip()
        if p and Path(p).is_file():
            resolved = str(Path(p).resolve())
            return True, self.package_manager._normalize_detected_exe_path(resolved) or resolved
        w = shutil.which("mediainfo") or shutil.which("mediainfo.exe")
        if w:
            return True, self.package_manager._normalize_detected_exe_path(w) or w
        return False, ""

    def _tool_line(self, name: str, check_func) -> str:
        found, path = check_func()
        if not found:
            return "Not found"
        ver = self._tool_version(name, path)
        return f"Installed ({ver}) — {path}" if ver else f"Installed — {path}"

    def _tool_version(self, tool_name: str, path: str) -> str | None:
        try:
            if tool_name == "FFmpeg":
                run_kw = {
                    "args": [path, "-version"],
                    "stdin": subprocess.DEVNULL,
                    "capture_output": True,
                    "text": True,
                    "timeout": 5,
                }
                run_kw.update(get_subprocess_kwargs())
                r = subprocess.run(**run_kw)
                if r.returncode == 0 and r.stdout:
                    line = r.stdout.split("\n")[0]
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if "version" in p.lower() and i + 1 < len(parts):
                            return parts[i + 1]
            if tool_name == "HandBrake CLI":
                r = subprocess.run(
                    [path, "--version"],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if r.returncode == 0 and r.stdout:
                    parts = r.stdout.split("\n")[0].split()
                    for p in parts:
                        if p.replace(".", "").isdigit():
                            return p
            if tool_name == "mkvinfo (MKVToolNix)":
                run_kw = {
                    "args": [path, "--version"],
                    "stdin": subprocess.DEVNULL,
                    "capture_output": True,
                    "text": True,
                    "timeout": 5,
                }
                run_kw.update(get_subprocess_kwargs())
                r = subprocess.run(**run_kw)
                if r.returncode == 0 and r.stdout:
                    parts = r.stdout.split("\n")[0].split()
                    for p in parts:
                        if p.replace(".", "").isdigit():
                            return p
            if tool_name == "MediaInfo":
                run_kw = {
                    "args": [path, "--version"],
                    "stdin": subprocess.DEVNULL,
                    "capture_output": True,
                    "text": True,
                    "timeout": 5,
                }
                run_kw.update(get_subprocess_kwargs())
                r = subprocess.run(**run_kw)
                if r.returncode == 0 and r.stdout:
                    line = r.stdout.split("\n")[0].strip()
                    return line[:80] if line else None
        except Exception:
            pass
        return None

    def _diagnostics_text(self) -> str:
        lines = [
            f"Video Encoder {_get_version()}",
            f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            f"PyQt6 {PYQT_VERSION_STR} (Qt {QT_VERSION_STR})",
            f"Platform: {platform.system()} {platform.release()} ({platform.machine()})",
            "",
        ]
        for name, fn in [
            ("FFmpeg", self.package_manager.check_ffmpeg),
            ("HandBrake CLI", self.package_manager.check_handbrake),
            ("mkvinfo", self.package_manager.check_mkvinfo),
            ("MediaInfo", self._check_mediainfo),
        ]:
            ok, path = fn()
            lines.append(f"{name}: {'OK' if ok else 'missing'} {path}")
        return "\n".join(lines)

    def _copy_diagnostics(self) -> None:
        QGuiApplication.clipboard().setText(self._diagnostics_text())
        self._about_status.setText("Diagnostics copied to clipboard.")

    def _refresh(self) -> None:
        self.package_manager = PackageManager()
        mapping = {
            "FFmpeg": self.package_manager.check_ffmpeg,
            "HandBrake CLI": self.package_manager.check_handbrake,
            "mkvinfo (MKVToolNix)": self.package_manager.check_mkvinfo,
            "MediaInfo": self._check_mediainfo,
        }
        for name, fn in mapping.items():
            if name in self.tool_labels:
                info = self._tool_line(name, fn)
                self.tool_labels[name].setText(f"<b>{name}:</b> {info}")
        self._about_status.setText("Dependency list refreshed.")
