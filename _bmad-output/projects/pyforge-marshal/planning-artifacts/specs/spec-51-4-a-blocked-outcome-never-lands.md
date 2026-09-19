---
title: '51.4: A blocked outcome never lands'
type: 'fix'
created: '2026-09-19'
status: 'in-progress'
baseline_revision: '1ff4b6d212084d74e3be6112221a4261822d74f0'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** doctor 27.3's session found an intent gap, reverted to baseline and set `blocked`; marshal landed the empty branch (PR #1476) and promoted `27-3 → done` — the truth was written above the Auto Run Result by hand and the story re-minted as 27.4→27.5

**Approach:** the supervisor's finalize sequence stops before verify and land on a `blocked` spec, journals `dispatch-blocked` with the spec's own reason, and the campaign records a station block rather than an advance

## Boundaries & Constraints

**Always:**
- the 27.3 fixture (empty diff against baseline + `status: blocked`) produces no PR and its tracked ledger row never reads `done`; the campaign fact names the reason
- an implementation with changed paths lands exactly as today (existing fixtures), and removing the status read re-lands the 27.3 fixture (mutation test)

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-252`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` (`_run_supervisor_finalize_sequence` and the run-loop land trigger read the worktree spec's `status:` before verify/land), `.../core/dispatch_completion.py::has_git_progress` (a revert-to-baseline plus a status flip is not progress), `.../core/dispatch_harness_done.py::parse_spec_status` (reused; the pre-launch guard treats `blocked` as not relaunchable without an operator decision), `.../core/dispatch_landing.py` (a `blocked` verdict), `.../cli/dispatch.py:: station_story_block_facts` + `.../core/dispatch_fleet.py` (the block reason; `NON_IMPLEMENT_STATUSES` already lists `blocked`), tests.
Ledger key: `51-4-a-blocked-outcome-never-lands`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-4-a-blocked-outcome-never-lands.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.4 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
