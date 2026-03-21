"""FFmpeg encoding tab (PyQt6).

The encoder core supports **Stop** (terminate current process); there is no
mid-encode pause/resume API in ``core.encoder`` to wire here.
"""

from __future__ import annotations

import threading
import re
import shlex
import time
from pathlib import Path
from typing import Callable, List, Optional

from PyQt6.QtCore import QObject, QThread, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QDoubleSpinBox,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .ffmpeg_command_util import (
    ffmpeg_preview_to_html,
    generate_command_preview,
    parse_and_substitute_command,
)
from ..widgets.log_viewer import LogViewer
from ..widgets.progress_bar import ProgressDisplay
from core.audio_normalize import build_integrated_loudnorm_filter
from core.batch_stats import BatchStats
from core.encoder import Encoder, EncodingProgress, extract_subtitle_stream, extract_text_subtitle_to_file, detect_subtitles, process_file_subtitles, TEXT_SUBTITLE_CODECS
from core.ffmpeg_translator import FFmpegTranslator
from core.subtitle_policy import decide_subtitle_action
from core.notifications import BatchNotification
from core.preset_parser import PresetParser
from core.track_analyzer import TrackAnalyzer
from core.track_selection import compute_effective_tracks
from storage import record_successful_encode
from utils.config import config
from utils.logger import logger


class _AnalyzeOneWorker(QObject):
    """Runs analyze_tracks() for a single file off the GUI thread."""

    finished = pyqtSignal(object, object)  # (tracks_dict, source_file)

    def __init__(self, source_file: Path, analyzer: TrackAnalyzer):
        super().__init__()
        self._source_file = source_file
        self._analyzer = analyzer

    def run(self) -> None:
        tracks = self._analyzer.analyze_tracks(self._source_file)
        self.finished.emit(tracks, self._source_file)


class _FFmpegUiBridge(QObject):
    log_msg = pyqtSignal(str, str)
    progress = pyqtSignal(object)
    reset_ui = pyqtSignal()
    toast = pyqtSignal(str, str)
    status_text = pyqtSignal(str)


