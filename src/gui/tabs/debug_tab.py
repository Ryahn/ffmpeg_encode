"""Debug tab for viewing mkvinfo output"""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from typing import Optional
import os
import sys
import subprocess
import shutil
from core.track_analyzer import TrackAnalyzer
from utils.config import config
from utils.logger import logger


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
        mkvinfo_tab = self.results_tabs.tab("mkvinfo Output")
        mkvinfo_btn_frame = ctk.CTkFrame(mkvinfo_tab)
        mkvinfo_btn_frame.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkButton(mkvinfo_btn_frame, text="Copy", width=80, command=lambda: self._copy_text(self.mkvinfo_text)).pack(side="left", padx=(0, 5), pady=5)
        self.mkvinfo_text = ctk.CTkTextbox(
            mkvinfo_tab,
            font=ctk.CTkFont(family="Courier", size=10)
        )
        self.mkvinfo_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Track analysis tab
        self.results_tabs.add("Track Analysis")
        analysis_tab = self.results_tabs.tab("Track Analysis")
        analysis_btn_frame = ctk.CTkFrame(analysis_tab)
        analysis_btn_frame.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkButton(analysis_btn_frame, text="Copy", width=80, command=self._copy_analysis).pack(side="left", padx=(0, 5), pady=5)
        analysis_frame = ctk.CTkScrollableFrame(analysis_tab)
        analysis_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.analysis_label = ctk.CTkLabel(
            analysis_frame,
            text="Select a file and click Analyze to see track analysis",
            anchor="w",
            justify="left"
        )
        self.analysis_label.pack(fill="x", padx=10, pady=10)
        self._last_analysis_text = ""

        # MediaInfo tab
        self.results_tabs.add("MediaInfo")
        self._setup_mediainfo_tab()

        # Log files tab
        self.results_tabs.add("Log Files")
        self._setup_log_tab()

        self.current_file: Optional[Path] = None

    def _copy_text(self, textbox: ctk.CTkTextbox) -> None:
        """Copy textbox content to clipboard (or selection if any)."""
        try:
            text = textbox.get("1.0", "end-1c")
            if text.strip():
                root = self.winfo_toplevel()
                root.clipboard_clear()
                root.clipboard_append(text)
        except Exception:
            pass

    def _copy_analysis(self) -> None:
        """Copy last track analysis text to clipboard."""
        if not self._last_analysis_text:
            return
        try:
            root = self.winfo_toplevel()
            root.clipboard_clear()
            root.clipboard_append(self._last_analysis_text)
        except Exception:
            pass

    def _setup_mediainfo_tab(self) -> None:
        """Setup MediaInfo tab: run mediainfo on current file, show output, Copy button."""
        mi_tab = self.results_tabs.tab("MediaInfo")
        mi_btn_frame = ctk.CTkFrame(mi_tab)
        mi_btn_frame.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkButton(mi_btn_frame, text="Run MediaInfo", width=120, command=self._run_mediainfo).pack(side="left", padx=(0, 5), pady=5)
        ctk.CTkButton(mi_btn_frame, text="Copy", width=80, command=lambda: self._copy_text(self.mediainfo_text)).pack(side="left", padx=(0, 5), pady=5)
        self.mediainfo_text = ctk.CTkTextbox(
            mi_tab,
            font=ctk.CTkFont(family="Courier", size=10)
        )
        self.mediainfo_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.mediainfo_text.insert("1.0", "Select a file and click Analyze, then use 'Run MediaInfo' to dump output here.")
        self.mediainfo_text.configure(state="disabled")

    def _run_mediainfo(self) -> None:
        """Run mediainfo on current file and show output."""
        if not self.current_file or not self.current_file.exists():
            self.mediainfo_text.configure(state="normal")
            self.mediainfo_text.delete("1.0", "end")
            self.mediainfo_text.insert("1.0", "No file selected or file does not exist. Select a file and click Analyze first.")
            self.mediainfo_text.configure(state="disabled")
            return
        mediainfo_path = config.get_mediainfo_path()
        if mediainfo_path and Path(mediainfo_path).exists():
            mediainfo_path = str(Path(mediainfo_path).resolve())
        else:
            mediainfo_path = shutil.which("mediainfo") or shutil.which("mediainfo.exe")
        if not mediainfo_path:
            self.mediainfo_text.configure(state="normal")
            self.mediainfo_text.delete("1.0", "end")
            self.mediainfo_text.insert("1.0", "MediaInfo not found. Set the path in Settings → Executable Paths → MediaInfo, or install MediaInfo and add it to PATH.")
            self.mediainfo_text.configure(state="disabled")
            return
        run_kw = {
            "args": [mediainfo_path, str(self.current_file)],
            "capture_output": True,
            "text": True,
            "timeout": 30,
        }
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            run_kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            result = subprocess.run(**run_kw)
            out = result.stdout or result.stderr or "(no output)"
        except subprocess.TimeoutExpired:
            out = "mediainfo timed out."
        except Exception as e:
            out = f"Error running mediainfo: {e}"
        self.mediainfo_text.configure(state="normal")
        self.mediainfo_text.delete("1.0", "end")
        self.mediainfo_text.insert("1.0", out)
        self.mediainfo_text.configure(state="disabled")
    
    def _setup_log_tab(self):
        """Setup the log files tab"""
        log_tab = self.results_tabs.tab("Log Files")
        
        # Log file info frame
        info_frame = ctk.CTkFrame(log_tab)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            info_frame,
            text="Current Log File:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        log_file = logger.get_log_file()
        if log_file and log_file.exists():
            log_path_str = str(log_file)
            self.log_path_label = ctk.CTkLabel(
                info_frame,
                text=log_path_str,
                anchor="w",
                justify="left",
                font=ctk.CTkFont(family="Courier", size=10)
            )
            self.log_path_label.pack(fill="x", padx=10, pady=5)
        else:
            self.log_path_label = ctk.CTkLabel(
                info_frame,
                text="No log file available (logging may have failed to initialize)",
                anchor="w",
                text_color="gray"
            )
            self.log_path_label.pack(fill="x", padx=10, pady=5)
        
        # Button frame
        button_frame = ctk.CTkFrame(log_tab)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="Open Log File",
            command=self._open_log_file,
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Open Log Directory",
            command=self._open_log_directory,
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Refresh Log View",
            command=self._refresh_log_view,
            width=150
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame,
            text="Copy",
            width=80,
            command=lambda: self._copy_text(self.log_display)
        ).pack(side="left", padx=5)

        # Recent logs display
        log_display_frame = ctk.CTkFrame(log_tab)
        log_display_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            log_display_frame,
            text="Recent Log Entries (last 100):",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        self.log_display = ctk.CTkTextbox(
            log_display_frame,
            font=ctk.CTkFont(family="Courier", size=9),
            wrap="word"
        )
        self.log_display.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Load initial log view
        self._refresh_log_view()
    
    def _open_log_file(self):
        """Open the current log file in default text editor"""
        log_file = logger.get_log_file()
        if not log_file or not log_file.exists():
            return
        
        try:
            if sys.platform == "win32":
                os.startfile(str(log_file))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(log_file)])
            else:
                subprocess.run(["xdg-open", str(log_file)])
        except Exception as e:
            # Fallback: try to open with default editor
            try:
                if sys.platform == "win32":
                    os.startfile(str(log_file), "edit")
                else:
                    subprocess.run(["xdg-open", str(log_file)])
            except:
                pass
    
    def _open_log_directory(self):
        """Open the log directory in file explorer"""
        log_file = logger.get_log_file()
        if not log_file:
            log_dir = Path.home() / ".video_encoder" / "logs"
        else:
            log_dir = log_file.parent
        
        if not log_dir.exists():
            return
        
        try:
            if sys.platform == "win32":
                os.startfile(str(log_dir))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(log_dir)])
            else:
                subprocess.run(["xdg-open", str(log_dir)])
        except Exception as e:
            pass
    
    def _refresh_log_view(self):
        """Refresh the log display with recent entries"""
        self.log_display.delete("1.0", "end")
        
        # Update log file path if it changed
        log_file = logger.get_log_file()
        if log_file and log_file.exists():
            log_path_str = str(log_file)
            if hasattr(self, 'log_path_label'):
                self.log_path_label.configure(text=log_path_str)
        
        # Get recent logs
        recent_logs = logger.get_recent_logs(100)
        
        if not recent_logs:
            self.log_display.insert("1.0", "No log entries yet.")
            return
        
        # Format logs for display
        log_text = ""
        for level, message in recent_logs:
            # Format with level indicator
            log_text += f"[{level}] {message}\n"
        
        self.log_display.insert("1.0", log_text)
        # Scroll to bottom
        self.log_display.see("end")
    
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
        sub = tracks.get("subtitle")
        analysis_text += f"Audio Track: {tracks.get('audio', 'Not found')}\n"
        if sub is not None:
            analysis_text += f"Subtitle Track: {sub} (HandBrake --subtitle {sub + 1})\n"
        else:
            analysis_text += "Subtitle Track: Not found\n"
        
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

        self._last_analysis_text = analysis_text
        self.analysis_label.configure(text=analysis_text)

