---
title: Baseline-drift defers get loud
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 9ca74754a3
---

<intent-contract>

## Intent

**Problem:** CAP-1 (`scripts/bmad_loop_baseline_drift_check.py`, Story 20.1 / PR #680) detects unrecovered baseline-drift defers, but FR-188 CAP-2 requires loud-defer containment: the finding must exit non-zero **and** surface where the operator already looks (`fleet-picture` ATTENTION), naming recovery inputs so a live recurrence cannot read healthy.

**Approach:** Complete CAP-2 on top of the shipped CAP-1 detector — wire/verify ATTENTION-plane surfacing (exit/report path + `fleet-picture` or equivalent). Pre-existing ATTENTION probe stubs in `scripts/fleet_picture.py` may already call the detector; this story owns proving the contract end-to-end and closing any gaps (message richness, tests, healthy-run silence). Loud defer only — never quiet auto-land. Do not edit `bmad_loop`.

## Acceptance Criteria

- Unrecovered baseline-drift fixture/run → detector exits non-zero **and** `fleet-picture` (or documented equivalent ATTENTION surface) names recovery inputs: story, run, preserved ref/patch, drifted-vs-real baselines (inline or via an unambiguous pointer to `baseline-drift-check` output that carries those fields).
- Clean / recovered state → no ATTENTION need line for baseline-drift; containment output cannot read healthy when an unrecovered defer exists.
- No quiet auto-land of deferred work; no edits to the `bmad_loop` package.
- Does not implement 20.3 upstream filing or 20.4–20.10.

## Boundaries & Constraints

**Never:** Edit `bmad_loop`. Never implement 20.3–20.10. Never `scripts/bmad-switch`. Finalize marshal ledger only. Do not touch steward 15-4.

</intent-contract>

## Code Map

- `scripts/bmad_loop_baseline_drift_check.py` (CAP-1 exit/report — extend only if CAP-2 needs richer stdout for ATTENTION)
- `scripts/fleet_picture.py` ATTENTION probe (baseline-drift block)
- Tests under `tests/scripts/` for ATTENTION / exit loudness

## Verification

- Fixture unrecovered → non-zero + ATTENTION names recovery inputs
- Clean/recovered → silent on this axis
- `pixi run --frozen -e local-recipes` related pytest green; CI package tests
