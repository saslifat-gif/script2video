# script2video

Local-first tools for turning a written script into production-ready narration,
then eventually into a complete video.

## Current scope: M3 CapCut companion

Stage 1 converts a structured YAML script into:

- one WAV file per scene;
- one combined, normalized narration WAV;
- a JSON manifest containing scene timing and provenance;
- readable errors for invalid scripts, unsupported voices, and failed synthesis.

The project includes a real Kokoro engine and a deterministic fake engine for
fast development tests. Both use the same engine interface, so additional
open-source TTS systems can be added without changing the script format or
orchestration layer.

M3 also creates a CapCut-ready package from a video and script:

- `narration.wav`, optionally fitted to the video's duration;
- `captions.srt`, with exact audio timing and no more than two display lines;
- `manifest.json`, containing video, narration, fitting, and timing metadata.

See [docs/stage-1-design.md](docs/stage-1-design.md) for the product and
technical design, and [examples/demo.yaml](examples/demo.yaml) for the proposed
input format.

## Install for real speech

Python 3.11 is recommended. Kokoro requires Python 3.10 through 3.12.

```bash
cd /Users/lifat/Projects/AI/script2video
/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[kokoro,alignment]'
```

The Kokoro dependency currently installs a bundled eSpeak NG loader on macOS.
If that loader is unavailable on another setup, install the system package for
English out-of-dictionary fallback and several non-English languages:

```bash
brew install espeak-ng
```

The first real render downloads the Kokoro model and selected voice from
Hugging Face. Later runs reuse the local model cache.

## CLI

```text
script2video voices --engine kokoro
script2video validate examples/demo.yaml
script2video render examples/minecraft.yaml --output builds/minecraft-kokoro
```

Supported project language codes are `en-US`, `en-GB`, `es-ES`, `fr-FR`,
`hi-IN`, `it-IT`, `ja-JP`, `pt-BR`, and `zh-CN`. A voice must belong to the
selected language. Run `script2video voices --engine kokoro` to see all 54
published voice IDs.

## CapCut package

Create narration and subtitles matched to a video:

```bash
.venv/bin/script2video capcut examples/minecraft.yaml \
  --video /path/to/video.mp4 \
  --output builds/minecraft-capcut
```

AI word alignment is enabled by default with MLX Whisper `tiny.en` on Apple
Silicon. It listens to the generated narration and measures word timestamps,
then reconciles those measurements to the exact supplied script. This prevents
recognition mistakes from changing subtitle text or shifting later cues. The
first aligned render downloads the selected Whisper timing model. Use `--no-align`
for the non-AI exact-block fallback, or `--align-model base.en` for a larger
English alignment model.

By default, the command measures the video with `ffprobe` and adjusts each
scene's Kokoro speed proportionally. It refuses a fit that would require a
speed outside `0.50` through `2.00`, because extreme fitting would make the
voice difficult to understand. Use `--no-fit` to preserve the script speeds.

To import the result into CapCut Desktop:

1. Import `narration.wav` and place it at timeline time zero.
2. Open **Captions → Add Captions**, then import the UTF-8 `captions.srt` file.
3. Keep the captions at timeline time zero and apply the desired caption style.

The caption blocks remain editable inside CapCut.

## Floating companion

Launch the always-on-top macOS window:

```bash
.venv/bin/script2video companion
```

Choose the YAML script, source video, output folder, optional voice, and
alignment model. The window can stay above CapCut while it generates the
package, opens the output folder, and launches CapCut. It is a companion window
rather than an injected CapCut plugin because CapCut does not expose a
documented desktop plugin SDK.

The deterministic fake engine writes valid WAV files containing
short test tones, allowing the complete pipeline to be developed and tested
without downloading a model.

Run the CLI from a source checkout:

```bash
PYTHONPATH=src python -m script2video --help
PYTHONPATH=src python -m script2video render examples/demo.yaml \
  --engine fake --voice test_narrator --output builds/demo
```

Run the dependency-light M1 tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Stage 1 is complete when `render` can reliably create deterministic narration
assets from a valid script on Apple Silicon, without using a hosted API.
