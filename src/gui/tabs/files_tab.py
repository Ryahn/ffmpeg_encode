"""Files tab for managing video files"""

import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar
from pathlib import Path
from typing import Optional, Callable, List

from ..widgets.file_list import FileListWidget
from ..dialogs.set_tracks_dialog import show_set_tracks_dialog
from core.file_scanner import FileScanner
from core.track_analyzer import TrackAnalyzer
from core.track_selection import compute_effective_tracks
from utils.config import config


class FilesTab(ctk.CTkFrame):
    """Tab for managing files to encode"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.scanner = FileScanner()
        self.scan_folder: Optional[Path] = None
        self.output_folder: Optional[Path] = None
        self.on_files_changed: Optional[Callable] = None
        self.on_status: Optional[Callable[[str], None]] = None

        mkvinfo_path = config.get_mkvinfo_path() or "mkvinfo"
        self.track_analyzer = TrackAnalyzer(
            mkvinfo_path=mkvinfo_path if mkvinfo_path != "mkvinfo" else None
        )
        self._load_tracks_busy = False

        # Top controls: two rows so output section has full width and buttons stay visible
        controls_frame = ctk.CTkFrame(self)
        controls_frame.pack(fill="x", padx=10, pady=10)

        # Row 1: Scan folder
        scan_frame = ctk.CTkFrame(controls_frame)
        scan_frame.pack(fill="x", padx=0, pady=(0, 5))
        
        ctk.CTkLabel(scan_frame, text="Scan Folder:").pack(side="left", padx=5)
        self.scan_folder_label = ctk.CTkLabel(
            scan_frame,
            text="Not selected",
            width=300,
            anchor="w"
        )
        self.scan_folder_label.pack(side="left", padx=5)
        
        ctk.CTkButton(
            scan_frame,
            text="Browse",
            command=self._browse_scan_folder,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            scan_frame,
            text="Scan",
            command=self._scan_folder,
            width=100
        ).pack(side="left", padx=5)
        
        # Row 2: Save to + output path (path shrinks so buttons stay in view)
        output_section = ctk.CTkFrame(controls_frame)
        output_section.pack(fill="x", padx=0, pady=0)
        
        self.output_destination_var = StringVar(value=config.get_output_destination())
        self.output_destination_var.trace_add("write", self._on_output_destination_changed)
        
        ctk.CTkLabel(output_section, text="Save to:").pack(side="left", padx=5)
        ctk.CTkRadioButton(
            output_section,
            variable=self.output_destination_var,
            value="input_folder",
            text="Same folder as input file",
            command=self._on_output_destination_choice
        ).pack(side="left", padx=5)
        ctk.CTkRadioButton(
            output_section,
            variable=self.output_destination_var,
            value="custom_folder",
            text="Output folder",
            command=self._on_output_destination_choice
        ).pack(side="left", padx=5)
        
        self.output_path_frame = ctk.CTkFrame(output_section)
        self.output_path_frame.pack(side="left", fill="x", expand=True, padx=5)
        self.output_folder_label = ctk.CTkLabel(
            self.output_path_frame,
            text="Not selected",
            anchor="w"
        )
        self.output_folder_label.pack(side="left", fill="x", expand=True, padx=(5, 2))
        self.browse_output_btn = ctk.CTkButton(
            self.output_path_frame,
            text="Select output folder",
            command=self._browse_output_folder,
            width=140
        )
        self.browse_output_btn.pack(side="right", padx=2)
        self.clear_output_btn = ctk.CTkButton(
            self.output_path_frame,
            text="Clear",
            command=self._clear_output_folder,
            width=60
        )
        self.clear_output_btn.pack(side="right", padx=2)
        
        # Row 3: Strip leading path segments (only when Output folder is selected)
        self.strip_frame = ctk.CTkFrame(controls_frame)
        self.strip_frame.pack(fill="x", padx=0, pady=(5, 0))
        ctk.CTkLabel(self.strip_frame, text="Strip leading path segments:").pack(side="left", padx=5, pady=5)
        self.strip_entry = ctk.CTkEntry(self.strip_frame, width=50)
        self.strip_entry.insert(0, str(config.get_strip_leading_path_segments()))
        self.strip_entry.pack(side="left", padx=(0, 10), pady=5)
        self.strip_entry.bind("<KeyRelease>", self._on_strip_changed)
        self.strip_entry.bind("<FocusOut>", self._on_strip_focus_out)
        self.preview_label = ctk.CTkLabel(
            self.strip_frame,
            text="Result: (select Output folder to see preview)",
            anchor="w"
        )
        self.preview_label.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        # File list
        self.file_list = FileListWidget(self)
        self.file_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Bottom controls
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            bottom_frame,
            text="Add Files",
            command=self._add_files,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            bottom_frame,
            text="Remove Selected",
            command=self._remove_selected,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            bottom_frame,
            text="Clear All",
            command=self._clear_all,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            bottom_frame,
            text="Select All",
            command=self._select_all,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            bottom_frame,
            text="Deselect All",
            command=self._deselect_all,
            width=100
        ).pack(side="left", padx=5)

        batch_frame = ctk.CTkFrame(self)
        batch_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(
            batch_frame,
            text="Set tracks…",
            command=self._open_set_tracks_dialog,
            width=110,
        ).pack(side="left", padx=5)
        self.load_tracks_btn = ctk.CTkButton(
            batch_frame,
            text="Load tracks",
            command=self._load_tracks,
            width=110,
        )
        self.load_tracks_btn.pack(side="left", padx=5)
        ctk.CTkButton(
            batch_frame,
            text="Mark for re-encode",
            command=self._mark_for_reencode,
            width=140,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            batch_frame,
            text="Clear re-encode",
            command=self._clear_reencode_marks,
            width=120,
        ).pack(side="left", padx=5)

        # Load saved scan folder
        last_scan = config.get_last_scan_folder()
        if last_scan and Path(last_scan).exists():
            self.scan_folder = Path(last_scan)
            self.scan_folder_label.configure(text=str(self.scan_folder))
        
        # Load saved output destination and folder
        dest = config.get_output_destination()
        self.output_destination_var.set(dest)
        if dest == "custom_folder":
            output_folder = config.get_default_output_folder()
            if output_folder and Path(output_folder).exists():
                self.output_folder = Path(output_folder)
                self.output_folder_label.configure(text=str(self.output_folder))
            else:
                self.output_folder = None
                self.output_folder_label.configure(text="Not selected")
        else:
            self.output_folder = None
            self.output_folder_label.configure(text="Not selected")
        self._update_output_path_visibility()
        self._update_preview()
    
    def _on_strip_changed(self, event=None):
        self._apply_strip_value()
    
    def _on_strip_focus_out(self, event=None):
        self._apply_strip_value()
    
    def _apply_strip_value(self):
        try:
            raw = self.strip_entry.get().strip()
            n = int(raw) if raw else 0
            n = max(0, min(99, n))
            config.set_strip_leading_path_segments(n)
            if raw != str(n):
                self.strip_entry.delete(0, "end")
                self.strip_entry.insert(0, str(n))
        except ValueError:
            pass
        self._update_preview()
    
    def _compute_preview_path(self) -> Optional[str]:
        if self.output_destination_var.get() != "custom_folder" or not self.output_folder:
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
                        relative_path = source_file.relative_to(root)
                        relative_dir = relative_path.parent
                        parts = relative_dir.parts
                        remaining = parts[strip_n:]
                        if remaining:
                            output_dir = self.output_folder / Path(*remaining)
                        else:
                            output_dir = self.output_folder
                        result_path = output_dir / f"{source_file.stem}{suffix}.mp4"
                        previews.append(str(result_path))
                    except ValueError:
                        output_dir = self.output_folder / source_file.parent.name
                        previews.append(str(output_dir / f"{source_file.stem}{suffix}.mp4"))
                else:
                    if self.scan_folder:
                        try:
                            relative_path = source_file.relative_to(self.scan_folder)
                            relative_dir = relative_path.parent
                            parts = relative_dir.parts
                            remaining = parts[strip_n:]
                            if remaining:
                                output_dir = self.output_folder / Path(*remaining)
                            else:
                                output_dir = self.output_folder
                            previews.append(str(output_dir / f"{source_file.stem}{suffix}.mp4"))
                        except ValueError:
                            previews.append(str(self.output_folder / f"{source_file.stem}{suffix}.mp4"))
                    else:
                        output_dir = self.output_folder / source_file.parent.name
                        previews.append(str(output_dir / f"{source_file.stem}{suffix}.mp4"))
            if not previews:
                return str(self.output_folder / f"file{suffix}.mp4") + " (example)"
            if len(roots_seen) > 1 or len(previews) > 1:
                return " | ".join(previews) if len(previews) <= 2 else previews[0] + " ..."
            return previews[0]
        parts = ["Subfolder", "Another"]
        remaining = parts[strip_n:] if strip_n < len(parts) else []
        if remaining:
            example = self.output_folder / Path(*remaining) / f"file{suffix}.mp4"
        else:
            example = self.output_folder / f"file{suffix}.mp4"
        return str(example) + " (example)"
    
    def _update_preview(self):
        path_str = self._compute_preview_path()
        if path_str is not None:
            self.preview_label.configure(text=f"Result: {path_str}")
        else:
            self.preview_label.configure(text="Result: (select Output folder to see preview)")
    
    def _browse_scan_folder(self):
        """Browse for scan folder"""
        folder = filedialog.askdirectory(title="Select folder to scan for video files")
        if folder:
            self.scan_folder = Path(folder)
            self.scan_folder_label.configure(text=str(self.scan_folder))
            config.set_last_scan_folder(str(self.scan_folder))
            self._update_preview()
    
    def _on_output_destination_changed(self, *args):
        """Update visibility and persist when destination radio changes"""
        val = self.output_destination_var.get()
        self._update_output_path_visibility()
        if val in ("input_folder", "custom_folder"):
            config.set_output_destination(val)

    def _on_output_destination_choice(self):
        """Called when user selects a destination radio button"""
        if self.output_destination_var.get() == "custom_folder":
            config.set_output_destination("custom_folder")

    def _update_output_path_visibility(self):
        """Enable or disable Clear button and strip control based on destination"""
        is_custom = self.output_destination_var.get() == "custom_folder"
        self.clear_output_btn.configure(state="normal" if is_custom else "disabled")
        self.strip_entry.configure(state="normal" if is_custom else "disabled")
        self._update_preview()

    def _browse_output_folder(self):
        """Browse for output folder; switches to Output folder mode if needed"""
        if self.output_destination_var.get() != "custom_folder":
            self.output_destination_var.set("custom_folder")
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_folder = Path(folder)
            self.output_folder_label.configure(text=str(self.output_folder))
            config.set_output_destination("custom_folder")
            config.set_default_output_folder(str(self.output_folder))
            self._update_preview()

    def _clear_output_folder(self):
        """Clear the chosen output folder; encodes fall back to input location until Browse again"""
        self.output_folder = None
        self.output_folder_label.configure(text="Not selected")
        config.set_default_output_folder("")
        self._update_preview()
    
    def _scan_folder(self):
        """Scan folder for video files"""
        if not self.scan_folder:
            messagebox.showwarning("No Folder", "Please select a scan folder first")
            return
        
        # Clear existing files
        self.file_list.clear()
        
        # Scan for files
        files = self.scanner.scan_directory(self.scan_folder, recursive=True)
        
        # Add files to list
        for file_path in files:
            self.file_list.add_file(file_path, relative_to=self.scan_folder, root=self.scan_folder)
        
        if self.on_files_changed:
            self.on_files_changed()
        self._update_preview()
        messagebox.showinfo(
            "Scan Complete",
            f"Found {len(files)} video file(s)"
        )
    
    def _add_files(self):
        """Add individual files"""
        files = filedialog.askopenfilenames(
            title="Select video files",
            filetypes=[
                ("Video files", "*.mkv *.mp4 *.mov *.avi *.m4v *.flv *.wmv *.webm"),
                ("All files", "*.*")
            ]
        )
        
        for file_path in files:
            path = Path(file_path)
            root = path.parent.parent if path.parent != path else path.parent
            self.file_list.add_file(path, root=root)
        
        if self.on_files_changed:
            self.on_files_changed()
        self._update_preview()
    
    def _remove_selected(self):
        """Remove selected files"""
        selected_count = self.file_list.remove_selected_files()
        if selected_count > 0:
            if self.on_files_changed:
                self.on_files_changed()
            self._update_preview()
            messagebox.showinfo("Files Removed", f"Removed {selected_count} file(s) from the list.")
        else:
            messagebox.showwarning("No Selection", "Please select one or more files to remove.")
    
    def _clear_all(self):
        """Clear all files"""
        self.file_list.clear()
        if self.on_files_changed:
            self.on_files_changed()
        self._update_preview()
    
    def _select_all(self):
        """Select all files in the list"""
        self.file_list.select_all()
    
    def _deselect_all(self):
        """Deselect all files in the list"""
        self.file_list.deselect_all()

    def _mark_for_reencode(self):
        indices = self.file_list.get_action_target_indices()
        if not indices:
            messagebox.showwarning(
                "No selection",
                "Select one or more files (click rows or use the checkbox column).",
            )
            return
        count = self.file_list.set_reencode_for_indices(indices, True)
        messagebox.showinfo(
            "Re-encode",
            f"Marked {count} file(s). They will be encoded even if the output file already exists.",
        )

    def _clear_reencode_marks(self):
        indices = self.file_list.get_action_target_indices()
        if not indices:
            indices = list(range(self.file_list.get_file_count()))
        if not indices:
            return
        count = self.file_list.set_reencode_for_indices(indices, False)
        messagebox.showinfo("Re-encode", f"Cleared re-encode mark on {count} file(s).")

    def _load_tracks(self):
        if self._load_tracks_busy:
            return
        files = self.file_list.get_files()
        if not files:
            messagebox.showwarning("No Files", "Add files to the list first.")
            return
        if not self.track_analyzer.mkvinfo_path and not self.track_analyzer.ffprobe_path:
            messagebox.showerror(
                "Track analysis unavailable",
                "Install MKVToolNix (mkvinfo) for MKV files, or FFmpeg (ffprobe) for other formats.",
            )
            return

        indices = self.file_list.get_action_target_indices()
        scope = "selected"
        if not indices:
            indices = list(range(len(files)))
            scope = "all"

        self._load_tracks_busy = True
        self.load_tracks_btn.configure(state="disabled")
        if self.on_status:
            self.on_status(f"Loading tracks ({scope})… 0/{len(indices)}")

        def worker():
            failed: List[str] = []
            results: List[dict] = []
            for pos, idx in enumerate(indices):
                source_file = Path(files[idx]["path"])
                tracks = self.track_analyzer.analyze_tracks(source_file)
                done = pos + 1
                total = len(indices)

                def update_status(p=done, t=total):
                    if self.on_status:
                        self.on_status(f"Loading tracks ({scope})… {p}/{t}")

                self.after(0, update_status)

                if tracks.get("error"):
                    failed.append(source_file.name)
                    continue

                effective_audio, subtitle_track = compute_effective_tracks(
                    tracks, self.track_analyzer
                )

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

            def apply_all():
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
                self.load_tracks_btn.configure(state="normal")
                if self.on_status:
                    self._update_status_after_load()
                parts = []
                if failed:
                    parts.append(f"Analysis failed: {len(failed)} file(s)")
                if no_audio_names:
                    parts.append(
                        f"No English audio (or disabled Japanese mode): {len(no_audio_names)} file(s)"
                    )
                if not parts:
                    messagebox.showinfo(
                        "Load tracks",
                        f"Updated track info for {len(indices)} file(s).",
                    )
                else:
                    messagebox.showinfo(
                        "Load tracks",
                        f"Processed {len(indices)} file(s).\n" + "\n".join(parts),
                    )

            self.after(0, apply_all)

        threading.Thread(target=worker, daemon=True).start()

    def _update_status_after_load(self):
        if self.on_status:
            count = self.file_list.get_file_count()
            self.on_status(f"Ready - {count} file(s) in queue")

    def _open_set_tracks_dialog(self):
        indices = self.file_list.get_action_target_indices()
        if not indices:
            messagebox.showwarning(
                "No selection",
                "Select one or more files (click rows or use the checkbox column).",
            )
            return
        files = self.file_list.get_files()
        first_idx = indices[0]
        source_file = Path(files[first_idx]["path"])
        if not source_file.exists():
            messagebox.showerror("File not found", str(source_file))
            return

        tracks = self.track_analyzer.analyze_tracks(source_file)
        if tracks.get("error"):
            messagebox.showerror(
                "Analysis failed",
                f"Could not read tracks: {tracks['error']}",
            )
            return
        all_tracks = tracks.get("all_tracks") or []
        if not all_tracks:
            messagebox.showinfo(
                "No track list",
                "Track layout could not be listed for this file. "
                "Use MKV files with mkvinfo, or load tracks after analysis support is added for this format.",
            )
            return

        audio_tracks = sorted(
            [t for t in all_tracks if t.get("type") == "audio"],
            key=lambda t: t["id"],
        )
        sub_tracks = sorted(
            [t for t in all_tracks if t.get("type") == "subtitles"],
            key=lambda t: t["id"],
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
            return f"Subtitle stream {t['id']} (HB {t['id'] + 1}) ({lang}){extra}", t["id"]

        audio_options = [("None (no audio track)", None)] + [audio_label(t) for t in audio_tracks]
        subtitle_options = [("None (no burned subtitles)", None)] + [
            sub_label(t) for t in sub_tracks
        ]

        picked = show_set_tracks_dialog(
            self,
            audio_options,
            subtitle_options,
            len(indices),
        )
        if picked is None:
            return
        audio_track, subtitle_track = picked
        if audio_track is None:
            if not messagebox.askyesno(
                "No audio",
                "Audio is set to None. Encoding may fail. Continue?",
            ):
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
        """Get list of files"""
        return self.file_list.get_files()
    
    def get_scan_folder(self) -> Optional[Path]:
        """Get scan folder"""
        return self.scan_folder
    
    def get_output_folder(self) -> Optional[Path]:
        """Get output folder"""
        return self.output_folder
    
    def get_output_path(self, source_file: Path) -> Path:
        """Get output path for a source file, preserving folder structure per file root."""
        use_custom = (
            self.output_destination_var.get() == "custom_folder" and self.output_folder
        )
        if not use_custom:
            return source_file.parent

        root = None
        for fd in self.file_list.get_files():
            if fd.get("path") == source_file:
                root = fd.get("root")
                break

        if root is not None:
            try:
                relative_path = source_file.relative_to(root)
                relative_dir = relative_path.parent
                parts = relative_dir.parts
                strip_n = config.get_strip_leading_path_segments()
                remaining = parts[strip_n:]
                if remaining:
                    output_dir = self.output_folder / Path(*remaining)
                else:
                    output_dir = self.output_folder
                output_dir.mkdir(parents=True, exist_ok=True)
                return output_dir
            except ValueError:
                pass

        if self.scan_folder:
            try:
                relative_path = source_file.relative_to(self.scan_folder)
                relative_dir = relative_path.parent
                parts = relative_dir.parts
                strip_n = config.get_strip_leading_path_segments()
                remaining = parts[strip_n:]
                if remaining:
                    output_dir = self.output_folder / Path(*remaining)
                else:
                    output_dir = self.output_folder
                output_dir.mkdir(parents=True, exist_ok=True)
                return output_dir
            except ValueError:
                pass

        output_dir = self.output_folder / source_file.parent.name
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

