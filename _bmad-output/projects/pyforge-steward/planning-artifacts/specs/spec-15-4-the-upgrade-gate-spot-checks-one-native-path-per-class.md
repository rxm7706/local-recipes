---
title: The upgrade gate spot-checks one native path per class
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: b28dde1f7d
---

<intent-contract>

## Intent

**Problem:** Dual-path install matrix claims seven native-method classes, but the upgrade verification gate does not exercise a cited native command per class (spec-bmad-suite-channel-product CAP-4).

**Approach:** Extend the Epic 14 CAP-5 upgrade-gate orbit so it spot-checks ≥1 cited native command per class from `install-matrix.md` (the tracked contract). Dashboards excluded by build cost (check-by-doc only). Failures are reported, not gating. Matrix remains the cited source of truth.

## Acceptance Criteria

- Gate exercises ≥1 cited native command for each non-dashboard class in the matrix.
- Dashboard classes: check-by-doc only (documented exclusion).
- Failures reported (warn / non-zero advisory), not hard-gating the upgrade prove-landed path unless already required by Epic 14.
- `install-matrix.md` stays the cited source of truth (no invented commands).
- Does not implement Epic 16+ platform hardening stories.

## Boundaries & Constraints

**Never:** Auto-merge. Never invent native commands not in the matrix. Never `scripts/bmad-switch`. Steward 12-7 remains skipped. Finalize steward ledger only. Do not touch marshal 19-4 / PR #679.

</intent-contract>

## Code Map

- install-matrix under steward bmad-suite-channel-product planning artifacts
- Epic 14 CAP-5 / `steward upgrade prove-landed` orbit
- Unit/fixture tests for per-class spot-check + dashboard doc-only path

## Verification

- `pixi run --frozen -e pyforge-steward pytest …` green
- Fixture covers seven classes; dashboards doc-only
- CI: detectors, linter, package tests
