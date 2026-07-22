# script2video

[English](README.md) | [简体中文](README.zh-CN.md)

Local-first tools for turning a structured YAML script into narration, timed
captions, and an editable CapCut package.

`script2video` runs speech generation and alignment on your machine. It can
render narration scene by scene, fit the result to an existing video, and
produce standard WAV, SRT, and JSON files without modifying CapCut project
files.

> **Status:** Ready for local use on macOS and Windows. Narration generation
> does not require a video. Add a video only when you want a timed CapCut
> package with captions.

![Script2Video companion workspace](docs/script2video-companion.png)

## Choose a workflow

| Goal | Video required? | Result |
| --- | --- | --- |
| Generate voice narration | No | `narration.wav`, scene WAV files, and `manifest.json` |
| Build a CapCut package | Yes | Narration, editable `captions.srt`, scenes, and timing metadata |

## Install once

Git is not required. Download the
[latest project ZIP](https://github.com/saslifat-gif/script2video/archive/refs/heads/main.zip),
extract it, and open a terminal in the extracted `script2video-main` folder.

`script2video` currently runs as a local Python application. It requires Python
3.11. FFmpeg is needed only when you select a video.

The first real-speech installation includes PyTorch, Transformers, tokenizers,
spaCy, and Kokoro's language tools. This is expected and may take several
minutes. The first render downloads the selected voice model; later runs reuse
the local cache.

### macOS

Install Python and the application:

```bash
brew install python@3.11 espeak-ng
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install ".[kokoro,alignment]"
```

If you plan to select a video and create CapCut packages, also run
`brew install ffmpeg`. If the `brew` command is unavailable, install
[Homebrew](https://brew.sh/) first.

AI word alignment requires a Mac with Apple Silicon. On an Intel Mac, install
`.[kokoro]` instead and use the exact caption-timing fallback.

### Windows PowerShell

Install Python with Windows Package Manager:

```powershell
winget install --exact --id Python.Python.3.11
```

Close PowerShell after the installation, then reopen it in the project folder.
This lets Windows recognize the new `py` command.

In the extracted `script2video-main` folder, install the Windows-compatible
application:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install ".[kokoro]"
```

If you plan to select a video and create CapCut packages, also install FFmpeg:

```powershell
winget install --exact --id Gyan.FFmpeg
```

The app can normally find Winget's FFmpeg installation immediately. If it
cannot, close and reopen the app once.

Create a separate `.venv` on each computer. Do not copy or synchronize the
Mac `.venv` to Windows: compiled packages such as `tokenizers`, NumPy, and audio
libraries contain operating-system-specific files. The repository already
ignores `.venv/`, so Git and project ZIP files transfer source code only.

MLX Whisper does not run on Windows. The companion disables it automatically
and uses exact caption-block timing instead.

Kokoro normally supplies its phoneme support through Python dependencies. If a
voice reports a missing eSpeak library, install the latest Windows MSI from the
[official eSpeak NG releases](https://github.com/espeak-ng/espeak-ng/releases).

## Open the companion UI

On macOS:

```bash
.venv/bin/script2video companion
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\script2video.exe companion
```

The companion is a local desktop window; no server or browser is required.

## Quick start

### Generate narration without a video

1. Open the companion UI.
2. For **Script**, choose `examples/minecraft.yaml` or your own YAML file.
3. Leave **Video** empty.
4. Choose an output folder and select a voice, or keep **Use script voice**.
5. Select **Generate Narration**.
6. When generation finishes, select **Open Output**.

The output contains `narration.wav`, `manifest.json`, and the individual scene
WAV files. FFmpeg is not required for this workflow.

### Build a CapCut package with a video

Follow the same steps, but choose a source video. The companion switches to
**Generate CapCut Package** and adds `captions.srt`, duration fitting, and video
timing metadata. Select **Remove video** at any time to return to narration-only
mode.

For command-line usage, validate a script and render its narration with:

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
- Generate narration without selecting a video.
- Render each scene separately and combine it into one normalized narration.
- Create editable SRT captions from the exact supplied script.
- Align captions to speech with MLX Whisper on Apple Silicon.
- Fit narration to a video's duration within a safe speaking-speed range.
- Build a CapCut-ready package with audio, captions, and timing metadata.
- Use a deterministic fake engine for fast, model-free development and tests.
- Launch an always-on-top desktop companion for the CapCut workflow.

## How it works

```text
YAML script
    |
    +-- no video --> narration.wav + scene WAVs + manifest.json
    |
    +-- video ----> narration.wav + captions.srt + scenes + manifest.json
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

Git is only needed for contributors who want to modify the source. Clone the
repository and install it in editable mode:

```bash
git clone https://github.com/saslifat-gif/script2video.git
cd script2video
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,kokoro,alignment]"
```

On Windows, activate with `.\.venv\Scripts\Activate.ps1` and omit `alignment`
from the extras.

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
