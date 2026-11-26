---
title: '117.18: The PR workflows write caches from main only and fetch what they read, and the gates run in a small environment'
type: 'chore'
created: '2026-11-26'
status: 'ready-for-dev'
story: 117-18-the-pr-workflows-write-caches-from-main-only-and-fetch-what-they-read-and-the-gates-run-in-a-small-environment
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
  - 'Containerfile'
  - 'src/platform/Containerfile'
  - '.dockerignore'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Actions cache holds 41.7 GB against a 40 GB limit; 14.9 GB of it was written from PR refs, which no later run can read, because 47 of 49 `setup-pixi` uses set no `cache-write`. Each of the eight `*-gate` jobs restores a station environment of 321 to 961 MB to run a script for about a second, and sits at the end of the critical path. The `changes` job takes 15 to 21 s ahead of every station job, 11 to 16 s of it checkout. The Detectors jobs fetch all history (22 s at the median). Every Containerfile copies the tree before `pixi install`, so any edit rebuilds the environment layer.

**Approach:** Set `cache-write` to pushes on `main` on every `setup-pixi` use and save the mypy cache from `main` alone. Run the gates in the smallest environment that carries the gate script's imports. Check out no file contents in `changes`. Fetch in the Detectors jobs the history the detectors read. In each Containerfile copy `pixi.toml`, `pixi.lock` and the path-package manifests first, install, then copy the tree; add the untracked and unneeded large directories to `.dockerignore`. No layer cache: the cache is over its limit.

Ledger key: `117-18-the-pr-workflows-write-caches-from-main-only-and-fetch-what-they-read-and-the-gates-run-in-a-small-environment`.

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

## Acceptance Criteria

**Given** the workflows at `d039bc7de3`
**When** the story lands
**Then** a PR head writes no `pixi-` cache entry, the gates judge the same reports against the same floors, and `changes` computes the same outputs
**And** the workflow meta-tests pass

- **AC1 — The workflow meta-tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

- **AC2 — On the PR head, no cache entry is created on the PR ref and the gates pass.** Expected: no `pixi-` key on `refs/pull/<n>/merge`.

  ```bash
  gh cache list --repo rxm7706/local-recipes --ref refs/pull/<n>/merge --json key,sizeInBytes
  ```

</intent-contract>

## Evidence (2026-11-26)

`gh api repos/rxm7706/local-recipes/actions/cache/usage`: 41,737,411,252 bytes; limit 40 GB; 40 entries (14.90 GB) on `refs/pull/*`. Gate jobs 18 to 57 s each over eight PR heads. `changes` 17 s median. Detectors fetch 22.3 s median, 50.8 s at most.
