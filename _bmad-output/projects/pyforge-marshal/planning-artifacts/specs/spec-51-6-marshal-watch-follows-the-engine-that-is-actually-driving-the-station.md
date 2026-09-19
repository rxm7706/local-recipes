---
title: '51.6: `marshal watch` follows the engine that is actually driving the station'
type: 'fix'
created: '2026-09-19'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
baseline_revision: 'd7f31dd88fdc2ebd05e54ce4e60ea897a839f3af'
---

<intent-contract>

## Intent

**Problem:** on 2026-09-18 the fleet watch read `dispatch-runs/` journals directly all day because `_gather_station` lets any `running`/`paused` `bmad-loop list` row win and consults `dispatch_run_id` only when no live row exists

**Approach:** the station's current run is the engine whose last journal fact is most recent

## Boundaries & Constraints

**Always:**
- a fixture with a `paused` loop row from 2026-08 and a dispatch run journaled today reports the dispatch run (harness, key, phase, last fact); with no dispatch run the loop row is chosen exactly as today; neither reports idle
- the choice function is mutation-tested (swapping the comparison re-selects the stale row)

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-254`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py::_gather_station` (the `_LIVE_STATUSES` row wins today; the choice becomes one pure function over the loop row's and the dispatch run's last journal timestamps), its `WatchPorts` / `_default_ports` (importing `iter_dispatch_run_dirs` / `gather_dispatch_journal_facts` from `cli/dispatch.py`, not re-implementing them), tests.
Ledger key: `51-6-marshal-watch-follows-the-engine-that-is-actually-driving-the-station`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-6-marshal-watch-follows-the-engine-that-is-actually-driving-the-station.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.6 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
