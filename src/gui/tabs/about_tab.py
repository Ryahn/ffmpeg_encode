"""About tab (PyQt6)."""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from core.package_manager import PackageManager


def _get_version() -> str:
    try:
        from ... import __version__

        return __version__
    except ImportError:
        pass
    try:
        init_file = Path(__file__).parent.parent.parent / "__init__.py"
        with open(init_file, encoding="utf-8") as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "Unknown"


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

        ref = QPushButton("Refresh dependencies")
        ref.clicked.connect(self._refresh)
        v.addWidget(ref)
        v.addStretch()

        out = QVBoxLayout(self)
        out.addWidget(scroll)

    def _tool_line(self, name: str, check_func) -> str:
        found, path = check_func()
        if not found:
            return "Not found"
        ver = self._tool_version(name, path)
        return f"Installed ({ver}) — {path}" if ver else f"Installed — {path}"

    def _tool_version(self, tool_name: str, path: str) -> str | None:
        try:
            if tool_name == "FFmpeg":
                r = subprocess.run(
                    [path, "-version"],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
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
        except Exception:
            pass
        return None

    def _refresh(self) -> None:
        self.package_manager = PackageManager()
        mapping = {
            "FFmpeg": self.package_manager.check_ffmpeg,
            "HandBrake CLI": self.package_manager.check_handbrake,
            "mkvinfo (MKVToolNix)": self.package_manager.check_mkvinfo,
        }
        for name, fn in mapping.items():
            if name in self.tool_labels:
                info = self._tool_line(name, fn)
                self.tool_labels[name].setText(f"<b>{name}:</b> {info}")
        QMessageBox.information(self, "Refresh", "Dependency information refreshed.")
