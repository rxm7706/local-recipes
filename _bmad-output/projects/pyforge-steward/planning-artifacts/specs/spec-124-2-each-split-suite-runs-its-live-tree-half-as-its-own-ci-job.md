---
title: '124.2: Each split suite runs its live-tree half as its own CI job'
type: 'feature'
created: '2026-11-10'
status: 'done'
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
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_ci.py
  - src/shared/packages/pyforge-herald/tests/meta/test_preflight_pages_lane.py
  - src/shared/packages/pyforge-herald/tests/meta/test_built_site_tests_install_first.py
  - src/shared/packages/pyforge-core/tests/meta/test_conformance_lane_wired.py
  - src/shared/packages/pyforge-testing-kit/tests/meta/test_testing_kit_lane_wired.py
  - src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_writer_lock.py
  - src/shared/packages/pyforge-mason/tests/meta/test_adapter_sole_caller.py
  - src/shared/packages/pyforge-mason/tests/unit/test_errors.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_compile.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_extras_graphify.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_recall.py
  - src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger.py
  - src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py
  - src/shared/packages/pyforge-steward/tests/meta/test_portability.py
  - src/shared/packages/pyforge-steward/tests/unit/test_suite_advance.py
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

## Integrator note (2026-11-11, from Story 124.1's build)

Story 124.1's build found work that lands here; the integrator assigns it to this story.

- Each split station's CI gate step carries, verbatim and after its unit report, the string its `pixi.toml` gate
  `cmd` carries: `--report ".steward/coverage/<s>-live*.json"` for atlas, herald, marshal, mason, scribe and
  warden. Until then the preflight refuses with exit 2 on a stranded gate.
- Core and the kit use the aggregate shape (Story 124.1's § Integrator ruling): the `core-test` and
  `testing-kit-test` jobs run `pyforge-core-package-test` and `pyforge-testing-kit-package-test`, and the
  `core-live-test` and `testing-kit-live-test` jobs run the `-live-test` tasks. Core's `lane_halves_problems` and
  the kit's lane guard accept that wiring; their split-copy helpers switch to the real split once it lands.
- The `herald-live-test` job runs the built-site tests: it sets up the `site` environment, runs
  `docs-site-install` first and sets `HERALD_DOCS_SITE_REQUIRED=1`, as the herald job does today.
- Files added to this story: steward's `src/pyforge/steward/preflight.py` and `tests/unit/test_preflight_ci.py`,
  herald's `tests/meta/test_preflight_pages_lane.py` and `tests/meta/test_built_site_tests_install_first.py` (its CI
  pin), core's `tests/meta/test_conformance_lane_wired.py` and the kit's `tests/meta/test_testing_kit_lane_wired.py`.
  After this story, re-run steward's `test_preflight_ci.py` and `test_preflight_selection.py` and herald's
  `test_preflight_pages_lane.py`; Story 124.1's red window closes here.

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first attempt. Each finding, then what this round did.

1. **Blocker: AC2 red, 5 failed and 54 passed.** In `tests/meta/test_station_tests_trigger_map.py`,
   `test_the_package_half_reads_nothing_outside_its_package[doctor|mason|scribe|steward]` and
   `test_every_read_and_declared_glob_fires_its_job` fail. Every failing read comes from a package-half module
   outside this story's files: doctor `tests/unit/test_sources_writer_lock.py` (56.5); mason
   `tests/meta/test_adapter_sole_caller.py` and `tests/unit/test_errors.py`, which use only the
   `.claude/scripts/conda-forge-expert` literal (38.2); scribe `tests/unit/conftest.py`, `test_compile.py`,
   `test_recall.py` and `test_extras_graphify.py` (33.1); steward `tests/unit/test_cutover_ledger.py` and
   `tests/unit/test_cutover_ledger_check.py` (121.6), and `tests/meta/test_portability.py` (123.2). Only package
   halves misfire (doctor 5, mason 2, scribe 26, steward 23). No live-half array misfires.
   *Response:* confirmed on re-run, with the same five failures. The fix belongs to each module's owner, who marks
   the module `pytest.mark.live_tree` or drops the literal. The integrator assigns them. This story cannot edit
   those files. A scratch simulation marked every named module and re-ran the derivation. Two problems remain
   after that:
   - Scribe's `tests/unit/conftest.py` cannot be cleared by a marker. Its fixture reads (`pixi.toml`,
     `src/platform/db/changelog/changes/pyforge-scribe-*.sql`) reach every package-half test that uses the fixture.
     Scribe's owner has to move the reads into a live-tree module or a fixture only live modules use.
   - `test_portability.py`, once marked, reads `docs/MAP.md`, and `steward_live_paths` did not list it. This round
     adds `docs/MAP.md` to `steward_live_paths` ahead of its reader. The 2026-10-12 rulings allow an array to name
     a path before its reader exists. With that entry, marking the steward modules leaves no live-half misfire.
   AC2 stays red until the owners land these fixes.
