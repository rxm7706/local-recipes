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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `3a9030c8bb` (2026-09-02, "steward: Story 41.4 follow-up review — whitespace, hostname checking, and three unpinned guarantees"); also `f098b49823` (2026-09-02, "marshal: promote sprint-status ledger for pyforge-steward (41.4 and epic-41 -> done)"); also `13e50483b3` (2026-09-02, "steward: Story 41.4 — record the review triage and close the spec"). Ledger row `41-4-the-currency-detector-is-fixed-before-its-data-is-caught-up: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md`, `src/platform/config/broker_tls.py`, `src/platform/config/startup/stage_one.py`, `src/platform/deploy/README.md`, `src/platform/tests/test_broker_tls_verified.py`, `src/platform/tests/test_startup_required_settings.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
