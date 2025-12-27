"""FFmpeg encoding tab"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable
import threading
import tempfile

from ..widgets.progress_bar import ProgressDisplay
from ..widgets.log_viewer import LogViewer
from core.preset_parser import PresetParser
from core.encoder import Encoder, EncodingProgress, extract_subtitle_stream
from core.track_analyzer import TrackAnalyzer
from core.ffmpeg_translator import FFmpegTranslator
from utils.config import config
from utils.logger import logger


class FFmpegTab(ctk.CTkFrame):
    """Tab for FFmpeg encoding"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.preset_parser: Optional[PresetParser] = None
        self.ffmpeg_translator: Optional[FFmpegTranslator] = None
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
        self.preset_label = ctk.CTkLabel(
            preset_frame,
            text="No preset loaded",
            width=300,
            anchor="w"
        )
        self.preset_label.pack(side="left", padx=5)
        
        ctk.CTkButton(
            preset_frame,
            text="Load Preset",
            command=self._load_preset,
            width=100
        ).pack(side="left", padx=5)
        
        # Command preview
        cmd_frame = ctk.CTkFrame(self)
        cmd_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            cmd_frame,
            text="FFmpeg Command:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        self.cmd_text = ctk.CTkTextbox(cmd_frame, height=100)
        self.cmd_text.pack(fill="x", padx=10, pady=5)
        self.cmd_text.configure(state="disabled")
        
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
    
    def _load_preset(self):
        """Load HandBrake preset file"""
        file = filedialog.askopenfilename(
            title="Select HandBrake preset JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file:
            try:
                self.preset_parser = PresetParser(Path(file))
                self.ffmpeg_translator = FFmpegTranslator(self.preset_parser)
                
                preset_name = self.preset_parser.get_preset_name()
                self.preset_label.configure(text=preset_name)
                
                # Update command preview (with placeholder file)
                self._update_command_preview()
                
                self._on_log("INFO", f"Loaded preset: {preset_name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load preset: {str(e)}")
    
    def _update_command_preview(self):
        """Update FFmpeg command preview"""
        if not self.ffmpeg_translator:
            return
        
        # Use placeholder for preview
        placeholder_input = Path("input.mkv")
        placeholder_output = Path("output.mp4")
        
        cmd = self.ffmpeg_translator.get_command_string(
            input_file=placeholder_input,
            output_file=placeholder_output,
            audio_track=1,
            subtitle_track=None
        )
        
        self.cmd_text.configure(state="normal")
        self.cmd_text.delete("1.0", "end")
        self.cmd_text.insert("1.0", cmd)
        self.cmd_text.configure(state="disabled")
    
    def _start_encoding(self):
        """Start encoding process"""
        if not self.preset_parser or not self.ffmpeg_translator:
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
        ffmpeg_path = config.get_ffmpeg_path() or "ffmpeg"
        
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
            
            # Extract subtitle if needed
            subtitle_file = None
            if tracks.get("subtitle") and not dry_run:
                subtitle_stream_id = tracks["subtitle"] - 1  # Convert to 0-indexed
                subtitle_file = extract_subtitle_stream(
                    ffmpeg_path=ffmpeg_path,
                    input_file=source_file,
                    subtitle_stream_id=subtitle_stream_id
                )
                if subtitle_file:
                    self._on_log("INFO", f"Extracted subtitle to: {subtitle_file}")
            
            # Build FFmpeg command
            ffmpeg_args = self.ffmpeg_translator.build_command(
                input_file=source_file,
                output_file=output_file,
                audio_track=tracks["audio"],
                subtitle_track=tracks.get("subtitle"),
                subtitle_file=subtitle_file
            )
            
            # Encode
            success = self.encoder.encode_with_ffmpeg(
                input_file=source_file,
                output_file=output_file,
                ffmpeg_args=ffmpeg_args,
                subtitle_file=subtitle_file,
                dry_run=dry_run
            )
            
            # Clean up subtitle file
            if subtitle_file and subtitle_file.exists():
                try:
                    subtitle_file.unlink()
                except Exception:
                    pass
            
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
        logger.info(f"[FFmpeg] {message}")

