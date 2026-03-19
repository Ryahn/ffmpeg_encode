"""Rewrite FFmpeg CLI args to burn bitmap (PGS/HDMV) subtitles via overlay.

FFmpeg's ``subtitles=`` video filter uses libass and only supports text-based
subtitles. PGS must be overlaid from a decoded subtitle stream using
``filter_complex`` and ``overlay``.

Prefer overlaying ``[0:N]`` from the **same** input as the video so subtitle PTS
matches the main file. A remuxed single-stream sidecar MKV can drift vs the
primary timeline and drop most subtitle frames with default overlay sync.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

# PGS is sparse; default overlay sync only uses secondary frames with PTS <=
# primary. ``nearest`` avoids gaps. ``eof_action=pass`` / ``shortest=0`` keep
# the video running when the subtitle demuxer hits EOF before the video ends.
_OVERLAY_SYNC = "eof_action=pass:shortest=0:ts_sync_mode=nearest"


def _strip_subtitles_filter_from_vf_chain(vf_chain: str) -> str:
    """Remove ``subtitles=...`` segments from a comma-separated ``-vf`` chain."""
    segments: List[str] = []
    depth = 0
    start = 0
    for idx, ch in enumerate(vf_chain):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            seg = vf_chain[start:idx].strip()
            if seg and not seg.lower().startswith("subtitles="):
                segments.append(seg)
            start = idx + 1
    tail = vf_chain[start:].strip()
    if tail and not tail.lower().startswith("subtitles="):
        segments.append(tail)
    return ",".join(segments)


def _find_first_input_index(args: List[str]) -> Optional[int]:
    for i in range(1, len(args) - 1):
        if args[i] == "-i":
            return i
    return None


def _copy_args_after_first_input_skipping_vf_and_video_map(
    tail_after_main_path: List[str],
) -> List[str]:
    """Copy FFmpeg tokens after the first input path; drop ``-vf``/``-filter:v`` and ``-map 0:v:0`` pairs."""
    out: List[str] = []
    j = 0
    while j < len(tail_after_main_path):
        tok = tail_after_main_path[j]
        if tok in ("-vf", "-filter:v"):
            j += 2
            continue
        if tok == "-map" and j + 1 < len(tail_after_main_path) and tail_after_main_path[j + 1] == "0:v:0":
            j += 2
            continue
        out.append(tok)
        j += 1
        if j < len(tail_after_main_path) and not tail_after_main_path[j].startswith("-"):
            out.append(tail_after_main_path[j])
            j += 1
    return out


def _filter_complex_bitmap_overlay(base_vf_without_sub: str, subtitle_pad: str) -> str:
    """subtitle_pad is e.g. ``[0:6]`` or ``[1:0]`` (filter graph stream link)."""
    if base_vf_without_sub.strip():
        return (
            f"[0:v:0]setpts=PTS-STARTPTS,{base_vf_without_sub}[bmv];"
            f"{subtitle_pad}setpts=PTS-STARTPTS[bms];"
            f"[bmv][bms]overlay={_OVERLAY_SYNC}[outv]"
        )
    return (
        f"[0:v:0]setpts=PTS-STARTPTS[bmv];"
        f"{subtitle_pad}setpts=PTS-STARTPTS[bms];"
        f"[bmv][bms]overlay={_OVERLAY_SYNC}[outv]"
    )


def rewrite_ffmpeg_args_for_bitmap_subtitle_overlay(
    args: List[str],
    *,
    main_subtitle_stream_index: Optional[int] = None,
    sidecar_sub_path: Optional[Path] = None,
) -> Optional[List[str]]:
    """
    Replace ``-vf ... subtitles=...`` with ``-filter_complex`` overlay burn-in.

    If ``main_subtitle_stream_index`` is set (0-based FFmpeg stream index on the
    main file), uses a **single** ``-i`` and overlays ``[0:idx]`` — best sync.

    Otherwise, if ``sidecar_sub_path`` is a readable ``.mkv``/``.mks``, uses a
    second ``-i`` and overlays ``[1:0]``.
    """
    if len(args) < 3:
        return None

    vf_idx: Optional[int] = None
    vf_val: Optional[str] = None
    for i, a in enumerate(args):
        if a in ("-vf", "-filter:v") and i + 1 < len(args):
            vf_idx = i
            vf_val = args[i + 1]
            break
    if vf_idx is None or vf_val is None or "subtitles=" not in vf_val.lower():
        return None

    in_idx = _find_first_input_index(args)
    if in_idx is None or in_idx + 1 >= len(args):
        return None

    # ``rest`` keeps audio options intact, including ``-af`` / ``-c:a`` / ``-b:a`` (only ``-vf`` and
    # ``-map 0:v:0`` pairs are stripped from the tail after the main input).
    main_path = args[in_idx + 1]
    exe = args[0]
    prefix = args[1:in_idx]
    tail = args[in_idx + 2 :]
    base = _strip_subtitles_filter_from_vf_chain(vf_val).strip()
    rest = _copy_args_after_first_input_skipping_vf_and_video_map(tail)

    if main_subtitle_stream_index is not None and main_subtitle_stream_index >= 0:
        graph = _filter_complex_bitmap_overlay(base, f"[0:{main_subtitle_stream_index}]")
        return [exe] + prefix + ["-i", main_path, "-filter_complex", graph, "-map", "[outv]"] + rest

    if sidecar_sub_path is not None:
        sc = sidecar_sub_path.expanduser()
        if sc.is_file() and sc.suffix.lower() in (".mkv", ".mks"):
            graph = _filter_complex_bitmap_overlay(base, "[1:0]")
            return (
                [exe]
                + prefix
                + ["-i", main_path, "-i", str(sc.resolve()), "-filter_complex", graph, "-map", "[outv]"]
                + rest
            )

    return None


def rewrite_ffmpeg_args_for_sidecar_subtitle_overlay(
    args: List[str],
    sidecar_sub_path: Path,
) -> Optional[List[str]]:
    """Backward-compatible wrapper: sidecar-only rewrite (no main stream index)."""
    return rewrite_ffmpeg_args_for_bitmap_subtitle_overlay(
        args, main_subtitle_stream_index=None, sidecar_sub_path=sidecar_sub_path
    )
