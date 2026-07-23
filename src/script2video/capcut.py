from __future__ import annotations

from pathlib import Path
from typing import Any

from script2video.alignment import WordAligner
from script2video.captions import (
    build_srt,
    build_word_aligned_srt,
    split_caption_text,
    write_srt,
)
from script2video.config import ProjectConfig
from script2video.engines.base import TTSEngine
from script2video.errors import PackageError
from script2video.manifest import write_manifest
from script2video.pipeline import render_project
from script2video.video import probe_video


def create_capcut_package(
    project: ProjectConfig,
    input_path: Path,
    video_path: Path,
    output_dir: Path,
    engine: TTSEngine,
    fit_to_video: bool = True,
    aligner: WordAligner | None = None,
) -> dict[str, Any]:
    video = probe_video(video_path)
    manifest = render_project(
        project, input_path, output_dir, engine, segmenter=split_caption_text
    )
    initial_duration_ms = float(manifest["audio"]["duration_ms"])
    target_duration_ms = video.duration_seconds * 1000
    fitted_project = project
    speed_factor = 1.0
    fit_applied = False
    fit_iterations = 0

    while (
        fit_to_video
        and _relative_difference(
            float(manifest["audio"]["duration_ms"]), target_duration_ms
        )
        > 0.005
        and fit_iterations < 3
    ):
        correction = _fit_correction(manifest, video.duration_seconds)
        speed_factor *= correction
        fitted_scenes = []
        for scene in fitted_project.scenes:
            fitted_speed = scene.speed * correction
            if not 0.5 <= fitted_speed <= 2.0:
                raise PackageError(
                    "Narration cannot fit the video without exceeding Kokoro's safe "
                    f"speed range. Required speed for scene '{scene.id}': "
                    f"{fitted_speed:.2f}; allowed: 0.50-2.00."
                )
            fitted_scenes.append(
                scene.model_copy(update={"speed": round(fitted_speed, 4)})
            )
        fitted_project = fitted_project.model_copy(update={"scenes": fitted_scenes})
        manifest = render_project(
            fitted_project,
            input_path,
            output_dir,
            engine,
            segmenter=split_caption_text,
        )
        fit_applied = True
        fit_iterations += 1

    final_duration_ms = float(manifest["audio"]["duration_ms"])
    srt_name = "captions.srt"
    alignment_metadata: dict[str, Any] = {"enabled": False}
    if aligner is None:
        srt = build_srt(fitted_project, manifest)
    else:
        transcript = " ".join(scene.text for scene in fitted_project.scenes)
        aligned_words = aligner.align(
            output_dir / "narration.wav", transcript, fitted_project.language
        )
        srt = build_word_aligned_srt(aligned_words)
        alignment_metadata = {
            "enabled": True,
            **aligner.identity(),
            "word_count": len(aligned_words),
        }
    write_srt(output_dir / srt_name, srt)
    manifest["capcut"] = {
        "video_file": str(video.path),
        "video_duration_ms": round(target_duration_ms, 3),
        "captions_file": srt_name,
        "alignment": alignment_metadata,
        "fit": {
            "requested": fit_to_video,
            "applied": fit_applied,
            "iterations": fit_iterations,
            "converged": _relative_difference(final_duration_ms, target_duration_ms)
            <= 0.005,
            "speed_factor": round(speed_factor, 6),
            "initial_narration_duration_ms": initial_duration_ms,
            "final_narration_duration_ms": final_duration_ms,
            "difference_ms": round(final_duration_ms - target_duration_ms, 3),
        },
        "import": {
            "audio_start_ms": 0,
            "captions_start_ms": 0,
            "instructions": (
                "Import narration.wav as audio and captions.srt through CapCut "
                "Desktop's caption import, both starting at timeline zero."
            ),
        },
    }
    write_manifest(output_dir / "manifest.json", manifest)
    return manifest


def _relative_difference(first: float, second: float) -> float:
    return abs(first - second) / max(second, 1.0)


def _fit_correction(manifest: dict[str, Any], target_seconds: float) -> float:
    sample_rate = int(manifest["audio"]["sample_rate"])
    target_samples = round(target_seconds * sample_rate)
    pause_samples = sum(
        int(scene["pause_after_samples"]) for scene in manifest["scenes"]
    )
    current_speech_samples = int(manifest["audio"]["duration_samples"]) - pause_samples
    target_speech_samples = target_samples - pause_samples
    if target_speech_samples <= 0:
        raise PackageError(
            "The configured scene pauses are longer than the selected video."
        )
    return current_speech_samples / target_speech_samples
