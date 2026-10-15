---
title: '104.1: cfe-regression-net runs when a script its tests load changes'
type: 'fix'
created: '2026-10-14'
status: 'done'
baseline_revision: '22e5c19c285e722bcf7d58203689d57e9cc4dd55'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-98-1-station-tests-run-when-what-they-read-changes.md
  - docs/dreams/pyforge-steward.md
  - .github/workflows/cfe-regression-net.yml
  - docs/governance/ci-surfaces.yaml
  - .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `.github/workflows/cfe-regression-net.yml` runs the conda-forge-expert regression suite (`pixi run --frozen
-e local-recipes test-ci`) only when a PR or a push to `main` touches `.claude/skills/conda-forge-expert/**`,
`.claude/scripts/conda-forge-expert/**`, `.claude/tools/conda_forge_server.py`, `pixi.toml`, `pixi.lock` or the
workflow itself. The suite's meta tests also load five repo-root scripts by path, each as
`REPO_ROOT / "scripts" / "<name>.py"`:

| Script | Loaded by (2026-10-14) |
|---|---|
| `scripts/fleet_picture.py` | ten `test_fleet_picture_*.py` files |
| `scripts/fleet_scan.py` | `test_dashboard_resolve_project.py`, `test_dashboard_scan_timing_wall_clock.py` |
| `scripts/loop_stall_check.py` | `test_loop_stall_check_awaiting_operator.py` |
| `scripts/spec_surface_check.py` | `test_spec_surface_check.py` |
| `scripts/unpushed_work_check.py` | `test_unpushed_work_check.py` |

Doctor Story 45.1 (merge `7c6dac8c07`, 2026-10-14) added a probe to `scripts/fleet_picture.py` that
`test_fleet_picture_main_attention.py` did not stub; three tests went red, and the lane stayed silent until steward
Story 102.1 touched `pixi.toml` (PR #2220). Mason Story 31.1 fixed the tests (CFE v8.100.4) and recorded this gap.

**Approach:** list the five scripts in both of the workflow's `paths:` filters, and add a steward meta test that derives
the list from the CFE tests' own source and fails when a filter misses one — the shape of Story 98.1
(`test_station_tests_trigger_map.py`), narrowed to repo-root scripts loaded by path. pr-preflight reads the same filters
(Story 71.2), so its lane selection follows with no other change.

### Living CAP citations

- **Parent.** A fix under `spec-pyforge-steward` CAP-159 (pr-preflight and CI run the lanes the workflow files select),
  in the shape of Story 98.1; no CAP, no FR, no flag (`spec-feature-flag-governance` Q1).
- **Owner.** `docs/governance/ci-surfaces.yaml` rows `cfe-regression-net` and `cfe-regression-net.cfe-regression-net`
  (owner `pyforge-steward`); unchanged.
- **Kinship.** `pyforge-doctor:CAP-89` (Story 45.1, the change that went unseen); `spec-pyforge-mason` CAP-23 (Story
  31.1, the CFE meta suite stays green).
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-14 (the CFE regression lane runs when what its
  tests load changes); the operator's ask in session.

## Acceptance Criteria

- **AC1 — The filters list the scripts.** Both `on.pull_request.paths` and `on.push.paths` of
  `.github/workflows/cfe-regression-net.yml` match `scripts/fleet_picture.py`, `scripts/fleet_scan.py`,
  `scripts/loop_stall_check.py`, `scripts/spec_surface_check.py` and `scripts/unpushed_work_check.py`
  (`PurePosixPath.full_match`).
- **AC2 — The list is derived, not kept by hand.** `tests/meta/test_cfe_regression_net_paths.py` parses every `.py`
  under `.claude/skills/conda-forge-expert/tests/`, finds module-level names bound to
  `Path(__file__).resolve().parents[N]` that resolve to the repository root, collects each `NAME / "scripts" / ...` join
  that names an existing repo-root file, and asserts both filters cover each.
- **AC3 — Not blind.** The derivation finds at least the five scripts of AC1.
- **AC4 — It fails when it should.** Dropping `scripts/fleet_picture.py` from either filter fails the test, naming the
  trigger and the path (run 2026-10-14 against a scratch copy of the workflow: `1 failed, 2 passed`).
- **AC5 — Nothing else moves.** `test_station_tests_trigger_map.py`, `test_preflight_selection.py` and
  `scripts/ci_surface_gates.py` exit 0; the registry rows and the job's `if:` gates are unchanged.

## Boundaries & Constraints

- Only repo-root `scripts/` files loaded by path. Data the tests read (`recipes/**`, `conda_build_config.yaml`,
  `.ci_support/*.yaml`, `docs/dashboard/index.html`) stays out: a filter on `recipes/**` would run the lane on every
  recipe PR. Station packages the tests import are installed into the lane's environment and judged by their own suites.
- No file under `.claude/skills/conda-forge-expert/` changes, so no `retro(cfe):` commit is needed.

## I/O & Edge-Case Matrix

| Change in a PR | Lane runs? |
|---|---|
| `scripts/fleet_picture.py` | yes (new) |
| `scripts/spec_surface_check.py` | yes (new) |
| `.claude/skills/conda-forge-expert/SKILL.md` | yes (as before) |
| `recipes/ironcalc/recipe.yaml` | no (data, by design) |
| a new CFE meta test loading `REPO_ROOT / "scripts" / "x.py"` without a filter line | the steward meta test fails until `scripts/x.py` is added |

## Binding

- Parent Spec capability: a fix under `spec-pyforge-steward` CAP-159; no CAP minted; no `SPEC.md` change.
- Dream: `docs/dreams/pyforge-steward.md` § Realization log, the 2026-10-14 (the CFE regression lane runs when what its
  tests load changes) entry.
- Epic: Epic 104 (new), Story 104.1. `epic-104` and `epic-104-retrospective` are minted with it.
- Ledger key: `104-1-cfe-regression-net-runs-when-a-script-its-tests-load-changes`.
- Ledger status at mint: `done` (specced and fixed in the same change, as herald 44.1 and mason 31.1 were).
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."104"`.
- Flag: none — a fix (`spec-feature-flag-governance` Q1).

## Epic excerpt

Story 104.1 in `epics.md` § Epic 104: the CFE regression lane runs when what its tests load changes.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/meta/test_cfe_regression_net_paths.py -q` — expected: 3 passed.
- AC4's mutation against a scratch copy of the workflow — expected: `1 failed, 2 passed`; restore it.
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py -q` — expected: exit 0 (118 passed on 2026-10-14).
- `pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0.

## Named, not fixed here

- Whether `cfe-regression-net` should also fire on the station packages its tests import (`pyforge.doctor`), as Story
  98.1's map does for station suites. Today those changes run their own station suites; the CFE meta tests that import
  them are a small set.

## Spec Change Log

- 2026-10-14: specced and fixed in the same change, at the operator's ask in session (raised as a follow-up by mason
  Story 31.1).

</intent-contract>

## Auto Run Result

Status: done

**Files changed:**
- `.github/workflows/cfe-regression-net.yml` — both `paths:` filters list the five repo-root scripts the CFE meta tests load
- `src/shared/packages/pyforge-steward/tests/meta/test_cfe_regression_net_paths.py` — new: derives the loaded scripts from the tests' AST and asserts both filters cover them
