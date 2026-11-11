---
title: '124.2: Each split suite runs its live-tree half as its own CI job'
type: 'feature'
created: '2026-11-10'
status: 'backlog'
flag-exempt: detector-or-gate
difficulty: heavy
story: 124.2
spec: pyforge-steward
surface:
  - .github/workflows/pyforge-station-tests.yml
  - docs/governance/ci-surfaces.yaml
  - docs/governance/preflight-budgets.toml
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py
  - src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Without the job, Story 124.1's split would drop every `live_tree` test of eight suites from CI.

**Approach:** Story 117.4's design applied to the suites it left to their own chains. The workflow, the registry, the budgets and steward's trigger-map test move together; no test is removed, re-marked or skipped; no job is paused or made advisory.

Ledger key: `124-2-each-split-suite-runs-its-live-tree-half-as-its-own-ci-job`. Type / Effort / Deps: feature / L / S-120.5, S-121.1, S-121.2, S-121.3, S-121.6, S-121.7, S-122.2, S-122.3, S-123.1, S-123.2, S-123.3, S-124.1, S-124.4.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** (FR-49) — two CI jobs per suite; **CAP-166** — a registry row per job.

## Boundaries & Constraints

**Always:**
- Derive path arrays, never narrow them by hand (rulings of 2026-10-12).
- Keep the capability citations in its three test files current.

**Never:**
- Never pause a job or make one advisory.
- Never add a runner for warden's slow lane (DW-5-2-5 stands) or the durations files (DW-steward-cutover-2026-11-10-11).
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — a live job exists for every split suite.** Expected: exit 0; prints `[]`, with STATIONS="atlas herald marshal mason scribe warden core testing-kit" less any station Story 124.1 left unsplit.
  ```bash
  python3 -c "import yaml,sys;j=yaml.safe_load(open('.github/workflows/pyforge-station-tests.yml'))['jobs'];m=[s for s in sys.argv[1:] if f'{s}-live-test' not in j];print(m);raise SystemExit(bool(m))" doctor steward $STATIONS
  ```
- **AC2 — every read fires a job and no package half reads outside its package.** Expected: exit 0; no package half of a split suite fires on a steward source edit or on a planning-only edit (UNSPLIT_ON_A_STATION_SRC_EDIT and UNSPLIT_ON_A_PLANNING_EDIT are empty or hold only a station Story 124.1 left unsplit).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q
  ```
- **AC3 — doctor's renamed live modules are the declared handoffs.** Expected: prints 1 or more, and `test_root_handoffs_are_declared_exactly` and `test_the_handoff_floor` pass in the run above.
  ```bash
  grep -c 'tests/unit/test_live_' src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
  ```
- **AC4 — the capability ledger fires doctor's and steward's live halves.** Expected: prints 4 or more (both `on.*.paths` lists, doctor_live_paths, steward_live_paths).
  ```bash
  grep -c 'docs/foundry/capability-ledger.yaml' .github/workflows/pyforge-station-tests.yml
  ```
- **AC5 — scribe's live job has its database.** Expected: prints a service whose image is `pgvector/pgvector:pg17`.
  ```bash
  python3 -c "import yaml;j=yaml.safe_load(open('.github/workflows/pyforge-station-tests.yml'))['jobs']['scribe-live-test'];print(sorted(j.get('services',{}))[0], j['services'][sorted(j['services'])[0]]['image'])"
  ```
- **AC6 — the preflight selects the lanes CI runs.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py -q
  ```
- **AC7 — the registry matches the workflow.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild ci-surface-gates-check
  ```
- **AC8 — path filters agree.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py src/shared/packages/pyforge-steward/tests/meta/test_workflows_have_no_duplicate_keys.py -q
  ```
- **AC9 — budgets name the new lanes.** Expected: prints one line per split suite (8 when all land).
  ```bash
  grep -cE '"pyforge-(atlas|herald|marshal|mason|scribe|warden|core|testing-kit)-live-test@' docs/governance/preflight-budgets.toml
  ```
