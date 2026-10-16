---
title: "45.1: Herald's built-site tests install docs-site first, in preflight and CI"
type: 'fix'
created: '2026-10-16'
status: 'done'
baseline_revision: 'd21af06fbc71e4aa91cd9e572c8fa59e9e4c2be6'
flag-exempt: detector-or-gate   # a fix needs no flag (spec-feature-flag-governance Q1: flagging a fix keeps the bug reachable); and herald's suite task is a gate whose silent green this story ends, so a flag-OFF run would report exactly that silent green (Q2's gate exemption), the rule steward 105.1 followed
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-105-1-the-preflight-never-runs-two-docs-site-lanes-at-once.md
  - pixi.toml
  - .github/workflows/pyforge-station-tests.yml
  - .github/workflows/coverage-gates.yml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/tests/meta/test_preflight_docs_site_lanes.py
  - src/shared/packages/pyforge-herald/tests/meta/pages_astro.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/estate_verify.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - docs/foundry/sbom-gaps.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** herald's built-site tests run only where `docs-site/node_modules` already happens to exist. Steward
Story 105.1 named this as residual risk. Line numbers are at `d21af06fbc`.

- **What the tests need.** `tests/meta/pages_astro.py` reads `RENDER_READY` (node on PATH and
  `docs-site/node_modules/astro/bin/astro.mjs` present) when it is imported, and `needs_astro` skips without it. That
  covers 17 tests in `test_one_generator.py` and `test_docs_site_nav.py`. `test_agent_surface_and_changes.py` keeps a
  copy of the marker (`_BUILD_READY`, `:38`-`:42`) for 8 more.
- **Nothing that runs the suite installs.** `pyforge-herald-test` is `pytest src/shared/packages/pyforge-herald/tests
  -q` with no dependency (`pixi.toml:3124`-`:3126`).
  - **The preflight.** A diff that touches only herald fires `pyforge-station-tests.yml`'s herald job and not
    `pages.yml`, so `run_preflight` selects `pyforge-herald-test` and not `docs-site-install`. 105.1 orders the
    install first only when both are selected.
  - **CI.** The herald job (`pyforge-station-tests.yml:579`-`:603`) sets up only `pyforge-herald` and runs `pixi run
    --frozen -e pyforge-herald pyforge-herald-test`. `pages_astro.py:34` says so: "No CI lane that runs the herald
    suite installs docs-site".
- **Measured.** Through `run_preflight`'s own selection, at `d21af06fbc`, with an untracked
  `tests/unit/preflight_probe.py` (a herald test-tree file, not a test module) and no `docs-site/node_modules`
  (journal `bd2a4ac1`, exit 0). The runner selected two of the eight lanes the proof's lane list names
  (`pyforge-herald-test`, `pyforge-herald-coverage-gate`) and no install. Herald reported 2033 passed and 30 skipped:
  25 of the skips name the docs-site install, 17 through `needs_astro` and 8 through its copy.
- **Why it is a defect.** CAP-61's success says `pyforge-herald-test` is green. The built-site half of that suite is
  the proof that the one generator renders the artifact, and it skipped wherever the suite ran.
- **What the fix must not do** (the independent review's should-fix 2, ruled by the operator through the coordinating
  session). fnd:CAP-13 says one pixi task run from the SBOM (plus its layer) alone runs the station suites, and
  `docs/foundry/sbom-gaps.md` classes `feature:site` as won't-do. `pyforge-station-tests` and `sbom-laptop-gate` run
  `pyforge-herald-test`, so that task, and every aggregate that uses it, stays free of the `site` environment and npm.

**Approach:** a separate task installs docs-site and then runs herald's suite. CI's herald job runs it strictly, the
preflight runs the install before herald's lane, and the plain suite task stays npm-free.

- **The plain task.** `pyforge-herald-test` keeps its `pytest` command and takes no dependency and no variable.
  Without an install its built-site tests skip, naming the install. So `pixi run --as-is --dry-run` of
  `pyforge-station-tests` and of `sbom-laptop-gate` (in `pyforge-foundry-full` or `pyforge-guild`) names no task in
  `site` and no `npm ci`.
- **The built task.** `pyforge-herald-test-built` is cmd-less: `depends-on = [{ task = "docs-site-install",
  environment = "site" }, { task = "pyforge-herald-test", environment = "pyforge-herald" }]`. pixi runs the
  dependencies of a cmd-less task in the order they are declared, as `pyforge-station-tests` already relies on: `npm
  ci` in `docs-site/`, in the `site` environment, then the suite. herald's environment gains no package, and
  `pixi.lock` does not move.
- **CI.** The herald job's `setup-pixi` sets up `pyforge-herald site`, so the `site` environment is cached beside
  herald's. Its test step runs `pixi run --frozen -e pyforge-herald pyforge-herald-test-built` with the step's
  `env: HERALD_DOCS_SITE_REQUIRED: "1"`. The Chromium step and `setup-uv` are unchanged: Astro needs only node, which
  both environments carry. A cmd-less task cannot carry `env` (pixi refuses the key), so the variable sits on the step.
