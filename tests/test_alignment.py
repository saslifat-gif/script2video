from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from script2video.alignment import (
    AlignedWord,
    MLXWhisperAligner,
    reconcile_script_words,
)
from script2video.captions import build_word_aligned_srt


class AlignmentTests(unittest.TestCase):
    def test_mlx_adapter_uses_timestamps_but_preserves_script(self) -> None:
        calls: list[dict[str, Any]] = []

        def transcribe(audio: str, **options: Any) -> dict[str, object]:
            calls.append({"audio": audio, **options})
            return {
                "segments": [
                    {
                        "words": [
                            {"word": " Hello", "start": 0.2, "end": 0.6},
                            {"word": " world", "start": 0.65, "end": 1.0},
                        ]
                    }
                ]
            }

        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "audio.wav"
            audio.touch()
            aligner = MLXWhisperAligner("tiny.en", transcriber=transcribe)
            words = aligner.align(audio, "Hello world!", "en-US")

        self.assertEqual([word.text for word in words], ["Hello", "world!"])
        self.assertEqual(words[0].start_seconds, 0.2)
        self.assertEqual(words[1].end_seconds, 1.0)
        self.assertEqual(
            calls[0]["path_or_hf_repo"], "mlx-community/whisper-tiny.en-mlx"
        )
        self.assertTrue(calls[0]["word_timestamps"])

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
