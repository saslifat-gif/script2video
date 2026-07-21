from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AudioFormat:
    sample_rate: int = 24_000
    channels: int = 1
    sample_width: int = 2


@dataclass(frozen=True)
class AudioChunk:
    pcm: bytes
    format: AudioFormat

    @property
    def sample_count(self) -> int:
        frame_width = self.format.channels * self.format.sample_width
        return len(self.pcm) // frame_width


@dataclass(frozen=True)
class Voice:
    id: str
    name: str
    languages: tuple[str, ...]


@dataclass(frozen=True)
class EngineIdentity:
    name: str
    version: str
    model: str


@dataclass(frozen=True)
class SynthesisRequest:
    text: str
    language: str
    voice: str
    speed: float = 1.0
    seed: int | None = None


class TTSEngine(Protocol):
    def list_voices(self) -> list[Voice]: ...

    def synthesize(self, request: SynthesisRequest) -> AudioChunk: ...

    def identity(self) -> EngineIdentity: ...