2. **Blocker: AC11, AC12 and AC13 red.** The causes are outside this story's files:
   - Scribe's live half stops at `test_spec_not_behind_memlog`: `spec-pyforge-steward` is behind its memlog until
     Story 122.5 re-derives it.
   - The steward package half fails on the five AC2 reads above.
   - The steward live half fails on
     `test_capability_ledger_live::test_the_ledger_has_no_finding_but_the_exemption` (Stories 121.7 and 122.5).
   - The steward coverage gate fails on `pyforge.steward.suite_advance` at 57.4%, a module only Story 122.3 touched.

   *Response:* this story's files are unchanged for these causes. The criteria are re-run below and reported with
   their causes.
3. **Major: the guard that every package half now relies on did not run on the PRs it exists to catch.**
   `real_derivation` assigned this meta-test's own reads to `steward_live`, but the module carried no `live_tree`
   mark. So it ran only in `steward-test`, which fires on steward's package and the shared surface alone. A station
   PR that added an outside read to its package half fired `steward-live-test`, which did not run the guard.
   *Response:* fixed. The module now carries `pytestmark = pytest.mark.live_tree`, so `pyforge-steward-live-test`
   runs it, both locally and in the `steward-live-test` job. That job's `steward_live_paths` lists
   `src/shared/packages/pyforge-*/tests/*`, so the self-attribution now holds. Per the live_tree rule, the
   import-time `REPO_ROOT`, `WORKFLOW`, `THIS_FILE_REL` and `PIXI_TOML` are now functions: `repo_root()`,
   `workflow_file()`, `this_file_rel()` and `pixi_toml_file()`. The comment in `real_derivation` now names
   `steward-live-test`. On the Approach line "no test is removed, re-marked or skipped": that clause protects the
   split suites' coverage, so that no station test leaves CI to make the split pass. This module is this story's own
   guard. The marker moves it to the half whose trigger list holds what it reads, so it runs on more PRs, not
   fewer. Nothing is deselected. Collection checks confirm it: with `-m "not slow and not live_tree"` the module
   collects 0 of 59 tests, and with `-m "live_tree and not slow"` it collects all 59. The integrator may overrule
   this reading.
4. **Minor: AC10 exits 2 with "no valid run in journal".** The worktree has no `.steward/preflight-runs.jsonl`.
   The budgets file parses: `load_budget_config` reads it before the journal.
   *Response:* nothing to change here. The criterion is re-run after doctor Story 58.4's full preflight writes the
   journal.
5. **Minor: this story's job moves left text stale outside its files.**
   - `docs/how-to/recipe-testing-and-builds.md:21` and the `pixi.toml` description of
     `pyforge-mason-recipe-build-smoke` (line 571) still put the smoke in mason-test. It now runs in mason-live-test.
   - The `pixi.toml` descriptions of `pyforge-{mason,scribe,warden}-coverage-gate` still say each mirrors a step of
     the `<s>-test` job. These are now separate gate jobs.
   - The `pixi.toml` description of `pyforge-herald-test-built` and herald's `tests/meta/pages_astro.py:39` still
     say CI's herald job runs `pyforge-herald-test-built`.
   - Doctor's `tests/meta/test_flag_gate_stays_outside_every_station.py:33` and
     `test_coverage_gate_stays_outside_every_station.py:89` still say `pyforge-core-test` runs on any single-station
     change. In CI, `core-live-test` now does.

   *Response:* outside this story's files. Reported for the integrator to assign: `pixi.toml` through Story 124.3
   or 122.4, plus the docs how-to, herald and doctor. `docs/how-to/pixi-tasks.md` is regenerated, not hand-edited.

**Round 1 re-run (2026-11-12).** Run with TMPDIR off tmpfs and scribe's Postgres up.

