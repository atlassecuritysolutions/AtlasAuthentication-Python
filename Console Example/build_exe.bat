@echo off
REM Build the Python console example into a single self-contained .exe.
REM Requires: Python 3.9+ x64 with PyInstaller (pip install pyinstaller).
REM
REM Output:  ../../../../- Builds/Atlas Auth Example (Python).exe
REM
REM Atlas.dll is bundled INSIDE the exe (via build_exe.spec's binaries=)
REM so there is no sidecar to lose. To ship the DLL alongside the exe
REM instead (rev'able without rebuild), remove the binaries entry in
REM build_exe.spec and copy Atlas.dll into the output folder manually.

setlocal
pushd "%~dp0"

python -m PyInstaller build_exe.spec ^
    --clean --noconfirm ^
    --distpath "\Output" ^
    --workpath "build"

set RC=%errorlevel%
popd
endlocal & exit /b %RC%
