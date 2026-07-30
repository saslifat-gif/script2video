from __future__ import annotations

import unittest
import wave
from io import BytesIO

from script2video.audio import wav_bytes
from script2video.engines.base import SynthesisRequest
from script2video.engines.fake import FakeEngine


class AudioTests(unittest.TestCase):
    def test_audio_chunk_can_be_served_as_a_complete_wav(self) -> None:
        chunk = FakeEngine().synthesize(
            SynthesisRequest(
                text="Voice preview",
                language="en-US",
                voice="test_narrator",
            )
        )

        encoded = wav_bytes(chunk)
        self.assertTrue(encoded.startswith(b"RIFF"))
        with wave.open(BytesIO(encoded), "rb") as preview:
            self.assertEqual(preview.getframerate(), chunk.format.sample_rate)
            self.assertEqual(preview.getnframes(), chunk.sample_count)


if __name__ == "__main__":
    unittest.main()
