"""HandBrake Settings tab (PyQt6) — comprehensive encoding configuration without preset files."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .ffmpeg_command_util import ffmpeg_preview_to_html
from .handbrake_command_util import generate_hb_command_preview
from core.handbrake_command_builder import HandBrakeCommandBuilder
from core.preset_parser import PresetParser
from core.subprocess_utils import get_subprocess_kwargs
from utils.config import config


class HandBrakeSettingsTab(QWidget):
    """Configure HandBrakeCLI encoding with UI controls — no preset file required."""

    main_window: Any = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.source_file: Optional[Path] = None
        self._source_resolution: Optional[tuple] = None
        self._detected_audio_codec: Optional[str] = None
        self._builder = HandBrakeCommandBuilder()
        self.get_files_callback: Optional[Callable] = None
        self.get_output_path_callback: Optional[Callable] = None

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(inner)

        root.addWidget(self._preset_group())
        root.addWidget(self._video_encoding_group())
        root.addWidget(self._resolution_group())
        root.addWidget(self._audio_group())
        root.addWidget(self._filters_group())
        root.addWidget(self._framerate_group())
        root.addWidget(self._container_group())
        root.addWidget(self._subtitle_group())
        root.addWidget(self._command_preview_group())
        root.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        self._load_widgets_from_config()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_files_changed(self) -> None:
        self._schedule_preview()

    def _schedule_preview(self) -> None:
        self._preview_timer.start(250)

    # ------------------------------------------------------------------
    # Group builders
    # ------------------------------------------------------------------

    def _preset_group(self) -> QGroupBox:
        group = QGroupBox("Preset Selection (optional)")
        layout = QFormLayout()

        load_btn = QPushButton("Load HandBrake Preset...")
        load_btn.setToolTip("Optionally load a HandBrake JSON preset to populate defaults")
        load_btn.clicked.connect(self._load_preset)
        layout.addRow("", load_btn)

        self.quality_preset_combo = QComboBox()
        self.quality_preset_combo.addItem("Balanced (CRF 28, medium speed)", "balanced")
        self.quality_preset_combo.addItem("Quality (CRF 24, slow)", "quality")
        self.quality_preset_combo.addItem("Compact (CRF 32, faster)", "compact")
        current = config.get_encoder_quality_preset()
        idx = self.quality_preset_combo.findData(current)
        if idx >= 0:
            self.quality_preset_combo.setCurrentIndex(idx)
        self.quality_preset_combo.currentIndexChanged.connect(self._on_quality_preset_changed)
        layout.addRow("Quality Preset:", self.quality_preset_combo)

        self.source_label = QLabel("(No source file selected)")
        layout.addRow("Source File:", self.source_label)

        group.setLayout(layout)
        return group

    def _video_encoding_group(self) -> QGroupBox:
        group = QGroupBox("Video Encoding")
        layout = QFormLayout()

        self.encoder_combo = QComboBox()
        for label, data in [
            ("H.264 (x264)", "x264"),
            ("H.265 (x265)", "x265"),
            ("H.264 NVENC", "nvenc_h264"),
            ("H.265 NVENC", "nvenc_h265"),
            ("H.264 VideoToolbox", "vt_h264"),
            ("H.265 VideoToolbox", "vt_h265"),
        ]:
            self.encoder_combo.addItem(label, data)
        self.encoder_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Video Encoder:", self.encoder_combo)

        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(0, 51)
        self.quality_spin.setValue(22)
        self.quality_spin.setToolTip("Lower = better quality, larger files (0-51)")
        self.quality_spin.valueChanged.connect(self._on_setting_changed)
        layout.addRow("Quality (RF):", self.quality_spin)

        self.speed_combo = QComboBox()
        for label, data in [
            ("Ultrafast", "ultrafast"),
            ("Superfast", "superfast"),
            ("Veryfast", "veryfast"),
            ("Faster", "faster"),
            ("Fast", "fast"),
            ("Medium", "medium"),
            ("Slow", "slow"),
            ("Slower", "slower"),
            ("Veryslow", "veryslow"),
            ("Placebo", "placebo"),
        ]:
            self.speed_combo.addItem(label, data)
        self.speed_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Encoder Preset:", self.speed_combo)

        self.profile_combo = QComboBox()
        for label, data in [
            ("Auto", "auto"),
            ("Baseline", "baseline"),
            ("Main", "main"),
            ("Main10 (10-bit)", "main10"),
            ("High", "high"),
        ]:
            self.profile_combo.addItem(label, data)
        self.profile_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Profile:", self.profile_combo)

        self.level_combo = QComboBox()
        self.level_combo.addItem("Auto", "auto")
        for lv in ["3.0", "3.1", "3.2", "4.0", "4.1", "4.2", "5.0", "5.1", "5.2", "6.0", "6.1", "6.2"]:
            self.level_combo.addItem(lv, lv)
        self.level_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Level:", self.level_combo)

        self.tune_combo = QComboBox()
        for label, data in [
            ("None", "none"),
            ("Film", "film"),
            ("Animation", "animation"),
            ("Grain", "grain"),
            ("Still Image", "stillimage"),
            ("PSNR", "psnr"),
            ("SSIM", "ssim"),
            ("Fast Decode", "fastdecode"),
            ("Zero Latency", "zerolatency"),
        ]:
            self.tune_combo.addItem(label, data)
        self.tune_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Tune:", self.tune_combo)

        group.setLayout(layout)
        return group

    def _resolution_group(self) -> QGroupBox:
        group = QGroupBox("Resolution")
        layout = QFormLayout()

        self.width_spin = QSpinBox()
        self.width_spin.setRange(0, 7680)
        self.width_spin.setSpecialValueText("Auto")
        self.width_spin.setToolTip("0 = automatic (let HandBrake decide)")
        self.width_spin.valueChanged.connect(self._on_setting_changed)
        layout.addRow("Width:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(0, 7680)
        self.height_spin.setSpecialValueText("Auto")
        self.height_spin.setToolTip("0 = automatic (let HandBrake decide)")
        self.height_spin.valueChanged.connect(self._on_setting_changed)
        layout.addRow("Height:", self.height_spin)

        self.max_width_spin = QSpinBox()
        self.max_width_spin.setRange(16, 7680)
        self.max_width_spin.setValue(1920)
        self.max_width_spin.setToolTip("Cap width (--maxWidth)")
        self.max_width_spin.valueChanged.connect(self._on_setting_changed)
        layout.addRow("Max Width:", self.max_width_spin)

        self.max_height_spin = QSpinBox()
        self.max_height_spin.setRange(16, 7680)
        self.max_height_spin.setValue(1080)
        self.max_height_spin.setToolTip("Cap height (--maxHeight)")
        self.max_height_spin.valueChanged.connect(self._on_setting_changed)
        layout.addRow("Max Height:", self.max_height_spin)

        self.crop_combo = QComboBox()
        self.crop_combo.addItem("Auto (HandBrake detects)", "auto")
        self.crop_combo.addItem("Disabled (no crop)", "disabled")
        self.crop_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Crop:", self.crop_combo)

        self.resolution_label = QLabel("(Auto-detect)")
        layout.addRow("Source:", self.resolution_label)

        group.setLayout(layout)
        return group

    def _audio_group(self) -> QGroupBox:
        group = QGroupBox("Audio")
        layout = QFormLayout()

        self.audio_encoder_combo = QComboBox()
        for label, data in [
            ("AAC (av_aac)", "av_aac"),
            ("Copy (passthrough)", "copy"),
            ("AC3", "ac3"),
            ("E-AC3", "eac3"),
            ("Opus", "opus"),
            ("FLAC", "flac"),
            ("MP3", "mp3"),
        ]:
            self.audio_encoder_combo.addItem(label, data)
        self.audio_encoder_combo.currentIndexChanged.connect(self._on_audio_encoder_changed)
        layout.addRow("Audio Encoder:", self.audio_encoder_combo)

        self.audio_bitrate_spin = QSpinBox()
        self.audio_bitrate_spin.setRange(32, 640)
        self.audio_bitrate_spin.setValue(160)
        self.audio_bitrate_spin.setSuffix(" kbps")
        self.audio_bitrate_spin.valueChanged.connect(self._on_setting_changed)
        layout.addRow("Bitrate:", self.audio_bitrate_spin)

        self.mixdown_combo = QComboBox()
        for label, data in [
            ("Mono", "mono"),
            ("Stereo", "stereo"),
            ("5.1 Surround", "5point1"),
            ("6.1 Surround", "6point1"),
            ("7.1 Surround", "7point1"),
        ]:
            self.mixdown_combo.addItem(label, data)
        self.mixdown_combo.setCurrentIndex(1)  # stereo
        self.mixdown_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Mixdown:", self.mixdown_combo)

        self.audio_info_label = QLabel("(No source file selected)")
        layout.addRow("Source Audio:", self.audio_info_label)

        group.setLayout(layout)
        return group

    def _filters_group(self) -> QGroupBox:
        group = QGroupBox("Filters (HandBrake-specific)")
        layout = QFormLayout()

        self.deinterlace_combo = QComboBox()
        for label, data in [
            ("Off", "off"),
            ("Default", "default"),
            ("Skip Spatial", "skip-spatial"),
            ("Bob", "bob"),
        ]:
            self.deinterlace_combo.addItem(label, data)
        self.deinterlace_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Deinterlace:", self.deinterlace_combo)

        self.detelecine_combo = QComboBox()
        self.detelecine_combo.addItem("Off", "off")
        self.detelecine_combo.addItem("Default", "default")
        self.detelecine_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Detelecine:", self.detelecine_combo)

        self.denoise_combo = QComboBox()
        self.denoise_combo.addItem("Off", "off")
        self.denoise_combo.addItem("NLMeans", "nlmeans")
        self.denoise_combo.addItem("HQDN3D", "hqdn3d")
        self.denoise_combo.currentIndexChanged.connect(self._on_denoise_changed)
        layout.addRow("Denoise:", self.denoise_combo)

        self.denoise_preset_combo = QComboBox()
        for label, data in [
            ("Ultralight", "ultralight"),
            ("Light", "light"),
            ("Medium", "medium"),
            ("Strong", "strong"),
        ]:
            self.denoise_preset_combo.addItem(label, data)
        self.denoise_preset_combo.setCurrentIndex(2)  # medium
        self.denoise_preset_combo.setEnabled(False)
        self.denoise_preset_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Denoise Strength:", self.denoise_preset_combo)

        self.sharpen_combo = QComboBox()
        self.sharpen_combo.addItem("Off", "off")
        self.sharpen_combo.addItem("Unsharp", "unsharp")
        self.sharpen_combo.addItem("Lapsharp", "lapsharp")
        self.sharpen_combo.currentIndexChanged.connect(self._on_sharpen_changed)
        layout.addRow("Sharpen:", self.sharpen_combo)

        self.sharpen_preset_combo = QComboBox()
        for label, data in [
            ("Ultralight", "ultralight"),
            ("Light", "light"),
            ("Medium", "medium"),
            ("Strong", "strong"),
        ]:
            self.sharpen_preset_combo.addItem(label, data)
        self.sharpen_preset_combo.setCurrentIndex(2)  # medium
        self.sharpen_preset_combo.setEnabled(False)
        self.sharpen_preset_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Sharpen Strength:", self.sharpen_preset_combo)

        self.chromasmooth_combo = QComboBox()
        for label, data in [
            ("Off", "off"),
            ("Ultralight", "ultralight"),
            ("Light", "light"),
            ("Medium", "medium"),
            ("Strong", "strong"),
            ("Stronger", "stronger"),
            ("Very Strong", "verystrong"),
        ]:
            self.chromasmooth_combo.addItem(label, data)
        self.chromasmooth_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Chromasmooth:", self.chromasmooth_combo)

        self.grayscale_cb = QCheckBox("Convert to grayscale")
        self.grayscale_cb.stateChanged.connect(self._on_setting_changed)
        layout.addRow("", self.grayscale_cb)

        group.setLayout(layout)
        return group

    def _framerate_group(self) -> QGroupBox:
        group = QGroupBox("Framerate")
        layout = QFormLayout()

        self.framerate_combo = QComboBox()
        self.framerate_combo.addItem("Same as source", "auto")
        for rate in ["5", "10", "12", "15", "23.976", "24", "25", "29.97", "30", "48", "50", "59.94", "60"]:
            self.framerate_combo.addItem(f"{rate} fps", rate)
        self.framerate_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Framerate:", self.framerate_combo)

        self.framerate_mode_combo = QComboBox()
        self.framerate_mode_combo.addItem("Peak (PFR) — recommended", "pfr")
        self.framerate_mode_combo.addItem("Constant (CFR)", "cfr")
        self.framerate_mode_combo.addItem("Variable (VFR)", "vfr")
        self.framerate_mode_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Mode:", self.framerate_mode_combo)

        group.setLayout(layout)
        return group

    def _container_group(self) -> QGroupBox:
        group = QGroupBox("Container / Output")
        layout = QFormLayout()

        self.format_combo = QComboBox()
        self.format_combo.addItem("MP4", "av_mp4")
        self.format_combo.addItem("MKV", "av_mkv")
        self.format_combo.addItem("WebM", "av_webm")
        self.format_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addRow("Format:", self.format_combo)

        self.optimize_cb = QCheckBox("Web optimize (moov atom at start)")
        self.optimize_cb.setChecked(True)
        self.optimize_cb.stateChanged.connect(self._on_setting_changed)
        layout.addRow("", self.optimize_cb)

        self.markers_cb = QCheckBox("Include chapter markers")
        self.markers_cb.setChecked(True)
        self.markers_cb.stateChanged.connect(self._on_setting_changed)
        layout.addRow("", self.markers_cb)

        group.setLayout(layout)
        return group

    def _subtitle_group(self) -> QGroupBox:
        group = QGroupBox("Subtitle Handling")
        layout = QFormLayout()

        sub_config = config.get("subtitle_handling", {})

        self.pgs_combo = QComboBox()
        self.pgs_combo.addItem("Omit subtitles", "omit")
        self.pgs_combo.addItem("Skip file", "skip_file")
        self.pgs_combo.addItem("Burn into video", "burn")
        current_pgs = sub_config.get("pgs", "omit")
        idx = self.pgs_combo.findData(current_pgs)
        if idx >= 0:
            self.pgs_combo.setCurrentIndex(idx)
        layout.addRow("PGS (bitmap):", self.pgs_combo)

        self.text_sub_combo = QComboBox()
        self.text_sub_combo.addItem("Burn into video", "burn")
        self.text_sub_combo.addItem("Omit", "omit")
        current_text = sub_config.get("embedded_text", "burn")
        idx = self.text_sub_combo.findData(current_text)
        if idx >= 0:
            self.text_sub_combo.setCurrentIndex(idx)
        layout.addRow("Text Subs (SRT):", self.text_sub_combo)

        self.ass_sub_combo = QComboBox()
        self.ass_sub_combo.addItem("Burn into video", "burn")
        self.ass_sub_combo.addItem("Omit", "omit")
        current_ass = sub_config.get("embedded_ass", "burn")
        idx = self.ass_sub_combo.findData(current_ass)
        if idx >= 0:
            self.ass_sub_combo.setCurrentIndex(idx)
        layout.addRow("ASS (styled):", self.ass_sub_combo)

        group.setLayout(layout)
        return group

    def _command_preview_group(self) -> QGroupBox:
        group = QGroupBox("HandBrakeCLI Command Preview")
        layout = QVBoxLayout()

        self.command_preview = QTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setMaximumHeight(150)
        layout.addWidget(self.command_preview)

        copy_btn = QPushButton("Copy Command")
        copy_btn.clicked.connect(self._copy_command)
        layout.addWidget(copy_btn)

        group.setLayout(layout)
        return group

    # ------------------------------------------------------------------
    # Config ↔ widget sync
    # ------------------------------------------------------------------

    def _load_widgets_from_config(self) -> None:
        """Populate widgets from persisted config (block signals to avoid feedback loops)."""
        widgets = [
            self.encoder_combo, self.quality_spin, self.speed_combo,
            self.profile_combo, self.level_combo, self.tune_combo,
            self.width_spin, self.height_spin, self.max_width_spin, self.max_height_spin,
            self.crop_combo, self.audio_encoder_combo, self.audio_bitrate_spin,
            self.mixdown_combo, self.format_combo, self.optimize_cb, self.markers_cb,
            self.deinterlace_combo, self.detelecine_combo, self.denoise_combo,
            self.denoise_preset_combo, self.sharpen_combo, self.sharpen_preset_combo,
            self.chromasmooth_combo, self.grayscale_cb,
            self.framerate_combo, self.framerate_mode_combo,
        ]
        for w in widgets:
            w.blockSignals(True)

        try:
            self._set_combo(self.encoder_combo, config.get_hb_encoder())
            self.quality_spin.setValue(config.get_hb_quality())
            self._set_combo(self.speed_combo, config.get_hb_encoder_preset())
            self._set_combo(self.profile_combo, config.get_hb_encoder_profile())
            self._set_combo(self.level_combo, config.get_hb_encoder_level())
            self._set_combo(self.tune_combo, config.get_hb_encoder_tune())
            self.width_spin.setValue(config.get_hb_width())
            self.height_spin.setValue(config.get_hb_height())
            self.max_width_spin.setValue(config.get_hb_max_width())
            self.max_height_spin.setValue(config.get_hb_max_height())
            self._set_combo(self.crop_combo, config.get_hb_crop_mode())
            self._set_combo(self.audio_encoder_combo, config.get_hb_audio_encoder())
            self.audio_bitrate_spin.setValue(config.get_hb_audio_bitrate())
            self._set_combo(self.mixdown_combo, config.get_hb_audio_mixdown())
            self._set_combo(self.format_combo, config.get_hb_format())
            self.optimize_cb.setChecked(config.get_hb_optimize())
            self.markers_cb.setChecked(config.get_hb_markers())
            self._set_combo(self.deinterlace_combo, config.get_hb_deinterlace())
            self._set_combo(self.detelecine_combo, config.get_hb_detelecine())
            self._set_combo(self.denoise_combo, config.get_hb_denoise())
            self._set_combo(self.denoise_preset_combo, config.get_hb_denoise_preset())
            self._set_combo(self.sharpen_combo, config.get_hb_sharpen())
            self._set_combo(self.sharpen_preset_combo, config.get_hb_sharpen_preset())
            self._set_combo(self.chromasmooth_combo, config.get_hb_chromasmooth())
            self.grayscale_cb.setChecked(config.get_hb_grayscale())
            self._set_combo(self.framerate_combo, config.get_hb_framerate())
            self._set_combo(self.framerate_mode_combo, config.get_hb_framerate_mode())

            # Enable/disable dependent widgets
            self.denoise_preset_combo.setEnabled(self.denoise_combo.currentData() != "off")
            self.sharpen_preset_combo.setEnabled(self.sharpen_combo.currentData() != "off")
            is_copy = self.audio_encoder_combo.currentData() == "copy"
            self.audio_bitrate_spin.setEnabled(not is_copy)
            self.mixdown_combo.setEnabled(not is_copy)
        finally:
            for w in widgets:
                w.blockSignals(False)

    @staticmethod
    def _set_combo(combo: QComboBox, value: str) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _persist_settings(self) -> None:
        """Write current widget values to config."""
        config.set_hb_encoder(self.encoder_combo.currentData() or "x264")
        config.set_hb_quality(self.quality_spin.value())
        config.set_hb_encoder_preset(self.speed_combo.currentData() or "medium")
        config.set_hb_encoder_profile(self.profile_combo.currentData() or "auto")
        config.set_hb_encoder_level(self.level_combo.currentData() or "auto")
        config.set_hb_encoder_tune(self.tune_combo.currentData() or "none")
        config.set_hb_width(self.width_spin.value())
        config.set_hb_height(self.height_spin.value())
        config.set_hb_max_width(self.max_width_spin.value())
        config.set_hb_max_height(self.max_height_spin.value())
        config.set_hb_crop_mode(self.crop_combo.currentData() or "auto")
        config.set_hb_audio_encoder(self.audio_encoder_combo.currentData() or "av_aac")
        config.set_hb_audio_bitrate(self.audio_bitrate_spin.value())
        config.set_hb_audio_mixdown(self.mixdown_combo.currentData() or "stereo")
        config.set_hb_format(self.format_combo.currentData() or "av_mp4")
        config.set_hb_optimize(self.optimize_cb.isChecked())
        config.set_hb_markers(self.markers_cb.isChecked())
        config.set_hb_deinterlace(self.deinterlace_combo.currentData() or "off")
        config.set_hb_detelecine(self.detelecine_combo.currentData() or "off")
        config.set_hb_denoise(self.denoise_combo.currentData() or "off")
        config.set_hb_denoise_preset(self.denoise_preset_combo.currentData() or "medium")
        config.set_hb_sharpen(self.sharpen_combo.currentData() or "off")
        config.set_hb_sharpen_preset(self.sharpen_preset_combo.currentData() or "medium")
        config.set_hb_chromasmooth(self.chromasmooth_combo.currentData() or "off")
        config.set_hb_grayscale(self.grayscale_cb.isChecked())
        config.set_hb_framerate(self.framerate_combo.currentData() or "auto")
        config.set_hb_framerate_mode(self.framerate_mode_combo.currentData() or "pfr")

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _on_setting_changed(self) -> None:
        self._persist_settings()
        self._schedule_preview()

    def _on_quality_preset_changed(self) -> None:
        preset_key = self.quality_preset_combo.currentData()
        if not preset_key:
            return
        config.set_encoder_quality_preset(preset_key)
        crf = config.get_quality_preset_crf(preset_key)
        speed = config.get_quality_preset_speed(preset_key)

        self.quality_spin.blockSignals(True)
        self.speed_combo.blockSignals(True)
        self.quality_spin.setValue(crf)
        self._set_combo(self.speed_combo, speed)
        self.quality_spin.blockSignals(False)
        self.speed_combo.blockSignals(False)

        self._persist_settings()
        self._schedule_preview()

    def _on_audio_encoder_changed(self) -> None:
        is_copy = self.audio_encoder_combo.currentData() == "copy"
        self.audio_bitrate_spin.setEnabled(not is_copy)
        self.mixdown_combo.setEnabled(not is_copy)
        self._on_setting_changed()

    def _on_denoise_changed(self) -> None:
        self.denoise_preset_combo.setEnabled(self.denoise_combo.currentData() != "off")
        self._on_setting_changed()

    def _on_sharpen_changed(self) -> None:
        self.sharpen_preset_combo.setEnabled(self.sharpen_combo.currentData() != "off")
        self._on_setting_changed()

    # ------------------------------------------------------------------
    # Preset loading (optional — populates fields)
    # ------------------------------------------------------------------

    def _load_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select HandBrake preset JSON", "", "JSON files (*.json);;All (*.*)"
        )
        if not path:
            return
        try:
            parser = PresetParser(Path(path))
            self._apply_preset(parser)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to load preset: {e}")

    def _apply_preset(self, parser: PresetParser) -> None:
        """Populate UI widgets from a parsed HandBrake preset."""
        encoder_map = {"x264": "x264", "x265": "x265"}
        raw_enc = parser.get_video_encoder()
        enc = encoder_map.get(raw_enc, raw_enc)
        self._set_combo(self.encoder_combo, enc)

        self.quality_spin.setValue(parser.get_video_quality())
        self._set_combo(self.speed_combo, parser.get_video_preset())
        self._set_combo(self.profile_combo, parser.get_video_profile())
        self._set_combo(self.level_combo, parser.get_video_level())

        tw, th = parser.get_video_resolution()
        self.max_width_spin.setValue(max(16, min(7680, int(tw))))
        self.max_height_spin.setValue(max(16, min(7680, int(th))))

        self._set_combo(self.audio_encoder_combo, parser.get_audio_encoder())
        self.audio_bitrate_spin.setValue(parser.get_audio_bitrate())
        self._set_combo(self.mixdown_combo, parser.get_audio_mixdown())

        fmt = parser.get_file_format()
        self._set_combo(self.format_combo, fmt)
        self.optimize_cb.setChecked(parser.get_optimize())
        self.markers_cb.setChecked(parser.get_chapter_markers())

        self._persist_settings()
        self._schedule_preview()

    # ------------------------------------------------------------------
    # Source file detection
    # ------------------------------------------------------------------

    def set_source_file(self, file_path: Path) -> None:
        self.source_file = file_path
        self.source_label.setText(file_path.name)
        try:
            info = self._get_ffprobe_info(file_path)
            streams = info.get("streams", [])
            video = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
            if video:
                w, h = video.get("width"), video.get("height")
                if w and h:
                    self.resolution_label.setText(f"{w}x{h}")
                    self._source_resolution = (w, h)
                else:
                    self.resolution_label.setText("(Unable to detect)")
            if audio:
                codec = audio.get("codec_name", "Unknown")
                self.audio_info_label.setText(codec.upper())
                self._detected_audio_codec = codec.lower()
            else:
                self.audio_info_label.setText("No audio detected")
        except Exception:
            self.resolution_label.setText("(Error)")
            self.audio_info_label.setText("(Error)")
        self._schedule_preview()

    def _get_ffprobe_info(self, file_path: Path) -> Dict[str, Any]:
        from utils.ffmpeg_paths import resolve_ffprobe_path
        ffprobe = resolve_ffprobe_path()
        if not ffprobe:
            return {}
        try:
            cmd = [
                ffprobe, "-v", "error",
                "-show_entries", "stream=width,height,codec_name,codec_type",
                "-of", "json", str(file_path),
            ]
            run_kw = {"args": cmd, "capture_output": True, "text": True, "timeout": 10}
            run_kw.update(get_subprocess_kwargs())
            result = subprocess.run(**run_kw)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return {}

    # ------------------------------------------------------------------
    # Command preview
    # ------------------------------------------------------------------

    def get_settings_dict(self) -> Dict[str, Any]:
        """Return current UI settings as a dict for HandBrakeCommandBuilder."""
        return config.get_hb_encoding_settings()

    def get_output_extension(self) -> str:
        fmt = self.format_combo.currentData() or "av_mp4"
        return {
            "av_mp4": ".mp4",
            "av_mkv": ".mkv",
            "av_webm": ".webm",
        }.get(fmt, ".mp4")

    def _update_preview(self) -> None:
        settings = self.get_settings_dict()
        template = self._builder.build_template(settings, include_subtitle=True)
        output_ext = self.get_output_extension()

        suffix = config.get_default_output_suffix()
        preview_text = generate_hb_command_preview(
            command_template=template,
            get_files_callback=self.get_files_callback,
            get_output_path_callback=self.get_output_path_callback,
            suffix=suffix,
            output_extension=output_ext,
        )
        self.command_preview.setHtml(ffmpeg_preview_to_html(preview_text))
        # Store plain text for copy
        self._plain_preview = preview_text

    def _copy_command(self) -> None:
        text = getattr(self, "_plain_preview", "") or self.command_preview.toPlainText()
        if text and not text.startswith("No "):
            QGuiApplication.clipboard().setText(text)
