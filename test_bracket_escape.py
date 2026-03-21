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

        # Check that brackets are properly escaped
        command_str = ' '.join(args)

        # The escaped brackets should be \[ and \] within the quoted path
        has_escaped_brackets = r'\[' in command_str and r'\]' in command_str

        if has_escaped_brackets:
            print("[OK] Square brackets are properly escaped")
            return True
        else:
            print("[FAIL] Square brackets are NOT properly escaped")
            print(f"Command: {command_str}")
            return False

if __name__ == '__main__':
    success = test_bracket_escape()
    sys.exit(0 if success else 1)
