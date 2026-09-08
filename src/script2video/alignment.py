from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class AlignedWord:
    text: str
    start_seconds: float
    end_seconds: float


class WordAligner(Protocol):
    def align(
        self, audio_path: Path, text: str, language: str
    ) -> list[AlignedWord]: ...

    def identity(self) -> dict[str, str]: ...


def reconcile_script_words(
    script: str, recognized: list[AlignedWord]
) -> list[AlignedWord]:
    """Preserve script text while borrowing timestamps from recognized words."""
    script_words = re.findall(r"\S+", script)
    if not script_words:
        return []

    script_keys = [
        _normalise_word(word, index) for index, word in enumerate(script_words)
    ]
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
    normalized = "".join(
        character for character in word.casefold() if character.isalnum()
    )
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
