---
title: '49.12: Index — mason realization-gate effect stories'
type: 'docs'
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

**Problem:** the `pyforge-mason` recipe verb family is `done` and unreachable — `mason doctor` reports `unavailable_verbs: ('recipe',)` because `[feature.pyforge-mason.dependencies]` (`pixi.toml:281-283`, two lines) lacks the `truststore` + `conda-forge-metadata` floor `cfe.py:180-186` requires, and nothing in the estate invokes `mason recipe|package|environment` **When** mason lands the dependency fix and on…

**Approach:** this row flips `done`

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-49-12-index-mason-realization-gate-effect-stories.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| the `pyforge-mason` recipe verb family is `done` and unreachable — `mason doctor` reports `unavailable_verbs: ('recipe',)` because `[feature.pyforge-mason.depe… | mason lands the dependency fix and one real invocation **Then** this row flips `done` | this row flips `done` | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the fix touches `pixi.toml`, which is steward-adjacent: if the dependency lines are added in a steward PR, that PR **regenerates `environment.yaml`** (ungated by the `maintenance` label) — named here… | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: this file only (the index row). Mason's own artifacts are **named, never edited** by steward
Ledger key: `49-12-index-mason-realization-gate-effect-stories`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-49-12-index-mason-realization-gate-effect-stories.md`.

## Epic excerpt

**Type:** index • **Effort:** S • **Deps:** S-49.2; cross-station: mason's effect epic (ledger `blocked` until it closes) • **FR/AD:** fleet readiness 2026-09-09 § 2.3 C6
**Surface:** this file only (the index row). Mason's own artifacts are **named, never edited** by steward
**Given** the `pyforge-mason` recipe verb family is `done` and unreachable — `mason doctor` reports `unavailable_verbs: ('recipe',)` because `[feature.pyforge-mason.dependencies]` (`pixi.toml:281-283`, two lines) lacks the `truststore` + `conda-forge-metadata` floor `cfe.py:180-186` requires, and nothing in the estate invokes `mason recipe|package|environment` **When** mason lands the dependency fix and one real invocation **Then** this row flips `done`
**And** the fix touches `pixi.toml`, which is steward-adjacent: if the dependency lines are added in a steward PR, that PR **regenerates `environment.yaml`** (ungated by the `maintenance` label) — named here so the obligation is not discovered at CI
**Status:** done
**Outcome (2026-09-13):** landed as a side effect of `spec-library-catalog-manifest-sync` (marshal Epic 36, PR #1291, `8beb582d30`) — `truststore >=0.10.4` and `conda-forge-metadata >=2026.9.10` are both now in `[feature.pyforge-mason.dependencies]`. Confirmed live: `mason doctor` reports `unavailable_verbs: ()`, and the `pyforge-mason-recipe-build-smoke` task (already wired into `pyforge-station-tests.yml`'s mason-test job) is the real invocation — `pixi run -e pyforge-mason pyforge-mason-recipe-build-smoke` builds `recipes/click-help-colors` via `mason recipe build`, `returncode: 0`, artifact produced. Ledger was never flipped after the work landed.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `49-12-index-mason-realization-gate-effect-stories: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
