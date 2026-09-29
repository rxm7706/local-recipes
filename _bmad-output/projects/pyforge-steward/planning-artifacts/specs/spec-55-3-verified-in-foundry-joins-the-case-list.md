---
title: 'verified-in-foundry joins the case list'
type: 'docs'
created: '2026-09-13'
status: 'done'
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `verified-in-foundry` can be claimed from Frame
preflight. That is not A/B behavior.

**Approach:** Join the claim to a 54.1 case-list id. Missing id is
HARD.

## Boundaries & Constraints

**Always:**
- Case-list id is the join key.

**Never:**
- Never accept Frame schema-only as verification.

</intent-contract>

## Acceptance Criteria

1. Claim without a case-list id is HARD.
2. Claim with a listed id is not HARD for this reason.
3. 54.1 list is the named surface (even if still in progress).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `1bd156d29e` (2026-09-13, "Merge pull request #1348 from rxm7706/steward-55-3-case-list-join"). Ledger row `55-3-verified-in-foundry-joins-the-case-list: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-55-3-verified-in-foundry-joins-the-case-list.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_ledger.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
