---
title: "117.12: The platform suite runs under xdist, its checks in a parallel job"
type: 'feature'
created: '2026-10-27'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a CI job and a test task (spec-feature-flag-governance Q1; roster list)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - docs/dreams/pyforge-steward.md
  - docs/governance/ci-surfaces.yaml
  - .github/workflows/pyforge-station-tests.yml
  - .github/workflows/platform-ci.yml
  - src/platform/pyproject.toml
---

<intent-contract>

## Intent

**Problem:** Platform CI's `test` job takes 340–350 s on every shared-surface PR: a serial 226 s pytest-django suite, 35 s of policy tests, 26 s of service start-up, 16 s of installs, 13 s of Chromium and 12 s of mypy, in one job. Once the image jobs leave the PR path (117.6) it is Platform CI's wall.

**Approach:** The suite runs under xdist on the runner's four cores (`pytest -n 4 --dist loadgroup`; pytest-django gives each worker its own test database; tests that share a fixture database carry `xdist_group`); ruff, `ruff format --check`, mypy, `manage.py check` and the policy suite move to a `checks` job that runs beside it. `pytest-xdist` joins the `platform-ci-test` feature; `scripts/platform-ci-local.sh` mirrors both jobs; the `platform-ci.checks` row is declared in `ci-surfaces.yaml`. CAP-174's budget on `platform-ci.test` stays.

Ledger key: `117-12-the-platform-suite-runs-under-xdist-with-its-checks-in-a-parallel-job`.
Type / Effort / Deps: feature / M / 117.6.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175 (amended 2026-10-27, later)** — the preflight and a PR's CI answer within a measured budget; a station suite runs once, as its package-local and live-tree halves, each half as N sharded jobs whose coverage the gate merges; the `changes` step and the gate diffs read shallow fetches; the platform suite runs under xdist. The repository is public: runner minutes are free and the wall is the only cost. The amendment's measurements and decision are in the Spec's `.memlog.md` (2026-10-27, later).
- **`spec-pyforge-steward` CAP-159** (Epic 71) and **CAP-166** (the CI surfaces registry) — extended, not rewritten; **CAP-174** (the Platform CI budget), **`spec-pyforge-core:CAP-8`** (the shared-surface rule) and **`spec-coverage-gate-independence`** — kept as written.

- **`spec-pyforge-steward` CAP-174** — the Platform CI test job's budget and its browser install; the budget row stays and the browser step stays in `test`.

## Acceptance Criteria

- **AC1 — Parallel.** `test` runs the suite under `-n 4` with the same collected count and the same verdicts; its pytest step is ≤ 90 s and the job ≤ 150 s on a four-core runner.
- **AC2 — Checks beside it.** A `checks` job runs ruff, `ruff format --check`, mypy, `manage.py check` and the policy suite in ≤ 90 s; neither job waits for the other.
- **AC3 — The twin.** `pixi run -e pyforge-guild platform-ci-local -- --test` runs both jobs' steps and reads the same verdicts.
- **AC4 — Declared.** `docs/governance/ci-surfaces.yaml` carries `platform-ci.checks`; `ci_surface_gates.py --check` and the steward platform-CI meta tests exit 0; `environment.yaml` is regenerated with the `pixi.toml` edit.

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
- Ledger key: `117-12-the-platform-suite-runs-under-xdist-with-its-checks-in-a-parallel-job`.
- Deps: 117.6.
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.
- Minted 2026-10-27 (later) in one chain commit (Wave 3 of the preflight and CI budget effort: Stories 117.10–117.12).

## Verification

**Commands:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0 with the same collected count as before.
- `pixi run --frozen -e pyforge-guild ci-surface-gates-check` — expected: exit 0.
- `gh api repos/rxm7706/local-recipes/actions/runs/<id>/jobs` on the first shared-surface PR after landing — expected: `test` ≤ 150 s, `checks` ≤ 90 s.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: built in the Wave 3 PR (2026-10-27). `platform-ci.yml`: the `test` job runs `python -m pytest -v -n 4 --dist loadgroup` alone; the new `checks` job (same services and slim env, no browser) runs the Django system checks, ruff, `ruff format --check`, mypy, the policy suite and the sqlmigrate extraction beside it; `pytest-xdist` joins the `platform-ci-test` feature (`pixi.lock` moved); `scripts/platform-ci-local.sh --test` mirrors both jobs' steps and runs the full suite under `-n 4 --dist loadgroup`; registry row `platform-ci.checks`. Measured locally through `platform-ci-local --test`: the policy suite 98 passed in 9 s, the full suite 1,355 passed and 14 skipped in 83 s under four workers (226 s serial in CI before); `ci_surface_gates.py --check` exit 0. The CI job's seconds: see the Spec Change Log after the PR's run.

## Spec Change Log

- 2026-10-27 (measured, PR #2335 head 336e1ccb1c (a shared-surface PR: `pixi.lock` moved, so every lane ran)): the `test` job 198 s (the suite 121 s under `-n 4`; 347 s with the serial 226 s suite on PR #2332's head), the `checks` job 112 s beside it (policy suite 25 s, mypy, ruff, system checks); Platform CI's wall 203 s.
- 2026-10-27: minted from the station Dream's second Realization-log entry of 2026-10-27 (the wall is the lanes the waves did not touch) and the CAP-175 amendment of the same date.

## Review Triage Log

- (none yet)
