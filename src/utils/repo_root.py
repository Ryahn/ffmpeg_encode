"""Locate the git repository root when running from a source checkout."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _has_git_dir(path: Path) -> bool:
    git = path / ".git"
    return git.is_dir() or git.is_file()


def find_git_repo_root() -> Path | None:
    candidates: list[Path] = []
    try:
        cwd = Path.cwd().resolve()
        candidates.append(cwd)
    except Exception:
        pass
    try:
        here = Path(__file__).resolve()
        for p in [here.parents[i] for i in range(min(8, len(here.parents)))]:
            candidates.append(p)
    except Exception:
        pass
    seen: set[Path] = set()
    for base in candidates:
        if base in seen:
            continue
        seen.add(base)
        cur = base
        for _ in range(32):
            if _has_git_dir(cur):
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent
    return None


def git_on_path() -> bool:
    return shutil.which("git") is not None


def run_git_pull(repo_root: Path) -> tuple[int, str, str]:
    """Run git pull in repo_root. Returns (returncode, stdout, stderr)."""
    kw: dict = {
        "args": ["git", "pull"],
        "cwd": str(repo_root),
        "capture_output": True,
        "text": True,
        "timeout": 120,
    }
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    r = subprocess.run(**kw)
    return r.returncode, r.stdout or "", r.stderr or ""
