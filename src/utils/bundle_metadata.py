"""Load version and distribution channel baked into frozen bundles."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_METADATA_CACHE: dict[str, Any] | None = None


def _bundle_metadata_path() -> Path | None:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", ""))
        if base.is_dir():
            p = base / "bundle_metadata.json"
            return p if p.is_file() else None
        return None
    here = Path(__file__).resolve().parents[1]
    p = here / "bundle_metadata.json"
    return p if p.is_file() else None


def load_bundle_metadata() -> dict[str, Any] | None:
    global _METADATA_CACHE
    if _METADATA_CACHE is not None:
        return _METADATA_CACHE
    path = _bundle_metadata_path()
    if not path:
        _METADATA_CACHE = {}
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            _METADATA_CACHE = data
            return data
    except Exception:
        pass
    _METADATA_CACHE = {}
    return None


def get_bundled_channel() -> str:
    meta = load_bundle_metadata()
    if not meta:
        return "unknown"
    ch = meta.get("channel")
    return ch if isinstance(ch, str) and ch else "unknown"


def get_bundled_version_string() -> str | None:
    meta = load_bundle_metadata()
    if not meta:
        return None
    v = meta.get("version")
    return v if isinstance(v, str) and v else None
