---
title: The dispatched run survives its operator, and its journal carries the timing signal
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: e76e1818de6
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

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/706
Merge: b38604e61d48e54a8eb9111b16e328d166566a7d
Merge policy: admin merge (`gh pr merge 706 --merge --admin --repo rxm7706/local-recipes`) — GitHub Actions billing blocks CI; local tests green before merge.
Summary: Story 22.6 (FR-193 CAP-6) adds `marshal factory dispatch-attach` / `dispatch-resume` to re-spawn dead completion supervisors, journals per-story timing (`dispatch-timing` with baseline→final revisions for Epic 23), preserves failed dispatch work under `failed/<story>/changes.patch`, and extends `marshal status` with supervision/timing/preserve fields from journal + process facts alone. Completes Epic 22 dispatch slice (CAP-1..CAP-6).
Files:
- `core/dispatch_preserve.py`, `core/dispatch_survival.py` — preserve paths + timing/supervision pure helpers
- `cli/dispatch.py`, `cli/spin.py` — dispatch-attach/resume verbs, supervisor re-spawn
- `dispatch_supervisor/__main__.py` — timing + preserve journaling on completion
- `cli/status.py`, `core/status.py`, `ports/vcs.py`, `adapters/vcs_git.py` — status overlay + worktree patch capture
- `core/findings.py`, `core/verdict.py` — MRS-DISP-023..026
- `tests/unit/test_dispatch_survival.py` — attach/resume, timing, preserve, reconcile fixtures
Verification: `pixi run -e pyforge-marshal pyforge-marshal-test` — **6219 passed**, 12 deselected.
Finalize: chore commit on main after merge (ledger key `22-6-the-dispatched-run-survives-its-operator-and-its-journal-carries-the-timing-signal` → done).
