"""Default output container: file extensions and HandBrake --format mapping."""

from __future__ import annotations

ALLOWED_CONTAINERS = frozenset({"mp4", "m4v", "mkv", "mov", "webm"})

_HB_FROM_LEGACY = {"av_mp4": "mp4", "av_mkv": "mkv", "av_webm": "webm"}


def normalize_container(value: str | None) -> str:
    """Return an allowlisted container id, defaulting to mp4."""
    if not value:
        return "mp4"
    v = str(value).strip().lower()
    if v in ALLOWED_CONTAINERS:
        return v
    if v.startswith("."):
        v = v.lstrip(".")
        if v in ALLOWED_CONTAINERS:
            return v
    return "mp4"


def file_extension_for_container(container: str) -> str:
    """File extension including dot (e.g. '.mkv')."""
    c = normalize_container(container)
    return f".{c}"


def handbrake_format_for_container(container: str) -> str:
    """HandBrakeCLI --format value for a logical container."""
    c = normalize_container(container)
    if c in ("mp4", "m4v", "mov"):
        return "av_mp4"
    if c == "mkv":
        return "av_mkv"
    if c == "webm":
        return "av_webm"
    return "av_mp4"


def default_container_from_handbrake_format(hb_format: str | None) -> str:
    """Map legacy handbrake_encoding.format (av_mp4, etc.) to default_output_container."""
    if not hb_format:
        return "mp4"
    v = str(hb_format).strip().lower()
    return _HB_FROM_LEGACY.get(v, "mp4")


def iso_bmff_extension(suffix: str) -> bool:
    """True if extension is ISO-BMFF family (streaming faststart applies)."""
    s = suffix.lower()
    if not s.startswith("."):
        s = f".{s}"
    return s in (".mp4", ".m4v", ".mov")


def subtitle_compat_container(container: str) -> str:
    """Normalize container name for CONTAINER_SUBTITLE_SUPPORT lookup (mp4/mkv)."""
    c = normalize_container(container)
    if c in ("m4v", "mov"):
        return "mp4"
    if c == "webm":
        return "webm"
    return c
