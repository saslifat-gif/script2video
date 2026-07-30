# Windows application packaging

Script2Video Studio v1.0.10 is packaged as a 64-bit, per-user Windows
application. Users receive one installer and do not need to install Python.

## Package design

```text
Python 3.11 + Script2Video + Kokoro + pywebview
    -> PyInstaller one-folder application
    -> Inno Setup compressed installer
    -> Script2Video-Studio-1.0.10-Windows-x64.exe
```

The one-folder layout starts faster than a giant self-extracting executable.
pywebview hosts Studio in a native Edge WebView2 window and falls back to the
default browser if the embedded renderer cannot start. Inno Setup still
presents the application as a single installer, adds Start Menu integration,
and provides a normal Windows uninstaller.

The Kokoro model and selected voices are downloaded to the user's normal
Hugging Face cache on first use. FFmpeg is detected from the system when video
support is needed. Neither is embedded in the installer.

## Automated build

The `Build desktop applications` GitHub Actions workflow runs both Windows and
macOS jobs. The Windows job installs the English spaCy model, executes the
tests, builds the application, compiles the installer, and uploads it as a
workflow artifact.

It runs for relevant pull requests, version tags, and manual dispatches.

## Local Windows build

Install Python 3.11 and Inno Setup 6, then run in PowerShell:

```powershell
py -3.11 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install ".[kokoro,packaging]"
.\.venv-build\Scripts\python.exe -m spacy download en_core_web_sm
.\.venv-build\Scripts\Activate.ps1
.\scripts\build-windows.ps1
```

The resulting installer is written to:

```text
release/Script2Video-Studio-1.0.10-Windows-x64.exe
```

## Release checklist

1. Download and install the workflow artifact on a clean Windows 11 machine.
2. Confirm Studio opens inside its own desktop window.
3. Generate narration with the default English voice.
4. Install FFmpeg and generate a CapCut package from a short video.
5. Quit Studio from the footer and uninstall it from Windows Settings.
6. Confirm `_internal/language_tags/data/json/index.json` exists in the
   one-folder application; the build script enforces this automatically.
7. Verify all four text splitting patterns and confirm the root output includes
   `captions.srt` with exact timing for every readable subtitle card.
8. Create the `v1.0.10` GitHub release only after this smoke test passes.
