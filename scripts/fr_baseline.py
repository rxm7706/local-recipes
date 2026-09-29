#!/usr/bin/env python
"""Mutation-only companion to `fr-without-cap-check` (doctor Story 25.2).

    python scripts/fr_baseline.py --snapshot                 # ONCE, at the ruling SHA
    python scripts/fr_baseline.py --project pyforge-<s>      # at that station's fold PR,
                                                             # after its PRD is re-derived
                                                             # FR <- CAP in full

`--project` re-baselines ONE station and carries every other station's entry
over untouched. A bare re-snapshot after the ruling is refused without
`--force`: it would launder every un-cited FR minted since.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "packages" / "pyforge-doctor" / "src"))

from pyforge.doctor.sources.one_chain import FR_BASELINE_REL, snapshot_fr_baseline  # noqa: E402


def _head_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fr-baseline", description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", action="store_true", help="take the fleet snapshot (once)")
    g.add_argument("--project", metavar="pyforge-<s>", help="re-baseline one station (at its fold PR)")
    ap.add_argument("--ruling-sha", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    path = REPO_ROOT / FR_BASELINE_REL
    existing = None
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None

    if args.snapshot and existing is not None and not args.force:
        print(f"refusing: {FR_BASELINE_REL.as_posix()} exists — re-baseline per station with "
              f"--project at its fold PR, or --force if you really mean it")
        return 1
    if args.project and existing is None:
        print(f"no baseline at {FR_BASELINE_REL.as_posix()}; take --snapshot first")
        return 1

    data = snapshot_fr_baseline(
        REPO_ROOT,
        ruling_sha=args.ruling_sha or (existing or {}).get("ruling_sha") or _head_sha(),
        only_project=args.project,
        existing=existing,
    )
    if args.project:
        data["rebaselined"] = {**(existing or {}).get("rebaselined", {}), args.project: _head_sha()}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    total = sum(len(v) for v in data["projects"].values())
    scope = args.project or "fleet"
    print(f"{scope}: {total} FR/NFR ids across {len(data['projects'])} station PRD(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
