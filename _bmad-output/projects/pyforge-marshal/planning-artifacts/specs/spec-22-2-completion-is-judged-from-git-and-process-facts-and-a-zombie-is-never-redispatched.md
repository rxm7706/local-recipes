---
title: Completion is judged from git and process facts, and a zombie is never redispatched
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 66b551be10
---

<intent-contract>

## Intent

**Problem:** Dispatched sessions (22.1) have no completion judge — harness notifications and self-reports are unreliable; busy-wait foreground paths risk watchdog kills; "dead" agents can land stories after failure notifications (FR-193 CAP-2).

**Approach:** Add detached supervisor (Story 3.4 shape) that judges dispatched session completion/failure from git facts (AD-33: story-branch commits, merge refs) plus running-process facts — never harness notifications, self-reports, or busy-wait polling. Regression-pin both traps: (a) no foreground busy-wait on long-running await; (b) killed/failed notification with live git progress → treat as live, refuse redispatch naming evidence. Surface in `core/status.py`. Deps: 22.1 done. Do not implement verification (22.3), landing (22.4), overlap guard (22.5), or attach/resume (22.6).

## Acceptance Criteria

- Completion/failure judged from git facts + process facts only (not harness notifications or self-reports).
- No foreground path busy-waits awaiting a dispatched session (detached supervisor owns await).
- Session with killed/failed notification but live git progress is treated as live; redispatch of same story refused with evidence.
- Both traps covered by regression tests (watchdog-kill trap + zombie-redispatch trap).
- Does not implement CAP-3..CAP-6 (Stories 22.3–22.6).

## Boundaries & Constraints

**Never:** Busy-wait in dispatch caller. Never trust harness self-report as completion verdict. Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-marshal-single-story-dispatch/SPEC.md` (CAP-2)
- `src/shared/packages/pyforge-marshal/` — detached supervisor, `core/status.py` dispatch completion overlay
- Tests: git-fact completion, process-fact liveness, no-busy-wait, zombie-redispatch refusal fixtures

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
- Regression tests pin both motivating traps from epics.md
