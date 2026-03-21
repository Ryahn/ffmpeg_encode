"""Batch audio loudness normalization (single audio stream per file)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

from core.audio_normalize import build_integrated_loudnorm_filter
from core.subprocess_utils import get_subprocess_kwargs

VIDEO_EXTENSIONS = frozenset(
    {
        ".mkv",
        ".mp4",
        ".mov",
        ".m4v",
        ".avi",
        ".flv",
        ".wmv",
        ".webm",
    }
)


def iter_media_files(root: Path, recursive: bool) -> List[Path]:
    """Return video files under ``root`` sorted by path."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        return []
    out: List[Path] = []
    if recursive:
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS:
                out.append(p)
    else:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS:
                out.append(p)
    out.sort(key=lambda x: str(x).lower())
    return out


def _ffprobe_streams(path: Path, ffprobe: str) -> Tuple[Optional[List[dict[str, Any]]], Optional[str]]:
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "stream=index,codec_type,codec_name",
        "-of",
        "json",
        str(path),
    ]
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            **get_subprocess_kwargs(),
        )
        if r.returncode != 0:
            return None, (r.stderr or "ffprobe failed").strip() or "ffprobe failed"
        data = json.loads(r.stdout)
        return data.get("streams") or [], None
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        return None, str(e)


def _audio_encoder_args(
    detected: str,
    fallback_codec: str,
    fallback_bitrate: int,
    container_suffix: str,
) -> List[str]:
    """Pick output audio encoder; MP4/M4V/MOV get AAC (or fallback) for mux compatibility."""
    br = max(32, int(fallback_bitrate))
    fc = (fallback_codec or "aac").strip().lower()
    ext = (container_suffix or "").lower()
    if ext in (".mp4", ".m4v", ".mov"):
        return ["-c:a", fc, "-b:a", f"{br}k"]
    c = (detected or "").lower().strip()
    if c in ("aac", "aac_latm"):
        return ["-c:a", "aac", "-b:a", f"{br}k"]
    if c == "mp3":
        return ["-c:a", "libmp3lame", "-b:a", f"{br}k"]
    if c == "opus":
        return ["-c:a", "libopus", "-b:a", f"{min(br, 256)}k"]
    if c == "flac":
        return ["-c:a", "flac"]
    if c in ("vorbis", "libvorbis"):
        return ["-c:a", "libvorbis", "-b:a", f"{br}k"]
    if c.startswith("pcm_"):
        return ["-c:a", "flac"]
    return ["-c:a", fc, "-b:a", f"{br}k"]


def build_loudnorm_ffmpeg_argv(
    input_path: Path,
    output_path: Path,
    ffprobe_exe: str,
    integrated_lufs: float,
    true_peak_db_tp: float,
    loudness_range: float,
    fallback_codec: str,
    fallback_bitrate: int,
) -> Tuple[Optional[List[str]], Optional[str]]:
    streams, err = _ffprobe_streams(input_path, ffprobe_exe)
    if err:
        return None, err
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    sub_streams = [s for s in streams if s.get("codec_type") == "subtitle"]

    if len(audio_streams) != 1:
        return None, (
            f"expected exactly 1 audio stream, found {len(audio_streams)} (skipping)"
        )

    detected = str(audio_streams[0].get("codec_name") or "")
    af = build_integrated_loudnorm_filter(
        integrated_lufs, true_peak_db_tp, loudness_range
    )
    a_enc = _audio_encoder_args(
        detected, fallback_codec, fallback_bitrate, input_path.suffix
    )

    # First token must be ``ffmpeg`` for ``Encoder.run_ffmpeg_argv`` substitution.
    args: List[str] = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-i",
        str(input_path),
    ]
    if video_streams:
        args += ["-map", "0:v:0", "-c:v", "copy"]
    args += ["-map", "0:a:0", "-af", af] + a_enc
    if sub_streams:
        args += ["-map", "0:s", "-c:s", "copy"]
    args += ["-map_chapters", "0", "-map_metadata", "0", "-y", str(output_path)]
    return args, None


def run_normalize_file(
    *,
    ffprobe_exe: str,
    input_path: Path,
    replace_original: bool,
    integrated_lufs: float,
    true_peak_db_tp: float,
    loudness_range: float,
    fallback_codec: str,
    fallback_bitrate: int,
    run_ffmpeg: Callable[[List[str], Path], bool],
) -> Tuple[bool, str]:
    """
    Normalize audio for one file. ``run_ffmpeg(argv, output_path)`` performs the encode.

    When ``replace_original`` is True, writes to a temp file next to the source then
    ``os.replace`` onto the original on success.
    """
    argv, err = build_loudnorm_ffmpeg_argv(
        input_path,
        input_path,
        ffprobe_exe,
        integrated_lufs,
        true_peak_db_tp,
        loudness_range,
        fallback_codec,
        fallback_bitrate,
    )
    if err:
        return False, err

    if replace_original:
        tmp = input_path.parent / f"{input_path.stem}.loudnorm-tmp{input_path.suffix}"
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        out_argv = argv[:-1] + [str(tmp)]
        ok = run_ffmpeg(out_argv, tmp)
        if not ok:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            return False, "encode failed"
        try:
            os.replace(tmp, input_path)
        except OSError as e:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            return False, f"replace failed: {e}"
        return True, ""

    out_path = input_path.parent / f"{input_path.stem}.normalized{input_path.suffix}"
    out_argv = argv[:-1] + [str(out_path)]
    ok = run_ffmpeg(out_argv, out_path)
    if not ok:
        try:
            if out_path.exists():
                out_path.unlink()
        except OSError:
            pass
        return False, "encode failed"
    return True, ""
