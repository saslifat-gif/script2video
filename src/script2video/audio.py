from __future__ import annotations

import os
import sys
import tempfile
import wave
from array import array
from io import BytesIO
from pathlib import Path

from script2video.engines.base import AudioChunk, AudioFormat


def silence(sample_count: int, audio_format: AudioFormat) -> bytes:
    frame_width = audio_format.channels * audio_format.sample_width
    return bytes(sample_count * frame_width)


def audible_bounds(chunk: AudioChunk) -> tuple[int, int]:
    """Locate audible PCM boundaries without removing audio or internal pauses.

    This conservative amplitude gate is for generated 16-bit PCM, not speech
    recognition. Keep 20 ms around the detected sound to protect quiet onsets
    and endings; unsupported formats and silent chunks retain their full span.
    """
    count = chunk.sample_count
    if chunk.format.sample_width != 2 or count == 0:
        return 0, count
    samples = array("h")
    samples.frombytes(chunk.pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    peak = max(abs(sample) for sample in samples)
    threshold = max(4, peak * 0.002)
    first = next(
        (i for i, sample in enumerate(samples) if abs(sample) >= threshold), None
    )
    if first is None:
        return 0, count
    last = next(
        i for i in range(len(samples) - 1, -1, -1) if abs(samples[i]) >= threshold
    )
    channels = chunk.format.channels
    padding = round(chunk.format.sample_rate * 0.020)
    return max(0, first // channels - padding), min(
        count, last // channels + 1 + padding
    )


def write_wav(path: Path, chunk: AudioChunk) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        with wave.open(str(temporary_path), "wb") as output:
            output.setnchannels(chunk.format.channels)
            output.setsampwidth(chunk.format.sample_width)
            output.setframerate(chunk.format.sample_rate)
            output.writeframes(chunk.pcm)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def wav_bytes(chunk: AudioChunk) -> bytes:
    """Return an audio chunk as a complete in-memory WAV file."""

    buffer = BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(chunk.format.channels)
        output.setsampwidth(chunk.format.sample_width)
        output.setframerate(chunk.format.sample_rate)
        output.writeframes(chunk.pcm)
    return buffer.getvalue()
