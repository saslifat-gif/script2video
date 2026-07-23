from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from script2video import __version__
from script2video.audio import silence, write_wav
from script2video.config import ProjectConfig
from script2video.engines.base import (
    AudioChunk,
    AudioFormat,
    SynthesisRequest,
    TTSEngine,
)
from script2video.errors import RenderError
from script2video.manifest import write_manifest


def render_project(
    project: ProjectConfig,
    input_path: Path,
    output_dir: Path,
    engine: TTSEngine,
    segmenter: Callable[[str], list[str]] | None = None,
) -> dict[str, Any]:
    identity = engine.identity()
    audio_format: AudioFormat | None = None
    combined_pcm = bytearray()
    scene_records: list[dict[str, Any]] = []
    scenes_dir = output_dir / "scenes"

    for position, scene in enumerate(project.scenes, start=1):
        voice = scene.voice or project.voice
        segment_texts = segmenter(scene.text) if segmenter else [scene.text]
        if not segment_texts:
            raise RenderError(f"Scene '{scene.id}' produced no narration segments")
        scene_pcm = bytearray()
        segment_records: list[dict[str, Any]] = []
        start_sample: int | None = None

        for segment_index, segment_text in enumerate(segment_texts, start=1):
            request = SynthesisRequest(
                text=segment_text,
                language=project.language,
                voice=voice,
                speed=scene.speed,
            )
            try:
                chunk = engine.synthesize(request)
            except Exception as exc:
                raise RenderError(
                    f"Scene '{scene.id}' segment {segment_index} synthesis "
                    f"failed: {exc}"
                ) from exc

            if audio_format is None:
                audio_format = chunk.format
            elif chunk.format != audio_format:
                raise RenderError(
                    f"Scene '{scene.id}' returned an inconsistent audio format"
                )
            if start_sample is None:
                start_sample = len(combined_pcm) // (
                    audio_format.channels * audio_format.sample_width
                )
            segment_start = start_sample + len(scene_pcm) // (
                audio_format.channels * audio_format.sample_width
            )
            segment_end = segment_start + chunk.sample_count
            segment_records.append(
                {
                    "text": segment_text,
                    "start_sample": segment_start,
                    "end_sample": segment_end,
                    "start_ms": _samples_to_ms(segment_start, audio_format.sample_rate),
                    "end_ms": _samples_to_ms(segment_end, audio_format.sample_rate),
                }
            )
            scene_pcm.extend(chunk.pcm)

        if audio_format is None or start_sample is None:
            raise RenderError(f"Scene '{scene.id}' returned no audio")
        scene_chunk = AudioChunk(pcm=bytes(scene_pcm), format=audio_format)
        speech_end_sample = start_sample + scene_chunk.sample_count
        pause_samples = round(scene.pause_after_ms * audio_format.sample_rate / 1000)
        end_sample = speech_end_sample + pause_samples
        filename = f"{position:03d}-{scene.id}.wav"
        write_wav(scenes_dir / filename, scene_chunk)
        combined_pcm.extend(scene_chunk.pcm)
        combined_pcm.extend(silence(pause_samples, audio_format))

        scene_records.append(
            {
                "id": scene.id,
                "file": f"scenes/{filename}",
                "text_sha256": hashlib.sha256(scene.text.encode()).hexdigest(),
                "voice": voice,
                "speed": scene.speed,
                "start_sample": start_sample,
                "speech_end_sample": speech_end_sample,
                "end_sample": end_sample,
                "duration_samples": end_sample - start_sample,
                "pause_after_samples": pause_samples,
                "start_ms": _samples_to_ms(start_sample, audio_format.sample_rate),
                "speech_end_ms": _samples_to_ms(
                    speech_end_sample, audio_format.sample_rate
                ),
                "end_ms": _samples_to_ms(end_sample, audio_format.sample_rate),
                "segments": segment_records,
            }
        )

    if audio_format is None:
        raise RenderError("The project contains no renderable scenes")

    narration = AudioChunk(pcm=bytes(combined_pcm), format=audio_format)
    write_wav(output_dir / "narration.wav", narration)
    manifest: dict[str, Any] = {
        "status": "success",
        "application_version": __version__,
        "rendered_at": datetime.now(UTC).isoformat(),
        "project": {"title": project.title, "language": project.language},
        "input": {
            "file": str(input_path),
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        },
        "engine": {
            "name": identity.name,
            "version": identity.version,
            "model": identity.model,
        },
        "audio": {
            "file": "narration.wav",
            "sample_rate": audio_format.sample_rate,
            "channels": audio_format.channels,
            "sample_width_bytes": audio_format.sample_width,
            "duration_samples": narration.sample_count,
            "duration_ms": _samples_to_ms(
                narration.sample_count, audio_format.sample_rate
            ),
        },
        "scenes": scene_records,
        "warnings": [],
    }
    write_manifest(output_dir / "manifest.json", manifest)
    return manifest


def _samples_to_ms(samples: int, sample_rate: int) -> float:
    return round(samples * 1000 / sample_rate, 3)
