from __future__ import annotations

import re
from typing import Literal

SceneSplitMode = Literal["sentence", "paragraph", "line", "whole"]
SCENE_SPLIT_MODES: tuple[SceneSplitMode, ...] = (
    "sentence",
    "paragraph",
    "line",
    "whole",
)

_CLOSING_MARKS = '"\'”’)]}】》」』'
_ABBREVIATIONS = {
    "dr",
    "e.g",
    "etc",
    "i.e",
    "jr",
    "mr",
    "mrs",
    "ms",
    "prof",
    "sr",
    "st",
    "vs",
}


def split_text_scenes(
    text: str, mode: SceneSplitMode = "sentence"
) -> list[str]:
    """Split plain narration using the selected scene pattern.

    Sentence mode ignores layout newlines and uses English/CJK punctuation.
    Other modes preserve explicit paragraph or line choices, or keep the whole
    script together.
    """

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    if mode not in SCENE_SPLIT_MODES:
        choices = ", ".join(SCENE_SPLIT_MODES)
        raise ValueError(f"Scene split mode must be one of: {choices}")

    if mode == "whole":
        return [_clean_scene_text(normalized)]
    if mode == "line":
        return [
            _clean_scene_text(line)
            for line in normalized.splitlines()
            if line.strip()
        ]
    if mode == "paragraph":
        return [
            _clean_scene_text(paragraph)
            for paragraph in re.split(r"\n\s*\n+", normalized)
            if paragraph.strip()
        ]

    scenes: list[str] = []
    narration = _clean_scene_text(normalized)
    start = 0
    index = 0
    while index < len(narration):
        character = narration[index]
        if character not in ".!?。！？":
            index += 1
            continue

        punctuation_end = index + 1
        while (
            punctuation_end < len(narration)
            and narration[punctuation_end] in ".!?。！？"
        ):
            punctuation_end += 1

        if character == "." and not _period_ends_sentence(narration, index):
            index = punctuation_end
            continue

        end = punctuation_end
        while end < len(narration) and narration[end] in _CLOSING_MARKS:
            end += 1
        if (
            character not in "。！？"
            and end < len(narration)
            and not narration[end].isspace()
        ):
            index = punctuation_end
            continue

        sentence = narration[start:end].strip()
        if sentence:
            scenes.append(sentence)
        start = end
        while start < len(narration) and narration[start].isspace():
            start += 1
        index = start

    remainder = narration[start:].strip()
    if remainder:
        scenes.append(remainder)

    return scenes


def _clean_scene_text(text: str) -> str:
    return " ".join(text.split())


def _period_ends_sentence(text: str, index: int) -> bool:
    if index > 0 and index + 1 < len(text):
        if text[index - 1].isdigit() and text[index + 1].isdigit():
            return False

    prefix = text[:index]
    match = re.search(r"([A-Za-z](?:[A-Za-z.]*)?)$", prefix)
    token = match.group(1).lower() if match else ""
    if token in _ABBREVIATIONS:
        return False
    if len(token) == 1 and token.isalpha():
        return False
    return True
