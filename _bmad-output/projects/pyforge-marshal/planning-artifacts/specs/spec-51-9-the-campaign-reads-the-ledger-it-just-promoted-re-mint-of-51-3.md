---
title: '51.9: The campaign reads the ledger it just promoted (re-mint of 51.3)'
type: 'fix'
created: '2026-09-19'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every herald 23.x landing on 2026-09-18 promoted the ledger onto `origin/main` and the campaign kept reading the primary checkout's stale copy until an operator pulled

**Approach:** finalize fast-forwards the primary only when it is a clean `main` (refusing by name and journaling otherwise — the checkout may belong to another session) and the campaign otherwise reads the promoted ledger from `origin/main`

## Boundaries & Constraints

**Always:**
- a fixture replaying the herald sequence (ledger promoted remotely, primary one commit behind) reports the story `done` on the next cycle and chains the next ready story with zero operator commands
- a dirty or non-`main` primary is never moved (fixture), `_promote_sprint_ledger` gains no second writer, and a primary already at `origin/main` is byte-identical

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-251`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` (post-ledger refresh step, reusing `cli/land.py::_resync_home_branch`), `.../cli/land.py::_promote_sprint_ledger` (unchanged single writer onto the remote tip), `.../cli/dispatch.py` (the fleet cycle's ledger read — `station_finalize_pending_story` / the `ledger_story_statuses(ledger_path)` call — falls back to `origin/main` when the primary is not a clean `main`), `.../core/dispatch_fleet.py::station_ledger_path`, tests.
Ledger key: `51-9-the-campaign-reads-the-ledger-it-just-promoted-re-mint-of-51-3`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-9-the-campaign-reads-the-ledger-it-just-promoted-re-mint-of-51-3.md`. Re-mint of Story 51.3 (2026-09-19), which landed hollow — see its tracked spec; identical contract, `Deps: S-51.2`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.9 (= 51.3) in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.

