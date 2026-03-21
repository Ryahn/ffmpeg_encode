"""Batch extract text subtitles (ASS/SRT/VTT) beside video files."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

from core.encoder import BITMAP_SUBTITLE_CODECS, TEXT_SUBTITLE_CODECS
from core.subprocess_utils import get_subprocess_kwargs
from core.tools_audio_normalize import iter_media_files

_WIN_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_track_title_component(raw: str) -> str:
    """Remove Windows path-forbidden characters; keep spaces and ``&``."""
    s = (raw or "").strip()
    if not s:
        return ""
    s = _WIN_INVALID.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _subtitle_extension_for_codec(codec: str) -> Optional[str]:
    c = codec.lower()
    if c in ("ass", "ssa"):
        return ".ass"
    if c == "subrip":
        return ".srt"
    if c == "webvtt":
        return ".vtt"
    return None


def list_text_subtitle_streams(path: Path, ffprobe: str) -> Tuple[List[dict[str, Any]], Optional[str]]:
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "stream=index,codec_name:stream_tags=language,title",
        "-of",
        "json",
        str(path),
    ]
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            **get_subprocess_kwargs(),
        )
        if r.returncode != 0:
            return [], (r.stderr or "ffprobe failed").strip() or "ffprobe failed"
        data = json.loads(r.stdout)
        streams = data.get("streams") or []
        out: List[dict[str, Any]] = []
        for s in streams:
            codec = (s.get("codec_name") or "").lower()
            if codec in BITMAP_SUBTITLE_CODECS:
                out.append(
                    {
                        "index": s.get("index"),
                        "codec_name": codec,
                        "bitmap": True,
                    }
                )
                continue
            if codec not in TEXT_SUBTITLE_CODECS:
                continue
            tags = s.get("tags") or {}
            if not isinstance(tags, dict):
                tags = {}
            out.append(
                {
                    "index": s.get("index"),
                    "codec_name": codec,
                    "language": (tags.get("language") or tags.get("LANG") or "und"),
                    "title": tags.get("title") or tags.get("TITLE") or "",
                }
            )
        return out, None
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        return [], str(e)


_TEXT_CODEC_TO_EXT = {
    "subrip": "srt",
    "ass": "ass",
    "ssa": "ass",
    "webvtt": "vtt",
}


def extract_text_subtitle_stream_with_runner(
    run_ffmpeg: Callable[[List[str], Path], bool],
    input_file: Path,
    subtitle_codec: str,
    subtitle_stream_id: int,
    output_file: Path,
) -> Tuple[Optional[Path], Optional[str]]:
    """Like ``extract_text_subtitle_to_file`` but uses ``run_ffmpeg`` for cancellable encode."""
    if subtitle_codec in BITMAP_SUBTITLE_CODECS:
        return None, f"Cannot extract bitmap subtitle codec '{subtitle_codec}' to text file"
    if subtitle_codec not in _TEXT_CODEC_TO_EXT:
        return None, f"Unsupported subtitle codec '{subtitle_codec}'"
    argv = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-i",
        str(input_file),
        "-map",
        f"0:{subtitle_stream_id}",
        "-c:s",
        "copy",
        "-y",
        str(output_file),
    ]
    if not run_ffmpeg(argv, output_file):
        return None, "ffmpeg failed"
    if output_file.exists() and output_file.stat().st_size > 0:
        return output_file, None
    try:
        if output_file.exists():
            output_file.unlink()
    except OSError:
        pass
    return None, "empty or missing output"


def build_sidecar_path(video: Path, stream: dict[str, Any]) -> Optional[Path]:
    ext = _subtitle_extension_for_codec(stream["codec_name"])
    if ext is None:
        return None
    idx = stream.get("index")
    if idx is None:
        return None
    lang = str(stream.get("language") or "und").strip() or "und"
    title_raw = stream.get("title") or ""
    title_safe = sanitize_track_title_component(str(title_raw))
    if not title_safe:
        title_part = f"track{idx}"
    else:
        title_part = title_safe
    name = f"{video.stem}.{lang}.{title_part}{ext}"
    return video.parent / name


def extract_all_text_subtitles_for_file(
    *,
    ffprobe_path: str,
    video_path: Path,
    log: Callable[[str, str], None],
    run_ffmpeg: Callable[[List[str], Path], bool],
) -> Tuple[int, int]:
    """
    Extract every text subtitle stream. Returns (success_count, skip_or_error_count).
    """
    streams, err = list_text_subtitle_streams(video_path, ffprobe_path)
    if err:
        log("ERROR", f"{video_path.name}: {err}")
        return 0, 1
    ok_n = 0
    bad_n = 0
    for st in streams:
        if st.get("bitmap"):
            log(
                "INFO",
                f"{video_path.name}: skip bitmap subtitle (codec={st.get('codec_name')})",
            )
            bad_n += 1
            continue
        out = build_sidecar_path(video_path, st)
        if out is None:
            bad_n += 1
            continue
        codec = st["codec_name"]
        sid = int(st["index"])
        path_out, emsg = extract_text_subtitle_stream_with_runner(
            run_ffmpeg,
            video_path,
            codec,
            sid,
            out,
        )
        if path_out:
            log("INFO", f"Wrote {path_out.name}")
            ok_n += 1
        else:
            log("WARNING", f"{video_path.name} stream {sid}: {emsg or 'extract failed'}")
            bad_n += 1
    return ok_n, bad_n


def iter_videos_for_subtitle_tool(root: Path, recursive: bool) -> List[Path]:
    return iter_media_files(root, recursive)
