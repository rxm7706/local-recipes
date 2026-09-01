---
title: 'Stranded-work signal after terminal verify-fail (Story 28.23, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'ready'
updated: '2026-09-01'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: small
baseline_revision: 20e88e8b0fd1ccd2cc38101691ac72aeb8df71cc
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-drain-self-resolution/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** After 28.17 terminalized verify-fail, fleet-picture still showed
**STUCK** (`derive_dispatch_phase` stayed `verifying`). Overlay was patched
(`20e88e8b0f`) but stranded work (unpushed branch / open PR) still has no
ATTENTION line — that was how 28.13 hid off `main`.

**Approach:** Lock the dead-tail overlay with a test. Name unpushed
`dispatch/<slug>/<story>` or an open unmerged PR in fleet-picture ATTENTION.

## Acceptance Criteria

- Given completion `failed` or `stopped_externally` and a dead tail, when
  status / fleet-picture run, then the home is not `verifying` / STUCK.
- Given an unpushed dispatch branch or open unmerged PR for that story, when
  fleet-picture runs, then ATTENTION names it.
- Given `20e88e8b0f` overlay behavior, when `TestDeriveDispatchPhase` runs,
  then `failed` + dead tail is `None`.

## Boundaries & Constraints

**Never:** Treat overlay as the only stranded-work signal. `scripts/bmad-switch`.

Ledger key: `28-23-stranded-work-signal-after-terminal-verify-fail`.

</intent-contract>

## Code Map

- `core/status.py` — `derive_dispatch_phase` (lock)
- `scripts/fleet_picture.py` — ATTENTION for unpushed dispatch refs / open PRs
- `tests/unit/test_status.py` — existing `test_failed_with_dead_tail_is_not_verifying`

## Verification

- `pixi run --frozen -e pyforge-marshal pytest …/test_status.py::TestDeriveDispatchPhase -q`
- fleet-picture unit / fixture if present
