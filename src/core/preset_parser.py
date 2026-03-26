"""Parse HandBrake JSON preset files"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from utils.validation import safe_int, safe_str

# Hard limit: a valid HandBrake JSON preset is a few KB at most.
_MAX_PRESET_FILE_BYTES = 1 * 1024 * 1024  # 1 MB


class PresetParser:
    """Parses HandBrake JSON preset files"""

    def __init__(self, preset_path: Path):
        self.preset_path = preset_path
        self.preset_data: Optional[Dict[str, Any]] = None
        self.preset: Optional[Dict[str, Any]] = None
        self._load()

    def _load(self):
        """Load and parse the preset file"""
        try:
            # Reject absurdly large files before reading into memory.
            file_size = self.preset_path.stat().st_size
            if file_size > _MAX_PRESET_FILE_BYTES:
                raise ValueError(
                    f"Preset file is too large ({file_size:,} bytes; max {_MAX_PRESET_FILE_BYTES:,})"
                )

            with open(self.preset_path, 'r', encoding='utf-8') as f:
                self.preset_data = json.load(f)

            if "PresetList" in self.preset_data and len(self.preset_data["PresetList"]) > 0:
                self.preset = self.preset_data["PresetList"][0]
            else:
                raise ValueError("PresetList is empty or missing")
        except Exception as e:
            raise ValueError(f"Failed to load preset: {str(e)}")
    
    def get_preset_name(self) -> str:
        """Get the preset name"""
        return self.preset.get("PresetName", "Unknown") if self.preset else "Unknown"
    
    def get_preset_description(self) -> str:
        """Get the preset description"""
        return self.preset.get("PresetDescription", "") if self.preset else ""
    
    def get_video_encoder(self) -> str:
        """Get video encoder (e.g., 'x264')"""
        return self.preset.get("VideoEncoder", "x264") if self.preset else "x264"
    
    def get_video_quality(self) -> int:
        """Get video quality slider value (CRF).

        Valid H.264/H.265 CRF range is 0–51; values outside that range are
        clamped so a crafted preset cannot pass an unexpected string to FFmpeg.
        """
        raw = self.preset.get("VideoQualitySlider", 22) if self.preset else 22
        return safe_int(raw, default=22, lo=0, hi=51)

    def get_video_preset(self) -> str:
        """Get video preset (e.g., 'medium')"""
        _ALLOWED = {
            "ultrafast", "superfast", "veryfast", "faster", "fast",
            "medium", "slow", "slower", "veryslow", "placebo",
        }
        raw = self.preset.get("VideoPreset", "medium") if self.preset else "medium"
        return safe_str(raw, default="medium", allowed=_ALLOWED)

    def get_video_profile(self) -> str:
        """Get video profile (e.g., 'high')"""
        _ALLOWED = {"baseline", "main", "high", "high10", "high422", "high444", "main10"}
        raw = self.preset.get("VideoProfile", "high") if self.preset else "high"
        return safe_str(raw, default="high", allowed=_ALLOWED)

    def get_video_level(self) -> str:
        """Get video level (e.g., '4.0')"""
        _ALLOWED = {
            "3.0", "3.1", "3.2",
            "4.0", "4.1", "4.2",
            "5.0", "5.1", "5.2",
            "6.0", "6.1", "6.2",
        }
        raw = str(self.preset.get("VideoLevel", "4.0")) if self.preset else "4.0"
        return safe_str(raw, default="4.0", allowed=_ALLOWED)

    def get_video_resolution(self) -> tuple:
        """Get video resolution (width, height).

        Values are cast to int and clamped to [8, 7680] so that a non-integer
        preset value cannot be interpolated into the FFmpeg ``scale=`` filter
        string and inject additional filter options.
        """
        if not self.preset:
            return (1920, 1080)
        width = safe_int(self.preset.get("PictureWidth", 1920), default=1920, lo=8, hi=7680)
        height = safe_int(self.preset.get("PictureHeight", 1080), default=1080, lo=8, hi=7680)
        return (width, height)
    
    def get_video_framerate(self) -> Optional[str]:
        """Get video framerate"""
        return self.preset.get("VideoFramerate") if self.preset else None
    
    def get_video_framerate_mode(self) -> str:
        """Get video framerate mode"""
        return self.preset.get("VideoFramerateMode", "pfr") if self.preset else "pfr"
    
    def get_video_color_range(self) -> str:
        """Get video color range"""
        return self.preset.get("VideoColorRange", "limited") if self.preset else "limited"
    
    def get_audio_encoder(self) -> str:
        """Get audio encoder"""
        if not self.preset or not self.preset.get("AudioList"):
            return "av_aac"
        
        audio_list = self.preset.get("AudioList", [])
        if audio_list and len(audio_list) > 0:
            return audio_list[0].get("AudioEncoder", "av_aac")
        return "av_aac"
    
    def get_audio_bitrate(self) -> int:
        """Get audio bitrate in kbps, clamped to [32, 640]."""
        if not self.preset or not self.preset.get("AudioList"):
            return 160
        audio_list = self.preset.get("AudioList", [])
        if audio_list:
            raw = audio_list[0].get("AudioBitrate", 160)
            return safe_int(raw, default=160, lo=32, hi=640)
        return 160
    
    def get_audio_mixdown(self) -> str:
        """Get audio mixdown (e.g., 'stereo')"""
        if not self.preset or not self.preset.get("AudioList"):
            return "stereo"
        
        audio_list = self.preset.get("AudioList", [])
        if audio_list and len(audio_list) > 0:
            return audio_list[0].get("AudioMixdown", "stereo")
        return "stereo"
    
    def get_file_format(self) -> str:
        """Get output file format"""
        return self.preset.get("FileFormat", "av_mp4") if self.preset else "av_mp4"
    
    def get_chapter_markers(self) -> bool:
        """Get whether to include chapter markers"""
        return self.preset.get("ChapterMarkers", True) if self.preset else True
    
    def get_optimize(self) -> bool:
        """Get whether to optimize for web"""
        return self.preset.get("Optimize", False) if self.preset else False

