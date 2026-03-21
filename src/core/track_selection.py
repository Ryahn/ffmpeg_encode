"""Shared logic for choosing audio and subtitle tracks from analyze_tracks() results."""

from typing import Callable, Optional, Tuple

from utils.config import config
from core.track_analyzer import TrackAnalyzer


def audio_mkv_stream_id_for_ordinal(tracks: dict, ordinal_1based: int) -> Optional[int]:
    """FFmpeg/Matroska 0-based stream index for the Nth audio stream (ordinal_1based is 1, 2, …)."""
    audios = sorted(
        (
            t
            for t in (tracks.get("all_tracks") or [])
            if t.get("type") == "audio" and t.get("id") is not None
        ),
        key=lambda t: t["id"],
    )
    if 1 <= ordinal_1based <= len(audios):
        return audios[ordinal_1based - 1]["id"]
    return None


def compute_effective_tracks(
    tracks: dict,
    track_analyzer: TrackAnalyzer,
    log_info: Optional[Callable[[str], None]] = None,
    source_label: str = "",
) -> Tuple[Optional[int], Optional[int]]:
    """
    Apply the same rules as the encode path: English audio, Japanese-audio mode,
    Signs & Songs subtitle, then first English sub when using first audio only.

    Returns:
        (effective_audio, subtitle_track): audio is 1-based index among audio streams
        (first audio = 1); subtitle is 0-based Matroska stream id, or None.
    """
    suffix = f" for: {source_label}" if source_label else ""

    effective_audio = tracks.get("audio")
    if (
        not effective_audio
        and config.get_allow_japanese_audio_with_english_subs()
        and tracks.get("first_audio")
    ):
        effective_audio = tracks["first_audio"]
        if log_info:
            log_info(
                f"No English audio; using first audio track ({effective_audio}) with English subs{suffix}"
            )
    if not effective_audio:
        return None, None

    subtitle_track = tracks.get("subtitle")
    using_japanese_audio = effective_audio == tracks.get("first_audio") and not tracks.get(
        "audio"
    )

    if subtitle_track is None and tracks.get("all_tracks"):
        for track in sorted(tracks["all_tracks"], key=lambda t: t["id"]):
            if track.get("type") != "subtitles":
                continue
            is_eng = track_analyzer._is_english_subtitle_track(
                track.get("language"), track.get("name")
            )
            is_signs = track_analyzer._is_signs_songs_track(track.get("name"))
            if is_eng and is_signs:
                subtitle_track = track["id"]
                tracks["subtitle"] = subtitle_track
                if log_info:
                    log_info(
                        f"Subtitle track {subtitle_track} (Signs & Songs) detected{suffix}"
                    )
                break
        if subtitle_track is None and using_japanese_audio:
            for track in sorted(tracks["all_tracks"], key=lambda t: t["id"]):
                if track.get("type") == "subtitles" and track_analyzer._matches_english_subtitle_language(
                    track.get("language")
                ):
                    subtitle_track = track["id"]
                    tracks["subtitle"] = subtitle_track
                    if log_info:
                        log_info(
                            f"Japanese-audio mode: using first English subtitle track {subtitle_track}{suffix}"
                        )
                    break

    return effective_audio, subtitle_track
