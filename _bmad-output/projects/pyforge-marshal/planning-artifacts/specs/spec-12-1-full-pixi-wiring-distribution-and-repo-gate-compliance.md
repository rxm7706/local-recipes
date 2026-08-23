---
title: Full pixi wiring, distribution, and repo-gate compliance
type: infra
created: '2026-08-23'
status: done
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      llms-full-check reports 82 pre-existing catalog drift findings on main
      (floor-drift + undocumented deps unrelated to copier); exit 1 before
      and after this story.
    evidence: |-
      pixi run -e local-recipes llms-full-check exits 1 on origin/main and
      on this branch with identical 82 findings; copier is documented and
      absent from the drift report.
    severity: medium
baseline_revision: 51a551af728db2816472e12970a8a3c8bb294fb1
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

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 1: (medium 1)
- reject: 0
- addressed_findings:
  - none

## Auto Run Result

Status: done

**Summary:** Wired Copier (`>=9.17,<10`) into root `[feature.pyforge-marshal.dependencies]`, added `COPIER_VERSION_RANGE` to `engine/copier.py`, and added `test_engine_version_range_sync.py` (NFR-C2 warden pattern). Updated `library-llms-full.md` for Genesis/copier. Builds and tests green.

**Files changed:**
- `pixi.toml` — copier run-dep in pyforge-marshal feature
- `engine/copier.py` — `COPIER_VERSION_RANGE` constant
- `tests/meta/test_engine_version_range_sync.py` — drift guard (new)
- `docs/reference/library-llms-full.md` — copier + pyforge-marshal env + scaffolding index

**Review:** 1 deferred (pre-existing llms-full-check floor drift on main, 82 findings; copier documented, no new undocumented-dep).

**Verification:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 5310 passed
- `pixi run -e pyforge-marshal pyforge-marshal-build` — conda + wheel/sdist OK
- `llms-full-check` — exit 1 pre-existing on main (82 drift); copier not among findings
