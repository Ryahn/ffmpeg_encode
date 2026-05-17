"""Unit tests for output container helpers."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import output_container as oc


class TestOutputContainer(unittest.TestCase):
    def test_normalize_container(self) -> None:
        self.assertEqual(oc.normalize_container("mkv"), "mkv")
        self.assertEqual(oc.normalize_container("M4V"), "m4v")
        self.assertEqual(oc.normalize_container(".webm"), "webm")
        self.assertEqual(oc.normalize_container(""), "mp4")
        self.assertEqual(oc.normalize_container("bogus"), "mp4")

    def test_file_extension(self) -> None:
        self.assertEqual(oc.file_extension_for_container("mp4"), ".mp4")
        self.assertEqual(oc.file_extension_for_container("mov"), ".mov")

    def test_handbrake_format(self) -> None:
        self.assertEqual(oc.handbrake_format_for_container("mp4"), "av_mp4")
        self.assertEqual(oc.handbrake_format_for_container("m4v"), "av_mp4")
        self.assertEqual(oc.handbrake_format_for_container("mov"), "av_mp4")
        self.assertEqual(oc.handbrake_format_for_container("mkv"), "av_mkv")
        self.assertEqual(oc.handbrake_format_for_container("webm"), "av_webm")

    def test_default_from_handbrake_format(self) -> None:
        self.assertEqual(oc.default_container_from_handbrake_format("av_mp4"), "mp4")
        self.assertEqual(oc.default_container_from_handbrake_format("av_mkv"), "mkv")
        self.assertEqual(oc.default_container_from_handbrake_format("av_webm"), "webm")
        self.assertEqual(oc.default_container_from_handbrake_format(None), "mp4")

    def test_iso_bmff_extension(self) -> None:
        self.assertTrue(oc.iso_bmff_extension(".mp4"))
        self.assertTrue(oc.iso_bmff_extension("m4v"))
        self.assertFalse(oc.iso_bmff_extension(".mkv"))

    def test_subtitle_compat_container(self) -> None:
        self.assertEqual(oc.subtitle_compat_container("m4v"), "mp4")
        self.assertEqual(oc.subtitle_compat_container("mov"), "mp4")
        self.assertEqual(oc.subtitle_compat_container("mkv"), "mkv")
        self.assertEqual(oc.subtitle_compat_container("mp4"), "mp4")


if __name__ == "__main__":
    unittest.main()
