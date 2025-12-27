"""FFmpeg encoding tab"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable, List
import threading
import tempfile
import shlex
import re

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
        
        # Command editor
        cmd_frame = ctk.CTkFrame(self)
        cmd_frame.pack(fill="x", padx=10, pady=10)
        
        cmd_header = ctk.CTkFrame(cmd_frame)
        cmd_header.pack(fill="x", padx=10, pady=5)
        
        header_left = ctk.CTkFrame(cmd_header)
        header_left.pack(side="left", padx=5)
        
        ctk.CTkLabel(
            header_left,
            text="FFmpeg Command:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=5)
        
        # Note about placeholders
        note_label = ctk.CTkLabel(
            header_left,
            text="(Note: 'input.mkv' and 'output.mp4' are example placeholders - actual file paths will be used during encoding)",
            font=ctk.CTkFont(size=9),
            text_color="gray"
        )
        note_label.pack(side="left", padx=10)
        
        # Command management buttons
        cmd_buttons = ctk.CTkFrame(cmd_header)
        cmd_buttons.pack(side="right", padx=5)
        
        ctk.CTkButton(
            cmd_buttons,
            text="Save",
            command=self._save_command,
            width=80
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            cmd_buttons,
            text="Load",
            command=self._load_saved_command,
            width=80
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            cmd_buttons,
            text="Load from File",
            command=self._load_command_from_file,
            width=100
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            cmd_buttons,
            text="Save to File",
            command=self._save_command_to_file,
            width=100
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            cmd_buttons,
            text="Reset",
            command=self._reset_command,
            width=80
        ).pack(side="left", padx=2)
        
        # Saved commands dropdown
        saved_frame = ctk.CTkFrame(cmd_frame)
        saved_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(saved_frame, text="Saved Commands:").pack(side="left", padx=5)
        self.saved_cmd_var = ctk.StringVar(value="")
        self.saved_cmd_dropdown = ctk.CTkComboBox(
            saved_frame,
            variable=self.saved_cmd_var,
            values=[""],
            command=self._on_saved_command_selected,
            width=300
        )
        self.saved_cmd_dropdown.pack(side="left", padx=5)
        
        ctk.CTkButton(
            saved_frame,
            text="Delete",
            command=self._delete_saved_command,
            width=80
        ).pack(side="left", padx=5)
        
        # Info note about placeholders
        info_frame = ctk.CTkFrame(cmd_frame)
        info_frame.pack(fill="x", padx=10, pady=(5, 0))
        
        info_label = ctk.CTkLabel(
            info_frame,
            text="ℹ️ Note: 'input.mkv' and 'output.mp4' shown below are EXAMPLE PLACEHOLDERS only. " +
                 "During encoding, these will be automatically replaced with the actual input and output file paths.",
            font=ctk.CTkFont(size=10),
            text_color="yellow",
            anchor="w",
            justify="left",
            wraplength=1000
        )
        info_label.pack(fill="x", padx=5, pady=5)
        
        # Command textbox (now editable)
        self.cmd_text = ctk.CTkTextbox(cmd_frame, height=100, font=ctk.CTkFont(family="Courier", size=10))
        self.cmd_text.pack(fill="x", padx=10, pady=5)
        # Keep it enabled for editing
        
        # Placeholder help
        placeholder_frame = ctk.CTkFrame(cmd_frame)
        placeholder_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            placeholder_frame,
            text="Placeholders:",
            font=ctk.CTkFont(size=10)
        ).pack(side="left", padx=5)
        
        placeholders = [
            ("{INPUT}", "Input file"),
            ("{OUTPUT}", "Output file"),
            ("{AUDIO_TRACK}", "Audio track number"),
            ("{SUBTITLE_TRACK}", "Subtitle track number"),
            ("{SUBTITLE_FILE}", "Subtitle file path")
        ]
        
        for placeholder, desc in placeholders:
            btn = ctk.CTkButton(
                placeholder_frame,
                text=placeholder,
                command=lambda p=placeholder: self._insert_placeholder(p),
                width=120,
                height=20,
                font=ctk.CTkFont(size=9)
            )
            btn.pack(side="left", padx=2)
        
        help_label = ctk.CTkLabel(
            placeholder_frame,
            text="(Click to insert)",
            font=ctk.CTkFont(size=9),
            text_color="gray"
        )
        help_label.pack(side="left", padx=5)
        
        # Update saved commands dropdown
        self._update_saved_commands_dropdown()
        
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
        self.preset_parser = PresetParser(preset_path)
        self.ffmpeg_translator = FFmpegTranslator(self.preset_parser)
        
        preset_name = self.preset_parser.get_preset_name()
        
        # Save the preset to config directory if requested
        if save:
            config.save_preset(preset_name, preset_path)
            config.set_last_used_preset(preset_name)
            self._refresh_preset_dropdown()
            # Update dropdown to show the selected preset
            self.preset_var.set(preset_name)
        else:
            # Still set as last used
            config.set_last_used_preset(preset_name)
        
        # Update command preview (with placeholder file)
        self._update_command_preview()
        
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
        
        self.cmd_text.delete("1.0", "end")
        self.cmd_text.insert("1.0", cmd)
    
    def _save_command(self):
        """Save the current command"""
        command = self.cmd_text.get("1.0", "end-1c").strip()
        if not command:
            messagebox.showwarning("No Command", "No command to save")
            return
        
        # Ask for a name
        from tkinter import simpledialog
        name = simpledialog.askstring("Save Command", "Enter a name for this command:")
        if name:
            config.save_ffmpeg_command(name, command)
            self._update_saved_commands_dropdown()
            messagebox.showinfo("Saved", f"Command saved as '{name}'")
    
    def _load_saved_command(self):
        """Load a saved command"""
        saved_cmd = self.saved_cmd_var.get()
        if not saved_cmd:
            messagebox.showwarning("No Selection", "Please select a saved command from the dropdown")
            return
        
        command = config.get_ffmpeg_command(saved_cmd)
        if command:
            self.cmd_text.delete("1.0", "end")
            self.cmd_text.insert("1.0", command)
        else:
            messagebox.showerror("Error", f"Command '{saved_cmd}' not found")
    
    def _load_command_from_file(self):
        """Load command from a text file"""
        file = filedialog.askopenfilename(
            title="Load FFmpeg Command",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    command = f.read().strip()
                self.cmd_text.delete("1.0", "end")
                self.cmd_text.insert("1.0", command)
                messagebox.showinfo("Loaded", "Command loaded from file")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")
    
    def _save_command_to_file(self):
        """Save command to a text file"""
        command = self.cmd_text.get("1.0", "end-1c").strip()
        if not command:
            messagebox.showwarning("No Command", "No command to save")
            return
        
        file = filedialog.asksaveasfilename(
            title="Save FFmpeg Command",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file:
            try:
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(command)
                messagebox.showinfo("Saved", f"Command saved to {file}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
    
    def _reset_command(self):
        """Reset command to generated from preset"""
        if self.ffmpeg_translator:
            self._update_command_preview()
        else:
            messagebox.showwarning("No Preset", "Load a HandBrake preset first to generate a command")
    
    def _delete_saved_command(self):
        """Delete a saved command"""
        saved_cmd = self.saved_cmd_var.get()
        if not saved_cmd:
            messagebox.showwarning("No Selection", "Please select a saved command to delete")
            return
        
        if messagebox.askyesno("Confirm Delete", f"Delete saved command '{saved_cmd}'?"):
            config.delete_ffmpeg_command(saved_cmd)
            self._update_saved_commands_dropdown()
            messagebox.showinfo("Deleted", f"Command '{saved_cmd}' deleted")
    
    def _update_saved_commands_dropdown(self):
        """Update the saved commands dropdown"""
        commands = config.get_saved_ffmpeg_commands()
        if commands:
            self.saved_cmd_dropdown.configure(values=list(commands.keys()))
        else:
            self.saved_cmd_dropdown.configure(values=[""])
            self.saved_cmd_var.set("")
    
    def _on_saved_command_selected(self, choice):
        """Handle saved command selection"""
        if choice:
            command = config.get_ffmpeg_command(choice)
            if command:
                self.cmd_text.delete("1.0", "end")
                self.cmd_text.insert("1.0", command)
    
    def _insert_placeholder(self, placeholder: str):
        """Insert a placeholder at the cursor position"""
        try:
            # Get cursor position
            cursor_pos = self.cmd_text.index("insert")
            # Insert the placeholder
            self.cmd_text.insert(cursor_pos, placeholder)
        except Exception:
            # If cursor position fails, just append
            self.cmd_text.insert("end", placeholder)
    
    def _start_encoding(self):
        """Start encoding process"""
        # Check if there's a command (either from preset or edited)
        command = self.cmd_text.get("1.0", "end-1c").strip()
        if not command:
            messagebox.showwarning("No Command", "Please load a preset or enter an FFmpeg command")
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
        
        # Reset encoder stop event
        if self.encoder:
            self.encoder.reset_stop_event()
        
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
            
            # Get command from textbox (user may have edited it)
            command_template = self.cmd_text.get("1.0", "end-1c").strip()
            if not command_template:
                self._on_log("ERROR", "No FFmpeg command found in textbox")
                file_data["status"] = "Error"
                if self.update_file_callback:
                    self.update_file_callback(i, file_data)
                continue
            
            self._on_log("INFO", f"Parsing FFmpeg command...")
            
            # Replace placeholders in the command with actual file paths
            try:
                ffmpeg_args = self._parse_and_substitute_command(
                    command_template,
                    source_file,
                    output_file,
                    tracks["audio"],
                    tracks.get("subtitle"),
                    subtitle_file
                )
                if not ffmpeg_args:
                    self._on_log("ERROR", "Command parsing resulted in empty arguments")
                    file_data["status"] = "Error"
                    if self.update_file_callback:
                        self.update_file_callback(i, file_data)
                    continue
                self._on_log("INFO", f"Command parsed successfully ({len(ffmpeg_args)} arguments)")
            except Exception as e:
                self._on_log("ERROR", f"Failed to parse command: {str(e)}")
                import traceback
                self._on_log("ERROR", f"Traceback: {traceback.format_exc()}")
                file_data["status"] = "Error"
                if self.update_file_callback:
                    self.update_file_callback(i, file_data)
                continue
            
            # Encode
            self._on_log("INFO", f"Starting encoding to: {output_file.name}")
            try:
                success = self.encoder.encode_with_ffmpeg(
                    input_file=source_file,
                    output_file=output_file,
                    ffmpeg_args=ffmpeg_args,
                    subtitle_file=subtitle_file,
                    dry_run=dry_run
                )
            except Exception as e:
                self._on_log("ERROR", f"Encoding failed with exception: {str(e)}")
                import traceback
                self._on_log("ERROR", f"Traceback: {traceback.format_exc()}")
                success = False
            
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
    
    def _parse_and_substitute_command(
        self,
        command_template: str,
        input_file: Path,
        output_file: Path,
        audio_track: int,
        subtitle_track: Optional[int],
        subtitle_file: Optional[Path]
    ) -> List[str]:
        """Parse command string and substitute placeholders with actual values"""
        # Replace common placeholders
        command = command_template
        
        # Helper function to escape backslashes for regex replacement
        # Windows paths like C:\Users need backslashes escaped to avoid \U being interpreted as Unicode escape
        def escape_for_replacement(path_str: str) -> str:
            return path_str.replace('\\', '\\\\')
        
        # Helper function to quote paths with spaces for command string
        def quote_path_if_needed(path_str: str) -> str:
            """Quote path if it contains spaces, for proper shlex.split() handling"""
            if ' ' in path_str:
                return f'"{path_str}"'
            return path_str
        
        input_file_str = str(input_file)
        output_file_str = str(output_file)
        
        # Quote paths with spaces
        input_file_quoted = quote_path_if_needed(input_file_str)
        output_file_quoted = quote_path_if_needed(output_file_str)
        
        # Escape backslashes for regex replacement
        input_file_escaped = escape_for_replacement(input_file_quoted)
        output_file_escaped = escape_for_replacement(output_file_quoted)
        
        # Replace input file placeholders
        command = re.sub(r'\binput\.mkv\b', input_file_escaped, command, flags=re.IGNORECASE)
        command = re.sub(r'\{INPUT\}', input_file_escaped, command)
        command = re.sub(r'<INPUT>', input_file_escaped, command)
        
        # Replace output file placeholders
        command = re.sub(r'\boutput\.mp4\b', output_file_escaped, command, flags=re.IGNORECASE)
        command = re.sub(r'\{OUTPUT\}', output_file_escaped, command)
        command = re.sub(r'<OUTPUT>', output_file_escaped, command)
        
        # Replace audio track placeholder
        command = re.sub(r'\{AUDIO_TRACK\}', str(audio_track), command)
        command = re.sub(r'<AUDIO_TRACK>', str(audio_track), command)
        
        # Replace subtitle track placeholder
        if subtitle_track:
            command = re.sub(r'\{SUBTITLE_TRACK\}', str(subtitle_track), command)
            command = re.sub(r'<SUBTITLE_TRACK>', str(subtitle_track), command)
        
        # Replace subtitle file placeholder
        if subtitle_file:
            # Escape the path for use in filter (convert to forward slashes for FFmpeg filters)
            # After converting \ to /, there are no backslashes left except \: which we need to escape for regex
            sub_path = str(subtitle_file).replace("\\", "/").replace(":", "\\:")
            sub_path = sub_path.replace("'", "'\\''")
            # Escape the backslash in \: for regex replacement (becomes \\: which regex will interpret as \:)
            sub_path_escaped = sub_path.replace('\\', '\\\\')
            command = re.sub(r'\{SUBTITLE_FILE\}', sub_path_escaped, command)
            command = re.sub(r'<SUBTITLE_FILE>', sub_path_escaped, command)
        
        # If command still contains "input.mkv" or "output.mp4" as literal paths, replace them
        # This handles the case where the preset generated command has placeholders in quotes
        if "input.mkv" in command.lower() or "output.mp4" in command.lower():
            # Try to find and replace the actual file paths in quotes
            # Use the already-quoted versions we created earlier
            command = re.sub(r'"input\.mkv"', input_file_escaped, command, flags=re.IGNORECASE)
            command = re.sub(r'"output\.mp4"', output_file_escaped, command, flags=re.IGNORECASE)
            # For single quotes, we still need to quote the paths
            input_single_quoted = escape_for_replacement(f"'{input_file_str}'")
            output_single_quoted = escape_for_replacement(f"'{output_file_str}'")
            command = re.sub(r"'input\.mkv'", input_single_quoted, command, flags=re.IGNORECASE)
            command = re.sub(r"'output\.mp4'", output_single_quoted, command, flags=re.IGNORECASE)
        
        # Parse the command string into a list of arguments
        # Use shlex to properly handle quoted arguments
        # Note: When passing a list to subprocess.Popen(), quotes are NOT needed - each element is a separate argument
        try:
            args = shlex.split(command, posix=False)  # posix=False for Windows compatibility
            # Explicitly strip quotes from all arguments (shlex should do this, but ensure it's done)
            # This is critical because subprocess.Popen() expects unquoted arguments when using a list
            args = [arg.strip('"').strip("'") for arg in args]
        except Exception:
            # Fallback: simple split if shlex fails (but this won't handle spaces correctly)
            args = command.split()
            # Still strip quotes in fallback
            args = [arg.strip('"').strip("'") for arg in args]
        
        # Replace "ffmpeg" with actual path if present (this should already be done, but just in case)
        ffmpeg_path = config.get_ffmpeg_path() or "ffmpeg"
        for i, arg in enumerate(args):
            if arg.lower() == "ffmpeg" or (arg.lower().endswith("ffmpeg.exe") and "ffmpeg" in arg.lower()):
                args[i] = ffmpeg_path
                break
        
        return args
    
    def _on_log(self, level: str, message: str):
        """Handle log message"""
        self.log_viewer.add_log(level, message)
        logger.info(f"[FFmpeg] {message}")

