#!/usr/bin/env python
"""Test command preview generation with proper placeholder substitution."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / 'src'))

from gui.tabs.ffmpeg_command_util import generate_command_preview, parse_and_substitute_command

def test_preview_generation():
    """Test that command preview properly replaces placeholders."""
    print("Testing command preview generation...")
    print()

    # Test with a template that uses {INPUT} and {OUTPUT} placeholders
    template = 'ffmpeg -i {INPUT} -c:v hevc_nvenc -cq 28 -preset p5 -y {OUTPUT}'

    # Mock callbacks
    def get_files():
        return [{'path': Path('test_input.mkv'), 'audio_track': 2, 'subtitle_track': None}]

    def get_output_path(source):
        return source.parent

    # Generate preview
    preview = generate_command_preview(template, get_files, get_output_path, '_encoded')

    print(f"Template: {template}")
    print()
    print(f"Preview: {preview}")
    print()

    # Verify that placeholders were replaced
    if '{INPUT}' not in preview and '{OUTPUT}' not in preview:
        print("[OK] Placeholders replaced successfully")
    else:
        print("[FAIL] Placeholders were not replaced!")
        return False

    # Verify that actual paths are present
    if 'test_input.mkv' in preview and 'test_input_encoded.mp4' in preview:
        print("[OK] Actual file paths present in preview")
    else:
        print("[FAIL] File paths not found in preview!")
        return False

    print()
    print("SUCCESS: All preview generation tests passed!")
    return True

if __name__ == '__main__':
    success = test_preview_generation()
    sys.exit(0 if success else 1)
