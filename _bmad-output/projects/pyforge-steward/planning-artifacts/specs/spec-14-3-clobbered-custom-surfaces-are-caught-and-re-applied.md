---
title: Clobbered custom surfaces are caught and re-applied
type: feature
created: '2026-08-23'
status: done
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


## Implementation Notes

- CAP-3 wired into `apply_bmad_core_upgrade` after the CAP-2 custom fingerprint check.
- Surfaces snapshotted pre-apply; post-apply detect → restore from installer `.bak` (preferred) or snapshot; else flag.
- Six-layer success via `BMAD_ACTIVE_PROJECT` and fixture-local `.active-project` (never `scripts/bmad-switch`).
- Installer `.bak` paths are always listed in `ReconcileReport.bak_files_accounted`.
- Tests: `tests/unit/test_upgrade_reconcile.py`.


## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/669
Merge SHA: e7d2ead159c59e974f44d600da2312d431433063
Finalize: 10d6c1149324ec6cf6324acc667bb6862fe1fc9f
Tests: 27 passed locally (reconcile+apply+preflight); CI green