- **The preflight selects the install.** `preflight_ci._step_matches` (`preflight_ci.py:455`) matches a lane when the
  task a CI step runs holds it in its `depends-on` closure. The herald job's step runs `pyforge-herald-test-built`,
  so the reader selects `docs-site-install@site` beside `pyforge-herald-test@pyforge-herald`.
- **The preflight runs it first.** Herald's lane has no edge to the install, so two things order it:
  - **Declaration.** `pr-preflight-lanes` gains `{ task = "docs-site-install", environment = "site" }` as a leg of its
    own, before `pyforge-station-tests`. The install is then the first docs-site lane declared, and 105.1's
    `_next_lane` gives it the docs-site lanes' first turn.
  - **The touched cut.** `touched_cut` keeps a selected `docs-site-install` beside any kept lane in `DOCS_SITE_TASKS`,
    with the reason "`<lane>` reads its install" (`preflight.DOCS_SITE_INSTALL_TASK`). Without it a touched run, the
    default before a push, would defer the install to CI while herald's lane ran. It adds no lane edge, so it cannot
    reach the hang below.
- **A missing install is a red test.** Under `HERALD_DOCS_SITE_REQUIRED=1` (CI's step, and
  `pyforge-herald-test-coverage`, which keeps its install dependency), `pages_astro.needs_astro` fails a built-site test
  whose install is missing, naming the install. A build helper (`astro_build`, and `test_agent_surface_and_changes.py`'s
  builder) calls `require_astro()` first, so a module fixture that builds before its tests reports the same cause, never
  node's stack. Without the variable (the plain task, a bare `pytest`, CI's coverage leg, which runs its driver) the
  tests skip, naming the command. `test_agent_surface_and_changes.py` uses `pages_astro`'s one marker.
- **`estate verify --lane`** (the review's should-fix 1). `estate_verify.py:441`-`:463` ran a filtered lane alone with
  `--skip-deps` and its edges dropped. With the plain task dependency-free, `--lane pyforge-herald-test` no longer
  bites (its tests skip, as before 45.1), but `--lane pages-build` still ran without `docs-site-install`.
  `_with_dependencies` now runs the chosen lanes' dependency closure first, in the lane list's order, as rows of their
  own.
- **The suite-reduction fallback** (nit). `preflight.py:716`-`:726` (`--collect-only` when every reduced segment
  collects nothing) gains `--skip-deps`, as every lane runs.
- **105.1's set and meta tests stay exact.** `DOCS_SITE_TASKS` does not change, and
  `test_preflight_docs_site_lanes.py` is byte-identical to `main`. The plain task has no dependency, so no task's
  closure reaches the install through herald's suite again; `pyforge-herald-test-built` has no `cmd`, so no rule
  derives it.
- **Steward's selection oracle.** `test_preflight_selection.py`'s oracle maps each workflow job to the lanes it runs.
  Herald's job runs `docs-site-install` too (its step's task depends on it), so the oracle adds the install when
  herald's output is true, and the `pixi.toml` and Dream-only cases expect it. The `pixi.toml` case still refuses
  `pages-build` and `pages-check`: `pages.yml` does not fire.
- **The generated pixi-tasks page.** Task descriptions change, so `docs/how-to/pixi-tasks.md` and its stamp in
  `docs/map.yaml` are regenerated (`docs-pixi-tasks`).
- **Owned elsewhere.** The latent preflight hang is steward's `DW-steward-103-6-1` (extended with this story's probe,
  `file:line` and the two fix options). The pre-existing `pr-preflight-lanes` dry-run failure is `DW-steward-45-1-1`.
- **Unchanged.** `preflight_ci.py`, `DOCS_SITE_TASKS`, the pre-push hook, `pixi.lock`, `environment.yaml`,
  coverage-gates.yml, pages.yml and every fnd:CAP-13 text.

