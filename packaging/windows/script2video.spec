from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


root = Path(SPECPATH).parents[1]
source = root / "src"
icon = root / "packaging" / "windows" / "script2video.ico"
version_file = root / "packaging" / "windows" / "version_info.txt"

datas = [
    (
        str(source / "script2video" / "web_static"),
        "script2video/web_static",
    ),
    (str(root / "LICENSE"), "."),
]
binaries = []
hiddenimports = [
    "kokoro",
    "numpy",
    "torch",
    "transformers",
]

# Kokoro loads its pipeline dynamically. Its language packages also rely on
# data files and the platform-specific eSpeak NG library at runtime.
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
        "IPython",
        "jupyter",
        "matplotlib",
        "notebook",
        "pytest",
        "setuptools",
        "tkinter",
        "cefpython3",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
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
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon),
    version=str(version_file),
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
