"""HandBrake encoding tab"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable
import threading

from ..widgets.progress_bar import ProgressDisplay
from ..widgets.log_viewer import LogViewer
from core.preset_parser import PresetParser
from core.encoder import Encoder, EncodingProgress
from core.track_analyzer import TrackAnalyzer
from core.ffmpeg_translator import FFmpegTranslator
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
        
        ctk.CTkLabel(
            log_frame,
            text="Encoding Log",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        self.log_viewer = LogViewer(log_frame, height=200)
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
            messagebox.showwarning("No Preset", "Please load a HandBrake preset first")
            return
        
        if not self.get_files_callback:
            messagebox.showwarning("No Files", "No files available. Please scan for files first.")
            return
        
        files = self.get_files_callback()
        if not files:
            messagebox.showwarning("No Files", "No files to encode")
            return
        
        if self.is_encoding:
            return
        
        self.is_encoding = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        
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
        
        for i, file_data in enumerate(files):
            if not self.is_encoding:
                break
            
            source_file = Path(file_data["path"])
            
            # Analyze tracks
            self._on_log("INFO", f"Analyzing tracks for: {source_file.name}")
            tracks = self.track_analyzer.analyze_tracks(source_file)
            
            if tracks.get("error"):
                self._on_log("ERROR", f"Track analysis failed: {tracks['error']}")
                file_data["status"] = "Error"
                continue
            
            if not tracks.get("audio"):
                self._on_log("WARNING", f"No English audio track found for: {source_file.name}")
                file_data["status"] = "Skipped"
                continue
            
            # Update file data with track info
            file_data["audio_track"] = tracks["audio"]
            file_data["subtitle_track"] = tracks.get("subtitle")
            if self.update_file_callback:
                self.update_file_callback(i, file_data)
            
            # Get output path from files tab
            if self.get_output_path_callback:
                output_dir = self.get_output_path_callback(source_file)
            else:
                output_dir = source_file.parent
            output_file = output_dir / f"{source_file.stem}{suffix}.mp4"
            
            # Check if output exists
            if skip_existing and output_file.exists():
                self._on_log("INFO", f"Skipping (exists): {output_file.name}")
                file_data["status"] = "Skipped"
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
                audio_track=tracks["audio"],
                subtitle_track=tracks.get("subtitle"),
                dry_run=dry_run
            )
            
            if success:
                file_data["status"] = "Complete"
                if output_file.exists():
                    file_data["output_path"] = output_file
                    file_data["output_size"] = output_file.stat().st_size
            else:
                file_data["status"] = "Error"
            
            if self.update_file_callback:
                self.update_file_callback(i, file_data)
        
        # Reset UI
        self.is_encoding = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.progress_display.reset()
    
    def _stop_encoding(self):
        """Stop encoding"""
        if self.encoder:
            self.encoder.stop()
        self.is_encoding = False
    
    def _on_progress(self, progress: EncodingProgress):
        """Handle progress update"""
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
    
    def _on_log(self, level: str, message: str):
        """Handle log message"""
        self.log_viewer.add_log(level, message)
        logger.info(f"[HandBrake] {message}")

