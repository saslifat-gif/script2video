from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

from script2video.alignment import AlignedWord
from script2video.config import ProjectConfig

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def build_srt(project: ProjectConfig, manifest: dict[str, Any]) -> str:
    sample_rate = int(manifest["audio"]["sample_rate"])
    entries: list[tuple[int, int, str]] = []
    manifest_scenes = {scene["id"]: scene for scene in manifest["scenes"]}

    for scene in project.scenes:
        timing = manifest_scenes[scene.id]
        exact_segments = timing.get("segments")
        if exact_segments:
            for segment in exact_segments:
                entries.append(
                    (
                        int(segment["start_sample"]),
                        int(segment["end_sample"]),
                        wrap_caption_two_lines(str(segment["text"])),
                    )
                )
            continue
        parts = split_caption_text(scene.text)
        start_sample = int(timing["start_sample"])
        end_sample = int(timing["speech_end_sample"])
        duration = end_sample - start_sample
        weights = [max(1, len(re.sub(r"\s+", "", part))) for part in parts]
        total_weight = sum(weights)
        cursor = start_sample
        consumed_weight = 0
        for index, (part, weight) in enumerate(zip(parts, weights, strict=True)):
            consumed_weight += weight
            part_end = (
                end_sample
                if index == len(parts) - 1
                else start_sample + round(duration * consumed_weight / total_weight)
            )
            entries.append(
                (cursor, max(cursor + 1, part_end), wrap_caption_two_lines(part))
            )
            cursor = part_end

    blocks = []
    for number, (start, end, text) in enumerate(entries, start=1):
        blocks.append(
            f"{number}\n"
            f"{format_srt_timestamp(start, sample_rate)} --> "
            f"{format_srt_timestamp(end, sample_rate)}\n"
            f"{text}"
        )
    return "\n\n".join(blocks) + "\n"


def split_caption_text(
    text: str, max_words: int = 16, max_chars: int = 84
) -> list[str]:
    sentences = _SENTENCE_BOUNDARY.split(" ".join(text.split()))
    parts: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        for word in sentence.split():
            candidate = " ".join([*current, word])
            if current and (len(current) >= max_words or len(candidate) > max_chars):
                parts.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
    if current:
        parts.append(" ".join(current))
    return parts or [text.strip()]


def wrap_caption_two_lines(text: str, line_target: int = 42) -> str:
    if len(text) <= line_target:
        return text
    words = text.split()
    if len(words) < 2:
        return text
    best_index = 1
    best_score: tuple[int, int] | None = None
    for index in range(1, len(words)):
        first = " ".join(words[:index])
        second = " ".join(words[index:])
        score = (max(len(first), len(second)), abs(len(first) - len(second)))
        if best_score is None or score < best_score:
            best_score = score
            best_index = index
    return " ".join(words[:best_index]) + "\n" + " ".join(words[best_index:])


def format_srt_timestamp(samples: int, sample_rate: int) -> str:
    return format_srt_milliseconds(round(samples * 1000 / sample_rate))


def format_srt_seconds(seconds: float) -> str:
    return format_srt_milliseconds(round(seconds * 1000))


def format_srt_milliseconds(total_ms: int) -> str:
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def build_word_aligned_srt(
    words: list[AlignedWord], max_words: int = 8, max_chars: int = 72
) -> str:
    if not words:
        return ""
    groups: list[list[AlignedWord]] = []
    current: list[AlignedWord] = []
    for word in words:
        candidate = _join_words([*current, word])
        gap = word.start_seconds - current[-1].end_seconds if current else 0.0
        if current and (
            len(current) >= max_words or len(candidate) > max_chars or gap >= 0.6
        ):
            groups.append(current)
            current = [word]
        else:
            current.append(word)
    if current:
        groups.append(current)

    blocks = []
    for number, group in enumerate(groups, start=1):
        text = wrap_caption_two_lines(_join_words(group), line_target=max_chars // 2)
        blocks.append(
            f"{number}\n"
            f"{format_srt_seconds(group[0].start_seconds)} --> "
            f"{format_srt_seconds(group[-1].end_seconds)}\n"
            f"{text}"
        )
    return "\n\n".join(blocks) + "\n"


def _join_words(words: list[AlignedWord]) -> str:
    result = ""
    attach = set(".,!?;:%)]}’'\"")
    for word in words:
        token = word.text.strip()
        if not result:
            result = token
        elif token and token[0] in attach:
            result += token
        else:
            result += " " + token
    return result


def write_srt(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(contents)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
