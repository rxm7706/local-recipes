---
title: Full pixi wiring, distribution, and repo-gate compliance
type: infra
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 88be2d2e07
---

<intent-contract>

## Intent

**Problem:** Genesis (pyforge-marshal seed package) is not wired into the workspace like pyforge-warden — conda/wheel distribution and always-on PR gates are not satisfied (FR-122, AD-64, NFR-C1–C3).

**Approach:** Wire the existing pyforge-marshal member into root pixi.toml (no new env), sync copier pin across pixi.toml / member run-deps / pyproject.toml, add version-range sync test (NFR-C2), regenerate environment.yaml, update library-llms-full.md, maintenance label on PR.

## Acceptance Criteria

- Copier engine dep lands in root `[feature.pyforge-marshal.dependencies]`, member `[package.run-dependencies]`, and pyproject.toml dependencies.
- Existing `pyforge-marshal` env remains lean; no `pyforge-genesis` env; `pyforge-marshal-test` covers `tests/**/seed*`.
- Version-range sync test: pixi.toml copier pin matches constant in `engine/copier.py`.
- Package builds as conda package and wheel+sdist.
- `environment.yaml` regenerated and committed; `llms-full-check` passes.
- PR has `maintenance` label.

## Boundaries & Constraints

**Never:** Create pyforge-genesis env or genesis-named pixi task. No conda-forge recipe work (not a recipes/ effort).

</intent-contract>

## Code Map

- Root `pixi.toml`, member `pixi.toml`, `pyproject.toml`
- `environment.yaml`, `docs/reference/library-llms-full.md`
- Version sync test under pyforge-marshal tests

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run -e local-recipes llms-full-check`
- `pixi project export conda-environment -e build > environment.yaml` (if pixi.toml changed)
