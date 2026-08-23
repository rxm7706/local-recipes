---
title: Dependencies are pixi-sourced, single-authority
type: chore
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 4d9c58ae85
---

<intent-contract>

## Intent

**Problem:** `src/platform/requirements/{base,local,production}.txt` still share authority with `[feature.platform-ci-test]` / platform-dev pixi features (guarded by `platform-ci-test-requirements-check`). CAP-5 (`spec-platform-fifteen-factors`) requires pixi.toml as the sole dependency authority — CI lanes and Containerfiles build from pixi alone; requirements files retired; docs updated.

**Approach:** Invert the current mirror: make pixi features the only source of truth for platform Python deps; delete or stop consuming `src/platform/requirements/*.txt`; retarget CI / Containerfile / docs / drift guard so nothing installs via `pip install -r` for the platform host. Suites stay green. Borrow MIT notices if any reference pattern is copied.

## Acceptance Criteria

- `src/platform/requirements/*.txt` retired (deleted or clearly non-authoritative tombstones with no install consumers).
- Platform CI lanes and both Containerfile stages resolve platform deps from pixi alone (no `pip install -r …/requirements`).
- Docs that taught the requirements chain updated to cite pixi features.
- Drift guard / reconciler either removed or rewritten so pixi is the authority (not requirements→pixi).
- Related platform / local-recipes tests green.
- Does not implement 16.2–16.5 (startup refusals, telemetry, policy-as-tests, OIDC) or steward 12-7 / 17.x.

## Boundaries & Constraints

**Never:** Touch AD-4/AD-17 topology or the 12.1 chart contract (factors as seams only). Never `scripts/bmad-switch`. Never auto-merge. Finalize steward ledger only. Do not touch marshal 20-2. Skip 12-7 forever.

</intent-contract>

## Code Map

- `src/platform/requirements/{base,local,production}.txt`
- `pixi.toml` — `[feature.platform-dev]`, `[feature.platform-ci-test]` (+ pypi-dependencies)
- `scripts/platform_ci_test_requirements_check.py` + pixi tasks `platform-ci-test-requirements-check` / `fix-platform-ci-test-requirements`
- Root `Containerfile` / platform image build paths
- Platform docs referencing the requirements chain

## Verification

- No install consumer of `src/platform/requirements/*.txt`
- CI + image build path uses pixi only
- `pixi run --frozen -e local-recipes` / `pyforge-steward` related tests green; CI detectors/linter/package tests
