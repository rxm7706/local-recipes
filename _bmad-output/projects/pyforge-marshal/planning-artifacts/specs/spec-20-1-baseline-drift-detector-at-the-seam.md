---
title: Baseline-drift detector at the seam
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-23'
shipped_ref: 'PR #680 / 3a4a7bd854'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 8c28d4ce8a
---

<intent-contract>

## Intent

**Problem:** When `bmad_loop` drifts a story's baseline mid-run, work is permanently deferred with no Marshal-side detector reading only the loop's own feeds (FR-188 / spec-bmad-loop-baseline-drift CAP-1). Five live occurrences in one session (PRs #482–#484 class).

**Approach:** Ship a detector that reads only feeds `bmad_loop` itself writes (`journal.jsonl`, `state.json`, `attempt-preserve/*` refs, `failed/*/changes.patch`) — never importing or editing the package — and fires naming the story, both baselines (real vs drifted), and the preserve ref. Clean runs yield no finding. Placement decision (this story): `scripts/*.py` (loop-stall-check precedent) or `pyforge.doctor.sources` (story-status-check precedent). Scope=runtime like `loop-stall-check` — excluded from `detectors-ci`.

## Acceptance Criteria

- Detector reproduces finding on fixture/journal shaped like run `20260813-094919-bfcb` story 9-6: names story, real baseline `523e938c7978`, drifted `26102ea12c6d`, and preserve ref.
- Clean-run fixture → no finding.
- Read-only over loop feeds; does not import or mutate `bmad_loop`.
- Scope=runtime; not registered in `detectors-ci`.
- Does not implement 20.2 “defers get loud” ATTENTION-plane surfacing (deps S-20.1).

## Boundaries & Constraints

**Never:** Edit `bmad_loop` package. Never implement 20.2–20.10. Never `scripts/bmad-switch`. Finalize marshal ledger only. Do not touch steward 15-4.

</intent-contract>

## Code Map

- Detector under `scripts/` or `pyforge.doctor.sources` (decide + document)
- Fixtures from baseline-drift journal / preserve-ref shape
- Meta/unit tests for fire vs clean

## Verification

- Fixture drift → named finding; clean → empty
- `pixi run --frozen -e pyforge-marshal` (and/or doctor env if source lives there) related tests green
- CI package tests; confirm not wired into detectors-ci

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/680
Merge SHA: 3a4a7bd8540a3deda68a77de5a9429fdac63649e
Placement: `scripts/bmad_loop_baseline_drift_check.py` (loop-stall-check precedent; not `pyforge.doctor.sources`)
Tests: `pixi run --frozen -e local-recipes pytest tests/scripts/test_bmad_loop_baseline_drift_check.py -q` → 5 passed
