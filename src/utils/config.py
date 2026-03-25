"""Configuration management for the application"""

import json
import os
import re
import sys
import shutil
import threading
from pathlib import Path
from typing import Optional, Dict, Any

from utils.ffmpeg_encoding import ALLOWED_MANUAL_PIX_FMT

CONFIG_SAVE_DEBOUNCE_SEC = 0.4


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
        self._save_lock = threading.Lock()
        self._dirty = False
        self._save_timer: Optional[threading.Timer] = None
        self._load()
    
    def _load(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, OSError, UnicodeError):
                self.config = {}
        else:
            self.config = {}

        # Merge with defaults to ensure all required keys exist
        self._ensure_defaults()
    
    def _set_defaults(self):
        """Set default configuration values"""
        self.config = {
            "ffmpeg_path": "",
            "ffprobe_path": "",
            "handbrake_path": "",
            "mkvinfo_path": "",
            "mediainfo_path": "",
            "output_destination": "input_folder",
            "default_output_folder": "",
            "default_output_suffix": "_encoded",
            "strip_leading_path_segments": 0,
            "encoding_mode": "sequential",
            "last_scan_folder": "",
            "skip_existing": False,
            "debug_logging": False,
            "allow_japanese_audio_with_english_subs": False,
            "audio_language_tags": ["en", "eng"],
            "audio_name_patterns": ["English", "ENG"],
            "audio_exclude_patterns": ["Japanese", "JPN", "日本語"],
            "subtitle_language_tags": ["en", "eng"],
            "subtitle_name_patterns": [
                "Signs.*Songs",
                "Signs.*Song",
                "Signs$",
                "English Signs",
                "^Signs\\s*$",
                "\\[Signs\\]",
                "English\\[Signs\\]",
            ],
            "subtitle_exclude_patterns": ["Japanese", "JPN", "日本語"],
            "audio_normalize_enabled": False,
            "audio_normalize_loudnorm_I": -16.0,
            "audio_normalize_loudnorm_TP": -1.5,
            "audio_normalize_loudnorm_LRA": 11.0,
            # Subtitle handling configuration
            "subtitle_handling": {
                "pgs": "omit",                  # skip_file | omit | burn
                "embedded_text": "mux",         # mux | burn | omit (applies to subrip, webvtt, etc.)
                "embedded_ass": "external",     # external | mux | burn | omit
                "external_text": "keep",        # keep | mux | both | burn | ignore
                "external_ass": "keep",         # keep | mux | both | burn | ignore
                "subtitle_source_priority": ["external", "embedded"]  # Which source to prefer
            },
            # UI behavior for subtitle handling
            "show_strategy_preview": True,      # Show strategy column always, dialog only if warnings/skips
            "warn_on_ass_mux": True,            # Warn when ASS muxed to MP4
            "warn_on_burn": True,               # Warn when burn is chosen
            # Encoder quality presets
            "encoder_quality_preset": "balanced",  # "balanced" | "quality" | "compact"
            "external_subtitle_tag": "default",    # "default" | "forced"
            "quality_presets": {
                "balanced": {
                    "description": "Good quality, moderate file size",
                    "crf": 28,
                    "preset": "medium"
                },
                "quality": {
                    "description": "Highest quality, larger files",
                    "crf": 24,
                    "preset": "slow"
                },
                "compact": {
                    "description": "Smallest files, acceptable quality",
                    "crf": 32,
                    "preset": "faster"
                }
            },
            "stats_api_enabled": True,
            "stats_api_base_url": "https://ffmpeg-encode.com",
            # FFmpeg Settings tab + FFmpegTranslator (GOP, pix fmt, scale targets)
            "ffmpeg_encoding": {
                "gop": 120,
                "pix_fmt_mode": "auto",
                "pix_fmt": "yuv420p",
                "color_range": "tv",
                "scale_cap_w": 1920,
                "scale_cap_h": 1080,
                "target_w": 1920,
                "target_h": 1080,
            },
            # HandBrake Settings tab (CLI flags built from UI)
            "handbrake_encoding": {
                "encoder": "x264",
                "quality": 22,
                "encoder_preset": "medium",
                "encoder_profile": "auto",
                "encoder_level": "auto",
                "encoder_tune": "none",
                "width": 0,
                "height": 0,
                "max_width": 1920,
                "max_height": 1080,
                "crop_mode": "auto",
                "audio_encoder": "av_aac",
                "audio_bitrate": 160,
                "audio_mixdown": "stereo",
                "format": "av_mp4",
                "optimize": True,
                "markers": True,
                "deinterlace": "off",
                "detelecine": "off",
                "denoise": "off",
                "denoise_preset": "medium",
                "sharpen": "off",
                "sharpen_preset": "medium",
                "chromasmooth": "off",
                "grayscale": False,
                "framerate": "auto",
                "framerate_mode": "pfr",
            },
        }

    def _ensure_defaults(self):
        """Merge default configuration with loaded config to fill in missing keys"""
        defaults = {}
        self._set_defaults()
        defaults = self.config.copy()

        # Merge defaults into current config, preserving existing values
        for key, default_value in defaults.items():
            if key not in self.config:
                self.config[key] = default_value
            elif isinstance(default_value, dict) and isinstance(self.config.get(key), dict):
                # For nested dicts, merge recursively
                for nested_key, nested_default in default_value.items():
                    if nested_key not in self.config[key]:
                        self.config[key][nested_key] = nested_default

    def _write_config_file_locked(self) -> None:
        """Persist config; caller must hold _save_lock."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except OSError as e:
            print(f"Error saving config: {e}")

    def _schedule_save(self) -> None:
        with self._save_lock:
            self._dirty = True
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None

            def run_save() -> None:
                with self._save_lock:
                    self._save_timer = None
                    if not self._dirty:
                        return
                    self._dirty = False
                    self._write_config_file_locked()

            timer = threading.Timer(CONFIG_SAVE_DEBOUNCE_SEC, run_save)
            self._save_timer = timer
            timer.daemon = True
            timer.start()

    def flush(self) -> None:
        """Write pending changes immediately (e.g. before app exit)."""
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None
            if not self._dirty:
                return
            self._dirty = False
            self._write_config_file_locked()

    def reload(self) -> None:
        """Reload config.json from disk; cancel pending debounced save."""
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None
            self._dirty = False
            self._load()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a configuration value; persists after a short debounce or on flush()."""
        self.config[key] = value
        self._schedule_save()
    
    def get_ffmpeg_path(self) -> str:
        """Get FFmpeg executable path"""
        return self.get("ffmpeg_path", "")
    
    def set_ffmpeg_path(self, path: str):
        """Set FFmpeg executable path"""
        self.set("ffmpeg_path", path)

    def get_ffprobe_path(self) -> str:
        """Get ffprobe executable path"""
        return self.get("ffprobe_path", "")

    def set_ffprobe_path(self, path: str):
        """Set ffprobe executable path"""
        self.set("ffprobe_path", path)
    
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

    def get_mediainfo_path(self) -> str:
        """Get MediaInfo executable path"""
        return self.get("mediainfo_path", "")

    def set_mediainfo_path(self, path: str):
        """Set MediaInfo executable path"""
        self.set("mediainfo_path", path)

    def get_output_destination(self) -> str:
        """Get output destination: 'input_folder' or 'custom_folder'"""
        if "output_destination" in self.config:
            return self.get("output_destination", "input_folder")
        folder = self.get("default_output_folder", "")
        if folder and Path(folder).exists():
            return "custom_folder"
        return "input_folder"

    def set_output_destination(self, destination: str):
        """Set output destination: 'input_folder' or 'custom_folder'"""
        self.set("output_destination", destination)

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

    def get_strip_leading_path_segments(self) -> int:
        """Get number of leading path segments to strip when preserving folder structure"""
        value = self.get("strip_leading_path_segments", 0)
        try:
            n = int(value)
            return max(0, min(99, n))
        except (TypeError, ValueError):
            return 0

    def set_strip_leading_path_segments(self, value: int):
        """Set number of leading path segments to strip (0-99)"""
        n = max(0, min(99, int(value)))
        self.set("strip_leading_path_segments", n)
    
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

    def get_debug_logging(self) -> bool:
        """Get whether debug log level is shown in the app log viewer"""
        return self.get("debug_logging", False)

    def set_debug_logging(self, value: bool):
        """Set whether debug log level is shown in the app log viewer"""
        self.set("debug_logging", value)

    def get_allow_japanese_audio_with_english_subs(self) -> bool:
        """When True, encode with first audio track + English subs when no English audio is found"""
        return self.get("allow_japanese_audio_with_english_subs", False)

    def set_allow_japanese_audio_with_english_subs(self, value: bool):
        """Set allow Japanese audio with English subs"""
        self.set("allow_japanese_audio_with_english_subs", value)

    def get_audio_normalize_enabled(self) -> bool:
        """When True, FFmpeg commands from the preset translator include single-pass loudnorm on audio."""
        return bool(self.get("audio_normalize_enabled", False))

    def set_audio_normalize_enabled(self, value: bool):
        """Enable or disable integrated loudnorm on FFmpeg-tab preset commands."""
        self.set("audio_normalize_enabled", bool(value))

    def get_audio_normalize_loudnorm_I(self) -> float:
        """Target integrated loudness (LUFS) for loudnorm (typical streaming ~ -16)."""
        return self._clamp_float(
            self.get("audio_normalize_loudnorm_I", -16.0),
            -70.0,
            -5.0,
            -16.0,
        )

    def set_audio_normalize_loudnorm_I(self, value: float):
        self.set(
            "audio_normalize_loudnorm_I",
            self._clamp_float(value, -70.0, -5.0, -16.0),
        )

    def get_audio_normalize_loudnorm_TP(self) -> float:
        """Maximum true peak (dBTP) for loudnorm."""
        return self._clamp_float(
            self.get("audio_normalize_loudnorm_TP", -1.5),
            -9.0,
            0.0,
            -1.5,
        )

    def set_audio_normalize_loudnorm_TP(self, value: float):
        self.set(
            "audio_normalize_loudnorm_TP",
            self._clamp_float(value, -9.0, 0.0, -1.5),
        )

    def get_audio_normalize_loudnorm_LRA(self) -> float:
        """Target loudness range for loudnorm."""
        return self._clamp_float(
            self.get("audio_normalize_loudnorm_LRA", 11.0),
            1.0,
            20.0,
            11.0,
        )

    def set_audio_normalize_loudnorm_LRA(self, value: float):
        self.set(
            "audio_normalize_loudnorm_LRA",
            self._clamp_float(value, 1.0, 20.0, 11.0),
        )

    @staticmethod
    def _clamp_float(raw: Any, lo: float, hi: float, fallback: float) -> float:
        try:
            x = float(raw)
        except (TypeError, ValueError):
            return fallback
        return max(lo, min(hi, x))

    @staticmethod
    def _sanitize_regex_patterns(patterns: list) -> list:
        """Validate each pattern string compiles as a regex.

        Invalid patterns are logged and silently dropped so that one bad entry
        cannot crash track analysis or silently match nothing at runtime.
        """
        valid: list = []
        for p in patterns:
            if not isinstance(p, str):
                continue
            try:
                re.compile(p)
                valid.append(p)
            except re.error as exc:
                print(f"Config: invalid regex pattern {p!r} dropped: {exc}")
        return valid

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
        self.set("audio_name_patterns", self._sanitize_regex_patterns(patterns))

    def get_audio_exclude_patterns(self) -> list:
        """Get audio exclude patterns"""
        return self.get("audio_exclude_patterns", ["Japanese", "JPN", "日本語"])

    def set_audio_exclude_patterns(self, patterns: list):
        """Set audio exclude patterns"""
        self.set("audio_exclude_patterns", self._sanitize_regex_patterns(patterns))
    
    def get_subtitle_language_tags(self) -> list:
        """Get subtitle language tags to match"""
        return self.get("subtitle_language_tags", ["en", "eng"])
    
    def set_subtitle_language_tags(self, tags: list):
        """Set subtitle language tags to match"""
        self.set("subtitle_language_tags", tags)
    
    def get_subtitle_name_patterns(self) -> list:
        """Get subtitle name patterns to match"""
        return self.get(
            "subtitle_name_patterns",
            [
                "Signs.*Songs",
                "Signs.*Song",
                "Signs$",
                "English Signs",
                "^Signs\\s*$",
                "\\[Signs\\]",
                "English\\[Signs\\]",
            ],
        )
    
    def set_subtitle_name_patterns(self, patterns: list):
        """Set subtitle name patterns to match"""
        self.set("subtitle_name_patterns", self._sanitize_regex_patterns(patterns))

    def get_subtitle_exclude_patterns(self) -> list:
        """Get subtitle exclude patterns"""
        return self.get("subtitle_exclude_patterns", ["Japanese", "JPN", "日本語"])

    def set_subtitle_exclude_patterns(self, patterns: list):
        """Set subtitle exclude patterns"""
        self.set("subtitle_exclude_patterns", self._sanitize_regex_patterns(patterns))
    
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

        # If preset with this name already exists, re-validate the stored path
        # before reusing it.  A hand-edited config.json could point the stored
        # path outside the presets directory; _safe_preset_path() catches that.
        if name in presets:
            validated = self._safe_preset_path(presets[name])
            if validated is None:
                # Stored path is invalid / escaped the presets dir — treat as new.
                del presets[name]
                dest_path = None
            else:
                dest_path = validated
        else:
            dest_path = None

        if dest_path is None:
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
    
    def _safe_preset_path(self, path_str: str) -> Optional[Path]:
        """Resolve path_str and confirm it sits inside the presets directory.

        Returns the resolved Path on success, None if the path escapes the
        presets directory (guards against path-traversal via a tampered config).
        """
        presets_dir = (self.config_dir / "presets").resolve()
        try:
            path = Path(path_str).resolve()
        except (TypeError, ValueError):
            return None
        if not path.is_relative_to(presets_dir):
            return None
        return path

    def get_preset_path(self, name: str) -> Optional[Path]:
        """Get the saved path for a preset by name"""
        presets = self.get_saved_presets()
        path_str = presets.get(name)
        if path_str:
            path = self._safe_preset_path(path_str)
            if path and path.exists():
                return path
        return None

    def delete_preset(self, name: str):
        """Delete a saved preset"""
        presets = self.get_saved_presets()
        if name in presets:
            path_str = presets[name]
            path = self._safe_preset_path(path_str)
            # Delete the file if it exists and is within the presets directory
            if path and path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass
            # Remove from config regardless of whether the file existed
            del presets[name]
            self.set_saved_presets(presets)
    
    def get_last_used_preset(self) -> Optional[str]:
        """Get the last used preset name"""
        return self.get("last_used_preset")
    
    def set_last_used_preset(self, name: str):
        """Set the last used preset name"""
        self.set("last_used_preset", name)

    def get_subtitle_handling(self) -> dict:
        """Get subtitle handling configuration"""
        return self.get("subtitle_handling", {
            "pgs": "omit",
            "embedded_text": "mux",
            "embedded_ass": "external",
            "external_text": "keep",
            "external_ass": "keep",
            "subtitle_source_priority": ["external", "embedded"]
        })

    def set_subtitle_handling(self, config_dict: dict):
        """Set subtitle handling configuration"""
        self.set("subtitle_handling", config_dict)

    def get_subtitle_pgs_action(self) -> str:
        """Get PGS subtitle handling action"""
        return self.get_subtitle_handling().get("pgs", "omit")

    def set_subtitle_pgs_action(self, action: str):
        """Set PGS subtitle handling action"""
        config_dict = self.get_subtitle_handling()
        config_dict["pgs"] = action
        self.set_subtitle_handling(config_dict)

    def get_subtitle_embedded_text_action(self) -> str:
        """Get embedded text subtitle handling action"""
        return self.get_subtitle_handling().get("embedded_text", "mux")

    def set_subtitle_embedded_text_action(self, action: str):
        """Set embedded text subtitle handling action"""
        config_dict = self.get_subtitle_handling()
        config_dict["embedded_text"] = action
        self.set_subtitle_handling(config_dict)

    def get_subtitle_embedded_ass_action(self) -> str:
        """Get embedded ASS subtitle handling action"""
        return self.get_subtitle_handling().get("embedded_ass", "external")

    def set_subtitle_embedded_ass_action(self, action: str):
        """Set embedded ASS subtitle handling action"""
        config_dict = self.get_subtitle_handling()
        config_dict["embedded_ass"] = action
        self.set_subtitle_handling(config_dict)

    def get_subtitle_external_text_action(self) -> str:
        """Get external text subtitle handling action"""
        return self.get_subtitle_handling().get("external_text", "keep")

    def set_subtitle_external_text_action(self, action: str):
        """Set external text subtitle handling action"""
        config_dict = self.get_subtitle_handling()
        config_dict["external_text"] = action
        self.set_subtitle_handling(config_dict)

    def get_subtitle_external_ass_action(self) -> str:
        """Get external ASS subtitle handling action"""
        return self.get_subtitle_handling().get("external_ass", "keep")

    def set_subtitle_external_ass_action(self, action: str):
        """Set external ASS subtitle handling action"""
        config_dict = self.get_subtitle_handling()
        config_dict["external_ass"] = action
        self.set_subtitle_handling(config_dict)

    def get_warn_on_ass_mux(self) -> bool:
        """Get warn on ASS muxing setting"""
        return self.get("warn_on_ass_mux", True)

    def set_warn_on_ass_mux(self, value: bool):
        """Set warn on ASS muxing setting"""
        self.set("warn_on_ass_mux", value)

    def get_warn_on_burn(self) -> bool:
        """Get warn on burn setting"""
        return self.get("warn_on_burn", True)

    def set_warn_on_burn(self, value: bool):
        """Set warn on burn setting"""
        self.set("warn_on_burn", value)

    def get_external_subtitle_tag(self) -> str:
        """Get external subtitle tag ('default' or 'forced')"""
        return self.get("external_subtitle_tag", "default")

    def set_external_subtitle_tag(self, value: str):
        """Set external subtitle tag ('default' or 'forced')"""
        self.set("external_subtitle_tag", value)

    def get_encoder_quality_preset(self) -> str:
        """Get the encoder quality preset ('balanced', 'quality', or 'compact')"""
        return self.get("encoder_quality_preset", "balanced")

    def set_encoder_quality_preset(self, value: str):
        """Set the encoder quality preset"""
        if value in ("balanced", "quality", "compact"):
            self.set("encoder_quality_preset", value)

    def get_quality_preset_config(self, preset_name: str) -> dict:
        """Get configuration for a quality preset"""
        presets = self.get("quality_presets", {})
        return presets.get(preset_name, presets.get("balanced", {}))

    def get_quality_preset_crf(self, preset_name: str = None) -> int:
        """Get CRF value for the current or specified preset"""
        if preset_name is None:
            preset_name = self.get_encoder_quality_preset()
        config = self.get_quality_preset_config(preset_name)
        return config.get("crf", 28)

    def get_quality_preset_speed(self, preset_name: str = None) -> str:
        """Get speed preset for the current or specified quality preset"""
        if preset_name is None:
            preset_name = self.get_encoder_quality_preset()
        config = self.get_quality_preset_config(preset_name)
        return config.get("preset", "medium")

    def get_stats_api_enabled(self) -> bool:
        return bool(self.config.get("stats_api_enabled", True))

    def set_stats_api_enabled(self, value: bool) -> None:
        self.config["stats_api_enabled"] = bool(value)
        self._schedule_save()

    def get_stats_api_base_url(self) -> str:
        return str(self.config.get("stats_api_base_url") or "https://ffmpeg-encode.com").strip()

    def set_stats_api_base_url(self, url: str) -> None:
        self.config["stats_api_base_url"] = (url or "").strip()
        self._schedule_save()

    def _ffmpeg_encoding_raw(self) -> Dict[str, Any]:
        raw = self.config.get("ffmpeg_encoding")
        return raw if isinstance(raw, dict) else {}

    def _ffmpeg_encoding_set_key(self, key: str, value: Any) -> None:
        fe = dict(self._ffmpeg_encoding_raw())
        fe[key] = value
        self.config["ffmpeg_encoding"] = fe
        self._schedule_save()

    def get_ffmpeg_gop(self) -> int:
        v = self._ffmpeg_encoding_raw().get("gop", 120)
        try:
            n = int(v)
        except (TypeError, ValueError):
            n = 120
        return max(12, min(600, n))

    def set_ffmpeg_gop(self, value: int) -> None:
        self._ffmpeg_encoding_set_key("gop", max(12, min(600, int(value))))

    def get_ffmpeg_pix_fmt_mode(self) -> str:
        m = self._ffmpeg_encoding_raw().get("pix_fmt_mode", "auto")
        return m if m in ("auto", "manual") else "auto"

    def set_ffmpeg_pix_fmt_mode(self, value: str) -> None:
        self._ffmpeg_encoding_set_key("pix_fmt_mode", value if value in ("auto", "manual") else "auto")

    def get_ffmpeg_pix_fmt(self) -> str:
        p = self._ffmpeg_encoding_raw().get("pix_fmt", "yuv420p")
        s = str(p).strip() if p else "yuv420p"
        return s if s in ALLOWED_MANUAL_PIX_FMT else "yuv420p"

    def set_ffmpeg_pix_fmt(self, value: str) -> None:
        s = str(value or "yuv420p").strip()
        self._ffmpeg_encoding_set_key("pix_fmt", s if s in ALLOWED_MANUAL_PIX_FMT else "yuv420p")

    def get_ffmpeg_color_range(self) -> str:
        c = self._ffmpeg_encoding_raw().get("color_range", "tv")
        return c if c in ("tv", "pc") else "tv"

    def set_ffmpeg_color_range(self, value: str) -> None:
        self._ffmpeg_encoding_set_key("color_range", value if value in ("tv", "pc") else "tv")

    def get_ffmpeg_scale_cap_w(self) -> int:
        return self._clamp_ffmpeg_dim(self._ffmpeg_encoding_raw().get("scale_cap_w", 1920))

    def get_ffmpeg_scale_cap_h(self) -> int:
        return self._clamp_ffmpeg_dim(self._ffmpeg_encoding_raw().get("scale_cap_h", 1080))

    def set_ffmpeg_scale_cap_w(self, value: int) -> None:
        self._ffmpeg_encoding_set_key("scale_cap_w", self._clamp_ffmpeg_dim(value))

    def set_ffmpeg_scale_cap_h(self, value: int) -> None:
        self._ffmpeg_encoding_set_key("scale_cap_h", self._clamp_ffmpeg_dim(value))

    def get_ffmpeg_target_w(self) -> int:
        return self._clamp_ffmpeg_dim(self._ffmpeg_encoding_raw().get("target_w", 1920))

    def get_ffmpeg_target_h(self) -> int:
        return self._clamp_ffmpeg_dim(self._ffmpeg_encoding_raw().get("target_h", 1080))

    def set_ffmpeg_target_w(self, value: int) -> None:
        self._ffmpeg_encoding_set_key("target_w", self._clamp_ffmpeg_dim(value))

    def set_ffmpeg_target_h(self, value: int) -> None:
        self._ffmpeg_encoding_set_key("target_h", self._clamp_ffmpeg_dim(value))

    # ------------------------------------------------------------------
    # HandBrake encoding settings
    # ------------------------------------------------------------------

    def _hb_encoding_raw(self) -> Dict[str, Any]:
        raw = self.config.get("handbrake_encoding")
        return raw if isinstance(raw, dict) else {}

    def _hb_encoding_set_key(self, key: str, value: Any) -> None:
        he = dict(self._hb_encoding_raw())
        he[key] = value
        self.config["handbrake_encoding"] = he
        self._schedule_save()

    def get_hb_encoding_settings(self) -> Dict[str, Any]:
        """Return the full handbrake_encoding dict (with defaults filled in)."""
        return dict(self._hb_encoding_raw())

    def get_hb_encoder(self) -> str:
        _ALLOWED = {"x264", "x265", "nvenc_h264", "nvenc_h265", "vt_h264", "vt_h265"}
        v = self._hb_encoding_raw().get("encoder", "x264")
        return v if v in _ALLOWED else "x264"

    def set_hb_encoder(self, value: str) -> None:
        self._hb_encoding_set_key("encoder", value)

    def get_hb_quality(self) -> int:
        v = self._hb_encoding_raw().get("quality", 22)
        try:
            n = int(v)
        except (TypeError, ValueError):
            n = 22
        return max(0, min(51, n))

    def set_hb_quality(self, value: int) -> None:
        self._hb_encoding_set_key("quality", max(0, min(51, int(value))))

    def get_hb_encoder_preset(self) -> str:
        _ALLOWED = {
            "ultrafast", "superfast", "veryfast", "faster", "fast",
            "medium", "slow", "slower", "veryslow", "placebo",
            "speed", "quality",
        }
        v = self._hb_encoding_raw().get("encoder_preset", "medium")
        return v if v in _ALLOWED else "medium"

    def set_hb_encoder_preset(self, value: str) -> None:
        self._hb_encoding_set_key("encoder_preset", value)

    def get_hb_encoder_profile(self) -> str:
        _ALLOWED = {"auto", "baseline", "main", "main10", "high", "high10", "high422", "high444"}
        v = self._hb_encoding_raw().get("encoder_profile", "auto")
        return v if v in _ALLOWED else "auto"

    def set_hb_encoder_profile(self, value: str) -> None:
        self._hb_encoding_set_key("encoder_profile", value)

    def get_hb_encoder_level(self) -> str:
        _ALLOWED = {
            "auto", "3.0", "3.1", "3.2", "4.0", "4.1", "4.2",
            "5.0", "5.1", "5.2", "6.0", "6.1", "6.2",
        }
        v = self._hb_encoding_raw().get("encoder_level", "auto")
        return v if v in _ALLOWED else "auto"

    def set_hb_encoder_level(self, value: str) -> None:
        self._hb_encoding_set_key("encoder_level", value)

    def get_hb_encoder_tune(self) -> str:
        _ALLOWED = {
            "none", "film", "animation", "grain", "stillimage",
            "psnr", "ssim", "fastdecode", "zerolatency",
        }
        v = self._hb_encoding_raw().get("encoder_tune", "none")
        return v if v in _ALLOWED else "none"

    def set_hb_encoder_tune(self, value: str) -> None:
        self._hb_encoding_set_key("encoder_tune", value)

    def get_hb_width(self) -> int:
        v = self._hb_encoding_raw().get("width", 0)
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 0
        return max(0, min(7680, n))

    def set_hb_width(self, value: int) -> None:
        self._hb_encoding_set_key("width", max(0, min(7680, int(value))))

    def get_hb_height(self) -> int:
        v = self._hb_encoding_raw().get("height", 0)
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 0
        return max(0, min(7680, n))

    def set_hb_height(self, value: int) -> None:
        self._hb_encoding_set_key("height", max(0, min(7680, int(value))))

    def get_hb_max_width(self) -> int:
        return self._clamp_ffmpeg_dim(self._hb_encoding_raw().get("max_width", 1920))

    def set_hb_max_width(self, value: int) -> None:
        self._hb_encoding_set_key("max_width", self._clamp_ffmpeg_dim(value))

    def get_hb_max_height(self) -> int:
        return self._clamp_ffmpeg_dim(self._hb_encoding_raw().get("max_height", 1080))

    def set_hb_max_height(self, value: int) -> None:
        self._hb_encoding_set_key("max_height", self._clamp_ffmpeg_dim(value))

    def get_hb_crop_mode(self) -> str:
        _ALLOWED = {"auto", "disabled", "custom"}
        v = self._hb_encoding_raw().get("crop_mode", "auto")
        return v if v in _ALLOWED else "auto"

    def set_hb_crop_mode(self, value: str) -> None:
        self._hb_encoding_set_key("crop_mode", value)

    def get_hb_audio_encoder(self) -> str:
        _ALLOWED = {"av_aac", "copy", "ac3", "eac3", "opus", "flac", "mp3"}
        v = self._hb_encoding_raw().get("audio_encoder", "av_aac")
        return v if v in _ALLOWED else "av_aac"

    def set_hb_audio_encoder(self, value: str) -> None:
        self._hb_encoding_set_key("audio_encoder", value)

    def get_hb_audio_bitrate(self) -> int:
        v = self._hb_encoding_raw().get("audio_bitrate", 160)
        try:
            n = int(v)
        except (TypeError, ValueError):
            n = 160
        return max(32, min(640, n))

    def set_hb_audio_bitrate(self, value: int) -> None:
        self._hb_encoding_set_key("audio_bitrate", max(32, min(640, int(value))))

    def get_hb_audio_mixdown(self) -> str:
        _ALLOWED = {"mono", "stereo", "5point1", "6point1", "7point1"}
        v = self._hb_encoding_raw().get("audio_mixdown", "stereo")
        return v if v in _ALLOWED else "stereo"

    def set_hb_audio_mixdown(self, value: str) -> None:
        self._hb_encoding_set_key("audio_mixdown", value)

    def get_hb_format(self) -> str:
        _ALLOWED = {"av_mp4", "av_mkv", "av_webm"}
        v = self._hb_encoding_raw().get("format", "av_mp4")
        return v if v in _ALLOWED else "av_mp4"

    def set_hb_format(self, value: str) -> None:
        self._hb_encoding_set_key("format", value)

    def get_hb_optimize(self) -> bool:
        return bool(self._hb_encoding_raw().get("optimize", True))

    def set_hb_optimize(self, value: bool) -> None:
        self._hb_encoding_set_key("optimize", bool(value))

    def get_hb_markers(self) -> bool:
        return bool(self._hb_encoding_raw().get("markers", True))

    def set_hb_markers(self, value: bool) -> None:
        self._hb_encoding_set_key("markers", bool(value))

    def get_hb_deinterlace(self) -> str:
        _ALLOWED = {"off", "default", "skip-spatial", "bob"}
        v = self._hb_encoding_raw().get("deinterlace", "off")
        return v if v in _ALLOWED else "off"

    def set_hb_deinterlace(self, value: str) -> None:
        self._hb_encoding_set_key("deinterlace", value)

    def get_hb_detelecine(self) -> str:
        _ALLOWED = {"off", "default"}
        v = self._hb_encoding_raw().get("detelecine", "off")
        return v if v in _ALLOWED else "off"

    def set_hb_detelecine(self, value: str) -> None:
        self._hb_encoding_set_key("detelecine", value)

    def get_hb_denoise(self) -> str:
        _ALLOWED = {"off", "nlmeans", "hqdn3d"}
        v = self._hb_encoding_raw().get("denoise", "off")
        return v if v in _ALLOWED else "off"

    def set_hb_denoise(self, value: str) -> None:
        self._hb_encoding_set_key("denoise", value)

    def get_hb_denoise_preset(self) -> str:
        _ALLOWED = {"ultralight", "light", "medium", "strong"}
        v = self._hb_encoding_raw().get("denoise_preset", "medium")
        return v if v in _ALLOWED else "medium"

    def set_hb_denoise_preset(self, value: str) -> None:
        self._hb_encoding_set_key("denoise_preset", value)

    def get_hb_sharpen(self) -> str:
        _ALLOWED = {"off", "unsharp", "lapsharp"}
        v = self._hb_encoding_raw().get("sharpen", "off")
        return v if v in _ALLOWED else "off"

    def set_hb_sharpen(self, value: str) -> None:
        self._hb_encoding_set_key("sharpen", value)

    def get_hb_sharpen_preset(self) -> str:
        _ALLOWED = {"ultralight", "light", "medium", "strong"}
        v = self._hb_encoding_raw().get("sharpen_preset", "medium")
        return v if v in _ALLOWED else "medium"

    def set_hb_sharpen_preset(self, value: str) -> None:
        self._hb_encoding_set_key("sharpen_preset", value)

    def get_hb_chromasmooth(self) -> str:
        _ALLOWED = {"off", "ultralight", "light", "medium", "strong", "stronger", "verystrong"}
        v = self._hb_encoding_raw().get("chromasmooth", "off")
        return v if v in _ALLOWED else "off"

    def set_hb_chromasmooth(self, value: str) -> None:
        self._hb_encoding_set_key("chromasmooth", value)

    def get_hb_grayscale(self) -> bool:
        return bool(self._hb_encoding_raw().get("grayscale", False))

    def set_hb_grayscale(self, value: bool) -> None:
        self._hb_encoding_set_key("grayscale", bool(value))

    def get_hb_framerate(self) -> str:
        _ALLOWED = {"auto", "5", "10", "12", "15", "23.976", "24", "25", "29.97", "30", "48", "50", "59.94", "60"}
        v = str(self._hb_encoding_raw().get("framerate", "auto"))
        return v if v in _ALLOWED else "auto"

    def set_hb_framerate(self, value: str) -> None:
        self._hb_encoding_set_key("framerate", value)

    def get_hb_framerate_mode(self) -> str:
        _ALLOWED = {"cfr", "vfr", "pfr"}
        v = self._hb_encoding_raw().get("framerate_mode", "pfr")
        return v if v in _ALLOWED else "pfr"

    def set_hb_framerate_mode(self, value: str) -> None:
        self._hb_encoding_set_key("framerate_mode", value)

    @staticmethod
    def _clamp_ffmpeg_dim(raw: Any) -> int:
        try:
            n = int(raw)
        except (TypeError, ValueError):
            n = 1920
        return max(16, min(7680, n))


# Global config instance
config = Config()

