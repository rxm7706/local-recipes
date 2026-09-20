---
title: '25.1: The deck pipeline runs from the Guild env'
type: 'fix'
created: '2026-09-20'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `deck_pipeline.py`'s `DeckExporter` and `sync_all.py`'s `FactsRefresher` / trio step shell `pixi run -e local-recipes deck-export | deck-facts | deck-trio` — tasks that are herald's own — while only `pyforge-guild` exists at runtime.

**Approach:** the three argvs name `-e pyforge-guild` (steward 63.6 registers the tasks in `guild-tasks` with their deps); the pipeline's fakes and the live sync proof keep their shapes.

## Boundaries & Constraints

**Always:**
- No `-e local-recipes` string remains in `pyforge-herald/src`
- `deck-sync-proof`'s opt-in live run still passes

**Never:**
- Do not register the tasks here — steward 63.6 owns `guild-tasks`; this story is gated on it (ledger `backlog` until then, per AGENTS.md's cross-project rule)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| deck export | `DeckExporter.export(slug)` | `["pixi","run","-e","pyforge-guild","deck-export",slug]` | unchanged failure text names the Guild env |
| facts refresh + trio | `sync-all` | `deck-facts` / `deck-trio` under `-e pyforge-guild` | unchanged |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-51`.
Surface: `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py`, `src/shared/packages/pyforge-herald/src/pyforge/herald/sync_all.py`, `src/shared/packages/pyforge-herald/tests/unit/test_deck_pipeline.py`, the sync-all tests.
Ledger key: `25-1-the-deck-pipeline-runs-from-the-guild-env`.
Minted 2026-09-20 from `epics.md`; dispatch after steward 63.6 lands.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `grep -rn 'local-recipes' src/shared/packages/pyforge-herald/src` finds no argv.
