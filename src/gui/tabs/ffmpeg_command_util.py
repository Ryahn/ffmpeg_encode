"""FFmpeg command preview and parsing (GUI-framework agnostic)."""

from __future__ import annotations

import html
import re
import shlex
import tempfile
from pathlib import Path
from typing import Callable, List, Optional

from core.ffmpeg_translator import _escape_ffmpeg_filter_path
from utils.config import config

_FFMPEG_PREVIEW_TOKEN_RE = re.compile(
    r"(\{SUBTITLE_FILE\}|\{SUBTITLE_TRACK\}|\{AUDIO_TRACK\}|\{INPUT\}|\{OUTPUT\}|"
    r"<SUBTITLE_FILE>|<SUBTITLE_TRACK>|<AUDIO_TRACK>|<INPUT>|<OUTPUT>|"
    r"\binput\.mkv\b|\boutput\.mp4\b)",
    re.IGNORECASE,
)

_PREVIEW_KNOWN_TOKENS = frozenset(
    {
        "{SUBTITLE_FILE}",
        "{SUBTITLE_TRACK}",
        "{AUDIO_TRACK}",
        "{INPUT}",
        "{OUTPUT}",
        "<SUBTITLE_FILE>",
        "<SUBTITLE_TRACK>",
        "<AUDIO_TRACK>",
        "<INPUT>",
        "<OUTPUT>",
    }
)

_UNKNOWN_PLACEHOLDER_RE = re.compile(r"(\{[A-Z][A-Z0-9_]*\}|<[A-Z][A-Z0-9_]*>)")

# Characters that require a path to be double-quoted when embedded in a
# command string that will later be parsed by shlex.split().
_PATH_QUOTE_CHARS = frozenset(' &^%!')


def _escape_gap_with_placeholder_marks(gap_plain: str) -> str:
    """HTML-escape a gap between primary tokens; badge unknown {FOO}/<FOO> placeholders."""
    if not gap_plain:
        return ""
    parts: List[str] = []
    last = 0
    for match in _UNKNOWN_PLACEHOLDER_RE.finditer(gap_plain):
        parts.append(html.escape(gap_plain[last : match.start()]))
        tok = match.group(1)
        if tok in _PREVIEW_KNOWN_TOKENS:
            parts.append(_ffmpeg_preview_token_span(tok))
        else:
            esc = html.escape(tok)
            parts.append(
                f'<span style="background-color:#5c2a2a;color:#ff9d9d;padding:1px 5px;'
                f'border-radius:3px;font-weight:600;" title="Unknown placeholder — check spelling">'
                f"{esc}</span>"
            )
        last = match.end()
    parts.append(html.escape(gap_plain[last:]))
    return "".join(parts)


def _ffmpeg_preview_token_span(token: str) -> str:
    low = token.lower()
    if low == "input.mkv" or token in ("{INPUT}", "<INPUT>"):
        bg, fg = "#1e3a52", "#7dd3fc"
    elif low == "output.mp4" or token in ("{OUTPUT}", "<OUTPUT>"):
        bg, fg = "#1a3d2e", "#4ade80"
    elif token in ("{AUDIO_TRACK}", "<AUDIO_TRACK>"):
        bg, fg = "#3d3020", "#f0a500"
    elif token in ("{SUBTITLE_TRACK}", "<SUBTITLE_TRACK>"):
        bg, fg = "#2d2640", "#c4b5fd"
    elif token in ("{SUBTITLE_FILE}", "<SUBTITLE_FILE>"):
        bg, fg = "#3d1f40", "#f9a8d4"
    else:
        bg, fg = "#38393f", "#c0c0c0"
    esc = html.escape(token)
    return (
        f'<span style="background-color:{bg};color:{fg};padding:1px 5px;'
        f'border-radius:3px;font-weight:600;">{esc}</span>'
    )


def ffmpeg_preview_to_html(plain_preview: str) -> str:
    """
    HTML for QTextEdit: same text as the plain preview, with colored inline
    badges for dynamic placeholders and example input.mkv / output.mp4 paths.
    """
    if plain_preview.startswith(("No command", "No files", "Error generating")):
        inner = html.escape(plain_preview)
        return (
            '<div style="color:#9ca3af;font-family:Consolas,Courier New,monospace;'
            'font-size:12px;white-space:pre-wrap;word-wrap:break-word;">'
            f"{inner}</div>"
        )
    chunks: List[str] = []
    pos = 0
    for match in _FFMPEG_PREVIEW_TOKEN_RE.finditer(plain_preview):
        chunks.append(_escape_gap_with_placeholder_marks(plain_preview[pos : match.start()]))
        chunks.append(_ffmpeg_preview_token_span(match.group(1)))
        pos = match.end()
    chunks.append(_escape_gap_with_placeholder_marks(plain_preview[pos:]))
    body = "".join(chunks)
    return (
        '<div style="color:#c0c0c0;font-family:Consolas,Courier New,monospace;'
        'font-size:12px;white-space:pre-wrap;word-wrap:break-word;">'
        f"{body}</div>"
    )


