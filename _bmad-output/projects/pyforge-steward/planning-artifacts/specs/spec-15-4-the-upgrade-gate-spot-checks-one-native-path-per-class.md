---
title: The upgrade gate spot-checks one native path per class
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: 9f32ca77067f8e9f49708a8d396367b26f51dabb
deferred:
  - summary: >-
      Live prove-landed may still hit the network / warm caches when running
      cited npx/uv spot-checks even with --help/--dry-run.
    evidence: |-
      Story 15.4 deliberately invokes native CLIs; side effects are inherent
      to the AC. Failures remain advisory.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
    severity: medium
  - summary: >-
      skip_native_spot_checks exists on build_prove_landed_report but has no
      CLI flag.
    evidence: |-
      Not required by CAP-4 AC.
    severity: low
  - summary: >-
      _BMAD_LOOP_UV_GIT_SPEC hard-pins v0.11.0 with no regeneration note when
      the matrix version moves.
    evidence: |-
      Citation substring test catches matrix edit drift after the fact.
    severity: low
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

- `install-matrix.md` under steward `spec-bmad-suite-channel-product`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` — CAP-5 prove-landed + advisory native spot-checks
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_native_path_spot_checks.py`

## Verification

- `pixi run --frozen -e pyforge-steward pytest …/test_upgrade_native_path_spot_checks.py …/test_upgrade_prove_landed.py -q` — 14 passed
- Fixture covers seven classes; dashboards doc-only; advisory fail keeps CLI EXIT_OK
- CI: detectors, linter, package tests

## Auto Run Result

Status: done

### Summary
CAP-5 prove-landed now advisory-spot-checks one cited native path per install-matrix class (dashboards check-by-doc only). Spot-check failures do not flip verdict/DutyResult.ok.
