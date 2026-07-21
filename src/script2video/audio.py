from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path

from script2video.engines.base import AudioChunk, AudioFormat


def silence(sample_count: int, audio_format: AudioFormat) -> bytes:
    frame_width = audio_format.channels * audio_format.sample_width
    return bytes(sample_count * frame_width)


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
