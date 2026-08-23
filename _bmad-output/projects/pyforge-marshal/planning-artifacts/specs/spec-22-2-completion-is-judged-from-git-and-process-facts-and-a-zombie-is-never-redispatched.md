---
title: Completion is judged from git and process facts, and a zombie is never redispatched
type: feature
created: '2026-08-23'
status: done
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

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/702
Merge: 91c4e5244a05959f7540822b5b2901e961c17ee5
Merge policy: admin merge (`gh pr merge 702 --merge --admin --repo rxm7706/local-recipes`) — GitHub Actions billing blocks CI; local tests green before merge.
Summary: Story 22.2 (FR-193 CAP-2) adds detached `dispatch_supervisor` spawned by `marshal factory dispatch` to judge completion from git facts (branch progress, merge refs per AD-33) plus process liveness — never harness notifications or foreground busy-wait. Zombie redispatch refused (`MRS-DISP-011`) when git shows live progress despite dead session. `FleetHomeFacts`/`marshal status` overlay extended with `dispatch_completion_verdict`.
Files:
- `core/dispatch_completion.py` — pure git+process completion judge
- `dispatch_supervisor/__main__.py` — detached supervisor loop (60s tick)
- `cli/dispatch.py` — spawn supervisor, baseline head journaling, zombie refusal
- `cli/status.py`, `core/status.py` — completion verdict overlay
- `core/findings.py`, `core/verdict.py` — MRS-DISP-011..013
- `tests/unit/test_dispatch_completion.py` — watchdog + zombie regression pins
Verification: `pixi run -e pyforge-marshal pyforge-marshal-test` — **6106 passed**, 12 deselected.
Out of scope (Stories 22.3–22.6): verification gate, landing, overlap guard, attach/resume.
