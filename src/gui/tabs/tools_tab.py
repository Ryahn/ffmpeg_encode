"""Batch tools: audio loudnorm and subtitle extraction (PyQt6)."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
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
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..widgets.log_viewer import LogViewer
from ..widgets.progress_bar import ProgressDisplay
from core.encoder import Encoder, EncodingProgress
from core.tools_audio_normalize import iter_media_files, run_normalize_file
from core.tools_subtitle_extract import extract_all_text_subtitles_for_file, iter_videos_for_subtitle_tool
from utils.config import config
from utils.ffmpeg_paths import resolve_ffprobe_path


class _ToolPanelBridge(QObject):
    log_msg = pyqtSignal(str, str)
    progress = pyqtSignal(object)
    status_text = pyqtSignal(str)
    batch_done = pyqtSignal()


class ToolsTab(QWidget):
    main_window: Any = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.encoder: Optional[Encoder] = None
        self._subtitle_encoder: Optional[Encoder] = None
        self._audio_thread: Optional[threading.Thread] = None
        self._sub_thread: Optional[threading.Thread] = None
        self._audio_abort = False
        self._sub_abort = False

        self._bridge_audio = _ToolPanelBridge(self)
        self._bridge_sub = _ToolPanelBridge(self)

        outer = QVBoxLayout(self)
        inner_tabs = QTabWidget()
        outer.addWidget(inner_tabs)

        self._audio_panel = self._build_audio_panel()
        self._sub_panel = self._build_subtitle_panel()
        inner_tabs.addTab(self._audio_panel, "Audio Normalizer")
        inner_tabs.addTab(self._sub_panel, "Extract Subtitles")

        self._bridge_audio.log_msg.connect(self._audio_log.add_log)
        self._bridge_audio.progress.connect(self._apply_audio_progress)
        self._bridge_audio.status_text.connect(self._audio_progress.set_status)
        self._bridge_audio.batch_done.connect(self._on_audio_batch_done)

        self._bridge_sub.log_msg.connect(self._sub_log.add_log)
        self._bridge_sub.progress.connect(self._apply_sub_progress)
        self._bridge_sub.status_text.connect(self._sub_progress.set_status)
        self._bridge_sub.batch_done.connect(self._on_sub_batch_done)

        self._init_encoder()
        self._sync_norm_run_enabled()

    def _init_encoder(self) -> None:
        ffmpeg_path = config.get_ffmpeg_path() or "ffmpeg"
        handbrake_path = config.get_handbrake_path() or "HandBrakeCLI"
        self.encoder = Encoder(
            ffmpeg_path=ffmpeg_path,
            handbrake_path=handbrake_path,
            progress_callback=self._on_encoder_progress_audio,
            log_callback=self._on_encoder_log_audio,
        )

    def _on_encoder_progress_audio(self, progress: EncodingProgress) -> None:
        self._bridge_audio.progress.emit(progress)

    def _on_encoder_log_audio(self, level: str, message: str) -> None:
        if level == "DEBUG" and not config.get_debug_logging():
            return
        self._bridge_audio.log_msg.emit(level, message)

    def _encoder_progress_sub(self, progress: EncodingProgress) -> None:
        self._bridge_sub.progress.emit(progress)

    def _encoder_log_sub(self, level: str, message: str) -> None:
        if level == "DEBUG" and not config.get_debug_logging():
            return
        self._bridge_sub.log_msg.emit(level, message)

    def _apply_audio_progress(self, progress: EncodingProgress) -> None:
        if progress.percent is not None:
            self._audio_progress.set_progress(progress.percent)
            t = f"{progress.percent:.1f}%"
            if progress.eta:
                t += f" — ETA: {progress.eta}"
            self._audio_progress.set_status(t)
        elif progress.time:
            t = f"Time: {progress.time}"
            if progress.speed:
                t += f" — {progress.speed:.2f}x"
            self._audio_progress.set_status(t)

    def _apply_sub_progress(self, progress: EncodingProgress) -> None:
        if progress.percent is not None:
            self._sub_progress.set_progress(progress.percent)
            t = f"{progress.percent:.1f}%"
            if progress.eta:
                t += f" — ETA: {progress.eta}"
            self._sub_progress.set_status(t)
        elif progress.time:
            t = f"Time: {progress.time}"
            if progress.speed:
                t += f" — {progress.speed:.2f}x"
            self._sub_progress.set_status(t)

    def _on_audio_batch_done(self) -> None:
        self._audio_run.setEnabled(True)
        self._audio_stop.setEnabled(False)
        self._audio_progress.set_status("Ready")

    def _on_sub_batch_done(self) -> None:
        self._subtitle_encoder = None
        self._sub_run.setEnabled(True)
        self._sub_stop.setEnabled(False)
        self._sub_progress.set_status("Ready")

    def _fallback_audio_codec_bitrate(self) -> tuple[str, int]:
        st = getattr(self.main_window, "ffmpeg_settings_tab", None)
        if st is not None:
            codec = st.audio_codec_combo.currentData() or "aac"
            return str(codec).strip().lower(), int(st.audio_bitrate_spinbox.value())
        return "aac", 192

    def _folder_row(self, line: QLineEdit, browse_title: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(line, stretch=1)

        def browse() -> None:
            d = QFileDialog.getExistingDirectory(self, browse_title, str(Path.home()))
            if d:
                line.setText(d)

        b = QPushButton("Browse")
        b.clicked.connect(browse)
        h.addWidget(b)
        return w

    def _build_audio_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(inner)

        folder_gb = QGroupBox("Folder")
        ff = QFormLayout(folder_gb)
        self._audio_folder = QLineEdit()
        ff.addRow("Folder:", self._folder_row(self._audio_folder, "Select folder"))
        self._audio_recursive = QCheckBox("Include subfolders")
        ff.addRow(self._audio_recursive)
        root.addWidget(folder_gb)

        loud_gb = QGroupBox("Loudness normalization")
        lv = QVBoxLayout(loud_gb)
        self._audio_norm_cb = QCheckBox(
            "Apply loudness normalization (FFmpeg single-pass loudnorm)"
        )
        self._audio_norm_cb.setChecked(config.get_audio_normalize_enabled())
        self._audio_norm_cb.toggled.connect(self._on_audio_norm_toggled)
        lv.addWidget(self._audio_norm_cb)
        form = QFormLayout()
        self._audio_I = QDoubleSpinBox()
        self._audio_I.setRange(-70.0, -5.0)
        self._audio_I.setDecimals(1)
        self._audio_I.setSingleStep(0.5)
        self._audio_I.setValue(config.get_audio_normalize_loudnorm_I())
        self._audio_I.valueChanged.connect(self._on_audio_loudnorm_values)
        form.addRow("Loudnorm target I (LUFS):", self._audio_I)
        self._audio_TP = QDoubleSpinBox()
        self._audio_TP.setRange(-9.0, 0.0)
        self._audio_TP.setDecimals(1)
        self._audio_TP.setSingleStep(0.5)
        self._audio_TP.setValue(config.get_audio_normalize_loudnorm_TP())
        self._audio_TP.valueChanged.connect(self._on_audio_loudnorm_values)
        form.addRow("Loudnorm true peak TP (dBTP):", self._audio_TP)
        self._audio_LRA = QDoubleSpinBox()
        self._audio_LRA.setRange(1.0, 20.0)
        self._audio_LRA.setDecimals(1)
        self._audio_LRA.setSingleStep(0.5)
        self._audio_LRA.setValue(config.get_audio_normalize_loudnorm_LRA())
        self._audio_LRA.valueChanged.connect(self._on_audio_loudnorm_values)
        form.addRow("Loudnorm loudness range LRA:", self._audio_LRA)
        lv.addLayout(form)
        self._audio_replace = QCheckBox("Replace original file")
        lv.addWidget(self._audio_replace)
        root.addWidget(loud_gb)

        btn_row = QHBoxLayout()
        self._audio_run = QPushButton("Run")
        self._audio_run.clicked.connect(self._start_audio_batch)
        self._audio_stop = QPushButton("Stop")
        self._audio_stop.clicked.connect(self._stop_audio_batch)
        self._audio_stop.setEnabled(False)
        btn_row.addWidget(self._audio_run)
        btn_row.addWidget(self._audio_stop)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self._audio_progress = ProgressDisplay()
        root.addWidget(self._audio_progress)
        self._audio_log = LogViewer(height=220)
        root.addWidget(self._audio_log)
        root.addStretch()

        lay.addWidget(scroll)
        self._sync_audio_loudnorm_spin_enabled()
        return panel

    def _build_subtitle_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(inner)

        folder_gb = QGroupBox("Folder")
        ff = QFormLayout(folder_gb)
        self._sub_folder = QLineEdit()
        ff.addRow("Folder:", self._folder_row(self._sub_folder, "Select folder"))
        self._sub_recursive = QCheckBox("Include subfolders")
        ff.addRow(self._sub_recursive)
        root.addWidget(folder_gb)

        note = QLabel(
            "Extracts text subtitles (SRT, ASS, WebVTT) next to each video. "
            "Bitmap subtitles are skipped. Output: VideoName.lang.Title.ext"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #888888; font-size: 12px;")
        root.addWidget(note)

        btn_row = QHBoxLayout()
        self._sub_run = QPushButton("Run")
        self._sub_run.clicked.connect(self._start_sub_batch)
        self._sub_stop = QPushButton("Stop")
        self._sub_stop.clicked.connect(self._stop_sub_batch)
        self._sub_stop.setEnabled(False)
        btn_row.addWidget(self._sub_run)
        btn_row.addWidget(self._sub_stop)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self._sub_progress = ProgressDisplay()
        root.addWidget(self._sub_progress)
        self._sub_log = LogViewer(height=220)
        root.addWidget(self._sub_log)
        root.addStretch()

        lay.addWidget(scroll)
        return panel

    def _on_audio_norm_toggled(self, checked: bool) -> None:
        config.set_audio_normalize_enabled(checked)
        self._sync_audio_loudnorm_spin_enabled()
        self._sync_norm_run_enabled()

    def _on_audio_loudnorm_values(self, _v: float = 0.0) -> None:
        config.set_audio_normalize_loudnorm_I(self._audio_I.value())
        config.set_audio_normalize_loudnorm_TP(self._audio_TP.value())
        config.set_audio_normalize_loudnorm_LRA(self._audio_LRA.value())

    def _sync_audio_loudnorm_spin_enabled(self) -> None:
        en = self._audio_norm_cb.isChecked()
        self._audio_I.setEnabled(en)
        self._audio_TP.setEnabled(en)
        self._audio_LRA.setEnabled(en)

    def _sync_norm_run_enabled(self) -> None:
        self._audio_run.setEnabled(self._audio_norm_cb.isChecked())

    def _other_batch_running(self) -> bool:
        if self._audio_thread and self._audio_thread.is_alive():
            return True
        if self._sub_thread and self._sub_thread.is_alive():
            return True
        return False

    def _start_audio_batch(self) -> None:
        if not self._audio_norm_cb.isChecked():
            QMessageBox.information(
                self,
                "Audio Normalizer",
                "Enable loudness normalization to run this tool.",
            )
            return
        folder = Path(self._audio_folder.text().strip())
        if not folder.is_dir():
            QMessageBox.warning(self, "Audio Normalizer", "Choose a valid folder.")
            return
        if self._other_batch_running():
            QMessageBox.warning(self, "Tools", "Another tool batch is still running.")
            return
        if self._audio_thread and self._audio_thread.is_alive():
            self._audio_thread.join(timeout=2.0)

        files = iter_media_files(folder, self._audio_recursive.isChecked())
        if not files:
            QMessageBox.information(self, "Audio Normalizer", "No supported video files in that folder.")
            return

        ffprobe = resolve_ffprobe_path()
        if not ffprobe:
            QMessageBox.critical(
                self,
                "Audio Normalizer",
                "ffprobe not found. Set FFprobe or FFmpeg in Settings → Executable Paths.",
            )
            return

        self._audio_log.clear()
        self._audio_progress.reset()
        self._audio_abort = False
        self._audio_run.setEnabled(False)
        self._audio_stop.setEnabled(True)
        if self.encoder:
            self.encoder.progress_callback = self._on_encoder_progress_audio
            self.encoder.log_callback = self._on_encoder_log_audio
            self.encoder.reset_stop_event()

        codec, br = self._fallback_audio_codec_bitrate()
        replace = self._audio_replace.isChecked()
        i_val = self._audio_I.value()
        tp_val = self._audio_TP.value()
        lra_val = self._audio_LRA.value()

        def work() -> None:
            total = len(files)
            ok = 0
            skipped = 0
            failed = 0
            try:
                for n, path in enumerate(files, start=1):
                    if self._audio_abort:
                        self._bridge_audio.log_msg.emit("INFO", "Stopped by user.")
                        break
                    if self.encoder:
                        self.encoder.reset_stop_event()

                    def run_ff(argv: list[str], out_path: Path) -> bool:
                        if self._audio_abort or not self.encoder:
                            return False
                        return self.encoder.run_ffmpeg_argv(argv, out_path)

                    self._bridge_audio.status_text.emit(f"File {n}/{total}: {path.name}")
                    self._bridge_audio.log_msg.emit("INFO", f"Processing ({n}/{total}): {path.name}")

                    result, msg = run_normalize_file(
                        ffprobe_exe=ffprobe,
                        input_path=path,
                        replace_original=replace,
                        integrated_lufs=i_val,
                        true_peak_db_tp=tp_val,
                        loudness_range=lra_val,
                        fallback_codec=codec,
                        fallback_bitrate=br,
                        run_ffmpeg=run_ff,
                    )
                    if result:
                        ok += 1
                        self._bridge_audio.log_msg.emit("SUCCESS", f"Done: {path.name}")
                    else:
                        if "expected exactly 1 audio stream" in (msg or ""):
                            skipped += 1
                            self._bridge_audio.log_msg.emit(
                                "WARNING",
                                f"Skip {path.name}: {msg}",
                            )
                        else:
                            failed += 1
                            self._bridge_audio.log_msg.emit(
                                "ERROR",
                                f"{path.name}: {msg or 'failed'}",
                            )

                    pct = 100.0 * n / max(total, 1)
                    pr = EncodingProgress()
                    pr.percent = pct
                    self._bridge_audio.progress.emit(pr)
            finally:
                self._bridge_audio.batch_done.emit()
                self._bridge_audio.log_msg.emit(
                    "INFO",
                    f"Finished: {ok} ok, {skipped} skipped, {failed} failed (of {total}).",
                )

        self._audio_thread = threading.Thread(target=work, daemon=True)
        self._audio_thread.start()

    def _stop_audio_batch(self) -> None:
        self._audio_abort = True
        if self.encoder:
            self.encoder.stop()

    def _start_sub_batch(self) -> None:
        folder = Path(self._sub_folder.text().strip())
        if not folder.is_dir():
            QMessageBox.warning(self, "Extract Subtitles", "Choose a valid folder.")
            return
        if self._other_batch_running():
            QMessageBox.warning(self, "Tools", "Another tool batch is still running.")
            return
        if self._sub_thread and self._sub_thread.is_alive():
            self._sub_thread.join(timeout=2.0)

        videos = iter_videos_for_subtitle_tool(folder, self._sub_recursive.isChecked())
        if not videos:
            QMessageBox.information(self, "Extract Subtitles", "No supported video files in that folder.")
            return

        ffprobe = resolve_ffprobe_path()
        if not ffprobe:
            QMessageBox.critical(
                self,
                "Extract Subtitles",
                "ffprobe not found. Set FFprobe or FFmpeg in Settings → Executable Paths.",
            )
            return

        self._sub_log.clear()
        self._sub_progress.reset()
        self._sub_abort = False
        self._sub_run.setEnabled(False)
        self._sub_stop.setEnabled(True)

        self._subtitle_encoder = Encoder(
            ffmpeg_path=config.get_ffmpeg_path() or "ffmpeg",
            handbrake_path=config.get_handbrake_path() or "HandBrakeCLI",
            progress_callback=self._encoder_progress_sub,
            log_callback=self._encoder_log_sub,
        )
        sub_enc = self._subtitle_encoder

        def work() -> None:
            total = len(videos)
            try:
                for n, path in enumerate(videos, start=1):
                    if self._sub_abort:
                        self._bridge_sub.log_msg.emit("INFO", "Stopped by user.")
                        break
                    sub_enc.reset_stop_event()

                    def run_ff(argv: list[str], out_path: Path) -> bool:
                        if self._sub_abort:
                            return False
                        return sub_enc.run_ffmpeg_argv(argv, out_path)

                    self._bridge_sub.status_text.emit(f"File {n}/{total}: {path.name}")
                    self._bridge_sub.log_msg.emit("INFO", f"({n}/{total}): {path.name}")

                    def log_cb(level: str, msg: str) -> None:
                        self._bridge_sub.log_msg.emit(level, msg)

                    extract_all_text_subtitles_for_file(
                        ffprobe_path=ffprobe,
                        video_path=path,
                        log=log_cb,
                        run_ffmpeg=run_ff,
                    )

                    pct = 100.0 * n / max(total, 1)
                    pr = EncodingProgress()
                    pr.percent = pct
                    self._bridge_sub.progress.emit(pr)
            finally:
                self._bridge_sub.batch_done.emit()

        self._sub_thread = threading.Thread(target=work, daemon=True)
        self._sub_thread.start()

    def _stop_sub_batch(self) -> None:
        self._sub_abort = True
        if self._subtitle_encoder:
            self._subtitle_encoder.stop()

    def shutdown_tools(self) -> None:
        """Stop any in-progress Tools batch (e.g. on app exit)."""
        self._stop_audio_batch()
        self._stop_sub_batch()

    def refresh_loudnorm_from_config(self) -> None:
        """If Settings / FFmpeg tab changed loudnorm, optionally sync (when visible)."""
        self._audio_norm_cb.blockSignals(True)
        self._audio_I.blockSignals(True)
        self._audio_TP.blockSignals(True)
        self._audio_LRA.blockSignals(True)
        try:
            self._audio_norm_cb.setChecked(config.get_audio_normalize_enabled())
            self._audio_I.setValue(config.get_audio_normalize_loudnorm_I())
            self._audio_TP.setValue(config.get_audio_normalize_loudnorm_TP())
            self._audio_LRA.setValue(config.get_audio_normalize_loudnorm_LRA())
        finally:
            self._audio_norm_cb.blockSignals(False)
            self._audio_I.blockSignals(False)
            self._audio_TP.blockSignals(False)
            self._audio_LRA.blockSignals(False)
        self._sync_audio_loudnorm_spin_enabled()
        self._sync_norm_run_enabled()
