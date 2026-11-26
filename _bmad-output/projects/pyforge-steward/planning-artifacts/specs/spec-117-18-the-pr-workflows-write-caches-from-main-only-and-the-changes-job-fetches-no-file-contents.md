---
title: '117.18: The PR workflows write caches from main only, and the changes job fetches no file contents'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 117-18-the-pr-workflows-write-caches-from-main-only-and-the-changes-job-fetches-no-file-contents
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/pyforge-station-tests.yml'
  - '.github/workflows/detectors.yml'
  - '.github/workflows/lint-types.yml'
  - '.github/workflows/cfe-regression-net.yml'
  - '.github/workflows/pages.yml'
  - '.github/workflows/marshal-local-recipes-seed-oracle.yml'
  - '.github/workflows/copilot-setup-steps.yml'
  - 'tests/durations/pyforge-steward-live.json'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Actions cache holds 41.7 GB against a 40 GB limit; 14.9 GB of it was written from PR refs, which no later run can read. In the seven workflows a pull request runs, 37 `setup-pixi` uses set no `cache-write`, and `lint-types` saves a new mypy cache entry (about 46 MB) for every source change. The `changes` job takes 15 to 21 s ahead of every station job, and 11 to 16 s of that is a two-commit fetch of every file's contents, for a job that only compares trees.

**Approach:** Set `cache-write` to pushes on `main` on those 37 `setup-pixi` uses. Split the mypy cache into a restore on every run and a save from `main` alone. Fetch the `changes` job's two commits with `filter: blob:none` and check out `.github/` only. Re-measure the steward live half's shard durations, which Story 117.14 changed.

Ledger key: `117-18-the-pr-workflows-write-caches-from-main-only-and-the-changes-job-fetches-no-file-contents`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- spec-pyforge-steward CAP-166 (the CI surfaces registry; no surface added or removed).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Measure before and after with the harness that measured the baseline (same tree shape, same machine).
- Check every edited workflow for duplicate keys and with the workflow meta-tests.

**Never:**
- Never narrow a station-tests path array (ruling D4, Story 98.1).
- Never remove a job, a gate or a floor.
- Never add a cache entry class while the cache is over its limit.
- Never change the `changes` job's script: only what it fetches.

## Acceptance Criteria

**Given** the workflows at `d039bc7de3`
**When** the story lands
**Then** a PR head writes no `pixi-` or `mypy-` cache entry, and `changes` computes the same outputs for the same diff
**And** the workflow meta-tests pass

- **AC1 — The workflow meta-tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

- **AC2 — On the PR head, no cache entry is created on the PR ref.** Expected: no `pixi-` or `mypy-` key on `refs/pull/<n>/merge`.

  ```bash
  gh cache list --repo rxm7706/local-recipes --ref refs/pull/<n>/merge --json key,sizeInBytes
  ```

</intent-contract>

## Evidence (2026-11-26)

`gh api repos/rxm7706/local-recipes/actions/cache/usage`: 41,737,411,252 bytes; limit 40 GB; 40 entries (14.90 GB) on `refs/pull/*`. Gate jobs 18 to 57 s each over eight PR heads. `changes` 17 s median. Detectors fetch 22.3 s median, 50.8 s at most.

## Not built in this story (2026-11-26)

Three parts of the approved plan were dropped after they were measured, and the story was renamed to what it does.

- **The gates in a small environment.** The local preflight matches a gate lane to its CI step by the step's command line and environment, so moving the CI step to another environment unbinds all eight lanes from CI. The gain is the environment restore of one gate job at the end of the critical path, about 10 s (`herald-gate`: 22 s).
- **A shallower fetch for the detectors.** The detectors read commit dates (`docs-currency`, `chain-currency`), merge subjects (`story-status`) and a base commit (`fr-without-cap`, `ledger-regression`), so they need the history they fetch.
- **The image layer order.** No workflow keeps a layer cache (no buildx, no `cache-from`), so a reordered layer is never reused on a fresh runner, and the cache is already over its limit. The image builds run on pushes to `main` and nightly, not on a pull request, so a change to them cannot be proved before it lands.

## Review round (2026-11-26)

The independent review held one finding: three Platform CI cluster jobs set up pixi with `cache: true` and no `cache-write`, and can run on a pull request when their variables are on, so "a PR head writes no `pixi-` cache entry" was not met. `platform-ci.yml`'s four `setup-pixi` uses now carry the same gate.
