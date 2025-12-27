"""Configuration management for the application"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """Manages application configuration"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".video_encoder"
        self.config_file = self.config_dir / "config.json"
        self.config: Dict[str, Any] = {}
        self._load()
    
    def _load(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception:
                self.config = {}
        else:
            self.config = {}
            self._set_defaults()
    
    def _set_defaults(self):
        """Set default configuration values"""
        self.config = {
            "ffmpeg_path": "",
            "handbrake_path": "",
            "mkvinfo_path": "",
            "default_output_folder": "",
            "default_output_suffix": "_encoded",
            "encoding_mode": "sequential",
            "last_scan_folder": "",
            "skip_existing": False,
            "audio_language_tags": ["en", "eng"],
            "audio_name_patterns": ["English", "ENG"],
            "audio_exclude_patterns": ["Japanese", "JPN", "日本語"],
            "subtitle_language_tags": ["en", "eng"],
            "subtitle_name_patterns": ["Signs.*Song", "Signs$", "English Signs", "^Signs\\s*$"],
            "subtitle_exclude_patterns": ["Japanese", "JPN", "日本語"]
        }
    
    def _save(self):
        """Save configuration to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a configuration value and save"""
        self.config[key] = value
        self._save()
    
    def get_ffmpeg_path(self) -> str:
        """Get FFmpeg executable path"""
        return self.get("ffmpeg_path", "")
    
    def set_ffmpeg_path(self, path: str):
        """Set FFmpeg executable path"""
        self.set("ffmpeg_path", path)
    
    def get_handbrake_path(self) -> str:
        """Get HandBrake executable path"""
        return self.get("handbrake_path", "")
    
    def set_handbrake_path(self, path: str):
        """Set HandBrake executable path"""
        self.set("handbrake_path", path)
    
    def get_mkvinfo_path(self) -> str:
        """Get mkvinfo executable path"""
        return self.get("mkvinfo_path", "")
    
    def set_mkvinfo_path(self, path: str):
        """Set mkvinfo executable path"""
        self.set("mkvinfo_path", path)
    
    def get_default_output_folder(self) -> str:
        """Get default output folder"""
        return self.get("default_output_folder", "")
    
    def set_default_output_folder(self, folder: str):
        """Set default output folder"""
        self.set("default_output_folder", folder)
    
    def get_default_output_suffix(self) -> str:
        """Get default output suffix"""
        return self.get("default_output_suffix", "_encoded")
    
    def set_default_output_suffix(self, suffix: str):
        """Set default output suffix"""
        self.set("default_output_suffix", suffix)
    
    def get_encoding_mode(self) -> str:
        """Get encoding mode preference"""
        return self.get("encoding_mode", "sequential")
    
    def set_encoding_mode(self, mode: str):
        """Set encoding mode preference"""
        self.set("encoding_mode", mode)
    
    def get_last_scan_folder(self) -> str:
        """Get last used scan folder"""
        return self.get("last_scan_folder", "")
    
    def set_last_scan_folder(self, folder: str):
        """Set last used scan folder"""
        self.set("last_scan_folder", folder)
    
    def get_skip_existing(self) -> bool:
        """Get skip existing files preference"""
        return self.get("skip_existing", False)
    
    def set_skip_existing(self, value: bool):
        """Set skip existing files preference"""
        self.set("skip_existing", value)
    
    def get_audio_language_tags(self) -> list:
        """Get audio language tags to match"""
        return self.get("audio_language_tags", ["en", "eng"])
    
    def set_audio_language_tags(self, tags: list):
        """Set audio language tags to match"""
        self.set("audio_language_tags", tags)
    
    def get_audio_name_patterns(self) -> list:
        """Get audio name patterns to match"""
        return self.get("audio_name_patterns", ["English", "ENG"])
    
    def set_audio_name_patterns(self, patterns: list):
        """Set audio name patterns to match"""
        self.set("audio_name_patterns", patterns)
    
    def get_audio_exclude_patterns(self) -> list:
        """Get audio exclude patterns"""
        return self.get("audio_exclude_patterns", ["Japanese", "JPN", "日本語"])
    
    def set_audio_exclude_patterns(self, patterns: list):
        """Set audio exclude patterns"""
        self.set("audio_exclude_patterns", patterns)
    
    def get_subtitle_language_tags(self) -> list:
        """Get subtitle language tags to match"""
        return self.get("subtitle_language_tags", ["en", "eng"])
    
    def set_subtitle_language_tags(self, tags: list):
        """Set subtitle language tags to match"""
        self.set("subtitle_language_tags", tags)
    
    def get_subtitle_name_patterns(self) -> list:
        """Get subtitle name patterns to match"""
        return self.get("subtitle_name_patterns", ["Signs.*Song", "Signs$", "English Signs", "^Signs\\s*$"])
    
    def set_subtitle_name_patterns(self, patterns: list):
        """Set subtitle name patterns to match"""
        self.set("subtitle_name_patterns", patterns)
    
    def get_subtitle_exclude_patterns(self) -> list:
        """Get subtitle exclude patterns"""
        return self.get("subtitle_exclude_patterns", ["Japanese", "JPN", "日本語"])
    
    def set_subtitle_exclude_patterns(self, patterns: list):
        """Set subtitle exclude patterns"""
        self.set("subtitle_exclude_patterns", patterns)


# Global config instance
config = Config()

