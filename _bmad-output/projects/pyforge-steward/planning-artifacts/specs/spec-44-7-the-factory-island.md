---
title: 'The factory island'
type: 'feature'
created: '2026-09-13'
status: 'done'
difficulty: heavy
story: 44.7
spec: python-foundry-cutover
surface: ["src/shared/packages/pyforge-mason/**", "_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md", ".github/workflows/**"]
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Recipe tooling still lives only on `local-recipes`. Foundry
must grow a `factory/` island so recipe churn never re-solves the estate.

**Approach:** Create the island **in `rxm7706/python-foundry`**:
`factory/pixi.toml` + lock, `factory/recipes/` (empty or a single smoke
recipe — **not** the 7,855-dir universe; that is 44.8), `build-locally.py`,
`.ci_support/`, `conda-forge.yml`, and CI on `paths: factory/**` only.
Estate `pixi.toml` on foundry stays free of rattler-build / conda-smithy /
conda-forge-pinning. `mason recipe build factory/recipes/<r>` matches
today's CFE wrap. Resolve `DW-RT-2026-09-02-1` (R-17b). Consult
`spec-reusable-cicd-workflows` for the second-consuming-repo trigger
instead of inventing a new CI shape.

## Boundaries & Constraints

**Always:**
- Lasting files land on `python-foundry` (private, trunk, merge-only).
- Island CI paths filter is `factory/**` only.
- Close `DW-RT-2026-09-02-1` when the island lock exists.

**Never:**
- Never copy the recipe universe (44.8).
- Never open a conda-forge / staged-recipes / feedstock PR (44.9 stays blocked).
- Never add solver-farm deps to the foundry estate lock.
- Never flip `pyforge.cutover_root`.
- Never mark 44.8 `done`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| foundry estate solve | `pixi.toml` at repo root | no rattler-build / conda-smithy / pinning | fail if they appear |
| island solve | `factory/pixi.toml` | recipe tooling present | named fail |
| mason recipe build | `factory/recipes/<r>` | same wrap as today's CFE | missing island is named fail |
| island CI | change under `factory/` | workflow runs | estate-only paths do not trigger it |

</intent-contract>

## Code Map

- Foundry clone: `/home/rxm7706/UserLocal/Projects/Github/rxm7706/python-foundry`.
- Mason wrap in local-recipes until 44.4/44.6 move paths.
- `spec-reusable-cicd-workflows` for the workflow shape.

## Acceptance Criteria

1. `factory/pixi.toml` + lock exist on foundry; estate lock has no solver-farm dep.
2. Island CI triggers on `factory/**` only.
3. `mason recipe build factory/recipes/<r>` matches today's CFE wrap (or a documented equivalent on the empty island).
4. `DW-RT-2026-09-02-1` marked resolved.
5. Ledger key `44-7-the-factory-island` is the only 44.x key this Story may mark `done`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `3f6504a964` (2026-09-13, "Merge pull request #1338 from rxm7706/steward-44-7-factory-island"). Ledger row `44-7-the-factory-island: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/scripts/conda-forge-expert/native-build.sh`, `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py`, `src/shared/packages/pyforge-mason/src/pyforge/mason/errors.py`, `src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py`, `src/shared/packages/pyforge-mason/src/pyforge/mason/resolve.py`, `src/shared/packages/pyforge-mason/tests/unit/test_factory_island.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `backlog` → `done` (ledger row `44-7-the-factory-island: done`).
- `## Auto Run Result` reconstructed from git (none survived).
