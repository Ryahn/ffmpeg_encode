"""Debug tab for viewing mkvinfo output"""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from typing import Optional
from core.track_analyzer import TrackAnalyzer
from utils.config import config


class DebugTab(ctk.CTkFrame):
    """Tab for debugging track detection"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        mkvinfo_path = config.get_mkvinfo_path() or "mkvinfo"
        self.track_analyzer = TrackAnalyzer(
            mkvinfo_path=mkvinfo_path if mkvinfo_path != "mkvinfo" else None
        )
        
        # File selection
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(file_frame, text="Video File:").pack(side="left", padx=5)
        self.file_label = ctk.CTkLabel(
            file_frame,
            text="No file selected",
            width=400,
            anchor="w"
        )
        self.file_label.pack(side="left", padx=5)
        
        ctk.CTkButton(
            file_frame,
            text="Browse",
            command=self._browse_file,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            file_frame,
            text="Analyze",
            command=self._analyze_file,
            width=100
        ).pack(side="left", padx=5)
        
        # Results frame
        results_frame = ctk.CTkFrame(self)
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tabs for different views
        self.results_tabs = ctk.CTkTabview(results_frame)
        self.results_tabs.pack(fill="both", expand=True)
        
        # mkvinfo output tab
        self.results_tabs.add("mkvinfo Output")
        self.mkvinfo_text = ctk.CTkTextbox(
            self.results_tabs.tab("mkvinfo Output"),
            font=ctk.CTkFont(family="Courier", size=10)
        )
        self.mkvinfo_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Track analysis tab
        self.results_tabs.add("Track Analysis")
        analysis_frame = ctk.CTkScrollableFrame(self.results_tabs.tab("Track Analysis"))
        analysis_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.analysis_label = ctk.CTkLabel(
            analysis_frame,
            text="Select a file and click Analyze to see track analysis",
            anchor="w",
            justify="left"
        )
        self.analysis_label.pack(fill="x", padx=10, pady=10)
        
        self.current_file: Optional[Path] = None
    
    def _browse_file(self):
        """Browse for a video file"""
        file = filedialog.askopenfilename(
            title="Select video file",
            filetypes=[
                ("Video files", "*.mkv *.mp4 *.mov *.avi"),
                ("All files", "*.*")
            ]
        )
        
        if file:
            self.current_file = Path(file)
            self.file_label.configure(text=self.current_file.name)
    
    def _analyze_file(self):
        """Analyze the selected file"""
        if not self.current_file:
            return
        
        # Get mkvinfo output
        mkvinfo_output = self.track_analyzer.get_mkvinfo_output(self.current_file)
        
        if mkvinfo_output:
            self.mkvinfo_text.delete("1.0", "end")
            self.mkvinfo_text.insert("1.0", mkvinfo_output)
        else:
            self.mkvinfo_text.delete("1.0", "end")
            self.mkvinfo_text.insert("1.0", "Failed to get mkvinfo output. Make sure mkvinfo is installed and the file is valid.")
        
        # Analyze tracks
        tracks = self.track_analyzer.analyze_tracks(self.current_file)
        
        # Display analysis results
        analysis_text = f"File: {self.current_file.name}\n\n"
        analysis_text += f"Audio Track: {tracks.get('audio', 'Not found')}\n"
        analysis_text += f"Subtitle Track: {tracks.get('subtitle', 'Not found')}\n"
        
        if tracks.get("error"):
            analysis_text += f"\nError: {tracks['error']}\n"
        
        # Show all tracks found
        if tracks.get("all_tracks"):
            analysis_text += "\n" + "="*50 + "\n"
            analysis_text += "All Tracks Found:\n"
            for track in tracks["all_tracks"]:
                analysis_text += f"\nTrack ID {track['id']} ({track['id'] + 1} for HandBrake):\n"
                analysis_text += f"  Type: {track['type'] or 'Unknown'}\n"
                analysis_text += f"  Language: {track['language'] or 'Not set'}\n"
                analysis_text += f"  Name: {track['name'] or 'Not set'}\n"
                
                # Show why it was or wasn't selected
                if track["type"] == "audio":
                    # Use the internal method (we'll make it accessible)
                    try:
                        is_eng = self.track_analyzer._is_english_track(track["language"], track["name"])
                        analysis_text += f"  English? {is_eng}\n"
                    except:
                        analysis_text += f"  English? (check failed)\n"
                elif track["type"] == "subtitles":
                    try:
                        is_eng = self.track_analyzer._is_english_subtitle_track(track["language"], track["name"])
                        is_signs = self.track_analyzer._is_signs_songs_track(track["name"])
                        analysis_text += f"  English? {is_eng}, Signs & Songs? {is_signs}\n"
                    except:
                        analysis_text += f"  English? (check failed), Signs & Songs? (check failed)\n"
        
        analysis_text += "\n" + "="*50 + "\n\n"
        analysis_text += "Detection Settings:\n"
        analysis_text += f"Audio Language Tags: {', '.join(config.get_audio_language_tags())}\n"
        analysis_text += f"Audio Name Patterns: {', '.join(config.get_audio_name_patterns())}\n"
        analysis_text += f"Audio Exclude Patterns: {', '.join(config.get_audio_exclude_patterns())}\n"
        analysis_text += f"Subtitle Language Tags: {', '.join(config.get_subtitle_language_tags())}\n"
        analysis_text += f"Subtitle Name Patterns: {', '.join(config.get_subtitle_name_patterns())}\n"
        analysis_text += f"Subtitle Exclude Patterns: {', '.join(config.get_subtitle_exclude_patterns())}\n"
        
        self.analysis_label.configure(text=analysis_text)

