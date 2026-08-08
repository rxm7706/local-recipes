#!/usr/bin/env python
"""Static-JSON snapshot exporter for the Herald web dashboard (Story 9.4's
"static-JSON-snapshot pattern"). No shared exporter existed anywhere in
this package when Epic 9 landed (2026-08-08) -- this script is that shared
exporter, kept deliberately thin (I/O only) so a future Epic 8/10 snapshot
adds a sibling ``export_*_snapshot`` function here rather than a duplicate
script; the actual data shaping lives in ``claims.snapshot``/``to_dict``,
reused by both this script and ``herald success --json``.

The web app is a plain static Vite bundle with no server (Epic 7) -- this
script is how ``.herald/claims.json`` (local, operator-machine-only)
becomes something the browser can ``fetch()``. Run it by hand, or wire it
into a build/deploy step; it is not triggered automatically by ``herald
success publish`` (publishing and re-exporting the web snapshot are
deliberately separate operations, same reasoning as ``herald deck
push`` staying separate from ``herald deck pull`` -- see cli.py's
``_run_deck_push`` docstring).

Usage:
    python scripts/export_web_snapshot.py [--repo-root PATH] [--out-dir PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PACKAGE_ROOT = _SCRIPT_DIR.parent
_SRC_DIR = _PACKAGE_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    # Only needed for an uninstalled/editable checkout -- a no-op once
    # pyforge-herald is installed (conda pkg or `pip install -e .`).
    sys.path.insert(0, str(_SRC_DIR))

from pyforge.herald import claims

DEFAULT_OUT_DIR = _PACKAGE_ROOT / "web" / "public"


def export_success_snapshot(*, repo_root: Path, out_dir: Path) -> Path:
    """Write ``out_dir/success.json`` -- every published claim under
    ``repo_root/.herald/claims.json``, newest first. Returns the written
    path."""
    claims_path = repo_root / claims.DEFAULT_CLAIMS_PATH
    payload = claims.snapshot(claims_path, status="published")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "success.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="repo root containing .herald/claims.json (default: cwd)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"directory to write success.json into (default: {DEFAULT_OUT_DIR})",
    )
    args = parser.parse_args(argv)
    out_path = export_success_snapshot(repo_root=args.repo_root, out_dir=args.out_dir)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
