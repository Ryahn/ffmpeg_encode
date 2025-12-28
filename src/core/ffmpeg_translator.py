"""Translate HandBrake presets to FFmpeg commands"""

from pathlib import Path
from typing import Optional, List
from .preset_parser import PresetParser


class FFmpegTranslator:
    """Translates HandBrake presets to FFmpeg commands"""
    
    def __init__(self, preset_parser: PresetParser):
        self.preset = preset_parser
    
    def build_command(
        self,
        input_file: Path,
        output_file: Path,
        audio_track: int,
        subtitle_track: Optional[int] = None,
        subtitle_file: Optional[Path] = None
    ) -> List[str]:
        """Build FFmpeg command from preset"""
        cmd = ["ffmpeg", "-i", str(input_file)]
        
        # Map video stream
        cmd.extend(["-map", "0:v:0"])
        
        # Map audio stream (audio_track is 1-indexed mkvmerge track ID)
        # Convert to 0-indexed FFmpeg stream ID and use absolute stream mapping
        # This matches the PowerShell script behavior: -map 0:$AudioStreamID
        audio_stream_id = audio_track - 1
        cmd.extend(["-map", f"0:{audio_stream_id}"])
        
        # Video codec settings
        video_encoder = self.preset.get_video_encoder()
        if video_encoder == "x264":
            cmd.extend(["-c:v", "libx264"])
        else:
            cmd.extend(["-c:v", video_encoder])
        
        # Video quality (CRF)
        crf = self.preset.get_video_quality()
        cmd.extend(["-crf", str(crf)])
        
        # Video preset
        preset = self.preset.get_video_preset()
        cmd.extend(["-preset", preset])
        
        # Video profile and level
        profile = self.preset.get_video_profile()
        level = self.preset.get_video_level()
        cmd.extend(["-profile:v", profile])
        cmd.extend(["-level", level])
        
        # Resolution
        width, height = self.preset.get_video_resolution()
        video_filters = [f"scale={width}:{height}:force_original_aspect_ratio=decrease"]
        
        # Add subtitle filter if needed
        if subtitle_file:
            # Escape the subtitle file path for use in filter
            # Use forward slashes and escape colon for Windows paths
            sub_path = str(subtitle_file).replace("\\", "/").replace(":", "\\:")
            sub_path = sub_path.replace("'", "'\\''")
            video_filters.append(f"subtitles='{sub_path}'")
        elif subtitle_track:
            # Include subtitle filter with placeholder that will be replaced during encoding
            # Use {SUBTITLE_FILE} placeholder which will be replaced with actual extracted subtitle file
            video_filters.append("subtitles='{SUBTITLE_FILE}'")
        
        if video_filters:
            cmd.extend(["-vf", ",".join(video_filters)])
        
        # Color range
        color_range = self.preset.get_video_color_range()
        if color_range == "limited":
            cmd.extend(["-color_range", "tv"])
        else:
            cmd.extend(["-color_range", "pc"])
        
        # Pixel format
        cmd.extend(["-pix_fmt", "yuv420p"])
        
        # GOP size (for compatibility)
        cmd.extend(["-g", "60"])
        
        # Audio codec settings
        audio_encoder = self.preset.get_audio_encoder()
        if audio_encoder == "av_aac":
            cmd.extend(["-c:a", "aac"])
        else:
            cmd.extend(["-c:a", audio_encoder])
        
        # Audio bitrate
        audio_bitrate = self.preset.get_audio_bitrate()
        cmd.extend(["-b:a", f"{audio_bitrate}k"])
        
        # Audio mixdown (channels)
        mixdown = self.preset.get_audio_mixdown()
        if mixdown == "stereo":
            cmd.extend(["-ac", "2"])
        elif mixdown == "mono":
            cmd.extend(["-ac", "1"])
        elif mixdown == "5.1":
            cmd.extend(["-ac", "6"])
        
        # Copy chapters
        if self.preset.get_chapter_markers():
            cmd.extend(["-map_chapters", "0"])
        
        # Copy metadata
        cmd.extend(["-map_metadata", "0"])
        
        # Optimize for streaming (faststart)
        if self.preset.get_optimize():
            cmd.extend(["-movflags", "+faststart"])
        
        # Overwrite output
        cmd.append("-y")
        
        # Output file
        cmd.append(str(output_file))
        
        return cmd
    
    def get_command_string(
        self,
        input_file: Path,
        output_file: Path,
        audio_track: int,
        subtitle_track: Optional[int] = None,
        subtitle_file: Optional[Path] = None
    ) -> str:
        """Get FFmpeg command as a string"""
        cmd = self.build_command(input_file, output_file, audio_track, subtitle_track, subtitle_file)
        return " ".join(f'"{arg}"' if " " in arg else arg for arg in cmd)
    
    def get_command_breakdown(
        self,
        input_file: Path,
        output_file: Path,
        audio_track: int,
        subtitle_track: Optional[int] = None
    ) -> dict:
        """Get a breakdown of the FFmpeg command"""
        width, height = self.preset.get_video_resolution()
        
        return {
            "input": str(input_file),
            "output": str(output_file),
            "video": {
                "codec": "libx264" if self.preset.get_video_encoder() == "x264" else self.preset.get_video_encoder(),
                "crf": self.preset.get_video_quality(),
                "preset": self.preset.get_video_preset(),
                "profile": self.preset.get_video_profile(),
                "level": self.preset.get_video_level(),
                "resolution": f"{width}x{height}",
                "color_range": self.preset.get_video_color_range()
            },
            "audio": {
                "codec": "aac" if self.preset.get_audio_encoder() == "av_aac" else self.preset.get_audio_encoder(),
                "bitrate": f"{self.preset.get_audio_bitrate()}k",
                "mixdown": self.preset.get_audio_mixdown(),
                "track": audio_track
            },
            "subtitle": {
                "track": subtitle_track,
                "burned": subtitle_track is not None
            }
        }