- **Pass:** AC1 (`[]`), AC3 (22), AC4 (4), AC5 (`postgres pgvector/pgvector:pg17`), AC6, AC7, AC8 and AC9 (8).
  The integrator-named re-runs are green too: steward `test_preflight_ci.py`, herald
  `test_preflight_pages_lane.py` and `test_built_site_tests_install_first.py`, core
  `test_conformance_lane_wired.py` and the kit's `test_testing_kit_lane_wired.py`.
- **AC2:** rc 1. The same five failures, all from the modules in finding 1.
  `test_root_handoffs_are_declared_exactly` and `test_the_handoff_floor` pass.
- **AC10:** rc 2, because the worktree has no journal. Against a scratch root holding this budgets file and the
  primary checkout's journal, the same report exits 0.
- **AC11:** rc 1. Every leg is green through mason. The run stops at scribe's live half on
  `test_live_tree_no_spec_is_behind_its_memlog` (Story 122.5). Legs run alone afterwards:
  - warden, both halves: rc 0.
  - `pyforge-steward-test`: rc 0. The trigger map now runs in the live half.
  - `pyforge-steward-live-test`: rc 1. It fails on the five AC2 failures and on
    `test_capability_ledger_live::test_the_ledger_has_no_finding_but_the_exemption` (Stories 121.7 and 122.5).
- **AC12:** rc 1. The atlas, doctor, herald, marshal and mason gates are OK. The run stops at scribe's live half,
  as AC11 does. Gate drivers run alone: scribe OK and warden OK. Steward fails on `pyforge.steward.suite_advance` at
  57.4%; only Story 122.3 (a87df74b2c) touched that module.
- **AC13:** rc 1, because its first command is AC11.

## Review findings (build, round 2, 2026-11-11)

A second independent review failed the round-1 build. This section lists each finding with its severity, where it
is and the problem, then what this round did. No acceptance command was corrected: the reviewer said none was wrong.

1. **Blocker: AC2 is still red** (`tests/meta/test_station_tests_trigger_map.py`). On re-run it gives rc 1: 5
   failed, 54 passed. The failures are `test_the_package_half_reads_nothing_outside_its_package[doctor|mason|scribe|steward]`
   and `test_every_read_and_declared_glob_fires_its_job`. Every misfire is a package-half read from a module this
   story does not own, and none of those modules is marked:
   - doctor: `tests/unit/test_sources_writer_lock.py` (56.5);
   - mason: `tests/meta/test_adapter_sole_caller.py` and `tests/unit/test_errors.py` (38.2);
   - scribe: `tests/unit/conftest.py`, `test_compile.py` and `test_extras_graphify.py` (33.1), and
     `test_recall.py` (33.2);
   - steward: `tests/unit/test_cutover_ledger.py` (121.1), `tests/unit/test_cutover_ledger_check.py` (121.6) and
     `tests/meta/test_portability.py` (123.2).

   The reviewer's simulation marked the nine modules. Every array then fired and the handoffs were exact, except
   scribe's conftest.
   *Response:* confirmed on the 2026-11-12 re-run, which gave the same five failures. Counted by source module,
   the misfires are `test_portability.py` 18, `test_extras_graphify.py` 16, `test_compile.py` 6,
   `test_sources_writer_lock.py` 5, the two cutover-ledger tests 5, `test_recall.py` 3, scribe's conftest 2 and the
   two mason tests 1. `test_root_handoffs_are_declared_exactly` and `test_the_handoff_floor` pass. The fix is in
   the owners' files. Each owner marks the module `pytest.mark.live_tree` or drops the tracked-path literal; the
   2026-10-12 ruling makes a string literal that names a tracked path a read. The integrator assigns this work,
   and this story cannot edit those files.

   On scribe's conftest, the reviewer's conclusion holds: no marker clears it. The reason the reviewer gave does
   not. `half_modules` does honour a conftest's marker line (see finding 5). The reads stay in the package half
   for a different reason. `Scanner._fixture_chain` evaluates `graph_store_factory` for every module under
   `tests/unit/`, and `test_graph_store_operations.py`, a package-half module, requests that fixture. Through
   `require_pg_dsn`, the fixture's postgres param reaches `pixi.toml` and
   `src/platform/db/changelog/changes/pyforge-scribe-*.sql`.

   This round ran a scratch simulation that also marked the conftest, `r2/sim_marks_conftest.py` under this
   story's build scratch. It leaves the same three package-half reads. Two ways out remain:
   - Scribe 33.1 restructures the conftest so that only live-tree modules request the postgres variant.
   - An integrator ruling lets the derivation follow a param's `live_tree` mark.

   This story does not make the derivation follow param marks without that ruling. That would be new behaviour
   this spec does not carry. The cheap version of it is unsound: crediting a whole fixture body to the live half
   because one of its params is marked would hide a package-half read in the fixture's other branch.
