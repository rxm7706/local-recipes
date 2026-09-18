---
title: '50.1: A landing never re-dispatches the story it just landed'
type: 'fix'
created: '2026-09-18'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the campaign cycles every 60 s and, on 2026-09-18, four times in a row saw a story neither live nor `done` inside the ~45 s between session exit and ledger promotion (`fleet-drain-runs/…151925342Z-82ce96c8`: `in-flight` 16:19:45Z → `dispatched` 16:20:47Z → `blocked … ended 'failed'` 16:21:47Z, `complete=true`)

**Approach:** a station whose most recent run's supervisor is alive but has not journaled `dispatch-completion` (or has journaled `dispatch-land` but the tracked ledger has not yet moved) reads as in flight, and a most-recent run that is a self-refusal of the already-merged kind (zero changed paths, session log names the merged PR / `done` spec) classifies as an advance reason

## Boundaries & Constraints

**Always:**
- the campaign reports `in-flight` for that cycle and chains the next ready story on the following one, and a fixture journal replaying the herald sequence completes the campaign with the next story `dispatched` rather than the same story `blocked`
- a genuine failed dispatch with zero changed paths and no merged evidence still blocks exactly as today (mutation test: removing the advance classification re-blocks the fixture)

**Never:**
- Do not make the supervisor trust a session's self-report, add a second gate, or re-attribute landed history — the Epic 50 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 2026-09-18 fixture | the real run/journal named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-244`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` (the fleet cycle: `_live_dispatch_story_keys` / `_station_block_evidence` / `_classify_attempt`), `.../core/dispatch_fleet.py` (`plan_station_queue`, `classify_fleet_block`, the harness-done advance reason), `.../dispatch_supervisor/__main__.py` (only if a "session exited, finalize pending" journal fact is needed), tests.
Ledger key: `50-1-a-landing-never-re-dispatches-the-story-it-just-landed`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-50-1-a-landing-never-re-dispatches-the-story-it-just-landed.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- A fixture journal replaying herald's 2026-09-18 sequence (`fleet-drain-runs/…151925342Z-82ce96c8`) completes with the NEXT story `dispatched`, never the same story `blocked`; a genuine failed dispatch with no merged evidence still blocks (mutation test).
