from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from script2video.errors import VideoProbeError

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class VideoInfo:
    path: Path
    duration_seconds: float
    width: int | None = None
    height: int | None = None


def probe_video(path: Path, runner: CommandRunner = subprocess.run) -> VideoInfo:
    if not path.is_file():
        raise VideoProbeError(f"Video file does not exist: {path}")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=width,height",
        "-select_streams",
        "v:0",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = runner(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise VideoProbeError(
            "ffprobe was not found. Install FFmpeg before creating a CapCut package."
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown ffprobe error"
        raise VideoProbeError(f"Could not inspect video '{path}': {detail}")
    try:
        payload: dict[str, Any] = json.loads(result.stdout)
        duration = float(payload["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VideoProbeError(f"Video '{path}' has no readable duration") from exc
    if duration <= 0:
        raise VideoProbeError(f"Video '{path}' has an invalid duration: {duration}")
    streams = payload.get("streams", [])
    video_stream = streams[0] if streams and isinstance(streams[0], dict) else {}
    width = _positive_int_or_none(video_stream.get("width"))
    height = _positive_int_or_none(video_stream.get("height"))
    return VideoInfo(
        path=path.resolve(),
        duration_seconds=duration,
        width=width,
        height=height,
    )


def _positive_int_or_none(value: object) -> int | None:
    if not isinstance(value, int | str):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None
