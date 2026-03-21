#!/usr/bin/env python
"""Test command substitution and parsing for FFmpeg execution."""

import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path.cwd() / 'src'))

from gui.tabs.ffmpeg_command_util import parse_and_substitute_command

def test_command_substitution():
    """Test that command substitution works correctly."""
    print("Testing command substitution and parsing...")
    print()

    # Create temporary test files to use
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        input_file = tmpdir / "test_input.mkv"
        output_file = tmpdir / "test_output.mp4"

        # Create dummy input file
        input_file.touch()

        # Test template with all placeholder types
        template = (
            'ffmpeg -i {INPUT} '
            '-c:v hevc_nvenc -cq 28 -preset p5 '
            '-map 0:v:0 -map 0:a:{AUDIO_TRACK} '
            '-c:a aac -b:a 128k '
            '-y {OUTPUT}'
        )

        def on_log(level, msg):
            print(f"[{level}] {msg}")

        # Parse and substitute
        args = parse_and_substitute_command(
            template,
            input_file,
            output_file,
            audio_track=2,  # Second audio track
            subtitle_track=None,
            subtitle_file=None,
            on_log=on_log
        )

        print(f"Template:")
        print(f"  {template}")
        print()

        if not args:
            print("[FAIL] Command parsing returned empty args!")
            return False

        print(f"Parsed args ({len(args)} items):")
        for i, arg in enumerate(args):
            # Hide long paths for readability
            display_arg = arg[:50] + "..." if len(arg) > 50 else arg
            print(f"  [{i}] {display_arg}")
        print()

        # Verify substitutions
        checks = [
            ('ffmpeg' in args[0].lower(), "First arg is ffmpeg executable"),
            (str(input_file) in args, "Input file path in args"),
            (str(output_file) in args, "Output file path in args"),
            ('hevc_nvenc' in ' '.join(args), "Video codec specified"),
            ('-map' in ' '.join(args), "Stream mapping present"),
        ]

        all_pass = True
        for check, desc in checks:
            status = "[OK]" if check else "[FAIL]"
            print(f"{status} {desc}")
            if not check:
                all_pass = False

        print()
        if all_pass:
            print("SUCCESS: All command substitution tests passed!")
        else:
            print("FAIL: Some tests did not pass!")

        return all_pass

if __name__ == '__main__':
    success = test_command_substitution()
    sys.exit(0 if success else 1)
