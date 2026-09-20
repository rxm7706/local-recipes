---
title: '14.7: Custom modules survive the core apply'
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

**Problem:** the installed manifest lists a `source: custom` module (skf) and the release catalog names its own installer, config files and optional pin **When** the apply runs **Then** the module is selected for the core apply, its config files are snapshotted before and restored after, its own installer (`bmad-module-skill-forge update`) runs after the core apply from the repo root, and the report names eac…

**Approach:** the module is selected for the core apply, its config files are snapshotted before and restored after, its own installer (`bmad-module-skill-forge update`) runs after the core apply from the repo root, and the report names each restored file — **And** the fixture replaying 2026-09-06 (skf deselected and deleted by `-y`; `skf-campaign` undeclared in `marketplace.json`; `_bmad/skf/config.yaml` rege…

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-14-7-custom-modules-survive-the-core-apply.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| the installed manifest lists a `source: custom` module (skf) and the release catalog names its own installer, config files and optional pin **When** the apply… | the apply runs | the module is selected for the core apply, its config files are snapshotted before and restored after, its own installer (`bmad-module-skill-forge update`) runs after the core apply from the repo roo… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the fixture replaying 2026-09-06 (skf deselected and deleted by `-y`; `skf-campaign` undeclared in `marketplace.json`; `_bmad/skf/config.yaml` regenerated with a literal `{project-root}/{value}`) end… | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `upgrade.py` (apply + reconcile), release-catalog schema (`custom_modules:`), steward CLI
Ledger key: `14-7-custom-modules-survive-the-core-apply`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-14-7-custom-modules-survive-the-core-apply.md`.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** 14.6 • **FR/AD:** spec-bmad-method-core-upgrade CAP-7
**Surface:** `upgrade.py` (apply + reconcile), release-catalog schema (`custom_modules:`), steward CLI
**Given** the installed manifest lists a `source: custom` module (skf) and the release
catalog names its own installer, config files and optional pin **When** the apply runs
**Then** the module is selected for the core apply, its config files are snapshotted before
and restored after, its own installer (`bmad-module-skill-forge update`) runs after the core
apply from the repo root, and the report names each restored file — **And** the fixture
replaying 2026-09-06 (skf deselected and deleted by `-y`; `skf-campaign` undeclared in
`marketplace.json`; `_bmad/skf/config.yaml` regenerated with a literal
`{project-root}/{value}`) ends with the module's skill dirs equal to its packaged source and
its config equal to the pre-apply bytes plus the installer's own appended keys
(failure-modes.md traps 13–14).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `196b8a8d2a` (2026-09-06, "feat(steward): CAP-7 — custom modules survive the core apply (Story 14.7)"). Ledger row `14-7-custom-modules-survive-the-core-apply: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/customization-inventory.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/failure-modes.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-scratch-worktree-lifecycle/.memlog.md`, `scripts/.spec-surface-baseline.json`, `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/6.12.0.yaml`, `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py`, `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py`, `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_preflight.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
