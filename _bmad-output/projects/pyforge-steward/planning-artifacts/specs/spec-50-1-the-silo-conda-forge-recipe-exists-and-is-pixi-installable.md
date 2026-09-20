---
title: 'The Silo conda-forge recipe exists and is pixi-installable'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pgsty/silo` (a maintained fork of the MinIO codebase — same S3/IAM API surface,
same on-disk format, same `MINIO_*` env vars — born because upstream MinIO gutted its own
community edition in 2026) has real, versioned per-platform release binaries but no conda-forge
feedstock (live-verified 2026-09-10). Story 50.2's local-dev object-storage tooling needs Silo
to be genuinely pixi-installable as its default backend.

**Approach:** Author a v1-format `recipe.yaml` under `recipes/silo/` wrapping the upstream
release binary for this repo's supported platforms, invoking `conda-forge-expert` for the full
recipe lifecycle (this repo's Rule 1: any conda-forge recipe work goes through that skill).
Build and test locally, then publish to the `SelfExplainML` anaconda.org channel — this repo's
own documented staging path (`commands-cheatsheet.md` § *Publishing to the SelfExplainML
channel*) for a recipe pending conda-forge acceptance — so it is pixi-installable immediately.
Submitting to `conda-forge/staged-recipes` for long-term community packaging is the normal
follow-up, not part of this story's own scope.

## Boundaries & Constraints

**Always:**
- The recipe wraps a real, versioned upstream Silo release binary — never a hand-built binary,
  never vendoring the Go source into a from-source build unless CFE's own recipe conventions for
  a Go-binary release require it.
- The four CFE gates pass before publishing: `validate_recipe`, `optimize_recipe`,
  `scan_for_vulnerabilities`, a green linux-64 `recipe-build`.
- Published to `SelfExplainML` only in this story — `conda-forge/staged-recipes` submission is
  named as the follow-up, never silently done or silently skipped.

**Never:**
- Never hand-author outside the `conda-forge-expert` skill's own lifecycle (Rule 1 is
  non-negotiable for conda-forge recipe work in this repo).
- Never touch the AD-1 exception's own boundary — this story only makes Silo installable; it
  does not deploy, launch, or configure anything.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Recipe validated | `recipes/silo/recipe.yaml` authored | `validate_recipe` passes | N/A |
| Recipe built locally | linux-64 target | `recipe-build` produces a real `.conda` artifact | N/A |
| Package published | Built artifact | `anaconda upload --user SelfExplainML` succeeds | N/A |
| pixi resolves it | `pixi.toml` references `silo` | `pixi install` resolves the SelfExplainML-channel package | N/A |

</intent-contract>

## Code Map

- `recipes/silo/recipe.yaml` — new, v1 format
- `recipes/silo/` — supporting files per CFE convention (patches, tests, as the recipe needs)
- `pixi.toml` — Story 50.2 adds the actual dependency reference; this story does not touch
  `pixi.toml` itself

## Tasks & Acceptance

**Execution:**
- `feature` — invoke `conda-forge-expert`; generate/author `recipes/silo/recipe.yaml` for
  `pgsty/silo`'s upstream release.
- `feature` — run the full CFE submission-ready gate (`validate_recipe`, `optimize_recipe`,
  `scan_for_vulnerabilities`, green linux-64 `recipe-build`).
- `feature` — publish the built package to the `SelfExplainML` anaconda.org channel.

**Acceptance Criteria:**
- Given `pgsty/silo` has real release binaries but no conda-forge feedstock, when a v1-format
  recipe is authored and carried through the full CFE lifecycle, then the recipe is genuinely
  buildable and testable locally.
- And the built package is published to `SelfExplainML`, so `pixi install` can resolve it
  without waiting on upstream conda-forge review.
- And upstream `conda-forge/staged-recipes` submission is named as the follow-up, not done or
  silently skipped in this story.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: full suite green (no
  steward code changes; this story is recipe-only, this command proves nothing else regressed)

## Spec Change Log

### 2026-09-10 — Landed
- `recipes/silo/recipe.yaml` authored (v1, binary-repackage of `pgsty/silo` release
  `RELEASE.2026-09-03T13-18-01Z`, conda version `20260903131801.0.0`), full CFE gate green
  (validate/optimize/scan/build all clean, linux-64 build + test), published to
  `https://anaconda.org/SelfExplainML/silo`. Landed via PR
  `rxm7706/local-recipes#1183` (merged `af704b562a`), based on local verification per the
  confirmed CI billing outage. `staged-recipes` submission deliberately NOT done — named
  follow-up per this story's own scope, and per an explicit operator instruction (no
  conda-forge PRs without confirmation).

## Review Triage Log

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `42dbaea6e0` (2026-09-10, "chore(steward): promote Story 50.1 to done in sprint ledger"); also `0187ec00b5` (2026-09-10, "feat(recipes): add Silo conda-forge recipe (pyforge-steward Story 50.1)"). Ledger row `50-1-the-silo-conda-forge-recipe-exists-and-is-pixi-installable: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-50-1-the-silo-conda-forge-recipe-exists-and-is-pixi-installable.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