2. **Blocker: AC11 and AC13 are red.** The reviewer ran each leg alone. 16 of 18 legs pass. Two fail:
   - `pyforge-scribe-live-test::test_live_tree_no_spec_is_behind_its_memlog` (Story 122.5 re-derives
     `spec-pyforge-steward`);
   - `pyforge-steward-live-test`, with the five AC2 failures and
     `test_capability_ledger_live::test_the_ledger_has_no_finding_but_the_exemption` (121.7 and 122.5).

   *Response:* confirmed, and outside this story's files. The 122.5 causes need that story, or an integrator ruling
   that names the window. The AC2 causes need the owners named in finding 1.
3. **Blocker: AC12, the steward gate.** `pyforge.steward.suite_advance` is at 57.4%, under the 80% unit floor.
   *Response:* confirmed, and the cause is now traced. `scripts/coverage_gates_ci.py` gates only the source modules
   that the branch diff touches. Story 122.3's one-line edit (a87df74b2c) makes `suite_advance` a touched module,
   and it is the only commit on the branch that touches it. On `main` the module is not judged, so the floor
   exposes coverage it already lacked. This story did not cause it. Story 122.3's owner adds tests, or the
   integrator records a ruling.
4. **Minor: AC10 exits 2 with "no valid run in journal".** The worktree has no `.steward/preflight-runs.jsonl`.
   The reviewer's scratch root, holding this budgets file and the primary checkout's journal, exits 0.
   *Response:* nothing to change. This round did not touch the budgets file. AC10 is re-run after doctor 58.4's
   full preflight writes the journal.
5. **Minor: the `half_modules` conftest rule.** The reviewer said a conftest always lands in the package half and
   that live-half arrays are never credited with conftest reads. *Response:* partly wrong, partly right.
   - Wrong on the marker. `pytest` ignores a conftest's `pytestmark`, but here it is a declaration, and
     `half_modules` honours it. Core's `tests/meta/conftest.py` (Story 117.1) and steward's
     `tests/integration/conftest.py` (Story 117.4) carry it. That is why steward's integration conftest is declared
     under `steward_live` in `ROOT_HANDOFF_INPUTS`.
   - Wrong on the live half. Every scanned module loads the conftests above it (`_fixture_chain`), which
     evaluates their fixtures and whatever the fixtures call. Those reads count in every half that has a module
     under the conftest. This round's scratch check (`r2/dbg_live.py`) shows `scribe_live` credited with the same
     three conftest reads as `scribe`.
   - Right on the docstring. It did not say how a conftest is attributed.

   Fixed: the `half_modules` docstring now states both routes and both consequences. The derivation does not follow
   param marks, and a hook in a marked conftest is credited to the live half only. `_collected`'s docstring now
   says that pytest *loads* a conftest. Behaviour is unchanged. The reviewer's other option, crediting every
   conftest to both halves, would put core's sibling-enumeration helpers, which only live modules call, into
   core's package half. That would be a false red, and it would undo the marker line two stories rely on. Ruff
   check and format are clean on the file.
6. **Minor: stale text outside this story's files** (round-1 finding 5). The affected texts are `pixi.toml`'s
   descriptions of `pyforge-mason-recipe-build-smoke`, `pyforge-{mason,scribe,warden}-coverage-gate` and
   `pyforge-herald-test-built`; `docs/how-to/recipe-testing-and-builds.md:21`; herald's `tests/meta/pages_astro.py:39`;
   and doctor's `test_flag_gate_stays_outside_every_station.py:33` and
   `test_coverage_gate_stays_outside_every_station.py:89`. *Response:* unchanged and outside this story's files.
   The integrator assigns them: `pixi.toml` through 124.3 or 122.4, plus the how-to page, herald and doctor.


## Integrator ruling (2026-11-12, before the chunk-7 retry)