def generate_command_preview(
    command_template: str,
    get_files_callback: Optional[Callable],
    get_output_path_callback: Optional[Callable],
    suffix: str,
) -> str:
    if not command_template.strip():
        return "No command entered - load a preset or enter a command to see preview"
    files = []
    if get_files_callback:
        files = get_files_callback()
    if not files:
        return "No files available - add files to see preview with actual file paths"
    first_file_data = files[0]
    source_file = Path(first_file_data["path"])
    if get_output_path_callback:
        output_dir = get_output_path_callback(source_file)
    else:
        output_dir = source_file.parent
    output_file = output_dir / f"{source_file.stem}{suffix}.mp4"
    audio_track = first_file_data.get("audio_track")
    subtitle_track = first_file_data.get("subtitle_track")
    # Do NOT call analyze_tracks() here — it is a blocking subprocess call that
    # would freeze the GUI thread on every debounced preview refresh.  If the
    # file has no cached track data yet, fall back to the default track number
    # so the preview renders quickly.  Users can run "Load tracks" to populate
    # real track data, after which the preview will reflect the actual values.
    if audio_track is None:
        audio_track = 2
    subtitle_file = None
    if subtitle_track is not None:
        subtitle_file = Path(tempfile.gettempdir()) / f"{source_file.stem}_subtitle.mkv"
    command = command_template

    def quote_path_if_needed(path_str: str) -> str:
        # Escape square brackets for FFmpeg (they have special meaning in FFmpeg syntax)
        path_str = path_str.replace('[', r'\[').replace(']', r'\]')
        if any(c in path_str for c in _PATH_QUOTE_CHARS):
            return f'"{path_str}"'
        return path_str

    input_file_str = str(source_file)
    output_file_str = str(output_file)
    input_file_quoted = quote_path_if_needed(input_file_str)
    output_file_quoted = quote_path_if_needed(output_file_str)

    def escape_for_replacement(path_str: str) -> str:
        return path_str.replace("\\", "\\\\")

    command = re.sub(r"\binput\.mkv\b", lambda m: input_file_quoted, command, flags=re.IGNORECASE)
    command = re.sub(r"\{INPUT\}", lambda m: input_file_quoted, command)
    command = re.sub(r"<INPUT>", lambda m: input_file_quoted, command)
    command = re.sub(r"\boutput\.mp4\b", lambda m: output_file_quoted, command, flags=re.IGNORECASE)
    command = re.sub(r"\{OUTPUT\}", lambda m: output_file_quoted, command)
    command = re.sub(r"<OUTPUT>", lambda m: output_file_quoted, command)
    command = re.sub(r"\{AUDIO_TRACK\}", str(audio_track), command)
    command = re.sub(r"<AUDIO_TRACK>", str(audio_track), command)
    audio_stream_id = audio_track - 1
    command = re.sub(
        r"(-map\s+0:v:0\s+)-map\s+0:\d+",
        rf"\1-map 0:{audio_stream_id}",
        command,
    )
    if subtitle_track is not None:
        command = re.sub(r"\{SUBTITLE_TRACK\}", str(subtitle_track), command)
        command = re.sub(r"<SUBTITLE_TRACK>", str(subtitle_track), command)
    if subtitle_file:
        sub_path = str(subtitle_file).replace("\\", "/").replace(":", "\\:")
        sub_path = sub_path.replace("'", "'\\''")
        command = re.sub(r"\{SUBTITLE_FILE\}", lambda m: sub_path, command)
        command = re.sub(r"<SUBTITLE_FILE>", lambda m: sub_path, command)
    command = re.sub(r'"input\.mkv"', lambda m: input_file_quoted, command, flags=re.IGNORECASE)
    command = re.sub(r'"output\.mp4"', lambda m: output_file_quoted, command, flags=re.IGNORECASE)
    input_single_quoted = f"'{input_file_str}'"
    output_single_quoted = f"'{output_file_str}'"
    command = re.sub(r"'input\.mkv'", lambda m: input_single_quoted, command, flags=re.IGNORECASE)
    command = re.sub(r"'output\.mp4'", lambda m: output_single_quoted, command, flags=re.IGNORECASE)
    ffmpeg_path = config.get_ffmpeg_path() or "ffmpeg"
    if ffmpeg_path != "ffmpeg":
        command = re.sub(r"\bffmpeg\b", lambda m: ffmpeg_path, command, flags=re.IGNORECASE)
    return command


