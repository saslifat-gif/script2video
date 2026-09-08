from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from script2video.alignment import AlignedWord, WordAligner
from script2video.captions import (
    build_srt,
    build_word_aligned_srt,
    split_caption_text,
    write_srt,
)
from script2video.config import ProjectConfig
from script2video.engines.base import TTSEngine
from script2video.errors import AlignmentError, PackageError
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
    converged = _relative_difference(final_duration_ms, target_duration_ms) <= 0.005
    if fit_to_video and not converged:
        difference_seconds = (final_duration_ms - target_duration_ms) / 1000
        direction = "longer" if difference_seconds > 0 else "shorter"
        manifest["warnings"].append(
            f"Narration is {abs(difference_seconds):.2f} seconds {direction} than "
            f"the video after {fit_iterations} fitting attempts. "
            "Review the timing in CapCut before using this package."
        )
    srt_name = "captions.srt"
    alignment_metadata: dict[str, Any] = {"enabled": False}
    if aligner is None:
        srt = build_srt(fitted_project, manifest)
    else:
        transcript = " ".join(scene.text for scene in fitted_project.scenes)
        try:
            aligned_words = aligner.align(
                output_dir / "narration.wav", transcript, fitted_project.language
            )
            if not _alignment_matches_segments(aligned_words, manifest):
                raise AlignmentError(
                    "AI timestamps disagree with the measured narration segments"
                )
            srt = build_word_aligned_srt(aligned_words)
            alignment_metadata = {
                "enabled": True,
                **aligner.identity(),
                "word_count": len(aligned_words),
            }
        except AlignmentError as exc:
            srt = build_srt(fitted_project, manifest)
            alignment_metadata = {
                "enabled": False,
                "requested": True,
                **aligner.identity(),
                "fallback_reason": str(exc),
            }
            manifest["warnings"].append(
                "AI alignment could not provide reliable timing. "
                "Captions use the measured narration segments instead."
            )
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
            "converged": converged,
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


def _alignment_matches_segments(
    words: list[AlignedWord], manifest: dict[str, Any]
) -> bool:
    """Reject global transcript drift using independently rendered audio anchors."""
    sample_rate = int(manifest["audio"]["sample_rate"])
    duration = int(manifest["audio"]["duration_samples"]) / sample_rate
    previous_end = 0.0
    for word in words:
        if (
            not math.isfinite(word.start_seconds)
            or not math.isfinite(word.end_seconds)
            or word.start_seconds < previous_end
            or word.end_seconds <= word.start_seconds
            or word.end_seconds > duration
        ):
            return False
        previous_end = word.end_seconds
    cursor = 0
    for scene in manifest["scenes"]:
        for segment in scene["segments"]:
            count = len(str(segment["text"]).split())
            group = words[cursor : cursor + count]
            if len(group) != count or not group:
                return False
            start = int(segment.get("audible_start_sample", segment["start_sample"]))
            end = int(segment.get("audible_end_sample", segment["end_sample"]))
            # Small boundary differences are expected from speech recognition;
            # crossing an independently measured segment by >150 ms is not.
            if (
                abs(group[0].start_seconds - start / sample_rate) > 0.150
                or abs(group[-1].end_seconds - end / sample_rate) > 0.150
            ):
                return False
            cursor += count
    return cursor == len(words) and cursor > 0
