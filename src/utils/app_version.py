"""Application version for display and update comparison."""

from __future__ import annotations

import sys
from pathlib import Path

from utils.bundle_metadata import get_bundled_channel, get_bundled_version_string


def _read_version_from_src_init() -> str | None:
    try:
        init_file = Path(__file__).resolve().parents[1] / "__init__.py"
        if not init_file.is_file():
            return None
        for line in init_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("__version__"):
                return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_app_version() -> str:
    """Version string shown in About and used for update checks."""
    if is_frozen():
        bundled = get_bundled_version_string()
        if bundled:
            return bundled
    return _read_version_from_src_init() or "Unknown"


def windows_install_heuristic() -> bool:
    """Best-effort: likely Inno install under Program Files."""
    if sys.platform != "win32" or not is_frozen():
        return False
    try:
        exe = Path(sys.executable).resolve()
        parts_lower = [p.lower() for p in exe.parts]
        if "program files" in " ".join(parts_lower):
            return True
        if any("program files" in p for p in parts_lower):
            return True
    except Exception:
        pass
    return False


def effective_update_channel() -> str:
    """Channel for picking a release asset (portable vs installer vs mac)."""
    ch = get_bundled_channel()
    if ch not in ("unknown", "", None):
        return ch
    if sys.platform == "darwin":
        return "mac_app"
    if sys.platform == "win32" and windows_install_heuristic():
        return "inno"
    if sys.platform == "win32":
        return "portable"
    return "unknown"
