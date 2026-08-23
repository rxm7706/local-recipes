---
title: Clobbered custom surfaces are caught and re-applied
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 0c9c17ecb5
---

<intent-contract>

## Intent

**Problem:** After Story 14.2 apply, repo-custom surfaces can still be clobbered — notably `resolve_config.py`'s multi-project layers 5/6 (clobbered in both manual upgrades) — with no detect/re-apply path (spec-bmad-method-core-upgrade CAP-3).

**Approach:** Extend the steward upgrade duty so that after a completed apply, clobbered repo-custom surfaces are detected and re-applied or flagged. Success criterion: `bmad-switch --current` AND a `BMAD_ACTIVE_PROJECT` override resolve all six config layers post-apply; installer `.bak`s are accounted for.

## Acceptance Criteria

- After a completed apply, clobbered repo-custom surfaces are detected (named regression: `resolve_config.py` layers 5/6).
- Clobbered surfaces are re-applied or flagged (never silently left broken).
- Success: `bmad-switch --current` AND `BMAD_ACTIVE_PROJECT` override resolve all six layers post-apply.
- Installer `.bak`s are accounted for.
- Fixture-covered; depends on 14.2 apply path.

## Boundaries & Constraints

**Never:** Implement 14.4 pin fan-out or later CAP stories. Never `scripts/bmad-switch` from parallel agents during tests that mutate shared marker — use env override. Steward 12-7 remains skipped. Finalize steward ledger only.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` — post-apply detect/re-apply
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — upgrade verbs
- `_bmad/scripts/resolve_config.py` — layers 5/6 named regression case (read/verify, do not break)
- Unit tests under `pyforge-steward/tests/`

## Verification

- `pixi run --frozen -e pyforge-steward pytest …` green
- Fixture covering layers 5/6 clobber → detect → re-apply/flag
- CI: detectors, linter, package/platform tests as applicable
