---
title: '25.1: The deck pipeline runs from the Guild env'
type: 'fix'
created: '2026-09-20'
status: 'done'
baseline_revision: '7f5584a2e49412b4fe9ee000d8f8b1760d024c4b'
final_revision: 'pending — the merge commit of the fleet/agents-md-mod PR (#1551)'
review_loop_iteration: 1
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

## Review Triage Log

### 2026-09-20 — hand-driven pass (operator: "why didn't we do this in #1551")
  - `[high]` `[patch]` `deck_pipeline.py` (`DeckExporter`, `_PixiPartialDeckExporter`, their failure messages and docstring) and `sync_all.py` (`FactsRefresher`, the trio step) shelled `-e local-recipes`; all name `-e pyforge-guild` now that the tasks live in `guild-tasks` with `pyforge-herald` in the Guild feature (steward 63.6, same PR — the cross-project gate resolved in one landing).
  - `[low]` `[patch]` `test_deck_pipeline.py` asserted the factory argv; updated.

## Auto Run Result

**Status:** done
**Summary:** herald's deck pipeline runs from the Guild env; the guard lists no herald offender.
**Verification:** `pyforge-herald-test` 1488 passed; `pixi run -e pyforge-guild deck-export|deck-facts|deck-trio -- --help` run.
**Files changed:** `deck_pipeline.py`, `sync_all.py`, `tests/unit/test_deck_pipeline.py`.
**Residual risks:** `deck-sync-proof`'s opt-in live run (Claude Design credentials) was not re-run here; its argv shape is unchanged apart from the env name.
**Follow-up review recommendation:** false
