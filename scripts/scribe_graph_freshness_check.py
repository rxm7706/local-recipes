#!/usr/bin/env python3
"""Freshness of the compiled scribe knowledge graph (Story 8.1, CAP-2).

WHAT IT CHECKS
--------------
The mtime of `.claude/data/pyforge-scribe/graph.json` -- the derived,
gitignored compiled-graph store `scribe graph compile` writes -- against the
nightly trigger's own schedule period (nightly = 24h, matching
`pyforge-scribe-nightly-compile.timer`'s `OnCalendar=*-*-* 02:30:00`, under
`src/shared/packages/pyforge-scribe/ops/systemd/`). Older than that period
surfaces as a finding: proof the trigger fired recently, not a second PR
gate (spec-8-1's own Boundaries & Constraints: "surfaces as an advisory
finding only -- never a PR gate, never a second verdict alongside the
detector set's existing gates"). `graph.json` itself stays read-only here --
this never promotes or duplicates its content, only inspects its mtime.

DEGRADATION
-----------
No `graph.json` at all (a fresh checkout, or a machine that never installed
the trigger) is its own advisory finding, not an error -- the store is
entirely optional until the trigger is installed.

EXIT
    0  graph.json is present and fresh
    1  graph.json is missing or older than the schedule's own period
"""
from __future__ import annotations

# Registry declaration -- see scripts/detectors.py. `runtime`: reads a
# gitignored, host-local derived artifact (.claude/data/pyforge-scribe/
# graph.json) a CI runner never populates -- exactly the false-green risk
# index_freshness_check.py names for its own runtime indices.
DETECTOR = {"scope": "runtime"}

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH_STORE_PATH = ROOT / ".claude" / "data" / "pyforge-scribe" / "graph.json"

# The nightly trigger's own period -- keep in sync BY HAND with
# pyforge-scribe-nightly-compile.timer's `OnCalendar=*-*-* 02:30:00` (once
# every 24h); parsing systemd calendar syntax has no cheap runtime value for
# one nightly cadence.
SCHEDULE_PERIOD_HOURS = 24


def check_freshness(
    graph_path: Path, *, now: float | None = None
) -> tuple[str, str, float | None]:
    """Returns (status, reason, age_hours). status is one of 'ok', 'missing',
    'stale'. age_hours is None when it could not be computed (missing store,
    or an unreadable mtime)."""
    if not graph_path.exists():
        return (
            "missing",
            f"no compiled graph store at {graph_path} -- the nightly trigger "
            "has never run on this machine (or was never installed; see "
            "docs/cli-runbooks.md 'Installing the nightly trigger')",
            None,
        )

    try:
        mtime = graph_path.stat().st_mtime
    except OSError as exc:
        return (
            "ok",
            f"graph store present at {graph_path}; freshness not evaluated "
            f"(mtime unreadable: {exc})",
            None,
        )

    resolved_now = now if now is not None else time.time()
    # Clamp to non-negative: a future mtime (clock skew, a restored
    # snapshot) must never report a nonsensical negative-hour age.
    age_hours = max(0.0, (resolved_now - mtime) / 3600)
    if age_hours > SCHEDULE_PERIOD_HOURS:
        return (
            "stale",
            f"graph store at {graph_path} is {age_hours:.1f}h old, older "
            f"than the nightly trigger's own {SCHEDULE_PERIOD_HOURS}h period "
            "-- it may not be installed, or may have stopped firing",
            age_hours,
        )
    return (
        "ok",
        f"graph store at {graph_path} is {age_hours:.1f}h old (fresh)",
        age_hours,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="output as JSON")
    # `[] if argv is None else argv`, never a bare `parse_args(argv)` --
    # argparse's own default falls back to `sys.argv[1:]`, which leaks a
    # test runner's own CLI args (e.g. pytest's) into this parser when a
    # test calls `main()` with no arguments (missing_preserve_check.py's own
    # precedent for this exact trap).
    args = parser.parse_args([] if argv is None else argv)

    status, reason, age_hours = check_freshness(GRAPH_STORE_PATH)

    findings: list[dict[str, str]] = []
    if status == "missing":
        findings.append({"code": "SCRIBE-GRAPHFRESH-001", "message": reason})
    elif status == "stale":
        findings.append({"code": "SCRIBE-GRAPHFRESH-002", "message": reason})

    if args.json:
        print(
            json.dumps(
                {
                    "status": status,
                    "age_hours": age_hours,
                    "reason": reason,
                    "_findings": findings,
                }
            )
        )
    else:
        if findings:
            print("scribe-graph-freshness -- advisory only, never a PR gate\n")
            for finding in findings:
                print(f"  {finding['code']} — {finding['message']}")
            print()
        else:
            print(f"scribe-graph-freshness — {reason}")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
