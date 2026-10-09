"""
Atlas SDK install hook.

Runs during a source-distribution install (`pip install` from the sdist) and does
one thing: write the dev marker, so the SDK can tell a developer machine from an
end-user bundle. pip does not run setup.py when it installs a wheel, which is what
a normal `pip install atlas-auth` gets, so the marker is written only in the sdist
case.

It makes no network calls and rewrites no package files. An earlier version fetched
atlas/__init__.py from a GitHub release and swapped it in place, which skipped pip's
hash checking, and no release ever carried that asset. Binding
updates arrive through `pip install -U`, from the registry.

Why a setup.py: pyproject.toml-only projects can't define custom install commands in
the standard, well-supported way. A sibling setup.py with
cmdclass={"install": AtlasInstallCommand} is the working pattern. pyproject.toml's
[build-system] handles the wheel/sdist build.

Never fails the install: every error is swallowed.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from setuptools import setup
from setuptools.command.install import install as _install


def _local_app_data() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base)
    return Path.home() / "AppData" / "Local"


def write_dev_marker(version: str) -> None:
    try:
        d = _local_app_data() / "AtlasAuth" / "data"
        d.mkdir(parents=True, exist_ok=True)
        marker = {
            "sdk": "pip",
            "version": version,
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        (d / "dev_marker.json").write_text(json.dumps(marker, indent=2), encoding="utf-8")
    except Exception:
        pass  # silent -- dev marker is a hint, not a gate


def _current_version() -> str:
    try:
        import ctypes
        # Atlas.dll sits next to setup.py in the sdist.
        dll = Path(__file__).resolve().parent / "Atlas.dll"
        if not dll.is_file():
            return "0.0.0"
        lib = ctypes.CDLL(str(dll))
        buf = ctypes.create_string_buffer(64)
        lib.Atlas_Version(buf, 64)
        v = buf.value.decode("utf-8", errors="replace").strip()
        return v or "0.0.0"
    except Exception:
        return "0.0.0"


class AtlasInstallCommand(_install):
    """Custom install command. pip invokes this for sdist installs."""

    def run(self):
        super().run()  # standard install first
        try:
            write_dev_marker(_current_version())
        except Exception:
            pass  # never fail the install


setup(cmdclass={"install": AtlasInstallCommand})
