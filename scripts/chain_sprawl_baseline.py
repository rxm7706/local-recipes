#!/usr/bin/env python
"""Mutation-only companion to `chain-sprawl-check` (doctor Story 25.1).

The detector itself is read-only (`python -m pyforge.doctor.sources
chain-sprawl`). This script owns the two writes the baseline ever takes:

    python scripts/chain_sprawl_baseline.py --snapshot   # ONCE, at the ruling SHA
    python scripts/chain_sprawl_baseline.py --prune      # after a fold: remove
                                                         # entries that no longer exist

`--snapshot` refuses when a baseline already exists (the dated snapshot is
taken once; re-taking it would launder every folder minted since). `--prune`
only ever removes. There is deliberately no `--add`: adding an entry is what
`fold-exemption:` in the artifact's own frontmatter is for.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "packages" / "pyforge-doctor" / "src"))

from pyforge.doctor.sources.one_chain import (  # noqa: E402
    CHAIN_SPRAWL_BASELINE_REL,
    prune_chain_sprawl_baseline,
    snapshot_chain_sprawl_baseline,
)


def _head_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="chain-sprawl-baseline", description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", action="store_true", help="take the dated snapshot (once)")
    g.add_argument("--prune", action="store_true", help="remove entries that no longer exist")
    ap.add_argument("--ruling-sha", default=None, help="SHA to record (default: HEAD)")
    ap.add_argument("--force", action="store_true", help="allow --snapshot over an existing baseline")
    args = ap.parse_args(argv)

    path = REPO_ROOT / CHAIN_SPRAWL_BASELINE_REL
    if args.snapshot:
        if path.exists() and not args.force:
            print(f"refusing: {CHAIN_SPRAWL_BASELINE_REL.as_posix()} exists — the snapshot is "
                  f"taken once; use --prune after a fold, or --force if you really mean it")
            return 1
        data = snapshot_chain_sprawl_baseline(REPO_ROOT, ruling_sha=args.ruling_sha or _head_sha())
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"snapshot: {len(data['dreams'])} dreams, {len(data['spec_folders'])} spec folders "
              f"at {data['ruling_sha']}")
        return 0

    data, removed = prune_chain_sprawl_baseline(REPO_ROOT)
    if data is None:
        print(f"cannot read {CHAIN_SPRAWL_BASELINE_REL.as_posix()}")
        return 2
    if not removed:
        print("prune: nothing to remove")
        return 0
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"prune: removed {len(removed)} entr{'y' if len(removed) == 1 else 'ies'}")
    for rel in removed:
        print(f"  - {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
