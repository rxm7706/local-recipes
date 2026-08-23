---
title: marshal seed explain and marshal seed version
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 88be2d2e07c8dec2df4501b0c95256a18a331e29
---

<intent-contract>

## Intent

**Problem:** Genesis seed conventions (artifact classes, rationale, hybrid regions, version pairing) are only narrated in prose — agents cannot query the model programmatically (FR-125, FR-127).

**Approach:** Add read-only CLI verbs `marshal seed explain <artifact>` and `marshal seed version` under `seed/verbs/`, wired through `cli/seed.py`. Explain resolves artifact id or repo path to a manifest entry and prints class, rationale, update behavior, and hybrid regions/anchors. Version prints CLI version, bundled model version, and adopted-repo model version when run inside an adopted tree.

## Acceptance Criteria

- Given an artifact id or path, when `marshal seed explain <artifact>` runs, then it prints class, manifest rationale, update behavior, and (for hybrid) regions and anchors; unknown artifacts get a helpful message with near matches.
- Given `--json`, then explain emits the same data structurally.
- When `marshal seed version` runs, then it prints CLI version and bundled model version, plus the adopted repo's model version when inside one (FR-125).
- Both verbs are read-only (no writes, no network).

## Boundaries & Constraints

**Always:** argparse-only CLI (AD-51 — no typer/rich). Reuse manifest resolution patterns from existing seed verbs.

**Never:** Mutating state, network I/O, or conda-forge recipe work.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/explain.py` — NEW
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/version.py` — NEW
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py` — register subcommands
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_explain.py` — NEW
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_version.py` — NEW

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pytest tests/packaging/test_dependency_completeness.py -k pyforge-marshal`

## Auto Run Result

Status: done

**Summary:** Implemented read-only `marshal seed explain <artifact>` and `marshal seed version` verbs (Story 11.6, FR-125/FR-127). Explain resolves manifest entries by id or path, renders class/rationale/update behavior/hybrid regions, supports `--json`, and suggests near matches on unknown queries. Version reports CLI semver, bundled model version, and adopted repo model version when state is readable.

**Files changed:**
- `seed/verbs/explain.py` — explain verb logic and rendering
- `seed/verbs/version.py` — version report logic and rendering
- `cli/seed.py` — wire subcommands, `--json`, and error handling
- `tests/unit/test_seed_verbs_explain.py` — explain unit tests
- `tests/unit/test_seed_verbs_version.py` — version unit tests
- `tests/unit/test_seed_scaffold.py` — retire explain/version stubs

**Review:** Self-review; no blocking findings. Scaffold tests updated for real verbs.

**Verification:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 5305 passed
- `pixi run --frozen -e pyforge-ci pytest tests/packaging/test_dependency_completeness.py -k pyforge-marshal` — 8 passed
- PR #641 CI: linter pass, detectors pass

**PR:** https://github.com/rxm7706/local-recipes/pull/641 (merge commit `e48ea1292d3`)

**followup_review_recommended:** false