The chunk-6 build run stopped during fix round 2, when the session dropped. Round 2's work on disk stays and
stands as written unless this ruling changes it. This ruling binds the implementer and the reviewer.

1. **AC2: the nine unmarked package-half modules.** This story now owns these nine modules, for their
   `pytestmark` line or the one flagged literal only:
   - `src/shared/packages/pyforge-doctor/tests/unit/test_sources_writer_lock.py`
   - `src/shared/packages/pyforge-mason/tests/meta/test_adapter_sole_caller.py`
   - `src/shared/packages/pyforge-mason/tests/unit/test_errors.py`
   - `src/shared/packages/pyforge-scribe/tests/unit/test_compile.py`
   - `src/shared/packages/pyforge-scribe/tests/unit/test_extras_graphify.py`
   - `src/shared/packages/pyforge-scribe/tests/unit/test_recall.py`
   - `src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger.py`
   - `src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py`
   - `src/shared/packages/pyforge-steward/tests/meta/test_portability.py`

   For each module, first check what the flagged literal does.
   - If the module really reads the tracked path, add `pytestmark = pytest.mark.live_tree`. If a `pytestmark`
     already exists, add the mark to it.
   - If the literal only names a path and the test never reads the live tree (a string it compares, or a path
     built under `tmp_path`), change the literal so the scan no longer counts a read. Keep the assertion as
     strong as it was.
   - Never move or delete an assertion or a test.
   After the edits, run the package half and the live half of doctor, mason, scribe and steward
   (`pyforge-<s>-package-test`, `pyforge-<s>-live-test`). Also run doctor's
   `tests/meta/test_package_half_is_the_oracle.py`. None may go red. No gap ceiling and no allowlist may grow.
2. **AC2: scribe's `tests/unit/conftest.py`.** Its reads of `pixi.toml` and
   `src/platform/db/changelog/changes/pyforge-scribe-*.sql` happen under the `postgres` param of
   `graph_store_factory`. That param carries `pytest.mark.live_tree` (conftest.py:136). Under
   `-m "not live_tree"`, pytest deselects the param, so the package half never runs those reads. Teach the
   derivation that fact:
   - A read reached only through a fixture param whose `pytest.param(..., marks=...)` includes
     `pytest.mark.live_tree` counts in the live half only.
   - Implement it in the scanner: read the marks in `@pytest.fixture(params=[...])` the way `_parametrized` reads
     `parametrize`.
   - Add a check to `test_station_tests_trigger_map.py`: a marked fixture param's read lands in the live half, and
     an unmarked param's read stays in the package half.
   - Correct the `half_modules` docstring: its first stated consequence (param marks are not followed) no longer
     holds.
   - Never edit scribe's conftest to hide a read. Never credit a read by file name or from a hand-kept list.
   - The unmarked `flatfile` param, or any other package-half path, may also reach one of these reads. If so, the
     read is real. Report it under `## Review findings` as a scribe finding, and do not hide it.
3. **AC12: `pyforge.steward.suite_advance` is at 57.4%.** The gap already existed. Story 122.3's one-line edit
   (a87df74b2c) only made the module a touched module. This story now owns `src/shared/packages/pyforge-steward/tests/unit/test_suite_advance.py`:
   - Add tests until the steward coverage gate passes for `suite_advance`.
   - The tests read nothing outside steward's package; use `tmp_path`.
   - The tests assert behaviour, not lines.
   - Never change `suite_advance.py`.
4. **Planned windows for AC10, AC11 and AC13.**
   - AC10 (`preflight-budget`, "no valid run in journal"): it passes by the reviewer's scratch-root method. The
     integrator re-runs it after the final full preflight writes `.steward/preflight-runs.jsonl`.
   - AC11 and AC13 pass when only these two legs are red:
     - `pyforge-scribe-live-test` `test_live_tree_no_spec_is_behind_its_memlog`, for `spec-pyforge-steward` only.
       It closes at steward 122.5.
     - `pyforge-steward-live-test`
       `test_capability_ledger_live.py::test_the_ledger_has_no_finding_but_the_exemption`. It closes at
       CLOSE-LEDGERS (see the integrator ruling in spec-121-7).
     Every other red leg is real.
   - AC12: once item 3 lands, every coverage gate must pass. No coverage gap is planned except `suite_advance`'s,
     and item 3 closes that one.
