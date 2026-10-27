---
title: "117.10: Each station suite runs as N sharded jobs whose coverage the gate merges"
type: 'feature'
created: '2026-10-27'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # CI jobs, test tasks and a gate (spec-feature-flag-governance Q1; roster list)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - docs/dreams/pyforge-steward.md
  - docs/governance/ci-surfaces.yaml
  - .github/workflows/pyforge-station-tests.yml
  - scripts/coverage_gates_ci.py
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
---

<intent-contract>

## Intent

**Problem:** After Waves 1–2 the longest station jobs on a four-core runner are `herald-test` 341 s, `marshal-test` 276 s, `atlas-test` 257 s and `steward-live-test` 245 s, and a PR's wall is its longest job. A job's floor is ~25 s of set-up (checkout, a cached env); the repository is public, so runner minutes are free and 30–35 jobs start within five seconds of each other. Splitting a suite across jobs costs nothing that matters and is the only way under 90 s.

**Approach:** Each station job becomes a matrix of N shards that run `pytest --splits N --group K -n auto` (`pytest-split`, a conda-forge package, on a durations file under `tests/durations/<station>.json` that the nightly run regenerates), N sized so no shard works longer than ~45 s (steward-live 5, marshal 5, atlas 4–5, herald 2–3 after H.1, doctor-live 2). Each shard writes `.steward/coverage/<s>-<half>-<K>.json` and uploads it; the gate job downloads every shard's report and judges `coverage_gates_ci.py --report …` over all of them (`merge_coverage_reports` already merges N). The trigger map (Story 98.1) keys a matrix job once; the local preflight keeps running the unsharded task on one 16-core machine.

Ledger key: `117-10-each-station-suite-runs-as-sharded-jobs-whose-coverage-the-gate-merges`.
Type / Effort / Deps: feature / L / 117.4; 117.6 and 117.8 first in the build order.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175 (amended 2026-10-27, later)** — the preflight and a PR's CI answer within a measured budget; a station suite runs once, as its package-local and live-tree halves, each half as N sharded jobs whose coverage the gate merges; the `changes` step and the gate diffs read shallow fetches; the platform suite runs under xdist. The repository is public: runner minutes are free and the wall is the only cost. The amendment's measurements and decision are in the Spec's `.memlog.md` (2026-10-27, later).
- **`spec-pyforge-steward` CAP-159** (Epic 71) and **CAP-166** (the CI surfaces registry) — extended, not rewritten; **CAP-174** (the Platform CI budget), **`spec-pyforge-core:CAP-8`** (the shared-surface rule) and **`spec-coverage-gate-independence`** — kept as written.

## Acceptance Criteria

- **AC1 — Shards.** Each station job of `pyforge-station-tests.yml` with a suite over 45 s of work is a `strategy.matrix.group` of N shards; a shard runs `--splits N --group K` on the station's durations file and the halves' collected counts summed over the shards equal the unsharded counts (steward 1623 + 1446, doctor 1213 + 2676 at the baseline).
- **AC2 — One verdict.** The gate downloads every shard's coverage JSON and judges their merge; for every module touched on three recorded heads the verdict and the percent equal the unsharded report's.
- **AC3 — The mark.** On a four-core runner no station job's pytest step exceeds 45 s; a shared-surface PR's shard total stays under 30 jobs.
- **AC4 — Nothing exempt.** `test_station_tests_trigger_map.py` passes with each matrix job keyed once and `PRESERVED` intact; `test_preflight_selection.py` selects a shard set as its job; the preflight journals the unsharded task once per station.
- **AC5 — Durations.** `tests/durations/<station>.json` is written only by the nightly run (`ci-canary.yml` or `substrate-nightly.yml`) and read by the shards; a missing file falls back to `pytest-split`'s count-based split, never to a red.

## Boundaries & Constraints

**Always:**
- Read every verdict from an exit code, never through a pipe; keep `PYFORGE_PREFLIGHT_SKIP=1` the one journaled opt-out.
- Regenerate `environment.yaml` in the same PR as any `pixi.toml` edit; label the PR `maintenance`.

**Never:**
- Never skip a lane where CI's own rule would run it; never delete, skip or re-mark a test to meet a budget; never narrow a `*_paths` array by hand (Story 98.1, rulings 2026-10-12); never pause, disable or set `continue-on-error` on a lane; never hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-175 (amended 2026-10-27, later).

Parent: `spec-pyforge-steward` CAP-175

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-27, later (the wall is the lanes the waves did not touch) entry.
- Epic: Epic 117, amended with this story.
- Ledger key: `117-10-each-station-suite-runs-as-sharded-jobs-whose-coverage-the-gate-merges`.
- Deps: 117.4; 117.6 and 117.8 first in the build order.
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.
- Minted 2026-10-27 (later) in one chain commit (Wave 3 of the preflight and CI budget effort: Stories 117.10–117.12).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-steward pyforge-steward-live-test -- --splits 5 --group 1` (each K in 1..5) — expected: pass; the collected counts sum to the unsharded count.
- `gh api repos/rxm7706/local-recipes/actions/runs?head_sha=<sha>` on the first PR after landing — expected: no station job's pytest step over 45 s.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check`, `ci-surface-gates-check` — expected: exit 0 each.

## Auto Run Result

Status: backlog

Summary: not started.

## Spec Change Log

- 2026-10-27: minted from the station Dream's second Realization-log entry of 2026-10-27 (the wall is the lanes the waves did not touch) and the CAP-175 amendment of the same date.

## Review Triage Log

- (none yet)
