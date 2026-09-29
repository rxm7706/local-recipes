---
title: README, adoption guide, and the finding→remedy reference
type: docs
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 98feec0d412
---

<intent-contract>

## Intent

**Problem:** First-time Genesis adopters lack a single place that explains the four verbs, five artifact classes, findings remedies, and brownfield adoption path (NFR-M3, D1).

**Approach:** Ship package README + finding→remedy reference + adoption guide covering verbs, classes, versions, state file, air-gap note, and managed-region contract; add a staleness test that every findings-enum member appears in the reference.

## Acceptance Criteria

- README covers all four verbs with worked examples, five artifact classes, two version numbers, state file role.
- Finding → remedy reference documents every findings-enum member with severity and fix (NFR-M3), SYNC-RUNBOOK shape.
- Adoption guide: dry-run → review plan → apply → wire `check` into CI.
- Air-gapped deployment note: in-package templates + conda-provisioned engine.
- Managed-region contract documented (markers, edit detection, delete = sanctioned opt-out).
- Test asserts every findings-enum member appears in the reference doc.

## Boundaries & Constraints

**Never:** Change CLI contracts from Story 12-5. Docs-only + staleness test.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/README.md`
- Finding-remedy reference under package docs/ or repo docs/ as established by siblings
- Staleness test under `tests/`

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `98feec0d41` (2026-08-23, "Merge pull request #654 from rxm7706/marshal/12-6-readme-adoption-guide"). Ledger row `12-6-readme-adoption-guide-and-the-finding-remedy-reference: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `src/shared/packages/pyforge-marshal/README.md`, `src/shared/packages/pyforge-marshal/docs/adoption-guide.md`, `src/shared/packages/pyforge-marshal/docs/air-gapped-deployment.md`, `src/shared/packages/pyforge-marshal/docs/finding-remedy-reference.md`, `src/shared/packages/pyforge-marshal/docs/managed-region-contract.md`, `src/shared/packages/pyforge-marshal/tests/meta/test_finding_remedy_reference_sync.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