5. **Stale texts that still name the old jobs (round-1 finding 5).** The integrator corrects them after BUILD-17,
   before the full preflight. They are not a finding against this story. The texts:
   - root `pixi.toml`, task descriptions only;
   - `docs/how-to/recipe-testing-and-builds.md:21`;
   - herald `tests/meta/pages_astro.py:39`;
   - doctor `tests/meta/test_flag_gate_stays_outside_every_station.py:33`;
   - doctor `tests/meta/test_coverage_gate_stays_outside_every_station.py:89`.
6. Append `## Review findings (build, round 3, 2026-11-12)` and say how each item above closed. Never change
   `pixi.lock`.

## Review findings (build, round 3, 2026-11-12)

Round 3 works the integrator ruling of 2026-11-12. Each item, then how it closed. Every run below used TMPDIR off
tmpfs, scribe's Postgres up, each suite under its env lock and one aggregate at a time.

1. **Item 1: the nine package-half modules.** Each module was checked for what its flagged literal does. In all nine
   the literal only names a path: a file planted under `tmp_path`, a citation or substring the test compares, or a
   path string handed to the code under test. None of them reads the live tree, so none was marked `live_tree`.
   Each flagged literal is now spelled as a join with the same value (`"/".join((...))`, or `Path("a", "b", ...)`
   where the test held a `Path`), under one two-line comment that says why. No assertion or test moved. Literals
   changed per module: doctor `test_sources_writer_lock.py` 7, mason `test_adapter_sole_caller.py` 1 and
   `test_errors.py` 1, scribe `test_compile.py` 7, `test_extras_graphify.py` 6 and `test_recall.py` 6, steward
   `test_cutover_ledger.py` 4, `test_cutover_ledger_check.py` 3 and `test_portability.py` 11. Ruff check and
   format are clean.
   - `test_portability.py` was the only reader of `docs/MAP.md` that round 1 listed in `steward_live_paths` ahead of
     time. Its literal was a string handed to `is_packaging_test_input`, not a read. So this round removes that
     array entry and the workflow comment that named it. Doctor's live array keeps its own `docs/MAP.md`. The
     derivation finds no steward live-half reader of the file.
   - Runs: doctor package 2707 passed; doctor live 1534 + 4 passed; mason package 1693 passed; mason live
     73 + 2 + 12 passed; scribe package 378 passed, 4 skipped; steward package 1958 + 33 passed; warden package
     2251 + 264 passed; warden live 148 passed; doctor `tests/meta/test_package_half_is_the_oracle.py` 16 passed.
     Scribe live: 1 failed, 162 passed. Steward live: 1 failed, 1776 passed, and its second segment 72 passed.
     Both failures are item 4's windows. No gap ceiling or allowlist changed.
2. **Item 2: scribe's conftest and fixture params.** Reading param marks alone would not have cleared the package
   half. Two other routes also credited scribe's conftest reads to it:
   - The scanner evaluated every fixture of every conftest a module loads, whether or not a test requests it.
     `live_repo_root` reaches `pixi.toml`, and `pg_dsn` reaches the changesets. Only live-tree modules request
     either fixture.
   - The unmarked conftest's whole-file scan ran each helper (`find_repo_root`, `scribe_changeset_paths`) as if
     it ran.

   The scanner in `tests/meta/test_station_tests_trigger_map.py` now models what pytest runs:
   - A fixture is evaluated when a scanned function requests it. Its body, the fixtures it requests and the helpers
     it calls count in the half that requests it. Autouse fixtures and `pytest.mark.usefixtures` count as requests.
   - A conftest's whole-file scan covers its hooks, module-level statements and string literals. Its fixtures count
     where requested and its helpers where called.
   - `_fixture_params` reads `@pytest.fixture(params=[...])`, the twin of `_parametrized`. A `pytest.param(...,
     marks=...)` that names `live_tree` is a marked param.
   - The package half (`Scanner(package_half=True)`) skips marked params. A comparison of `request.param` with
     constants decides its branch, and a decided branch that returns ends the body.
   - The live-tree half runs every param. `derive_reads` also scans there each package-half test module that
     requests a marked param (`Scanner.requests_a_live_param`), because pytest runs that test with that param in
     the live-tree half. Today that is scribe's `tests/unit/test_graph_store_operations.py` alone.

   One fix-now in the same scanner: `_call_function` cached a result the depth limit had cut short. Once
   `pg_dsn` became the first caller, scribe's live half lost its changeset glob read that way. A result the
   depth limit cuts short is no longer cached.

   A before/after dump of the whole derivation (20 outputs) shows what moved:
   - Scribe's package half loses `pixi.toml`, `src/platform/db/changelog/changes` and its
     `pyforge-scribe-*.sql` glob, all from the conftest.
   - `scribe_live` keeps all three.
   - `mason_live` gains a second source for a read it already had.

   No other read and no handoff moved. Every package half now derives empty. Neither the unmarked `flatfile`
   param nor any other package-half path reaches the three reads, so there is no scribe finding. The new check,
   `test_a_live_tree_fixture_param_counts_in_the_live_tree_half_only`, plants a package through
   `Scanner(sources=...)` in the shape of `graph_store_factory`. It asserts that the marked param's read lands in
   the live-tree half only, that the unmarked param's read stays in the package half, and that the same read
   counts in the package half once its mark is dropped. A scratch mutation run reds it when the mark filter, the
   branch decision or the mark reading is removed. The `half_modules` docstring now describes both halves'
   handling and no longer says param marks are not followed. AC2: 60 passed.
