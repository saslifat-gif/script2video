from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from script2video.errors import VideoProbeError

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class VideoInfo:
    path: Path
    duration_seconds: float


def probe_video(path: Path, runner: CommandRunner = subprocess.run) -> VideoInfo:
    if not path.is_file():
        raise VideoProbeError(f"Video file does not exist: {path}")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
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
    return VideoInfo(path=path.resolve(), duration_seconds=duration)
