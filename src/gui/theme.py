"""Semantic color tokens for the app (shared by QSS in styles.py).

Runtime colors match app-theme.css :root. Tk/CustomTkinter helpers were removed
for the PyQt6 GUI; use gui.styles.get_stylesheet() at startup.
"""

from __future__ import annotations

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

APP_TREE_ROW_BG = APP_BG_SUNKEN
APP_TREE_HEADING_BG = APP_BG_RAISED
APP_TREE_SELECTION_BG = "#1e3a52"

MONO_FONT_CANDIDATES = (
    "JetBrains Mono",
    "Cascadia Code",
    "Consolas",
    "Courier New",
)


def theme_json_path():
    """Legacy path for bundled JSON theme (unused by PyQt6)."""
    import sys
    from pathlib import Path

    if getattr(sys, "frozen", False):
        bundled = Path(sys._MEIPASS) / "gui" / "themes" / "video_encoder_dark.json"
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parent / "themes" / "video_encoder_dark.json"
