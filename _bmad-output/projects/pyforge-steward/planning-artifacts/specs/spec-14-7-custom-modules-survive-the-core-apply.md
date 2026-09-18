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

