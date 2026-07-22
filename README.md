# script2video

[English](README.md) | [简体中文](README.zh-CN.md)

Local-first tools for turning a structured YAML script into narration, timed
captions, and an editable CapCut package.

`script2video` runs speech generation and alignment on your machine. It can
render narration scene by scene, fit the result to an existing video, and
produce standard WAV, SRT, and JSON files without modifying CapCut project
files.

![Script2Video companion workspace](docs/script2video-companion.png)

## Install for users

Git is not required. Download the
[latest project ZIP](https://github.com/saslifat-gif/script2video/archive/refs/heads/main.zip),
extract it, and open a terminal in the extracted `script2video-main` folder.

`script2video` currently runs as a local Python application. It requires Python
3.11 and FFmpeg, which provides the `ffprobe` video-inspection command.

### macOS

Install the system dependencies and the application:

```bash
brew install ffmpeg espeak-ng
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install ".[kokoro,alignment]"
```

AI word alignment requires a Mac with Apple Silicon. On an Intel Mac, install
`.[kokoro]` instead and use the exact caption-timing fallback.

### Windows PowerShell

When using a VS Code Remote Tunnel, first confirm that the terminal belongs to
the Windows machine. Its prompt should look like `PS C:\...>`, not a macOS path
such as `/Users/...`. You can verify the active machine with:

```powershell
Get-Location
py -3.11 -c "import platform, sys; print(sys.executable); print(platform.platform())"
```

If the output mentions macOS or `/Users`, reconnect VS Code to the Windows
tunnel and open a new terminal before installing anything.

Install Python and FFmpeg with Windows Package Manager, then restart PowerShell
so `ffprobe` is available on `PATH`:

```powershell
winget install --exact --id Python.Python.3.11
winget install --exact --id Gyan.FFmpeg
```

In the extracted `script2video-main` folder, install the Windows-compatible
application:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install ".[kokoro]"
```

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

The first render downloads the selected Kokoro model and voice from Hugging
Face. The first aligned render also downloads the selected Whisper model.
Later runs reuse the local caches.

## Quick start

1. Open the companion UI.
2. For **Script**, choose `examples/minecraft.yaml` or your own YAML file.
3. Choose a source video and output folder.
4. Select a voice or keep **Use script voice**.
5. Select **Generate CapCut Package**.
6. When generation finishes, select **Open Output** or **Open CapCut**.

The output folder contains `narration.wav`, `captions.srt`, `manifest.json`, and
the individual scene WAV files.

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
- Render each scene separately and combine it into one normalized narration.
- Create editable SRT captions from the exact supplied script.
- Align captions to speech with MLX Whisper on Apple Silicon.
- Fit narration to a video's duration within a safe speaking-speed range.
- Build a CapCut-ready package with audio, captions, and timing metadata.
- Use a deterministic fake engine for fast, model-free development and tests.
- Launch an always-on-top desktop companion for the CapCut workflow.

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
