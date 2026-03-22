"""Write bundle_metadata.json before PyInstaller (CI and local release builds)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", required=True, help="Semver or 'dev'")
    p.add_argument(
        "--channel",
        required=True,
        choices=("portable", "inno", "mac_app", "unknown"),
        help="Distribution channel baked into the frozen bundle",
    )
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = root / "src" / "bundle_metadata.json"
    out.write_text(
        json.dumps({"version": args.version, "channel": args.channel}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
