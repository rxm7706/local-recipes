---
title: 'CAP-4 land heals mechanical and DIRTY PRs (Story 28.20, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'ready'
updated: '2026-09-01'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
baseline_revision: 20e88e8b0fd1ccd2cc38101691ac72aeb8df71cc
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-drain-self-resolution/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** PR #985 died on a ledger-only conflict, then `gh pr merge` stayed
`DIRTY` while `merge-tree` was clean. CAP-4 waited for a chat.

**Approach:** Union `sprint-status-ledger.yaml` keys (`done` beats `backlog`);
optionally spec `status:` ready→done. If git is clean and GitHub `mergeable` is
false, advance `main`, retire the PR, resync ledger. Unknown conflicts escalate
with paths named.

## Acceptance Criteria

- Given a PR whose only conflict is the sprint ledger, when land runs, then
  both sides' `done` keys survive, the branch is pushed, merge is retried.
- Given clean `merge-tree` and GitHub `DIRTY`, when land runs, then `main`
  contains the story commits and the PR is not left OPEN+DIRTY.
- Given a conflict in an unknown path, when land runs, then it escalates
  naming that path and does not merge.

## Boundaries & Constraints

**Never:** Merge unknown conflicts. Skip story-caused red CI. `scripts/bmad-switch`.

Ledger key: `28-20-cap-4-land-heals-mechanical-and-dirty-prs`.

</intent-contract>

## Code Map

- `core/dispatch_landing.py` / land CLI composition
- Tests: merge-tree / ledger-union fixtures (no live GitHub required)

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
