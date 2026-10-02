# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller Unified Specification File for Juvion.

Builds a standalone, redistributable desktop package for:
- Windows (Juvion.exe + DLLs + Assets)
- Linux (Juvion binary + Libs + Desktop entry)
- macOS (Juvion.app Application Bundle)
"""

import sys
import os
import json
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

app_name = "Juvion"
base_dir = Path.cwd()
app_version = json.loads((base_dir / "version.json").read_text(encoding="utf-8"))["version"]

# Honor the torch exclusion in Windows DLL-discovery subprocesses as well.
os.environ["JUVION_BUILD_NO_TORCH"] = "1"
os.environ["PYTHONPATH"] = str(base_dir / "build_support") + os.pathsep + os.environ.get("PYTHONPATH", "")

# Additional data directories and files to bundle
datas = [
    ("assets", "assets"),
    ("version.json", "."),
    ("LICENSE", "."),
    ("LICENSE-Writingway", "."),
]

binaries = []
hiddenimports = [
    "tiktoken_ext.openai_public",
    "tiktoken_ext",
    "PyQt5.QtSvg",
    "spylls",
    "spylls.hunspell",
    "docx",
    "docx.oxml",
    "docx.oxml.ns",
    "ebooklib",
    "ebooklib.epub",
    "bs4",
    "markdownify",
    "markdown",
    "roman",
    "kanjize",
    "num2words",
    "pyttsx3",
    "pyttsx3.drivers",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "PyQt5.QtChart",
    "PyQt5.QtWebEngineWidgets",
    "sqlite3",
]
hiddenimports.append({"win32": "pyttsx3.drivers.sapi5", "darwin": "pyttsx3.drivers.nsss"}.get(sys.platform, "pyttsx3.drivers.espeak"))

def _safe_collect_all(package_name):
    global datas, binaries, hiddenimports
    try:
        d, b, h = collect_all(package_name)
        datas += d
        binaries += b
        hiddenimports += h
        print(f"Collected package: {package_name} ({len(d)} data, {len(b)} bin, {len(h)} imports)")
    except Exception as e:
        print(f"Skipping collect_all({package_name}): {e}")

_safe_collect_all("cmudict")
_safe_collect_all("spylls")
_safe_collect_all("imageio")
_safe_collect_all("langchain_ollama")

# Select appropriate app icon based on OS
app_icon = None
if sys.platform.startswith("win"):
    ico_candidate = base_dir / "assets" / "icons" / "app_icon.ico"
    if ico_candidate.exists():
        app_icon = str(ico_candidate)
elif sys.platform.startswith("darwin"):
    icns_candidate = base_dir / "assets" / "icons" / "app_icon.icns"
    if icns_candidate.exists():
        app_icon = str(icns_candidate)
    elif (base_dir / "assets" / "icons" / "app_icon.png").exists():
        app_icon = str(base_dir / "assets" / "icons" / "app_icon.png")
else:
    png_candidate = base_dir / "assets" / "icons" / "app_icon.png"
    if png_candidate.exists():
        app_icon = str(png_candidate)

a = Analysis(
    ["main.py"],
    pathex=[str(base_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "matplotlib.tests",
        "scipy",
        "torch",
        "torchaudio",
        "torchvision",
        "torch.testing",
        "torch.distributed",
        "pytest",
        "unittest",
        "IPython",
        "notebook",
        "jupyter",
        "tensorboard",
        "whisper",
        "openai_whisper",
        "pyaudio",
        "demucs",
        "noisereduce",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=os.environ.get("TARGET_ARCH", None),
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)

# macOS App Bundle (only built on Darwin)
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{app_name}.app",
        icon=app_icon,
        bundle_identifier="com.juvion.studio",
        info_plist={
            "CFBundleName": "Juvion",
            "CFBundleDisplayName": "Juvion",
            "CFBundleGetInfoString": "Juvion — Estúdio Literário",
            "CFBundleIdentifier": "com.juvion.studio",
            "CFBundleVersion": app_version,
            "CFBundleShortVersionString": app_version,
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
        },
    )
