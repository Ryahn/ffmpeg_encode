"""Settings tab (PyQt6)."""

from __future__ import annotations

import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QButtonGroup,
)

from core.package_manager import PackageManager
from utils.config import config


class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.package_manager = PackageManager()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(inner)

        root.addWidget(self._paths_group())
        root.addWidget(self._output_group())
        root.addWidget(self._encoding_group())
        root.addWidget(self._track_group())
        root.addStretch()

        lay = QVBoxLayout(self)
        lay.addWidget(scroll)
        lay.addWidget(QLabel("Settings save automatically when changed."))
        lay.addWidget(self._btn("Save All Settings", self._save_all))

    def _btn(self, t, fn):
        b = QPushButton(t)
        b.clicked.connect(fn)
        return b

    def _path_row(self, label: str, value: str, browse, auto):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        e = QLineEdit(value)
        h.addWidget(e, stretch=1)
        h.addWidget(self._btn("Browse", lambda: browse(e)))
        h.addWidget(self._btn("Auto-detect", lambda: auto(e)))
        return w, e

    def _paths_group(self) -> QGroupBox:
        g = QGroupBox("Executable Paths")
        f = QFormLayout(g)
        w1, self.ffmpeg_entry = self._path_row(
            "FFmpeg", config.get_ffmpeg_path() or "", self._browse_ffmpeg, self._auto_ffmpeg
        )
        f.addRow("FFmpeg:", w1)
        w2, self.handbrake_entry = self._path_row(
            "HandBrake", config.get_handbrake_path() or "", self._browse_hb, self._auto_hb
        )
        f.addRow("HandBrake CLI:", w2)
        w3, self.mkvinfo_entry = self._path_row(
            "mkvinfo", config.get_mkvinfo_path() or "", self._browse_mkv, self._auto_mkv
        )
        f.addRow("mkvinfo:", w3)
        w4, self.mediainfo_entry = self._path_row(
            "MediaInfo", config.get_mediainfo_path() or "", self._browse_mi, self._auto_mi
        )
        f.addRow("MediaInfo:", w4)
        self.ffmpeg_entry.editingFinished.connect(lambda: config.set_ffmpeg_path(self.ffmpeg_entry.text().strip()))
        self.handbrake_entry.editingFinished.connect(
            lambda: config.set_handbrake_path(self.handbrake_entry.text().strip())
        )
        self.mkvinfo_entry.editingFinished.connect(lambda: config.set_mkvinfo_path(self.mkvinfo_entry.text().strip()))
        self.mediainfo_entry.editingFinished.connect(
            lambda: config.set_mediainfo_path(self.mediainfo_entry.text().strip())
        )
        return g

    def _browse_ffmpeg(self, e):
        p, _ = QFileDialog.getOpenFileName(self, "FFmpeg", "", "Executable (*.exe);;All (*.*)")
        if p:
            e.setText(p)
            config.set_ffmpeg_path(p)

    def _browse_hb(self, e):
        p, _ = QFileDialog.getOpenFileName(self, "HandBrake CLI", "", "Executable (*.exe);;All (*.*)")
        if p:
            e.setText(p)
            config.set_handbrake_path(p)

    def _browse_mkv(self, e):
        p, _ = QFileDialog.getOpenFileName(self, "mkvinfo", "", "Executable (*.exe);;All (*.*)")
        if p:
            e.setText(p)
            config.set_mkvinfo_path(p)

    def _browse_mi(self, e):
        p, _ = QFileDialog.getOpenFileName(self, "MediaInfo", "", "Executable (*.exe);;All (*.*)")
        if p:
            e.setText(p)
            config.set_mediainfo_path(p)

    def _auto_ffmpeg(self, e):
        ok, path = self.package_manager.check_ffmpeg()
        if ok:
            e.setText(path)
            config.set_ffmpeg_path(path)
        else:
            QMessageBox.information(self, "Not found", "FFmpeg not found on PATH.")

    def _auto_hb(self, e):
        ok, path = self.package_manager.check_handbrake()
        if ok:
            e.setText(path)
            config.set_handbrake_path(path)
        else:
            QMessageBox.information(self, "Not found", "HandBrake CLI not found.")

    def _auto_mkv(self, e):
        ok, path = self.package_manager.check_mkvinfo()
        if ok:
            e.setText(path)
            config.set_mkvinfo_path(path)
        else:
            QMessageBox.information(self, "Not found", "mkvinfo not found.")

    def _auto_mi(self, e):
        p = shutil.which("mediainfo") or shutil.which("mediainfo.exe")
        if p:
            e.setText(p)
            config.set_mediainfo_path(p)
        else:
            QMessageBox.information(self, "Not found", "MediaInfo not on PATH.")

    def _output_group(self) -> QGroupBox:
        g = QGroupBox("Output Settings")
        f = QFormLayout(g)
        self.suffix_entry = QLineEdit(config.get_default_output_suffix())
        self.suffix_entry.textChanged.connect(lambda t: config.set_default_output_suffix(t))
        f.addRow("Default output suffix:", self.suffix_entry)
        return g

    def _encoding_group(self) -> QGroupBox:
        g = QGroupBox("Encoding")
        v = QVBoxLayout(g)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Default encoding mode:"))
        self._mode_grp = QButtonGroup(self)
        self._m_seq = QRadioButton("Sequential")
        self._m_par = QRadioButton("Parallel")
        self._mode_grp.addButton(self._m_seq)
        self._mode_grp.addButton(self._m_par)
        if config.get_encoding_mode() == "parallel":
            self._m_par.setChecked(True)
        else:
            self._m_seq.setChecked(True)
        self._m_seq.toggled.connect(self._persist_mode)
        mode_row.addWidget(self._m_seq)
        mode_row.addWidget(self._m_par)
        v.addLayout(mode_row)
        self.skip_cb = QCheckBox("Skip existing encoded files by default")
        self.skip_cb.setChecked(config.get_skip_existing())
        self.skip_cb.toggled.connect(lambda x: config.set_skip_existing(x))
        v.addWidget(self.skip_cb)
        self.debug_cb = QCheckBox("Enable debug logging")
        self.debug_cb.setChecked(config.get_debug_logging())
        self.debug_cb.toggled.connect(lambda x: config.set_debug_logging(x))
        v.addWidget(self.debug_cb)
        self.norm_cb = QCheckBox("Apply loudness normalization (FFmpeg single-pass loudnorm)")
        self.norm_cb.setChecked(config.get_audio_normalize_enabled())
        self.norm_cb.toggled.connect(lambda x: config.set_audio_normalize_enabled(x))
        v.addWidget(self.norm_cb)
        return g

    def _persist_mode(self) -> None:
        config.set_encoding_mode("parallel" if self._m_par.isChecked() else "sequential")

    def _track_group(self) -> QGroupBox:
        g = QGroupBox("Track detection")
        f = QFormLayout(g)
        self.ja_cb = QCheckBox("Encode Japanese audio with English subs when no English audio")
        self.ja_cb.setChecked(config.get_allow_japanese_audio_with_english_subs())
        self.ja_cb.toggled.connect(lambda x: config.set_allow_japanese_audio_with_english_subs(x))
        f.addRow(self.ja_cb)
        self.audio_lang = QLineEdit(", ".join(config.get_audio_language_tags()))
        self.audio_lang.textChanged.connect(self._save_audio_lang)
        f.addRow("Audio language tags:", self.audio_lang)
        self.audio_name = QLineEdit(", ".join(config.get_audio_name_patterns()))
        self.audio_name.textChanged.connect(self._save_audio_name)
        f.addRow("Audio name patterns:", self.audio_name)
        self.audio_ex = QLineEdit(", ".join(config.get_audio_exclude_patterns()))
        self.audio_ex.textChanged.connect(self._save_audio_ex)
        f.addRow("Audio exclude patterns:", self.audio_ex)
        self.sub_lang = QLineEdit(", ".join(config.get_subtitle_language_tags()))
        self.sub_lang.textChanged.connect(self._save_sub_lang)
        f.addRow("Subtitle language tags:", self.sub_lang)
        self.sub_name = QLineEdit(", ".join(config.get_subtitle_name_patterns()))
        self.sub_name.textChanged.connect(self._save_sub_name)
        f.addRow("Subtitle name patterns:", self.sub_name)
        self.sub_ex = QLineEdit(", ".join(config.get_subtitle_exclude_patterns()))
        self.sub_ex.textChanged.connect(self._save_sub_ex)
        f.addRow("Subtitle exclude patterns:", self.sub_ex)
        return g

    def _save_audio_lang(self, t: str) -> None:
        config.set_audio_language_tags([x.strip() for x in t.split(",") if x.strip()])

    def _save_audio_name(self, t: str) -> None:
        config.set_audio_name_patterns([x.strip() for x in t.split(",") if x.strip()])

    def _save_audio_ex(self, t: str) -> None:
        config.set_audio_exclude_patterns([x.strip() for x in t.split(",") if x.strip()])

    def _save_sub_lang(self, t: str) -> None:
        config.set_subtitle_language_tags([x.strip() for x in t.split(",") if x.strip()])

    def _save_sub_name(self, t: str) -> None:
        config.set_subtitle_name_patterns([x.strip() for x in t.split(",") if x.strip()])

    def _save_sub_ex(self, t: str) -> None:
        config.set_subtitle_exclude_patterns([x.strip() for x in t.split(",") if x.strip()])

    def _save_all(self) -> None:
        try:
            config.set_ffmpeg_path(self.ffmpeg_entry.text().strip())
            config.set_handbrake_path(self.handbrake_entry.text().strip())
            config.set_mkvinfo_path(self.mkvinfo_entry.text().strip())
            config.set_mediainfo_path(self.mediainfo_entry.text().strip())
            config.set_default_output_suffix(self.suffix_entry.text())
            config.set_encoding_mode("parallel" if self._m_par.isChecked() else "sequential")
            config.set_skip_existing(self.skip_cb.isChecked())
            config.set_debug_logging(self.debug_cb.isChecked())
            config.set_audio_normalize_enabled(self.norm_cb.isChecked())
            QMessageBox.information(self, "Saved", "All settings saved.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
