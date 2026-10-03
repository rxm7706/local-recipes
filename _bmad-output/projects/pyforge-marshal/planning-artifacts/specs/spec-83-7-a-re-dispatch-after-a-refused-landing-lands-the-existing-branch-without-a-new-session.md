---
title: '83.7: A re-dispatch after a refused landing lands the existing branch without a new session'
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: '1e75e5281378fbef48bc08e395d14d437c69311b'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A single-story `marshal factory dispatch` takes the land-only path (Story 29.2) only when
`core/dispatch_harness_done.py::blocks_harness_relaunch` sees the worktree spec read `done` with no follow-up review
recommended. A landing that the supervisor refused on a merge conflict (MRS-DISP-038) or on a red check (MRS-DISP-056)
leaves the spec where the session stopped. On 2026-10-02, after the operator fixed 82.5's branch by hand (its spec read
`in-progress` at the fixed head), the re-dispatch launched a full dev and review session on finished work; the operator
stopped it within seconds and merged the PR by hand. Only MRS-DISP-040 (a failed landing verification) reached the
land-only path.

**Approach:** the land-only decision also reads the latest run's journal: a run that journaled a `dispatch-land`
outcome with verdict `refused` finished its session, so the dispatch re-verifies, waits for the PR's checks, merges and
finalizes, and launches no session, whatever status the worktree spec reads. A run that never reached a landing attempt
is judged as today.

Ledger key: `83-7-a-re-dispatch-after-a-refused-landing-lands-the-existing-branch-without-a-new-session`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 29.2 (a harness-done story is land-only, CAP-4) and CAP-4 (Story 28.20). A defect of shipped behaviour, so no new
  CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a latest run that journaled a refused dispatch-land outcome and a worktree spec reading in-progress When a single-story dispatch runs Then it takes the land-only path and launches no session
- Given a latest run that journaled no landing attempt When a single-story dispatch runs Then it launches a session as today
- Given the land-only path meets a refusal it cannot clear When it runs Then it refuses again and leaves the PR open
- Given the journal rule removed When its new test runs Then it fails (mutation)
- Given a latest run that journaled a refused dispatch-land outcome and a worktree spec reading `ready-for-dev` or `draft` (the story was sent back after the refusal) When a single-story dispatch runs Then it launches a session and never takes the land-only path; the refused-landing rule applies only while the spec reads where a session stopped (`in-progress`, `in-review`)
- Given the send-back guard removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Decide from the run journal's own landing evidence, the same evidence the supervisor wrote.

**Never:** Do not change how a landing is verified or merged. Do not mark a spec `done` to force the path.

</intent-contract>

## Binding

Parent: Story 29.2 (a harness-done story is land-only, CAP-4) and CAP-4 (Story 28.20).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 (night) entry.
Ledger key: `83-7-a-re-dispatch-after-a-refused-landing-lands-the-existing-branch-without-a-new-session`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 at the operator's request to chain the defects found landing Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- 2026-10-03 — sent back by the operator session (landing review). Two acceptance criteria added: a sent-back spec (`ready-for-dev`, `draft`) always launches a session, with a mutation test. Status back to `ready-for-dev`.

## Review Triage Log

### 2026-10-03 — Landing (operator session)
- The second session (run `pyforge-marshal-20261003T095540348Z-29d5d440`) passed dispatch verification; the landing refused MRS-DISP-038 on `cli/dispatch.py`, `.claude/memory/MEMORY.md` and the Spec memlog after Stories 83.8 and 83.6 landed. Merged `origin/main` by hand: `dispatch_once` keeps 83.8's `backlog` -> `ready-for-dev` worktree rewrite first, then this story's refused-landing land-only decision; `MEMORY.md` keeps both index lines; the memlog is the union of both sides.
- Reviewed against the amended intent: `should_take_harness_done_land_only` applies the refused-landing rule only to `in-progress`/`in-review`, and `ready-for-dev`/`draft` always launch a session (pinned by `test_refused_landing_does_not_force_land_only_after_send_back_to_draft` and the `ready-for-dev` cases). Accepted.
- Green on the merge: `lint-types`, `pyforge-marshal-test` (10856 passed), `pyforge-deps-test`, `pyforge-core-test`, `deferred-work-check`, `spec_surface_reconcile.py`.

### 2026-10-03 — Landing review (operator session) — sent back
- Dispatch run `pyforge-marshal-20261003T033616311Z-73036a43` failed verification on the operator's launch environment (`python` not on PATH; not this story's code).
- `high` `patch` `should_take_harness_done_land_only` returns True whenever the latest run journaled a refused `dispatch-land`, whatever the worktree spec says. A story the operator sends back after a refused landing (status reset to `ready-for-dev` because review found a defect) would then take land-only: re-verify, and merge the known-bad branch if verification passes. On 2026-10-03 landing review found a defect verification cannot see (83.3's deferred-work union deleting 275 of 484 live entries); had that branch been refused at landing instead of at verification, this rule would have merged it. Apply the refused-landing rule only while the spec reads `in-progress` or `in-review`; `ready-for-dev` and `draft` always launch a session. Keep the shared rule in `core/dispatch_harness_done.py` so `cli/dispatch.py` and `cli/drain_plan.py` agree.

### 2026-10-03 — Review pass (send-back guard)
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (self-review against AC including send-back criteria; implementation matches intent)

### 2026-10-02 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (self-review against AC; no subagent layers — implementation matches intent)

## Auto Run Result

Status: done

**Summary:** Extended the single-story dispatch land-only gate (Story 29.2) so a latest run whose journal records a refused `dispatch-land` outcome takes CAP-4 re-verify/merge without launching `bmad-build-auto` while the worktree spec reads `in-progress` or `in-review`. After an operator send-back to `ready-for-dev` or `draft`, re-dispatch always launches a session.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py` — `_REFUSED_LANDING_LAND_ONLY_STATUSES`; `should_take_harness_done_land_only` send-back guard
- Unit tests in `test_dispatch_harness_done.py`, `test_dispatch.py`

**Review:** Self-review against AC after 2026-10-03 landing-review send-back criteria; 0 patch/defer/intent_gap items.

**Verification:** `pyforge-marshal-test` 10837 passed; `pyforge-deps-test` 130 passed; `lint-types` exit 0; `python scripts/spec_surface_reconcile.py` OK.

**Follow-up review recommended:** false
