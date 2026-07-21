from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import typer

from script2video.alignment import MLXWhisperAligner
from script2video.capcut import create_capcut_package
from script2video.config import load_project
from script2video.engines.base import TTSEngine
from script2video.engines.fake import FakeEngine
from script2video.engines.kokoro import KokoroEngine
from script2video.errors import EngineUnavailableError, Script2VideoError
from script2video.pipeline import render_project

app = typer.Typer(
    no_args_is_help=True,
    help="Turn structured scripts into narration assets.",
)


def get_engine(name: str) -> TTSEngine:
    if name == "fake":
        return FakeEngine()
    if name == "kokoro":
        return KokoroEngine()
    raise EngineUnavailableError(
        f"Unknown engine '{name}'. Available engines: fake, kokoro"
    )


@app.command()
def validate(script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)]) -> None:
    """Validate a YAML script without rendering audio."""
    try:
        project = load_project(script)
    except Script2VideoError as exc:
        _fail(exc, code=2)
    typer.echo(f"Valid: {project.title} ({len(project.scenes)} scenes)")


@app.command()
def voices(
    engine: Annotated[str, typer.Option("--engine", "-e")] = "fake",
) -> None:
    """List voices exposed by a TTS engine."""
    try:
        selected = get_engine(engine)
    except Script2VideoError as exc:
        _fail(exc, code=3)
    for voice in selected.list_voices():
        typer.echo(f"{voice.id}\t{voice.name}\t{', '.join(voice.languages)}")


@app.command()
def render(
    script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Build output directory.")
    ],
    engine: Annotated[
        str | None,
        typer.Option("--engine", "-e", help="Override the engine in the script."),
    ] = None,
    voice: Annotated[
        str | None,
        typer.Option("--voice", "-v", help="Override the default script voice."),
    ] = None,
) -> None:
    """Render scene WAV files, combined narration, and a timing manifest."""
    try:
        project = load_project(script)
        if voice is not None:
            project = project.model_copy(update={"voice": voice})
        selected = get_engine(engine or project.engine)
        manifest = render_project(project, script, output, selected)
    except Script2VideoError as exc:
        _fail(exc, code=4)
    typer.echo(
        f"Rendered {len(manifest['scenes'])} scenes to {output} "
        f"({manifest['audio']['duration_ms']} ms)"
    )


@app.command("capcut")
def capcut_package(
    script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    video: Annotated[
        Path, typer.Option("--video", help="Video whose duration narration should match.")
    ],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="CapCut package directory.")
    ],
    engine: Annotated[
        str | None, typer.Option("--engine", "-e", help="Override script engine.")
    ] = None,
    voice: Annotated[
        str | None, typer.Option("--voice", "-v", help="Override script voice.")
    ] = None,
    fit: Annotated[
        bool, typer.Option("--fit/--no-fit", help="Fit narration to video duration.")
    ] = True,
    align: Annotated[
        bool,
        typer.Option(
            "--align/--no-align", help="AI-align the known script at word level."
        ),
    ] = True,
    align_model: Annotated[
        str, typer.Option("--align-model", help="MLX Whisper model name.")
    ] = "tiny.en",
) -> None:
    """Create narration, editable SRT captions, and metadata for CapCut."""
    try:
        project = load_project(script)
        if voice is not None:
            project = project.model_copy(update={"voice": voice})
        selected = get_engine(engine or project.engine)
        aligner = MLXWhisperAligner(model_name=align_model) if align else None
        manifest = create_capcut_package(
            project,
            script,
            video,
            output,
            selected,
            fit_to_video=fit,
            aligner=aligner,
        )
    except Script2VideoError as exc:
        _fail(exc, code=5)
    capcut = manifest["capcut"]
    typer.echo(
        f"Created CapCut package in {output}: narration.wav + captions.srt "
        f"({capcut['fit']['final_narration_duration_ms']} ms)"
    )


@app.command()
def companion() -> None:
    """Open the always-on-top CapCut companion window."""
    from script2video.companion import run_companion

    run_companion()


def _fail(error: Exception, code: int) -> NoReturn:
    typer.echo(f"Error: {error}", err=True)
    raise typer.Exit(code=code)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
