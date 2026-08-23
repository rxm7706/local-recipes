---
title: README, adoption guide, and the finding→remedy reference
type: docs
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 8b1c76cccc
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
