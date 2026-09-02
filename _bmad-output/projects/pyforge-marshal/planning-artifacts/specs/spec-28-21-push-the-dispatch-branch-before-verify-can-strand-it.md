---
title: 'Push the dispatch branch before verify can strand it (Story 28.21, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'done'
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

**Problem:** 28.13 finished in `.worktrees/dispatch-pyforge-marshal-28.13`.
`origin/dispatch/pyforge-marshal/28.13` never existed. Verify refuse skipped
land. Recovery was cherry-pick.

**Approach:** Push `origin/dispatch/<slug>/<story>` once the session has a
commitable result — before independent verify. A later refuse must still leave
a reachable ref.

## Acceptance Criteria

- Given a dispatch worktree with a story commit, when verify later refuses,
  then `git ls-remote` shows `dispatch/<slug>/<story>`.
- Given no commitable result, when the session ends, then no empty branch is
  pushed.

## Boundaries & Constraints

**Never:** Force-push `main`. Skip verify. `scripts/bmad-switch`.

Ledger key: `28-21-push-the-dispatch-branch-before-verify-can-strand-it`.

</intent-contract>

## Code Map

- `dispatch_supervisor/__main__.py` / `cli/dispatch.py` — push after first
  story commit / before verify
- Tests: vcs-port fake remote

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`

## Review Triage Log

### 2026-09-01 — Review pass (bmad-build-auto)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

## Auto Run Result

Status: done

**Summary:** The dispatch completion supervisor now pushes `origin/dispatch/<slug>/<story>` after the pre-verify WIP commit and before independent verify runs, so a later verify refuse still leaves work on a reachable remote ref. Push is skipped when there is no git progress (no empty branch). Failures journal as `MRS-DISP-037` (WARN) and do not block verify.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_push.py` — pure eligibility (`may_push_dispatch_branch_before_verify`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` — `KIND_DISPATCH_PUSH` journal kind
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` — `_run_and_journal_dispatch_push` wired before verify
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`, `core/verdict.py`, `tests/unit/test_findings.py` — `MRS-DISP-037` registration
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_push.py` — unit coverage with fake VCS

**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 7395 passed, 0 failed (12 slow deselected, 62s).

**Follow-up review recommended:** false (0 patch findings).

**Residual risks:** Push failure is WARN-only; work remains local until a later successful push or land. Story 28.23 will surface unpushed refs in ATTENTION.
