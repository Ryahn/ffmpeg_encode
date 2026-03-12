r"""
Standalone script to run track detection logic and print verbose debug output.
Uses the same config and TrackAnalyzer as the main app.

Run from project root:
  python scripts/debug_track_detection.py "C:\path\to\file.mkv"
Or with default test file:
  python scripts/debug_track_detection.py
"""

import re
import sys
from pathlib import Path

# Use UTF-8 for stdout so config/track names with non-ASCII print correctly on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add src to path so we use the same modules as the app
_project_root = Path(__file__).resolve().parent.parent
_src = _project_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from utils.config import config
from core.track_analyzer import TrackAnalyzer


DEFAULT_FILE = (
    r"C:\Users\ryanc\Downloads\RawAnime\Raw\[neoDESU] Arifureta [Season 2-3 + OVA + Special] "
    r"[BD 1080p x265 HEVC OPUS AAC] [Dual Audio]\Season 3\Arifureta - From Commonplace to "
    r"World's Strongest - S03E09.mkv"
)


def _print_section(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def _test_pattern(pattern: str, text: str, flags: int = re.IGNORECASE) -> bool:
    if not text:
        return False
    try:
        return bool(re.search(pattern, text, flags))
    except re.error:
        return False


def run_debug(file_path: Path) -> None:
    print(f"File: {file_path}")
    print(f"Exists: {file_path.exists()}")
    if not file_path.exists():
        print("ERROR: File not found.")
        return

    _print_section("Detection settings (from config)")
    print("Audio language tags:", config.get_audio_language_tags())
    print("Audio name patterns:", config.get_audio_name_patterns())
    print("Audio exclude patterns:", config.get_audio_exclude_patterns())
    print("Subtitle language tags:", config.get_subtitle_language_tags())
    print("Subtitle name patterns:", config.get_subtitle_name_patterns())
    print("Subtitle exclude patterns:", config.get_subtitle_exclude_patterns())

    analyzer = TrackAnalyzer()
    if not analyzer.mkvinfo_path:
        print("\nERROR: mkvinfo not found. Install MKVToolNix and ensure mkvinfo is on PATH.")
        return

    print(f"\nmkvinfo path: {analyzer.mkvinfo_path}")

    _print_section("Running analyze_tracks()")
    result = analyzer.analyze_tracks(file_path)

    if result.get("error"):
        print(f"ERROR: {result['error']}")
        return

    print(f"Selected audio track (1-based): {result.get('audio')}")
    sub = result.get("subtitle")
    print(f"Selected subtitle track (0-based): {sub}" + (f"  (HandBrake --subtitle {sub + 1})" if sub is not None else ""))

    all_tracks = result.get("all_tracks") or []
    if not all_tracks:
        print("No tracks in result.")
        return

    sorted_tracks = sorted(all_tracks, key=lambda t: t["id"])

    _print_section("Parsed tracks (as used by analyzer)")
    for track in sorted_tracks:
        tid = track["id"]
        handbrake_id = tid + 1
        typ = track.get("type") or "?"
        lang = track.get("language") or "(not set)"
        name = track.get("name") or "(not set)"
        print(f"\n  Track ID {tid} (HandBrake {handbrake_id}): type={typ}, language={lang!r}, name={name!r}")

    _print_section("Audio track selection (first English by id)")
    for track in sorted_tracks:
        if track.get("type") != "audio":
            continue
        tid = track["id"]
        lang = track.get("language")
        name = track.get("name")
        print(f"\n  Track ID {tid} (HandBrake {tid + 1}): lang={lang!r}, name={name!r}")

        lang_tags = config.get_audio_language_tags()
        name_patterns = config.get_audio_name_patterns()
        exclude_patterns = config.get_audio_exclude_patterns()

        if lang:
            for tag in lang_tags:
                match = lang.lower() == tag.lower() or lang.lower().startswith(tag.lower() + "-") or lang.lower().startswith(tag.lower() + "_")
                print(f"    Language tag {tag!r}: {match}")
        if name:
            for pat in name_patterns:
                m = _test_pattern(pat, name)
                print(f"    Name pattern {pat!r}: {m}")
            for pat in exclude_patterns:
                m = _test_pattern(pat, name)
                print(f"    Exclude pattern {pat!r}: {m}")

        is_eng = analyzer._is_english_track(lang, name)
        print(f"    --> _is_english_track: {is_eng}")

    _print_section("Subtitle track selection (first English + Signs & Songs by id)")
    for track in sorted_tracks:
        if track.get("type") != "subtitles":
            continue
        tid = track["id"]
        lang = track.get("language")
        name = track.get("name")
        print(f"\n  Track ID {tid} (HandBrake {tid + 1}): lang={lang!r}, name={name!r}")

        lang_tags = config.get_subtitle_language_tags()
        exclude_patterns = config.get_subtitle_exclude_patterns()
        name_patterns = config.get_subtitle_name_patterns()

        print("    English check:")
        if lang:
            for tag in lang_tags:
                match = lang.lower() == tag.lower() or lang.lower().startswith(tag.lower() + "-") or lang.lower().startswith(tag.lower() + "_")
                print(f"      Language tag {tag!r}: {match}")
            if name:
                for pat in exclude_patterns:
                    m = _test_pattern(pat, name)
                    print(f"      Exclude pattern {pat!r}: {m}")
        is_english_sub = analyzer._is_english_subtitle_track(lang, name)
        print(f"    --> _is_english_subtitle_track: {is_english_sub}")

        print("    Signs & Songs check (name patterns):")
        if name:
            for pat in name_patterns:
                m = _test_pattern(pat, name)
                print(f"      Pattern {pat!r} vs name {name!r}: {m}")
        else:
            print("      (no name -> no match)")
        is_signs_songs = analyzer._is_signs_songs_track(name)
        print(f"    --> _is_signs_songs_track: {is_signs_songs}")

        would_select = is_english_sub and is_signs_songs
        print(f"    --> Would select this track: {would_select}")

    _print_section("Final result")
    print(f"  Audio track (1-based):    {result.get('audio')}")
    sub = result.get("subtitle")
    print(f"  Subtitle track (0-based): {sub}" + (f"  (HandBrake: {sub + 1})" if sub is not None else ""))
    print()


def main() -> None:
    if len(sys.argv) >= 2:
        path = Path(sys.argv[1])
    else:
        path = Path(DEFAULT_FILE)
    run_debug(path)


if __name__ == "__main__":
    main()
