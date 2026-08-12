# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the Atlas Python Console example.
#
# Build:
#   pyinstaller build_exe.spec --clean --noconfirm --distpath "..\..\..\..\- Builds"
#
# Output:
#   - Builds/Atlas Auth Example (Python).exe     (single self-extracting file)
#
# Design notes:
# - `--onefile` writes a self-extracting exe that unpacks the interpreter
#   + stdlib + the `atlas/` package + Atlas.dll into a temp `_MEIxxx`
#   folder on each launch. End users see one .exe; no sidecar.
# - Atlas.dll is bundled via `binaries=` so it lives inside the .exe and
#   is extracted alongside the package on launch. atlas/_ffi.py's
#   _MEIPASS probe locates it at runtime.
# - `atlas/` package is added via `pathex` so `import atlas` resolves at
#   analysis time.
from pathlib import Path

HERE    = Path(SPECPATH).resolve()
SDK_DIR = HERE.parent / "Atlas SDK"

a = Analysis(
    ['Atlas Auth Example.py'],
    pathex=[str(SDK_DIR)],
    binaries=[
        # (source, destination-inside-bundle). '.' places the DLL at the
        # bundle root, which is what _ffi.py's _MEIPASS probe expects.
        (str(SDK_DIR / "Atlas.dll"), '.'),
    ],
    datas=[],
    hiddenimports=['atlas', 'atlas._ffi'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Atlas Auth Example (Python)',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
