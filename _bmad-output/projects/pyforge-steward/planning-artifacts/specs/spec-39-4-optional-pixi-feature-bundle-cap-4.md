---
title: Optional pixi feature bundle (CAP-4)
type: feature
created: '2026-09-01'
status: ready
updated: '2026-09-01'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-metapackage/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/install-matrix.md
  - recipes/bmad-suite/suite-members.yaml
  - recipes/bmad-suite/recipe.yaml
  - pixi.toml
warnings: []
deferred: []
baseline_revision: 770672a1564c59cbe832a509d52907e66c4589ca
---

<intent-contract>

## Intent

**Problem:** CAP-1–3 shipped the `bmad-suite` metapackage on SelfExplainML (`2026.9.1`), but the factory still carries ~11 separate `bmad-*` pins under `[feature.local-recipes.dependencies]`. Greenfield operators who want the full suite have no documented one-pin pixi path; CAP-4 in `spec-bmad-suite-metapackage` remains open.

**Approach:** Add an opt-in `[feature.bmad-suite-full]` that depends on the published `bmad-suite` metapackage from SelfExplainML, plus a lean proof environment that composes only that feature (solver smoke without pulling the fat `local-recipes` graph). Leave the factory default untouched — `local-recipes` keeps every explicit member pin for pipeline-truth / doctor drift granularity. Extend `install-matrix.md` with a greenfield “one pin” row and cite the feature name. Do not fold dashboard installs into this feature (`feature.bmad-ui` stays separate).

## Acceptance Criteria

- Given `pixi.toml`, when parsed, then `[feature.bmad-suite-full]` exists with `channels` including `SelfExplainML` and a `bmad-suite` floor matching the published metapackage CalVer (`>=2026.9.1` at spec time).
- Given the `local-recipes` environment definition, when inspected, then it does **not** compose `bmad-suite-full` (factory explicit pins remain authoritative).
- Given `[feature.local-recipes.dependencies]`, when compared to baseline, then every existing `bmad-*` member pin block is unchanged (no removal or replacement by this story).
- Given a new lean environment (e.g. `bmad-suite-full`) composing `[feature.bmad-suite-full]` (+ minimal `python`), when `pixi lock --check -e bmad-suite-full` runs on CI-capable hardware, then the lock resolves without error.
- Given `install-matrix.md`, when read, then a **Greenfield one-pin** section documents `feature.bmad-suite-full` / `bmad-suite` as the suite install path and states that `bmad-method` remains conda-forge-canonical inside the metapackage (not a separate pixi pin when using the bundle).
- Given `[feature.bmad-ui]`, when inspected, then it is byte-identical aside from incidental lock regeneration — this story does not move or duplicate dashboard deps.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` per dispatch — never `scripts/bmad-switch`. Metapackage population stays `recipes/bmad-suite/suite-members.yaml` (13 active); WDS stays published-but-skip-wired per parent install-matrix. Regenerate `pixi.lock` only for the new proof env / feature slice.

**Block If:** Individual `bmad-*` pins are removed from `[feature.local-recipes.dependencies]`; `local-recipes` env starts composing `bmad-suite-full`; dashboard deps migrate into `bmad-suite-full`; or a conda-forge feedstock for `bmad-suite` is attempted.

**Never:** Auto-merge refresh PRs. Wire modules through `steward provision` (CAP-3 scope). Replace `feature.bmad-ui`. Reimplement CAP-1–3 generator/recipe logic. Touch doctor Story 19.1 manifest reader.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Feature declared | `pixi.toml` parse | `[feature.bmad-suite-full.dependencies]` lists `bmad-suite >=2026.9.1`; feature declares SelfExplainML channel | meta test fails if feature or channel missing |
| Factory default preserved | `environments.local-recipes` | feature list unchanged — no `bmad-suite-full` | test fails if local-recipes composes the bundle feature |
| Member pins intact | diff vs baseline | all pre-existing `bmad-*` lines under `[feature.local-recipes.dependencies]` retained | test fails on pin removal |
| Proof env solves | `pixi lock --check -e bmad-suite-full` | exit 0 | fail loud with solver stderr in CI log |
| Greenfield docs | `install-matrix.md` | new section names feature + one `pixi add` example | test fails if section absent |
| Dashboard isolation | `[feature.bmad-ui]` | unchanged deps/tasks | test fails if bmad-ui deps copied into bmad-suite-full |
| Platform selectors | linux-only member (`bmad-module-skill-forge`) | metapackage run deps express platform skip; proof env on linux-64 resolves | solver failure surfaces upstream; do not duplicate per-member pins into the feature |

</intent-contract>

## Code Map

- `pixi.toml` — add `[feature.bmad-suite-full]` (+ channels/deps comment citing `spec-bmad-suite-metapackage` CAP-4); add lean `[environments.bmad-suite-full]` proof env; do **not** alter `[feature.local-recipes.dependencies]` bmad block or `[environments.local-recipes]` feature list.
- `pixi.lock` — lockfile delta for the new feature/env only (minimal regeneration).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/install-matrix.md` — greenfield one-pin section (feature name, metapackage channel, note that `bmad-ui` remains opt-in via `feature.bmad-ui`).
- `tests/packaging/test_bmad_suite_full_feature.py` — new: tomllib structural tests (feature exists, local-recipes does not compose it, local-recipes pins preserved, bmad-ui untouched); optional subprocess guard skipping `pixi lock --check` when pixi absent.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-39-4-optional-pixi-feature-bundle-cap-4.md` — this spec (tracked contract).
- Read-only references: `recipes/bmad-suite/recipe.yaml`, `recipes/bmad-suite/suite-members.yaml`, `spec-bmad-suite-metapackage/SPEC.md`.

## Tasks & Acceptance

**Execution:**
- `pixi.toml` — declare `[feature.bmad-suite-full]` and proof environment — CAP-4 opt-in surface
- `install-matrix.md` — document greenfield one-pin install path — operator discoverability
- `tests/packaging/test_bmad_suite_full_feature.py` — lock structural invariants — CI guard without full factory solve
- `pixi.lock` — refresh for new env — solver proof artifact
- planning-artifacts spec + ledger finalize on merge — durable contract

**Acceptance Criteria:** (same as intent-contract AC block — dispatch uses this file as the verification oracle.)

## Verification

- `pytest tests/packaging/test_bmad_suite_full_feature.py -q` → green
- `pixi lock --check -e bmad-suite-full` → exit 0 (from repo root)
- `pixi run -e pyforge-steward pyforge-steward-test` → green (no steward code changes expected; packaging test is primary)
- Manual: `install-matrix.md` greenfield section readable; `steward suite pipeline-truth` still reports 13 packages (factory pins unchanged)

## Spec Change Log

- 2026-09-01: Drafted from Epic 39.4 / `spec-bmad-suite-metapackage` CAP-4; unblocks steward fleet drain (`MRS-DISP-005`).
