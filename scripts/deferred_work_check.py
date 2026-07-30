#!/usr/bin/env python3
"""Detector: no deferred-work entry lives ONLY in gitignored Tier-3.

Why this exists
---------------
bmad-loop's follow-up-review damping has a safety valve: when
``limits.max_followup_reviews`` is spent while a review still recommends an
independent follow-up, the orchestrator force-converges and **refiles the
recommendation into the deferred-work ledger** rather than burning another cycle.

That valve writes to ``implementation-artifacts/deferred-work.md`` — which is
**gitignored**. So "we'll catch it in the ledger later" is false by default: the
note lands in scratch space that does not survive a clone or a worktree teardown.

pyforge-atlas has already lost data exactly this way (its live ledger is still
truncated to 10 of 57 entries, collateral of the 2026-07-19 copy failure), and
two consecutive Epic-10 stories (10.5, 10.6) were damped with their
recommendations written only to Tier-3. Both became durable only because a human
promoted them by hand — nothing in the loop would have.

This detector closes that gap from the outside. bmad-loop is an installed conda
package; patching its refile target would be undone by the next reinstall, so the
durable fix is a repo-side check that FAILS when a Tier-3 ``DW-*`` id has no
tracked twin.

What it checks
--------------
For every ``_bmad-output/projects/<slug>/``:

  Tier-3   implementation-artifacts/deferred-work.md        (gitignored, scratch)
  tracked  planning-artifacts/deferred-work-ledger.md       (durable, source of record)

Every ``DW-*`` id in the Tier-3 file must appear somewhere in the tracked ledger.
The comparison is by ID, deliberately loose about body text: the tracked entry is
expected to be REWRITTEN on promotion (renamed to the ledger's
``DW-<story>-<n>`` convention, given a resolution, cross-referenced), so
demanding identical prose would fire on every correctly-promoted entry.

A bare generic id (``DW-1``, ``DW-2``) is reported with a hint, because that is
what the loop emits and it collides with the next run that emits one — the
promoted entry should be renamed.

Exit codes
----------
0  every Tier-3 id has a tracked twin (or no Tier-3 ledger exists)
1  at least one id is Tier-3-only

Usage: ``pixi run -e local-recipes deferred-work-check [-- --json]``
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS = REPO_ROOT / "_bmad-output" / "projects"

TIER3 = Path("implementation-artifacts") / "deferred-work.md"
TRACKED = Path("planning-artifacts") / "deferred-work-ledger.md"

# `DW-` then id chars. Trailing separators are stripped so `DW-B4-`, which appears
# in prose as a family prefix, does not read as a distinct id.
_DW_RE = re.compile(r"\bDW-[A-Za-z0-9][A-Za-z0-9-]*")
# The loop's own un-namespaced output: DW-1, DW-2, ...
_GENERIC_RE = re.compile(r"^DW-\d+$")


def _ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    return {m.group(0).rstrip("-") for m in _DW_RE.finditer(text)}


# A Tier-3 ledger below this is boilerplate (a header and no deferrals worth keeping).
_SUBSTANTIVE_BYTES = 2048


def scan() -> list[dict]:
    findings: list[dict] = []
    if not PROJECTS.is_dir():
        return findings
    for proj in sorted(p for p in PROJECTS.iterdir() if p.is_dir()):
        t3_path, tracked_path = proj / TIER3, proj / TRACKED
        if not t3_path.is_file():
            continue

        # FILE-level check, and the reason this detector nearly shipped useless: an
        # ID-only comparison silently passes a project with NO tracked ledger at all
        # whose Tier-3 entries happen not to use `DW-` ids. pyforge-herald (26K) and
        # pyforge-doctor (6.4K) are exactly that, and warden carries 62K of which only
        # two entries are ID'd. Measure the FILE, not just the ids in it.
        size = t3_path.stat().st_size
        if not tracked_path.is_file() and size >= _SUBSTANTIVE_BYTES:
            findings.append(
                {
                    "kind": "no-tracked-ledger",
                    "project": proj.name,
                    "id": "",
                    "tier3": str(t3_path.relative_to(REPO_ROOT)),
                    "tracked": str(tracked_path.relative_to(REPO_ROOT)),
                    "tier3_bytes": size,
                    "generic_id": False,
                }
            )

        t3 = _ids(t3_path)
        if not t3:
            continue
        tracked = _ids(tracked_path)
        for dw in sorted(t3 - tracked):
            findings.append(
                {
                    "kind": "tier3-only-deferral",
                    "project": proj.name,
                    "id": dw,
                    "tier3": str((proj / TIER3).relative_to(REPO_ROOT)),
                    "tracked": str((proj / TRACKED).relative_to(REPO_ROOT)),
                    "generic_id": bool(_GENERIC_RE.match(dw)),
                }
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    findings = scan()

    if args.json:
        print(json.dumps({"findings": findings}, indent=2))
        return 1 if findings else 0

    scanned = sorted(
        p.name for p in PROJECTS.iterdir() if p.is_dir() and (p / TIER3).is_file()
    ) if PROJECTS.is_dir() else []
    print(f"Deferred-work durability — {len(scanned)} project(s) with a Tier-3 ledger"
          + (f": {', '.join(scanned)}" if scanned else ""))

    if not findings:
        print("\nOK: every Tier-3 deferral has a tracked twin.")
        return 0

    print(f"\nFINDINGS ({len(findings)}):")
    for f in findings:
        if f["kind"] == "no-tracked-ledger":
            print(f"  ✗ [no-tracked-ledger] {f['project']}: {f['tier3']} holds "
                  f"{f['tier3_bytes'] / 1024:.0f} KB of deferred work and "
                  f"{f['tracked']} does not exist — the WHOLE record is gitignored.")
            continue
        hint = ""
        if f["generic_id"]:
            hint = ("  — a generic id: bmad-loop's own damping output. Rename it to the "
                    "ledger's DW-<story>-<n> convention on promotion, or the next damped "
                    "story collides with it.")
        print(f"  ✗ [{f['kind']}] {f['project']}/{f['id']}: present in {f['tier3']} "
              f"but NOT in {f['tracked']}{hint}")
    print("\nTier-3 is gitignored — an entry only there does not survive a clone or a\n"
          "worktree teardown. Promote it into the tracked ledger (rewriting the body and\n"
          "adding a resolution is expected), then re-run.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