3. **Item 3: `suite_advance` coverage.** `tests/unit/test_suite_advance.py` gains 11 behaviour tests. They cover
   each refusal at resolve (a missing recipe, a package the truth report omits), a failing stage that stops the
   chain, the live, quiet and dry-run summaries, the text report, `advance_from_namespace`, and each default stage
   runner. The default runners get a recording `subprocess` stand-in, and `fetch_channel_version` is stubbed, so no
   test reaches a subprocess, the network or `gh`. Every tree is under `tmp_path`. `suite_advance.py` is unchanged.
   The module reaches 99% (branch) in its own file's run. The steward gate driver reports OK, 23 modules at or
   above 80%.
4. **Item 4: the planned windows.** The re-run results:
   - AC10: rc 2 in the worktree ("no valid run in journal"). By the scratch-root method (this budgets file and the
     primary checkout's journal under `PIXI_PROJECT_ROOT`), rc 0.
   - AC11: rc 1. Every leg is green through `pyforge-scribe-test`, and the run stops at `pyforge-scribe-live-test`.
     Run alone after it, steward package, warden package and warden live are rc 0. Steward live is rc 1 on
     `test_capability_ledger_live.py::test_the_ledger_has_no_finding_but_the_exemption` alone.
   - The scribe red is `test_live_tree_no_spec_is_behind_its_memlog`. It holds the ruling's window
     (`spec-pyforge-steward` behind its memlog, 2 entries, closed at steward 122.5). The same assertion also lists
     25 rows of `spec-pyforge-marshal` and 7 of `spec-pyforge-unifying-strategy` in
     `tests/meta/data/spec_behind_memlog_known.json` that are no longer behind. Scribe Story 31.4 (BUILD-16)
     refreshes that file. This cause sits in the same test but outside the ruling's literal "for
     `spec-pyforge-steward` only", so it is reported here for the integrator. It is not this story's file.
   - AC12: rc 1. The aggregate's scribe gate depends on scribe's live leg (the AC11 window). Each of the eight gate
     command lines run alone against the reports the runs above wrote is rc 0: atlas, doctor, herald, marshal,
     mason, scribe, steward and warden.
   - AC13: rc 1, because its first command is AC11 with the same stop. Its second command is the steward live leg
     above.
5. **Item 5: stale job texts.** Left to the integrator, as ruled. No file named there was touched.

**Round 3 acceptance re-run (2026-11-12).** AC1 `[]` rc 0; AC2 60 passed rc 0; AC3 22; AC4 4; AC5
`postgres pgvector/pgvector:pg17`; AC6 83 passed rc 0; AC7 rc 0; AC8 21 passed rc 0; AC9 8; AC10 rc 2 (rc 0 by the
scratch root); AC11 rc 1; AC12 rc 1 (every gate rc 0 alone); AC13 rc 1. The integrator-named re-runs: steward
`test_preflight_ci.py` 25 passed, herald `test_preflight_pages_lane.py` and `test_built_site_tests_install_first.py`
22 passed, core `test_conformance_lane_wired.py` 16 passed, the kit's `test_testing_kit_lane_wired.py` 21 passed.
`pixi.lock` is unchanged.
