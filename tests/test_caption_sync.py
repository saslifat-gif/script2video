from __future__ import annotations

import json
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import Mock, patch

from script2video.alignment import AlignedWord
from script2video.audio import audible_bounds
from script2video.capcut import create_capcut_package
from script2video.captions import build_srt
from script2video.config import ProjectConfig, SceneConfig
from script2video.engines.base import AudioChunk, AudioFormat
from script2video.engines.fake import FakeEngine
from script2video.errors import AlignmentError
from script2video.pipeline import render_project
from script2video.srt import parse_srt
from script2video.video import VideoInfo


class PaddedEngine(FakeEngine):
    def synthesize(self, request):
        # 200 ms silence, 400 ms audible PCM, 400 ms silence.
        return AudioChunk(
            bytes(400) + struct.pack("<h", 1000) * 400 + bytes(800),
            AudioFormat(sample_rate=1000),
        )


class CaptionSyncTests(unittest.TestCase):
    def project(self):
        return ProjectConfig(
            title="Sync",
            language="en-US",
            engine="fake",
            voice="test_narrator",
            scenes=[
                SceneConfig(id="first", text="First.", pause_after_ms=250),
                SceneConfig(id="second", text="Second."),
            ],
        )

    def test_subtitles_follow_sound_without_changing_audio_or_accumulating_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.txt"
            source.write_text("First. Second.")
            manifest = render_project(self.project(), source, root, PaddedEngine())
            cues = parse_srt(build_srt(self.project(), manifest))
            self.assertEqual(
                [(c.start_ms, c.end_ms) for c in cues], [(180, 620), (1430, 1870)]
            )
            self.assertEqual(manifest["audio"]["duration_samples"], 2250)
            with wave.open(str(root / "narration.wav")) as audio:
                expected = PaddedEngine().synthesize(None).pcm
                self.assertEqual(
                    audio.readframes(audio.getnframes()),
                    expected + bytes(500) + expected,
                )

    def test_silence_and_unsupported_formats_keep_original_span(self):
        for chunk in [
            AudioChunk(bytes(200), AudioFormat()),
            AudioChunk(bytes(100), AudioFormat(sample_width=1)),
        ]:
            self.assertEqual(audible_bounds(chunk), (0, chunk.sample_count))

    def test_quiet_speech_internal_pause_and_stereo_are_preserved(self):
        # Sound only in the right channel; an internal pause must remain intact.
        pcm = bytes(400) + struct.pack("<hh", 0, 10) * 100
        pcm += bytes(800) + struct.pack("<hh", 0, 10) * 100 + bytes(400)
        self.assertEqual(
            audible_bounds(AudioChunk(pcm, AudioFormat(sample_rate=1000, channels=2))),
            (80, 520),
        )

    def test_video_alignment_falls_back_for_drift_invalid_times_or_failure(self):
        cases = [
            [AlignedWord("First.", 0.18, 0.62), AlignedWord("Second.", 1.43, 1.87)],
            [AlignedWord("First.", 0.5, 0.9), AlignedWord("Second.", 1.75, 2.19)],
            [AlignedWord("First.", float("nan"), 0.6)],
            [AlignedWord("First.", 0.6, 0.2)],
            [],
            AlignmentError("Alignment unavailable"),
        ]
        for index, result in enumerate(cases):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "source.txt"
                source.write_text("First. Second.")
                aligner = Mock()
                aligner.identity.return_value = {"engine": "test"}
                if isinstance(result, Exception):
                    aligner.align.side_effect = result
                else:
                    aligner.align.return_value = result
                with patch(
                    "script2video.capcut.probe_video",
                    return_value=VideoInfo(root / "video.mp4", 2.25),
                ):
                    manifest = create_capcut_package(
                        self.project(),
                        source,
                        root / "video.mp4",
                        root,
                        PaddedEngine(),
                        fit_to_video=False,
                        aligner=aligner,
                    )
                self.assertEqual(manifest["capcut"]["alignment"]["enabled"], index == 0)
                self.assertEqual(bool(manifest["warnings"]), index != 0)
                if index:
                    cues = parse_srt((root / "captions.srt").read_text())
                    self.assertEqual(
                        [(c.start_ms, c.end_ms) for c in cues],
                        [(180, 620), (1430, 1870)],
                    )
                    persisted = json.loads((root / "manifest.json").read_text())
                    self.assertIn("fallback_reason", persisted["capcut"]["alignment"])
