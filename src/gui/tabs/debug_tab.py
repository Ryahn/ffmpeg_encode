"""Debug tab (PyQt6)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.track_analyzer import TrackAnalyzer
from utils.config import config
from utils.logger import logger


class DebugTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        mkvinfo_path = config.get_mkvinfo_path() or "mkvinfo"
        self.track_analyzer = TrackAnalyzer(
            mkvinfo_path=mkvinfo_path if mkvinfo_path != "mkvinfo" else None
        )
        self.current_file: Optional[Path] = None

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Video file:"))
        self.file_label = QLabel("No file selected")
        top.addWidget(self.file_label, stretch=1)
        top.addWidget(self._btn("Browse", self._browse))
        top.addWidget(self._btn("Analyze", self._analyze))
        root.addLayout(top)

        tabs = QTabWidget()
        self.mkvinfo_text = QPlainTextEdit()
        self.mkvinfo_text.setReadOnly(True)
        miw = QWidget()
        mil = QVBoxLayout(miw)
        mil.addWidget(self._btn("Copy mkvinfo", lambda: self._copy(self.mkvinfo_text)))
        mil.addWidget(self.mkvinfo_text)
        tabs.addTab(miw, "mkvinfo Output")

        self.analysis_text = QPlainTextEdit()
        self.analysis_text.setReadOnly(True)
        aw = QWidget()
        al = QVBoxLayout(aw)
        al.addWidget(self._btn("Copy analysis", lambda: self._copy(self.analysis_text)))
        al.addWidget(self.analysis_text)
        tabs.addTab(aw, "Track Analysis")

        self.mi_out = QPlainTextEdit()
        self.mi_out.setReadOnly(True)
        mi_tab = QWidget()
        ml = QVBoxLayout(mi_tab)
        mh = QHBoxLayout()
        mh.addWidget(self._btn("Run MediaInfo", self._run_mediainfo))
        mh.addWidget(self._btn("Copy", lambda: self._copy(self.mi_out)))
        ml.addLayout(mh)
        ml.addWidget(self.mi_out)
        tabs.addTab(mi_tab, "MediaInfo")

        self.log_display = QPlainTextEdit()
        self.log_display.setReadOnly(True)
        log_tab = QWidget()
        ll = QVBoxLayout(log_tab)
        lf = QHBoxLayout()
        lf.addWidget(self._btn("Open log file", self._open_log_file))
        lf.addWidget(self._btn("Open log dir", self._open_log_dir))
        lf.addWidget(self._btn("Refresh", self._refresh_log))
        lf.addWidget(self._btn("Copy", lambda: self._copy(self.log_display)))
        ll.addLayout(lf)
        self.log_path_label = QLabel("")
        ll.addWidget(self.log_path_label)
        ll.addWidget(self.log_display)
        tabs.addTab(log_tab, "Log Files")
        root.addWidget(tabs)

        self._refresh_log()

    def _btn(self, t, fn):
        b = QPushButton(t)
        b.clicked.connect(fn)
        return b

    def _copy(self, w: QPlainTextEdit) -> None:
        QGuiApplication.clipboard().setText(w.toPlainText())

    def _browse(self) -> None:
        p, _ = QFileDialog.getOpenFileName(
            self, "Video", "", "Video (*.mkv *.mp4 *.mov *.avi);;All (*.*)"
        )
        if p:
            self.current_file = Path(p)
            self.file_label.setText(self.current_file.name)

    def _analyze(self) -> None:
        if not self.current_file:
            return
        out = self.track_analyzer.get_mkvinfo_output(self.current_file)
        self.mkvinfo_text.setPlainText(out or "Failed to get mkvinfo output.")
        tracks = self.track_analyzer.analyze_tracks(self.current_file)
        lines = [f"File: {self.current_file.name}", ""]
        lines.append(f"Audio Track: {tracks.get('audio', 'Not found')}")
        sub = tracks.get("subtitle")
        lines.append(
            f"Subtitle Track: {sub} (HandBrake --subtitle {sub + 1})"
            if sub is not None
            else "Subtitle Track: Not found"
        )
        if tracks.get("error"):
            lines.append(f"\nError: {tracks['error']}")
        if tracks.get("all_tracks"):
            lines.append("\n" + "=" * 50 + "\nAll tracks:\n")
            for tr in tracks["all_tracks"]:
                lines.append(
                    f"\nID {tr['id']} type={tr.get('type')} lang={tr.get('language')} name={tr.get('name')}"
                )
        lines.append("\n" + "=" * 50 + "\nDetection settings:\n")
        lines.append(f"Audio lang tags: {config.get_audio_language_tags()}")
        lines.append(f"Subtitle name patterns: {config.get_subtitle_name_patterns()}")
        self.analysis_text.setPlainText("\n".join(lines))

    def _run_mediainfo(self) -> None:
        if not self.current_file or not self.current_file.exists():
            self.mi_out.setPlainText("Select a file and click Analyze first.")
            return
        mediainfo_path = config.get_mediainfo_path()
        if mediainfo_path and Path(mediainfo_path).exists():
            mediainfo_path = str(Path(mediainfo_path).resolve())
        else:
            import shutil

            mediainfo_path = shutil.which("mediainfo") or shutil.which("mediainfo.exe")
        if not mediainfo_path:
            self.mi_out.setPlainText("Set MediaInfo path in Settings or install on PATH.")
            return
        run_kw = {
            "args": [mediainfo_path, str(self.current_file)],
            "stdin": subprocess.DEVNULL,
            "capture_output": True,
            "text": True,
            "timeout": 30,
        }
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            run_kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            r = subprocess.run(**run_kw)
            self.mi_out.setPlainText(r.stdout or r.stderr or "(no output)")
        except Exception as e:
            self.mi_out.setPlainText(str(e))

    def _open_log_file(self) -> None:
        lf = logger.get_log_file()
        if lf and lf.exists():
            try:
                if sys.platform == "win32":
                    os.startfile(str(lf))
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(lf)], stdin=subprocess.DEVNULL)
                else:
                    subprocess.run(["xdg-open", str(lf)], stdin=subprocess.DEVNULL)
            except Exception:
                pass

    def _open_log_dir(self) -> None:
        lf = logger.get_log_file()
        d = lf.parent if lf else Path.home() / ".video_encoder" / "logs"
        if d.exists():
            try:
                if sys.platform == "win32":
                    os.startfile(str(d))
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(d)], stdin=subprocess.DEVNULL)
                else:
                    subprocess.run(["xdg-open", str(d)], stdin=subprocess.DEVNULL)
            except Exception:
                pass

    def _refresh_log(self) -> None:
        lf = logger.get_log_file()
        if lf and lf.exists():
            self.log_path_label.setText(str(lf))
        else:
            self.log_path_label.setText("No log file")
        recent = logger.get_recent_logs(100)
        if not recent:
            self.log_display.setPlainText("No log entries yet.")
            return
        self.log_display.setPlainText("\n".join(f"[{a}] {b}" for a, b in recent))
