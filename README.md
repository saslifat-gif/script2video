# script2video

Local-first tools for turning a structured YAML script into narration, timed
captions, and an editable CapCut package.

`script2video` runs speech generation and alignment on your machine. It can
render narration scene by scene, fit the result to an existing video, and
produce standard WAV, SRT, and JSON files without modifying CapCut project
files.

![Script2Video companion workspace](docs/script2video-companion.png)

## Open the companion UI

After installation, launch the desktop companion with the CLI command:

```bash
script2video companion
```

From a source checkout, you can open it directly without activating the virtual
environment:

```bash
.venv/bin/script2video companion
```

You can also use Python's module entry point:

```bash
.venv/bin/python -m script2video companion
```

All three methods open the same local, always-on-top workspace. Choose a YAML
script, source video, and output folder, then select **Generate CapCut Package**.

## Deploy locally

`script2video` is a local CLI and macOS companion rather than a hosted web
service. A typical deployment is an isolated Python environment on the machine
where you edit video.

You need Python 3.11, plus `ffprobe` for the CapCut workflow. MLX Whisper
alignment requires a Mac with Apple Silicon.

```bash
git clone https://github.com/saslifat-gif/script2video.git
cd script2video

brew install ffmpeg espeak-ng
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[kokoro,alignment]"
```

The first render downloads the selected Kokoro model and voice from Hugging
Face. The first aligned render also downloads the selected Whisper model.
Later runs reuse the local caches.

## Quick start

Validate the example script, inspect the available voices, and render
narration:

```bash
script2video validate examples/demo.yaml
script2video voices --engine kokoro
script2video render examples/demo.yaml --output builds/demo
```

To create narration and subtitles fitted to an existing video:

```bash
script2video capcut examples/minecraft.yaml \
  --video /path/to/video.mp4 \
  --output builds/minecraft-capcut
```

The result is ready in `builds/minecraft-capcut/` as `narration.wav`,
`captions.srt`, `manifest.json`, and individual scene WAV files.

## Features

- Generate natural speech locally with [Kokoro](https://github.com/hexgrad/kokoro).
- Render each scene separately and combine it into one normalized narration.
- Create editable SRT captions from the exact supplied script.
- Align captions to speech with MLX Whisper on Apple Silicon.
- Fit narration to a video's duration within a safe speaking-speed range.
- Build a CapCut-ready package with audio, captions, and timing metadata.
- Use a deterministic fake engine for fast, model-free development and tests.
- Launch an always-on-top macOS companion window for the CapCut workflow.

## How it works

```text
YAML script + source video
          |
          v
  narration generation
          |
          +-- scene WAV files
          +-- combined narration.wav
          +-- captions.srt
          +-- manifest.json
```

## Script format

Projects are small YAML files with settings and ordered scenes:

```yaml
title: Script2Video Demo
language: en-US
engine: kokoro
voice: af_heart

scenes:
  - id: intro
    text: Welcome. This script becomes locally generated narration.
    pause_after_ms: 500

  - id: explanation
    text: Each scene is rendered separately and recorded in the manifest.
    speed: 1.0
```

See [`examples/demo.yaml`](examples/demo.yaml) for a complete example.

## Create a CapCut package

Generate narration and subtitles timed to an existing video:

```bash
script2video capcut examples/minecraft.yaml \
  --video /path/to/video.mp4 \
  --output builds/minecraft-capcut
```

The output directory contains:

```text
builds/minecraft-capcut/
├── narration.wav
├── captions.srt
├── manifest.json
└── scenes/
    └── 001-*.wav
```

By default, the command:

1. Measures the video duration with `ffprobe`.
2. Adjusts scene speeds to fit the narration to the video.
3. Aligns the supplied text to the generated speech with MLX Whisper.
4. Writes editable audio, captions, and timing metadata.

The fitter rejects speeds outside `0.50`–`2.00` to keep narration
understandable. Use `--no-fit` to preserve script speeds, `--no-align` for the
exact-block timing fallback, or `--align-model base.en` for a larger English
alignment model.

To use the package in CapCut Desktop:

1. Import `narration.wav` and place it at timeline time zero.
2. Open **Captions → Add Captions** and import `captions.srt` as UTF-8.
3. Keep the captions at timeline time zero and apply your preferred style.

For implementation details, see
[`docs/m3-capcut.md`](docs/m3-capcut.md).

## Companion workflow

The always-on-top window lets you choose a YAML script, source video, output
folder, voice, and alignment model. It can generate the package, open the
output folder, and launch CapCut.

The companion exports standard files instead of editing CapCut projects
directly because CapCut does not provide a documented desktop plugin SDK.

## Languages and voices

Supported project language codes are `en-US`, `en-GB`, `es-ES`, `fr-FR`,
`hi-IN`, `it-IT`, `ja-JP`, `pt-BR`, and `zh-CN`. The selected voice must support
the project language.

List all voices exposed by Kokoro:

```bash
script2video voices --engine kokoro
```

## Development

Install the development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the complete test suite:

```bash
python -m pytest
```

For quick testing without downloading speech models, override the script's
engine with the deterministic fake engine:

```bash
script2video render examples/demo.yaml \
  --engine fake \
  --voice test_narrator \
  --output builds/demo-fake
```

The fake engine writes valid WAV files containing short test tones, so the
pipeline can be tested end to end without a hosted API or model download.

## Documentation

- [Stage 1 design](docs/stage-1-design.md)
- [CapCut package design](docs/m3-capcut.md)

## License

This project is licensed under the terms in [`LICENSE`](LICENSE).
