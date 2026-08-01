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
# - `--onefile` (EXE with a.binaries + a.datas + a.zipfiles): PyInstaller
#   writes a self-extracting exe that unpacks the interpreter + stdlib +
#   our `atlas/` package + Atlas.dll into a temp `_MEIxxx` folder on each
#   launch. The user only sees one .exe.
# - Atlas.dll is bundled as a binary so it lives inside the .exe. The
#   atlas/_ffi.py `_MEIPASS` fallback locates it at runtime. Advantage:
#   single-file distribution, no sidecar to lose. Trade-off: rev'ing the
#   DLL means rebuilding the exe. If you'd rather ship the DLL alongside
#   the exe (independently updatable), remove the binaries=[('...',...)]
#   entry below and copy Atlas.dll next to the exe after build.
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
