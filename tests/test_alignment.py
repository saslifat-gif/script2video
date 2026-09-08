from __future__ import annotations

import unittest

from script2video.alignment import (
    AlignedWord,
    reconcile_script_words,
)
from script2video.captions import build_word_aligned_srt


class AlignmentTests(unittest.TestCase):
    def test_reconciles_recognition_mismatch_without_losing_script_words(self) -> None:
        recognized = [
            AlignedWord("Mine", 0.0, 0.2),
            AlignedWord("craft", 0.2, 0.45),
            AlignedWord("changed", 0.5, 0.9),
            AlignedWord("gaming", 1.0, 1.4),
        ]

        words = reconcile_script_words("Minecraft changed gaming.", recognized)

        self.assertEqual(
            [word.text for word in words], ["Minecraft", "changed", "gaming."]
        )
        self.assertEqual(words[0].end_seconds, 0.5)
        self.assertEqual(words[1].start_seconds, 0.5)
        self.assertEqual(words[-1].end_seconds, 1.4)

    def test_builds_short_word_timed_caption_cues(self) -> None:
        words = [
            AlignedWord("Hello", 0.2, 0.6),
            AlignedWord("world!", 0.65, 1.1),
            AlignedWord("Next", 2.0, 2.3),
            AlignedWord("phrase.", 2.35, 2.8),
        ]

        srt = build_word_aligned_srt(words)

        self.assertIn("00:00:00,200 --> 00:00:01,100", srt)
        self.assertIn("Hello world!", srt)
        self.assertIn("00:00:02,000 --> 00:00:02,800", srt)
        self.assertIn("Next phrase.", srt)


if __name__ == "__main__":
    unittest.main()
