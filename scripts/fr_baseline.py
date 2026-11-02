#!/usr/bin/env python
"""Mutation-only companion to `fr-without-cap-check` (doctor Stories 25.2, 50.1 and 50.2).

    python scripts/fr_baseline.py --prune                    # the ONLY routine verb: drop ids
                                                             # that gained an arrow and findings
                                                             # keys that stopped firing
    python scripts/fr_baseline.py --project pyforge-<s>      # at that station's fold PR:
                                                             # re-snapshot its arrowless ids;
                                                             # refused when it would ADD one
                                                             # (--force only after a review that
                                                             # names each ADDED id in the PR)
    python scripts/fr_baseline.py --snapshot-findings        # ONE-TIME: write the `findings` map;
                                                             # refused once it exists (--force only
                                                             # after a review that names each
                                                             # ADDED key in the PR)
    python scripts/fr_baseline.py --snapshot                 # ONCE, at the ruling SHA

The operator rule (CAP-92): the baseline only shrinks. `projects` lists, per
station, the FR/NFR ids whose definition carried no citation when snapshotted
-- an FR that has an arrow is enforced forever. `findings` lists the
structural arrow-grammar findings (`<check>:<FR-id>`) present at
`findings_sha`; the detector reports them as `fr-baselined`, never FAIL, and
WARNs `fr-baseline-stale` for an entry that no longer applies. A new finding
is never laundered in: `--snapshot-findings` prints the keys it would ADD and
REMOVE and refuses when a `findings` map already exists, unless `--force`.
`--project` re-baselines ONE station and carries every other station's entry
over untouched; it prints the ids it would ADD and REMOVE and refuses an ADD
unless `--force` (doctor Story 50.2). A bare re-snapshot after the ruling is
refused without `--force`: it would launder every un-cited FR minted since.

Every key a write ADDS to the file it read is recorded in the file's `forced`
list with this run's HEAD (`record_fr_additions`). That record is the only
escape `fr-without-cap` admits for a key added since the merge-base with
origin/main (`fr-baseline-grown`, doctor Story 50.2): a hand edit, or an
`owners` row, never admits one. `--prune` drops a record whose key it removed.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "packages" / "pyforge-doctor" / "src"))

from pyforge.doctor.sources.one_chain import (  # noqa: E402
    FR_BASELINE_REL,
    prune_fr_baseline,
    record_fr_additions,
    snapshot_fr_baseline,
    snapshot_fr_findings,
)


def _head_sha(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _print_delta(old: dict[str, list[str]], new: dict[str, list[str]]) -> int:
    """Print, per station, the keys a `findings` or `projects` rewrite would ADD
    and REMOVE; return the number it would add."""
    added_total = 0
    for slug in sorted(set(old) | set(new)):
        before, after = set(old.get(slug, [])), set(new.get(slug, []))
        added, removed = sorted(after - before), sorted(before - after)
        added_total += len(added)
        if added or removed:
            print(f"{slug}: +{len(added)} -{len(removed)}")
            for key in added:
                print(f"  ADD    {key}")
            for key in removed:
                print(f"  REMOVE {key}")
    return added_total


def _print_recorded(recorded: list[tuple[str, str, str]], head: str) -> None:
    for slug, kind, key in recorded:
        print(f"  FORCED {slug} {kind} {key} @ {head}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fr-baseline", description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", action="store_true", help="take the fleet snapshot (once)")
    g.add_argument("--project", metavar="pyforge-<s>", help="re-baseline one station (at its fold PR)")
    g.add_argument(
        "--snapshot-findings",
        action="store_true",
        help="write the `findings` map (one-time; refused once it exists unless --force)",
    )
    g.add_argument("--prune", action="store_true", help="remove entries that no longer apply (never adds)")
    ap.add_argument("--ruling-sha", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    root = REPO_ROOT
    path = root / FR_BASELINE_REL
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
        data, removed = prune_fr_baseline(root)
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
        new = snapshot_fr_findings(root)
        old = existing.get("findings")
        if isinstance(old, dict):
            added = _print_delta(old, new)
            if not args.force:
                print(f"refusing: `findings` already exists ({added} key(s) would be ADDED) — the map only "
                      f"shrinks: `--prune` is the routine verb; `--force` only after a review that names "
                      f"each added key in the PR")
                return 1
        previous = copy.deepcopy(existing)
        head = _head_sha(root)
        existing["findings"] = new
        existing["findings_sha"] = head
        recorded = record_fr_additions(previous, existing, head)
        _write(path, existing)
        for slug, keys in new.items():
            print(f"{slug}: {len(keys)} finding(s)")
        _print_recorded(recorded, head)
        return 0

    head = _head_sha(root)
    data = snapshot_fr_baseline(
        root,
        ruling_sha=args.ruling_sha or (existing or {}).get("ruling_sha") or head,
        only_project=args.project,
        existing=existing,
    )
    if args.project:
        before = (existing or {}).get("projects")
        added = _print_delta(before if isinstance(before, dict) else {}, data["projects"])
        if added and not args.force:
            print(f"refusing: --project {args.project} would ADD {added} id(s) to `projects` — the baseline only "
                  f"shrinks: `--prune` is the routine verb; `--force` only at the station's fold PR, after a review "
                  f"that names each added id in the PR")
            return 1
        data["rebaselined"] = {**(existing or {}).get("rebaselined", {}), args.project: head}
    recorded = record_fr_additions(existing, data, head)
    _write(path, data)
    _print_recorded(recorded, head)
    total = sum(len(v) for v in data["projects"].values())
    scope = args.project or "fleet"
    print(f"{scope}: {total} arrowless FR/NFR id(s) across {len(data['projects'])} station PRD(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
