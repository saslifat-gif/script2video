# Stage 1 design: script to narration

## 1. Goal

Build a local CLI that accepts a structured video script, synthesizes every
spoken scene with an open-source TTS engine, joins the results, and records
accurate timing metadata for later video assembly.

Stage 1 produces audio and timing data only. Images, B-roll, subtitles burned
into video, transitions, background music, and final video rendering belong to
later stages.

## 2. Product decisions

### Default engine: Kokoro

Use Kokoro as the first engine because it is lightweight, fast enough for local
iteration, and its model weights use Apache 2.0. Its main limitation is language
and voice coverage, so the application must not embed Kokoro-specific concepts
outside the engine adapter.

Do not make voice cloning part of the first milestone. Cloning introduces
heavier models, reference-audio management, consent requirements, and licensing
constraints. It can be introduced later as another engine capability.

### Local-first, batch-first

The MVP is a command-line batch processor rather than a web application. This
keeps model setup and debugging visible, makes runs reproducible, and gives a
future UI or API a stable core to call.

### WAV as the canonical output

Generate lossless PCM WAV during processing. Compressed delivery formats can be
created later. All scene audio is normalized to the same sample rate, channel
count, and sample format before concatenation.

## 3. User workflow

```text
YAML script
    -> schema validation
    -> text cleanup and chunking
    -> TTS engine synthesis
    -> scene WAV files
    -> silence/pause insertion
    -> loudness normalization
    -> combined narration.wav
    -> manifest.json with exact timings
```

Suggested commands:

```bash
script2video voices --engine kokoro
script2video validate examples/demo.yaml
script2video render examples/demo.yaml --output builds/demo
script2video render examples/demo.yaml --scene intro --force
```

## 4. Input contract

Use YAML because scripts are edited by people and benefit from comments and
multiline text. Each scene has a stable ID so a changed scene can be regenerated
without invalidating the rest of the project.

Required project fields:

- `title`: human-readable project name.
- `language`: BCP 47-style language code, initially `en-US` or `en-GB`.
- `engine`: engine adapter name.
- `voice`: default engine voice ID.
- `scenes`: ordered list of spoken scenes.

Required scene fields:

- `id`: unique, filename-safe identifier.
- `text`: narration to speak.

Optional scene fields:

- `voice`: override the project voice.
- `speed`: speaking-speed multiplier.
- `pause_after_ms`: silence to append after the scene.
- `notes`: production notes ignored by TTS.

Reject unknown fields initially. A strict schema catches spelling mistakes and
prevents silently incorrect renders.

## 5. Output contract

For an input named `demo.yaml`, a successful build looks like:

```text
builds/demo/
  narration.wav
  manifest.json
  scenes/
    001-intro.wav
    002-explanation.wav
  cache/
    <content-hash>.wav
```

The manifest should include:

- application version;
- engine name and model/version identifier;
- input file hash;
- output audio format;
- scene order, text hash, voice, speed, start time, end time, and duration;
- warnings and render timestamp.

Timing values should be stored as integer samples as the source of truth, with
milliseconds included for convenience. Integer samples avoid accumulated
floating-point drift during later video synchronization.

## 6. Architecture

Recommended language: Python 3.11 or newer.

```text
src/script2video/
  cli.py                 command definitions
  config.py              YAML loading and validated models
  pipeline.py            render orchestration
  text.py                cleanup and sentence-aware chunking
  audio.py               format conversion, silence, concatenation
  manifest.py            build metadata and timing
  cache.py               content-addressed audio cache
  engines/
    base.py              TTS engine protocol
    kokoro.py            initial adapter
tests/
  unit/
  integration/
```

The engine boundary should expose a small contract:

```python
class TTSEngine(Protocol):
    def list_voices(self) -> list[Voice]: ...
    def synthesize(self, request: SynthesisRequest) -> AudioChunk: ...
    def identity(self) -> EngineIdentity: ...
```

`SynthesisRequest` contains normalized text, language, voice, speed, and an
optional deterministic seed. `AudioChunk` contains PCM samples and audio-format
metadata. The adapter must not write final project files; the pipeline owns all
paths and output policy.

Suggested libraries:

- `typer` for the CLI;
- `pydantic` for strict input validation;
- `PyYAML` for input parsing;
- `numpy` and `soundfile` for PCM handling;
- `kokoro` as an optional engine dependency;
- `pytest` for tests;
- `ruff` and `mypy` for static checks.

Keep FFmpeg available for later export and diagnostics, but do not require a
subprocess for ordinary WAV concatenation.

## 7. Text processing

TTS quality depends heavily on chunking. Normalize whitespace, preserve useful
punctuation, and split at sentence boundaries before falling back to clause or
word boundaries. Combine very short adjacent sentences when safe, since tiny
utterances can sound less natural. Never silently rewrite words.

Store both original and normalized text hashes in the manifest. Log a warning
when text is unusually short, unusually long, empty after normalization, or
contains characters unsupported by the selected language frontend.

## 8. Caching and reproducibility

The cache key should hash all inputs that can change synthesized audio:

```text
engine identity + model identity + normalized text + language + voice + speed
+ seed + audio format
```

Model versions should be pinned. A normal rerun reuses cached scene audio; the
`--force` flag bypasses the cache. Cache writes must be atomic so an interrupted
render cannot leave a valid-looking partial file.

## 9. Error handling

Fail before synthesis when the script is invalid. During synthesis, report the
scene ID and preserve completed cached scenes. Never produce `narration.wav` or
mark the manifest successful if any required scene failed.

Use distinct nonzero exit codes for invalid input, unavailable engine/model,
synthesis failure, and output failure so automation can respond appropriately.

## 10. Responsible voice use

The MVP ships only with voices distributed by the selected model. Any future
voice-cloning feature should require the user to confirm that they own or have
permission to use the reference voice. Record the reference asset hash and
consent acknowledgement in provenance metadata. Do not imitate a public figure
by default.

## 11. Milestones

### M1: Walking skeleton

- package layout and CLI;
- strict YAML validation;
- a fake engine used by fast tests;
- scene output and manifest generation.

### M2: Local Kokoro rendering

- Kokoro adapter and voice listing;
- sentence-aware chunking;
- scene WAV generation and concatenation;
- Apple Silicon setup documentation.

### M3: Production reliability

- content-addressed cache;
- loudness normalization and peak protection;
- atomic builds and useful exit codes;
- integration tests using a very short real render.

## 12. Stage 1 acceptance criteria

- A new user can install the project and render the example on Apple Silicon.
- The command works without a hosted service or API key.
- Invalid scripts fail with the exact field and scene that caused the problem.
- Every scene has its own WAV and exact start/end timing in the manifest.
- Unchanged scenes are not synthesized again on the second run.
- The combined file has consistent format and no clipping at scene joins.
- The same pinned model and configuration produce structurally identical build
  metadata, excluding the render timestamp.
- Unit tests do not download or initialize a real TTS model.

## 13. Explicitly deferred

- graphical editor or web API;
- voice cloning and custom voice training;
- subtitle alignment at the word level;
- background music and sound effects;
- stock-media search or image/video generation;
- final MP4 rendering.
