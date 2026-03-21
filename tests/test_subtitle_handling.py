"""Unit tests for subtitle handling system"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.encoder import (
    SubtitleInfo, SubtitleDecision, can_mux_to_container,
    TEXT_SUBTITLE_CODECS, BITMAP_SUBTITLE_CODECS
)
from core.subtitle_policy import decide_subtitle_action


class TestSubtitleInfo(unittest.TestCase):
    """Test SubtitleInfo data class"""

    def test_init(self):
        """Test SubtitleInfo initialization"""
        info = SubtitleInfo()
        self.assertIsNone(info.external_text)
        self.assertIsNone(info.external_ass)
        self.assertEqual(info.embedded, [])
        self.assertFalse(info.has_any)

    def test_has_any_with_external_text(self):
        """Test has_any property with external text"""
        info = SubtitleInfo()
        info.external_text = Path("test.srt")
        self.assertTrue(info.has_any)

    def test_has_any_with_embedded(self):
        """Test has_any property with embedded"""
        info = SubtitleInfo()
        info.embedded.append({"index": 0, "codec": "subrip", "type": "text"})
        self.assertTrue(info.has_any)


class TestSubtitleDecision(unittest.TestCase):
    """Test SubtitleDecision class"""

    def test_init_defaults(self):
        """Test SubtitleDecision initialization"""
        decision = SubtitleDecision()
        self.assertEqual(decision.action, "omit")
        self.assertEqual(decision.reason, "No subtitles found")
        self.assertEqual(decision.warnings, [])
        self.assertIsNone(decision.source)
        self.assertIsNone(decision.stream_index)

    def test_init_with_params(self):
        """Test SubtitleDecision with parameters"""
        decision = SubtitleDecision("mux", "Test reason")
        self.assertEqual(decision.action, "mux")
        self.assertEqual(decision.reason, "Test reason")


class TestContainerCompatibility(unittest.TestCase):
    """Test container subtitle compatibility checker"""

    def test_subrip_to_mp4(self):
        """Test SRT to MP4 compatibility"""
        supported, method, warning = can_mux_to_container("subrip", "mp4")
        self.assertTrue(supported)
        self.assertEqual(method, "mov_text")
        self.assertIsNone(warning)

    def test_ass_to_mp4(self):
        """Test ASS to MP4 compatibility"""
        supported, method, warning = can_mux_to_container("ass", "mp4")
        self.assertTrue(supported)
        self.assertEqual(method, "mov_text")
        self.assertIsNotNone(warning)

    def test_pgssub_to_mp4(self):
        """Test PGS to MP4 incompatibility"""
        supported, method, warning = can_mux_to_container("pgssub", "mp4")
        self.assertFalse(supported)
        self.assertIsNone(method)
        self.assertIsNotNone(warning)

    def test_pgssub_to_mkv(self):
        """Test PGS to MKV compatibility"""
        supported, method, warning = can_mux_to_container("pgssub", "mkv")
        self.assertTrue(supported)
        self.assertEqual(method, "copy")


class TestSubtitlePolicy(unittest.TestCase):
    """Test subtitle policy decision engine"""

    def setUp(self):
        """Set up test config"""
        self.config = {
            "subtitle_handling": {
                "pgs": "omit",
                "embedded_text": "mux",
                "embedded_ass": "external",
                "external_text": "keep",
                "external_ass": "keep",
                "subtitle_source_priority": ["external", "embedded"]
            },
            "warn_on_ass_mux": True,
            "warn_on_burn": True
        }

    def test_no_subtitles(self):
        """Test decision with no subtitles"""
        info = SubtitleInfo()
        decision = decide_subtitle_action(info, self.config)
        self.assertEqual(decision.action, "omit")
        self.assertEqual(decision.reason, "No subtitles found")

    def test_external_text_preferred(self):
        """Test external text subtitles are preferred"""
        info = SubtitleInfo()
        info.external_text = Path("test.srt")
        info.embedded.append({"index": 0, "codec": "ass", "type": "text"})

        decision = decide_subtitle_action(info, self.config)
        self.assertEqual(decision.action, "keep")
        self.assertEqual(decision.source, "external_text")

    def test_embedded_text_with_no_external(self):
        """Test embedded text when no external"""
        info = SubtitleInfo()
        info.embedded.append({"index": 0, "codec": "subrip", "type": "text"})

        decision = decide_subtitle_action(info, self.config)
        self.assertEqual(decision.action, "mux")
        self.assertEqual(decision.source, "embedded_text")

    def test_embedded_ass_uses_external_action(self):
        """Test embedded ASS uses external action"""
        info = SubtitleInfo()
        info.embedded.append({"index": 0, "codec": "ass", "type": "text"})

        decision = decide_subtitle_action(info, self.config)
        self.assertEqual(decision.action, "external")
        self.assertEqual(decision.source, "embedded_ass")

    def test_ass_mux_warning(self):
        """Test warning for ASS muxing"""
        info = SubtitleInfo()
        info.embedded.append({"index": 0, "codec": "ass", "type": "text"})

        # Change policy to mux ASS
        config = self.config.copy()
        config["subtitle_handling"]["embedded_ass"] = "mux"

        decision = decide_subtitle_action(info, config)
        self.assertEqual(decision.action, "mux")
        self.assertGreater(len(decision.warnings), 0)
        self.assertIn("styling", decision.warnings[0].lower())

    def test_pgs_omit_decision(self):
        """Test PGS omit decision"""
        info = SubtitleInfo()
        info.embedded.append({"index": 0, "codec": "pgssub", "type": "bitmap"})

        decision = decide_subtitle_action(info, self.config)
        self.assertEqual(decision.action, "omit")
        self.assertEqual(decision.source, "embedded_bitmap")

    def test_pgs_skip_decision(self):
        """Test PGS skip decision"""
        info = SubtitleInfo()
        info.embedded.append({"index": 0, "codec": "pgssub", "type": "bitmap"})

        config = self.config.copy()
        config["subtitle_handling"]["pgs"] = "skip_file"

        decision = decide_subtitle_action(info, config)
        self.assertEqual(decision.action, "skip_file")

    def test_burn_warning(self):
        """Test burn action generates warning"""
        info = SubtitleInfo()
        info.embedded.append({"index": 0, "codec": "subrip", "type": "text"})

        config = self.config.copy()
        config["subtitle_handling"]["embedded_text"] = "burn"

        decision = decide_subtitle_action(info, config)
        self.assertEqual(decision.action, "burn")
        self.assertGreater(len(decision.warnings), 0)
        self.assertIn("transcod", decision.warnings[0].lower())


if __name__ == '__main__':
    unittest.main()
