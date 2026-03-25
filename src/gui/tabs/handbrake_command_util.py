"""HandBrake command preview and placeholder substitution (GUI-framework agnostic).

Reuses ``ffmpeg_preview_to_html`` from ``ffmpeg_command_util`` for the
colour-coded HTML badge rendering — the token regex already recognises all
the placeholders used here.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

from utils.config import config

# Characters that require double-quoting when embedding in a preview string.
_PATH_QUOTE_CHARS = frozenset(" &^%!")


def _quote_path(path_str: str) -> str:
    if any(c in path_str for c in _PATH_QUOTE_CHARS):
        return f'"{path_str}"'
    return path_str


def generate_hb_command_preview(
    command_template: str,
    get_files_callback: Optional[Callable],
    get_output_path_callback: Optional[Callable],
    suffix: str,
    output_extension: str = ".mp4",
) -> str:
    """Substitute placeholders in a HandBrakeCLI template for the command preview.

    Mirrors the behaviour of ``generate_command_preview`` in ``ffmpeg_command_util``
    but uses HandBrake conventions (1-based audio/subtitle track numbers).
    """
    if not command_template.strip():
        return "No command — configure settings on the HB Settings tab"

    files = []
    if get_files_callback:
        files = get_files_callback()
    if not files:
        return "No files available — add files on the Files tab to see preview"

    first = files[0]
    source_file = Path(first["path"])

    if get_output_path_callback:
        output_dir = get_output_path_callback(source_file)
    else:
        output_dir = source_file.parent
    output_file = output_dir / f"{source_file.stem}{suffix}{output_extension}"

    audio_track = first.get("audio_track")
    if audio_track is None:
        audio_track = 1

    subtitle_track = first.get("subtitle_track")

    command = command_template

    # Substitute executable path
    handbrake_path = config.get_handbrake_path() or "HandBrakeCLI"
    command = f"{handbrake_path} {command}" if not command.startswith(handbrake_path) else command

    # Input / output
    input_q = _quote_path(str(source_file))
    output_q = _quote_path(str(output_file))
    command = re.sub(r"\{INPUT\}", lambda _m: input_q, command)
    command = re.sub(r"\{OUTPUT\}", lambda _m: output_q, command)

    # Audio track (HandBrake uses 1-based)
    command = re.sub(r"\{AUDIO_TRACK\}", str(audio_track), command)

    # Subtitle track (HandBrake uses 1-based; internally stored as 0-based)
    if subtitle_track is not None:
        command = re.sub(r"\{SUBTITLE_TRACK\}", str(subtitle_track + 1), command)

    return command
