from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from script2video.config import ProjectConfig, SceneConfig
from script2video.errors import ScriptLoadError

_TIMING_LINE = re.compile(
    r"^\s*(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{3})(?:\s+.*)?$"
)
_HTML_TAG = re.compile(r"<[^>]+>")
_ASS_TAG = re.compile(r"\{\\[^}]+\}")


@dataclass(frozen=True)
class SrtCue:
    number: int
    start_ms: int
    end_ms: int
    text: str


def parse_srt(contents: str) -> list[SrtCue]:
    normalized = contents.removeprefix("\ufeff").replace("\r\n", "\n").replace(
        "\r", "\n"
    )
    blocks = re.split(r"\n[ \t]*\n+", normalized.strip())
    cues: list[SrtCue] = []
    for block_number, block in enumerate(blocks, start=1):
        lines = [line.rstrip() for line in block.splitlines()]
        if not any(line.strip() for line in lines):
            continue
        timing_index = next(
            (index for index, line in enumerate(lines[:2]) if _TIMING_LINE.match(line)),
            None,
        )
        if timing_index is None:
            raise ScriptLoadError(
                f"Invalid SRT cue {block_number}: expected a timestamp line"
            )
        match = _TIMING_LINE.match(lines[timing_index])
        if match is None:  # pragma: no cover - guarded by timing_index
            raise ScriptLoadError(f"Invalid SRT cue {block_number}")
        start_ms = _parse_timestamp(match.group("start"), block_number)
        end_ms = _parse_timestamp(match.group("end"), block_number)
        if end_ms <= start_ms:
            raise ScriptLoadError(
                f"Invalid SRT cue {block_number}: end time must be after start time"
            )
        cue_text = _clean_cue_text(lines[timing_index + 1 :])
        if not cue_text:
            raise ScriptLoadError(f"Invalid SRT cue {block_number}: text is empty")
        cues.append(
            SrtCue(
                number=len(cues) + 1,
                start_ms=start_ms,
                end_ms=end_ms,
                text=cue_text,
            )
        )
    if not cues:
        raise ScriptLoadError("SRT file contains no subtitle cues")
    return cues


def load_srt_project(
    path: Path,
    language: str,
    engine: str,
    voice: str,
) -> ProjectConfig:
    cues = load_srt_cues(path)
    return _project_from_cues(cues, language, engine, voice, title=path.stem)


def load_srt_cues(path: Path) -> list[SrtCue]:
    if path.suffix.lower() != ".srt":
        raise ScriptLoadError(f"Subtitle script must be an .srt file: {path}")
    try:
        contents = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ScriptLoadError(
            f"SRT file must use UTF-8 encoding: '{path}'"
        ) from exc
    except OSError as exc:
        raise ScriptLoadError(f"Could not read SRT script '{path}': {exc}") from exc
    return parse_srt(contents)


def project_from_srt(
    contents: str,
    language: str,
    engine: str,
    voice: str,
    title: str = "Imported subtitles",
) -> ProjectConfig:
    return _project_from_cues(
        parse_srt(contents), language, engine, voice, title=title
    )


def _project_from_cues(
    cues: list[SrtCue],
    language: str,
    engine: str,
    voice: str,
    title: str,
) -> ProjectConfig:
    scenes: list[SceneConfig] = []
    for index, cue in enumerate(cues):
        next_start = cues[index + 1].start_ms if index + 1 < len(cues) else cue.end_ms
        pause_after_ms = min(60_000, max(0, next_start - cue.end_ms))
        scenes.append(
            SceneConfig(
                id=f"subtitle-{cue.number:03d}",
                text=cue.text,
                pause_after_ms=pause_after_ms,
                notes=(
                    f"Imported SRT timing: {cue.start_ms}ms-{cue.end_ms}ms"
                ),
            )
        )
    try:
        return ProjectConfig(
            title=title.strip() or "Imported subtitles",
            language=language,
            engine=engine,
            voice=voice,
            scenes=scenes,
        )
    except ValidationError as exc:
        raise ScriptLoadError(f"Invalid SRT narration settings: {exc}") from exc


def _parse_timestamp(value: str, cue_number: int) -> int:
    match = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})", value)
    if match is None:
        raise ScriptLoadError(f"Invalid timestamp in SRT cue {cue_number}: {value}")
    hours, minutes, seconds, milliseconds = (int(part) for part in match.groups())
    if minutes >= 60 or seconds >= 60:
        raise ScriptLoadError(f"Invalid timestamp in SRT cue {cue_number}: {value}")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds


def _clean_cue_text(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines if line.strip())
    text = _ASS_TAG.sub("", text)
    text = _HTML_TAG.sub("", text)
    return " ".join(html.unescape(text).split())
