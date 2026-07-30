# macOS packaging

Script2Video Studio v1.0.7 is packaged as an Apple Silicon application and
distributed in a DMG. It requires macOS 14 or later.

The release workflow runs the tests, verifies Kokoro's language registry, and
creates `Script2Video-Studio-1.0.7-macOS-arm64.dmg`.

Build locally on an Apple Silicon Mac with:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install ".[kokoro,alignment,packaging]"
.venv/bin/python -m spacy download en_core_web_sm
PATH="$PWD/.venv/bin:$PATH" ./scripts/build-macos.sh
```

The application is currently unsigned. macOS may require the user to
Control-click the app and choose **Open** the first time.
