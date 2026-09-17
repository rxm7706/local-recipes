---
title: Optional pixi feature bundle (CAP-4)
type: feature
created: '2026-09-01'
status: done
updated: '2026-09-01'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-metapackage/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/install-matrix.md
  - recipes/bmad-suite/suite-members.yaml
  - recipes/bmad-suite/recipe.yaml
  - pixi.toml
warnings: []
deferred: []
baseline_revision: a35b7d5e59b731ef6bc7b9c42bb96c148cc57521
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

## Review Triage Log

### 2026-09-01 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 3, low 1)
- defer: 0
- reject: 15
- addressed_findings:
  - `[medium]` `[patch]` install-matrix.md claimed "the bundle does not fold dashboard installs in", but `bmad-suite`'s own run deps (verified against `recipes/bmad-suite/recipe.yaml` and the new `pixi.lock` entries) unconditionally pull `bmad-dashboard` and (linux/osx) `mybmad-dashboard` — corrected the wording to distinguish `feature.bmad-ui`'s separate install *surfaces* (VS Code extension, self-hosted web app) from the metapackage's transitive package set, which pulls all 13 active members by design per `spec-bmad-suite-metapackage`'s own CAP-4 success signal.
  - `[medium]` `[patch]` the new live-solver test (`test_pixi_lock_check_resolves_the_bmad_suite_full_environment`) wasn't excluded from `pyforge-ci`'s documented pure-stdlib/no-network `pyforge-deps-test` sweep of `tests/packaging` — confirmed `pixi` is on PATH inside `pyforge-ci` too (`feature.python` pins it), so the `shutil.which` guard alone didn't skip it there. Added a second `skipif` on `PIXI_ENVIRONMENT_NAME == "pyforge-ci"`; verified `pixi run -e pyforge-ci python -m pytest tests/packaging/test_bmad_suite_full_feature.py -q` now shows the test skipped instead of executing a live solve.
  - `[medium]` `[patch]` `bmad-suite` was undocumented in `docs/reference/library-llms-full.md`, confirmed via `pixi run -e local-recipes llms-full-check` reporting a real `undocumented-dep` finding (not speculative) — added a `bmad-suite-full` envs-table row and a `bmad-suite` catalog entry in § 12; detector now reports clean.
  - `[low]` `[patch]` the `pixi add --feature bmad-suite-full bmad-suite` greenfield example didn't mention the target project also needs the `SelfExplainML` channel configured — added a note.

## Spec Change Log

- 2026-09-01: Drafted from Epic 39.4 / `spec-bmad-suite-metapackage` CAP-4; unblocks steward fleet drain (`MRS-DISP-005`).

## Auto Run Result

**Summary:** Added an opt-in `[feature.bmad-suite-full]` (linux-64, channels `conda-forge`+`SelfExplainML`) that depends on the published `bmad-suite` metapackage (`>=2026.9.1`) plus a minimal `python` floor, and a lean `bmad-suite-full` proof environment composing only that feature. `local-recipes` is untouched — it keeps all 11 explicit `bmad-*` pins and does not compose the new feature. `install-matrix.md` gained a "Greenfield one-pin (CAP-4)" section documenting the install path and clarifying that `bmad-suite`'s transitive package set (all 13 active members, including the two dashboard packages) rides along even though `feature.bmad-ui`'s own install *surfaces* (VS Code extension / self-hosted web app) stay separate and unwired. `docs/reference/library-llms-full.md` gained matching catalog entries so its drift detector stays clean.

**Files changed:**
- `pixi.toml` — new `[feature.bmad-suite-full]` block + `bmad-suite-full` environment entry.
- `pixi.lock` — additive-only regeneration for the new environment (0 deletions).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/install-matrix.md` — new Greenfield one-pin section (corrected during review to accurately describe dashboard-package transitivity; added a SelfExplainML-channel note to the `pixi add --feature` example).
- `tests/packaging/test_bmad_suite_full_feature.py` (new) — 8 tomllib structural tests covering every I/O matrix row, plus a live `pixi lock --check` solver-proof test skipped both when `pixi` is absent and when running inside the lean `pyforge-ci` sweep.
- `docs/reference/library-llms-full.md` — envs-table row for `bmad-suite-full` + a `bmad-suite` catalog entry (§ 12), closing an `llms-full-check` drift finding surfaced during review.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-39-4-optional-pixi-feature-bundle-cap-4.md` — this spec (status/baseline bookkeeping + this Auto Run Result).

**Review findings breakdown:** 19 raised across 4 parallel layers (blind hunter, edge-case hunter, verification-gap, intent-alignment auditor) → 4 patched (0 high, 3 medium, 1 low), 0 deferred, 15 rejected (mostly blind-hunter items grounded-out on independent verification: `environment.yaml` re-export confirmed byte-identical, the 13-vs-11-member split already documented in the test's own comments, `review_loop_iteration` correctly stays 0 outside a bad_spec loopback, etc.). See `## Review Triage Log` above for the itemized pass.

**Follow-up review recommendation:** `true` — this pass's patched findings score 3×medium(3) + 1×low(1) = 10 ≥ 5 (no high-severity patches).

**Verification performed:**
- `pytest tests/packaging/test_bmad_suite_full_feature.py -q` → 8 passed.
- `pixi lock --check` → exit 0 (repo's pixi 0.78.0 has no per-environment `-e` selector on `lock`; documented deviation from the spec's literal `-e bmad-suite-full` form).
- `pixi install -e bmad-suite-full` → solved and installed cleanly on linux-64 CI-capable hardware (this session's host).
- `pixi run -e pyforge-steward pyforge-steward-test` → 993 passed.
- `pixi run -e pyforge-steward steward suite pipeline-truth --json` → `package_count: 13` (factory pins unchanged).
- `pixi run -e local-recipes llms-full-check` → clean (post-patch; was 1 finding pre-patch).
- `pixi run -e local-recipes pixi-version-check` → clean.
- `pixi run -e pyforge-ci python -m pytest tests/packaging/test_bmad_suite_full_feature.py -q` → 7 passed, 1 skipped (post-patch; confirms the live-solver test no longer runs inside the lean no-network sweep).
- Manual: `install-matrix.md` greenfield section reviewed for accuracy against `recipes/bmad-suite/recipe.yaml`'s actual run deps.

**Residual risks:**
- `tests/packaging/test_openteams_handoffs.py` carries 4 pre-existing failures (missing local `pyforge-atlas-bootstrap` fixture) confirmed unrelated to this change via `git stash` — not touched, not this story's scope.
- The spec's literal `pixi lock --check -e bmad-suite-full` verification command doesn't exist in this workspace's pinned pixi (0.78.0); the test and manual verification substitute a whole-workspace `pixi lock --check`, which still fails loudly on any unresolvable environment.
- Applying the repo's `maintenance` label (required for any non-`recipes/` PR per CLAUDE.md's always-on gate) is a PR-open-time action, not yet performed as part of this build-auto run.
