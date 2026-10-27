#!/usr/bin/env python3
"""Detector: the eight station planning spines are CURRENT — staleness + coherence only.

The currency axis of the per-project CAP-3 chain audit, swept across every station in
one run. `chain-layers-audit-check` audits ONE project across ALL FOUR checkpoints
(layers, coherence, staleness, orphans); this sweep deliberately narrows to the two
checkpoints the chain-currency reconciler owns (Dream:
archive/docs/dreams/chain-currency-sweep.md; runbook:
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
import contextlib
import io
import json
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


def _load_gatherer():
    """The in-process gatherer the subprocess used to call (doctor Story 55.2, AD-1:
    a Doctor source is a library call, never a subprocess reimplementation).
    Returns ``None`` when ``pyforge.doctor`` is not importable here."""
    try:
        from pyforge.doctor.sources import board
    except Exception:  # noqa: BLE001 -- unimportable == COULD NOT RUN, reported per station
        return None
    return board.gather_chain_layers_audit


def _audit(slug: str) -> tuple[list[dict], str | None]:
    """(currency findings, error) for one station. error means COULD NOT RUN.

    Story 55.2: one process for the eight stations. ``gather_chain_layers_audit``
    saves and restores ``fleet_scan``'s module globals per call, so sequential
    calls are independent; its human ``[fleet]`` preamble is swallowed so the
    script's own ``--json`` stays parseable.
    """
    gather = _load_gatherer()
    if gather is None:
        return (
            [],
            f"{slug}: pyforge.doctor is not importable here (run under pixi run -e pyforge-guild)",
        )
    sink = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink):
            findings = gather(REPO_ROOT, slug)
    except Exception as exc:  # noqa: BLE001 -- an audit that raises is COULD NOT RUN, never a crash
        return [], f"{slug}: audit raised {type(exc).__name__}: {exc}"
    rows = [f.to_json_dict() for f in findings]
    hits = [
        {**f, "project": slug}
        for f in rows
        if f.get("check") in CURRENCY_CHECKS and f.get("status") == "fail"
    ]
    return hits, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--project",
        metavar="SLUG",
        choices=STATIONS,
        help="sweep a single station instead of all eight",
    )
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
            state = (
                "current" if not hits else f"{len(hits)} currency checkpoint fail(s)"
            )
            print(f"[chain-currency] {slug}: {state}")
            for h in hits:
                print(f"[chain-currency]   {h['check']}: {h.get('message', '')}")

    if args.json:
        print(json.dumps({"findings": all_hits, "errors": errors}, indent=2))

    if all_hits:
        if not args.json:
            print(
                f"[chain-currency] FINDINGS: {len(all_hits)} across "
                f"{len({h['project'] for h in all_hits})} station(s) — run the "
                f"reconciler sweep (CHAIN-CURRENCY-RUNBOOK.md)"
            )
        return 1
    if errors:
        return 2
    if not args.json:
        print(f"[chain-currency] all {len(slugs)} station spine(s) current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
