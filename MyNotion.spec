# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for MyNotion.
Build with: pyinstaller MyNotion.spec
"""

import sys
from pathlib import Path

block_cipher = None

# Project root (where this .spec file lives)
ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "src" / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        # Bundle the resources folder (icons used at runtime)
        (str(ROOT / "resources"), "resources"),
    ],
    hiddenimports=[
        "qasync",
        "httpx",
        "httpx._transports",
        "httpx._transports.default",
        "ai.providers.ollama",
        "ai.providers.anthropic",
        "ollama",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "pytest_qt",
        "pytest_asyncio",
        "unittest",
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MyNotion",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No terminal window when double-clicked
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "resources" / "mynotion.ico"),
)