class FFmpegTab(QWidget):
    _PLACEHOLDER_CHIP_STYLES = {
        "{INPUT}": ("#1e3a52", "#7dd3fc", "#2a4a6a"),
        "{OUTPUT}": ("#1a3d2e", "#4ade80", "#255238"),
        "{AUDIO_TRACK}": ("#3d3020", "#f0a500", "#524018"),
        "{SUBTITLE_TRACK}": ("#2d2640", "#c4b5fd", "#3d3558"),
        "{SUBTITLE_FILE}": ("#3d1f40", "#f9a8d4", "#522840"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None
        self.preset_parser: Optional[PresetParser] = None
        self.ffmpeg_translator: Optional[FFmpegTranslator] = None
        self.encoder: Optional[Encoder] = None
        self.track_analyzer: Optional[TrackAnalyzer] = None
        self.encoding_thread: Optional[threading.Thread] = None
        self._detect_thread: Optional[QThread] = None
        self.is_encoding = False
        self.batch_stats: Optional[BatchStats] = None
        self.get_files_callback: Optional[Callable] = None
        self.update_file_callback: Optional[Callable] = None
        self.get_output_path_callback: Optional[Callable] = None
        self._progress_ui_throttle_last: Optional[float] = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_command_preview_display)
        self._last_preview_plain = ""

        self._bridge = _FFmpegUiBridge(self)

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(inner)

        preset_gb = QGroupBox("HandBrake preset")
        pr = QHBoxLayout(preset_gb)
        pr.addWidget(QLabel("Saved preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(280)
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        pr.addWidget(self.preset_combo)
        pr.addWidget(self._btn("Load Preset", self._load_preset))
        self.detect_tracks_btn = self._btn("Detect Tracks", self._detect_and_update_tracks)
        pr.addWidget(self.detect_tracks_btn)
        root.addWidget(preset_gb)

        cmd_gb = QGroupBox("FFmpeg command (editable)")
        cmd_l = QVBoxLayout(cmd_gb)

        # Custom Command Override checkbox
        override_layout = QHBoxLayout()
        self.custom_command_override_cb = QCheckBox("Custom Command Override")
        self.custom_command_override_cb.setChecked(False)
        self.custom_command_override_cb.setToolTip(
            "When checked, uses the command exactly as-is, bypassing all app settings "
            "(subtitles, audio normalization, etc.). When unchecked, app settings optimize the command."
        )
        self.custom_command_override_cb.toggled.connect(self._on_custom_override_toggled)
        override_layout.addWidget(self.custom_command_override_cb)
        override_layout.addWidget(QLabel("⚠️ Bypasses subtitle handling, audio, and other settings"))
        override_layout.addStretch()
        cmd_l.addLayout(override_layout)

        self.cmd_text = QPlainTextEdit()
        self.cmd_text.setMinimumHeight(90)
        self.cmd_text.textChanged.connect(self._schedule_preview_update)
        cmd_l.addWidget(self.cmd_text)
        hb = QHBoxLayout()
        for t, fn in [
            ("Save", self._save_command),
            ("Load", self._load_saved_command),
            ("Load from File", self._load_command_from_file),
            ("Save to File", self._save_command_to_file),
            ("Reset", self._reset_command),
        ]:
            hb.addWidget(self._btn(t, fn))
        cmd_l.addLayout(hb)
        root.addWidget(cmd_gb)

        loud_gb = QGroupBox("Audio — loudnorm (preset-generated command)")
        loud_note = QLabel(
            "When a HandBrake preset is loaded, toggling these updates the command text "
            "the same way as Settings → Encoding."
        )
        loud_note.setWordWrap(True)
        loud_note.setStyleSheet("color: #888888; font-size: 12px;")
        loud_l = QVBoxLayout(loud_gb)
        loud_l.addWidget(loud_note)
        loud_form = QFormLayout()
        self.loudnorm_cb = QCheckBox("Apply integrated loudnorm (-af)")
        self.loudnorm_cb.setChecked(config.get_audio_normalize_enabled())
        self.loudnorm_cb.toggled.connect(self._on_loudnorm_enabled_changed)
        loud_form.addRow(self.loudnorm_cb)
        self.loudnorm_I = QDoubleSpinBox()
        self.loudnorm_I.setRange(-70.0, -5.0)
        self.loudnorm_I.setDecimals(1)
        self.loudnorm_I.setSingleStep(0.5)
        self.loudnorm_I.setValue(config.get_audio_normalize_loudnorm_I())
        self.loudnorm_I.valueChanged.connect(self._on_loudnorm_params_changed)
        loud_form.addRow("Target I (LUFS):", self.loudnorm_I)
        self.loudnorm_TP = QDoubleSpinBox()
        self.loudnorm_TP.setRange(-9.0, 0.0)
        self.loudnorm_TP.setDecimals(1)
        self.loudnorm_TP.setSingleStep(0.5)
        self.loudnorm_TP.setValue(config.get_audio_normalize_loudnorm_TP())
        self.loudnorm_TP.valueChanged.connect(self._on_loudnorm_params_changed)
        loud_form.addRow("True peak TP (dBTP):", self.loudnorm_TP)
        self.loudnorm_LRA = QDoubleSpinBox()
        self.loudnorm_LRA.setRange(1.0, 20.0)
        self.loudnorm_LRA.setDecimals(1)
        self.loudnorm_LRA.setSingleStep(0.5)
        self.loudnorm_LRA.setValue(config.get_audio_normalize_loudnorm_LRA())
        self.loudnorm_LRA.valueChanged.connect(self._on_loudnorm_params_changed)
        loud_form.addRow("Loudness range LRA:", self.loudnorm_LRA)
        loud_l.addLayout(loud_form)
        self._sync_loudnorm_controls_enabled()
        root.addWidget(loud_gb)

        saved_gb = QGroupBox("Saved command snippets")
        sv = QHBoxLayout(saved_gb)
        sv.addWidget(QLabel("Name:"))
        self.saved_cmd_combo = QComboBox()
        self.saved_cmd_combo.setMinimumWidth(260)
        self.saved_cmd_combo.currentTextChanged.connect(self._on_saved_command_selected)
        sv.addWidget(self.saved_cmd_combo)
        sv.addWidget(self._btn("Delete", self._delete_saved_command))
        root.addWidget(saved_gb)

        preview_gb = QGroupBox("Resolved preview (first queued file)")
        preview_l = QVBoxLayout(preview_gb)
        preview_hdr = QHBoxLayout()
        preview_hdr.addWidget(
            QLabel(
                "Known placeholders are color-coded; unknown {TOKENS} show in red. Copy uses plain text."
            )
        )
        preview_hdr.addStretch()
        preview_hdr.addWidget(self._btn("Copy plain text", self._copy_preview_to_clipboard))
        preview_l.addLayout(preview_hdr)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(100)
        self.preview_text.setAcceptRichText(True)
        preview_l.addWidget(self.preview_text)
        root.addWidget(preview_gb)

        ph_gb = QGroupBox("Insert placeholders")
        ph = QHBoxLayout(ph_gb)
        ph.addWidget(QLabel("Click to insert at cursor:"))
        for token in [
            "{INPUT}",
            "{OUTPUT}",
            "{AUDIO_TRACK}",
            "{SUBTITLE_TRACK}",
            "{SUBTITLE_FILE}",
        ]:
            ph.addWidget(self._placeholder_chip(token))
        ph.addStretch()
        root.addWidget(ph_gb)

        enc_gb = QGroupBox("Encoding")
        enc_l = QVBoxLayout(enc_gb)
        opt = QHBoxLayout()
        self.dry_run_cb = QCheckBox("Dry Run")
        self.skip_cb = QCheckBox("Skip Existing")
        self.skip_cb.setChecked(config.get_skip_existing())
        self.skip_cb.toggled.connect(lambda v: config.set_skip_existing(v))
        opt.addWidget(self.dry_run_cb)
        opt.addWidget(self.skip_cb)
        opt.addWidget(QLabel("Output Suffix:"))
        self.suffix_entry = QLineEdit(config.get_default_output_suffix())
        self.suffix_entry.setMaximumWidth(140)
        self.suffix_entry.textChanged.connect(self._schedule_preview_update)
        opt.addWidget(self.suffix_entry)
        opt.addWidget(QLabel("Mode:"))
        self._mode_seq = QRadioButton("Sequential")
        self._mode_par = QRadioButton("Parallel")
        if config.get_encoding_mode() == "parallel":
            self._mode_par.setChecked(True)
        else:
            self._mode_seq.setChecked(True)
        self._mode_seq.toggled.connect(lambda: config.set_encoding_mode("parallel" if self._mode_par.isChecked() else "sequential"))
        self._mode_par.toggled.connect(lambda: config.set_encoding_mode("parallel" if self._mode_par.isChecked() else "sequential"))
        opt.addWidget(self._mode_seq)
        opt.addWidget(self._mode_par)
        opt.addStretch()
        self.start_btn = self._btn("Start Encoding", self._start_encoding)
        opt.addWidget(self.start_btn)
        self.stop_btn = self._btn("Stop", self._stop_encoding)
        self.stop_btn.setEnabled(False)
        opt.addWidget(self.stop_btn)
        enc_l.addLayout(opt)
        self.progress_display = ProgressDisplay()
        enc_l.addWidget(self.progress_display)
        root.addWidget(enc_gb)

        outer.addWidget(scroll)

        log_fr = QFrame()
        ll = QVBoxLayout(log_fr)
        self.log_viewer = LogViewer(height=180)
        lh = QHBoxLayout()
        lh.addWidget(QLabel("<b>Encoding Log</b>"))
        lh.addWidget(self._btn("Copy", lambda: self.log_viewer.copy_to_clipboard()))
        ll.addLayout(lh)
        ll.addWidget(self.log_viewer)
        outer.addWidget(log_fr)

        self._bridge.log_msg.connect(self._append_log)
        self._bridge.progress.connect(self._apply_progress)
        self._bridge.reset_ui.connect(self._reset_ui_on_encode_end)
        self._bridge.toast.connect(self._emit_toast)
        self._bridge.status_text.connect(self.progress_display.set_status)

        self._init_encoder()
        self._refresh_preset_dropdown()
        self._update_saved_commands_dropdown()
        self._load_last_preset()
        self._update_command_preview_display()

    _AF_OPTION_RE = re.compile(
        r"(?P<prefix>\s)-af\s+(?P<val>'[^']*'|\"[^\"]*\"|\S+)"
    )

    def _btn(self, text, slot):
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b

    def _placeholder_chip(self, token: str) -> QPushButton:
        b = QPushButton(token)
        bg, fg, hover = self._PLACEHOLDER_CHIP_STYLES[token]
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {fg};
                border-radius: 5px;
                padding: 4px 8px;
                font-weight: 600;
                font-family: Consolas, "Courier New", monospace;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {hover};
            }}
            """
        )
        b.clicked.connect(lambda: self._insert_placeholder(token))
        return b

    def _sync_loudnorm_controls_enabled(self) -> None:
        enabled = self.loudnorm_cb.isChecked()
        self.loudnorm_I.setEnabled(enabled)
        self.loudnorm_TP.setEnabled(enabled)
        self.loudnorm_LRA.setEnabled(enabled)

    def _on_loudnorm_enabled_changed(self, checked: bool) -> None:
        config.set_audio_normalize_enabled(checked)
        self._sync_loudnorm_controls_enabled()
        self._refresh_preset_command_after_loudnorm()

    def _on_loudnorm_params_changed(self, _value: float = 0.0) -> None:
        config.set_audio_normalize_loudnorm_I(self.loudnorm_I.value())
        config.set_audio_normalize_loudnorm_TP(self.loudnorm_TP.value())
        config.set_audio_normalize_loudnorm_LRA(self.loudnorm_LRA.value())
        self._refresh_preset_command_after_loudnorm()

    def _on_custom_override_toggled(self, checked: bool) -> None:
        """Handle Custom Command Override checkbox toggle."""
        if checked:
            self._on_log("WARNING", "Custom Command Override enabled - app settings will be bypassed")
        else:
            self._on_log("INFO", "Custom Command Override disabled - app settings will be applied")

    def _refresh_preset_command_after_loudnorm(self) -> None:
        self._apply_loudnorm_to_current_cmd_text()
        self._schedule_preview_update()

    def apply_audio_normalize_settings_from_config(self) -> None:
        """Sync loudnorm widgets when config was changed elsewhere (e.g. Settings tab)."""
        self.loudnorm_cb.blockSignals(True)
        self.loudnorm_I.blockSignals(True)
        self.loudnorm_TP.blockSignals(True)
        self.loudnorm_LRA.blockSignals(True)
        try:
            self.loudnorm_cb.setChecked(config.get_audio_normalize_enabled())
            self.loudnorm_I.setValue(config.get_audio_normalize_loudnorm_I())
            self.loudnorm_TP.setValue(config.get_audio_normalize_loudnorm_TP())
            self.loudnorm_LRA.setValue(config.get_audio_normalize_loudnorm_LRA())
        finally:
            self.loudnorm_cb.blockSignals(False)
            self.loudnorm_I.blockSignals(False)
            self.loudnorm_TP.blockSignals(False)
            self.loudnorm_LRA.blockSignals(False)
        self._sync_loudnorm_controls_enabled()
        self._schedule_preview_update()

    def _strip_af_value_quotes(self, af_value: str) -> tuple[str, str]:
        """Return (unquoted_value, quote_char) where quote_char is '' or one of \"'\" / '\"'."""
        if len(af_value) >= 2 and af_value[0] == af_value[-1] and af_value[0] in ("'", '"'):
            return af_value[1:-1], af_value[0]
        return af_value, ""

    def _quote_af_value(self, af_value_unquoted: str, quote_char: str) -> str:
        if quote_char:
            return f"{quote_char}{af_value_unquoted}{quote_char}"
        return af_value_unquoted

    def _apply_loudnorm_to_current_cmd_text(self) -> None:
        """
        Update only the -af option in the current command template.

        This preserves manual video encoding edits (e.g. NVENC encoder selection)
        while still letting the loudnorm toggle affect audio loudness.
        """
        filter_expr = self._audio_filter_from_settings()
        cmd = self.cmd_text.toPlainText()
        if not cmd.strip():
            return

        def repl_enable(match: re.Match) -> str:
            prefix = match.group("prefix")
            existing_raw = match.group("val")
            existing, quote_char = self._strip_af_value_quotes(existing_raw)

            if existing.strip().startswith("loudnorm="):
                new_val = self._quote_af_value(filter_expr or "", quote_char)
            else:
                # If user already has some audio filters, append loudnorm.
                existing_parts = [p.strip() for p in existing.split(",") if p.strip()]
                if existing_parts:
                    existing_parts.append(filter_expr or "")
                    new_val = self._quote_af_value(",".join(existing_parts), quote_char)
                else:
                    new_val = self._quote_af_value(filter_expr or "", quote_char)

            return f"{prefix}-af {new_val}"

        def repl_disable(match: re.Match) -> str:
            prefix = match.group("prefix")
            existing_raw = match.group("val")
            existing, quote_char = self._strip_af_value_quotes(existing_raw)

            parts = [p.strip() for p in existing.split(",") if p.strip()]
            kept = [p for p in parts if not p.startswith("loudnorm=")]
            if not kept:
                return ""  # remove whole -af option
            return f"{prefix}-af {self._quote_af_value(','.join(kept), quote_char)}"

        # Enable loudnorm: replace/insert
        if filter_expr:
            if self._AF_OPTION_RE.search(cmd):
                new_cmd = self._AF_OPTION_RE.sub(repl_enable, cmd, count=1)
            else:
                insert_at: Optional[int] = None
                for patt in [r"\s-c:a\b", r"\s-map_chapters\b", r"\s-y\b"]:
                    m = re.search(patt, cmd)
                    if m:
                        insert_at = m.start()
                        break
                insert_str = f" -af {filter_expr}"
                if insert_at is not None:
                    new_cmd = cmd[:insert_at] + insert_str + cmd[insert_at:]
                else:
                    new_cmd = cmd + insert_str
        else:
            # Disable loudnorm: remove loudnorm entries from -af, but keep other filters.
            if not self._AF_OPTION_RE.search(cmd):
                return
            new_cmd = self._AF_OPTION_RE.sub(repl_disable, cmd, count=1)

        self.cmd_text.blockSignals(True)
        self.cmd_text.setPlainText(new_cmd)
        self.cmd_text.blockSignals(False)

    def _audio_filter_from_settings(self) -> Optional[str]:
        if not config.get_audio_normalize_enabled():
            return None
        return build_integrated_loudnorm_filter(
            config.get_audio_normalize_loudnorm_I(),
            config.get_audio_normalize_loudnorm_TP(),
            config.get_audio_normalize_loudnorm_LRA(),
        )

    def _schedule_preview_update(self) -> None:
        self._preview_timer.start(300)

    def on_files_changed(self) -> None:
        self._schedule_preview_update()

    def _init_encoder(self) -> None:
        ffmpeg_path = config.get_ffmpeg_path() or "ffmpeg"
        handbrake_path = config.get_handbrake_path() or "HandBrakeCLI"
        mkvinfo_path = config.get_mkvinfo_path() or "mkvinfo"
        self.encoder = Encoder(
            ffmpeg_path=ffmpeg_path,
            handbrake_path=handbrake_path,
            progress_callback=self._on_progress,
            log_callback=self._on_log,
        )
        self.track_analyzer = TrackAnalyzer(
            mkvinfo_path=mkvinfo_path if mkvinfo_path != "mkvinfo" else None
        )

    def _refresh_preset_dropdown(self) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("")
        for name in config.get_saved_presets().keys():
            self.preset_combo.addItem(name)
        self.preset_combo.blockSignals(False)

    def _load_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select HandBrake preset JSON file", "", "JSON (*.json);;All (*.*)"
        )
        if path:
            try:
                self._load_preset_from_path(Path(path), save=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _load_preset_from_path(self, preset_path: Path, save: bool = False) -> None:
        self.preset_parser = PresetParser(preset_path)
        self.ffmpeg_translator = FFmpegTranslator(self.preset_parser)
        preset_name = self.preset_parser.get_preset_name()
        if save:
            config.save_preset(preset_name, preset_path)
            config.set_last_used_preset(preset_name)
            self._refresh_preset_dropdown()
            i = self.preset_combo.findText(preset_name)
            if i >= 0:
                self.preset_combo.setCurrentIndex(i)
        else:
            config.set_last_used_preset(preset_name)
        self._update_command_preview()
        self._update_command_preview_display()
        self._on_log("INFO", f"Loaded preset: {preset_name}")

        # Check for preset subtitle filter conflicts with subtitle policy
        self._check_preset_subtitle_conflicts(preset_name, preset_path)

    def _on_preset_selected(self, choice: str) -> None:
        if not choice:
            return
        pp = config.get_preset_path(choice)
        if pp:
            try:
                self._load_preset_from_path(pp, save=False)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                self._refresh_preset_dropdown()
                self.preset_combo.setCurrentIndex(0)

    def _load_last_preset(self) -> None:
        last = config.get_last_used_preset()
        if last:
            pp = config.get_preset_path(last)
            if pp:
                try:
                    self._load_preset_from_path(pp, save=False)
                    i = self.preset_combo.findText(last)
                    if i >= 0:
                        self.preset_combo.setCurrentIndex(i)
                except Exception:
                    pass

    def _check_preset_subtitle_conflicts(self, preset_name: str, preset_path: Path) -> None:
        """Check if preset has subtitle burning filters that conflict with subtitle policy.

        If conflicts are detected, offer user the option to update the preset.
        """
        # Get the current FFmpeg command
        cmd = self.cmd_text.toPlainText().strip()

        # Check if command contains subtitle filter
        has_subtitle_filter = "-vf" in cmd and "subtitles=" in cmd or \
                              "-filter_complex" in cmd and "subtitles=" in cmd

        if not has_subtitle_filter:
            return  # No subtitle filter, no conflict

        # Get current subtitle policy - any non-omit setting will conflict with burning
        subtitle_handling = config.get_subtitle_handling()
        pgs_action = subtitle_handling.get("pgs", "omit")
        embedded_text = subtitle_handling.get("embedded_text", "mux")
        embedded_ass = subtitle_handling.get("embedded_ass", "external")
        external_text = subtitle_handling.get("external_text", "keep")
        external_ass = subtitle_handling.get("external_ass", "keep")

        # Check if any non-omit policies are set
        has_non_omit_policy = any([
            pgs_action != "omit",
            embedded_text != "omit",
            embedded_ass != "omit",
            external_text not in ("ignore", "omit"),
            external_ass not in ("ignore", "omit")
        ])

        if not has_non_omit_policy:
            return  # All policies are omit, no conflict

        # Conflict detected - offer update or use as-is
        reply = QMessageBox.warning(
            self,
            "Subtitle Filter Conflict",
            f"Your preset '{preset_name}' contains a subtitle burning filter "
            "(-vf subtitles=...), but your Subtitle Handling policy is set to:\n\n"
            f"  • PGS: {pgs_action}\n"
            f"  • Embedded text: {embedded_text}\n"
            f"  • Embedded ASS: {embedded_ass}\n"
            f"  • External text: {external_text}\n"
            f"  • External ASS: {external_ass}\n\n"
            "Burning subtitles will cause Jellyfin to re-encode on playback.\n\n"
            "Options:\n"
            "  • [Update Preset] - Remove the filter, use your subtitle policy\n"
            "  • [Use As-Is] - Keep the filter (ignore your policy)\n"
            "  • [Cancel] - Don't load this preset",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Cancel:
            # User cancelled, clear the preset
            self.cmd_text.setPlainText("")
            self.preset_combo.setCurrentIndex(0)
            self._on_log("INFO", "Preset loading cancelled")
            return

        if reply == QMessageBox.StandardButton.Yes:
            # Update preset - remove subtitle filter
            self._remove_subtitle_filter_from_command()
            self._on_log("INFO", f"Updated preset '{preset_name}' to remove subtitle filter")

    def _remove_subtitle_filter_from_command(self) -> None:
        """Remove subtitle burning filter from FFmpeg command."""
        cmd = self.cmd_text.toPlainText()

        # Remove -vf subtitles=... pattern (handles simple cases)
        # Pattern to match -vf "..." with subtitles filter
        cmd = re.sub(r'-vf\s+"[^"]*subtitles=[^"]*"', '', cmd)
        cmd = re.sub(r"-vf\s+'[^']*subtitles=[^']*'", '', cmd)
        # For unquoted -vf (less common)
        cmd = re.sub(r'-vf\s+\S*subtitles=\S+\s+', '', cmd)

        # Also handle -filter_complex with subtitles
        cmd = re.sub(r'-filter_complex\s+"[^"]*subtitles=[^"]*"', '', cmd)
        cmd = re.sub(r"-filter_complex\s+'[^']*subtitles=[^']*'", '', cmd)

        # Clean up excess whitespace
        cmd = re.sub(r'\s+', ' ', cmd).strip()

        self.cmd_text.blockSignals(True)
        self.cmd_text.setPlainText(cmd)
        self.cmd_text.blockSignals(False)
        self._update_command_preview_display()

    def _remove_conflicting_subtitle_filters_from_args(self, ffmpeg_args: List[str], subtitle_decision) -> List[str]:
        """Remove subtitle-related filters from FFmpeg args based on subtitle decision.

        If we're handling a text subtitle (ASS/SRT), remove PGS overlay filters.
        If we're omitting subtitles, remove all subtitle-related filters.

        Args:
            ffmpeg_args: List of FFmpeg arguments
            subtitle_decision: SubtitleDecision with action and codec info

        Returns:
            Modified args list with conflicting filters removed
        """
        if not subtitle_decision:
            return ffmpeg_args

        # Check if we need to remove filters
        needs_filter_removal = False

        if subtitle_decision.action in ("omit", "skip_file"):
            needs_filter_removal = True
        elif (subtitle_decision.source and
              subtitle_decision.source.startswith("embedded") and
              subtitle_decision.codec and
              subtitle_decision.codec not in ("pgssub", "hdmv_pgs_subtitle")):
            # Text subtitle - check if there's an overlay filter to remove
            for i, arg in enumerate(ffmpeg_args):
                if 'overlay=' in arg or 'subtitles=' in arg:
                    needs_filter_removal = True
                    break

        if not needs_filter_removal:
            return ffmpeg_args

        # Remove -filter_complex or -vf arguments that contain subtitle-related filters
        new_args = []
        i = 0
        while i < len(ffmpeg_args):
            arg = ffmpeg_args[i]

            # Check if this is a filter flag
            if arg in ('-filter_complex', '-vf'):
                # Skip this flag and check the next argument
                if i + 1 < len(ffmpeg_args):
                    next_arg = ffmpeg_args[i + 1]
                    # Check if filter contains overlay or subtitles
                    if 'overlay=' in next_arg or 'subtitles=' in next_arg:
                        # Skip both the flag and the filter argument
                        i += 2
                        self._on_log("DEBUG", f"Removed {arg} filter: {next_arg[:50]}...")
                        continue

                # Keep the flag and argument if no removal needed
                new_args.append(arg)
                if i + 1 < len(ffmpeg_args):
                    i += 1
                    new_args.append(ffmpeg_args[i])
            else:
                new_args.append(arg)

            i += 1

        return new_args

    def _update_command_preview(self) -> None:
        if not self.ffmpeg_translator:
            return
        ph_in = Path("input.mkv")
        ph_out = Path("output.mp4")
        subtitle_track_preview = None
        if self.get_files_callback:
            files = self.get_files_callback()
            if files:
                fd = files[0]
                subtitle_track_preview = fd.get("subtitle_track")
                if subtitle_track_preview is None and self.track_analyzer:
                    try:
                        tr = self.track_analyzer.analyze_tracks(Path(fd["path"]))
                        if not tr.get("error"):
                            subtitle_track_preview = tr.get("subtitle")
                    except Exception:
                        pass
        cmd = self.ffmpeg_translator.get_command_string(
            input_file=ph_in,
            output_file=ph_out,
            audio_track=2,
            subtitle_track=subtitle_track_preview,
            audio_filter=self._audio_filter_from_settings(),
        )
        self.cmd_text.blockSignals(True)
        self.cmd_text.setPlainText(cmd)
        self.cmd_text.blockSignals(False)

    def _detect_and_update_tracks(self) -> None:
        if not self.ffmpeg_translator:
            QMessageBox.warning(self, "No Preset", "Please load a HandBrake preset first")
            return
        if not self.get_files_callback:
            QMessageBox.warning(self, "No Files", "Add files to the file list first.")
            return
        files = self.get_files_callback()
        if not files:
            QMessageBox.warning(self, "No Files", "No files in the file list.")
            return
        source_file = Path(files[0]["path"])
        if not source_file.exists():
            QMessageBox.critical(self, "Not Found", str(source_file))
            return
        if not self.track_analyzer:
            QMessageBox.critical(self, "No Analyzer", "Track analyzer not available.")
            return

        self._on_log("INFO", f"Analyzing tracks for: {source_file.name}")
        self.detect_tracks_btn.setEnabled(False)

        self._detect_thread = QThread()
        worker = _AnalyzeOneWorker(source_file, self.track_analyzer)
        worker.moveToThread(self._detect_thread)
        self._detect_thread.started.connect(worker.run)
        worker.finished.connect(
            lambda tracks, sf: self._on_detect_tracks_done(tracks, sf, files)
        )
        worker.finished.connect(self._detect_thread.quit)
        worker.finished.connect(worker.deleteLater)
        self._detect_thread.finished.connect(self._detect_thread.deleteLater)
        self._detect_thread.start()

    def _on_detect_tracks_done(self, tracks: dict, source_file: Path, files: list) -> None:
        self.detect_tracks_btn.setEnabled(True)
        try:
            if tracks.get("error"):
                QMessageBox.critical(self, "Failed", tracks["error"])
                return
            audio_track, subtitle_track = compute_effective_tracks(
                tracks,
                self.track_analyzer,
                log_info=lambda msg: self._on_log("INFO", msg),
                source_label="",
            )
            if not audio_track:
                QMessageBox.warning(
                    self,
                    "No Audio",
                    "No English audio track found. Enable Japanese+audio option in Settings if needed.",
                )
                return
            files[0]["audio_track"] = audio_track
            files[0]["subtitle_track"] = subtitle_track
            if self.update_file_callback:
                self.update_file_callback(0, files[0])
            ph_in = Path("input.mkv")
            ph_out = Path("output.mp4")
            cmd = self.ffmpeg_translator.get_command_string(
                input_file=ph_in,
                output_file=ph_out,
                audio_track=audio_track,
                subtitle_track=subtitle_track,
                audio_filter=self._audio_filter_from_settings(),
            )
            self.cmd_text.setPlainText(cmd)
            self._update_command_preview_display()
            QMessageBox.information(self, "Tracks", "Tracks detected; command updated.")
            self._on_log("SUCCESS", "Tracks detected")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _generate_command_preview(self) -> str:
        return generate_command_preview(
            self.cmd_text.toPlainText(),
            self.get_files_callback,
            self.get_output_path_callback,
            self.suffix_entry.text() or config.get_default_output_suffix(),
        )

    def _update_command_preview_display(self) -> None:
        try:
            plain = self._generate_command_preview()
        except Exception as e:
            plain = f"Error generating preview: {e}"
        self._last_preview_plain = plain
        try:
            self.preview_text.setHtml(ffmpeg_preview_to_html(plain))
        except Exception:
            self.preview_text.setPlainText(plain)

    def _copy_preview_to_clipboard(self) -> None:
        t = (self._last_preview_plain or "").strip()
        if t and not t.startswith("No command") and not t.startswith("No files"):
            QGuiApplication.clipboard().setText(t)
            self._show_toast("Preview copied (plain text).", "success")
        else:
            self._show_toast("Nothing useful to copy yet.", "warning")

    def _save_command(self) -> None:
        cmd = self.cmd_text.toPlainText().strip()
        if not cmd:
            QMessageBox.warning(self, "Empty", "No command to save")
            return
        name, ok = QInputDialog.getText(self, "Save Command", "Name:")
        if ok and name.strip():
            config.save_ffmpeg_command(name.strip(), cmd)
            self._update_saved_commands_dropdown()

    def _load_saved_command(self) -> None:
        n = self.saved_cmd_combo.currentText()
        if not n:
            return
        c = config.get_ffmpeg_command(n)
        if c:
            self.cmd_text.setPlainText(c)
            self._update_command_preview_display()

    def _load_command_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load command", "", "Text (*.txt);;All (*.*)")
        if path:
            try:
                self.cmd_text.setPlainText(Path(path).read_text(encoding="utf-8").strip())
                self._update_command_preview_display()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _save_command_to_file(self) -> None:
        cmd = self.cmd_text.toPlainText().strip()
        if not cmd:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save command", "", "Text (*.txt)")
        if path:
            try:
                Path(path).write_text(cmd, encoding="utf-8")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _reset_command(self) -> None:
        if self.ffmpeg_translator:
            self._update_command_preview()
            self._update_command_preview_display()
        else:
            QMessageBox.warning(self, "No Preset", "Load a HandBrake preset first")

    def _delete_saved_command(self) -> None:
        n = self.saved_cmd_combo.currentText()
        if not n:
            return
        r = QMessageBox.question(
            self,
            "Delete",
            f"Delete '{n}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if r == QMessageBox.StandardButton.Yes:
            config.delete_ffmpeg_command(n)
            self._update_saved_commands_dropdown()

    def _update_saved_commands_dropdown(self) -> None:
        cmds = config.get_saved_ffmpeg_commands()
        self.saved_cmd_combo.blockSignals(True)
        self.saved_cmd_combo.clear()
        for k in cmds.keys():
            self.saved_cmd_combo.addItem(k)
        self.saved_cmd_combo.blockSignals(False)

    def _on_saved_command_selected(self, choice: str) -> None:
        if choice:
            c = config.get_ffmpeg_command(choice)
            if c:
                self.cmd_text.setPlainText(c)
                self._update_command_preview_display()

    def _insert_placeholder(self, p: str) -> None:
        self.cmd_text.insertPlainText(p)
        self._schedule_preview_update()

    def _append_log(self, level: str, message: str) -> None:
        self.log_viewer.add_log(level, message)

    def _apply_progress(self, progress: EncodingProgress) -> None:
        if progress.percent is not None:
            self.progress_display.set_progress(progress.percent)
            s = f"{progress.percent:.1f}%"
            if progress.eta:
                s += f" - ETA: {progress.eta}"
            self.progress_display.set_status(s)
        elif progress.time:
            s = f"Time: {progress.time}"
            if progress.speed:
                s += f" - Speed: {progress.speed:.2f}x"
            self.progress_display.set_status(s)

    def _on_progress(self, progress: EncodingProgress) -> None:
        now = time.monotonic()
        min_interval = 0.2
        near = progress.percent is not None and progress.percent >= 100.0
        if (
            self._progress_ui_throttle_last is not None
            and (now - self._progress_ui_throttle_last) < min_interval
            and not near
        ):
            return
        self._progress_ui_throttle_last = now
        self._bridge.progress.emit(progress)

    def _on_log(self, level: str, message: str) -> None:
        if level == "DEBUG" and not config.get_debug_logging():
            return
        self._bridge.log_msg.emit(level, message)
        p = f"[FFmpeg] {message}"
        if level == "ERROR":
            logger.error(p)
        elif level == "WARNING":
            logger.warning(p)
        elif level == "SUCCESS":
            logger.success(p)
        elif level == "DEBUG":
            logger.debug(p)
        else:
            logger.info(p)

    def _emit_toast(self, message: str, kind: str) -> None:
        w = self.main_window or self.window()
        if hasattr(w, "toast_manager"):
            w.toast_manager.show(message, message_type=kind, duration=5)

    def _show_toast(self, message: str, kind: str = "warning") -> None:
        self._emit_toast(message, kind)

    def _start_encoding(self) -> None:
        cmd = self.cmd_text.toPlainText().strip()
        if not cmd:
            self._show_toast("Please load a preset or enter an FFmpeg command", "warning")
            return
        if not self.get_files_callback or not self.get_files_callback():
            self._show_toast("No files to encode", "warning")
            return
        if self.is_encoding:
            return
        if self.encoding_thread and self.encoding_thread.is_alive():
            self.encoding_thread.join(timeout=2.0)
        self.is_encoding = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        if self.encoder:
            self.encoder.reset_stop_event()
        self.batch_stats = BatchStats()
        cmd_snapshot = self.cmd_text.toPlainText().strip()
        self.encoding_thread = threading.Thread(
            target=self._encode_files,
            args=(self.get_files_callback(), cmd_snapshot),
            daemon=True,
        )
        self.encoding_thread.start()

    def _encode_files(self, files, command_template: str) -> None:
        dry_run = self.dry_run_cb.isChecked()
        skip_existing = self.skip_cb.isChecked()
        suffix = self.suffix_entry.text()
        ffmpeg_path = config.get_ffmpeg_path() or "ffmpeg"
        completed_count = 0
        skipped_count = 0
        error_count = 0
        for i, file_data in enumerate(files):
            if not self.is_encoding:
                break
            source_file = Path(file_data["path"])
            if file_data.get("tracks_from_user"):
                if file_data.get("audio_track") is None:
                    self._on_log("ERROR", f"No audio track set for {source_file.name}")
                    file_data["status"] = "Error"
                    error_count += 1
                    continue
                effective_audio = file_data["audio_track"]
                subtitle_track = file_data.get("subtitle_track")
                self._on_log("INFO", f"Using tracks from file list for: {source_file.name}")
            else:
                self._on_log("INFO", f"Analyzing tracks for: {source_file.name}")
                tracks = self.track_analyzer.analyze_tracks(source_file)
                if tracks.get("error"):
                    self._on_log("ERROR", f"Track analysis failed: {tracks['error']}")
                    file_data["status"] = "Error"
                    error_count += 1
                    continue
                effective_audio, subtitle_track = compute_effective_tracks(
                    tracks,
                    self.track_analyzer,
                    log_info=lambda msg: self._on_log("INFO", msg),
                    source_label=source_file.name,
                )
                if not effective_audio:
                    self._on_log("WARNING", f"No English audio: {source_file.name}")
                    file_data["status"] = "Skipped"
                    if self.batch_stats:
                        self.batch_stats.add_file_result(
                            filename=source_file.name,
                            elapsed=0,
                            input_size=0,
                            output_size=0,
                            success=False,
                            skipped=True,
                        )
                    skipped_count += 1
                    continue
                file_data["audio_track"] = effective_audio
                file_data["subtitle_track"] = subtitle_track

                # Extract subtitle language from tracks if subtitle was found
                if subtitle_track is not None and "streams" in tracks:
                    for stream in tracks.get("streams", []):
                        if stream.get("index") == subtitle_track:
                            lang = stream.get("language", "en")
                            # Map full language names to ISO codes if needed
                            lang_map = {"english": "en", "japanese": "ja", "spanish": "es", "french": "fr", "german": "de"}
                            lang_code = lang_map.get(lang.lower(), lang.lower()[:2] if len(lang) >= 2 else "en")
                            file_data["subtitle_language"] = lang_code
                            break

            # Detect and apply subtitle policy (unless Custom Override is enabled)
            if self.custom_command_override_cb.isChecked():
                # Skip subtitle handling with custom override
                subtitle_decision = None
                file_data["subtitle_strategy"] = "Custom Override - disabled"
            else:
                subtitle_settings = {
                    "subtitle_handling": config.get_subtitle_handling(),
                    "warn_on_ass_mux": config.get_warn_on_ass_mux(),
                    "warn_on_burn": config.get_warn_on_burn()
                }
                subtitle_decision = process_file_subtitles(
                    source_file,
                    subtitle_settings,
                    ffmpeg_path,
                    ffprobe_path=None,  # Uses "ffprobe" from PATH by default
                    log_callback=lambda lev, msg: self._on_log(lev, msg)
                )
                file_data["subtitle_strategy"] = subtitle_decision.reason

            # Handle skip_file decision
            if subtitle_decision.action == "skip_file":
                file_data["status"] = "Skipped"
                if self.batch_stats:
                    self.batch_stats.add_file_result(
                        filename=source_file.name,
                        elapsed=0,
                        input_size=0,
                        output_size=0,
                        success=False,
                        skipped=True,
                    )
                skipped_count += 1
                continue

            if self.update_file_callback:
                self.update_file_callback(i, file_data)
            output_dir = (
                self.get_output_path_callback(source_file)
                if self.get_output_path_callback
                else source_file.parent
            )
            output_file = output_dir / f"{source_file.stem}{suffix}.mp4"
            if skip_existing and not file_data.get("reencode", False) and output_file.exists():
                self._on_log("INFO", f"Skipping (exists): {output_file.name}")
                file_data["status"] = "Skipped"
                if self.batch_stats:
                    self.batch_stats.add_file_result(
                        filename=source_file.name,
                        elapsed=0,
                        input_size=0,
                        output_size=0,
                        success=False,
                        skipped=True,
                    )
                skipped_count += 1
                continue
            file_data["status"] = "Encoding"
            if self.update_file_callback:
                self.update_file_callback(i, file_data)

            # Extract text-based subtitles to external files if policy requires it
            # (skip if Custom Override is enabled)
            extracted_subtitle_file = None
            if (not self.custom_command_override_cb.isChecked() and
                subtitle_decision and
                subtitle_decision.action == "external" and
                subtitle_decision.codec and
                subtitle_decision.stream_index is not None and
                not dry_run):
                # Only extract text-based subtitles (skip bitmap codecs like pgssub)
                if subtitle_decision.codec in TEXT_SUBTITLE_CODECS:
                    # Determine output extension based on codec
                    if subtitle_decision.codec in {"ass", "ssa"}:
                        sub_ext = ".ass"
                    else:
                        sub_ext = ".srt"

                    # Get language code and tag for Jellyfin-compatible naming
                    # Format: filename.tag.language.ext (e.g., episode.default.ja.ass)
                    lang_code = file_data.get("subtitle_language", "en")  # Default to 'en' if not detected
                    sub_tag = config.get_external_subtitle_tag()  # 'default' or 'forced'

                    # Build filename with tag and language following Jellyfin convention
                    external_sub_path = output_dir / f"{source_file.stem}{suffix}.{sub_tag}.{lang_code}{sub_ext}"

                    extracted_file, extraction_err = extract_text_subtitle_to_file(
                        ffmpeg_path=ffmpeg_path,
                        input_file=source_file,
                        subtitle_codec=subtitle_decision.codec,
                        subtitle_stream_id=subtitle_decision.stream_index,
                        output_file=external_sub_path
                    )
                    if extracted_file:
                        extracted_subtitle_file = extracted_file
                        self._on_log("INFO", f"Extracted {subtitle_decision.codec} subtitle ({lang_code}) to {extracted_file.name}")
                    elif extraction_err:
                        self._on_log("WARNING", f"Could not extract subtitle: {extraction_err}")

            subtitle_file = None
            if subtitle_track is not None and not dry_run:
                subtitle_file, err = extract_subtitle_stream(
                    ffmpeg_path=ffmpeg_path,
                    input_file=source_file,
                    subtitle_stream_id=subtitle_track,
                )
                if subtitle_file and subtitle_file.exists() and subtitle_file.stat().st_size == 0:
                    subtitle_file = None
                elif not subtitle_file:
                    self._on_log("WARNING", f"Subtitle extract issue: {err or 'unknown'}")
            if not command_template:
                self._on_log("ERROR", "No FFmpeg command")
                error_count += 1
                continue
            try:
                ffmpeg_args = parse_and_substitute_command(
                    command_template,
                    source_file,
                    output_file,
                    effective_audio,
                    subtitle_track,
                    subtitle_file,
                    lambda lev, msg: self._on_log(lev, msg),
                )
                if not ffmpeg_args:
                    file_data["status"] = "Error"
                    error_count += 1
                    continue

                # Apply app settings optimizations unless Custom Override is enabled
                if not self.custom_command_override_cb.isChecked():
                    # Remove subtitle filters that conflict with our subtitle policy decision
                    # Work directly with ffmpeg_args list to avoid quote escaping issues
                    ffmpeg_args = self._remove_conflicting_subtitle_filters_from_args(ffmpeg_args, subtitle_decision)
                    self._on_log("INFO", f"Applied app settings optimizations to command")
                else:
                    self._on_log("INFO", f"Custom Command Override enabled - using command as-is")
            except Exception as e:
                self._on_log("ERROR", str(e))
                file_data["status"] = "Error"
                error_count += 1
                continue
            self._progress_ui_throttle_last = None
            t0 = time.time()
            try:
                ok = self.encoder.encode_with_ffmpeg(
                    input_file=source_file,
                    output_file=output_file,
                    ffmpeg_args=ffmpeg_args,
                    subtitle_file=subtitle_file,
                    subtitle_stream_index=subtitle_track,
                    dry_run=dry_run,
                )
            except Exception as e:
                self._on_log("ERROR", str(e))
                ok = False
            elapsed = time.time() - t0
            if subtitle_file and subtitle_file.exists():
                try:
                    subtitle_file.unlink()
                except Exception:
                    pass
            if ok:
                file_data["status"] = "Complete"
                file_data["reencode"] = False
                out_sz = 0
                if output_file.exists():
                    file_data["output_path"] = output_file
                    out_sz = output_file.stat().st_size
                    file_data["output_size"] = out_sz
                if self.batch_stats:
                    self.batch_stats.add_file_result(
                        filename=source_file.name,
                        elapsed=elapsed,
                        input_size=source_file.stat().st_size if source_file.exists() else 0,
                        output_size=out_sz,
                        success=True,
                    )
                if not dry_run:
                    try:
                        record_successful_encode(out_sz, elapsed)
                    except Exception as e:
                        logger.warning(f"Could not update lifetime stats: {e}")
                completed_count += 1
            else:
                file_data["status"] = "Error"
                if self.batch_stats:
                    self.batch_stats.add_file_result(
                        filename=source_file.name,
                        elapsed=elapsed,
                        input_size=0,
                        output_size=0,
                        success=False,
                        error_msg="failed",
                    )
                error_count += 1
            if self.update_file_callback:
                self.update_file_callback(i, file_data)
            if self.batch_stats and completed_count >= 3:
                eta = self.batch_stats.calculate_batch_eta(len(files), completed_count)
                if eta:
                    self._on_log("INFO", f"Batch ETA: {eta}")
                    if "Batch ETA" not in self.progress_display.get_status():
                        self._bridge.status_text.emit(f"Batch ETA: {eta}")
        if self.batch_stats:
            summary = self.batch_stats.summary_text()
            self._bridge.toast.emit(summary, "error" if error_count > 0 else "success")
            BatchNotification.send_completion(
                completed=completed_count,
                skipped=skipped_count,
                errors=error_count,
                total=self.batch_stats.get_total_files(),
                elapsed_time=self.batch_stats.get_elapsed_time_str(),
            )
        self._bridge.reset_ui.emit()

    def _reset_ui_on_encode_end(self) -> None:
        self.is_encoding = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_display.reset()

    def _stop_encoding(self) -> None:
        def w():
            if self.encoder:
                self.encoder.stop()
            self.is_encoding = False

        threading.Thread(target=w, daemon=True).start()
