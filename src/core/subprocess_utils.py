"""Shared subprocess helpers (e.g. hide console on Windows)."""

import subprocess
import sys
from typing import Any, Dict


def get_subprocess_kwargs() -> Dict[str, Any]:
    """Kwargs for Popen/run so no console window flashes on Windows."""
    kwargs: Dict[str, Any] = {}
    if sys.platform == "win32":
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            kwargs["creationflags"] = 0x08000000
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = si
    return kwargs
