---
title: 'Stranded-work signal after terminal verify-fail (Story 28.23, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'done'
updated: '2026-09-02'
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

- `core/status.py` — `derive_dispatch_phase` (lock), `derive_dispatch_stranded_work`, dead-tail overlay publish
- `cli/status.py` — fold stranded-work signal from unpushed-work detector
- `scripts/fleet_picture.py` — ATTENTION for unpushed dispatch refs / open PRs
- `tests/unit/test_status.py` — `TestDeriveDispatchPhase`, `TestDeriveDispatchStrandedWork`
- `tests/meta/test_fleet_picture_stranded_work.py` — ATTENTION assembly

## Verification

- `pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_status.py::TestDeriveDispatchPhase -q`
- `pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_status.py::TestDeriveDispatchStrandedWork -q`
- `pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_fleet_picture_stranded_work.py -q`

## Review Triage Log

### 2026-09-02 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

## Auto Run Result

Status: done

Summary: CAP-6 stranded-work signal — terminal dead-tail dispatch rows publish completion + unpushed-branch evidence via `marshal status`; fleet-picture ATTENTION names unpushed `dispatch/<slug>/<story>` or matching open PR.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py` — `derive_dispatch_stranded_work`, dead-tail overlay publish path
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` — compute stranded work per home
- `scripts/fleet_picture.py` — ATTENTION needs lines + open-PR-by-head helper
- `src/shared/packages/pyforge-marshal/tests/unit/test_status.py` — phase lock + stranded-work tests
- `src/shared/packages/pyforge-marshal/tests/meta/test_fleet_picture_stranded_work.py` — ATTENTION meta tests

Review findings breakdown: 0 patches, 0 deferred, 0 rejected (clean review pass).

Follow-up review recommendation: false (0 patched findings).

Verification performed:
- `pixi run --frozen -e pyforge-marshal pytest …/TestDeriveDispatchPhase …/TestDeriveDispatchStrandedWork …/test_fleet_picture_stranded_work.py -q` — **17 passed** in 1.10s

Residual risks: open-PR ATTENTION depends on `gh pr list` (same degrade pattern as existing open-PR probe); unpushed signal unknown when unpushed-work detector cannot run.
