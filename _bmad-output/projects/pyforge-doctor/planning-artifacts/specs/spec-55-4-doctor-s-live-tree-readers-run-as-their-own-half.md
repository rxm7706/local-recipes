---
title: "55.4: Doctor's live-tree readers run as their own half"
type: 'feature'
created: '2026-10-27'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a CI job and a test task (spec-feature-flag-governance Q1; roster list)
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py
  - scripts/chain_currency_sweep_check.py
  - pixi.toml
---

<intent-contract>

## Intent

**Problem:** Doctor is the station whose suite fans out most: `doctor_paths` lists `src`, `scripts`, `_bmad`, `archive`, `docs/dreams`, `docs/governance`, the planning globs and `.claude/skills` because a few dozen of its tests read them, yet the whole 3881-test suite runs each time (PRs #2323–#2327 all ran it).

**Approach:** Under Story 117.4's convention (a `tests/live/` directory or a `live_tree` marker — one for all stations), doctor moves its readers: the 19 `ROOT_HANDOFF_INPUTS["doctor"]` files, `tests/meta/**`, `unit/test_checks_env_hygiene.py`, `unit/test_hygiene_definitions.py`, `unit/test_capability_ledger.py`, `unit/test_fleet_scan_*.py` and whatever the derivation still finds outside the package. Two pixi tasks, two jobs; steward's trigger map proves the split.

Ledger key: `55-4-doctor-s-live-tree-readers-run-as-their-own-half`.
Type / Effort / Deps: feature / M / steward Story 117.4 (the two-halves convention, the trigger map keyed by job, the workflow shape).

### Living CAP citations

- **spec-pyforge-steward:CAP-175 (relay: each station suite runs as its package-local and live-tree halves; operator ruling D4 of 2026-10-27) — no doctor CAP.**
- **`spec-pyforge-steward:CAP-175`** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; doctor's part of its fleet, measured and ruled 2026-10-27 (D1–D4 in that Spec's `.memlog.md`).
- **`spec-pyforge-doctor` AD-1, AD-2, AD-5** — a Doctor source is a library call; the exit-code space is closed; `run_git` is the one subprocess site.

## Acceptance Criteria

- **AC1 — Two halves.** `pyforge-doctor-test` and `pyforge-doctor-live-test` together collect the baseline's count; the speed-budget alone-run rides the half that collects its module (the live half: `test_check_speed_budget.py` reads the live tree).
- **AC2 — Empty outside reads.** `test_station_tests_trigger_map.py` derives no outside read for the doctor package job and today's set for the live job.
- **AC3 — Fan-out.** The `changes` script on a one-file fixture diff under `_bmad-output/projects/pyforge-marshal/planning-artifacts/` sets `doctor_live=true` and `doctor=false`; under `src/shared/packages/pyforge-doctor/src/` both are `true` (steward's trigger map asserts both fixtures).
- **AC4 — CI.** On a planning-only PR the `doctor-test` job reads `skipped` and `doctor-live-test` passes in ≤ 120 s.

## Boundaries & Constraints

**Always:**
- Keep every finding's shape and verdict; read every verdict from an exit code, never through a pipe.
- Keep `run_git` the one subprocess site for `git grep`; keep the exit-code space `{0, 2, 130}`.

**Never:**
- Never delete, skip or re-mark a test to meet a time; never narrow `doctor_paths` by hand (Story 98.1, rulings 2026-10-12); never hand-edit `SPEC.md`; never reimplement a Doctor source as a subprocess.

</intent-contract>

## Binding

- Parent capability: spec-pyforge-steward:CAP-175.

Parent: spec-pyforge-steward:CAP-175

- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-27 (the repo-scope detectors and the doctor suite answer in seconds) entry.
- Epic: Epic 55, minted with this story.
- Ledger key: `55-4-doctor-s-live-tree-readers-run-as-their-own-half`.
- Deps: steward Story 117.4 (the two-halves convention, the trigger map keyed by job, the workflow shape).
- Surface: `marshal-policy.toml` `[epic_surfaces]."55"`.
- Minted 2026-10-27 in one chain commit beside steward Epic 117 (the preflight and CI budget effort).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` and `pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test` — expected: pass; counts sum to the baseline.
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q` — expected: pass.

**Run before the push:**
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: built in the Wave 2 PR (2026-10-27) beside steward Story 117.4, under its `live_tree` marker convention. 43 doctor modules carry `pytestmark = pytest.mark.live_tree` (the 19 `ROOT_HANDOFF_INPUTS["doctor"]` gatherer files, `tests/meta/**`, `test_checks_env_hygiene.py`, `test_check_speed_budget.py` and every other module the trigger map derived an outside read for); the marker is registered in `pyforge-doctor/pyproject.toml`. `pyforge-doctor-test` collects `-m "not slow and not live_tree"` (1213 tests, 12 s on 16 workers, writes `.steward/coverage/doctor-unit.json`); `pyforge-doctor-live-test` collects `-m "live_tree and not slow"` with the speed-budget module set aside and run alone afterwards (2676 tests, 47 s, writes `doctor-live.json`); together 3889, the old task's collection. The gate (`pyforge-doctor-coverage-gate`, the `doctor-gate` CI job) judges the two reports merged. Workflow: `doctor` fires on `src/shared/packages/pyforge-doctor` and the shared surface, `doctor_live` on the old `doctor_paths` (now `doctor_live_paths`); `doctor-live-test` and `doctor-gate` jobs added; `ci-surfaces.yaml` rows `pyforge-station-tests.doctor-live-test` / `doctor-gate`. Steward's `test_station_tests_trigger_map.py` derives the doctor package half's outside reads as empty and asserts it. AC4 (the planning-only PR runs `doctor-live-test` ≤ 120 s, `doctor-test` skipped) reads from the first planning-only PR after this lands.

## Spec Change Log

- 2026-10-27: minted from the station Dream's entry of 2026-10-27 beside steward Epic 117 (spec-pyforge-steward:CAP-175).
- 2026-10-27: AC1's set-aside speed-budget run moved with its module into the live half (the test reads the live tree, so the marker puts it there; the package half has no set-aside run). `scripts/coverage_gates_ci.py`'s mirror of the set-aside run is now tested against steward's `test_preflight_concurrency.py`.

## Review Triage Log

- (none yet)
