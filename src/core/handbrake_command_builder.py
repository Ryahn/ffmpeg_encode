"""Build HandBrakeCLI command lines from UI settings (no preset file required)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


# Allowlists for string parameters — prevent injection via crafted config values.
_ENCODERS = {"x264", "x265", "nvenc_h264", "nvenc_h265", "vt_h264", "vt_h265"}
_PRESETS = {
    "ultrafast", "superfast", "veryfast", "faster", "fast",
    "medium", "slow", "slower", "veryslow", "placebo",
    "speed", "quality",
}
_PROFILES = {"auto", "baseline", "main", "main10", "high", "high10", "high422", "high444"}
_LEVELS = {
    "auto", "3.0", "3.1", "3.2", "4.0", "4.1", "4.2",
    "5.0", "5.1", "5.2", "6.0", "6.1", "6.2",
}
_TUNES = {
    "none", "film", "animation", "grain", "stillimage",
    "psnr", "ssim", "fastdecode", "zerolatency",
}
_AUDIO_ENCODERS = {"av_aac", "copy", "ac3", "eac3", "opus", "flac", "mp3"}
_MIXDOWNS = {"mono", "stereo", "5point1", "6point1", "7point1"}
_FORMATS = {"av_mp4", "av_mkv", "av_webm"}
_CROP_MODES = {"auto", "disabled", "custom"}
_DEINTERLACE = {"off", "default", "skip-spatial", "bob"}
_DETELECINE = {"off", "default"}
_DENOISE = {"off", "nlmeans", "hqdn3d"}
_DENOISE_PRESETS = {"ultralight", "light", "medium", "strong"}
_SHARPEN = {"off", "unsharp", "lapsharp"}
_SHARPEN_PRESETS = {"ultralight", "light", "medium", "strong"}
_CHROMASMOOTH = {"off", "ultralight", "light", "medium", "strong", "stronger", "verystrong"}
_FRAMERATES = {"auto", "5", "10", "12", "15", "23.976", "24", "25", "29.97", "30", "48", "50", "59.94", "60"}
_FRAMERATE_MODES = {"cfr", "vfr", "pfr"}


def _safe_str(value: Any, default: str, allowed: set) -> str:
    if not isinstance(value, str):
        return default
    value = value.strip()
    return value if value in allowed else default


def _safe_int(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


class HandBrakeCommandBuilder:
    """Builds HandBrakeCLI commands from a settings dictionary."""

    def build_template(self, settings: Dict[str, Any], include_subtitle: bool = False) -> str:
        """Build a command string with {INPUT}, {OUTPUT}, {AUDIO_TRACK}, {SUBTITLE_TRACK} placeholders.

        This is used for the command preview in the UI.
        """
        parts = self._build_parts(settings, include_subtitle=include_subtitle)

        # Replace actual input/output with placeholders
        parts.extend(["--input", "{INPUT}"])
        parts.extend(["--output", "{OUTPUT}"])

        return " ".join(parts)

    def build_argv(
        self,
        input_file: Path,
        output_file: Path,
        settings: Dict[str, Any],
        audio_track: int,
        subtitle_track: Optional[int] = None,
        handbrake_path: str = "HandBrakeCLI",
    ) -> List[str]:
        """Build final argv with actual values for encoding execution."""
        include_subtitle = subtitle_track is not None
        parts = self._build_parts(settings, include_subtitle=include_subtitle)

        # Replace placeholders with actual values
        argv = [handbrake_path]
        for part in parts:
            if part == "{AUDIO_TRACK}":
                argv.append(str(audio_track))
            elif part == "{SUBTITLE_TRACK}":
                argv.append(str((subtitle_track or 0) + 1))
            else:
                argv.append(part)

        argv.extend(["--input", str(input_file)])
        argv.extend(["--output", str(output_file)])
        return argv

    def _build_parts(self, settings: Dict[str, Any], include_subtitle: bool = False) -> List[str]:
        """Build the core argument parts (without input/output and without executable)."""
        parts: List[str] = []

        # Video encoder
        encoder = _safe_str(settings.get("encoder"), "x264", _ENCODERS)
        parts.extend(["--encoder", encoder])

        # Quality (RF/CRF)
        quality = _safe_int(settings.get("quality"), 22, 0, 51)
        parts.extend(["--quality", str(quality)])

        # Encoder preset (speed)
        preset = _safe_str(settings.get("encoder_preset"), "medium", _PRESETS)
        parts.extend(["--encoder-preset", preset])

        # Encoder profile
        profile = _safe_str(settings.get("encoder_profile"), "auto", _PROFILES)
        if profile != "auto":
            parts.extend(["--encoder-profile", profile])

        # Encoder level
        level = _safe_str(settings.get("encoder_level"), "auto", _LEVELS)
        if level != "auto":
            parts.extend(["--encoder-level", level])

        # Encoder tune
        tune = _safe_str(settings.get("encoder_tune"), "none", _TUNES)
        if tune != "none":
            parts.extend(["--encoder-tune", tune])

        # Resolution
        width = _safe_int(settings.get("width"), 0, 0, 7680)
        height = _safe_int(settings.get("height"), 0, 0, 7680)
        max_width = _safe_int(settings.get("max_width"), 1920, 16, 7680)
        max_height = _safe_int(settings.get("max_height"), 1080, 16, 7680)

        if width > 0:
            parts.extend(["--width", str(width)])
        if height > 0:
            parts.extend(["--height", str(height)])
        parts.extend(["--maxWidth", str(max_width)])
        parts.extend(["--maxHeight", str(max_height)])

        # Crop
        crop_mode = _safe_str(settings.get("crop_mode"), "auto", _CROP_MODES)
        if crop_mode == "disabled":
            parts.extend(["--crop", "0:0:0:0"])

        # Audio
        audio_encoder = _safe_str(settings.get("audio_encoder"), "av_aac", _AUDIO_ENCODERS)
        parts.extend(["--aencoder", audio_encoder])

        if audio_encoder != "copy":
            audio_bitrate = _safe_int(settings.get("audio_bitrate"), 160, 32, 640)
            parts.extend(["--ab", str(audio_bitrate)])

            mixdown = _safe_str(settings.get("audio_mixdown"), "stereo", _MIXDOWNS)
            parts.extend(["--mixdown", mixdown])

        # Audio track placeholder
        parts.extend(["--audio", "{AUDIO_TRACK}"])

        # Container format
        fmt = _safe_str(settings.get("format"), "av_mp4", _FORMATS)
        parts.extend(["--format", fmt])

        # Web optimize
        if settings.get("optimize", True):
            parts.append("--optimize")

        # Chapter markers
        if settings.get("markers", True):
            parts.append("--markers")

        # Subtitle
        if include_subtitle:
            parts.extend(["--subtitle", "{SUBTITLE_TRACK}"])
            parts.append("--subtitle-burned")

        # --- Filters ---

        # Deinterlace
        deinterlace = _safe_str(settings.get("deinterlace"), "off", _DEINTERLACE)
        if deinterlace != "off":
            parts.append(f"--deinterlace={deinterlace}")

        # Detelecine
        detelecine = _safe_str(settings.get("detelecine"), "off", _DETELECINE)
        if detelecine != "off":
            parts.append("--detelecine")

        # Denoise
        denoise = _safe_str(settings.get("denoise"), "off", _DENOISE)
        if denoise != "off":
            denoise_preset = _safe_str(settings.get("denoise_preset"), "medium", _DENOISE_PRESETS)
            parts.append(f"--denoise={denoise}")
            parts.append(f"--denoise-preset={denoise_preset}")

        # Sharpen
        sharpen = _safe_str(settings.get("sharpen"), "off", _SHARPEN)
        if sharpen != "off":
            sharpen_preset = _safe_str(settings.get("sharpen_preset"), "medium", _SHARPEN_PRESETS)
            parts.append(f"--sharpen={sharpen}")
            parts.append(f"--sharpen-preset={sharpen_preset}")

        # Chromasmooth
        chromasmooth = _safe_str(settings.get("chromasmooth"), "off", _CHROMASMOOTH)
        if chromasmooth != "off":
            parts.append(f"--chromasmooth={chromasmooth}")

        # Grayscale
        if settings.get("grayscale", False):
            parts.append("--grayscale")

        # Framerate
        framerate = _safe_str(str(settings.get("framerate", "auto")), "auto", _FRAMERATES)
        framerate_mode = _safe_str(settings.get("framerate_mode", "pfr"), "pfr", _FRAMERATE_MODES)
        if framerate != "auto":
            parts.extend(["--rate", framerate])
        parts.append(f"--{framerate_mode}")

        return parts
