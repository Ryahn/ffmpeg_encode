"""Settings tab (PyQt6)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, List

from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDoubleSpinBox,
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
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.package_manager import PackageManager
from utils.config import config


class SettingsTab(QWidget):
    main_window: Any = None

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
        root.addWidget(self._files_defaults_group())
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

    def _files_defaults_group(self) -> QGroupBox:
        g = QGroupBox("Files tab defaults")
        note = QLabel(
            "Strip count and default output folder are shared with the Files tab "
            "(switch to Files to refresh the view after changes here)."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #888888; font-size: 12px;")
        outer = QVBoxLayout(g)
        outer.addWidget(note)
        form = QFormLayout()
        self.strip_spin = QSpinBox()
        self.strip_spin.setRange(0, 99)
        self.strip_spin.setValue(config.get_strip_leading_path_segments())
        self.strip_spin.valueChanged.connect(lambda v: config.set_strip_leading_path_segments(int(v)))
        form.addRow("Strip leading path segments:", self.strip_spin)

        dest = QWidget()
        dv = QVBoxLayout(dest)
        dv.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self._files_dest_grp = QButtonGroup(self)
        self._files_radio_input = QRadioButton("Save next to input file (default)")
        self._files_radio_custom = QRadioButton("Default custom output folder")
        self._files_dest_grp.addButton(self._files_radio_input)
        self._files_dest_grp.addButton(self._files_radio_custom)
        if config.get_output_destination() == "custom_folder":
            self._files_radio_custom.setChecked(True)
        else:
            self._files_radio_input.setChecked(True)
        self._files_radio_input.toggled.connect(self._on_files_default_dest_toggled)
        self._files_radio_custom.toggled.connect(self._on_files_default_dest_toggled)
        row.addWidget(self._files_radio_input)
        row.addWidget(self._files_radio_custom)
        dv.addLayout(row)
        fold_row = QHBoxLayout()
        self.default_output_folder_entry = QLineEdit(config.get_default_output_folder())
        self.default_output_folder_entry.editingFinished.connect(
            lambda: config.set_default_output_folder(self.default_output_folder_entry.text().strip())
        )
        fold_row.addWidget(self.default_output_folder_entry, stretch=1)
        self._browse_default_out_btn = self._btn("Browse…", self._browse_default_output_folder)
        fold_row.addWidget(self._browse_default_out_btn)
        dv.addLayout(fold_row)
        form.addRow("Output destination:", dest)
        outer.addLayout(form)
        self._sync_default_output_folder_widgets()
        return g

    def _on_files_default_dest_toggled(self) -> None:
        if self._files_radio_custom.isChecked():
            config.set_output_destination("custom_folder")
        else:
            config.set_output_destination("input_folder")
        self._sync_default_output_folder_widgets()

    def _sync_default_output_folder_widgets(self) -> None:
        custom = self._files_radio_custom.isChecked()
        self.default_output_folder_entry.setEnabled(custom)
        self._browse_default_out_btn.setEnabled(custom)

    def _browse_default_output_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select default output folder")
        if d:
            self._files_radio_custom.setChecked(True)
            self.default_output_folder_entry.setText(d)
            config.set_output_destination("custom_folder")
            config.set_default_output_folder(d)
            self._sync_default_output_folder_widgets()

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
        self.norm_cb.toggled.connect(self._on_norm_enabled_changed)
        v.addWidget(self.norm_cb)
        loud_form = QFormLayout()
        self.loudnorm_I = QDoubleSpinBox()
        self.loudnorm_I.setRange(-70.0, -5.0)
        self.loudnorm_I.setDecimals(1)
        self.loudnorm_I.setSingleStep(0.5)
        self.loudnorm_I.setValue(config.get_audio_normalize_loudnorm_I())
        self.loudnorm_I.valueChanged.connect(self._on_loudnorm_value_changed)
        loud_form.addRow("Loudnorm target I (LUFS):", self.loudnorm_I)
        self.loudnorm_TP = QDoubleSpinBox()
        self.loudnorm_TP.setRange(-9.0, 0.0)
        self.loudnorm_TP.setDecimals(1)
        self.loudnorm_TP.setSingleStep(0.5)
        self.loudnorm_TP.setValue(config.get_audio_normalize_loudnorm_TP())
        self.loudnorm_TP.valueChanged.connect(self._on_loudnorm_value_changed)
        loud_form.addRow("Loudnorm true peak TP (dBTP):", self.loudnorm_TP)
        self.loudnorm_LRA = QDoubleSpinBox()
        self.loudnorm_LRA.setRange(1.0, 20.0)
        self.loudnorm_LRA.setDecimals(1)
        self.loudnorm_LRA.setSingleStep(0.5)
        self.loudnorm_LRA.setValue(config.get_audio_normalize_loudnorm_LRA())
        self.loudnorm_LRA.valueChanged.connect(self._on_loudnorm_value_changed)
        loud_form.addRow("Loudnorm loudness range LRA:", self.loudnorm_LRA)
        v.addLayout(loud_form)
        self._sync_loudnorm_spin_enabled()
        return g

    def _on_norm_enabled_changed(self, checked: bool) -> None:
        config.set_audio_normalize_enabled(checked)
        self._sync_loudnorm_spin_enabled()

    def _on_loudnorm_value_changed(self, _v: float) -> None:
        config.set_audio_normalize_loudnorm_I(self.loudnorm_I.value())
        config.set_audio_normalize_loudnorm_TP(self.loudnorm_TP.value())
        config.set_audio_normalize_loudnorm_LRA(self.loudnorm_LRA.value())

    def _sync_loudnorm_spin_enabled(self) -> None:
        enabled = self.norm_cb.isChecked()
        self.loudnorm_I.setEnabled(enabled)
        self.loudnorm_TP.setEnabled(enabled)
        self.loudnorm_LRA.setEnabled(enabled)

    def _persist_mode(self) -> None:
        config.set_encoding_mode("parallel" if self._m_par.isChecked() else "sequential")

    def reload_from_config(self) -> None:
        """Refresh widgets from config (when user opens this tab)."""
        self.strip_spin.blockSignals(True)
        self.strip_spin.setValue(config.get_strip_leading_path_segments())
        self.strip_spin.blockSignals(False)
        if config.get_output_destination() == "custom_folder":
            self._files_radio_custom.setChecked(True)
        else:
            self._files_radio_input.setChecked(True)
        self.default_output_folder_entry.blockSignals(True)
        self.default_output_folder_entry.setText(config.get_default_output_folder())
        self.default_output_folder_entry.blockSignals(False)
        self._sync_default_output_folder_widgets()
        self.loudnorm_I.blockSignals(True)
        self.loudnorm_TP.blockSignals(True)
        self.loudnorm_LRA.blockSignals(True)
        self.loudnorm_I.setValue(config.get_audio_normalize_loudnorm_I())
        self.loudnorm_TP.setValue(config.get_audio_normalize_loudnorm_TP())
        self.loudnorm_LRA.setValue(config.get_audio_normalize_loudnorm_LRA())
        self.loudnorm_I.blockSignals(False)
        self.loudnorm_TP.blockSignals(False)
        self.loudnorm_LRA.blockSignals(False)
        self.norm_cb.setChecked(config.get_audio_normalize_enabled())
        self._sync_loudnorm_spin_enabled()

    def _executable_path_warnings(self) -> List[str]:
        issues: List[str] = []
        checks = [
            ("FFmpeg", self.ffmpeg_entry.text().strip()),
            ("HandBrake CLI", self.handbrake_entry.text().strip()),
            ("mkvinfo", self.mkvinfo_entry.text().strip()),
            ("MediaInfo", self.mediainfo_entry.text().strip()),
        ]
        for label, path in checks:
            if not path:
                continue
            p = Path(path)
            if not p.is_file():
                issues.append(f"{label}: not a file or not found:\n{path}")
        return issues

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
            config.set_strip_leading_path_segments(self.strip_spin.value())
            config.set_default_output_folder(self.default_output_folder_entry.text().strip())
            config.set_encoding_mode("parallel" if self._m_par.isChecked() else "sequential")
            config.set_skip_existing(self.skip_cb.isChecked())
            config.set_debug_logging(self.debug_cb.isChecked())
            config.set_audio_normalize_enabled(self.norm_cb.isChecked())
            config.set_audio_normalize_loudnorm_I(self.loudnorm_I.value())
            config.set_audio_normalize_loudnorm_TP(self.loudnorm_TP.value())
            config.set_audio_normalize_loudnorm_LRA(self.loudnorm_LRA.value())
            mw = self.main_window
            if mw is not None and hasattr(mw, "refresh_encoder_clients"):
                mw.refresh_encoder_clients()
            if mw is not None and hasattr(mw, "ffmpeg_tab"):
                ft = mw.ffmpeg_tab
                ft.apply_audio_normalize_settings_from_config()
                ft._refresh_preset_command_after_loudnorm()
            warnings = self._executable_path_warnings()
            if warnings:
                QMessageBox.warning(
                    self,
                    "Saved — check paths",
                    "Settings were saved.\n\n"
                    + "\n\n".join(warnings)
                    + "\n\nEmpty paths are OK if the tool is on PATH.",
                )
            else:
                QMessageBox.information(self, "Saved", "All settings saved.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
