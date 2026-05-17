"""Tests for audio track selection (issue #2: untagged single audio, HandBrake index)."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.track_analyzer import TrackAnalyzer
from core.track_selection import (
    audio_mkv_stream_id_for_ordinal,
    compute_effective_tracks,
    handbrake_audio_track_index,
)

# Minimal mkvinfo-shaped output: one untagged audio stream (Doc Brown sample shape).
_DOC_BROWN_MKVINFO = """
|  + Track number: 1 (track ID for mkvmerge & mkvextract: 0)
|  + Track type: video
|  + Track number: 2 (track ID for mkvmerge & mkvextract: 1)
|  + Track type: audio
|  + Track number: 3 (track ID for mkvmerge & mkvextract: 2)
|  + Track type: subtitles
|  + Language: spa
"""


class TestTrackSelection(unittest.TestCase):
    def setUp(self):
        self.analyzer = TrackAnalyzer()

    def test_untagged_single_audio_uses_first_without_japanese_mode(self):
        tracks = self.analyzer._parse_mkvinfo_output(_DOC_BROWN_MKVINFO)
        self.assertIsNone(tracks["audio"])
        self.assertEqual(tracks["first_audio"], 1)
        with patch("core.track_selection.config") as mock_cfg:
            mock_cfg.get_allow_japanese_audio_with_english_subs.return_value = False
            audio, _sub = compute_effective_tracks(tracks, self.analyzer)
        self.assertEqual(audio, 1)

    def test_handbrake_audio_index_is_audio_ordinal_not_mkv_id(self):
        tracks = self.analyzer._parse_mkvinfo_output(_DOC_BROWN_MKVINFO)
        with patch("core.track_selection.config") as mock_cfg:
            mock_cfg.get_allow_japanese_audio_with_english_subs.return_value = False
            audio, _sub = compute_effective_tracks(tracks, self.analyzer)
        stream_id = audio_mkv_stream_id_for_ordinal(tracks, audio)
        self.assertEqual(stream_id, 1)
        self.assertEqual(handbrake_audio_track_index(audio), 1)
        self.assertNotEqual(handbrake_audio_track_index(audio), stream_id + 1)

    def test_two_audio_no_english_skips_without_japanese_mode(self):
        mkvinfo = _DOC_BROWN_MKVINFO + """
|  + Track number: 4 (track ID for mkvmerge & mkvextract: 3)
|  + Track type: audio
|  + Language: jpn
"""
        tracks = self.analyzer._parse_mkvinfo_output(mkvinfo)
        with patch("core.track_selection.config") as mock_cfg:
            mock_cfg.get_allow_japanese_audio_with_english_subs.return_value = False
            audio, _sub = compute_effective_tracks(tracks, self.analyzer)
        self.assertIsNone(audio)

    @unittest.skipUnless(
        Path(__file__).parent.parent.joinpath("2015 Message from Doc Brown.mkv").is_file(),
        "sample MKV not present",
    )
    def test_doc_brown_sample_integration(self):
        sample = Path(__file__).parent.parent / "2015 Message from Doc Brown.mkv"
        tracks = self.analyzer.analyze_tracks(sample)
        with patch("core.track_selection.config") as mock_cfg:
            mock_cfg.get_allow_japanese_audio_with_english_subs.return_value = False
            audio, _sub = compute_effective_tracks(tracks, self.analyzer, source_label=sample.name)
        self.assertEqual(audio, 1)
        self.assertEqual(handbrake_audio_track_index(audio), 1)


if __name__ == "__main__":
    unittest.main()
