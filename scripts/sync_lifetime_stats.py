r"""
Trigger a one-off upload of lifetime stats to the configured stats API.

Run from project root (same layout as other scripts in this folder):

  python scripts/sync_lifetime_stats.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
_src = _project_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from core.stats_api_client import sync_lifetime_stats_to_api  # noqa: E402


def main() -> None:
    sync_lifetime_stats_to_api()
    print("sync_lifetime_stats_to_api() finished (check logs for HTTP status).")


if __name__ == "__main__":
    main()
