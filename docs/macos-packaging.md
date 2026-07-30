# macOS packaging

Script2Video Studio v1.0.11 can be packaged locally as an Apple Silicon
application for development and personal use. It requires macOS 14 or later.

Public GitHub releases are Windows-only because the project does not currently
have an Apple Developer ID certificate or notarization account. The local build
creates `Script2Video-Studio-1.0.11-macOS-arm64.dmg` when needed.

Build locally on an Apple Silicon Mac with:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install ".[kokoro,alignment,packaging]"
.venv/bin/python -m spacy download en_core_web_sm
PATH="$PWD/.venv/bin:$PATH" ./scripts/build-macos.sh
```

The local application is unsigned and is not intended for public distribution.
