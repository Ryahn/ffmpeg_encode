"""Configuration management for the application"""

import json
import os
import sys
import shutil
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """Manages application configuration"""
    
    def __init__(self):
        # Use platform-appropriate config directory
        if sys.platform == "win32":
            # Windows: Use AppData\Local\VideoEncoder
            appdata = os.getenv('LOCALAPPDATA')
            if appdata:
                self.config_dir = Path(appdata) / "VideoEncoder"
            else:
                # Fallback if LOCALAPPDATA is not set
                self.config_dir = Path.home() / "AppData" / "Local" / "VideoEncoder"
        else:
            # macOS/Linux: Use ~/.video_encoder
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
    
    def get_saved_ffmpeg_commands(self) -> dict:
        """Get saved FFmpeg commands"""
        return self.get("saved_ffmpeg_commands", {})
    
    def set_saved_ffmpeg_commands(self, commands: dict):
        """Set saved FFmpeg commands"""
        self.set("saved_ffmpeg_commands", commands)
    
    def save_ffmpeg_command(self, name: str, command: str):
        """Save an FFmpeg command with a name"""
        commands = self.get_saved_ffmpeg_commands()
        commands[name] = command
        self.set_saved_ffmpeg_commands(commands)
    
    def get_ffmpeg_command(self, name: str) -> Optional[str]:
        """Get a saved FFmpeg command by name"""
        commands = self.get_saved_ffmpeg_commands()
        return commands.get(name)
    
    def delete_ffmpeg_command(self, name: str):
        """Delete a saved FFmpeg command"""
        commands = self.get_saved_ffmpeg_commands()
        if name in commands:
            del commands[name]
            self.set_saved_ffmpeg_commands(commands)
    
    def get_saved_presets(self) -> dict:
        """Get saved preset paths (name -> path mapping)"""
        return self.get("saved_presets", {})
    
    def set_saved_presets(self, presets: dict):
        """Set saved preset paths"""
        self.set("saved_presets", presets)
    
    def save_preset(self, name: str, preset_path: Path):
        """Save a preset by copying it to the config directory"""
        # Create presets directory if it doesn't exist
        presets_dir = self.config_dir / "presets"
        presets_dir.mkdir(parents=True, exist_ok=True)
        
        presets = self.get_saved_presets()
        
        # If preset with this name already exists, use the same path
        if name in presets:
            dest_path = Path(presets[name])
        else:
            # Create a safe filename from the preset name
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name)
            safe_name = safe_name.strip()
            if not safe_name:
                safe_name = "preset"
            
            # Copy preset file to config directory
            dest_path = presets_dir / f"{safe_name}.json"
            
            # Handle duplicate filenames
            counter = 1
            while dest_path.exists():
                dest_path = presets_dir / f"{safe_name}_{counter}.json"
                counter += 1
        
        # Copy/update the preset file
        shutil.copy2(preset_path, dest_path)
        
        # Save the mapping (name -> saved path)
        presets[name] = str(dest_path)
        self.set_saved_presets(presets)
        
        return dest_path
    
    def get_preset_path(self, name: str) -> Optional[Path]:
        """Get the saved path for a preset by name"""
        presets = self.get_saved_presets()
        path_str = presets.get(name)
        if path_str:
            path = Path(path_str)
            if path.exists():
                return path
        return None
    
    def delete_preset(self, name: str):
        """Delete a saved preset"""
        presets = self.get_saved_presets()
        if name in presets:
            path_str = presets[name]
            path = Path(path_str)
            # Delete the file if it exists
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass
            # Remove from config
            del presets[name]
            self.set_saved_presets(presets)
    
    def get_last_used_preset(self) -> Optional[str]:
        """Get the last used preset name"""
        return self.get("last_used_preset")
    
    def set_last_used_preset(self, name: str):
        """Set the last used preset name"""
        self.set("last_used_preset", name)


# Global config instance
config = Config()

