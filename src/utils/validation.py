"""Shared input-validation helpers."""
from __future__ import annotations

from typing import Any, Optional


def safe_str(value: Any, default: str, allowed: Optional[set] = None) -> str:
    """Return *value* as a stripped string if it is in *allowed* (or if no allowlist).

    Falls back to *default* when the value is not a string, is empty, or is
    not in the allowlist.  Keeps the trusted-input surface for values that go
    directly into FFmpeg filter strings or subprocess args as small as possible.
    """
    if not isinstance(value, str):
        return default
    value = value.strip()
    if not value:
        return default
    if allowed is not None and value not in allowed:
        return default
    return value


def safe_int(value: Any, default: int, lo: int, hi: int) -> int:
    """Cast *value* to int via float and clamp to [lo, hi]; return *default* on error."""
    try:
        result = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, result))
