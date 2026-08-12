"""
Atlas SDK install hook.

The Python analog of the C++ MSBuild post-build target and the JS
`postinstall` script. Runs automatically during `pip install`,
`pip install -U`, and any pip-driven install flow.

Three responsibilities, in order:
  1. Write the dev marker so the runtime DLL updater knows this is
     a dev install (not an end-user bundle).
  2. Fetch releases/latest from the Python repo. If newer than what
     just installed, download the new atlas/__init__.py + Atlas.c.h
     and atomic-swap them in place, preserving the dev's API_KEY.
  3. Stay silent on every failure. pip install must never break
     because of the install hook.

Why a setup.py: pyproject.toml-only projects can't define custom
install commands in the standard, well-supported way. A sibling
setup.py with cmdclass={"install": AtlasInstallCommand} is the
modern, working pattern. pyproject.toml's [build-system] handles
the wheel/sdist build; setup.py is consulted by pip for the
install command specifically.
"""

import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from setuptools import setup
from setuptools.command.install import install as _install


RELEASES_URL = (
    "https://api.github.com/repos/atlassecuritysolutions/"
    "AtlasAuthentication-Python/releases/latest"
)

ASSETS = [
    {"rel_path": "atlas/__init__.py", "asset_name": "atlas/__init__.py"},
    {"rel_path": "Atlas.c.h",         "asset_name": "Atlas.c.h"},
]


def _local_app_data() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base)
    return Path.home() / "AppData" / "Local"


def write_dev_marker(site_packages_root: Path, version: str) -> None:
    try:
        d = _local_app_data() / "AtlasAuth"
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
        from pathlib import Path
        # atlas/ is the package being installed; Atlas.dll sits next to it
        # in the wheel's data_files layout.
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


def _log(msg: str) -> None:
    sys.stdout.write("[atlas-sdk] " + msg + "\n")
    sys.stdout.flush()


def _https_get_json(url: str, timeout: float = 5.0):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "atlas-sdk-install/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _https_get_bytes(url: str, timeout: float = 15.0):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "atlas-sdk-install/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return resp.read()
    except Exception:
        return None


def _is_allowed_url(url: str) -> bool:
    return bool(re.match(
        r"^https://(api\.github\.com|github\.com|objects\.githubusercontent\.com|"
        r"raw\.githubusercontent\.com|release-assets\.githubusercontent\.com)/",
        url,
    ))


def _compare_semver(a: str, b: str) -> int:
    def parts(s: str):
        s = re.sub(r"^v", "", s)
        out = [int(x) for x in re.findall(r"\d+", s)]
        while len(out) < 3:
            out.append(0)
        return out
    pa, pb = parts(a), parts(b)
    for x, y in zip(pa, pb):
        if x < y: return -1
        if x > y: return 1
    return 0


def _extract_api_key(body: str) -> str:
    m = re.search(r"""API_KEY\s*=\s*['"]([^'"]*)['"]""", body)
    return m.group(1) if m else ""


def _patch_api_key_and_stamp(new_bytes: bytes, user_key: str, from_v: str, to_v: str) -> bytes:
    try:
        body = new_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return new_bytes
    idx = body.find("API_KEY")
    if idx == -1:
        return new_bytes
    line_start = body.rfind("\n", 0, idx) + 1
    if from_v and to_v and from_v != to_v:
        stamp = (
            f"# Atlas SDK auto-updated on "
            f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}: "
            f"{from_v} -> {to_v}\n"
        )
        body = body[:line_start] + stamp + body[line_start:]
    if not user_key:
        return body.encode("utf-8")
    pat = re.compile(r"""(API_KEY\s*=\s*)(['"])([^'"]*)\2""")
    if not pat.search(body):
        return body.encode("utf-8")
    body = pat.sub(lambda m: m.group(1) + m.group(2) + user_key + m.group(2), body, count=1)
    return body.encode("utf-8")


def _atomic_swap_file(target: Path, data: bytes) -> bool:
    new_path = target.with_suffix(target.suffix + ".new")
    try:
        if new_path.exists():
            new_path.unlink()
        new_path.write_bytes(data)
        os.replace(new_path, target)  # atomic on Windows + POSIX, same-volume
        return True
    except Exception:
        try:
            if new_path.exists():
                new_path.unlink()
        except Exception:
            pass
        return False


def run_post_install(site_packages_root: Path) -> None:
    """The actual work. Public so it can be invoked standalone if needed."""
    version = _current_version()
    write_dev_marker(site_packages_root, version)

    release = _https_get_json(RELEASES_URL)
    if not release:
        return
    tag = release.get("tag_name")
    assets = release.get("assets") or []
    if not tag or not isinstance(assets, list):
        return

    remote_v = re.sub(r"^v", "", str(tag))
    if _compare_semver(remote_v, version) <= 0:
        return  # up to date or ahead

    # Read the dev's existing API_KEY from the file we just installed.
    user_key = ""
    try:
        idx_path = site_packages_root / "atlas" / "__init__.py"
        if idx_path.exists():
            user_key = _extract_api_key(idx_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    swapped = 0
    for a in ASSETS:
        asset = next((x for x in assets if x and x.get("name") == a["asset_name"]), None)
        if not asset:
            continue
        url = asset.get("browser_download_url") or ""
        if not _is_allowed_url(url):
            continue
        data = _https_get_bytes(url)
        if not data:
            continue
        if a["asset_name"] == "atlas/__init__.py":
            data = _patch_api_key_and_stamp(data, user_key, version, remote_v)
        target = site_packages_root / a["rel_path"]
        if _atomic_swap_file(target, data):
            swapped += 1

    if swapped > 0:
        _log(f"updated binding files: {version} -> {remote_v} ({swapped} file(s))")


class AtlasInstallCommand(_install):
    """Custom install command. pip invokes this during `pip install`."""

    def run(self):
        super().run()  # standard install first
        # After install, locate site-packages root from the wheel's
        # install layout. self.install_lib is the directory pip just
        # installed everything into.
        try:
            root = Path(self.install_lib)
        except Exception:
            return
        if not root.exists():
            return
        try:
            run_post_install(root)
        except Exception:
            pass  # never fail the install


setup(cmdclass={"install": AtlasInstallCommand})
