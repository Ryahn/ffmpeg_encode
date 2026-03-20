"""Files tab for managing video files (PyQt6)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..dialogs.set_tracks_dialog import show_set_tracks_dialog
from ..widgets.file_list import FileListWidget
from core.file_scanner import FileScanner
from core.track_analyzer import TrackAnalyzer
from core.track_selection import compute_effective_tracks
from utils.config import config

logger = logging.getLogger(__name__)


class _AnalyzeOneWorker(QObject):
    """Runs analyze_tracks() for a single file off the GUI thread."""

    finished = pyqtSignal(object, object)  # (tracks_dict, source_file)

    def __init__(self, source_file: Path, analyzer: TrackAnalyzer):
        super().__init__()
        self._source_file = source_file
        self._analyzer = analyzer

    def run(self) -> None:
        try:
            tracks = self._analyzer.analyze_tracks(self._source_file)
        except Exception:
            raise

        self.finished.emit(tracks, self._source_file)


class _LoadTracksWorker(QObject):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list, list, str)

    def __init__(self, indices: List[int], files: list, analyzer: TrackAnalyzer):
        super().__init__()
        self._indices = indices
        self._files = files
        self._analyzer = analyzer

    def run(self) -> None:
        failed: List[str] = []
        results: List[dict] = []
        scope = "selected" if len(self._indices) < len(self._files) else "all"
        for pos, idx in enumerate(self._indices):
            source_file = Path(self._files[idx]["path"])
            self.progress.emit(pos + 1, len(self._indices), scope)
            tracks = self._analyzer.analyze_tracks(source_file)
            if tracks.get("error"):
                failed.append(source_file.name)
                continue
            effective_audio, subtitle_track = compute_effective_tracks(tracks, self._analyzer)
            if effective_audio is not None:
                results.append(
                    {
                        "idx": idx,
                        "audio": effective_audio,
                        "subtitle": subtitle_track,
                        "no_audio_name": None,
                    }
                )
            else:
                results.append(
                    {
                        "idx": idx,
                        "audio": None,
                        "subtitle": None,
                        "no_audio_name": source_file.name,
                    }
                )
        self.finished.emit(results, failed, scope)


class FilesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanner = FileScanner()
        self.scan_folder: Optional[Path] = None
        self.output_folder: Optional[Path] = None
        self.on_files_changed: Optional[Callable] = None
        self.on_status: Optional[Callable[[str], None]] = None
        self._load_tracks_busy = False
        self._load_thread: Optional[QThread] = None
        self._analyze_thread: Optional[QThread] = None
        self._analyze_worker: Optional[_AnalyzeOneWorker] = None
        self._set_tracks_btn: Optional[QPushButton] = None

        mkvinfo_path = config.get_mkvinfo_path() or "mkvinfo"
        self.track_analyzer = TrackAnalyzer(
            mkvinfo_path=mkvinfo_path if mkvinfo_path != "mkvinfo" else None
        )

        root = QVBoxLayout(self)
        controls = QFrame()
        cv = QVBoxLayout(controls)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Scan Folder:"))
        self.scan_folder_label = QLabel("Not selected")
        self.scan_folder_label.setMinimumWidth(300)
        self.scan_folder_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        row1.addWidget(self.scan_folder_label)
        row1.addWidget(self._btn("Browse", self._browse_scan_folder))
        row1.addWidget(self._btn("Scan", self._scan_folder))
        cv.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Save to:"))
        self._dest_group = QButtonGroup(self)
        self._radio_input = QRadioButton("Same folder as input file")
        self._radio_custom = QRadioButton("Output folder")
        self._dest_group.addButton(self._radio_input)
        self._dest_group.addButton(self._radio_custom)
        if config.get_output_destination() == "custom_folder":
            self._radio_custom.setChecked(True)
        else:
            self._radio_input.setChecked(True)
        self._radio_input.toggled.connect(self._on_destination_toggled)
        self._radio_custom.toggled.connect(self._on_destination_toggled)
        row2.addWidget(self._radio_input)
        row2.addWidget(self._radio_custom)
        self.output_folder_label = QLabel("Not selected")
        self.output_folder_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        row2.addWidget(self.output_folder_label, stretch=1)
        row2.addWidget(self._btn("Select output folder", self._browse_output_folder))
        row2.addWidget(self._btn("Clear", self._clear_output_folder))
        cv.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Strip leading path segments:"))
        self.strip_entry = QLineEdit(str(config.get_strip_leading_path_segments()))
        self.strip_entry.setMaximumWidth(60)
        self.strip_entry.textChanged.connect(self._on_strip_changed)
        row3.addWidget(self.strip_entry)
        self.preview_label = QLabel("Result: (select Output folder to see preview)")
        self.preview_label.setWordWrap(True)
        self.preview_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        row3.addWidget(self.preview_label, stretch=1)
        cv.addLayout(row3)

        root.addWidget(controls)

        self.file_list = FileListWidget(self)
        self.file_list.on_paths_dropped = self._on_paths_dropped
        root.addWidget(self.file_list, stretch=1)

        bottom = QHBoxLayout()
        for text, slot in [
            ("Add Files", self._add_files),
            ("Remove Selected", self._remove_selected),
            ("Clear All", self._clear_all),
            ("Select All", self._select_all),
            ("Deselect All", self._deselect_all),
        ]:
            bottom.addWidget(self._btn(text, slot))
        root.addLayout(bottom)

        batch = QHBoxLayout()
        self._set_tracks_btn = self._btn("Set tracks…", self._open_set_tracks_dialog)
        batch.addWidget(self._set_tracks_btn)
        self.load_tracks_btn = self._btn("Load tracks", self._load_tracks)
        batch.addWidget(self.load_tracks_btn)
        batch.addWidget(self._btn("Mark for re-encode", self._mark_for_reencode))
        batch.addWidget(self._btn("Clear re-encode", self._clear_reencode_marks))
        root.addLayout(batch)

        last_scan = config.get_last_scan_folder()
        if last_scan and Path(last_scan).exists():
            self.scan_folder = Path(last_scan)
            self.scan_folder_label.setText(str(self.scan_folder))
        dest = config.get_output_destination()
        if dest == "custom_folder":
            of = config.get_default_output_folder()
            if of and Path(of).exists():
                self.output_folder = Path(of)
                self.output_folder_label.setText(str(self.output_folder))
        self._update_output_path_visibility()
        self._update_preview()

    def reload_from_config(self) -> None:
        """Refresh paths and strip count from disk config (e.g. after editing Settings)."""
        mkvinfo_path = config.get_mkvinfo_path() or "mkvinfo"
        self.track_analyzer = TrackAnalyzer(
            mkvinfo_path=mkvinfo_path if mkvinfo_path != "mkvinfo" else None
        )
        self.strip_entry.blockSignals(True)
        self.strip_entry.setText(str(config.get_strip_leading_path_segments()))
        self.strip_entry.blockSignals(False)
        last_scan = config.get_last_scan_folder()
        if last_scan and Path(last_scan).exists():
            self.scan_folder = Path(last_scan)
            self.scan_folder_label.setText(str(self.scan_folder))
        else:
            self.scan_folder = None
            self.scan_folder_label.setText("Not selected")
        if config.get_output_destination() == "custom_folder":
            self._radio_custom.setChecked(True)
        else:
            self._radio_input.setChecked(True)
        of = config.get_default_output_folder()
        if of and Path(of).exists():
            self.output_folder = Path(of)
            self.output_folder_label.setText(str(self.output_folder))
        else:
            self.output_folder = None
            self.output_folder_label.setText("Not selected")
        self._update_output_path_visibility()
        self._update_preview()

    def _btn(self, text: str, slot) -> QPushButton:
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b

    def _show_toast(self, message: str, message_type: str = "info") -> None:
        w = self.window()
        if hasattr(w, "toast_manager"):
            w.toast_manager.show(message, message_type=message_type, duration=3)

    def _on_destination_toggled(self) -> None:
        if self._radio_custom.isChecked():
            config.set_output_destination("custom_folder")
        else:
            config.set_output_destination("input_folder")
        self._update_output_path_visibility()
        self._update_preview()

    def _on_strip_changed(self) -> None:
        try:
            raw = self.strip_entry.text().strip()
            n = int(raw) if raw else 0
            n = max(0, min(99, n))
            config.set_strip_leading_path_segments(n)
        except ValueError:
            pass
        self._update_preview()

    def _compute_preview_path(self) -> Optional[str]:
        if not self._radio_custom.isChecked() or not self.output_folder:
            return None
        suffix = config.get_default_output_suffix()
        strip_n = config.get_strip_leading_path_segments()
        files = self.file_list.get_files()
        if files:
            roots_seen = set()
            previews = []
            for fd in files[:3]:
                source_file = Path(fd["path"])
                root = fd.get("root")
                if root is not None:
                    roots_seen.add(root)
                    try:
                        rel = source_file.relative_to(root)
                        parts = rel.parent.parts
                        remaining = parts[strip_n:]
                        od = (
                            self.output_folder / Path(*remaining)
                            if remaining
                            else self.output_folder
                        )
                        previews.append(str(od / f"{source_file.stem}{suffix}.mp4"))
                    except ValueError:
                        previews.append(
                            str(self.output_folder / source_file.parent.name / f"{source_file.stem}{suffix}.mp4")
                        )
                elif self.scan_folder:
                    try:
                        rel = source_file.relative_to(self.scan_folder)
                        parts = rel.parent.parts
                        remaining = parts[strip_n:]
                        od = (
                            self.output_folder / Path(*remaining)
                            if remaining
                            else self.output_folder
                        )
                        previews.append(str(od / f"{source_file.stem}{suffix}.mp4"))
                    except ValueError:
                        previews.append(str(self.output_folder / f"{source_file.stem}{suffix}.mp4"))
                else:
                    od = self.output_folder / source_file.parent.name
                    previews.append(str(od / f"{source_file.stem}{suffix}.mp4"))
            if len(roots_seen) > 1 or len(previews) > 1:
                return " | ".join(previews[:2]) + (" ..." if len(previews) > 2 else "")
            return previews[0] if previews else str(self.output_folder / f"file{suffix}.mp4") + " (example)"
        parts = ["Subfolder", "Another"]
        remaining = parts[strip_n:] if strip_n < len(parts) else []
        ex = (
            self.output_folder / Path(*remaining) / f"file{suffix}.mp4"
            if remaining
            else self.output_folder / f"file{suffix}.mp4"
        )
        return str(ex) + " (example)"

    def _update_preview(self) -> None:
        p = self._compute_preview_path()
        if p:
            text = f"Result: {p}"
            self.preview_label.setText(text)
            self.preview_label.setToolTip(text)
        else:
            self.preview_label.setText("Result: (select Output folder to see preview)")
            self.preview_label.setToolTip("")

    def _update_output_path_visibility(self) -> None:
        custom = self._radio_custom.isChecked()
        self.strip_entry.setEnabled(custom)

    def _browse_scan_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select folder to scan for video files")
        if d:
            self.scan_folder = Path(d)
            self.scan_folder_label.setText(str(self.scan_folder))
            config.set_last_scan_folder(str(self.scan_folder))
            self._update_preview()

    def _browse_output_folder(self) -> None:
        self._radio_custom.setChecked(True)
        d = QFileDialog.getExistingDirectory(self, "Select output folder")
        if d:
            self.output_folder = Path(d)
            self.output_folder_label.setText(str(self.output_folder))
            config.set_output_destination("custom_folder")
            config.set_default_output_folder(str(self.output_folder))
            self._update_preview()

    def _clear_output_folder(self) -> None:
        self.output_folder = None
        self.output_folder_label.setText("Not selected")
        config.set_default_output_folder("")
        self._update_preview()

    def _ingest_local_paths(self, paths: List[Path]) -> int:
        """Add files or scan dropped/selected paths. Returns count of list entries added."""
        count = 0
        for raw in paths:
            try:
                path = raw.resolve()
            except OSError:
                path = raw
            if not path.exists():
                continue
            if path.is_file():
                if self.scanner.is_video_file(path):
                    root = path.parent.parent if path.parent != path else path.parent
                    self.file_list.add_file(path, root=root)
                    count += 1
            elif path.is_dir():
                found = self.scanner.scan_directory(path, recursive=True)
                for fp in found:
                    self.file_list.add_file(fp, relative_to=path, root=path)
                    count += 1
        return count

    def _on_paths_dropped(self, paths: List[Path]) -> None:
        n = self._ingest_local_paths(paths)
        if n > 0:
            if self.on_files_changed:
                self.on_files_changed()
            self._update_preview()
            self._show_toast(f"Added {n} item(s) from drop", "success")
        elif paths:
            self._show_toast("No video files found in the drop.", "warning")

    def _scan_folder(self) -> None:
        if not self.scan_folder:
            self._show_toast("Please select a scan folder first", "warning")
            return
        self.file_list.clear()
        files = self.scanner.scan_directory(self.scan_folder, recursive=True)
        for fp in files:
            self.file_list.add_file(fp, relative_to=self.scan_folder, root=self.scan_folder)
        if self.on_files_changed:
            self.on_files_changed()
        self._update_preview()
        self._show_toast(f"Found {len(files)} video file(s)", "success")

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select video files",
            "",
            "Video files (*.mkv *.mp4 *.mov *.avi *.m4v *.flv *.wmv *.webm);;All files (*.*)",
        )
        if not paths:
            return
        n = self._ingest_local_paths([Path(p) for p in paths])
        if n > 0:
            if self.on_files_changed:
                self.on_files_changed()
            self._update_preview()
        else:
            self._show_toast("No supported video files in selection.", "warning")

    def _remove_selected(self) -> None:
        n = self.file_list.remove_selected_files()
        if n > 0:
            if self.on_files_changed:
                self.on_files_changed()
            self._update_preview()
            self._show_toast(f"Removed {n} file(s) from the list.", "info")
        else:
            self._show_toast("Please select one or more files to remove.", "warning")

    def _clear_all(self) -> None:
        self.file_list.clear()
        if self.on_files_changed:
            self.on_files_changed()
        self._update_preview()

    def _select_all(self) -> None:
        self.file_list.select_all()

    def _deselect_all(self) -> None:
        self.file_list.deselect_all()

    def _mark_for_reencode(self) -> None:
        indices = self.file_list.get_action_target_indices()
        if not indices:
            QMessageBox.warning(
                self,
                "No selection",
                "Select one or more files (click rows or use the checkbox column).",
            )
            return
        count = self.file_list.set_reencode_for_indices(indices, True)
        QMessageBox.information(
            self,
            "Re-encode",
            f"Marked {count} file(s). They will be encoded even if the output file already exists.",
        )

    def _clear_reencode_marks(self) -> None:
        indices = self.file_list.get_action_target_indices()
        if not indices:
            indices = list(range(self.file_list.get_file_count()))
        if not indices:
            return
        count = self.file_list.set_reencode_for_indices(indices, False)
        self._show_toast(f"Cleared re-encode mark on {count} file(s).", "info")

    def _load_tracks(self) -> None:
        if self._load_tracks_busy:
            return
        files = self.file_list.get_files()
        if not files:
            self._show_toast("Add files to the list first.", "warning")
            return
        if not self.track_analyzer.mkvinfo_path and not self.track_analyzer.ffprobe_path:
            QMessageBox.critical(
                self,
                "Track analysis unavailable",
                "Install MKVToolNix (mkvinfo) for MKV files, or FFmpeg (ffprobe) for other formats.",
            )
            return
        indices = self.file_list.get_action_target_indices()
        if not indices:
            indices = list(range(len(files)))
        self._load_tracks_busy = True
        self.load_tracks_btn.setEnabled(False)

        self._load_thread = QThread()
        self._load_worker = _LoadTracksWorker(indices, files, self.track_analyzer)
        self._load_worker.moveToThread(self._load_thread)
        self._load_thread.started.connect(self._load_worker.run)
        self._load_worker.finished.connect(self._on_load_tracks_finished)
        self._load_worker.finished.connect(self._load_thread.quit)
        self._load_worker.finished.connect(self._load_worker.deleteLater)
        self._load_thread.finished.connect(self._load_thread.deleteLater)
        self._load_worker.progress.connect(self._on_load_tracks_progress)

        self._load_thread.start()

    def _on_load_tracks_progress(self, done: int, total: int, scope: str) -> None:
        if self.on_status:
            self.on_status(f"Loading tracks ({scope})… {done}/{total}")

    def _on_load_tracks_finished(self, results: list, failed: list, scope: str) -> None:
        no_audio_names: List[str] = []
        for r in results:
            if r["no_audio_name"]:
                no_audio_names.append(r["no_audio_name"])
            self.file_list.update_file(
                r["idx"],
                audio_track=r["audio"],
                subtitle_track=r["subtitle"],
                tracks_from_user=False,
            )
        self._load_tracks_busy = False
        self.load_tracks_btn.setEnabled(True)
        if self.on_status:
            self.on_status(f"Ready - {self.file_list.get_file_count()} file(s) in queue")
        parts = []
        if failed:
            parts.append(f"Analysis failed: {len(failed)} file(s)")
        if no_audio_names:
            parts.append(
                f"No English audio (or disabled Japanese mode): {len(no_audio_names)} file(s)"
            )
        if not parts:
            QMessageBox.information(self, "Load tracks", f"Updated track info for {len(results)} file(s).")
        else:
            QMessageBox.information(
                self,
                "Load tracks",
                f"Processed {len(results)} file(s).\n" + "\n".join(parts),
            )

    def _open_set_tracks_dialog(self) -> None:
        indices = self.file_list.get_action_target_indices()
        if not indices:
            QMessageBox.warning(
                self,
                "No selection",
                "Select one or more files (click rows or use the checkbox column).",
            )
            return
        files = self.file_list.get_files()
        first_idx = indices[0]
        source_file = Path(files[first_idx]["path"])
        if not source_file.exists():
            QMessageBox.critical(self, "File not found", str(source_file))
            return

        # Run analyze_tracks() on a worker thread to avoid blocking the GUI.
        if self._set_tracks_btn:
            self._set_tracks_btn.setEnabled(False)
        if self.on_status:
            self.on_status(f"Analyzing tracks for {source_file.name}…")

        self._analyze_thread = QThread()
        worker = _AnalyzeOneWorker(source_file, self.track_analyzer)
        self._analyze_worker = worker  # Keep a Python reference so the QObject isn't GC'd.
        worker.moveToThread(self._analyze_thread)
        self._analyze_thread.started.connect(worker.run)
        worker.finished.connect(
            lambda tracks, sf: self._on_analyze_done_set_tracks(tracks, sf, indices)
        )
        worker.finished.connect(self._analyze_thread.quit)
        worker.finished.connect(worker.deleteLater)
        self._analyze_thread.finished.connect(self._analyze_thread.deleteLater)
        self._analyze_thread.start()

    def _on_analyze_done_set_tracks(
        self, tracks: dict, source_file: Path, indices: list
    ) -> None:
        self._analyze_worker = None
        if self._set_tracks_btn:
            self._set_tracks_btn.setEnabled(True)
        if self.on_status:
            self.on_status(f"Ready - {self.file_list.get_file_count()} file(s) in queue")

        if tracks.get("error"):
            QMessageBox.critical(self, "Analysis failed", f"Could not read tracks: {tracks['error']}")
            return
        all_tracks = tracks.get("all_tracks") or []
        if not all_tracks:
            QMessageBox.information(
                self,
                "No track list",
                "Track layout could not be listed for this file.",
            )
            return
        audio_tracks = sorted([t for t in all_tracks if t.get("type") == "audio"], key=lambda t: t["id"])
        sub_tracks = sorted(
            [t for t in all_tracks if t.get("type") == "subtitles"], key=lambda t: t["id"]
        )

        def audio_label(t):
            n = t["id"] + 1
            lang = t.get("language") or "?"
            name = (t.get("name") or "").strip()
            extra = f" — {name}" if name else ""
            return f"Audio track {n} ({lang}){extra}", n

        def sub_label(t):
            lang = t.get("language") or "?"
            name = (t.get("name") or "").strip()
            extra = f" — {name}" if name else ""
            return (
                f"Subtitle stream {t['id']} (HB {t['id'] + 1}) ({lang}){extra}",
                t["id"],
            )

        audio_options = [("None (no audio track)", None)] + [audio_label(t) for t in audio_tracks]
        subtitle_options = [("None (no burned subtitles)", None)] + [sub_label(t) for t in sub_tracks]
        picked = show_set_tracks_dialog(self, audio_options, subtitle_options, len(indices))
        if picked is None:
            return
        audio_track, subtitle_track = picked
        if audio_track is None:
            r = QMessageBox.question(
                self,
                "No audio",
                "Audio is set to None. Encoding may fail. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                return
        for idx in indices:
            self.file_list.update_file(
                idx,
                audio_track=audio_track,
                subtitle_track=subtitle_track,
                tracks_from_user=True,
            )
        if self.on_files_changed:
            self.on_files_changed()

    def get_files(self):
        return self.file_list.get_files()

    def get_scan_folder(self) -> Optional[Path]:
        return self.scan_folder

    def get_output_folder(self) -> Optional[Path]:
        return self.output_folder

    def get_output_path(self, source_file: Path) -> Path:
        use_custom = self._radio_custom.isChecked() and self.output_folder
        if not use_custom:
            return source_file.parent
        root = None
        for fd in self.file_list.get_files():
            if fd.get("path") == source_file:
                root = fd.get("root")
                break
        if root is not None:
            try:
                rel = source_file.relative_to(root)
                parts = rel.parent.parts
                strip_n = config.get_strip_leading_path_segments()
                remaining = parts[strip_n:]
                od = self.output_folder / Path(*remaining) if remaining else self.output_folder
                od.mkdir(parents=True, exist_ok=True)
                return od
            except ValueError:
                pass
        if self.scan_folder:
            try:
                rel = source_file.relative_to(self.scan_folder)
                parts = rel.parent.parts
                strip_n = config.get_strip_leading_path_segments()
                remaining = parts[strip_n:]
                od = self.output_folder / Path(*remaining) if remaining else self.output_folder
                od.mkdir(parents=True, exist_ok=True)
                return od
            except ValueError:
                pass
        od = self.output_folder / source_file.parent.name
        od.mkdir(parents=True, exist_ok=True)
        return od
