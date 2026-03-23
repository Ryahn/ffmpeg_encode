"""FFmpeg Settings tab (PyQt6) - Comprehensive encoding configuration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Optional, Dict

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from core.preset_parser import PresetParser
from core.track_analyzer import TrackAnalyzer
from core.subprocess_utils import get_subprocess_kwargs
from utils.config import config
from utils.ffmpeg_encoding import resolve_pix_fmt


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
        root.addWidget(self._ffmpeg_advanced_group())
        root.addWidget(self._audio_group())
        root.addWidget(self._subtitle_group())
        root.addWidget(self._command_preview_group())
        root.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        self._load_ffmpeg_encoding_widgets()

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

    def _ffmpeg_advanced_group(self) -> QGroupBox:
        """GOP, pixel format, color range, and scale dimensions (persisted)."""
        group = QGroupBox("Advanced video (FFmpeg)")
        layout = QFormLayout()

        self.gop_spinbox = QSpinBox()
        self.gop_spinbox.setRange(12, 600)
        self.gop_spinbox.setToolTip("Keyframe interval (-g); larger can improve compression")
        self.gop_spinbox.valueChanged.connect(self._on_ffmpeg_encoding_changed)
        layout.addRow("GOP (-g):", self.gop_spinbox)

        self.pix_fmt_combo = QComboBox()
        self.pix_fmt_combo.addItem("Auto (match profile)", "auto")
        self.pix_fmt_combo.addItem("yuv420p (8-bit 4:2:0)", "yuv420p")
        self.pix_fmt_combo.addItem("yuv420p10le (10-bit)", "yuv420p10le")
        self.pix_fmt_combo.addItem("yuv420p12le (12-bit)", "yuv420p12le")
        self.pix_fmt_combo.addItem("yuv444p", "yuv444p")
        self.pix_fmt_combo.addItem("yuv444p10le", "yuv444p10le")
        self.pix_fmt_combo.addItem("nv12", "nv12")
        self.pix_fmt_combo.addItem("p010le", "p010le")
        self.pix_fmt_combo.currentIndexChanged.connect(self._on_ffmpeg_encoding_changed)
        layout.addRow("Pixel format:", self.pix_fmt_combo)

        self.color_range_combo = QComboBox()
        self.color_range_combo.addItem("TV (limited)", "tv")
        self.color_range_combo.addItem("PC (full)", "pc")
        self.color_range_combo.currentIndexChanged.connect(self._on_ffmpeg_encoding_changed)
        layout.addRow("Color range:", self.color_range_combo)

        self.scale_cap_w_spin = QSpinBox()
        self.scale_cap_w_spin.setRange(16, 7680)
        self.scale_cap_w_spin.setToolTip("Max width in cap pass-through scale (min with iw)")
        self.scale_cap_w_spin.valueChanged.connect(self._on_ffmpeg_encoding_changed)
        layout.addRow("Scale cap width:", self.scale_cap_w_spin)

        self.scale_cap_h_spin = QSpinBox()
        self.scale_cap_h_spin.setRange(16, 7680)
        self.scale_cap_h_spin.setToolTip("Max height in cap pass-through scale (min with ih)")
        self.scale_cap_h_spin.valueChanged.connect(self._on_ffmpeg_encoding_changed)
        layout.addRow("Scale cap height:", self.scale_cap_h_spin)

        self.target_w_spin = QSpinBox()
        self.target_w_spin.setRange(16, 7680)
        self.target_w_spin.setToolTip("Target width for upscale / >1080p downscale branch")
        self.target_w_spin.valueChanged.connect(self._on_ffmpeg_encoding_changed)
        layout.addRow("Target width:", self.target_w_spin)

        self.target_h_spin = QSpinBox()
        self.target_h_spin.setRange(16, 7680)
        self.target_h_spin.setToolTip("Target height for upscale / >1080p downscale branch")
        self.target_h_spin.valueChanged.connect(self._on_ffmpeg_encoding_changed)
        layout.addRow("Target height:", self.target_h_spin)

        group.setLayout(layout)
        return group

    def _load_ffmpeg_encoding_widgets(self) -> None:
        self.gop_spinbox.blockSignals(True)
        self.pix_fmt_combo.blockSignals(True)
        self.color_range_combo.blockSignals(True)
        self.scale_cap_w_spin.blockSignals(True)
        self.scale_cap_h_spin.blockSignals(True)
        self.target_w_spin.blockSignals(True)
        self.target_h_spin.blockSignals(True)
        try:
            self.gop_spinbox.setValue(config.get_ffmpeg_gop())
            mode = config.get_ffmpeg_pix_fmt_mode()
            if mode == "auto":
                i = self.pix_fmt_combo.findData("auto")
            else:
                fmt = config.get_ffmpeg_pix_fmt()
                i = self.pix_fmt_combo.findData(fmt)
                if i < 0:
                    i = self.pix_fmt_combo.findData("auto")
            if i >= 0:
                self.pix_fmt_combo.setCurrentIndex(i)
            cr = config.get_ffmpeg_color_range()
            cri = self.color_range_combo.findData(cr)
            if cri >= 0:
                self.color_range_combo.setCurrentIndex(cri)
            self.scale_cap_w_spin.setValue(config.get_ffmpeg_scale_cap_w())
            self.scale_cap_h_spin.setValue(config.get_ffmpeg_scale_cap_h())
            self.target_w_spin.setValue(config.get_ffmpeg_target_w())
            self.target_h_spin.setValue(config.get_ffmpeg_target_h())
        finally:
            self.gop_spinbox.blockSignals(False)
            self.pix_fmt_combo.blockSignals(False)
            self.color_range_combo.blockSignals(False)
            self.scale_cap_w_spin.blockSignals(False)
            self.scale_cap_h_spin.blockSignals(False)
            self.target_w_spin.blockSignals(False)
            self.target_h_spin.blockSignals(False)

    def _on_ffmpeg_encoding_changed(self) -> None:
        config.set_ffmpeg_gop(self.gop_spinbox.value())
        pix_data = self.pix_fmt_combo.currentData()
        if pix_data == "auto":
            config.set_ffmpeg_pix_fmt_mode("auto")
        else:
            config.set_ffmpeg_pix_fmt_mode("manual")
            config.set_ffmpeg_pix_fmt(str(pix_data))
        config.set_ffmpeg_color_range(str(self.color_range_combo.currentData() or "tv"))
        config.set_ffmpeg_scale_cap_w(self.scale_cap_w_spin.value())
        config.set_ffmpeg_scale_cap_h(self.scale_cap_h_spin.value())
        config.set_ffmpeg_target_w(self.target_w_spin.value())
        config.set_ffmpeg_target_h(self.target_h_spin.value())
        self._update_preview()

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

                    tw, th = parser.get_video_resolution()
                    self.target_w_spin.blockSignals(True)
                    self.target_h_spin.blockSignals(True)
                    self.target_w_spin.setValue(max(16, min(7680, int(tw))))
                    self.target_h_spin.setValue(max(16, min(7680, int(th))))
                    self.target_w_spin.blockSignals(False)
                    self.target_h_spin.blockSignals(False)
                    config.set_ffmpeg_target_w(self.target_w_spin.value())
                    config.set_ffmpeg_target_h(self.target_h_spin.value())

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

            run_kw = {
                "args": cmd,
                "capture_output": True,
                "text": True,
                "timeout": 10,
            }
            run_kw.update(get_subprocess_kwargs())
            result = subprocess.run(**run_kw)
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
            codec = self.codec_combo.currentData()
            crf = self.crf_spinbox.value()
            speed = self.speed_combo.currentData()
            profile = self.profile_combo.currentData()
            level = self.level_combo.currentData()

            cap_w = self.scale_cap_w_spin.value()
            cap_h = self.scale_cap_h_spin.value()
            target_w = self.target_w_spin.value()
            target_h = self.target_h_spin.value()
            gop = self.gop_spinbox.value()
            color_range = self.color_range_combo.currentData() or "tv"
            pix_sel = self.pix_fmt_combo.currentData()
            if pix_sel == "auto":
                pix_fmt = resolve_pix_fmt(str(profile or "main"), "auto", "yuv420p")
            else:
                pix_fmt = resolve_pix_fmt(
                    str(profile or "main"), "manual", str(pix_sel)
                )

            if self._source_resolution:
                src_width, src_height = self._source_resolution
            else:
                src_width, src_height = target_w, target_h

            if self.upscale_checkbox.isChecked():
                scale_filter = (
                    f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease"
                )
            elif src_height <= 1080:
                scale_filter = (
                    f"scale='min(iw,{cap_w})':'min(ih,{cap_h})'"
                    f":force_original_aspect_ratio=decrease"
                )
            else:
                scale_filter = (
                    f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease"
                )

            audio_codec_option = "-c:a copy"
            if self.audio_auto_copy_checkbox.isChecked() and self._detected_audio_codec:
                detected = self._detected_audio_codec.lower()
                if detected in ["aac", "mp3", "opus"]:
                    audio_codec_option = "-c:a copy"
                else:
                    fallback = self.audio_codec_combo.currentData()
                    bitrate = self.audio_bitrate_spinbox.value()
                    audio_codec_option = f"-c:a {fallback} -b:a {bitrate}k"
            else:
                fallback = self.audio_codec_combo.currentData()
                bitrate = self.audio_bitrate_spinbox.value()
                audio_codec_option = f"-c:a {fallback} -b:a {bitrate}k"

            audio_parts = [audio_codec_option]
            if not audio_codec_option.startswith("-c:a copy"):
                audio_parts.append("-ac 2")

            cmd_parts = [
                "ffmpeg -i {INPUT}",
                "-map 0:v:0 -map 0:a:{AUDIO_TRACK}",
                f"-c:v {codec}",
                f"-cq {crf}",
                f"-preset {speed}",
                f"-profile:v {profile}",
                f"-level {level}",
                f'-vf "{scale_filter}"',
                f"-color_range {color_range}",
                f"-pix_fmt {pix_fmt}",
                f"-g {gop}",
                *audio_parts,
                "-map_chapters 0",
                "-map_metadata 0",
                "-y {OUTPUT}",
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
