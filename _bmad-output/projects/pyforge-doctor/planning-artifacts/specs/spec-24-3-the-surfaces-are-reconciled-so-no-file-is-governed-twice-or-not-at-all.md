---
title: '24.3: The surfaces are reconciled so no file is governed twice or not at all'
type: 'fix'
created: '2026-09-16'
status: 'in-review'
baseline_revision: 'e9d593f0cb79a73b623026f0008803cc54f58ec6'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 24.1 moves files testing-charter currently lists while the governance Spec surface is [] until the move.

**Approach:** Governance Spec declares its surface; testing-charter drops the two drivers; both memlogs record the hand-over; each key is stamped scoped. spec-surface reports no ungoverned and no drift. Surfaces are disjoint. git ls-files shows every new path tracked before the stamp.

## Boundaries & Constraints

**Always:**
- Scoped --write-baseline --spec <key> only, never bare.
- Governance and testing-charter surfaces are disjoint.

**Never:**
- Do not run a bare spec_surface_check.py --write-baseline.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| after stamps | spec-surface | no ungoverned, no drift on moved paths | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-coverage-gate-independence CAP-1; spec-pyforge-testing-charter surface; spec-surface baseline`.
Surface: docs/governance/spec-coverage-gate-independence/SPEC.md + .memlog.md; spec-pyforge-testing-charter SPEC.md + .memlog.md; scripts/.spec-surface-baseline.json (scoped stamps only)..
Ledger key: `24-3-the-surfaces-are-reconciled-so-no-file-is-governed-twice-or-not-at-all`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-24-3-the-surfaces-are-reconciled-so-no-file-is-governed-twice-or-not-at-all.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

