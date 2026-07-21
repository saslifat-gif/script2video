from __future__ import annotations

import hashlib
import math
import struct

from script2video.engines.base import (
    AudioChunk,
    AudioFormat,
    EngineIdentity,
    SynthesisRequest,
    Voice,
)


class FakeEngine:
    """Deterministic tone generator used for development and tests."""

    _format = AudioFormat()
    _voices = (
        Voice("test_narrator", "Test Narrator", ("en-US", "en-GB")),
        Voice("test_low", "Test Narrator (Low)", ("en-US", "en-GB")),
    )

    def list_voices(self) -> list[Voice]:
        return list(self._voices)

    def identity(self) -> EngineIdentity:
        return EngineIdentity(name="fake", version="1", model="deterministic-tone")

    def synthesize(self, request: SynthesisRequest) -> AudioChunk:
        voices = {voice.id for voice in self._voices}
        if request.voice not in voices:
            available = ", ".join(sorted(voices))
            raise ValueError(
                f"Unknown fake voice '{request.voice}'. Available voices: {available}"
            )

        digest = hashlib.sha256(
            f"{request.text}|{request.voice}|{request.seed}".encode()
        ).digest()
        base_frequency = 180 if request.voice == "test_low" else 260
        frequency = base_frequency + digest[0] % 80
        duration_seconds = max(0.25, min(4.0, len(request.text) * 0.025))
        duration_seconds /= request.speed
        sample_count = round(duration_seconds * self._format.sample_rate)
        amplitude = 5_000

        frames = bytearray(sample_count * self._format.sample_width)
        fade_samples = min(round(self._format.sample_rate * 0.02), sample_count // 2)
        for index in range(sample_count):
            envelope = 1.0
            if fade_samples:
                envelope = min(1.0, index / fade_samples)
                envelope = min(envelope, (sample_count - index - 1) / fade_samples)
            sample = round(
                amplitude
                * envelope
                * math.sin(2 * math.pi * frequency * index / self._format.sample_rate)
            )
            struct.pack_into("<h", frames, index * 2, sample)

        return AudioChunk(pcm=bytes(frames), format=self._format)
