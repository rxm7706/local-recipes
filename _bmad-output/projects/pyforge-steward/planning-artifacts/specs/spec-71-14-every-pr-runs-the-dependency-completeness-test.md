---
title: "71.14: Every PR runs the dependency-completeness test, locally and in CI"
type: 'fix'
created: '2026-10-25'
status: 'in-review'
baseline_revision: '529f06d52b6d6469b847519905c20bf528a60334'
flag-exempt: detector-or-gate   # a fix needs no flag (spec-feature-flag-governance Q1), and pr-preflight is a gate, as 71.12 and 71.13 recorded
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/retros/retro-pyforge-atlas-2026-10-25.md
  - pixi.toml
  - .github/workflows/detectors.yml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-doctor/tests/meta/test_preflight_mirrors_scripts_suite.py
  - tests/packaging/test_dependency_completeness.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the test that catches an undeclared import runs on no PR. Line numbers are at `529f06d52b`.

- `tests/packaging/test_dependency_completeness.py` (task `pyforge-deps-test`, `pixi.toml:843`-`:845`, `-e pyforge-ci`,
  about 4 s) checks that every module-level import of each `pyforge-*` package is declared in both manifests. Atlas
  Story 37.7 (#2294) imported `numpy` without declaring it, and `main` stayed red on this test until #2307
  (`DW-atlas-retro-2026-10-15-4`, third recurrence; the 2026-10-25 atlas retro's Finding 2, candidate fix 1).
- `pr-preflight-lanes` (`pixi.toml:1668`, `depends-on` at `:1680`) has 37 lanes and none runs it, and no workflow under
  `.github/workflows/` names it. Only marshal's `verify_commands` does, which a hand-landed branch never reads.
- Under the touched scope (the dev default), `preflight_ci.touch_verdict` (`:1689`-`:1713`) keeps a lane only for its
  station package, a path its command names, or (lint and types) Python under `src/`. `pyforge-ci` maps to no station
  package and the command names only `tests/packaging`, so a new leg would be deferred for an atlas-only diff.

**Approach:**
- Add `{ task = "pyforge-deps-test", environment = "pyforge-ci" }` to `pr-preflight-lanes` with a "Fourteenth leg" note,
  and the same task as a step of the Detectors `scripts-suite` job (`detectors.yml:78`-`:116`, `on: pull_request`
  with no paths, `pyforge-ci` already installed). Doctor's `test_preflight_mirrors_scripts_suite.py` reds a step with no
  leg, so both land together.
- `touch_verdict` keeps a lane whose task is `pyforge-deps-test` when a path `tests/packaging` reads changed: a
  `pyforge-*` package's `pyproject.toml` or `pixi.toml`, a Python file under its `src/`, the root `pixi.toml` (three
  of the eight files read it) or a root `Containerfile*` (two read those).
- A `fix` under CAP-159: no CAP, no flag. No new job, workflow or ci-surfaces row; the task does not change.

Ledger key: `71-14-every-pr-runs-the-dependency-completeness-test`. Type / Effort / Deps: fix / S / —.

## Acceptance Criteria

- **AC1 — The leg.** `pixi run -e pyforge-guild pr-preflight-lanes`' `depends-on` includes the task in `pyforge-ci`;
  `list_preflight_lanes` lists it; `test_pr_preflight_lanes_resolve_under_pixi.py` passes.
- **AC2 — The CI step.** The Detectors `scripts-suite` job runs `pixi run --frozen -e pyforge-ci pyforge-deps-test`;
  doctor's `test_preflight_mirrors_scripts_suite.py` passes, and fails with the step and no leg.
- **AC3 — The touched scope.** `touch_verdict` keeps the lane for a diff that changes
  `src/shared/packages/pyforge-atlas/pyproject.toml`, a package `pixi.toml`, a `.py` under a package's `src/`, the root
  `pixi.toml` or a root `Containerfile*`; it defers the lane for a diff with none of those (a doc, a test outside
  `src/`, another package's README, a nested Containerfile). Unit tests pin each case and fail when the rule is removed.
- **AC4 — Nothing else moves.** Other lanes' verdicts are unchanged; `pixi run --frozen -e pyforge-steward
  pyforge-steward-test` passes; `environment.yaml` does not change (`pyforge steward estate reconcile`), and
  `docs/how-to/pixi-tasks.md`, generated from `pixi.toml`, is regenerated.

## Boundaries & Constraints

**Never:** add a job, a workflow or a ci-surfaces row; change `pyforge-deps-test` itself; change any other lane's
touch rule.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-159. No CAP is minted.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, 2026-10-25 (the dependency-completeness test runs on no PR).
- Epic 71 (done; reopened by this story under doctor Story 41.5's rule). Ledger key above. Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the mirror meta-test, AC2).
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from a file (on a
  host whose `/tmp` is tmpfs, with `TMPDIR` on the repository's filesystem), the new lane among those run.

## Spec Change Log

- 2026-10-25: drafted from the Dream entry of 2026-10-25 and the 2026-10-25 atlas retro's candidate fix 1, at the
  operator's direction "want those steward ones done here too".
- 2026-10-25: review round 1: the touch rule widened to every path `tests/packaging` reads (the root `pixi.toml` and
  root `Containerfile*` join; AC3 updated: the root `pixi.toml` now keeps the lane), and AC4 names the regenerated
  `pixi-tasks.md`. Implemented in its own green commit (the selection oracle moved with the lane). Moved to `in-review`.

## Run results

2026-10-25, after the round-1 fixes:
- `list_preflight_lanes` over the real `pixi.toml`: 38 lanes, `pyforge-deps-test@pyforge-ci` among them (AC1).
- `test_pr_preflight_lanes_resolve_under_pixi.py` 10 passed; doctor's `test_preflight_mirrors_scripts_suite.py` 5
  passed (AC2).
- `test_preflight_scope.py` and `test_preflight_selection.py` pass; with the rule disabled, the kept cases fail (AC3).
- `pyforge steward estate reconcile`: `environment.yaml` unchanged; `docs-pixi-tasks -- --check` current (AC4). Its
  other rewrites (stamp churn on `docs/map.yaml` and `docs/reference/environments.md`, its journal, a doctor memlog line
  and the unifying-strategy Dream's env matrix) were not this story's and were left out.
- `pixi run -e pyforge-guild lint-types`: exit 0.

## Review Triage Log

**Review 1 (independent, 2026-10-25): PASS** with should-fixes; all fixed.
- should-fix: `docs/how-to/pixi-tasks.md` stale after the `pixi.toml` edit. Regenerated.
- should-fix: the 71.14 commit was red alone (the selection oracle gained the lane only in the 99.8 commit). The branch
  was rebuilt so 71.14's commit carries its oracle and formatting.
- should-fix: the touch rule modelled one of the eight files the task runs. Widened (root `pixi.toml`, root
  `Containerfile*`).
- nit: the Detectors step was named for one test; renamed `tests/packaging (pyforge-deps-test)`.
