from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


root = Path(SPECPATH).parents[1]
source = root / "src"
icon = root / "packaging" / "macos" / "script2video.icns"

datas = [
    (str(source / "script2video" / "web_static"), "script2video/web_static"),
    (str(root / "LICENSE"), "."),
]
binaries = []
hiddenimports = [
    "kokoro",
    "mlx_whisper",
    "numpy",
    "script2video.alignment_worker",
    "torch",
    "transformers",
]

for package in (
    "cn2an",
    "fugashi",
    "jaconv",
    "jieba",
    "kokoro",
    "misaki",
    "mojimoji",
    "language_tags",
    "espeakng_loader",
    "en_core_web_sm",
    "ordered_set",
    "pyopenjtalk",
    "pypinyin",
    "pypinyin_dict",
    "unidic",
    "webview",
    "mlx",
    "mlx_whisper",
):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

hiddenimports += collect_submodules("huggingface_hub")

analysis = Analysis(
    [str(source / "script2video" / "desktop.py")],
    pathex=[str(source)],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "IPython", "jupyter", "matplotlib", "notebook", "pytest", "setuptools",
        "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6",
    ],
    noarchive=False,
)

pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Script2Video Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon),
)
bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Script2Video Studio",
)
app = BUNDLE(
    bundle,
    name="Script2Video Studio.app",
    icon=str(icon),
    bundle_identifier="com.saslifat.script2video",
    info_plist={
        "LSMinimumSystemVersion": "14.0",
        "NSHighResolutionCapable": True,
    },
)