**Rejected:**
- **A dependency on `pyforge-herald-test` itself** (the first commit, `57af743b4f`). It ordered the install by an
  edge and kept it in a touched run for free, but `pyforge-station-tests` and `sbom-laptop-gate` then pulled the
  `site` environment and 361 npm packages: `pixi run --as-is --dry-run -e pyforge-foundry-full sbom-laptop-gate`
  listed `docs-site-install in site`, against fnd:CAP-13 (the review's should-fix 2).
- **A strict built task with its own `cmd` and `env`.** CI's step would then run it and not `pyforge-herald-test`, so
  the reader would match no CI step to the plain lane, which `pr-preflight-lanes` holds through `pyforge-station-tests`
  (`spec-pyforge-core`'s meta test requires that aggregate there). A lane no step matches has "no CI counterpart" and
  always runs, so every preflight would run herald's suite twice.
- **Replacing `pyforge-station-tests` in `pr-preflight-lanes` with its legs**, herald's swapped for the built task.
  `pyforge-core`'s `test_conformance_lane_wired.py` reds a `pr-preflight-lanes` without `pyforge-station-tests`.
- **Implicit edges from every docs-site lane to a selected install in `run_preflight`.** One mechanism for order and
  cut, but it changes 105.1's tested scheduling: AC12's red-stop test runs herald before a deferred install.
- **An install-first rule in `_next_lane`.** The same conflict with AC12; the declaration order gives the same turn on
  the shipped list with no scheduler change.
- **A dependency on `pyforge-herald-coverage-gate`.** coverage-gates.yml's matrix step runs `python
  scripts/coverage_gates_ci.py`, not the task, so the reader matches the gate's lane by its command line, and that
  match brings no dependency. On a diff of `scripts/coverage_gate.py` alone (the coverage gates' shared surface, which
  fires every station's gate and not herald's job), the reader selects the gate's lane without the install. A lane
  whose dependency lane is not in the run never becomes ready, and the scheduler loop spins: the probe
  `gate_dep_hang_probe.py` (scratch) was still running after 30 s.
- **Making the preflight close over dependencies in a full-scope run.** That is the general cure for the hang above,
  but this story needs it for no lane; it is steward's, on `DW-steward-103-6-1`.
- **Failing under `CI`, as atlas's `WASM_SMOKE_REQUIRED or CI` does.** CI's coverage leg runs herald's unit suite,
  built-site tests included, through its driver with no install. Under `CI` that leg would go red.
- **Failing under a `PYFORGE_PREFLIGHT_*` variable.** The preflight sets none in a lane's environment.
- **Installing in a CI step of its own** (`pixi run -e site docs-site-install` before the test step). The same
  selection, but no named task to run locally; the built task gives one.

Ledger key: `45-1-the-built-site-tests-install-docs-site-first`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-herald` CAP-61 (one generator renders the whole Pages site). Its success says
  `pyforge-herald-test` is green, and the built-site tests are its evidence. This story restores that oracle, so it
  mints no CAP and changes no `SPEC.md` text.
- **Works with.** `pyforge-steward:CAP-159` (`spec-pyforge-steward`): the preflight's selection (Story 71.2), its
  docs-site mutex and order (Story 105.1) and its touched scope (Story 103.6), which gains the install rule; and
  steward's `estate verify` (Story 100.4, `pyforge-steward:CAP-167`), which now runs a lane's dependencies first.
- **Holds.** `fnd:CAP-13` (`spec-python-foundry-cutover`): the laptop gate runs the station suites from the SBOM alone.
- **Governance.** `pixi.toml` is shared surface. `pyforge-station-tests.yml`, `preflight.py`, `estate_verify.py` and
  steward's tests are on `spec-pyforge-steward`'s surface (and `preflight.py` on `spec-pyforge-core`'s), and herald's
  tests on `spec-pyforge-herald`'s.
- **Flag.** None: under `spec-feature-flag-governance` Q1 a `fix` needs no flag. The spec also carries
  `flag-exempt: detector-or-gate`, because herald's suite task is a gate.
- **Origin.** `docs/dreams/pyforge-herald.md`, Realization log, the 2026-10-16 entry (the built-site tests skip
  silently), and steward Story 105.1's residual risk ("A herald-only diff does not select `docs-site-install`").

## Acceptance Criteria

- **AC1: the plain task stays npm-free.** `pyforge-herald-test` has no `depends-on` and no
  `HERALD_DOCS_SITE_REQUIRED`. The `depends-on` closures of `pyforge-station-tests` and `sbom-laptop-gate` hold no task
  of the `site` feature and no dependency in the `site` environment; the same walk finds the install under
  `pyforge-herald-test-built` and `pr-preflight-lanes`. `pixi run --as-is --dry-run` of both aggregates names no task
  in `site`.
- **AC2: the built task installs, then runs the suite.** `pyforge-herald-test-built` has no `cmd` and `depends-on =
  [docs-site-install@site, pyforge-herald-test@pyforge-herald]`, in that order; `docs-site-install` is `npm ci` with
  `cwd = "docs-site"`. `pyforge-herald-test-coverage` depends on the install and sets the variable.
- **AC3: the gate takes no dependency.** `pyforge-herald-coverage-gate` has no `depends-on` and no
  `HERALD_DOCS_SITE_REQUIRED`.
- **AC4: CI runs the built task strictly.** The herald job's `setup-pixi` sets up `pyforge-herald` and `site`. Its
  one herald run step is `pixi run --frozen -e pyforge-herald pyforge-herald-test-built`, with
  `HERALD_DOCS_SITE_REQUIRED: "1"` in the step's `env`.
- **AC5: the preflight installs first.** In a scratch repo carrying the real workflows and `pixi.toml`, a branch that
  touches only a herald test-tree file gets `pyforge-herald-test@pyforge-herald` and `docs-site-install@site` from
  `select_lanes`, and not `pages-check`. Herald's lane has no edge. The install is the first docs-site lane declared
  and comes before herald among the selected lanes. `touched_cut` keeps it as "`pyforge-herald-test@pyforge-herald`
  reads its install". Through `run_preflight` with an injected runner, the install ends before herald starts at
  `--jobs 1` and `--jobs 8`, in the full and the touched scope.
- **AC6: the touched rule is narrow.** In a fixture, a kept docs-site lane brings a selected install; a kept lane
  outside the set leaves it deferred; an install the selection did not select is never added.
- **AC7: a required, missing install is red.** `requires_astro(ready=False, required=True)` makes a test that fails
  with pytest's `Failed`, naming `HERALD_DOCS_SITE_REQUIRED` and the install, and keeps the test's fixture
  parameters. `required=False` makes a `skip` mark naming the install, and `ready=True` leaves the test unchanged. In a
  child pytest the two give `1 failed, 1 skipped`. `astro_build` with `RENDER_READY` false fails naming the install.
- **AC8: `estate verify --lane` runs its dependencies first.** A filtered lane whose dependency the selection did not
  select runs after that dependency, each a row of its own.
- **AC9: the fallback skips dependencies.** The suite reduction's `--collect-only` fallback argv carries `--skip-deps`.
- **AC10: 105.1 stays exact.** `DOCS_SITE_TASKS` is unchanged, `test_preflight_docs_site_lanes.py` is byte-identical
  to `main` and passes, and `test_preflight_selection.py`'s oracle equals the reader's selection on every parametrized
  diff.
- **AC11: mutation.** Each change below fails the named test (recorded under Verification run):
  - the built task's two dependencies swapped (AC2);
  - the install dependency given back to `pyforge-herald-test` (AC1);
  - the CI step's variable dropped, or the step running the plain task (AC4, AC5);
  - the install leg dropped from `pr-preflight-lanes` (AC5);
  - the touched rule off (AC6);
  - `estate verify` running a filtered lane alone (AC8);
  - the fallback without `--skip-deps` (AC9);
  - `needs_astro`'s required branch skipping instead of failing (AC7).
- **AC12: the proof.** On fresh copies (`git archive` of `main`, then `main` plus this story) with no
  `docs-site/node_modules` and only an untracked herald probe, through the copy's own `run_preflight`: before, the run
  selects no install and herald reports 25 skips naming it; after, in the full and the touched scope, the install runs
  first and herald reports none. `HERALD_DOCS_SITE_REQUIRED=1 pixi run --frozen -e pyforge-herald
  pyforge-herald-test-built` from no install runs `npm ci` and then the suite with no such skip.
- **AC13: green, and the surface reconciled.** These exit 0: the CI task above; steward's suite; `lint-types`;
  `ci_surface_gates.py --check`; `detectors-ci`; the planning detectors; `llms-full-check`; `pixi-version-check`;
  `docs_pixi_tasks --check`. `pixi.lock` is unchanged and `environment.yaml` re-exports byte-identical. Each changed
  governed path gets a reconcile entry on the memlog of every Spec that governs it, and the scoped stamps are taken
  after the commit.

## Boundaries & Constraints

**Always:**
- Keep `pyforge-herald-test`, and every aggregate that runs it, free of the `site` environment and npm (fnd:CAP-13).
- Keep the strict run where it is promised: CI's herald job sets the variable on the built task's step.
- Keep `needs_astro` declared once, in `pages_astro.py`.

**Never:**
- Never change `preflight_ci.py`, `DOCS_SITE_TASKS`, 105.1's meta test, `pixi.lock`, `environment.yaml` or the
  pre-push hook.
- Never give a lane a dependency the preflight's reader would not select with it (`DW-steward-103-6-1`).
- Never weaken an existing assertion.

**Residual risk:**
- **The order in a full run rests on declaration.** Herald's lane has no edge to the install; the install's leg in
  `pr-preflight-lanes` makes it the first docs-site lane declared. AC5's two tests fail if the leg moves or goes. A red
  install no longer blocks herald's lane, which then runs against whatever the tree holds (and the run is red anyway).
- **Local `pyforge-herald-test` and `pyforge-station-tests` still skip the 25 without an install,** by the ruling.
  `pyforge-herald-test-built` is the local way to run them.
- **The preflight's herald lane is not strict.** It runs the plain task, so a missing install skips there rather than
  failing; the install runs first in both scopes, and CI's job is strict.
- **CI's coverage leg still skips the built-site tests.** It runs `coverage_gates_ci.py`, not a task, and installs no
  docs-site. The herald job runs them; their coverage contribution to herald's modules is nil (Astro builds in a child
  process).
- **The built task needs the npm registry.** `npm ci` downloads unless npm's cache holds the packages. The pytest run
  stays offline, behind `tests/conftest.py`'s egress fixture.
- **CI cost.** About +1.5-2 minutes on a herald job of about 2 minutes (test step 77-108 s on the last runs), plus one
  cold setup-pixi cache on the first run, because the environment list changes the cache key. Locally the suite went
  from about 74 s to about 158 s with the built-site tests (+84 s), and `npm ci` takes 3-6 s.

## I/O & Edge-Case Matrix

| Situation | Before (`main`) | After |
|---|---|---|
| herald-only diff, fresh tree, full preflight | herald alone; the 25 skip | the install, then herald; the 25 run |
| the same, touched preflight | herald alone; the 25 skip | the install kept ("reads its install"), then herald |
| CI herald job | `pyforge-herald` only; the 25 skip | `pyforge-herald site`; `npm ci`, then the 25 run, strictly |
| `pixi run -e pyforge-herald pyforge-herald-test`, no install | the 25 skip | the 25 skip (npm-free, unchanged) |
| `pyforge-station-tests`, `sbom-laptop-gate` | no `site` task | no `site` task (unchanged) |
| `pixi run -e pyforge-herald pyforge-herald-test-built` | (no task) | `npm ci`, then the suite |
| the plain task under `HERALD_DOCS_SITE_REQUIRED=1`, no install | the 25 skip | the 25 fail or error, each naming the install |
| CI coverage leg (herald) | built-site tests skip | unchanged |
| a `scripts/coverage_gate.py`-only diff, preflight | the gate's lane alone | unchanged (no dependency to strand) |
| `estate verify --lane pages-build` | runs without the install | the install row, then `pages-build` |
| a diff that fires `pages.yml` too | the install first (105.1) | unchanged |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-61 (one generator renders the whole Pages site). No CAP is minted,
  and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-16 entry (the built-site tests skip
  silently), amended the same day for the review.
- Epic: Epic 45 (new; Epic 44 is `done` and its theme is the docs shelf).
- Ledger key: `45-1-the-built-site-tests-install-docs-site-first`.
- Ledger status at mint: `in-progress`; `done` with the review fixes, in the landing PR.
- Deps: none. Steward Story 105.1 (PR #2242, `94a77d724d`) is on `main`.
- Spec: the `spec-pyforge-herald` memlog records the evidence, the design, the refutation, the review's redesign and
  the surface reconcile; the `spec-python-foundry-cutover` memlog records that the laptop gate stays npm-free.
- Surface: `marshal-policy.toml` `[epic_surfaces]."45"`.

## Verification

**Commands:**
- `HERALD_DOCS_SITE_REQUIRED=1 pixi run --frozen -e pyforge-herald pyforge-herald-test-built` — expected: pass, with
  no skip naming the docs-site install (CI's herald step).
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass. The station's `verify_commands`
  (MRS-GATE-010 binding), npm-free.

**Run before the push (not dispatch gates):**
- `PYTEST_ADDOPTS= pixi run --frozen -e pyforge-herald pytest
  src/shared/packages/pyforge-herald/tests/meta/test_built_site_tests_install_first.py
  src/shared/packages/pyforge-herald/tests/meta/test_preflight_pages_lane.py -q` — expected: exit 0 (AC1-AC5, AC7).
- `PYTEST_ADDOPTS= pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (AC6, AC8-AC10).
- `pixi run --as-is --dry-run -e pyforge-foundry-full sbom-laptop-gate`, the same in `-e pyforge-guild`, and `-e
  pyforge-guild pyforge-station-tests` — expected: exit 0, no task "in site", no `npm ci` (AC1).
- The AC11 mutations, one at a time — expected: each fails its named tests; each file is restored byte for byte.
- The proof (AC12): `make_copy.py` and `run_lanes.py` (scratch `b451-driver/`) build fresh copies and run the copy's
  `run_preflight` over a lane list in the shipped order, with each lane's command run in the worktree's installed
  environment.
- `lint-types`, `ci_surface_gates.py --check`, `detectors-ci`, the planning detectors, `llms-full-check`,
  `pixi-version-check`, `docs_pixi_tasks.py --check` and the `environment.yaml` export check — expected: exit 0.

## Verification run (2026-10-16)

The first commit's run (`57af743b4f`), kept as the record of that design; the review fixes below supersede its
dependency on `pyforge-herald-test`.

Hand-implemented on branch `chain-herald-tests-install-docs-site-2026-10-16`, from baseline `d21af06fbc` (steward 105.1,
PR #2242, which merged to `main` as `94a77d724d` during this run), uncommitted (staged). The diff is for an independent
review against this spec, not against this summary. Every verdict below is read from its exit code.

- **Before (`d21af06fbc`, the proof driver `herald_lanes_run.py`).** No `docs-site/node_modules`, an untracked herald
  probe. Journal `bd2a4ac1`, exit 0. The runner selected `pyforge-herald-test` and `pyforge-herald-coverage-gate`, and
  no install. Herald ran 0.2-74.7 s: 2033 passed, 30 skipped, 25 of them naming the docs-site install (16 in
  `test_one_generator.py`, 1 in `test_docs_site_nav.py`, 8 in `test_agent_surface_and_changes.py`).
- **The reader, explicit paths.** `preflight_ci.select_lanes_for_paths` over the probe path alone, with the branch's
  diff of that moment: 22 lanes before, herald's without the install; 23 after, `docs-site-install@site` among them.
  A touched-scope cut keeps it as "pyforge-herald-test@pyforge-herald depends on it".
- **After (the same driver and state, code final but for `require_astro` and this story's last test).** Journal
  `90114f10`, exit 0. Three lanes: `docs-site-install` 0.5-3.8 s, `pyforge-herald-test` 3.8-162.5 s (2068 passed,
  5 skipped, none naming the install), the gate 162.5-162.9 s.
- **After, final tree.** Journal `760d9d17`, exit 0. The branch now regenerates `docs/how-to/pixi-tasks.md`, so
  `pages.yml` fires as well and all eight lanes run: `docs-site-install` 0.6-4.6, `pages-build` 4.6-11.8, herald
  11.8-184.2 (2069 passed, 5 skipped), the gate, `pages-check` 184.5-186.3 and `docs-site-validate-sidebar`
  186.3-186.7; the two builtin-only validators ran beside the install (0.6-1.0). AC4's test holds the herald-only case
  on the final tree, in a scratch repo.
- **CI equivalent.** `rm -rf docs-site/node_modules`, then `PYTEST_ADDOPTS=-rs pixi run --frozen -e pyforge-herald
  pyforge-herald-test`: `npm ci` in the `site` env ("added 361 packages ... in 3s"), then 2068 passed and 5 skipped,
  exit 0, 2 min 36 s wall. On the final tree, the same command: "added 361 packages ... in 4s", 2069 passed, 5 skipped,
  exit 0 (171.3 s of pytest). The five skips are the live spikes (`HERALD_LIVE_WEBHOOK`, `HERALD_LIVE_DESIGN`).
- **Loud.** `pixi run --frozen --skip-deps -e pyforge-herald pyforge-herald-test` with no install: exit 1, 13 failed
  and 12 errors (the module fixtures that build), 25 in all, each naming the install; no node stack trace. Before
  `require_astro`, the 12 errors carried node's `Cannot find module .../astro.mjs`.
- **The refutation.** `gate_dep_hang_probe.py` gave `pyforge-herald-coverage-gate` the install dependency in a scratch
  repo with the real workflows and committed a `scripts/coverage_gate.py`-only diff. The reader selected the gate's lane
  and not the install, and `run_preflight` with an injected runner was still running after 30 s.
- **AC7.** Each mutation failed its named tests, and every file was restored byte for byte (`filecmp`, then `md5sum
  -c`):
  - the install dependency dropped: 2 failed (the task test's `pyforge-herald-test` case and AC4's test);
  - `HERALD_DOCS_SITE_REQUIRED` dropped: 1 failed;
  - `site` dropped from the job's `environments`: 1 failed;
  - the required branch skipping: 2 failed (the decorator test and the child pytest);
  - the whole closure again: 2 failed (the equality test and the `sbom-laptop-gate` test).
- **Tests.**
  - The herald suite through its task (AC9): exit 0, 2069 passed, 5 skipped.
  - This story's herald tests with `test_preflight_pages_lane.py`: 17 passed.
  - Steward's suite (`pyforge-steward-test`): the first run after the `pixi.toml` change failed the seven selection
    tests that pin the oracle (each on the extra `docs-site-install`); with the oracle restated, exit 0, 2842 passed,
    2 skipped. Steward's `-k "preflight or docs_site or trigger"` over the trigger map, the docs-site lane meta test
    and the unit tests: 423 passed.
  - `pyforge-core-test` 2484 passed; `pyforge-testing-kit-test` 95 passed; `pyforge-doctor-scripts-test` 1618 passed.
- **Gates.**
  - `pixi run --frozen -e pyforge-guild lint-types`: exit 0, after the last edit.
  - `python scripts/ci_surface_gates.py --check`: exit 0.
  - `pixi run --frozen -e pyforge-guild detectors-ci`: exit 0.
  - Each of these exited 0, after the last edit: `chain-completeness-check`, `dream-chain-check`,
    `dreams-hygiene-check`, `deferred-work-check`, `ledger-regression-check`, `story-status-check`,
    `chain-currency-sweep-check`, `ad-citation-check` (after qualifying this spec's two citations of steward's
    capability as `pyforge-steward:CAP-159`), `flag-gate-check`, `tea-playwright-check` (after regenerating herald's
    matrix) and `spec-surface-check` (with the memlog reconciles below; no stamp).
  - `llms-full-check` and `scripts/pixi_version_check.py`: exit 0.
  - `docs_pixi_tasks.py --check`: exit 0 after the regeneration (it was stale on the new descriptions).
  - `pixi.lock`: unchanged (`git diff --quiet`). `environment.yaml`: `pixi project export conda-environment -e build`
    is byte-identical (`cmp`).
- **Surface reconcile.** Memlog events on `spec-pyforge-herald` (the tests, `pixi.toml`, the planning files),
  `spec-pyforge-steward` (two passes: the docs-site lane meta test, the workflow, then the selection test),
  `spec-pyforge-doctor` (`docs/how-to/pixi-tasks.md`, `docs/map.yaml`) and `spec-pixi-candidate-currency`
  (`pixi.toml`): the four Specs `spec-surface-check` named, and herald's own.
- **Not done here.** No commit and no scoped stamp: the orchestrating session stamps `spec-pyforge-herald`,
  `spec-pyforge-steward`, `spec-pyforge-doctor` and `spec-pixi-candidate-currency` from a clean tree after
  committing. The probe was removed. No station's coverage gate was run: the diff touches no module under any
  station's `src/`. The other station suites that a `pixi.toml` change fires in CI (atlas, doctor, marshal, mason,
  scribe, warden) were not run here. The independent review is still to come.

## Review (2026-10-16)

The independent review of `57af743b4f` returned **PASS** with three should-fix findings and two nits (orchestrating
session's scratchpad, `review-45-1.md`, probes `rv451-*`). The coordinating session ruled on should-fix 2. Every
finding is resolved in one unit on `1c0010dc36` (`57af743b4f` merged with `main`).

- **1 (should-fix): `estate verify --lane pyforge-herald-test` went red.** It ran the lane alone, `--skip-deps`, in a
  fresh worktree, so the task's variable failed the 25 tests. **Resolution:** the redesign keeps the plain task
  dependency-free and variable-free, so that run skips them again; and `estate_verify._with_dependencies` now runs a
  filtered lane's dependency closure first (`pages-build` after `docs-site-install`). AC8's test covers it.
- **2 (should-fix; operator ruling): the laptop gate pulled in npm.** `pyforge-station-tests` and `sbom-laptop-gate`
  reached `docs-site-install@site` through `pyforge-herald-test`'s new dependency, against fnd:CAP-13 and the
  won't-do `feature:site` row. **Resolution:** the redesign under Approach: `pyforge-herald-test` stays npm-free, CI
  runs the cmd-less `pyforge-herald-test-built` strictly, `pr-preflight-lanes` declares the install, and the touched
  cut keeps it. AC1's tests pin both aggregates' closures. The decision is on the `spec-python-foundry-cutover`
  memlog.
- **3 (should-fix): the latent preflight hang had no owner.** **Resolution:** steward's `DW-steward-103-6-1` already
  named it (Story 103.6's review). The row now carries this story's probe, the cause at `1c0010dc36`
  (`preflight.py:849`, `:1242`-`:1251`, `:1294`-`:1297`) and the two fix options: close a full-scope selection over
  `depends_on`, or refuse with `EXIT_CONFIG`. It is not fixed here.
- **Nit 1: the collect-only fallback re-ran `npm ci`.** **Resolution:** it passes `--skip-deps` (AC9). With the plain
  task dependency-free it no longer would, but every lane runs that way.
- **Nit 2: the CI-cost estimate.** **Resolution:** restated as about +1.5-2 minutes plus one cold setup-pixi cache
  (Residual risk).
- **Observation: `pr-preflight-lanes`' dry-run fails** ("could not find the task 'pages-build'"), pre-existing at
  `d21af06fbc`. **Resolution:** steward's `DW-steward-45-1-1`.

## Verification run (2026-10-16, review fixes)

Run on `1c0010dc36` with the review unit in the working tree, then staged. Every verdict is read from its exit code.
Scratch directories are fresh and named `b451-*` (the review's `scratchpad/arch` collision).

- **(a) The laptop gate is npm-free.** `pixi run --as-is --dry-run` lists no task "in site" and no `npm ci`, exit 0,
  for `-e pyforge-foundry-full sbom-laptop-gate`, `-e pyforge-guild sbom-laptop-gate` and `-e pyforge-guild
  pyforge-station-tests`. On `1c0010dc36` before the fix, each listed `docs-site-install in site`. `pyforge-herald-test`
  alone lists no `site` task either. AC1's two closure tests pass.
- **(b) CI's herald job installs and runs strictly.** `pixi run --as-is --dry-run -e pyforge-herald
  pyforge-herald-test-built` lists `docs-site-install in site`, then `pyforge-herald-test`. From no
  `docs-site/node_modules`, `HERALD_DOCS_SITE_REQUIRED=1 PYTEST_ADDOPTS=-rs pixi run --frozen -e pyforge-herald
  pyforge-herald-test-built` ran `npm ci` ("added 361 packages ... in 3s"), then the suite: exit 0, 2074 passed,
  5 skipped (the live spikes), none naming the install. The same command after the last edit: exit 0, 2074 passed,
  5 skipped. Strictness: with the variable and no install, `pixi run --frozen -e pyforge-herald pyforge-herald-test`
  exits 1, 13 failed and 12 errors, each naming the install, no node stack trace. Without the variable it exits 0,
  2049 passed, 30 skipped (25 naming the install): npm-free, as the ruling wants.
- **(c) A herald-only diff in the preflight** (`make_copy.py` and `run_lanes.py`, scratch `b451-driver/`). Fresh
  copies, a `git archive` of `main` (`94a77d724d`) and of `main` plus this story's diff, each committed as its only
  commit with `origin/main` at it, no `docs-site/node_modules`, and only an untracked herald test-tree probe. Each run
  is the copy's own `run_preflight`, over a lane list in the shipped order, with each lane's command run in the
  worktree's installed environment.
  - **The reader on the real `pixi.toml`.** Before: 19 lanes, herald's and the gate, no install. After: 20 lanes,
    `docs-site-install@site` the first docs-site lane declared, herald's lane with no edge. The touched cut keeps the
    install as "pyforge-herald-test@pyforge-herald reads its install".
  - **Before, full scope** (journal `a6a6fa16`, exit 0). 2 of 8 lanes: herald 0.0-130.4 s, 2033 passed, 30 skipped,
    25 naming the install.
  - **After, full scope** (journal `5dfa905f`, exit 0, steward's suite running beside it). 3 of 8 lanes:
    `docs-site-install` 0.0-6.5 s, herald 6.5-260.1 s, 2074 passed, 5 skipped, none naming the install; the gate
    260.1-260.2 s.
  - **After, touched scope** (a third fresh copy; journal `428a96ed`, exit 0). 3 lanes, 0 deferred:
    `docs-site-install` 0.0-3.8 s, herald 3.8-178.2 s, 2074 passed, 5 skipped.
- **(d) 105.1 stays exact.** `DOCS_SITE_TASKS` is unchanged; `test_preflight_docs_site_lanes.py` is byte-identical to
  `main` and passes.
- **AC11 mutations.** Each failed its named tests, and every file was restored byte for byte (`filecmp`, then
  `md5sum -c`): the built task's dependencies swapped (1 failed); the install given back to the plain task (3); the CI
  step's variable dropped (1); the CI step running the plain task (2); the install leg dropped from
  `pr-preflight-lanes` (2); the touched rule off (1); `estate verify` running a filtered lane alone (1); the fallback
  without `--skip-deps` (1); the required branch skipping (2).
- **Tests.** Herald, through CI's task: above. Steward's suite (`pyforge-steward-test`): exit 0, 2845 passed,
  2 skipped, before the planning edits; exit 0, 2845 passed, 2 skipped, after them.
- **Gates.**
  - `lint-types`: exit 0, after the last code edit.
  - `ci_surface_gates.py --check`: exit 0. `detectors-ci`: exit 0.
  - Each exited 0: `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`, `deferred-work-check`,
    `ledger-regression-check`, `story-status-check`, `chain-currency-sweep-check`, `ad-citation-check`,
    `flag-gate-check`, `tea-playwright-check` (after regenerating herald's matrix), `spec-surface-check` (with the
    memlog reconciles; no stamp) and `llms-full-check`.
  - `scripts/pixi_version_check.py`: exit 0. `docs_pixi_tasks.py --check`: exit 0 after the regeneration.
  - `pixi.lock` and `environment.yaml` are unchanged against `main` (`git diff --quiet`), and `pixi project export
    conda-environment -e build` is byte-identical to `environment.yaml` (`cmp`).
- **Surface reconcile.** Memlog events on `spec-pyforge-herald` (decision and reconcile), `spec-pyforge-steward`
  (third pass), `spec-pyforge-core` (co-governor of `preflight.py` and `estate_verify.py`), `spec-pyforge-doctor` and
  `spec-pixi-candidate-currency` (second passes), and `spec-python-foundry-cutover` (the laptop gate stays npm-free).
- **Not done here.** No commit and no scoped stamp: the orchestrating session stamps `spec-pyforge-herald`,
  `spec-pyforge-steward`, `spec-pyforge-core`, `spec-pyforge-doctor` and `spec-pixi-candidate-currency` from a clean
  tree after committing. No probe remains in the worktree. The atlas, doctor, marshal, mason, scribe and warden suites,
  which a `pixi.toml` change fires in CI, were not run here.

## Spec Change Log

- 2026-10-16: minted from the Dream's 2026-10-16 entry and the orchestrating session's brief. `type: fix`, no flag,
  no CAP. Bound to `spec-pyforge-herald` CAP-61. The brief's dependency on `pyforge-herald-coverage-gate` is refuted
  (Rejected).
- 2026-10-16 (implementation): steward's `test_preflight_selection.py` joins the surface, because its oracle pinned
  the lanes herald's job runs; `docs/how-to/pixi-tasks.md` and its `docs/map.yaml` stamp are regenerated; herald's TEA
  matrix is regenerated. No AC changed.
- 2026-10-16 (review): PASS with three should-fix findings and two nits, all resolved (§ Review). The operator ruled
  that the SBOM laptop gate stays npm-free, so the design changes: `pyforge-herald-test` keeps no dependency, the
  cmd-less `pyforge-herald-test-built` is CI's strict run, `pr-preflight-lanes` declares the install, and steward's
  touched cut keeps it. Added: `estate verify` runs a lane's dependencies first; `--skip-deps` on the collect-only
  fallback; two steward deferred-work rows. The ACs are restated (AC1-AC13). Status `done`, in the landing PR.
