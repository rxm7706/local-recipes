---
title: 'Push the dispatch branch before verify can strand it (Story 28.21, Epic 28)'
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