- **AC10 — the budget report runs.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild preflight-budget
  ```
- **AC11 — the aggregate runs both halves of every suite.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild pyforge-station-tests
  ```
- **AC12 — the coverage gates read both reports.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild pyforge-station-coverage-gates
  ```
- **AC13 — every station suite, both halves, through the aggregate the preflight lanes read.** Expected: exit 0 (the full preflight runs once, in doctor 58.4).
  ```bash
  pixi run --frozen -e pyforge-guild pyforge-station-tests && pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-175 (FR-49), CAP-166

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 124.
- Ledger key: `124-2-each-split-suite-runs-its-live-tree-half-as-its-own-ci-job` (`backlog` at mint).
- Deps: S-120.5, S-121.1, S-121.2, S-121.3, S-121.6, S-121.7, S-122.2, S-122.3, S-123.1, S-123.2, S-123.3, S-124.1, S-124.4.
- Surface: `.github/workflows/pyforge-station-tests.yml`, `docs/governance/ci-surfaces.yaml`, `docs/governance/preflight-budgets.toml` (a governance act: the first measured medians), `src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py`, `src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py`, `src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py`.
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `python3 -c "import yaml,sys;j=yaml.safe_load(open('.github/workflows/pyforge-station-tests.yml'))['jobs'];m=[s for s in sys.argv[1:] if f'{s}-live-test' not in j];print(m);raise SystemExit(bool(m))" doctor steward $STATIONS` — expected: exit 0; prints `[]`, with STATIONS="atlas herald marshal mason scribe warden core testing-kit" less any station Story 124.1 left unsplit.
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q` — expected: exit 0; no package half of a split suite fires on a steward source edit or on a planning-only edit (UNSPLIT_ON_A_STATION_SRC_EDIT and UNSPLIT_ON_A_PLANNING_EDIT are empty or hold only a station Story 124.1 left unsplit).

## Notes

- Cross-station deps: every story of this PR that owns a path under a station's tests/ (except 122.4, 124.3 and scribe 31.4, which follow it): warden:S-25.3, warden:S-26.1, warden:S-26.2, warden:S-26.3, warden:S-27.1, scribe:S-31.1, scribe:S-32.1, scribe:S-32.2, scribe:S-32.3, scribe:S-33.1, scribe:S-33.2, mason:S-37.3, mason:S-38.1, mason:S-38.2, mason:S-38.3, mason:S-39.1, atlas:S-47.1, atlas:S-47.2, atlas:S-48.1, atlas:S-48.2, atlas:S-48.3, herald:S-50.3, herald:S-51.1, herald:S-51.2, herald:S-52.1, herald:S-52.2, doctor:S-56.1, doctor:S-56.2, doctor:S-56.3, doctor:S-56.4, doctor:S-56.5, doctor:S-57.2, doctor:S-57.3, doctor:S-58.1, doctor:S-58.2, marshal:S-114.2, marshal:S-114.3, marshal:S-115.1, marshal:S-115.2, marshal:S-115.3, marshal:S-115.4, marshal:S-116.1, marshal:S-116.2, marshal:S-116.3, marshal:S-116.4, marshal:S-117.1, marshal:S-117.2, marshal:S-117.3, marshal:S-117.4, marshal:S-117.6, marshal:S-117.7, marshal:S-118.1.
- Red window, by design: from the first such story until this one lands, `test_every_read_and_declared_glob_fires_its_job` in steward's live half reds on the new reads; the integrator runs steward's live half after this story.
- Budget values for the new lanes are the first measured medians; changing preflight-budgets.toml is a governance act and this spec says so. scripts/coverage_gates_ci.py needs no edit.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (steward and host: Story 122.5) and doctor Story 58.4 runs every scoped stamp once, after the last edit.
