---
title: The dispatched run survives its operator, and its journal carries the timing signal
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 4945e8abc6
---

<intent-contract>

## Intent

**Problem:** Dispatched runs die with the operator terminal — no attach/resume, no unsupervised reconciliation, no timing signal for Epic 23 (FR-193 CAP-6).

**Approach:** Killing the dispatching terminal leaves the session running; `marshal status` reports from journal + process facts; attach/resume recovers supervision; story completed while unsupervised reconciles from git facts; failed/abandoned worktree + diff survive (`changes.patch` analog); journal records per-story start/end and baseline→final revisions. Deps: 22.1 done. Completes Epic 22 dispatch slice.

## Acceptance Criteria

- Terminal kill does not stop dispatched session; status from journal + process facts alone.
- Attach/resume recovers supervision of live dispatch.
- Unsupervised completion reconciled from git facts (not lost).
- Abandoned session worktree and diff preserved for recovery.
- Journal carries per-story timing + baseline→final revision fields (Epic 23 effort signal source).
- Epic 22 CAP-1..CAP-6 dispatch path complete after this story.

## Boundaries & Constraints

**Never:** Busy-wait in foreground attach path. Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-marshal-single-story-dispatch/SPEC.md` (CAP-6)
- Journal + attach/resume (AD-22/AD-25/AD-30); Epic 1 work-preservation discipline
- `cli/dispatch.py`, `dispatch_supervisor`, `core/status.py`
- Tests: terminal-survival, attach/resume, unsupervised reconcile, journal timing fields

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
