#!/usr/bin/env python3
"""Detector: the eight station planning spines are CURRENT — staleness + coherence only.

The currency axis of the per-project CAP-3 chain audit, swept across every station in
one run. `chain-layers-audit-check` audits ONE project across ALL FOUR checkpoints
(layers, coherence, staleness, orphans); this sweep deliberately narrows to the two
checkpoints the chain-currency reconciler owns (Dream:
docs/dreams/chain-currency-sweep.md; runbook:
_bmad-output/projects/pyforge-doctor/CHAIN-CURRENCY-RUNBOOK.md):

* **staleness** — a feeds edge fired (research newer than brief, spec newer than PRD,
  code newer than retro, …) or a still-building chain's contract fell behind its code.
* **coherence** — a spec overtaken by its own downstream (open questions while PRD +
  arch exist), an unowned chain, a chain with no Dream.

Layer gaps and orphans are EXCLUDED on purpose: they are policy work owned by the
chain-completeness detectors (and the pending deck-policy decision), and folding the
80-chain deck gap into this exit code would make the sweep permanently red — the
"always red, gets ignored" trap the currency logic itself documents suppressing.

scope=repo: the audit reads tracked planning artifacts, dreams, and the tracked
sprint ledgers only. Exit 0 all current; 1 any staleness/coherence finding; 2 a
station's audit could not run (unknown, never green). Pass --json for machine output,
--project <slug> to sweep one station.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DETECTOR = {"scope": "repo"}

REPO_ROOT = Path(__file__).resolve().parent.parent

STATIONS = (
    "pyforge-atlas",
    "pyforge-doctor",
    "pyforge-herald",
    "pyforge-marshal",
    "pyforge-mason",
    "pyforge-scribe",
    "pyforge-steward",
    "pyforge-warden",
)

CURRENCY_CHECKS = frozenset(
    {"chain-audit-checkpoint-staleness", "chain-audit-checkpoint-coherence"}
)


def _audit(slug: str) -> tuple[list[dict], str | None]:
    """(currency findings, error) for one station. error means COULD NOT RUN."""
    proc = subprocess.run(
        [sys.executable, "-m", "pyforge.doctor.sources", "chain-completeness",
         "--layers", "--project", slug, "--json"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    out = proc.stdout
    # The gather prints a human [fleet] preamble before the JSON array; the array
    # starts at the first line that is exactly "[".
    lines = out.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "["), None)
    if start is None:
        detail = (proc.stderr or out or "no output").strip().splitlines()
        return [], f"{slug}: no JSON array in audit output ({detail[-1] if detail else 'empty'})"
    try:
        findings = json.loads("\n".join(lines[start:]))
    except json.JSONDecodeError as exc:
        return [], f"{slug}: audit JSON unparseable ({exc})"
    hits = [
        {**f, "project": slug}
        for f in findings
        if f.get("check") in CURRENCY_CHECKS and f.get("status") == "fail"
    ]
    return hits, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--project", metavar="SLUG", choices=STATIONS,
                    help="sweep a single station instead of all eight")
    args = ap.parse_args()

    slugs = (args.project,) if args.project else STATIONS
    all_hits: list[dict] = []
    errors: list[str] = []
    for slug in slugs:
        hits, err = _audit(slug)
        if err:
            errors.append(err)
            if not args.json:
                print(f"[chain-currency] {slug}: UNKNOWN — {err}")
            continue
        all_hits.extend(hits)
        if not args.json:
            state = "current" if not hits else f"{len(hits)} currency checkpoint fail(s)"
            print(f"[chain-currency] {slug}: {state}")
            for h in hits:
                print(f"[chain-currency]   {h['check']}: {h.get('message', '')}")

    if args.json:
        print(json.dumps({"findings": all_hits, "errors": errors}, indent=2))

    if all_hits:
        if not args.json:
            print(f"[chain-currency] FINDINGS: {len(all_hits)} across "
                  f"{len({h['project'] for h in all_hits})} station(s) — run the "
                  f"reconciler sweep (CHAIN-CURRENCY-RUNBOOK.md)")
        return 1
    if errors:
        return 2
    if not args.json:
        print(f"[chain-currency] all {len(slugs)} station spine(s) current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
