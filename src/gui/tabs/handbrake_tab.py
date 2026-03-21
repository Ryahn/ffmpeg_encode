"""HandBrake encoding tab (PyQt6)."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ..widgets.log_viewer import LogViewer
from ..widgets.progress_bar import ProgressDisplay
from core.batch_stats import BatchStats
from core.encoder import Encoder, EncodingProgress, format_cli_argv
from core.notifications import BatchNotification
from core.preset_parser import PresetParser
from core.track_analyzer import TrackAnalyzer
from core.track_selection import audio_mkv_stream_id_for_ordinal, compute_effective_tracks
from storage import record_successful_encode
from utils.config import config
from utils.logger import logger


class _HandBrakeUiBridge(QObject):
    log_msg = pyqtSignal(str, str)
    progress = pyqtSignal(object)
    reset_ui = pyqtSignal()
    toast = pyqtSignal(str, str)
    status_text = pyqtSignal(str)


class HandBrakeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None
        self.preset_parser: Optional[PresetParser] = None
        self.preset_path: Optional[Path] = None
        self.encoder: Optional[Encoder] = None
        self.track_analyzer: Optional[TrackAnalyzer] = None
        self.encoding_thread: Optional[threading.Thread] = None
        self.is_encoding = False
        self.batch_stats: Optional[BatchStats] = None
        self.get_files_callback: Optional[Callable] = None
        self.update_file_callback: Optional[Callable] = None
        self.get_output_path_callback: Optional[Callable] = None

        self._bridge = _HandBrakeUiBridge(self)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_command_preview_display)

        root = QVBoxLayout(self)
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("HandBrake Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(300)
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        preset_row.addWidget(self.preset_combo)
        preset_row.addWidget(self._btn("Load Preset", self._load_preset))
        self.preset_info_label = QLabel("")
        preset_row.addWidget(self.preset_info_label)
        root.addLayout(preset_row)

        pv = QHBoxLayout()
        pv.addWidget(QLabel("<b>HandBrake CLI preview</b> (first queued file)"))
        pv.addWidget(self._btn("Copy", self._copy_command_preview))
        root.addLayout(pv)
        self.command_preview = QPlainTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setMinimumHeight(72)
        self.command_preview.setPlaceholderText("Load a preset and add files to see the command.")
        root.addWidget(self.command_preview)

        opt = QHBoxLayout()
        self.dry_run_cb = QCheckBox("Dry Run")
        self.skip_cb = QCheckBox("Skip Existing")
        self.skip_cb.setChecked(config.get_skip_existing())
        self.skip_cb.toggled.connect(lambda v: config.set_skip_existing(v))
        opt.addWidget(self.dry_run_cb)
        opt.addWidget(self.skip_cb)
        opt.addWidget(QLabel("Output Suffix:"))
        self.suffix_entry = QLineEdit(config.get_default_output_suffix())
        self.suffix_entry.setMaximumWidth(160)
        self.suffix_entry.textChanged.connect(self._schedule_preview_update)
        opt.addWidget(self.suffix_entry)
        opt.addWidget(QLabel("Mode:"))
        self._mode_seq = QRadioButton("Sequential")
        self._mode_par = QRadioButton("Parallel")
        if config.get_encoding_mode() == "parallel":
            self._mode_par.setChecked(True)
        else:
            self._mode_seq.setChecked(True)
        self._mode_seq.toggled.connect(self._persist_mode)
        self._mode_par.toggled.connect(self._persist_mode)
        opt.addWidget(self._mode_seq)
        opt.addWidget(self._mode_par)
        opt.addStretch()
        self.start_btn = self._btn("Start Encoding", self._start_encoding)
        opt.addWidget(self.start_btn)
        self.stop_btn = self._btn("Stop", self._stop_encoding)
        self.stop_btn.setEnabled(False)
        opt.addWidget(self.stop_btn)
        root.addLayout(opt)

        self.progress_display = ProgressDisplay()
        root.addWidget(self.progress_display)

        log_fr = QFrame()
        log_l = QVBoxLayout(log_fr)
        self.log_viewer = LogViewer(height=200)
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("<b>Encoding Log</b>"))
        hdr.addWidget(self._btn("Copy", lambda: self.log_viewer.copy_to_clipboard()))
        log_l.addLayout(hdr)
        log_l.addWidget(self.log_viewer)
        root.addWidget(log_fr, stretch=1)

        self._bridge.log_msg.connect(self._append_log)
        self._bridge.progress.connect(self._apply_progress)
        self._bridge.reset_ui.connect(self._reset_ui_on_encode_end)
        self._bridge.toast.connect(self._emit_toast)
        self._bridge.status_text.connect(self.progress_display.set_status)

        self._init_encoder()
        self._refresh_preset_dropdown()
        self._load_last_preset()
        self._update_command_preview_display()

    def on_files_changed(self) -> None:
        self._schedule_preview_update()

    def _schedule_preview_update(self) -> None:
        self._preview_timer.start(250)

    def _btn(self, text, slot):
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b

    def _persist_mode(self) -> None:
        config.set_encoding_mode("parallel" if self._mode_par.isChecked() else "sequential")

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
        self._schedule_preview_update()

    def _refresh_preset_dropdown(self) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("")
        for name in config.get_saved_presets().keys():
            self.preset_combo.addItem(name)
        self.preset_combo.blockSignals(False)

    def _load_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select HandBrake preset JSON file",
            "",
            "JSON files (*.json);;All files (*.*)",
        )
        if path:
            try:
                self._load_preset_from_path(Path(path), save=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load preset: {e}")

    def _load_preset_from_path(self, preset_path: Path, save: bool = False) -> None:
        self.preset_path = preset_path
        self.preset_parser = PresetParser(self.preset_path)
        preset_name = self.preset_parser.get_preset_name()
        preset_desc = self.preset_parser.get_preset_description()
        if save:
            config.save_preset(preset_name, preset_path)
            config.set_last_used_preset(preset_name)
            self._refresh_preset_dropdown()
            idx = self.preset_combo.findText(preset_name)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
        else:
            config.set_last_used_preset(preset_name)
        self.preset_info_label.setText(f"Description: {preset_desc}" if preset_desc else "")
        self._on_log("INFO", f"Loaded preset: {preset_name}")
        self._schedule_preview_update()

    def _on_preset_selected(self, choice: str) -> None:
        if not choice:
            return
        preset_path = config.get_preset_path(choice)
        if preset_path:
            try:
                self._load_preset_from_path(preset_path, save=False)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load preset: {e}")
                self._refresh_preset_dropdown()
                self.preset_combo.setCurrentIndex(0)

    def _load_last_preset(self) -> None:
        last = config.get_last_used_preset()
        if last:
            pp = config.get_preset_path(last)
            if pp:
                try:
                    self._load_preset_from_path(pp, save=False)
                    idx = self.preset_combo.findText(last)
                    if idx >= 0:
                        self.preset_combo.setCurrentIndex(idx)
                except Exception:
                    pass

    def _resolve_tracks_for_preview(self, file_data: dict, source_file: Path) -> tuple[Optional[int], Optional[int]]:
        audio_track = file_data.get("audio_track")
        subtitle_track = file_data.get("subtitle_track")
        if file_data.get("tracks_from_user"):
            return audio_track, subtitle_track
        if audio_track is not None:
            return audio_track, subtitle_track
        if not self.track_analyzer:
            return None, subtitle_track
        try:
            tracks = self.track_analyzer.analyze_tracks(source_file)
            if tracks.get("error"):
                return None, subtitle_track
            return compute_effective_tracks(
                tracks,
                self.track_analyzer,
                log_info=lambda _msg: None,
                source_label=source_file.name,
            )
        except Exception:
            return None, subtitle_track

    def _update_command_preview_display(self) -> None:
        if not self.preset_parser or not self.preset_path:
            self.command_preview.setPlainText("Load a HandBrake preset to see the CLI command.")
            return
        if not self.encoder:
            self.command_preview.setPlainText("Encoder not initialized.")
            return
        if not self.get_files_callback:
            self.command_preview.setPlainText("Add files on the Files tab to see input/output paths.")
            return
        files = self.get_files_callback()
        if not files:
            self.command_preview.setPlainText("Add files on the Files tab to see input/output paths.")
            return
        fd = files[0]
        source_file = Path(fd["path"])
        suffix = (self.suffix_entry.text() or "").strip() or config.get_default_output_suffix()
        if self.get_output_path_callback:
            output_dir = self.get_output_path_callback(source_file)
        else:
            output_dir = source_file.parent
        output_file = output_dir / f"{source_file.stem}{suffix}.mp4"

        audio_track, subtitle_track = self._resolve_tracks_for_preview(fd, source_file)
        if audio_track is None:
            self.command_preview.setPlainText(
                "Could not determine the audio track for the first queued file.\n"
                'Use "Load tracks" on the Files tab, or check that mkvinfo/ffprobe is configured in Settings.\n\n'
                f"Output path would be:\n{output_file}"
            )
            return

        argv = self.encoder.build_handbrake_argv(
            input_file=source_file,
            output_file=output_file,
            preset_file=self.preset_path,
            preset_name=self.preset_parser.get_preset_name(),
            audio_track=audio_track,
            subtitle_track=subtitle_track,
        )
        self.command_preview.setPlainText(format_cli_argv(argv))

    def _copy_command_preview(self) -> None:
        text = self.command_preview.toPlainText().strip()
        if not text or text.startswith("Load a HandBrake") or text.startswith("Add files"):
            self._show_toast("Nothing to copy yet.", "warning")
            return
        if text.startswith("Could not determine"):
            self._show_toast("Fix track analysis before copying.", "warning")
            return
        QGuiApplication.clipboard().setText(text)
        self._show_toast("Command copied to clipboard.", "success")

    def _append_log(self, level: str, message: str) -> None:
        self.log_viewer.add_log(level, message)

    def _apply_progress(self, progress: EncodingProgress) -> None:
        if progress.percent is not None:
            self.progress_display.set_progress(progress.percent)
            status = f"{progress.percent:.1f}%"
            if progress.eta:
                status += f" - ETA: {progress.eta}"
            self.progress_display.set_status(status)
        elif progress.time:
            status = f"Time: {progress.time}"
            if progress.speed:
                status += f" - Speed: {progress.speed:.2f}x"
            self.progress_display.set_status(status)

    def _on_progress(self, progress: EncodingProgress) -> None:
        self._bridge.progress.emit(progress)

    def _on_log(self, level: str, message: str) -> None:
        if level == "DEBUG" and not config.get_debug_logging():
            return
        self._bridge.log_msg.emit(level, message)
        prefixed = f"[HandBrake] {message}"
        if level == "ERROR":
            logger.error(prefixed)
        elif level == "WARNING":
            logger.warning(prefixed)
        elif level == "SUCCESS":
            logger.success(prefixed)
        elif level == "DEBUG":
            logger.debug(prefixed)
        else:
            logger.info(prefixed)

    def _emit_toast(self, message: str, kind: str) -> None:
        w = self.main_window or self.window()
        if hasattr(w, "toast_manager"):
            w.toast_manager.show(message, message_type=kind, duration=5)

    def _show_toast(self, message: str, kind: str = "warning") -> None:
        self._emit_toast(message, kind)

    def _start_encoding(self) -> None:
        if not self.preset_parser:
            self._show_toast("Please load a HandBrake preset first", "warning")
            return
        if not self.get_files_callback:
            self._show_toast("No files available. Please scan for files first.", "warning")
            return
        files = self.get_files_callback()
        if not files:
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
        self.encoding_thread = threading.Thread(target=self._encode_files, args=(files,), daemon=True)
        self.encoding_thread.start()

    def _encode_files(self, files) -> None:
        dry_run = self.dry_run_cb.isChecked()
        skip_existing = self.skip_cb.isChecked()
        suffix = self.suffix_entry.text()
        completed_count = 0
        skipped_count = 0
        error_count = 0
        for i, file_data in enumerate(files):
            if not self.is_encoding:
                break
            source_file = Path(file_data["path"])
            if file_data.get("tracks_from_user"):
                stored_audio = file_data.get("audio_track")
                if stored_audio is None:
                    self._on_log(
                        "ERROR",
                        f"No audio track set for {source_file.name} (Set tracks chose no audio).",
                    )
                    file_data["status"] = "Error"
                    continue
                effective_audio = stored_audio
                subtitle_track = file_data.get("subtitle_track")
                self._on_log("INFO", f"Using tracks from file list for: {source_file.name}")
                file_data["audio_track"] = effective_audio
                file_data["subtitle_track"] = subtitle_track
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
                    self._on_log("WARNING", f"No English audio track found for: {source_file.name}")
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
                file_data["audio_ffmpeg_stream_index"] = audio_mkv_stream_id_for_ordinal(
                    tracks, effective_audio
                )
            stream_idx = file_data.get("audio_ffmpeg_stream_index")
            hb_audio = stream_idx + 1 if stream_idx is not None else effective_audio
            if self.update_file_callback:
                self.update_file_callback(i, file_data)
            if self.get_output_path_callback:
                output_dir = self.get_output_path_callback(source_file)
            else:
                output_dir = source_file.parent
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
            file_start_time = time.time()
            success = self.encoder.encode_with_handbrake(
                input_file=source_file,
                output_file=output_file,
                preset_file=self.preset_path,
                preset_name=self.preset_parser.get_preset_name(),
                audio_track=hb_audio,
                subtitle_track=subtitle_track,
                dry_run=dry_run,
            )
            file_elapsed_time = time.time() - file_start_time
            if success:
                file_data["status"] = "Complete"
                file_data["reencode"] = False
                input_size = source_file.stat().st_size if source_file.exists() else 0
                output_size = 0
                if output_file.exists():
                    file_data["output_path"] = output_file
                    output_size = output_file.stat().st_size
                    file_data["output_size"] = output_size
                if self.batch_stats:
                    self.batch_stats.add_file_result(
                        filename=source_file.name,
                        elapsed=file_elapsed_time,
                        input_size=input_size,
                        output_size=output_size,
                        success=True,
                    )
                if not dry_run:
                    try:
                        record_successful_encode(output_size, file_elapsed_time)
                    except Exception as e:
                        logger.warning(f"Could not update lifetime stats: {e}")
                completed_count += 1
            else:
                file_data["status"] = "Error"
                if self.batch_stats:
                    self.batch_stats.add_file_result(
                        filename=source_file.name,
                        elapsed=0,
                        input_size=0,
                        output_size=0,
                        success=False,
                        error_msg="Encoding failed",
                    )
                error_count += 1
            if self.update_file_callback:
                self.update_file_callback(i, file_data)
            if self.batch_stats and completed_count >= 3:
                eta = self.batch_stats.calculate_batch_eta(len(files), completed_count)
                if eta:
                    self._on_log("INFO", f"Batch ETA: {eta}")
                    cur = self.progress_display.get_status()
                    if "Batch ETA" not in cur:
                        self._bridge.status_text.emit(f"Batch ETA: {eta}")

        if self.batch_stats:
            summary = self.batch_stats.summary_text()
            toast_type = "error" if error_count > 0 else "success"
            self._bridge.toast.emit(summary, toast_type)
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
        def stop_worker():
            if self.encoder:
                self.encoder.stop()
            self.is_encoding = False

        threading.Thread(target=stop_worker, daemon=True).start()
