from __future__ import annotations

import struct
import unittest

import numpy as np

from script2video.engines.base import SynthesisRequest
from script2video.engines.kokoro import KokoroEngine


class StubPipeline:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(
        self, text: str, *, voice: str, speed: float, split_pattern: str
    ) -> object:
        self.calls.append(
            {
                "text": text,
                "voice": voice,
                "speed": speed,
                "split_pattern": split_pattern,
            }
        )
        yield text, "phonemes", np.array([-1.0, 0.0, 0.5, 1.0], dtype=np.float32)


class KokoroEngineTests(unittest.TestCase):
    def test_converts_kokoro_float_audio_to_pcm16(self) -> None:
        created: list[tuple[str, StubPipeline]] = []

        def factory(*, lang_code: str, repo_id: str) -> StubPipeline:
            self.assertEqual(repo_id, "hexgrad/Kokoro-82M")
            pipeline = StubPipeline()
            created.append((lang_code, pipeline))
            return pipeline

        engine = KokoroEngine(pipeline_factory=factory)
        chunk = engine.synthesize(
            SynthesisRequest(
                text="Hello from Kokoro.",
                language="en-US",
                voice="af_heart",
                speed=1.1,
            )
        )

        self.assertEqual(created[0][0], "a")
        self.assertEqual(chunk.format.sample_rate, 24_000)
        self.assertEqual(chunk.sample_count, 4)
        self.assertEqual(struct.unpack("<4h", chunk.pcm), (-32767, 0, 16383, 32767))
        self.assertEqual(created[0][1].calls[0]["voice"], "af_heart")
        self.assertEqual(created[0][1].calls[0]["speed"], 1.1)

    def test_reuses_pipeline_for_same_language(self) -> None:
        creations = 0

        def factory(*, lang_code: str, repo_id: str) -> StubPipeline:
            nonlocal creations
            creations += 1
            return StubPipeline()

        engine = KokoroEngine(pipeline_factory=factory)
        request = SynthesisRequest(
            text="Hello.", language="en-US", voice="af_heart"
        )
        engine.synthesize(request)
        engine.synthesize(request)

        self.assertEqual(creations, 1)

    def test_rejects_voice_from_wrong_language(self) -> None:
        engine = KokoroEngine(pipeline_factory=lambda **_: StubPipeline())
        with self.assertRaisesRegex(ValueError, "does not match language"):
            engine.synthesize(
                SynthesisRequest(
                    text="Hello.", language="en-US", voice="bf_emma"
                )
            )

    def test_lists_all_official_voices_without_loading_model(self) -> None:
        engine = KokoroEngine(
            pipeline_factory=lambda **_: self.fail("should not load pipeline")
        )
        voices = engine.list_voices()

        self.assertEqual(len(voices), 54)
        self.assertIn("af_heart", {voice.id for voice in voices})
        self.assertIn("zf_xiaoxiao", {voice.id for voice in voices})


if __name__ == "__main__":
    unittest.main()
