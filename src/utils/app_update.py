"""GitHub release checks and applying updates (frozen + source)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version

GITHUB_OWNER_REPO = "Ryahn/ffmpeg_encode"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_OWNER_REPO}/releases/latest"


@dataclass(frozen=True)
class GitHubRelease:
    tag_name: str
    version_normalized: str
    html_url: str
    body: str
    assets: tuple[dict[str, Any], ...]


def normalize_tag_version(tag: str) -> str:
    t = (tag or "").strip()
    if t.lower().startswith("v"):
        t = t[1:].lstrip()
    return t


def parse_semver(s: str) -> Version | None:
    try:
        return Version(normalize_tag_version(s))
    except InvalidVersion:
        return None


def fetch_latest_release() -> GitHubRelease:
    req = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ffmpeg_encode-update-check",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    tag = str(data.get("tag_name") or "")
    assets = tuple(data.get("assets") or ())
    return GitHubRelease(
        tag_name=tag,
        version_normalized=normalize_tag_version(tag),
        html_url=str(data.get("html_url") or ""),
        body=str(data.get("body") or ""),
        assets=assets,
    )


def compare_to_local(remote_tag: str, local_version: str) -> str:
    """Return 'newer', 'older_or_equal', or 'unknown'."""
    rv = parse_semver(remote_tag)
    lv = parse_semver(local_version)
    if rv is None:
        return "unknown"
    if lv is None:
        return "newer"
    if rv > lv:
        return "newer"
    return "older_or_equal"


def _asset_by_pred(assets: tuple[dict[str, Any], ...], pred) -> dict[str, Any] | None:
    for a in assets:
        name = str(a.get("name") or "")
        if pred(name):
            return a
    return None


def pick_asset(release: GitHubRelease, channel: str) -> dict[str, Any] | None:
    assets = release.assets
    if channel == "inno":
        return _asset_by_pred(
            assets, lambda n: "setup" in n.lower() and n.endswith(".exe")
        )
    if channel == "portable":
        return _asset_by_pred(
            assets, lambda n: "portable" in n.lower() and n.endswith(".zip")
        )
    if channel == "mac_app":
        a = _asset_by_pred(assets, lambda n: n.endswith(".dmg"))
        if a:
            return a
        return _asset_by_pred(
            assets,
            lambda n: n.endswith(".zip") and "ffmpeg_encode" in n.lower(),
        )
    portable = _asset_by_pred(
        assets, lambda n: "portable" in n.lower() and n.endswith(".zip")
    )
    if portable:
        return portable
    return _asset_by_pred(
        assets, lambda n: "setup" in n.lower() and n.endswith(".exe")
    )


def download_asset(url: str, dest: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ffmpeg_encode-update-check"},
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=300) as resp:
        dest.write_bytes(resp.read())


def apply_installer_windows(setup_path: Path) -> None:
    if sys.platform != "win32":
        raise OSError("Installer launch is only supported on Windows")
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [str(setup_path)],
        cwd=str(setup_path.parent),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )


def _portable_updater_ps1() -> str:
    return r"""param(
  [Parameter(Mandatory=$true)][int]$TargetPid,
  [Parameter(Mandatory=$true)][string]$ZipPath,
  [Parameter(Mandatory=$true)][string]$InstallDir
)
$ErrorActionPreference = 'Stop'
try { Wait-Process -Id $TargetPid -Timeout 7200 -ErrorAction SilentlyContinue } catch {}
$expandRoot = Join-Path $env:TEMP ("ffmpeg_encode_upd_" + [Guid]::NewGuid().ToString("n"))
New-Item -ItemType Directory -Path $expandRoot -Force | Out-Null
try {
  Expand-Archive -LiteralPath $ZipPath -DestinationPath $expandRoot -Force
  $inner = Join-Path $expandRoot 'ffmpeg_encode'
  if (-not (Test-Path -LiteralPath $inner)) {
    throw "Unexpected portable zip layout (missing ffmpeg_encode folder)"
  }
  Get-ChildItem -LiteralPath $inner | ForEach-Object {
    $target = Join-Path $InstallDir $_.Name
    Copy-Item -LiteralPath $_.FullName -Destination $target -Recurse -Force
  }
  $exe = Join-Path $InstallDir 'ffmpeg_encode.exe'
  if (Test-Path -LiteralPath $exe) {
    Start-Process -FilePath $exe -WorkingDirectory $InstallDir
  }
} finally {
  Remove-Item -LiteralPath $expandRoot -Recurse -Force -ErrorAction SilentlyContinue
}
"""


def launch_portable_replace_after_exit(zip_path: Path) -> None:
    if sys.platform != "win32":
        raise OSError("Portable replace-after-exit is only implemented on Windows")
    ps1 = Path(tempfile.gettempdir()) / f"ffmpeg_encode_update_{os.getpid()}.ps1"
    ps1.write_text(_portable_updater_ps1(), encoding="utf-8")
    install_dir = str(Path(sys.executable).resolve().parent)
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps1),
            str(os.getpid()),
            str(zip_path),
            install_dir,
        ],
        creationflags=flags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def open_mac_artifact(path: Path) -> None:
    if sys.platform != "darwin":
        raise OSError("open is only used on macOS")
    subprocess.Popen(["open", str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def fetch_release_safe() -> tuple[GitHubRelease | None, str | None]:
    try:
        return fetch_latest_release(), None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, "No published releases found for this repository."
        return None, f"GitHub returned HTTP {e.code}."
    except urllib.error.URLError as e:
        return None, f"Network error: {e.reason!s}"
    except Exception as e:
        return None, str(e)


def pick_asset_safe(release: GitHubRelease, channel: str) -> dict[str, Any] | None:
    if channel == "unknown":
        if sys.platform == "darwin":
            return pick_asset(release, "mac_app")
        return pick_asset(release, "unknown")
    a = pick_asset(release, channel)
    if a:
        return a
    if sys.platform == "darwin":
        return pick_asset(release, "mac_app")
    return pick_asset(release, "unknown")
