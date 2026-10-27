---
title: "117.2: A station's coverage floor is judged from its own suite's run, and coverage-gates.yml retires"
type: 'feature'
created: '2026-10-27'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a CI job, a test task or a preflight report (spec-feature-flag-governance Q1; roster list)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - docs/dreams/pyforge-steward.md
  - docs/governance/ci-surfaces.yaml
  - .github/workflows/pyforge-station-tests.yml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
---

<intent-contract>

## Intent

**Problem:** The coverage gate re-runs the suite it just watched: `scripts/coverage_gates_ci.py:_run_pytest_cov` starts a second pytest over `tests/unit tests/meta -m "not slow"` under `--cov`, in CI as its own workflow (1849 runner-s per PR) and locally as a lane that starts beside the suite lane. Story 71.4's suite reduction only lets the test lane skip what the gate ran, and not for atlas, doctor and mason, whose task cmds hold `&&`.

**Approach:** `scripts/station_suite_ci.py --station <s> --base <ref> --head HEAD` computes the gate segment and its complement with `preflight_suite_reduction._build_reduced_segments`, runs the gate segment through `_run_pytest_cov` (which writes the JSON), evaluates it with `_evaluate`, then runs the complement plain. `_parse_single_pytest` learns `&&` tasks. `coverage_gates_ci.py --report` evaluates an existing JSON. The pixi gate task depends on its suite task and reads `.steward/coverage/<s>.json`; the CI station jobs call the driver; `coverage-gates.yml` retires through the registry and `ci_surface_gates.py --render`.

Ledger key: `117-2-a-station-s-coverage-floor-is-judged-from-its-own-suite-s-run-and-coverage-gates-yml-retires`.
Type / Effort / Deps: feature / M / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; this story is one of its eight parts (Epic 117). Operator rulings D1–D4 of 2026-10-27 in the Spec's `.memlog.md`.
- **`spec-pyforge-steward` CAP-159** (Epic 71: the preflight's journal, CI-rule lane selection, concurrency, coverage reuse, xdist for the then-large suites) and **CAP-166** (the CI surfaces registry, its switches and render) — extended, not rewritten.
- **`spec-pyforge-steward` CAP-174**, **`spec-pyforge-core` CAP-8** (the shared-surface rule) and **`spec-coverage-gate-independence`** — kept as written.

## Acceptance Criteria

- **AC1 — One run.** On a PR touching one station, that station's unit+meta tests are collected exactly once across the head's jobs (`gh api …/jobs` step logs show one pytest run of `tests/unit tests/meta`).
- **AC2 — Same verdict.** `coverage_gates_ci.py --report` over the driver's JSON returns the same pass/fail and the same measured percentage (±0.1) as the two-run gate at the baseline commit, for every station with a non-trivial floor.
- **AC3 — Retired.** `docs/governance/ci-surfaces.yaml` carries `coverage-gates` with `state: retired`; `python scripts/ci_surface_gates.py --check` exits 0; the workflow file is removed or disabled by the render; `PAUSE_COVERAGE_GATES` is deleted from the repo variables (operator step, journaled).
- **AC4 — Locally too.** A touched-scope preflight on a steward-only diff journals one suite lane and a gate lane under 10 s that `depends_on` it.
- **AC5 — `&&` tasks.** `preflight_suite_reduction._parse_single_pytest` returns the segments of the atlas, doctor and mason tasks; `test_preflight_suite_reduction.py` covers them.

## Boundaries & Constraints

**Always:**
- Read every verdict from an exit code, never through a pipe; keep `PYFORGE_PREFLIGHT_SKIP=1` the one journaled opt-out.
- Regenerate `environment.yaml` in the same PR as any `pixi.toml` edit; label the PR `maintenance`.

**Never:**
- Never skip a lane where CI's own rule would run it; never delete, skip or re-mark a test to meet a budget; never narrow a `*_paths` array by hand (Story 98.1, rulings 2026-10-12); never pause, disable or set `continue-on-error` on a lane; never hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-175.

Parent: `spec-pyforge-steward` CAP-175

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-27 (the preflight answers in eleven minutes, a PR's CI in thirteen) entry.
- Epic: Epic 117, minted with this story.
- Ledger key: `117-2-a-station-s-coverage-floor-is-judged-from-its-own-suite-s-run-and-coverage-gates-yml-retires`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.
- Minted 2026-10-27 in one chain commit (the preflight and CI budget effort: steward Epic 117; doctor, herald, mason, atlas, scribe and warden chains follow).

## Verification

**Commands:**
- `pixi run -e pyforge-steward python scripts/station_suite_ci.py --station steward --base origin/main --head HEAD` — expected: exit 0; one pytest run under `--cov`, one plain.
- `python scripts/ci_surface_gates.py --check` — expected: exit 0 with the `coverage-gates` row `retired`.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (suite-reduction unit tests included).

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: backlog

Summary: not started.

## Spec Change Log

- 2026-10-27: minted from the station Dream's entry of 2026-10-27 and the operator's rulings D1–D4 of the same date.

## Review Triage Log

- (none yet)
