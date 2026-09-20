---
title: '14.6: The installer is driven on purpose, and a no-op apply is a refusal'
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

**Problem:** a clean tree and a target release **When** `steward upgrade bmad-core --apply` runs **Then** the installer is invoked with `--directory <repo>`, `--modules <every module `_bmad/_config/manifest.yaml` lists>` (core, bmm and each `source: custom` module) and a closed stdin, with `node` / `bmad-method` resolved from the repo's pixi env when they are not on PATH — no wrapper script — **And** an insta…

**Approach:** the installer is invoked with `--directory <repo>`, `--modules <every module `_bmad/_config/manifest.yaml` lists>` (core, bmm and each `source: custom` module) and a closed stdin, with `node` / `bmad-method` resolved from the repo's pixi env when they are not on PATH — no wrapper script — **And** an installer exit 0 that left zero changed paths is reported `ok=False` with failure-modes.md trap 12…

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-14-6-the-installer-is-driven-on-purpose-and-a-no-op-apply-is-a-refusal.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| a clean tree and a target release **When** `steward upgrade bmad-core --apply` runs **Then** the installer is invoked with `--directory <repo>`, `--modules <ev… | `steward upgrade bmad-core --apply` runs **Then** the installer is invoked with `--directory <repo>`, `--modules <every… | the installer is invoked with `--directory <repo>`, `--modules <every module `_bmad/_config/manifest.yaml` lists>` (core, bmm and each `source: custom` module) and a closed stdin, with `node` / `bmad… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | an installer exit 0 that left zero changed paths is reported `ok=False` with failure-modes.md trap 12 named (the 2026-09-06 first apply was exactly that silent no-op), never a green. | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` (apply path), release catalogs
Ledger key: `14-6-the-installer-is-driven-on-purpose-and-a-no-op-apply-is-a-refusal`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-14-6-the-installer-is-driven-on-purpose-and-a-no-op-apply-is-a-refusal.md`.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** 14.2 • **FR/AD:** spec-bmad-method-core-upgrade CAP-6
**Surface:** `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` (apply path), release catalogs
**Given** a clean tree and a target release **When** `steward upgrade bmad-core --apply`
runs **Then** the installer is invoked with `--directory <repo>`, `--modules <every module
`_bmad/_config/manifest.yaml` lists>` (core, bmm and each `source: custom` module) and a
closed stdin, with `node` / `bmad-method` resolved from the repo's pixi env when they are
not on PATH — no wrapper script — **And** an installer exit 0 that left zero changed paths
is reported `ok=False` with failure-modes.md trap 12 named (the 2026-09-06 first apply was
exactly that silent no-op), never a green.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `0286066638` (2026-09-06, "feat(steward): CAP-6 — the apply drives the installer on purpose and refuses a zero-diff exit 0 (Story 14.6)"). Ledger row `14-6-the-installer-is-driven-on-purpose-and-a-no-op-apply-is-a-refusal: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/customization-inventory.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/failure-modes.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `scripts/.spec-surface-baseline.json`, `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py`, `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py`, `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_reconcile.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
