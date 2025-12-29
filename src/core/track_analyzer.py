"""Analyze video tracks using mkvinfo or ffprobe"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Tuple, List
import shutil
from utils.config import config


def _get_subprocess_kwargs() -> dict:
    """Get subprocess kwargs with hidden console window on Windows"""
    kwargs = {}
    if sys.platform == 'win32':
        # Use CREATE_NO_WINDOW constant (0x08000000) to prevent console window
        # This works with both Popen and run, and still allows stdout/stderr capture
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        else:
            # Fallback to constant value if attribute not available
            kwargs['creationflags'] = 0x08000000
    return kwargs


class TrackAnalyzer:
    """Analyzes video files to detect audio and subtitle tracks"""
    
    def __init__(self, mkvinfo_path: Optional[str] = None, ffprobe_path: Optional[str] = None):
        self.mkvinfo_path = mkvinfo_path or self._find_mkvinfo()
        self.ffprobe_path = ffprobe_path or self._find_ffprobe()
    
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
            run_kwargs.update(_get_subprocess_kwargs())
            
            result = subprocess.run(**run_kwargs)
            if result.returncode == 0:
                return result.stdout
            return result.stderr
        except Exception:
            return None
    
    def _find_mkvinfo(self) -> Optional[str]:
        """Find mkvinfo executable"""
        return shutil.which("mkvinfo") or shutil.which("mkvinfo.exe")
    
    def _find_ffprobe(self) -> Optional[str]:
        """Find ffprobe executable"""
        return shutil.which("ffprobe") or shutil.which("ffprobe.exe")
    
    def analyze_tracks(self, file_path: Path) -> Dict[str, Optional[int]]:
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
            run_kwargs.update(_get_subprocess_kwargs())
            
            result = subprocess.run(**run_kwargs)
            
            if result.returncode != 0:
                return {"audio": None, "subtitle": None, "error": "mkvinfo failed"}
            
            return self._parse_mkvinfo_output(result.stdout)
        except subprocess.TimeoutExpired:
            return {"audio": None, "subtitle": None, "error": "mkvinfo timed out"}
        except Exception as e:
            return {"audio": None, "subtitle": None, "error": str(e)}
    
    def _parse_mkvinfo_output(self, output: str) -> Dict[str, Optional[int]]:
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
        # Convert to 1-indexed for HandBrake compatibility (same as PowerShell script)
        # Process tracks in order (as they appear in the file) to match PowerShell behavior
        for track in sorted(tracks, key=lambda t: t["id"]):
            if track["type"] == "audio" and audio_track is None:
                is_english = self._is_english_track(track["language"], track["name"])
                if is_english:
                    # Return 1-indexed track number (mkvmerge track ID + 1)
                    # This matches the PowerShell script behavior: $AudioTrackNumber = $CurrentTrackNumber + 1
                    audio_track = track["id"] + 1
                    # Break after finding first English audio track (matches PowerShell behavior)
                    break
            
            if track["type"] == "subtitles" and subtitle_track is None:
                is_english_sub = self._is_english_subtitle_track(track.get("language"), track.get("name"))
                is_signs_songs = self._is_signs_songs_track(track.get("name"))
                # Only set subtitle_track if BOTH conditions are met
                if is_english_sub and is_signs_songs:
                    subtitle_track = track["id"] + 1  # Convert to 1-indexed
                    # Break after finding first matching subtitle track (similar to audio)
                    break
        
        result = {
            "audio": audio_track,
            "subtitle": subtitle_track,
            "error": None,
            "all_tracks": tracks  # For debugging
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
            # Check if name matches any pattern
            matches_pattern = False
            for pattern in name_patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    matches_pattern = True
                    break
            
            if matches_pattern:
                # Check if it matches any exclude pattern
                for exclude_pattern in exclude_patterns:
                    if re.search(exclude_pattern, name, re.IGNORECASE):
                        return False
                return True
        
        return False
    
    def _is_signs_songs_track(self, name: Optional[str]) -> bool:
        """Check if a subtitle track matches Signs & Songs pattern using configurable patterns"""
        if not name:
            return False
        
        patterns = config.get_subtitle_name_patterns()
        
        for pattern in patterns:
            if re.search(pattern, name, re.IGNORECASE):
                return True
        
        return False
    
    def _is_english_subtitle_track(self, language: Optional[str], name: Optional[str]) -> bool:
        """Check if a subtitle track is English using configurable patterns"""
        # Get configurable patterns
        lang_tags = config.get_subtitle_language_tags()
        exclude_patterns = config.get_subtitle_exclude_patterns()
        
        # Check language tag (primary method for determining English subtitles)
        if language:
            lang_lower = language.lower()
            for tag in lang_tags:
                if lang_lower == tag.lower() or lang_lower.startswith(tag.lower() + "-") or lang_lower.startswith(tag.lower() + "_"):
                    # Language matches, but check if it's excluded by name
                    if name:
                        for exclude_pattern in exclude_patterns:
                            if re.search(exclude_pattern, name, re.IGNORECASE):
                                return False
                    return True
        
        # If no language tag or doesn't match, return False
        # (We don't check name patterns here because those are for Signs & Songs detection, not English detection)
        return False
    
    def _analyze_with_ffprobe(self, file_path: Path) -> Dict[str, Optional[int]]:
        """Analyze tracks using ffprobe (fallback)"""
        # This is a simplified version - full implementation would parse ffprobe JSON
        # For now, return None tracks and let the user manually select
        return {"audio": None, "subtitle": None, "error": "FFprobe analysis not fully implemented"}

