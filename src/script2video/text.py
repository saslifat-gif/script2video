from __future__ import annotations

import re

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


def split_text_scenes(text: str) -> list[str]:
    """Split plain narration into sentence-sized scenes.

    Blank lines always end a scene. English and CJK sentence punctuation also
    end scenes, while common abbreviations and decimal points remain intact.
    """

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    scenes: list[str] = []
    for paragraph in re.split(r"\n\s*\n+", normalized):
        paragraph = " ".join(paragraph.split())
        if not paragraph:
            continue
        start = 0
        index = 0
        while index < len(paragraph):
            character = paragraph[index]
            if character not in ".!?。！？":
                index += 1
                continue

            punctuation_end = index + 1
            while (
                punctuation_end < len(paragraph)
                and paragraph[punctuation_end] in ".!?。！？"
            ):
                punctuation_end += 1

            if character == "." and not _period_ends_sentence(paragraph, index):
                index = punctuation_end
                continue

            end = punctuation_end
            while end < len(paragraph) and paragraph[end] in _CLOSING_MARKS:
                end += 1
            if (
                character not in "。！？"
                and end < len(paragraph)
                and not paragraph[end].isspace()
            ):
                index = punctuation_end
                continue

            sentence = paragraph[start:end].strip()
            if sentence:
                scenes.append(sentence)
            start = end
            while start < len(paragraph) and paragraph[start].isspace():
                start += 1
            index = start

        remainder = paragraph[start:].strip()
        if remainder:
            scenes.append(remainder)

    return scenes


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
