---
title: Declare eight stations five-tier complete
type: chore
created: '2026-08-26'
status: done
updated: '2026-08-26'
baseline_commit: 9446d14bc2
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Ledgers show every station story done, but canopy:FR-39 still treated the roster as undeclared. Mason's skill cell stayed empty because the detector required `pyforge-mason/`, which Epic 11 forbids.

**Approach:** Count `conda-forge-expert` as mason's skill. Set `DECLARED_COMPLETE` to the eight-station roster so a missing cell fails CI.

## Acceptance Criteria

- Given the live repo, when `five_tier.check` runs, then all eight stations have CLI, portal, service, skill, and persona.
- Given mason, when the detector runs, then skill is true iff `.claude/skills/conda-forge-expert/SKILL.md` exists.
- Given a declared 03 station missing a cell, when the check runs, then it fails.

## Boundaries & Constraints

**Always:** Ledger `37-1-declare-eight-stations-five-tier-complete`. Host never imports `pyforge.*`.

**Never:** A second SKF recipe skill that replaces `conda-forge-expert`. MCP slice 3. Mosaic required. vizro-ai. 28-page inventory.

</intent-contract>

## Tasks

- [x] Mason skill cell → CFE. `DECLARED_COMPLETE = STATIONS`.
- [x] Live matrix test requires zero holes.
- [x] Ledger via `sprint-ledger-sync`.

## Verification

`pixi run -e pyforge-steward -- pytest src/shared/packages/pyforge-steward/tests/meta/test_five_tier_check.py -q`

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `d7853d7983` (2026-08-26, "Merge pull request #874 from rxm7706/steward/37-1-five-tier-roster-drain"). Ledger row `37-1-declare-eight-stations-five-tier-complete: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-37-1-declare-eight-stations-five-tier-complete.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/shared/packages/pyforge-steward/src/pyforge/steward/five_tier.py`, `src/shared/packages/pyforge-steward/tests/meta/test_five_tier_check.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
