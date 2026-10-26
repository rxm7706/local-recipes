#!/usr/bin/env python
"""Mutation-only companion to `fr-without-cap-check` (doctor Stories 25.2 and 50.1).

    python scripts/fr_baseline.py --snapshot                 # ONCE, at the ruling SHA
    python scripts/fr_baseline.py --project pyforge-<s>      # at that station's fold PR:
                                                             # re-snapshot its arrowless ids
    python scripts/fr_baseline.py --snapshot-findings        # rewrite the `findings` map
                                                             # (every station) at HEAD
    python scripts/fr_baseline.py --prune                    # drop ids that gained an arrow
                                                             # and findings keys that stopped firing

`projects` lists, per station, the FR/NFR ids whose definition carried no
citation when snapshotted -- an FR that has an arrow is enforced forever, so
the list only shrinks. `findings` lists the structural arrow-grammar findings
(`<check>:<FR-id>`) present at `findings_sha`; the detector reports them as
`fr-baselined`, never FAIL, and WARNs `fr-baseline-stale` for a key that no
longer fires. `--project` re-baselines ONE station and carries every other
station's entry over untouched. A bare re-snapshot after the ruling is
refused without `--force`: it would launder every un-cited FR minted since.
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
    FR_BASELINE_REL,
    prune_fr_baseline,
    snapshot_fr_baseline,
    snapshot_fr_findings,
)


def _head_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fr-baseline", description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", action="store_true", help="take the fleet snapshot (once)")
    g.add_argument("--project", metavar="pyforge-<s>", help="re-baseline one station (at its fold PR)")
    g.add_argument("--snapshot-findings", action="store_true", help="rewrite the `findings` map for every station")
    g.add_argument("--prune", action="store_true", help="remove entries that no longer apply (never adds)")
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
    if not args.snapshot and existing is None:
        print(f"no baseline at {FR_BASELINE_REL.as_posix()}; take --snapshot first")
        return 1

    if args.prune:
        data, removed = prune_fr_baseline(REPO_ROOT)
        if data is None:
            print(f"{FR_BASELINE_REL.as_posix()} is unreadable; nothing pruned")
            return 1
        _write(path, data)
        print(f"pruned {len(removed)} entr{'y' if len(removed) == 1 else 'ies'}" + (":" if removed else ""))
        for entry in removed:
            print(f"  {entry}")
        return 0

    if args.snapshot_findings:
        assert existing is not None
        existing["findings"] = snapshot_fr_findings(REPO_ROOT)
        existing["findings_sha"] = _head_sha()
        _write(path, existing)
        for slug, keys in existing["findings"].items():
            print(f"{slug}: {len(keys)} finding(s)")
        return 0

    data = snapshot_fr_baseline(
        REPO_ROOT,
        ruling_sha=args.ruling_sha or (existing or {}).get("ruling_sha") or _head_sha(),
        only_project=args.project,
        existing=existing,
    )
    if args.project:
        data["rebaselined"] = {**(existing or {}).get("rebaselined", {}), args.project: _head_sha()}
    _write(path, data)
    total = sum(len(v) for v in data["projects"].values())
    scope = args.project or "fleet"
    print(f"{scope}: {total} arrowless FR/NFR id(s) across {len(data['projects'])} station PRD(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
