"""Subtitle handling policy decision engine"""

from typing import Dict, Any, Optional, List
from core.encoder import SubtitleInfo, SubtitleDecision, can_mux_to_container, TEXT_SUBTITLE_CODECS


def decide_subtitle_action(
    subtitle_info: SubtitleInfo,
    settings: Dict[str, Any]
) -> SubtitleDecision:
    """Apply user policy to detected subtitles.

    Determines the best subtitle action based on what's available and user preferences.
    Returns a SubtitleDecision with action, reason, warnings, and source info.

    Args:
        subtitle_info: Detected subtitle sources (external, embedded)
        settings: User configuration including subtitle_handling and preferences

    Returns:
        SubtitleDecision with the chosen action and metadata
    """
    decision = SubtitleDecision("omit", "No subtitles found")

    # Get source priority from settings (default: check external first, then embedded)
    priority = settings.get("subtitle_handling", {}).get("subtitle_source_priority", ["external", "embedded"])
    warn_on_ass_mux = settings.get("warn_on_ass_mux", True)
    warn_on_burn = settings.get("warn_on_burn", True)
    subtitle_handling = settings.get("subtitle_handling", {})

    # Check sources in priority order
    for source_type in priority:
        if source_type == "external":
            # Check external text subtitles first (SRT, VTT, etc.)
            if subtitle_info.external_text:
                decision.action = subtitle_handling.get("external_text", "keep")
                decision.source = "external_text"
                decision.reason = f"User setting: {decision.action} external text subtitles"
                break

            # Check external ASS subtitles
            elif subtitle_info.external_ass:
                decision.action = subtitle_handling.get("external_ass", "keep")
                decision.source = "external_ass"
                decision.reason = f"User setting: {decision.action} external ASS subtitles"

                if decision.action == "mux" and warn_on_ass_mux:
                    decision.warnings.append(
                        "⚠️ ASS subtitles may lose styling, fonts, and positioning when muxed to MP4 as mov_text"
                    )
                break

        elif source_type == "embedded":
            if subtitle_info.embedded:
                stream = subtitle_info.embedded[0]  # Use first embedded subtitle stream
                decision.stream_index = stream["index"]
                codec = stream["codec"]
                decision.codec = codec  # Store codec for later use

                if stream["type"] == "bitmap":
                    # PGS or other bitmap subtitles
                    decision.action = subtitle_handling.get("pgs", "omit")
                    decision.source = "embedded_bitmap"

                    if decision.action == "skip_file":
                        decision.reason = "User setting: skip files with PGS subtitles"
                    else:
                        decision.reason = f"User setting: {decision.action} PGS bitmap subtitles"
                    break

                elif stream["type"] == "text":
                    # Text-based subtitles (SRT, ASS, WebVTT, etc.)
                    if codec in {"ass", "ssa"}:
                        decision.action = subtitle_handling.get("embedded_ass", "external")
                        decision.source = "embedded_ass"
                        decision.reason = f"User setting: {decision.action} embedded ASS subtitles"

                        if decision.action == "mux" and warn_on_ass_mux:
                            decision.warnings.append(
                                "⚠️ ASS subtitles may lose styling, fonts, and positioning when muxed to MP4 as mov_text"
                            )
                    else:
                        # SRT, WebVTT, SubRip, etc.
                        decision.action = subtitle_handling.get("embedded_text", "mux")
                        decision.source = "embedded_text"
                        decision.reason = f"User setting: {decision.action} embedded {codec} subtitles"
                    break

    # Validate action against container compatibility
    if decision.source and decision.action == "mux" and decision.source != "omit":
        # Determine which codec to check
        if decision.source == "external_text":
            codec = "subrip"  # Generic text subtitle codec
        elif decision.source == "external_ass":
            codec = "ass"
        else:
            # embedded_text or embedded_bitmap
            codec = subtitle_info.embedded[0]["codec"] if subtitle_info.embedded else "subrip"

        supported, method, warning = can_mux_to_container(codec, "mp4")
        if not supported:
            decision.action = "omit"
            if warning:
                decision.warnings.append(f"Cannot mux {codec} to MP4: {warning}")
            decision.reason = f"Container check: {codec} cannot be muxed to MP4, will omit subtitles"

    # Add burn warning if user selected burn action
    if decision.action == "burn" and warn_on_burn:
        decision.warnings.insert(0,
            "⚠️ Burning subtitles into video will cause Jellyfin to re-encode on playback. "
            "This may cause transcoding delays and higher server CPU usage."
        )

    return decision
