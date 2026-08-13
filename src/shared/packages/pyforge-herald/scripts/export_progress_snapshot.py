#!/usr/bin/env python
"""Static-JSON snapshot exporter for the Herald web dashboard's Progress
tab (Story 13.3): mirrors ``export_web_snapshot.py``/
``export_notices_snapshot.py``'s shape -- I/O only, the actual data comes
from ``progress.list_records``, reused by ``herald progress --json``.

Replaces ``web/scripts/sync-progress.mjs`` (a raw ``node`` copy of
``.herald/progress.json``), which stopped working once Story 13.3 moved
progress storage into ``.herald/herald.db``: that script read
``.herald/progress.json`` directly, bypassing Python entirely, and would
have silently started exporting an empty snapshot (a ``console.warn``, no
hard failure) once this story stopped writing that file at all. This
script goes through ``progress.py``'s own public read function instead, so
it can never drift from what the CLI itself reports.

Usage:
    python scripts/export_progress_snapshot.py [--repo-root PATH] [--out-dir PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PACKAGE_ROOT = _SCRIPT_DIR.parent
_SRC_DIR = _PACKAGE_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    # Only needed for an uninstalled/editable checkout -- a no-op once
    # pyforge-herald is installed (conda pkg or `pip install -e .`).
    sys.path.insert(0, str(_SRC_DIR))

from pyforge.herald import progress

DEFAULT_OUT_DIR = _PACKAGE_ROOT / "web" / "public"


def export_progress_snapshot(*, repo_root: Path, out_dir: Path) -> Path:
    """Write ``out_dir/progress.json`` -- every recorded progress entry
    under ``repo_root/.herald/herald.db``, newest first (``list_records``'s
    own default order). Returns the written path."""
    progress_path = repo_root / progress.DEFAULT_PROGRESS_PATH
    payload = [asdict(record) for record in progress.list_records(progress_path)]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "progress.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="repo root containing .herald/herald.db (default: cwd)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"directory to write progress.json into (default: {DEFAULT_OUT_DIR})",
    )
    args = parser.parse_args(argv)
    out_path = export_progress_snapshot(repo_root=args.repo_root, out_dir=args.out_dir)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
