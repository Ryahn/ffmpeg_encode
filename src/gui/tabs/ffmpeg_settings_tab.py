"""FFmpeg Settings tab (PyQt6) - Comprehensive encoding configuration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Optional, Dict

from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from core.preset_parser import PresetParser
from core.ffmpeg_translator import FFmpegTranslator
from core.track_analyzer import TrackAnalyzer
from utils.config import config


class FFmpegSettingsTab(QWidget):
    """Configure FFmpeg encoding with preset selection and smart detection."""

    main_window: Any = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.preset_path: Optional[Path] = None
        self.source_file: Optional[Path] = None
        self.media_info: Dict[str, Any] = {}
        self.track_analyzer = TrackAnalyzer()
        self._detected_audio_codec: Optional[str] = None
        self._source_resolution: Optional[tuple] = None

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(inner)

        root.addWidget(self._preset_group())
        root.addWidget(self._video_encoding_group())
        root.addWidget(self._audio_group())
        root.addWidget(self._subtitle_group())
        root.addWidget(self._command_preview_group())
        root.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

    def _preset_group(self) -> QGroupBox:
        """Preset selection and detection."""
        group = QGroupBox("Preset Selection")
        layout = QFormLayout()

        # Preset selector
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("-- None --", None)
        self.preset_combo.addItem("AppleTV 1080p30 Auto", "appletv_1080p30.json")
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        layout.addRow("Preset:", self.preset_combo)

        # Quality preset selector
        self.quality_preset_combo = QComboBox()
        self.quality_preset_combo.addItem("Balanced (CRF 28, medium speed)", "balanced")
        self.quality_preset_combo.addItem("Quality (CRF 24, slow)", "quality")
        self.quality_preset_combo.addItem("Compact (CRF 32, faster)", "compact")

        current_preset = config.get_encoder_quality_preset()
        if current_preset in ["balanced", "quality", "compact"]:
            self.quality_preset_combo.setCurrentText(
                self.quality_preset_combo.itemText(
                    self.quality_preset_combo.findData(current_preset)
                )
            )
        self.quality_preset_combo.currentIndexChanged.connect(self._update_preview)
        layout.addRow("Quality Preset:", self.quality_preset_combo)

        # Source file detection
        self.source_label = QLabel("(No source file selected)")
        layout.addRow("Source File:", self.source_label)

        group.setLayout(layout)
        return group

    def _video_encoding_group(self) -> QGroupBox:
        """Video codec and quality settings."""
        group = QGroupBox("Video Encoding")
        layout = QFormLayout()

        # Video codec
        self.codec_combo = QComboBox()
        self.codec_combo.addItem("HEVC (hevc_nvenc)", "hevc_nvenc")
        self.codec_combo.addItem("H.264 (h264_nvenc)", "h264_nvenc")
        self.codec_combo.addItem("H.264 CPU (libx264)", "libx264")
        self.codec_combo.addItem("HEVC CPU (libx265)", "libx265")
        self.codec_combo.setCurrentIndex(0)  # Default to HEVC
        self.codec_combo.currentIndexChanged.connect(self._update_preview)
        layout.addRow("Video Codec:", self.codec_combo)

        # CRF (Quality)
        self.crf_spinbox = QSpinBox()
        self.crf_spinbox.setRange(0, 51)
        self.crf_spinbox.setValue(28)
        self.crf_spinbox.setToolTip("Lower = better quality, larger files (0-51)")
        self.crf_spinbox.valueChanged.connect(self._update_preview)
        layout.addRow("Quality (CRF):", self.crf_spinbox)

        # Preset (Speed)
        self.speed_combo = QComboBox()
        self.speed_combo.addItem("Slow (best quality)", "slow")
        self.speed_combo.addItem("Medium", "medium")
        self.speed_combo.addItem("Fast", "fast")
        self.speed_combo.addItem("Faster (NVENC p4)", "p4")
        self.speed_combo.addItem("Balanced (NVENC p5)", "p5")
        self.speed_combo.addItem("Quality (NVENC p6)", "p6")
        self.speed_combo.setCurrentIndex(4)  # Default to p5
        self.speed_combo.currentIndexChanged.connect(self._update_preview)
        layout.addRow("Speed Preset:", self.speed_combo)

        # Resolution handling
        self.resolution_label = QLabel("(Auto-detect)")
        layout.addRow("Resolution:", self.resolution_label)

        self.upscale_checkbox = QCheckBox("Allow upscaling to 1080p")
        self.upscale_checkbox.setChecked(False)
        self.upscale_checkbox.stateChanged.connect(self._update_preview)
        layout.addRow("", self.upscale_checkbox)

        # Profile and level
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("main", "main")
        self.profile_combo.addItem("main10 (10-bit)", "main10")
        self.profile_combo.setCurrentIndex(0)
        self.profile_combo.currentIndexChanged.connect(self._update_preview)
        layout.addRow("Profile:", self.profile_combo)

        self.level_combo = QComboBox()
        self.level_combo.addItem("4.1", "4.1")
        self.level_combo.addItem("4.0", "4.0")
        self.level_combo.addItem("5.0", "5.0")
        self.level_combo.setCurrentIndex(0)
        self.level_combo.currentIndexChanged.connect(self._update_preview)
        layout.addRow("Level:", self.level_combo)

        group.setLayout(layout)
        return group

    def _audio_group(self) -> QGroupBox:
        """Audio codec detection and settings."""
        group = QGroupBox("Audio Handling")
        layout = QFormLayout()

        # Auto-copy checkbox
        self.audio_auto_copy_checkbox = QCheckBox("Auto-copy audio codec if compatible")
        self.audio_auto_copy_checkbox.setChecked(True)
        self.audio_auto_copy_checkbox.setToolTip(
            "If source audio codec matches output container, copy instead of re-encode"
        )
        self.audio_auto_copy_checkbox.stateChanged.connect(self._update_preview)
        layout.addRow("", self.audio_auto_copy_checkbox)

        # Detected audio info
        self.audio_info_label = QLabel("(No source file selected)")
        layout.addRow("Source Audio:", self.audio_info_label)

        # Fallback codec
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItem("AAC (aac)", "aac")
        self.audio_codec_combo.addItem("MP3 (libmp3lame)", "libmp3lame")
        self.audio_codec_combo.addItem("Opus (libopus)", "libopus")
        self.audio_codec_combo.setCurrentIndex(0)
        self.audio_codec_combo.currentIndexChanged.connect(self._update_preview)
        layout.addRow("Fallback Codec:", self.audio_codec_combo)

        # Bitrate
        self.audio_bitrate_spinbox = QSpinBox()
        self.audio_bitrate_spinbox.setRange(64, 320)
        self.audio_bitrate_spinbox.setValue(160)
        self.audio_bitrate_spinbox.setSuffix(" kbps")
        self.audio_bitrate_spinbox.valueChanged.connect(self._update_preview)
        layout.addRow("Bitrate:", self.audio_bitrate_spinbox)

        group.setLayout(layout)
        return group

    def _subtitle_group(self) -> QGroupBox:
        """Subtitle handling options."""
        group = QGroupBox("Subtitle Handling")
        layout = QFormLayout()

        # Get current settings
        sub_config = config.get("subtitle_handling", {})

        # PGS handling
        self.pgs_combo = QComboBox()
        self.pgs_combo.addItem("Omit subtitles", "omit")
        self.pgs_combo.addItem("Skip file", "skip_file")
        self.pgs_combo.addItem("Burn into video", "burn")
        current_pgs = sub_config.get("pgs", "omit")
        self.pgs_combo.setCurrentText({
            "omit": "Omit subtitles",
            "skip_file": "Skip file",
            "burn": "Burn into video"
        }.get(current_pgs, "Omit subtitles"))
        layout.addRow("PGS (bitmap):", self.pgs_combo)

        # Text subtitles
        self.text_sub_combo = QComboBox()
        self.text_sub_combo.addItem("Mux into MP4", "mux")
        self.text_sub_combo.addItem("Burn into video", "burn")
        self.text_sub_combo.addItem("Omit", "omit")
        current_text = sub_config.get("embedded_text", "mux")
        self.text_sub_combo.setCurrentText({
            "mux": "Mux into MP4",
            "burn": "Burn into video",
            "omit": "Omit"
        }.get(current_text, "Mux into MP4"))
        layout.addRow("Text Subs (SRT):", self.text_sub_combo)

        # ASS subtitles
        self.ass_sub_combo = QComboBox()
        self.ass_sub_combo.addItem("Keep external", "external")
        self.ass_sub_combo.addItem("Mux into MP4", "mux")
        self.ass_sub_combo.addItem("Burn into video", "burn")
        self.ass_sub_combo.addItem("Omit", "omit")
        current_ass = sub_config.get("embedded_ass", "external")
        self.ass_sub_combo.setCurrentText({
            "external": "Keep external",
            "mux": "Mux into MP4",
            "burn": "Burn into video",
            "omit": "Omit"
        }.get(current_ass, "Keep external"))
        layout.addRow("ASS (styled):", self.ass_sub_combo)

        group.setLayout(layout)
        return group

    def _command_preview_group(self) -> QGroupBox:
        """FFmpeg command preview."""
        group = QGroupBox("FFmpeg Command Preview")
        layout = QVBoxLayout()

        self.command_text = QPlainTextEdit()
        self.command_text.setReadOnly(True)
        self.command_text.setMaximumHeight(150)
        layout.addWidget(self.command_text)

        # Copy button
        copy_btn = QPushButton("Copy Command")
        copy_btn.clicked.connect(self._copy_command)
        layout.addWidget(copy_btn)

        group.setLayout(layout)
        return group

    def _on_preset_changed(self) -> None:
        """Handle preset selection change."""
        preset_file = self.preset_combo.currentData()
        if preset_file:
            try:
                preset_path = Path(preset_file)
                if not preset_path.is_absolute():
                    preset_path = Path.cwd() / preset_path

                if preset_path.exists():
                    parser = PresetParser(preset_path)

                    # Update video settings from preset
                    encoder = parser.get_video_encoder()
                    if encoder == "x264":
                        self.codec_combo.setCurrentText("H.264 (h264_nvenc)")
                    elif encoder == "x265":
                        self.codec_combo.setCurrentText("HEVC (hevc_nvenc)")

                    self.crf_spinbox.setValue(parser.get_video_quality())

                    preset = parser.get_video_preset()
                    self.speed_combo.setCurrentText(preset)

                    self.profile_combo.setCurrentText(parser.get_video_profile())
                    self.level_combo.setCurrentText(parser.get_video_level())

                    self.audio_bitrate_spinbox.setValue(parser.get_audio_bitrate())

                    self.preset_path = preset_path
            except Exception as e:
                print(f"Error loading preset: {e}")

        self._update_preview()

    def _get_ffprobe_info(self, file_path: Path) -> Dict[str, Any]:
        """Get detailed media info using ffprobe."""
        from utils.ffmpeg_paths import resolve_ffprobe_path

        ffprobe = resolve_ffprobe_path()
        if not ffprobe:
            return {}

        try:
            cmd = [
                ffprobe,
                "-v", "error",
                "-show_entries", "stream=width,height,codec_name,codec_type",
                "-of", "json",
                str(file_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data
        except Exception as e:
            print(f"ffprobe error: {e}")

        return {}

    def set_source_file(self, file_path: Path) -> None:
        """Update source file and detect media properties."""
        self.source_file = file_path
        self.source_label.setText(file_path.name)

        # Detect media info using ffprobe
        try:
            ffprobe_data = self._get_ffprobe_info(file_path)
            streams = ffprobe_data.get("streams", [])

            # Find video stream
            video_stream = None
            audio_stream = None

            for stream in streams:
                if stream.get("codec_type") == "video" and not video_stream:
                    video_stream = stream
                elif stream.get("codec_type") == "audio" and not audio_stream:
                    audio_stream = stream

            # Update resolution
            if video_stream:
                width = video_stream.get("width")
                height = video_stream.get("height")

                if width and height:
                    self.resolution_label.setText(f"{width}x{height}")
                    self._source_resolution = (width, height)

                    # Disable upscaling if source is already >= 1080p
                    if height >= 1080:
                        self.upscale_checkbox.setEnabled(False)
                        self.upscale_checkbox.setChecked(False)
                    else:
                        self.upscale_checkbox.setEnabled(True)
                else:
                    self.resolution_label.setText("(Unable to detect)")
                    self._source_resolution = None
            else:
                self.resolution_label.setText("(Unable to detect)")
                self._source_resolution = None

            # Update audio info
            if audio_stream:
                codec = audio_stream.get("codec_name", "Unknown")
                audio_text = f"{codec.upper()}"
                self.audio_info_label.setText(audio_text)
                self._detected_audio_codec = codec.lower() if codec else None
            else:
                self.audio_info_label.setText("No audio detected")
                self._detected_audio_codec = None

        except Exception as e:
            print(f"Error detecting media info: {e}")
            self.audio_info_label.setText("(Error detecting)")
            self.resolution_label.setText("(Error detecting)")
            self._source_resolution = None
            self._detected_audio_codec = None

        self._update_preview()

    def _update_preview(self) -> None:
        """Update FFmpeg command preview with smart resolution handling."""
        if not self.source_file:
            self.command_text.setPlainText("(Select a source file and preset)")
            return

        try:
            # Build command based on current settings
            codec = self.codec_combo.currentData()
            crf = self.crf_spinbox.value()
            speed = self.speed_combo.currentData()
            profile = self.profile_combo.currentData()
            level = self.level_combo.currentData()

            # Smart resolution handling
            if self._source_resolution:
                src_width, src_height = self._source_resolution
            else:
                src_width, src_height = 1920, 1080

            # Determine target resolution
            if self.upscale_checkbox.isChecked():
                # User wants to scale to 1080p
                target_width, target_height = 1920, 1080
                scale_filter = "scale=1920:1080:force_original_aspect_ratio=decrease"
            else:
                # Smart resolution: keep source res if < 1080p, otherwise use 1080p
                if src_height <= 1080:
                    # Don't upscale - keep source resolution. Commas inside min() must be
                    # escaped (\,) or FFmpeg treats them as filter-chain separators.
                    scale_filter = (
                        f"scale=min(1920\\,{src_width}):min(1080\\,{src_height})"
                        f":force_original_aspect_ratio=decrease"
                    )
                    target_width, target_height = src_width, src_height
                else:
                    # Source is > 1080p, downscale to 1080p
                    target_width, target_height = 1920, 1080
                    scale_filter = "scale=1920:1080:force_original_aspect_ratio=decrease"

            # Audio codec handling
            audio_codec_option = "-c:a copy"
            if self.audio_auto_copy_checkbox.isChecked() and self._detected_audio_codec:
                # Check if detected audio codec is compatible with MP4
                detected = self._detected_audio_codec.lower()
                if detected in ["aac", "mp3", "opus"]:
                    audio_codec_option = "-c:a copy"
                else:
                    # Use fallback codec for incompatible formats
                    fallback = self.audio_codec_combo.currentData()
                    bitrate = self.audio_bitrate_spinbox.value()
                    audio_codec_option = f"-c:a {fallback} -b:a {bitrate}k"
            else:
                # Auto-copy disabled, use configured codec
                fallback = self.audio_codec_combo.currentData()
                bitrate = self.audio_bitrate_spinbox.value()
                audio_codec_option = f"-c:a {fallback} -b:a {bitrate}k"

            # Build command parts (use {INPUT}, {OUTPUT}, {AUDIO_TRACK} placeholders)
            cmd_parts = [
                'ffmpeg -i {INPUT}',
                "-map 0:v:0 -map 0:a:{AUDIO_TRACK}",
                f"-c:v {codec}",
                f"-cq {crf}",
                f"-preset {speed}",
                f"-profile:v {profile}",
                f"-level {level}",
                f'-vf "{scale_filter}"',
                "-color_range tv",
                "-pix_fmt yuv420p",
                "-g 60",
                audio_codec_option,
                "-ac 2",
                "-map_chapters 0",
                "-map_metadata 0",
                '-y {OUTPUT}'
            ]

            command = " ".join(cmd_parts)
            self.command_text.setPlainText(command)

        except Exception as e:
            self.command_text.setPlainText(f"Error: {e}")

    def _copy_command(self) -> None:
        """Copy command to clipboard."""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.command_text.toPlainText())
