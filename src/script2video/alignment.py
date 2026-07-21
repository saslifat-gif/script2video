from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable, Protocol

from script2video.errors import AlignmentError

Transcriber = Callable[..., dict[str, Any]]

_LANGUAGES = {
    "en-US": "en",
    "en-GB": "en",
    "es-ES": "es",
    "fr-FR": "fr",
    "hi-IN": "hi",
    "it-IT": "it",
    "ja-JP": "ja",
    "pt-BR": "pt",
    "zh-CN": "zh",
}

_MODEL_REPOSITORIES = {
    "tiny.en": "mlx-community/whisper-tiny.en-mlx",
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base.en": "mlx-community/whisper-base.en-mlx",
    "base": "mlx-community/whisper-base-mlx",
}


@dataclass(frozen=True)
class AlignedWord:
    text: str
    start_seconds: float
    end_seconds: float


class WordAligner(Protocol):
    def align(self, audio_path: Path, text: str, language: str) -> list[AlignedWord]: ...

    def identity(self) -> dict[str, str]: ...


class MLXWhisperAligner:
    """Timestamp speech with MLX Whisper and reconcile it to the exact script."""

    def __init__(
        self,
        model_name: str = "tiny.en",
        transcriber: Transcriber | None = None,
    ) -> None:
        self.model_name = model_name
        self._transcriber = transcriber

    def identity(self) -> dict[str, str]:
        return {
            "engine": "mlx-whisper",
            "backend": "apple-silicon",
            "model": self.model_name,
        }

    def align(self, audio_path: Path, text: str, language: str) -> list[AlignedWord]:
        language_code = _LANGUAGES.get(language)
        if language_code is None:
            raise AlignmentError(
                f"MLX Whisper does not recognize project language '{language}'."
            )
        if language_code != "en" and self.model_name.endswith(".en"):
            raise AlignmentError(
                f"Alignment model '{self.model_name}' is English-only. "
                "Use a multilingual model such as 'tiny'."
            )
        repository = _MODEL_REPOSITORIES.get(self.model_name, self.model_name)
        try:
            if self._transcriber is None:
                recognized = self._align_in_isolated_worker(
                    audio_path, text, language_code, repository
                )
            else:
                result = self._transcriber(
                    str(audio_path),
                    path_or_hf_repo=repository,
                    language=language_code,
                    initial_prompt=text,
                    word_timestamps=True,
                    verbose=None,
                )
                recognized = _extract_words(result)
        except Exception as exc:
            raise AlignmentError(f"MLX Whisper alignment failed: {exc}") from exc

        if not recognized:
            raise AlignmentError("MLX Whisper returned no word timestamps")
        return reconcile_script_words(text, recognized)

    def _align_in_isolated_worker(
        self, audio_path: Path, text: str, language: str, repository: str
    ) -> list[AlignedWord]:
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "script2video.alignment_worker"],
                input=json.dumps(
                    {
                        "audio_path": str(audio_path.resolve()),
                        "text": text,
                        "language": language,
                        "repository": repository,
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            raise AlignmentError(
                f"Could not start isolated MLX Whisper worker: {exc}"
            ) from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()
            message = detail[-1] if detail else "worker exited without an error message"
            if "No module named 'mlx_whisper'" in completed.stderr:
                message = (
                    "AI word alignment is not installed. Install it with: "
                    "pip install -e '.[alignment]'"
                )
            raise AlignmentError(f"Isolated MLX Whisper worker failed: {message}")
        try:
            payload = json.loads(completed.stdout)
            return [
                AlignedWord(
                    str(word["text"]),
                    float(word["start_seconds"]),
                    float(word["end_seconds"]),
                )
                for word in payload["words"]
            ]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AlignmentError("MLX Whisper worker returned invalid timing data") from exc


def reconcile_script_words(
    script: str, recognized: list[AlignedWord]
) -> list[AlignedWord]:
    """Preserve script text while borrowing timestamps from recognized words."""
    script_words = re.findall(r"\S+", script)
    if not script_words:
        return []

    script_keys = [_normalise_word(word, index) for index, word in enumerate(script_words)]
    recognized_keys = [
        _normalise_word(word.text, index) for index, word in enumerate(recognized)
    ]
    timings: list[tuple[float, float] | None] = [None] * len(script_words)
    matcher = SequenceMatcher(None, script_keys, recognized_keys, autojunk=False)
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            source_index = block.a + offset
            recognized_word = recognized[block.b + offset]
            timings[source_index] = (
                recognized_word.start_seconds,
                recognized_word.end_seconds,
            )

    recognized_end = max(word.end_seconds for word in recognized)
    cursor = 0
    while cursor < len(timings):
        if timings[cursor] is not None:
            cursor += 1
            continue
        gap_start = cursor
        while cursor < len(timings) and timings[cursor] is None:
            cursor += 1
        gap_end = cursor
        left = timings[gap_start - 1][1] if gap_start else 0.0
        right = timings[gap_end][0] if gap_end < len(timings) else recognized_end
        if right <= left:
            right = left + 0.01 * (gap_end - gap_start)
        step = (right - left) / (gap_end - gap_start)
        for offset, index in enumerate(range(gap_start, gap_end)):
            timings[index] = (left + step * offset, left + step * (offset + 1))

    aligned: list[AlignedWord] = []
    previous_end = 0.0
    for word, timing in zip(script_words, timings, strict=True):
        assert timing is not None
        start = max(previous_end, timing[0])
        end = max(start + 0.001, timing[1])
        aligned.append(AlignedWord(word, start, end))
        previous_end = end
    return aligned


def _normalise_word(word: str, index: int) -> str:
    normalized = "".join(character for character in word.casefold() if character.isalnum())
    return normalized or f"__punctuation_{index}"


def _extract_words(result: Any) -> list[AlignedWord]:
    segments = result.get("segments", []) if isinstance(result, dict) else []
    words: list[AlignedWord] = []
    for segment in segments:
        segment_words = segment.get("words", []) if isinstance(segment, dict) else []
        for word in segment_words:
            if not isinstance(word, dict):
                continue
            text = str(word.get("word", word.get("text", ""))).strip()
            start = word.get("start")
            end = word.get("end")
            if not text or start is None or end is None:
                continue
            start_value = float(start)
            end_value = float(end)
            if end_value > start_value:
                words.append(AlignedWord(text, start_value, end_value))
    words.sort(key=lambda item: (item.start_seconds, item.end_seconds))
    return words


# Compatibility for code written during the M3 preview.
StableTSAligner = MLXWhisperAligner
