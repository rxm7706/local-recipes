---
title: 'Finalize escalations self-clear past a later success'
type: 'fix'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `gather_fleet_finalize_escalations` (`cli/dispatch.py:531`) walks a station's dispatch run directories newest-to-oldest and reports the *first* run whose finalize attempt failed, `continue`-ing past any newer run that finalized cleanly rather than stopping at the newest run outright. Once a station has a failed-finalize run anywhere in its history, `marshal status`/`fleet-picture` report it as an active `awaiting-operator` escalation forever, even after later stories dispatch and land successfully and the named worktree has been deleted. Live incident (2026-09-10): pyforge-marshal's Story 33.2 dispatch failed to finalize; the operator recovered it manually (push + PR, outside the supervisor's own finalize/land path) and the worktree was later removed, but `marshal status --project pyforge-marshal` kept reporting `supervisor finalize failed: ... .worktrees/dispatch-pyforge-marshal-33.2` after Stories 33.8/33.9/33.10 all dispatched and landed cleanly on top.

**Approach:** Stop the walk at the newest dispatch run for the station and report an escalation only if *that* run's finalize attempt failed — do not search further back once a newer run has superseded it. Additionally, treat an escalation whose `worktree_path` no longer exists on disk as resolved rather than active, so a manually-recovered-and-cleaned-up worktree cannot resurface even within the newest-run's own history.

## Boundaries & Constraints

**Always:** Preserve the existing behavior when the newest dispatch run for a station *is* the one that failed to finalize (still reports `awaiting-operator` naming that worktree). Keep `FinalizeEscalation`'s existing shape (`story`, `worktree_path`) and its consumers in `cli/status.py` unchanged.

**Never:** Rewrite or delete historical journal files to "fix" old records — the journal is the audit trail. Add a new CLI verb whose sole purpose is manually clearing an escalation (a self-clearing read is the fix, not an acknowledge command). Change `finalize_attempt_failed`'s per-run detection logic — only the walk's stop condition and worktree-existence check.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| NEWEST_RUN_FAILED | Station's newest dispatch run for its story failed to finalize | Escalation reported, naming that run's worktree | Unchanged from today |
| SUPERSEDED_BY_SUCCESS | Newest dispatch run finalized cleanly; an older run (any story) failed to finalize | No escalation reported for the station | The older failure stays in the journal, just not surfaced |
| WORKTREE_ALREADY_GONE | Newest run failed to finalize, but its `worktree_path` no longer exists on disk | No escalation reported (treated as resolved) | Directory-existence check only; no journal mutation |
| NO_RUNS_YET | Station has no dispatch run directories | No escalation reported | Same as today (empty dict entry) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:531-559` — `gather_fleet_finalize_escalations`: change the walk to stop at the newest run per slug, and add a worktree-existence guard before recording an escalation
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch*.py` — add coverage for the superseded-by-success and worktree-gone cases (existing tests for the newest-run-failed case should already cover the unchanged path)

## Tasks & Acceptance

**Execution:**
- `cli/dispatch.py` — `gather_fleet_finalize_escalations`: examine only the newest `run_dir` per slug (drop the `continue`-past-non-failures backward search); skip recording when `Path(worktree).is_dir()` is false — fix
- test file (existing `test_dispatch*.py` covering this function, or a new sibling) — add `SUPERSEDED_BY_SUCCESS` and `WORKTREE_ALREADY_GONE` cases from the I/O matrix — test

**Acceptance Criteria:**
- Given a station whose newest dispatch run finalized cleanly but an older run for a different story failed to finalize, when `marshal status --project <slug>` runs, then no `awaiting_operator_remedy`/`finalize_escalation_worktree` is reported for that station
- Given a station whose newest dispatch run failed to finalize and its worktree still exists, when `marshal status` runs, then the escalation is still reported exactly as today
- Given a station whose newest dispatch run failed to finalize but its worktree has since been deleted, when `marshal status` runs, then no escalation is reported
- Given the live pyforge-marshal project post-fix, when `marshal status --project pyforge-marshal --format json` runs, then the stale 33.2 `awaiting-operator` row is gone

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test -- -k "finalize_escalation or gather_fleet_finalize"` — expected: all pass, including the two new matrix cases
- `pixi run -e pyforge-marshal marshal status --project pyforge-marshal --format json` — expected: no `33.2` reference anywhere in the output
