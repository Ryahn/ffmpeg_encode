"""Analyze video tracks using mkvinfo or ffprobe"""

import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Any, Pattern
import shutil

from core.subprocess_utils import get_subprocess_kwargs
from utils.config import config

_REGEX_CACHE_MAX_KEYS = 64


class TrackAnalyzer:
    """Analyzes video files to detect audio and subtitle tracks"""
    
    def __init__(self, mkvinfo_path: Optional[str] = None, ffprobe_path: Optional[str] = None):
        self.mkvinfo_path = mkvinfo_path or self._find_mkvinfo()
        self.ffprobe_path = ffprobe_path or self._find_ffprobe()
        self._regex_cache: Dict[tuple, List[Pattern[str]]] = {}

    def _compiled_regexes(self, pattern_strings: List[str]) -> List[Pattern[str]]:
        key = tuple(pattern_strings)
        cached = self._regex_cache.get(key)
        if cached is None:
            if len(self._regex_cache) >= _REGEX_CACHE_MAX_KEYS:
                self._regex_cache.clear()
            cached = [re.compile(p, re.IGNORECASE) for p in pattern_strings]
            self._regex_cache[key] = cached
        return cached
    
    def get_mkvinfo_output(self, file_path: Path) -> Optional[str]:
        """Get raw mkvinfo output for debugging"""
        if not self.mkvinfo_path:
            return None
        try:
            # Hide console window on Windows (for release builds)
            run_kwargs = {
                'args': [self.mkvinfo_path, str(file_path)],
                'capture_output': True,
                'text': True,
                'timeout': 30
            }
            run_kwargs.update(get_subprocess_kwargs())
            
            result = subprocess.run(**run_kwargs)
            if result.returncode == 0:
                return result.stdout
            return result.stderr
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            return None
    
    def _find_mkvinfo(self) -> Optional[str]:
        """Find mkvinfo executable"""
        return shutil.which("mkvinfo") or shutil.which("mkvinfo.exe")
    
    def _find_ffprobe(self) -> Optional[str]:
        """Find ffprobe executable"""
        return shutil.which("ffprobe") or shutil.which("ffprobe.exe")
    
    def analyze_tracks(self, file_path: Path) -> Dict[str, Any]:
        """Analyze tracks in a video file"""
        if file_path.suffix.lower() == ".mkv" and self.mkvinfo_path:
            return self._analyze_mkv_tracks(file_path)
        elif self.ffprobe_path:
            return self._analyze_with_ffprobe(file_path)
        else:
            return {"audio": None, "subtitle": None, "error": "No analyzer available"}
    
    def _analyze_mkv_tracks(self, file_path: Path) -> Dict[str, Optional[int]]:
        """Analyze MKV tracks using mkvinfo"""
        try:
            # Hide console window on Windows (for release builds)
            run_kwargs = {
                'args': [self.mkvinfo_path, str(file_path)],
                'capture_output': True,
                'text': True,
                'timeout': 30
            }
            run_kwargs.update(get_subprocess_kwargs())
            
            result = subprocess.run(**run_kwargs)
            
            if result.returncode != 0:
                return {"audio": None, "subtitle": None, "error": "mkvinfo failed"}
            
            return self._parse_mkvinfo_output(result.stdout)
        except subprocess.TimeoutExpired:
            return {"audio": None, "subtitle": None, "error": "mkvinfo timed out"}
        except (OSError, FileNotFoundError) as e:
            return {"audio": None, "subtitle": None, "error": str(e)}
    
    def _parse_mkvinfo_output(self, output: str) -> Dict[str, Any]:
        """Parse mkvinfo output to find tracks"""
        audio_track = None
        subtitle_track = None
        
        # Collect all tracks first
        tracks = []
        lines = output.splitlines()
        current_track = None
        
        for line in lines:
            # Strip leading whitespace and pipe characters
            line_clean = line.lstrip('| \t')
            
            # Detect track start
            match = re.search(r'\+ Track number: (\d+) \(track ID for mkvmerge & mkvextract: (\d+)\)', line_clean)
            if match:
                # Save previous track if exists
                if current_track is not None:
                    tracks.append(current_track)
                
                # Start new track
                track_id = int(match.group(2))  # mkvmerge track ID (0-indexed)
                current_track = {
                    "id": track_id,
                    "type": None,
                    "language": None,
                    "name": None
                }
                continue
            
            if current_track is None:
                continue
            
            # Detect track type
            match = re.search(r'\+ Track type: (audio|subtitles|video)', line_clean)
            if match:
                current_track["type"] = match.group(1)
                continue
            
            # Detect language (prefer IETF BCP 47 format)
            # IETF BCP 47 can have hyphens, e.g., "eng-eng"
            match = re.search(r'\+ Language \(IETF BCP 47\): ([^\s]+)', line_clean)
            if match:
                current_track["language"] = match.group(1)
                continue
            
            match = re.search(r'\+ Language: (\w+)', line_clean)
            if match and current_track["language"] is None:
                current_track["language"] = match.group(1)
                continue
            
            # Detect track name
            match = re.search(r'\+ Name: (.+)', line_clean)
            if match:
                current_track["name"] = match.group(1).strip()
                continue
        
        # Save last track
        if current_track is not None:
            tracks.append(current_track)
        
        # Process tracks to find English audio and Signs & Songs subtitle
        # Use mkvmerge track ID directly (matches FFmpeg stream index in MKV files)
        # Audio: 1-based for HandBrake CLI. Also record first audio track for "Japanese + English subs" mode.
        sorted_tracks = sorted(tracks, key=lambda t: t["id"])
        first_audio_track = None
        for track in sorted_tracks:
            if track.get("type") != "audio":
                continue
            tid = track.get("id")
            if tid is None:
                continue
            if first_audio_track is None:
                first_audio_track = tid + 1
            if audio_track is None:
                is_english = self._is_english_track(track.get("language"), track.get("name"))
                if is_english:
                    audio_track = tid + 1
                    break

        # Subtitle: explicitly pick the first (by id) English subtitle that matches Signs & Songs.
        # Return 0-based track id (HandBrake CLI expects 1-based; conversion at encode time).
        for track in sorted_tracks:
            if track["type"] != "subtitles":
                continue
            is_english_sub = self._is_english_subtitle_track(track.get("language"), track.get("name"))
            is_signs_songs = self._is_signs_songs_track(track.get("name"))
            if is_english_sub and is_signs_songs:
                stid = track.get("id")
                if stid is not None:
                    subtitle_track = stid
                break
        
        result = {
            "audio": audio_track,
            "first_audio": first_audio_track,
            "subtitle": subtitle_track,
            "error": None,
            "all_tracks": tracks
        }
        # Debug: log what's being returned
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Track analysis result: audio={audio_track}, subtitle={subtitle_track}")
        return result
    
    def _is_english_track(self, language: Optional[str], name: Optional[str]) -> bool:
        """Check if a track is English using configurable patterns"""
        # Get configurable patterns
        lang_tags = config.get_audio_language_tags()
        name_patterns = config.get_audio_name_patterns()
        exclude_patterns = config.get_audio_exclude_patterns()
        
        # Check language tag (handle cases like "eng-eng" by checking if it starts with or contains the tag)
        if language:
            lang_lower = language.lower()
            for tag in lang_tags:
                if lang_lower == tag.lower() or lang_lower.startswith(tag.lower() + "-") or lang_lower.startswith(tag.lower() + "_"):
                    return True
        
        # Check name for English indicators (but not excluded patterns)
        if name:
            matches_pattern = False
            for compiled in self._compiled_regexes(name_patterns):
                if compiled.search(name):
                    matches_pattern = True
                    break

            if matches_pattern:
                for compiled in self._compiled_regexes(exclude_patterns):
                    if compiled.search(name):
                        return False
                return True
        
        return False
    
    def _is_signs_songs_track(self, name: Optional[str]) -> bool:
        """Check if a subtitle track matches Signs & Songs pattern using configurable patterns"""
        if not name:
            return False
        
        patterns = config.get_subtitle_name_patterns()
        for compiled in self._compiled_regexes(patterns):
            if compiled.search(name):
                return True

        return False
    
    def _matches_english_subtitle_language(self, language: Optional[str]) -> bool:
        """True if the track's language tag is English (no exclude check). Used when Japanese-audio mode needs first English sub."""
        if not language:
            return False
        lang_lower = language.lower()
        for tag in config.get_subtitle_language_tags():
            if lang_lower == tag.lower() or lang_lower.startswith(tag.lower() + "-") or lang_lower.startswith(tag.lower() + "_"):
                return True
        return False

    def _is_english_subtitle_track(self, language: Optional[str], name: Optional[str]) -> bool:
        """Check if a subtitle track is English using configurable patterns (language + exclude by name)."""
        lang_tags = config.get_subtitle_language_tags()
        exclude_patterns = config.get_subtitle_exclude_patterns()

        if language:
            lang_lower = language.lower()
            for tag in lang_tags:
                if lang_lower == tag.lower() or lang_lower.startswith(tag.lower() + "-") or lang_lower.startswith(tag.lower() + "_"):
                    if name:
                        for compiled in self._compiled_regexes(exclude_patterns):
                            if compiled.search(name):
                                return False
                    return True
        return False
    
    def _analyze_with_ffprobe(self, file_path: Path) -> Dict[str, Optional[int]]:
        """Analyze tracks using ffprobe (fallback)"""
        # This is a simplified version - full implementation would parse ffprobe JSON
        # For now, return None tracks and let the user manually select
        return {"audio": None, "subtitle": None, "error": "FFprobe analysis not fully implemented"}

