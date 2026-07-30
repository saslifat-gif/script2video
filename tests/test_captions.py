from __future__ import annotations

import unittest

from script2video.captions import (
    build_srt,
    format_srt_timestamp,
    split_caption_text,
    wrap_caption_two_lines,
)
from script2video.config import ProjectConfig


class CaptionTests(unittest.TestCase):
    def test_formats_srt_timestamps(self) -> None:
        self.assertEqual(format_srt_timestamp(36_000, 24_000), "00:00:01,500")
        self.assertEqual(format_srt_timestamp(24_000 * 3_661, 24_000), "01:01:01,000")

    def test_splits_long_text_into_readable_blocks(self) -> None:
        parts = split_caption_text(
            "This is the first sentence. This second sentence contains many more "
            "words and should become multiple readable caption blocks."
        )
        self.assertGreaterEqual(len(parts), 2)
        self.assertTrue(all(len(part) <= 84 for part in parts))

    def test_wraps_caption_into_at_most_two_balanced_lines(self) -> None:
        caption = wrap_caption_two_lines(
            "This caption is long enough that it should display on two balanced lines."
        )
        lines = caption.splitlines()

        self.assertEqual(len(lines), 2)
        self.assertLessEqual(abs(len(lines[0]) - len(lines[1])), 10)

    def test_builds_subtitles_within_scene_speech_timing(self) -> None:
        project = ProjectConfig.model_validate(
            {
                "title": "Captions",
                "language": "en-US",
                "engine": "fake",
                "voice": "test_narrator",
                "scenes": [
                    {
                        "id": "intro",
                        "text": "First sentence. Second sentence.",
                    }
                ],
            }
        )
        manifest = {
            "audio": {"sample_rate": 24_000},
            "scenes": [{"id": "intro", "start_sample": 0, "speech_end_sample": 48_000}],
        }

        srt = build_srt(project, manifest)

        self.assertIn("First sentence.", srt)
        self.assertIn("Second sentence.", srt)
        self.assertIn("00:00:02,000", srt)

    def test_uses_exact_rendered_segment_boundaries_when_available(self) -> None:
        project = ProjectConfig.model_validate(
            {
                "title": "Exact Captions",
                "language": "en-US",
                "engine": "fake",
                "voice": "test_narrator",
                "scenes": [{"id": "intro", "text": "First. Second."}],
            }
        )
        manifest = {
            "audio": {"sample_rate": 24_000},
            "scenes": [
                {
                    "id": "intro",
                    "start_sample": 0,
                    "speech_end_sample": 48_000,
                    "segments": [
                        {"text": "First.", "start_sample": 0, "end_sample": 12_000},
                        {
                            "text": "Second.",
                            "start_sample": 12_000,
                            "end_sample": 48_000,
                        },
                    ],
                }
            ],
        }

        srt = build_srt(project, manifest)

        self.assertIn("00:00:00,000 --> 00:00:00,500", srt)
        self.assertIn("00:00:00,500 --> 00:00:02,000", srt)

    def test_long_exact_segment_becomes_multiple_readable_cards(self) -> None:
        text = (
            "I just downloaded the AMD GPU version and Windows Defender says "
            "that it contains a warning, but I cannot tell whether the result "
            "is safe or a false positive."
        )
        project = ProjectConfig.model_validate(
            {
                "title": "Readable captions",
                "language": "en-US",
                "engine": "fake",
                "voice": "test_narrator",
                "scenes": [{"id": "intro", "text": text}],
            }
        )
        manifest = {
            "audio": {"sample_rate": 24_000},
            "scenes": [
                {
                    "id": "intro",
                    "start_sample": 0,
                    "speech_end_sample": 240_000,
                    "segments": [
                        {
                            "text": text,
                            "start_sample": 0,
                            "end_sample": 240_000,
                        }
                    ],
                }
            ],
        }

        blocks = build_srt(project, manifest).strip().split("\n\n")

        self.assertGreaterEqual(len(blocks), 3)
        for block in blocks:
            caption_lines = block.splitlines()[2:]
            self.assertLessEqual(len(caption_lines), 2)
            self.assertLessEqual(max(map(len, caption_lines)), 40)


if __name__ == "__main__":
    unittest.main()
