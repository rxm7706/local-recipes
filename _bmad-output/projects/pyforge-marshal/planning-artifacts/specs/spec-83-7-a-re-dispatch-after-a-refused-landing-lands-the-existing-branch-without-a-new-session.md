---
title: '83.7: A re-dispatch after a refused landing lands the existing branch without a new session'
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: 'abbb7ba05f5ce65e54b320b4d30e2c9e7d916c90'
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

## Review Triage Log

### 2026-10-02 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (self-review against AC; no subagent layers — implementation matches intent)

## Auto Run Result

Status: done

**Summary:** Extended the single-story dispatch land-only gate (Story 29.2) so a latest run whose journal records a refused `dispatch-land` outcome takes CAP-4 re-verify/merge without launching `bmad-build-auto`, even when the worktree spec still reads `in-progress`.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py` — `should_take_harness_done_land_only`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — read refused landing verdict from journal; gate dispatch_once
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/drain_plan.py` — same land-only predicate for `--plan`
- Unit tests in `test_dispatch_harness_done.py`, `test_dispatch.py`, `test_dispatch_survival.py`

**Review:** No patch/defer/intent_gap items.

**Verification:** `pyforge-marshal-test` 10832 passed; `pyforge-deps-test` 130 passed; `lint-types` exit 0; `python scripts/spec_surface_reconcile.py` OK (pixi pyforge-guild).

**Follow-up review recommended:** false
