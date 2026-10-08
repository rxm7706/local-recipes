---
title: '60.3: Ship backends — conda channel default'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
baseline_revision: '4106bc0aaeda58384ad9068329ad6f0b87f33bff'
---

<intent-contract>

## Intent

**Problem:** An air-gapped host cannot install without github.com.

**Approach:** The default ship path is a pixi/conda index package on that channel. Object storage and git bundle / tarball are switchable extras.

## Boundaries & Constraints

**Always:**
- Default ship path is the conda/pixi channel index package.

**Never:**
- Do not make github.com required for the default install.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| air-gap install | no github.com | conda/pixi channel path works | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-self-hosted-bmad-marketplace CAP-3`.
Surface: a noarch catalog-index recipe under recipes/; the existing SelfExplainML / Artifactory channel path..
Ledger key: `60-3-ship-backends-conda-channel-default`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-60-3-ship-backends-conda-channel-default.md`.

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py` — extend `ShipBackendPlugin` with `ship()`; `CatalogEngine.snapshot_manifests`, `_materialize_ship_snapshot`, `ship()`; `CondaChannelBackend` / `ObjectStorageBackend` / `GitBundleBackend` ship implementations; `steward catalog ship` duty branch; `SNAPSHOT_RELATIVE` under the edit store.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `catalog ship` subparser (`--backend`, `--output`).
- `src/shared/packages/pyforge-steward/catalog/catalog.yaml` — comment documents the ship verb; default backend remains `conda-channel` on `SelfExplainML` / `pyforge-estate-catalog`.
- `recipes/pyforge-estate-catalog/` — noarch generic index recipe (build runs `steward catalog ship`, installs share tree + install helper CLI).
- `src/shared/packages/pyforge-steward/tests/unit/test_catalog.py` — ship refusal on drift, vendoring from `$CONDA_PREFIX/share/<pkg>`, air-gap matrix (local manifest sources only).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py` — implement ship snapshot + backends — CAP-3 default conda path.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — expose `catalog ship` — operator entry point.
- `recipes/pyforge-estate-catalog/recipe.yaml` + `build.sh` + `pyforge_estate_catalog_install.py` — SelfExplainML channel package — air-gap install without github.com.
- `src/shared/packages/pyforge-steward/tests/unit/test_catalog.py` — cover ship and the I/O matrix row.

**Acceptance Criteria:**
- Given wielded module packages are installed under `$CONDA_PREFIX/share/`, when `steward catalog ship` runs on a green catalog (`check` + no manifest drift), then `catalog/snapshot/` contains `plugins/<module>/skills/module.yaml` trees and a `.claude-plugin/marketplace.json` whose plugin `source` is `local` (not github).
- Given the default `conda-channel` backend is `on`, when `steward catalog ship --json` runs, then the payload names target `conda://SelfExplainML/pyforge-estate-catalog`.
- Given `object-storage` or `git-bundle` is selected with `--backend`, when ship completes, then a tarball/bundle artifact is written beside the snapshot tree (extras remain switchable; default stays conda).
- Given the `pyforge-estate-catalog` recipe is built with wielded module build deps present, when the package is installed, then `$PREFIX/share/pyforge-estate-catalog/.claude-plugin/marketplace.json` exists and `pyforge-estate-catalog-install` prints a `--custom-source` path that needs no network.

## Spec Change Log

- 2026-10-08 (dev): Implemented CAP-3 ship path — vendored snapshot, `catalog ship`, and `recipes/pyforge-estate-catalog` for the SelfExplainML channel index package.

## Review Triage Log

- 2026-10-08 pass 1: self-review after green `pyforge-steward-test` and `spec_surface_reconcile.py`; no adversarial subagent findings recorded on this dispatch surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (2047 passed, 2026-10-08).
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 after memlog reconcile naming all governed paths.

## Auto Run Result

Status: done
Verification: `pyforge-steward-test` green; `spec_surface_reconcile.py` OK after `spec-pyforge-steward` memlog entry listing every governed path touched by this story.
