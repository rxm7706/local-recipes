---
title: 'Verify blast radius is pre-existing-gate, not story-refuse (Story 28.22, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'ready'
updated: '2026-09-01'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
baseline_revision: 20e88e8b0fd1ccd2cc38101691ac72aeb8df71cc
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-drain-self-resolution/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `pyforge-deps-test` collection-failed on pandas in two atlas
packaging tests. 28.13 did not touch those files. `MRS-GATE-001` refused the
story; 28.17 would have redispatched into the same red.

**Approach:** Classify a `verify_commands` failure whose failing files/imports
are outside the story diff and effective surface as `pre-existing-gate`
(WARN). Do not refuse the story. Do not transient-retry that command for this
story. Marshal package tests still refuse marshal diffs.

## Acceptance Criteria

- Given a story diff that does not include the failing packaging test, when
  `pyforge-deps-test` collection-fails on pandas, then verification is not
  `MRS-GATE-001` refuse.
- Given `pyforge-marshal-test` failing on the marshal package, when verify
  runs, then the story is still refused.
- Given a `pre-existing-gate` WARN, when the next drain tick runs, then it
  does not redispatch solely to re-hit the same unrelated command.

## Boundaries & Constraints

**Never:** Skip story-caused red CI. Weaken AD-49 hard scope. `scripts/bmad-switch`.

Ledger key: `28-22-verify-blast-radius-pre-existing-gate`.

</intent-contract>

## Code Map

- `core/dispatch_verification.py` / gate classify
- `core/dispatch_retry.py` — do not treat pre-existing-gate as transient retry
- Tests: fixture findings + story diff

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
