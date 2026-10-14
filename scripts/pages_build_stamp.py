#!/usr/bin/env python3
"""Write ``build.json`` and decide deploy for the Pages workflow (Story 102.2)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for _pkg in ("pyforge-core", "pyforge-steward"):
    _src = REPO_ROOT / "src" / "shared" / "packages" / _pkg / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from pyforge.core.flags import read_boolean  # noqa: E402
from pyforge.steward.pages import (  # noqa: E402
    PAGES_DUTY_FLAG,
    build_json,
    decide_deploy,
    tree_hash,
)


def _fetch_live_text(url: str) -> str | None:
    try:
        proc = subprocess.run(
            ["curl", "-fsSL", "--max-time", "30", url],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stamp build.json and print deploy decision outputs.")
    parser.add_argument("--root", type=Path, required=True, help="Built site root (docs-site/build/site)")
    parser.add_argument(
        "--live-url",
        required=True,
        help="URL of the live build.json (e.g. https://…/build.json)",
    )
    parser.add_argument("--built-from", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"root is not a directory: {root}", file=sys.stderr)
        return 1

    digest = tree_hash(root)
    built_at = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    document = build_json(digest, args.built_from, args.run_id, built_at)
    out_path = root / "build.json"
    out_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    flag_on = read_boolean(PAGES_DUTY_FLAG, default=False)
    live_text = _fetch_live_text(args.live_url)
    changed = decide_deploy(digest, live_text, flag_on=flag_on)

    print(f"tree_hash={digest}")
    print(f"changed={'true' if changed else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
