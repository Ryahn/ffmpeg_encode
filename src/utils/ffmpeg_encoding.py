"""Shared FFmpeg encoding helpers (pixel format vs profile, etc.)."""

from __future__ import annotations

PROFILE_PIX_FMT = {
    "main10": "yuv420p10le",
    "main12": "yuv420p12le",
}

# Allowed manual -pix_fmt values from UI / config (reject unknown on load/set).
ALLOWED_MANUAL_PIX_FMT = (
    "yuv420p",
    "yuv420p10le",
    "yuv420p12le",
    "yuv444p",
    "yuv444p10le",
    "nv12",
    "p010le",
)


def resolve_pix_fmt(profile: str, mode: str, manual: str) -> str:
    """Return pixel format for encoding: auto from HEVC/H264 profile or fixed manual."""
    if mode == "manual":
        m = (manual or "yuv420p").strip()
        return m if m in ALLOWED_MANUAL_PIX_FMT else "yuv420p"
    p = (profile or "main").strip().lower()
    return PROFILE_PIX_FMT.get(p, "yuv420p")
