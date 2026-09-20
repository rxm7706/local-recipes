---
title: '51.11: A session that halts blocked with its verdict uncommitted is a blocked outcome, not an operator stop'
type: 'fix'
created: '2026-09-20'
updated: '2026-09-20'
status: 'done'
baseline_revision: 'c8277c03c117ff4779d54a2ff9d900f519415971'
review_loop_iteration: 0
followup_review_recommended: true
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** doctor Story 26.1's session (run `pyforge-doctor-20260919T233255320Z-8f2b958e`) halted on an intent gap exactly as the workflow prescribes — code reverted, the tracked spec flipped to `status: blocked` with its Review Triage Log and Auto Run Result, the attempt saved to the worktree's Tier-3 as a patch — but left the spec and the revert *uncommitted* and exited. The supervisor saw `session_alive: False` against a HEAD (`678d409fc3`) that still carried two wip commits with real code, wrote `dispatch-finalize ok:false` and `dispatch-completion stop_reason: external-operator-stop`, and never a `dispatch-blocked` row. CAP-252's blocked detection reads committed state only; marshal 51.7's halt was caught only because that session committed the blocked spec first. `fleet-picture` then shows 26.1 `backlog` with no trace of the block, and the triage log lives only in a worktree awaiting teardown.

**Approach:** before classifying an unexplained session exit as `external-operator-stop`, the supervisor reads the worktree's *working-tree* copy of the tracked story spec (`core/dispatch_harness_done.py::parse_spec_status`); on `blocked` with an Auto Run Result it commits the spec and any `*-attempted-change*.patch` under the worktree's Tier-3 onto the dispatch branch, journals `dispatch-blocked` with the spec's blocking condition, preserves the worktree and completes with verdict `blocked`; the primary's tracked twin is promoted to `blocked` so the fleet picture shows it.

## Boundaries & Constraints

**Always:**
- The classifier narrows, never widens: a session that dies with a clean working tree and no terminal spec status still reads `stopped_externally`
- Marshal 51.7's committed-halt path (`dispatch-blocked` from committed state) is byte-identical after this story
- The supervisor never trusts a self-report — it reads the spec file, `git status` and the process; nothing the session prints is evidence
- The record survives worktree teardown: the blocked spec and the patch are on the dispatch branch and the twin is on the primary

**Never:**
- Do not land, merge or promote `done` anything from a blocked exit; do not add a second gate or verdict owner
- Do not delete or reset the worktree — `dispatch-preserve` semantics hold
- Do not re-attribute an operator-killed session as blocked because a stale `blocked` spec happens to sit in the tree from an earlier pass: the Auto Run Result's `baseline_revision` must equal the run's own baseline

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the doctor 26.1 replay | two wip commits with code; working tree = reverted code + spec `status: blocked` (Auto Run Result, `baseline_revision` = run baseline); session gone | `dispatch-blocked` (reason: intent gap), completion verdict `blocked`, a branch commit with the spec + patch, primary twin `blocked` | n/a |
| operator kill | clean working tree, spec `in-progress`, session gone | `stopped_externally` / `external-operator-stop` as today | n/a |
| committed halt (51.7's shape) | HEAD carries the blocked spec, tree clean | unchanged: `dispatch-blocked` as today | n/a |
| stale blocked spec from an earlier pass | spec `blocked` but `baseline_revision` ≠ this run's baseline | `stopped_externally`; journal names the mismatch | advisory note, no block |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-258`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` (the exit classifier), `core/dispatch_completion.py`, `core/dispatch_landing.py` (twin promotion of a `blocked` tracked spec), `core/dispatch_harness_done.py::parse_spec_status` (reused, not re-implemented), tests with the replay fixture.
Ledger key: `51-11-a-session-that-halts-blocked-with-its-verdict-uncommitted-is-a-blocked-outcome-not-an-operator-stop`.
Minted 2026-09-20 from `epics.md` so `marshal factory dispatch` can resolve this file; dispatch after Story 51.7 lands (shared hub file).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.11 in `epics.md` hold on the replay fixture; the fixture's final state is the one recorded in the doctor run's journal, not inferred.
