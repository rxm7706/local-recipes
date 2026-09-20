---
title: '63.6: No station code assumes the local-recipes environment at runtime'
type: 'feature'
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

**Problem:** only `pyforge-guild` exists at runtime (operator ruling 2026-09-20), yet station code shells to `pixi run -e local-recipes …` and reads `.pixi/envs/local-recipes/…`: marshal `cli/watch.py` (bmad-loop list/status), `core/gate.py` (`platform-ci-local`), `adapters/scribe_cli.py` (fallback bin); herald `deck_pipeline.py`, `sync_all.py` (`deck-export`, `deck-facts`, `deck-trio`); steward `provision.py` (bmad-builder skills share dir), `upgrade.py` (bin on PATH), `suite.py` (probe fallback). Each works only on a machine that happens to carry the 10 GB recipe-factory env.

**Approach:** every shelled task is reachable from `pyforge-guild` — registered in `guild-tasks` with its deps in `[feature.pyforge-guild.dependencies]`, each dep named with the task that needs it — steward's own lookups read the Guild env's `share/` and `bin/`, and a steward meta-test scans every station's `src/` for `-e local-recipes` / `.pixi/envs/local-recipes` and lists offenders. Marshal 46.12 and herald 25.1 fix their own shell-outs; until they land the guard names exactly those files.

## Boundaries & Constraints

**Always:**
- `pyforge-guild` stays the bare minimum: the size delta is reported and every added dep is justified by a named task
- The guard is a test in steward's suite (the Guild env is steward's), never a second detector
- Steward's provisioner reads share dirs from the Guild env; test fixtures stage `.pixi/envs/pyforge-guild/share/…`

**Never:**
- Do not move a task by copying its pins — reference the existing feature deps
- Do not fix marshal's or herald's code here (one-chain-per-station; the guard's allowlist names them until their stories land)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| every shelled task | `pixi run -e pyforge-guild deck-export\|deck-facts\|deck-trio\|platform-ci-local\|wasm-build\|bmad-loop list` | runs (or reports its own precondition), never "task not found" | n/a |
| guard, before 46.12 / 25.1 | station src scan | offenders = the marshal and herald files, listed by path:line | fail |
| guard, after | station src scan | zero offenders | pass |
| steward provisioner | Guild env share dir present | skills provisioned from `.pixi/envs/pyforge-guild/share/…` | refuses naming the path when absent |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward CAP-152`.
Surface: `pixi.toml` (`guild-tasks`, `[feature.pyforge-guild.dependencies]`), `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py`, `upgrade.py`, `suite.py`, `src/shared/packages/pyforge-steward/tests/meta/test_no_station_assumes_local_recipes.py` (new), the steward provision/upgrade test fixtures.
Ledger key: `63-6-no-station-code-assumes-the-local-recipes-environment-at-runtime`.
Minted 2026-09-20 from `epics.md` so `marshal factory dispatch` can resolve this file.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `pixi run -e pyforge-guild <task>` for each shelled task; `du -sh .pixi/envs/pyforge-guild` before and after, reported in the Auto Run Result.
