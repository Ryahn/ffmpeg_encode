"""Application theme tokens and CustomTkinter theme loading.

Runtime colors match app-theme.css :root. Tk does not parse CSS; keep JSON + this
module in sync when changing the design.
"""

from __future__ import annotations

import sys
import tkinter.font as tkfont
from pathlib import Path
from typing import Optional

import customtkinter as ctk

# Surfaces (app-theme.css)
APP_BG = "#1a1b1f"
APP_BG_RAISED = "#26272c"
APP_BG_SUNKEN = "#111215"
APP_BG_TAB = "#20212a"

APP_BORDER = "#38393f"
APP_BORDER_INNER = "#25262a"

APP_BLUE = "#1d6fb8"
APP_BLUE_LIGHT = "#5ba4f5"

APP_TEXT = "#c0c0c0"
APP_TEXT_DIM = "#888888"
APP_TEXT_TITLE = "#c8c8c8"
APP_TEXT_HEADER = "#999999"
APP_TEXT_CMD = "#7dd3fc"
APP_TEXT_PREVIEW = "#9ca3af"

APP_STATUS_PENDING = "#888888"
APP_STATUS_ANALYZING = "#f0a500"
APP_STATUS_READY = "#4ade80"
APP_STATUS_ENCODING = "#5bcefa"
APP_STATUS_DONE = "#4ade80"
APP_STATUS_ERROR = "#ff5f57"

APP_LOG_INFO = "#5ba4f5"
APP_LOG_SUCCESS = "#4ade80"
APP_LOG_WARN = "#f0a500"
APP_LOG_PLAIN = "#888888"

APP_BUTTON_DISABLED_BG = "#2e2f34"
APP_BUTTON_DISABLED_TEXT = "#555555"

APP_SCROLLBAR_THUMB = "#3a3b40"

# ttk.Treeview: selection hint (~ rgba(29, 111, 184, 0.18) on dark body)
APP_TREE_ROW_BG = APP_BG_SUNKEN
APP_TREE_HEADING_BG = APP_BG_RAISED
APP_TREE_SELECTION_BG = "#1e3a52"

MONO_FONT_CANDIDATES = (
    "JetBrains Mono",
    "Cascadia Code",
    "Consolas",
    "Courier New",
)

_cached_mono_family: Optional[str] = None


def theme_json_path() -> Path:
    if getattr(sys, "frozen", False):
        bundled = Path(sys._MEIPASS) / "gui" / "themes" / "video_encoder_dark.json"
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parent / "themes" / "video_encoder_dark.json"


def apply_theme() -> None:
    path = theme_json_path()
    if path.is_file():
        ctk.set_default_color_theme(str(path))
    else:
        ctk.set_default_color_theme("blue")


def prime_monospace_font(master) -> None:
    """Resolve monospace family once (call after a Tk window exists)."""
    global _cached_mono_family
    if _cached_mono_family is not None:
        return
    try:
        root = master.winfo_toplevel()
        families = set(tkfont.families(root))
    except Exception:
        families = set()
    _cached_mono_family = "Consolas"
    for candidate in MONO_FONT_CANDIDATES:
        if candidate in families:
            _cached_mono_family = candidate
            break


def monospace_font(
    size: int = 13,
    weight: str = "normal",
    master=None,
) -> ctk.CTkFont:
    if master is not None:
        prime_monospace_font(master)
    family = _cached_mono_family or "Consolas"
    return ctk.CTkFont(family=family, size=size, weight=weight)


def monospace_tk_tuple(master, size: int = 13) -> tuple[str, int]:
    """For ttk/tk widgets that need (family, size)."""
    prime_monospace_font(master)
    return (_cached_mono_family or "Consolas", size)
