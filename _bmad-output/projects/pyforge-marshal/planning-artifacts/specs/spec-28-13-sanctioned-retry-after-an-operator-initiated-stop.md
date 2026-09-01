---
title: 'Sanctioned retry after an operator-initiated stop (Story 28.13, Epic 28)'
type: 'feature'
created: '2026-08-31'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** A dispatch ended by an external stop (SIGTERM outside marshal's own idle/budget
ladder) is journaled as `failed` the same way a genuine verdict/review/crash failure is —
`MRS-DRAIN-005` then refuses retry through `drain`/`dispatch --stories`, forcing an
undocumented bare-`dispatch <slug> <story>` workaround. Retries also risk silently stepping
on uncommitted worktree changes left behind by the kill.

**Approach:** Distinguish externally-stopped dispatches in the journal from genuine
failures. Make externally-stopped stories retryable through the normal `drain`/`dispatch
--stories` path. Before a retry touches a worktree carrying uncommitted changes, surface
the diff (file count, line count). Ensure `MRS-DISP-011` liveness detection does not treat
leftover uncommitted worktree changes alone as proof a session process is still alive —
while keeping refusal when a session process is genuinely still live unchanged.

## Acceptance Criteria

- Given a dispatch session stopped by SIGTERM from outside marshal's own idle/budget
  ladder, when the journal records the outcome, then it is not recorded as `failed` the way
  a genuine verdict/review/crash failure is.
- Given an externally-stopped story, when retrying through `drain`/`dispatch --stories`,
  then dispatch proceeds without requiring the bare-`dispatch <slug> <story>` workaround and
  without `MRS-DRAIN-005` refusal.
- Given a retry against a worktree already carrying uncommitted changes, when marshal
  evaluates whether to proceed, then the diff (file count, line count) is reported before
  touching the worktree — never silently ignored or discarded.
- Given a worktree with uncommitted changes but no live session process, when
  `MRS-DISP-011` evaluates liveness, then leftover diff alone does not block or misread as
  live — proven by a test diffing dead-process + dirty-worktree from live-process cases.
- Given a session process genuinely still alive, when `MRS-DISP-011` evaluates, then
  refusal behavior is unchanged from today.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-13-sanctioned-retry-after-an-operator-initiated-stop`.

**Block If:** A change would auto-discard uncommitted work without operator acknowledgement,
or weaken `MRS-DISP-011` when a live process is actually running.

**Never:** Treat every SIGTERM as retryable (marshal's own idle/budget ladder stops keep
today's semantics). Silent worktree reset on retry.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` (journal outcome taxonomy; retry eligibility)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` (`MRS-DRAIN-005` / `--stories` retry path)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py` (external-stop vs genuine-failure classification)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` (`MRS-DISP-011` liveness — worktree diff vs process)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(external-stop journal class, sanctioned `--stories` retry, diff surfacing, liveness split).
Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.13 and spec-marshal-token-economy CAP-15. Deps: —. Motivating
incident: atlas 21.7 SIGTERM kill journaled as failed; marshal 28.2 worktree held 647
uncommitted lines — see `docs/dreams/marshal-dependency-aware-dispatch.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-31: drafted from marshal-dependency-aware-dispatch fold-in (CAP-15; bmad-correct-course sprint-change-proposal-2026-08-31)

## Operational note (2026-09-01 — interim hotfix, NOT this story shipped)

Epic 28 dispatch campaign hotfixes added **`classify_dispatch_block`** /
`DispatchBlockKind.TRANSIENT` in `core/dispatch_retry.py` so quota/auth harness
failures and retriable verify gates do not permanently trigger `MRS-DRAIN-005`.
That is **not** CAP-15: it does not distinguish SIGTERM-from-outside in the
journal, surface WIP diffs before retry, or split `MRS-DISP-011` liveness the way
this spec's ACs require. Treat the hotfix as drain-unblocking interim; this story
remains `ready-for-dev` until the journal taxonomy lands. SCP:
`change-history/sprint-change-proposal-2026-09-01-dispatch-autonomy-hotfixes.md`.