def parse_and_substitute_command(
    command_template: str,
    input_file: Path,
    output_file: Path,
    audio_track: int,
    subtitle_track: Optional[int],
    subtitle_file: Optional[Path],
    on_log: Callable[[str, str], None],
) -> List[str]:
    command = command_template
    command = re.sub(r"(scale=[^,\s'\"]+):si=\d+", r"\1", command)

    def escape_for_replacement(path_str: str) -> str:
        return path_str.replace("\\", "\\\\")

    def quote_path_if_needed(path_str: str) -> str:
        # Escape square brackets for FFmpeg (they have special meaning in FFmpeg syntax)
        path_str = path_str.replace('[', r'\[').replace(']', r'\]')
        if any(c in path_str for c in _PATH_QUOTE_CHARS):
            return f'"{path_str}"'
        return path_str

    input_file_str = str(input_file)
    output_file_str = str(output_file)
    input_file_quoted = quote_path_if_needed(input_file_str)
    output_file_quoted = quote_path_if_needed(output_file_str)
    input_file_escaped = escape_for_replacement(input_file_quoted)
    output_file_escaped = escape_for_replacement(output_file_quoted)

    command = re.sub(r"\binput\.mkv\b", input_file_escaped, command, flags=re.IGNORECASE)
    command = re.sub(r"\{INPUT\}", input_file_escaped, command)
    command = re.sub(r"<INPUT>", input_file_escaped, command)
    command = re.sub(r"\boutput\.mp4\b", output_file_escaped, command, flags=re.IGNORECASE)
    command = re.sub(r"\{OUTPUT\}", output_file_escaped, command)
    command = re.sub(r"<OUTPUT>", output_file_escaped, command)
    command = re.sub(r"\{AUDIO_TRACK\}", str(audio_track), command)
    command = re.sub(r"<AUDIO_TRACK>", str(audio_track), command)
    audio_stream_id = audio_track - 1
    command = re.sub(
        r"(-map\s+0:v:0\s+)-map\s+0:\d+",
        rf"\1-map 0:{audio_stream_id}",
        command,
    )
    if subtitle_track is not None:
        command = re.sub(r"\{SUBTITLE_TRACK\}", str(subtitle_track), command)
        command = re.sub(r"<SUBTITLE_TRACK>", str(subtitle_track), command)
    if subtitle_file:
        sub_path = _escape_ffmpeg_filter_path(str(subtitle_file))
        command = re.sub(r"\{SUBTITLE_FILE\}", lambda m: sub_path, command)
        command = re.sub(r"<SUBTITLE_FILE>", lambda m: sub_path, command)
    else:
        command = re.sub(
            r",\s*subtitles=['\"](?:\{SUBTITLE_FILE\}|<SUBTITLE_FILE>)['\"]",
            "",
            command,
        )
        command = re.sub(
            r"subtitles=['\"](?:\{SUBTITLE_FILE\}|<SUBTITLE_FILE>)['\"]\s*,",
            "",
            command,
        )
    if "input.mkv" in command.lower() or "output.mp4" in command.lower():
        command = re.sub(r'"input\.mkv"', input_file_escaped, command, flags=re.IGNORECASE)
        command = re.sub(r'"output\.mp4"', output_file_escaped, command, flags=re.IGNORECASE)
        input_single_quoted = escape_for_replacement(f"'{input_file_str}'")
        output_single_quoted = escape_for_replacement(f"'{output_file_str}'")
        command = re.sub(r"'input\.mkv'", input_single_quoted, command, flags=re.IGNORECASE)
        command = re.sub(r"'output\.mp4'", output_single_quoted, command, flags=re.IGNORECASE)

    _remaining = re.findall(r"\{[A-Z_]+\}|<[A-Z_]+>", command)
    if _remaining:
        on_log(
            "WARNING",
            "Unresolved placeholder(s) in command — encoding may fail: "
            + ", ".join(dict.fromkeys(_remaining)),
        )

    # Validate input/output files exist before parsing command
    # (use original unescaped paths, not the FFmpeg-escaped versions)
    if not input_file.exists():
        on_log("ERROR", f"Input file does not exist: {input_file}")
        return []

    try:
        args = shlex.split(command, posix=False)
    except Exception as e:
        on_log("ERROR", f"Command parsing failed ({e}); cannot build argument list.")
        return []

    if not args:
        return []

    ffmpeg_executable = (config.get_ffmpeg_path() or "").strip() or "ffmpeg"
    first_name = Path(args[0]).name.lower()
    configured_name = Path(ffmpeg_executable).name.lower()
    allowed_first = {"ffmpeg", "ffmpeg.exe"}
    if configured_name:
        allowed_first.add(configured_name)
    if first_name not in allowed_first:
        raise ValueError(
            "Command must start with ffmpeg or ffmpeg.exe, or the FFmpeg executable "
            "configured in Settings (first argument was not recognized as FFmpeg)."
        )
    args[0] = ffmpeg_executable
    return args
