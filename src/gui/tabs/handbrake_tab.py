"""HandBrake encoding tab"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable
import threading
import time

from ..widgets.progress_bar import ProgressDisplay
from ..widgets.log_viewer import LogViewer
from ..widgets.toast import ToastManager
from core.preset_parser import PresetParser
from core.encoder import Encoder, EncodingProgress
from core.track_analyzer import TrackAnalyzer
from core.track_selection import compute_effective_tracks
from core.ffmpeg_translator import FFmpegTranslator
from core.notifications import BatchNotification
from core.batch_stats import BatchStats
from utils.config import config
from utils.logger import logger


class HandBrakeTab(ctk.CTkFrame):
    """Tab for HandBrake encoding"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.preset_parser: Optional[PresetParser] = None
        self.preset_path: Optional[Path] = None
        self.encoder: Optional[Encoder] = None
        self.track_analyzer: Optional[TrackAnalyzer] = None
        self.encoding_thread: Optional[threading.Thread] = None
        self.is_encoding = False
        self.batch_stats: Optional[BatchStats] = None
        self.toast_manager: Optional[object] = None
        self.get_files_callback: Optional[Callable] = None
        self.update_file_callback: Optional[Callable] = None
        self.get_output_path_callback: Optional[Callable] = None
        
        # Top section - Preset selection
        preset_frame = ctk.CTkFrame(self)
        preset_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(preset_frame, text="HandBrake Preset:").pack(side="left", padx=5)
        
        # Preset dropdown
        self.preset_var = ctk.StringVar(value="")
        self.preset_dropdown = ctk.CTkComboBox(
            preset_frame,
            variable=self.preset_var,
            width=300,
            command=self._on_preset_selected
        )
        self.preset_dropdown.pack(side="left", padx=5)
        self._refresh_preset_dropdown()
        
        ctk.CTkButton(
            preset_frame,
            text="Load Preset",
            command=self._load_preset,
            width=100
        ).pack(side="left", padx=5)
        
        # Preset info
        self.preset_info_label = ctk.CTkLabel(
            preset_frame,
            text="",
            font=ctk.CTkFont(size=10)
        )
        self.preset_info_label.pack(side="left", padx=10)
        
        # Encoding controls
        controls_frame = ctk.CTkFrame(self)
        controls_frame.pack(fill="x", padx=10, pady=10)
        
        # Options
        options_frame = ctk.CTkFrame(controls_frame)
        options_frame.pack(side="left", padx=5)
        
        self.dry_run_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            options_frame,
            text="Dry Run",
            variable=self.dry_run_var
        ).pack(side="left", padx=5)
        
        self.skip_existing_var = ctk.BooleanVar(value=config.get_skip_existing())
        ctk.CTkCheckBox(
            options_frame,
            text="Skip Existing",
            variable=self.skip_existing_var
        ).pack(side="left", padx=5)
        
        # Output suffix
        suffix_frame = ctk.CTkFrame(controls_frame)
        suffix_frame.pack(side="left", padx=5)
        
        ctk.CTkLabel(suffix_frame, text="Output Suffix:").pack(side="left", padx=5)
        self.suffix_entry = ctk.CTkEntry(suffix_frame, width=150)
        self.suffix_entry.insert(0, config.get_default_output_suffix())
        self.suffix_entry.pack(side="left", padx=5)
        
        # Encoding mode
        mode_frame = ctk.CTkFrame(controls_frame)
        mode_frame.pack(side="left", padx=5)
        
        ctk.CTkLabel(mode_frame, text="Mode:").pack(side="left", padx=5)
        self.mode_var = ctk.StringVar(value=config.get_encoding_mode())
        ctk.CTkRadioButton(
            mode_frame,
            text="Sequential",
            variable=self.mode_var,
            value="sequential"
        ).pack(side="left", padx=2)
        ctk.CTkRadioButton(
            mode_frame,
            text="Parallel",
            variable=self.mode_var,
            value="parallel"
        ).pack(side="left", padx=2)
        
        # Buttons
        buttons_frame = ctk.CTkFrame(controls_frame)
        buttons_frame.pack(side="right", padx=5)
        
        self.start_button = ctk.CTkButton(
            buttons_frame,
            text="Start Encoding",
            command=self._start_encoding,
            width=120
        )
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = ctk.CTkButton(
            buttons_frame,
            text="Stop",
            command=self._stop_encoding,
            width=100,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)
        
        # Progress display
        self.progress_display = ProgressDisplay(self)
        self.progress_display.pack(fill="x", padx=10, pady=10)
        
        # Log viewer
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_viewer = LogViewer(log_frame, height=200)
        log_header = ctk.CTkFrame(log_frame)
        log_header.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(
            log_header,
            text="Encoding Log",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=(0, 10), pady=0)
        ctk.CTkButton(log_header, text="Copy", width=70, command=self.log_viewer.copy_to_clipboard).pack(side="left")
        self.log_viewer.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Initialize encoder
        self._init_encoder()
        
        # Try to load last used preset
        self._load_last_preset()
    
    def _init_encoder(self):
        """Initialize encoder with paths from config"""
        ffmpeg_path = config.get_ffmpeg_path() or "ffmpeg"
        handbrake_path = config.get_handbrake_path() or "HandBrakeCLI"
        mkvinfo_path = config.get_mkvinfo_path() or "mkvinfo"
        
        self.encoder = Encoder(
            ffmpeg_path=ffmpeg_path,
            handbrake_path=handbrake_path,
            progress_callback=self._on_progress,
            log_callback=self._on_log
        )
        
        self.track_analyzer = TrackAnalyzer(
            mkvinfo_path=mkvinfo_path if mkvinfo_path != "mkvinfo" else None
        )
    
    def _refresh_preset_dropdown(self):
        """Refresh the preset dropdown with saved presets"""
        saved_presets = config.get_saved_presets()
        preset_names = list(saved_presets.keys())
        
        if preset_names:
            self.preset_dropdown.configure(values=[""] + preset_names)
        else:
            self.preset_dropdown.configure(values=[""])
    
    def _load_preset(self):
        """Load HandBrake preset file from file dialog"""
        file = filedialog.askopenfilename(
            title="Select HandBrake preset JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file:
            try:
                self._load_preset_from_path(Path(file), save=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load preset: {str(e)}")
    
    def _load_preset_from_path(self, preset_path: Path, save: bool = False):
        """Load a preset from a file path"""
        self.preset_path = preset_path
        self.preset_parser = PresetParser(self.preset_path)
        preset_name = self.preset_parser.get_preset_name()
        preset_desc = self.preset_parser.get_preset_description()
        
        # Save the preset to config directory if requested
        if save:
            saved_path = config.save_preset(preset_name, preset_path)
            config.set_last_used_preset(preset_name)
            self._refresh_preset_dropdown()
            # Update dropdown to show the selected preset
            self.preset_var.set(preset_name)
        else:
            # Still set as last used
            config.set_last_used_preset(preset_name)
        
        self.preset_info_label.configure(
            text=f"Description: {preset_desc}" if preset_desc else ""
        )
        
        self._on_log("INFO", f"Loaded preset: {preset_name}")
    
    def _on_preset_selected(self, choice: str):
        """Handle preset selection from dropdown"""
        if not choice:
            return
        
        preset_path = config.get_preset_path(choice)
        if preset_path:
            try:
                self._load_preset_from_path(preset_path, save=False)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load preset: {str(e)}")
                self._refresh_preset_dropdown()
                self.preset_var.set("")
    
    def _marshal_ui_update(self, func, *args, **kwargs):
        """Marshal a UI update to the main thread via after()"""
        self.after(0, func, *args, **kwargs)
    
    def _reset_ui_on_encode_end(self):
        """Reset UI after encoding (safe from worker thread via marshaling)"""
        self.is_encoding = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.progress_display.reset()
    
    def _load_last_preset(self):
        """Load the last used preset if available"""
        last_preset = config.get_last_used_preset()
        if last_preset:
            preset_path = config.get_preset_path(last_preset)
            if preset_path:
                try:
                    self._load_preset_from_path(preset_path, save=False)
                    self.preset_var.set(last_preset)
                except Exception:
                    # If preset file doesn't exist or is invalid, just ignore
                    pass
    
    def _start_encoding(self):
        """Start encoding process"""
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
        
        # Ensure previous encoding thread has fully exited before starting new one
        if self.encoding_thread and self.encoding_thread.is_alive():
            self.encoding_thread.join(timeout=2.0)
        
        self.is_encoding = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        
        # Reset encoder stop event so next run isn't blocked
        if self.encoder:
            self.encoder.reset_stop_event()
        
        # Initialize batch statistics
        self.batch_stats = BatchStats()
        
        # Start encoding in thread
        self.encoding_thread = threading.Thread(
            target=self._encode_files,
            args=(files,),
            daemon=True
        )
        self.encoding_thread.start()
    
    def _encode_files(self, files):
        """Encode files (runs in thread)"""
        dry_run = self.dry_run_var.get()
        skip_existing = self.skip_existing_var.get()
        suffix = self.suffix_entry.get()
        mode = self.mode_var.get()
        
        # Get output folder from files tab
        # This will be handled by the main window
        
        # Track batch statistics
        batch_start_time = time.time()
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
                self._on_log(
                    "INFO",
                    f"Using tracks from file list for: {source_file.name}",
                )
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
                    self._on_log(
                        "WARNING",
                        f"No English audio track found for: {source_file.name}",
                    )
                    file_data["status"] = "Skipped"
                    
                    if self.batch_stats:
                        self.batch_stats.add_file_result(
                            filename=source_file.name,
                            elapsed=0,
                            input_size=0,
                            output_size=0,
                            success=False,
                            skipped=True
                        )
                    
                    skipped_count += 1
                    continue

                file_data["audio_track"] = effective_audio
                file_data["subtitle_track"] = subtitle_track
            if self.update_file_callback:
                self.update_file_callback(i, file_data)
            
            # Get output path from files tab
            if self.get_output_path_callback:
                output_dir = self.get_output_path_callback(source_file)
            else:
                output_dir = source_file.parent
            output_file = output_dir / f"{source_file.stem}{suffix}.mp4"
            
            # Check if output exists
            if (
                skip_existing
                and not file_data.get("reencode", False)
                and output_file.exists()
            ):
                self._on_log("INFO", f"Skipping (exists): {output_file.name}")
                file_data["status"] = "Skipped"
                
                if self.batch_stats:
                    self.batch_stats.add_file_result(
                        filename=source_file.name,
                        elapsed=0,
                        input_size=0,
                        output_size=0,
                        success=False,
                        skipped=True
                    )
                
                skipped_count += 1
                continue
            
            # Update status
            file_data["status"] = "Encoding"
            if self.update_file_callback:
                self.update_file_callback(i, file_data)
            
            # Encode
            success = self.encoder.encode_with_handbrake(
                input_file=source_file,
                output_file=output_file,
                preset_file=self.preset_path,
                preset_name=self.preset_parser.get_preset_name(),
                audio_track=effective_audio,
                subtitle_track=subtitle_track,
                dry_run=dry_run
            )
            
            if success:
                file_data["status"] = "Complete"
                file_data["reencode"] = False
                input_size = source_file.stat().st_size if source_file.exists() else 0
                output_size = 0
                if output_file.exists():
                    file_data["output_path"] = output_file
                    output_size = output_file.stat().st_size
                    file_data["output_size"] = output_size
                
                # Record statistics
                if self.batch_stats:
                    self.batch_stats.add_file_result(
                        filename=source_file.name,
                        elapsed=0,  # Encoder doesn't track per-file time, so use 0
                        input_size=input_size,
                        output_size=output_size,
                        success=True
                    )
                
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
                        error_msg="Encoding failed"
                    )
                
                error_count += 1
            
            if self.update_file_callback:
                self.update_file_callback(i, file_data)
        
        # Calculate elapsed time and send completion notification
        if self.batch_stats:
            summary = self.batch_stats.summary_text()
            
            # Show summary as in-app toast
            def show_summary():
                widget = self.master
                max_depth = 10
                depth = 0
                
                while widget and depth < max_depth:
                    if hasattr(widget, "toast_manager"):
                        toast_type = "error" if error_count > 0 else "success"
                        widget.toast_manager.show(summary, message_type=toast_type, duration=5)
                        return
                    widget = getattr(widget, "master", None)
                    depth += 1
            
            self._marshal_ui_update(show_summary)
            
            # Also send via notification system (displays in app-managed toasts)
            BatchNotification.send_completion(
                completed=completed_count,
                skipped=skipped_count,
                errors=error_count,
                total=self.batch_stats.get_total_files(),
                elapsed_time=self.batch_stats.get_elapsed_time_str()
            )
        
        # Reset UI — marshal to main thread to avoid Tk threading issues
        self._marshal_ui_update(self._reset_ui_on_encode_end)
    
    def _stop_encoding(self):
        """Stop encoding (runs in background thread to avoid UI freeze)"""
        # Run stop in a background thread to prevent UI freeze
        def stop_worker():
            if self.encoder:
                self.encoder.stop()
            self.is_encoding = False
        
        # Use daemon thread so it doesn't block the UI
        threading.Thread(target=stop_worker, daemon=True).start()
    
    def _on_progress(self, progress: EncodingProgress):
        """Handle progress update — marshal to main thread"""
        def update_progress():
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
        
        self._marshal_ui_update(update_progress)
    
    def _on_log(self, level: str, message: str):
        """Handle log message — marshal to main thread"""
        if level == "DEBUG" and not config.get_debug_logging():
            return
        
        def update_log():
            self.log_viewer.add_log(level, message)
        
        def log_to_file():
            prefixed_message = f"[HandBrake] {message}"
            if level == "ERROR":
                logger.error(prefixed_message)
            elif level == "WARNING":
                logger.warning(prefixed_message)
            elif level == "SUCCESS":
                logger.success(prefixed_message)
            elif level == "DEBUG":
                logger.debug(prefixed_message)
            else:  # INFO or default
                logger.info(prefixed_message)
        
        # Marshal log viewer update to main thread
        self._marshal_ui_update(update_log)
        # File logging can happen on the worker thread (no Tk involvement)
        log_to_file()
    
    def _show_toast(self, message: str, message_type: str = "info") -> None:
        """Show in-app toast notification"""
        # Traverse up the widget hierarchy to find MainWindow
        widget = self.master
        max_depth = 10
        depth = 0
        
        while widget and depth < max_depth:
            if hasattr(widget, "toast_manager"):
                widget.toast_manager.show(message, message_type=message_type, duration=3)
                return
            widget = getattr(widget, "master", None)
            depth += 1

