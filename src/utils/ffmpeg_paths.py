"""Resolve FFmpeg-related executables (ffprobe next to ffmpeg, then PATH)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional


def resolve_ffprobe_path(ffmpeg_path: Optional[str] = None) -> Optional[str]:
    """Return path to ffprobe: beside ``ffmpeg_path`` if set, else cwd/name, else PATH."""
    from utils.config import config

    fp = ffmpeg_path if ffmpeg_path is not None else (config.get_ffmpeg_path() or "")
    candidates: list[Path] = []
    if fp:
        parent = Path(fp).expanduser().resolve().parent
        candidates.append(parent / "ffprobe.exe")
        candidates.append(parent / "ffprobe")
    candidates.append(Path("ffprobe.exe"))
    candidates.append(Path("ffprobe"))
    for path in candidates:
        try:
            if path.exists():
                return str(path)
        except OSError:
            continue
    return shutil.which("ffprobe") or shutil.which("ffprobe.exe")
