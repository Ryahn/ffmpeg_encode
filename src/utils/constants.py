"""Shared application-wide constants."""
from __future__ import annotations

VIDEO_EXTENSIONS: frozenset[str] = frozenset({
    ".mkv", ".mp4", ".mov", ".m4v", ".avi",
    ".flv", ".wmv", ".webm", ".ts", ".mts",
    ".m2ts", ".vob", ".3gp", ".3g2",
})
