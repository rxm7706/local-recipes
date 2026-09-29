---
title: '63.1: The `pyforge-guild` feature and environment exist and the Guild tasks live in it'
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

**Problem:** every planning task is reachable only through a 10 GB environment

**Approach:** `pixi install -e pyforge-guild` from cold is under 1 GB on disk and `pixi run -e pyforge-guild detectors-ci` is green on `main`

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-63-1-the-pyforge-guild-feature-and-environment-exist-and-the-guild-tasks-live-in-it.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| every planning task is reachable only through a 10 GB environment | this story lands | `pixi install -e pyforge-guild` from cold is under 1 GB on disk and `pixi run -e pyforge-guild detectors-ci` is green on `main` | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | every moved task still runs as `pixi run -e local-recipes <task>` because `local-recipes` includes `pyforge-guild`; no task name exists in two features | n/a |
| And-clause from epics.md | when the story lands | `pyforge-station-tests` and `pr-preflight` pass from `pyforge-guild`; `environment.yaml` is regenerated | n/a |
| And-clause from epics.md | when the story lands | the token-economy kit is on the floor, not assumed: `headroom` and `node` resolve on PATH in `pyforge-guild`, `marshal seed check` reports the headroom kit item present, and a dispatch dry-run raises… | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `pixi.toml` (`[feature.pyforge-guild]`, `[environments]`, the 48 moved `[feature.pyforge-guild.tasks.*]`), `pixi.lock`, `environment.yaml`, `scripts/detectors.py` if it names an env.
Ledger key: `63-1-the-pyforge-guild-feature-and-environment-exist-and-the-guild-tasks-live-in-it`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-63-1-the-pyforge-guild-feature-and-environment-exist-and-the-guild-tasks-live-in-it.md`.

## Epic excerpt

**Type:** infra • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-steward CAP-5
**Surface:** `pixi.toml` (`[feature.pyforge-guild]`, `[environments]`, the 48 moved `[feature.pyforge-guild.tasks.*]`), `pixi.lock`, `environment.yaml`, `scripts/detectors.py` if it names an env.
**Given** every planning task is reachable only through a 10 GB environment
**When** this story lands
**Then** `pixi install -e pyforge-guild` from cold is under 1 GB on disk and `pixi run -e pyforge-guild detectors-ci` is green on `main`
**And** every moved task still runs as `pixi run -e local-recipes <task>` because `local-recipes` includes `pyforge-guild`; no task name exists in two features
**And** `pyforge-station-tests` and `pr-preflight` pass from `pyforge-guild`; `environment.yaml` is regenerated
**And** the token-economy kit is on the floor, not assumed: `headroom` and `node` resolve on PATH in `pyforge-guild`, `marshal seed check` reports the headroom kit item present, and a dispatch dry-run raises no `MRS-DISP-033` (the 2026-09-01 silent no-op shape)
**Status:** backlog

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `0896705b3b` (2026-09-16, "steward 63.1 follow-up: resolve tasks by declaring feature; pr-preflight gains the scripts-suite leg"); also `7f1316dffa` (2026-09-16, "steward 63.1: pyforge-guild -- the Guild's minimal session environment (859 MB vs 10 GB)"). Ledger row `63-1-the-pyforge-guild-feature-and-environment-exist-and-the-guild-tasks-live-in-it: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `pixi.toml`, `src/shared/packages/pyforge-steward/tests/unit/test_guards.py`, `tests/scripts/test_deck_facts.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
