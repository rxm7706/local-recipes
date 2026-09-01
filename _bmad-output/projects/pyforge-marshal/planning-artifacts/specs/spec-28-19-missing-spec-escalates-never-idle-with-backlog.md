---
title: 'Missing-spec escalates, never idle-with-backlog (Story 28.19, Epic 28)'
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
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Steward 39.4 looked **idle** while remaining=1 because
`MRS-DISP-005` is a refuse, not an escalation. Operators read idle as drained.

**Approach:** v1 does **not** auto-author a stub spec. Preflight refuse for a
missing tracked spec sets `awaiting-operator` (or fleet-picture ATTENTION) and
names the expected `spec-<e>-<n>-*.md` path.

## Acceptance Criteria

- Given a ledger key whose specs glob is empty, when drain preflight refuses,
  then the station is not reported idle while remaining > 0.
- Given that refuse, when `marshal status` / fleet-picture run, then ATTENTION
  (or `awaiting-operator`) names the expected spec path.
- Given this story, when reviewed, then no code writes a new story spec file.

## Boundaries & Constraints

**Never:** Auto-draft specs. `scripts/bmad-switch`. Hide remaining backlog.

Ledger key: `28-19-missing-spec-escalates-never-idle-with-backlog`.

</intent-contract>

## Code Map

- `cli/dispatch.py` / `core/dispatch_fleet.py` — refuse → station state
- `core/status.py` / `scripts/fleet_picture.py` — ATTENTION / awaiting-operator
- Tests: status + fleet-picture unit fixtures

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
