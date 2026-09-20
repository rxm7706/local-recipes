---
title: "Harness done is CAP-4 only — never another session"
type: "fix"
created: "2026-09-02"
status: "done"
updated: "2026-09-02"
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
context:
  - "_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md"
  - "docs/dreams/marshal-single-story-dispatch.md"
  - "src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py"
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** After the harness exits `done`, drain still sees `backlog` on
`main` and launches another `bmad-build-auto`. 41.2 was DIRTY; 13.2 had no
PR. Both loops were marshal re-dispatch, not GitHub reviewers.

**Approach:** Treat harness `done` as session-terminal. Next step is CAP-4
only. Land fail parks the story. Do not start another harness until the
operator unparks.

## Acceptance Criteria

- Given a dispatch whose harness halted `done`, when the fleet supervisor
  ticks, then it does not launch another `bmad-build-auto` for that story.
- Given the same, when CAP-4 can land, then it opens/merges the PR and
  promotes the ledger — no second session.
- Given CAP-4 fail (GitHub DIRTY / conflicts, or no PR on the dispatch
  branch), when the supervisor ticks, then the station is
  `awaiting-operator` / CHAIN naming the PR or worktree, and the harness is
  not re-invoked.
- Given a 41.2-shaped DIRTY PR or a 13.2-shaped branch with commits and no
  PR, when drain runs, then additional harness launch count is 0.

## Boundaries & Constraints

**Never:** A second landing path. `scripts/bmad-switch`. Re-dispatch because
`sprint-status-ledger.yaml` on `main` is still `backlog`. Replace 28.20
mechanical-conflict heal — compose with it; unknown conflicts still escalate.

**Deps:** S-29.1 (harness must also refuse; marshal must not rely on the skill
alone).

Ledger key: `29-2-harness-done-is-cap-4-only-never-another-session`.

</intent-contract>

## Tasks

- [x] Fleet/supervisor: harness exit `done` → CAP-4 only, never relaunch.
- [x] Land fail → `awaiting-operator` / CHAIN with PR or worktree named.
- [x] Regression: 41.2 DIRTY + 13.2 no-PR fixtures → 0 harness relaunches.
- [x] Ledger `29-2-harness-done-is-cap-4-only-never-another-session` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`pixi run -e pyforge-marshal pyforge-marshal-test` scoped to dispatch fleet /
supervisor tests added by this story.

## Source

Dream addendum 2026-09-02. CAP-11 marshal half. Change proposal:
`sprint-change-proposal-2026-09-02-done-spec-review-loop.md`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `c6eff1e9ac` (2026-09-02, "marshal: mark Story 29.2 done after CAP-4-only dispatch landed."); also `a516d07f50` (2026-09-02, "marshal: treat harness-done as CAP-4 only, never another session (29.2)."). Ledger row `29-2-harness-done-is-cap-4-only-never-another-session: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-29-2-harness-done-is-cap-4-only-never-another-session.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
