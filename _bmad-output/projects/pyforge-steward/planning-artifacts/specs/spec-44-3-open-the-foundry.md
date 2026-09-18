---
title: '44.3: Open the foundry'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `rxm7706/python-foundry` created as a fresh, recipe-free, lean-pixi estate with estate-only CI

**Approach:** Phase 1 has a lasting root to move into.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-44-3-open-the-foundry.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| a fresh clone **When** CI runs on the empty estate **Then** it is green, no `recipes/` directory exists, `pixi.toml` is `name = "pyforge"` with no solver-farm… | CI runs on the empty estate **Then** it is green, no `recipes/` directory exists, `pixi.toml` is `name = "pyforge"` wit… | it is green, no `recipes/` directory exists, `pixi.toml` is `name = "pyforge"` with no solver-farm tooling, and `environment.yaml` is either workflow-produced or absent | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the repo envelope is set per `fnd:AD-14`: visibility private (permanently), `main` protected with merge commits only, secrets and vars re-provisioned through `steward keys` from manifest rows of kind… | n/a |
| And-clause from epics.md | when the story lands | CI evidence follows `fnd:AD-23` as amended 2026-09-13 (D1): authoritative proof on this empty estate is a fresh-clone `pixi run estate-smoke` (no Helm chart yet, so no CRC). GHA (`estate.yml`) is a t… | n/a |

</intent-contract>

## Binding

Parent Spec capability: `fnd:CAP-1`.
Surface: named on the story in epics.md
Ledger key: `44-3-open-the-foundry`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-44-3-open-the-foundry.md`.

## Epic excerpt

As a platform operator,
I want `rxm7706/python-foundry` created as a fresh, recipe-free, lean-pixi estate with estate-only CI,
So that Phase 1 has a lasting root to move into.

**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** fnd:CAP-1 • fnd:AD-1, fnd:AD-3, fnd:AD-8, fnd:AD-9, fnd:AD-14, fnd:AD-16, fnd:AD-23 • R-17a
**Outward (`fnd:AD-9`):** creates a GitHub repository — **flipped 2026-09-13** by the operator (create the second git root; protect `main`; trunk-based from commit one). Never auto-drained.
**Given** a fresh clone **When** CI runs on the empty estate **Then** it is green, no `recipes/` directory exists, `pixi.toml` is `name = "pyforge"` with no solver-farm tooling, and `environment.yaml` is either workflow-produced or absent
**And** the repo envelope is set per `fnd:AD-14`: visibility private (permanently), `main` protected with merge commits only, secrets and vars re-provisioned through `steward keys` from manifest rows of kind `secret`, the foundry epoch SHA recorded, and `src/platform/config/flags.json` carries `pyforge.cutover_root: local-recipes` (`fnd:AD-17`)
**And** CI evidence follows `fnd:AD-23` as amended 2026-09-13 (D1): authoritative proof on this empty estate is a fresh-clone `pixi run estate-smoke` (no Helm chart yet, so no CRC). GHA (`estate.yml`) is a twin and may stay red. `steward budget check` (44.15) is not a confirmation gate
**Status:** done

