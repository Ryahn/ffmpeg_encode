"""Settings tab for configuration"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from utils.config import config
from core.package_manager import PackageManager


class SettingsTab(ctk.CTkFrame):
    """Tab for application settings"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.package_manager = PackageManager()
        
        # Create scrollable frame
        scrollable = ctk.CTkScrollableFrame(self)
        scrollable.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Path settings section
        path_frame = ctk.CTkFrame(scrollable)
        path_frame.pack(fill="x", pady=10)
        
        path_header = ctk.CTkFrame(path_frame)
        path_header.pack(anchor="w", padx=10, pady=10, fill="x")
        
        ctk.CTkLabel(
            path_header,
            text="Executable Paths",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=5)
        
        self._create_help_icon(
            path_header,
            "Paths to FFmpeg, HandBrake CLI, and mkvinfo executables.\n"
            "Use 'Auto-detect' to find them automatically, or 'Browse' to select manually.\n"
            "If not found, the application can install them via Chocolatey (Windows) or Homebrew (Mac)."
        )
        
        # FFmpeg path
        self._create_path_setting(
            path_frame,
            "FFmpeg:",
            config.get_ffmpeg_path(),
            self._browse_ffmpeg,
            self._auto_detect_ffmpeg,
            "Path to the FFmpeg executable.\n"
            "FFmpeg is used for encoding videos when using the FFmpeg tab.\n"
            "If not found, can be installed via Chocolatey (Windows) or Homebrew (Mac)."
        )
        
        # HandBrake path
        self._create_path_setting(
            path_frame,
            "HandBrake CLI:",
            config.get_handbrake_path(),
            self._browse_handbrake,
            self._auto_detect_handbrake,
            "Path to the HandBrake CLI executable (HandBrakeCLI.exe on Windows).\n"
            "HandBrake is used for encoding videos when using the HandBrake tab.\n"
            "If not found, can be installed via Chocolatey (Windows) or Homebrew (Mac)."
        )
        
        # mkvinfo path
        self._create_path_setting(
            path_frame,
            "mkvinfo:",
            config.get_mkvinfo_path(),
            self._browse_mkvinfo,
            self._auto_detect_mkvinfo,
            "Path to the mkvinfo executable (part of MKVToolNix).\n"
            "mkvinfo is used to analyze MKV files and detect audio/subtitle tracks.\n"
            "If not found, can be installed via Chocolatey (Windows) or Homebrew (Mac)."
        )
        
        # Output settings section
        output_frame = ctk.CTkFrame(scrollable)
        output_frame.pack(fill="x", pady=10)
        
        output_header = ctk.CTkFrame(output_frame)
        output_header.pack(anchor="w", padx=10, pady=10, fill="x")
        
        ctk.CTkLabel(
            output_header,
            text="Output Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=5)
        
        self._create_help_icon(
            output_header,
            "Default suffix added to output filenames.\n"
            "Example: If source is 'video.mkv' and suffix is '_encoded',\n"
            "the output will be 'video_encoded.mp4'."
        )
        
        # Default output suffix
        suffix_frame = ctk.CTkFrame(output_frame)
        suffix_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(suffix_frame, text="Default Output Suffix:").pack(side="left", padx=5)
        self.suffix_entry = ctk.CTkEntry(suffix_frame, width=200)
        self.suffix_entry.insert(0, config.get_default_output_suffix())
        self.suffix_entry.pack(side="left", padx=5)
        self.suffix_entry.bind("<KeyRelease>", self._on_suffix_changed)
        
        # Encoding settings section
        encoding_frame = ctk.CTkFrame(scrollable)
        encoding_frame.pack(fill="x", pady=10)
        
        encoding_header = ctk.CTkFrame(encoding_frame)
        encoding_header.pack(anchor="w", padx=10, pady=10, fill="x")
        
        ctk.CTkLabel(
            encoding_header,
            text="Encoding Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=5)
        
        self._create_help_icon(
            encoding_header,
            "Encoding mode:\n"
            "- Sequential: Encode one file at a time\n"
            "- Parallel: Encode multiple files simultaneously\n\n"
            "Skip existing: Skip files that already have encoded versions."
        )
        
        # Encoding mode
        mode_frame = ctk.CTkFrame(encoding_frame)
        mode_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(mode_frame, text="Default Encoding Mode:").pack(side="left", padx=5)
        self.mode_var = ctk.StringVar(value=config.get_encoding_mode())
        ctk.CTkRadioButton(
            mode_frame,
            text="Sequential",
            variable=self.mode_var,
            value="sequential",
            command=self._on_mode_changed
        ).pack(side="left", padx=5)
        ctk.CTkRadioButton(
            mode_frame,
            text="Parallel",
            variable=self.mode_var,
            value="parallel",
            command=self._on_mode_changed
        ).pack(side="left", padx=5)
        
        # Skip existing
        skip_frame = ctk.CTkFrame(encoding_frame)
        skip_frame.pack(fill="x", padx=10, pady=5)
        
        self.skip_var = ctk.BooleanVar(value=config.get_skip_existing())
        ctk.CTkCheckBox(
            skip_frame,
            text="Skip existing encoded files by default",
            variable=self.skip_var,
            command=self._on_skip_changed
        ).pack(anchor="w")
        
        # Track detection settings section
        track_frame = ctk.CTkFrame(scrollable)
        track_frame.pack(fill="x", pady=10)
        
        track_header = ctk.CTkFrame(track_frame)
        track_header.pack(anchor="w", padx=10, pady=10, fill="x")
        
        ctk.CTkLabel(
            track_header,
            text="Track Detection Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=5)
        
        self._create_help_icon(
            track_header,
            "Configure how the application detects audio and subtitle tracks.\n\n"
            "Language Tags: Language codes to match (e.g., 'en', 'eng')\n"
            "Name Patterns: Regex patterns to match in track names (comma-separated)\n"
            "Exclude Patterns: Patterns to exclude (e.g., 'Japanese' to skip Japanese tracks)\n\n"
            "Use the Debug tab to see what tracks are found and why they're selected."
        )
        
        # Audio language tags
        self._create_list_setting(
            track_frame,
            "Audio Language Tags:",
            config.get_audio_language_tags(),
            self._on_audio_lang_tags_changed,
            "Language codes to match for English audio tracks.\n"
            "Comma-separated list (e.g., 'en, eng').\n"
            "Matches if the track's language tag equals or starts with these values."
        )
        
        # Audio name patterns
        self._create_list_setting(
            track_frame,
            "Audio Name Patterns:",
            config.get_audio_name_patterns(),
            self._on_audio_name_patterns_changed,
            "Regex patterns to match in audio track names.\n"
            "Comma-separated list (e.g., 'English, ENG').\n"
            "If a track name matches any pattern, it's considered English (unless excluded)."
        )
        
        # Audio exclude patterns
        self._create_list_setting(
            track_frame,
            "Audio Exclude Patterns:",
            config.get_audio_exclude_patterns(),
            self._on_audio_exclude_patterns_changed,
            "Patterns to exclude from audio track selection.\n"
            "Comma-separated list (e.g., 'Japanese, JPN, 日本語').\n"
            "Tracks matching these patterns will be skipped even if they match language/name patterns."
        )
        
        # Subtitle language tags
        self._create_list_setting(
            track_frame,
            "Subtitle Language Tags:",
            config.get_subtitle_language_tags(),
            self._on_subtitle_lang_tags_changed,
            "Language codes to match for English subtitle tracks.\n"
            "Comma-separated list (e.g., 'en, eng').\n"
            "Matches if the track's language tag equals or starts with these values."
        )
        
        # Subtitle name patterns
        self._create_list_setting(
            track_frame,
            "Subtitle Name Patterns:",
            config.get_subtitle_name_patterns(),
            self._on_subtitle_name_patterns_changed,
            "Regex patterns to match in subtitle track names for 'Signs & Songs' detection.\n"
            "Comma-separated list (e.g., 'Signs.*Song, Signs$, English Signs').\n"
            "These are regex patterns, so use '.*' for 'any characters' and '$' for 'end of string'."
        )
        
        # Subtitle exclude patterns
        self._create_list_setting(
            track_frame,
            "Subtitle Exclude Patterns:",
            config.get_subtitle_exclude_patterns(),
            self._on_subtitle_exclude_patterns_changed,
            "Patterns to exclude from subtitle track selection.\n"
            "Comma-separated list (e.g., 'Japanese, JPN, 日本語').\n"
            "Tracks matching these patterns will be skipped even if they match language/name patterns."
        )
    
    def _create_help_icon(self, parent, help_text: str):
        """Create a help icon with tooltip"""
        help_label = ctk.CTkLabel(
            parent,
            text="?",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="gray",
            cursor="hand2",
            width=20
        )
        help_label.pack(side="left", padx=5)
        
        def show_help(event=None):
            messagebox.showinfo("Help", help_text)
        
        help_label.bind("<Button-1>", show_help)
        help_label.bind("<Enter>", lambda e: help_label.configure(text_color="blue"))
        help_label.bind("<Leave>", lambda e: help_label.configure(text_color="gray"))
        
        return help_label
    
    def _create_path_setting(self, parent, label, value, browse_cmd, auto_detect_cmd, help_text: str = None):
        """Create a path setting row"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=5)
        
        label_frame = ctk.CTkFrame(frame)
        label_frame.pack(side="left", padx=5)
        
        ctk.CTkLabel(label_frame, text=label, width=120).pack(side="left", padx=5)
        
        if help_text:
            self._create_help_icon(label_frame, help_text)
        
        entry = ctk.CTkEntry(frame, width=400)
        entry.insert(0, value)
        entry.pack(side="left", padx=5, fill="x", expand=True)
        
        ctk.CTkButton(
            frame,
            text="Browse",
            command=lambda: browse_cmd(entry),
            width=80
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            frame,
            text="Auto-detect",
            command=lambda: auto_detect_cmd(entry),
            width=100
        ).pack(side="left", padx=5)
        
        return entry
    
    def _browse_ffmpeg(self, entry):
        """Browse for FFmpeg executable"""
        file = filedialog.askopenfilename(
            title="Select FFmpeg executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if file:
            entry.delete(0, "end")
            entry.insert(0, file)
            config.set_ffmpeg_path(file)
    
    def _browse_handbrake(self, entry):
        """Browse for HandBrake executable"""
        file = filedialog.askopenfilename(
            title="Select HandBrake CLI executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if file:
            entry.delete(0, "end")
            entry.insert(0, file)
            config.set_handbrake_path(file)
    
    def _browse_mkvinfo(self, entry):
        """Browse for mkvinfo executable"""
        file = filedialog.askopenfilename(
            title="Select mkvinfo executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if file:
            entry.delete(0, "end")
            entry.insert(0, file)
            config.set_mkvinfo_path(file)
    
    def _auto_detect_ffmpeg(self, entry):
        """Auto-detect FFmpeg"""
        found, path = self.package_manager.check_ffmpeg()
        if found:
            entry.delete(0, "end")
            entry.insert(0, path)
            config.set_ffmpeg_path(path)
        else:
            from tkinter import messagebox
            messagebox.showinfo("Not Found", "FFmpeg not found. Would you like to install it?")
            # TODO: Offer to install
    
    def _auto_detect_handbrake(self, entry):
        """Auto-detect HandBrake"""
        found, path = self.package_manager.check_handbrake()
        if found:
            entry.delete(0, "end")
            entry.insert(0, path)
            config.set_handbrake_path(path)
        else:
            from tkinter import messagebox
            messagebox.showinfo("Not Found", "HandBrake CLI not found. Would you like to install it?")
            # TODO: Offer to install
    
    def _auto_detect_mkvinfo(self, entry):
        """Auto-detect mkvinfo"""
        found, path = self.package_manager.check_mkvinfo()
        if found:
            entry.delete(0, "end")
            entry.insert(0, path)
            config.set_mkvinfo_path(path)
        else:
            from tkinter import messagebox
            messagebox.showinfo("Not Found", "mkvinfo not found. Would you like to install it?")
            # TODO: Offer to install
    
    def _on_suffix_changed(self, event=None):
        """Handle suffix change"""
        suffix = self.suffix_entry.get()
        config.set_default_output_suffix(suffix)
    
    def _on_mode_changed(self):
        """Handle encoding mode change"""
        mode = self.mode_var.get()
        config.set_encoding_mode(mode)
    
    def _on_skip_changed(self):
        """Handle skip existing change"""
        value = self.skip_var.get()
        config.set_skip_existing(value)
    
    def _create_list_setting(self, parent, label, value_list, callback, help_text: str = None):
        """Create a list setting row (comma-separated)"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=5)
        
        label_frame = ctk.CTkFrame(frame)
        label_frame.pack(side="left", padx=5)
        
        ctk.CTkLabel(label_frame, text=label, width=200).pack(side="left", padx=5)
        
        if help_text:
            self._create_help_icon(label_frame, help_text)
        
        entry = ctk.CTkEntry(frame, width=500)
        entry.insert(0, ", ".join(value_list))
        entry.pack(side="left", padx=5, fill="x", expand=True)
        entry.bind("<KeyRelease>", lambda e, cb=callback: cb(entry.get()))
        
        return entry
    
    def _on_audio_lang_tags_changed(self, value: str):
        """Handle audio language tags change"""
        tags = [tag.strip() for tag in value.split(",") if tag.strip()]
        config.set_audio_language_tags(tags)
    
    def _on_audio_name_patterns_changed(self, value: str):
        """Handle audio name patterns change"""
        patterns = [p.strip() for p in value.split(",") if p.strip()]
        config.set_audio_name_patterns(patterns)
    
    def _on_audio_exclude_patterns_changed(self, value: str):
        """Handle audio exclude patterns change"""
        patterns = [p.strip() for p in value.split(",") if p.strip()]
        config.set_audio_exclude_patterns(patterns)
    
    def _on_subtitle_lang_tags_changed(self, value: str):
        """Handle subtitle language tags change"""
        tags = [tag.strip() for tag in value.split(",") if tag.strip()]
        config.set_subtitle_language_tags(tags)
    
    def _on_subtitle_name_patterns_changed(self, value: str):
        """Handle subtitle name patterns change"""
        patterns = [p.strip() for p in value.split(",") if p.strip()]
        config.set_subtitle_name_patterns(patterns)
    
    def _on_subtitle_exclude_patterns_changed(self, value: str):
        """Handle subtitle exclude patterns change"""
        patterns = [p.strip() for p in value.split(",") if p.strip()]
        config.set_subtitle_exclude_patterns(patterns)

