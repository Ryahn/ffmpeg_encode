"""Resolve FFmpeg-related executables (ffprobe next to ffmpeg, then PATH)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional


def resolve_ffprobe_path(ffmpeg_path: Optional[str] = None) -> Optional[str]:
    """Return ffprobe: Settings path if set, else beside ffmpeg, else cwd/name, else PATH."""
    from utils.config import config

    explicit = (config.get_ffprobe_path() or "").strip()
    if explicit:
        p = Path(explicit).expanduser()
        try:
            if p.is_file():
                return str(p.resolve())
        except OSError:
            pass

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
