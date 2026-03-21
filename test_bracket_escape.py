#!/usr/bin/env python
"""Test that square brackets in file paths are properly escaped."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / 'src'))

from gui.tabs.ffmpeg_command_util import parse_and_substitute_command
import tempfile

def test_bracket_escape():
    """Test that square brackets are escaped in FFmpeg commands."""
    print("Testing square bracket escaping...")
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create a file with square brackets in the name
        input_file = tmpdir / "[Judas] Test - S01E01.mkv"
        output_file = tmpdir / "[Judas] Test - S01E01_encoded.mp4"
        input_file.touch()

        # Template with {INPUT} and {OUTPUT} placeholders
        template = 'ffmpeg -i {INPUT} -c:v hevc_nvenc -cq 28 -y {OUTPUT}'

        def on_log(level, msg):
            print(f"[{level}] {msg}")

        # Parse and substitute
        args = parse_and_substitute_command(
            template,
            input_file,
            output_file,
            audio_track=1,
            subtitle_track=None,
            subtitle_file=None,
            on_log=on_log
        )

        print()
        print(f"Input file: {input_file.name}")
        print(f"Output file: {output_file.name}")
        print()
        print("Generated FFmpeg arguments:")
        for i, arg in enumerate(args):
            display = arg[:60] + "..." if len(arg) > 60 else arg
            print(f"  [{i:2d}] {display}")
        print()

        # Check that the file path with brackets is properly handled
        command_str = ' '.join(args)

        # The path should be quoted (because it's in a temp directory with brackets)
        # and brackets should NOT be escaped inside quotes (quotes protect them)
        has_quoted_path = '[Judas]' in command_str and '"' in command_str

        # Verify the path is the actual file (not double-escaped like \\[)
        has_correct_path = '[Judas] Test' in command_str
        has_no_double_escape = r'\\[' not in command_str

        if has_quoted_path and has_correct_path and has_no_double_escape:
            print("[OK] Brackets are properly handled (quoted, not escaped)")
            return True
        else:
            print("[FAIL] Bracket handling is incorrect")
            print(f"Command: {command_str}")
            print(f"  - Quoted path: {has_quoted_path}")
            print(f"  - Correct path: {has_correct_path}")
            print(f"  - No double escape: {has_no_double_escape}")
            return False

if __name__ == '__main__':
    success = test_bracket_escape()
    sys.exit(0 if success else 1)
