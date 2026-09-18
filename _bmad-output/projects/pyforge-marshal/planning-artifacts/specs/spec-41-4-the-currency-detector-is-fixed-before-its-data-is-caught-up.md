---
title: '41.4: The currency detector is fixed before its data is caught up'
type: 'feature'
created: '2026-09-18'
status: 'done'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As a fleet operator, I want the zero-grace currency check given a 2-day window first, and only then the genuinely stale pairs re-stamped, So that noise is removed before data is touched, and real drift stays visible.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `41-4-the-currency-detector-is-fixed-before-its-data-is-caught-up`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / M / S-41.3.

### Living CAP citations

- Cited: `spec-bmad-output-hygiene CAP-11`.

## Acceptance Criteria

- Given a user report of universal "outdated" readings after CAP-10, where 0–1 day `spec`/`prd` findings are true by construction rather than drift When this story lands Then `_FEEDS_GRACE_DAYS = 2` is live in the currency loop and the 0–1 day findings vanish across all 8 stations And only pairs whose own `currency_review` proves the bump was structural are re-stamped

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a user report of universal "outdated" readings after CAP-10, where 0–1 day `spec | this story lands | `_FEEDS_GRACE_DAYS = 2` is live in the currency loop and the 0–1 day findings va | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 41.4 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
