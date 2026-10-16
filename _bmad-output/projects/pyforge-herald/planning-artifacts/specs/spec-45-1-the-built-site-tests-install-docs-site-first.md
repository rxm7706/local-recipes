---
title: "45.1: Herald's built-site tests install docs-site first, in preflight and CI"
type: 'fix'
created: '2026-10-16'
status: 'in-review'
baseline_revision: 'd21af06fbc71e4aa91cd9e572c8fa59e9e4c2be6'
flag-exempt: detector-or-gate   # a fix needs no flag (spec-feature-flag-governance Q1: flagging a fix keeps the bug reachable); and herald's suite task is a gate whose silent green this story ends, so a flag-OFF run would report exactly that silent green (Q2's gate exemption), the rule steward 105.1 followed
review_loop_iteration: 0
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

**Approach:** herald's suite task installs docs-site first, and fails, never skips, when the install it promised is
missing.

- **The dependency.** `pyforge-herald-test` and `pyforge-herald-test-coverage` (whose unit suite takes in
  `tests/meta`) get `depends-on = [{ task = "docs-site-install", environment = "site" }]`. That is `npm ci` in
  `docs-site/`, in the `site` environment, so herald's environment gains no package and `pixi.lock` does not move. A
  plain `pixi run -e pyforge-herald pyforge-herald-test` installs first.
- **The preflight joins it with no code change.** `preflight_ci._step_matches` (`preflight_ci.py:455`) matches a lane
  when the task a CI step runs holds it in its `depends-on` closure. The herald job's step runs `pyforge-herald-test`,
  so the reader selects `docs-site-install@site` whenever it selects herald's lane. `list_preflight_lanes` gives
  herald's lane the edge to the install, and `touched_cut` keeps a kept lane's dependencies. 105.1's mutex and
  `_next_lane` then run the install before herald.
- **CI.** The herald job's `setup-pixi` sets up `pyforge-herald site`, so the `site` environment is cached beside
  herald's. The task's dependency runs `npm ci` there. The Chromium step and `setup-uv` are unchanged: Astro needs
  only node, which both environments carry.
- **A missing install is a red test.** Both tasks set `HERALD_DOCS_SITE_REQUIRED=1`. Under it,
  `pages_astro.needs_astro` fails a built-site test whose install is missing, naming the install. A build helper
  (`astro_build`, and `test_agent_surface_and_changes.py`'s builder) calls `require_astro()` first, so a module fixture
  that builds before its tests reports the same cause, never node's stack. Without the variable (a bare `pytest`, or
  CI's coverage leg, which runs its driver and not the task) the tests skip, naming the command, as before.
  `test_agent_surface_and_changes.py` uses `pages_astro`'s one marker.
- **Steward's docs-site lane meta test.** `test_preflight_docs_site_lanes.py` derives `preflight.DOCS_SITE_TASKS`
  from five rules. Its install rule read a task's whole `depends-on` closure, which now reaches `docs-site-install`
  from `sbom-laptop-gate` through the cmd-less `pyforge-station-tests` and herald's suite. That task's own command never
  touches `docs-site/`. The rule now follows a lane's own edges, an aggregate without a `cmd` expanded to its own, as
  `preflight` builds them. The declared set does not change.
- **Steward's selection oracle.** `test_preflight_selection.py`'s oracle maps each workflow job to the lanes it runs.
  Herald's job now runs `docs-site-install` too (its step's task depends on it), so the oracle adds the install when
  herald's output is true, and the `pixi.toml` and Dream-only cases expect it. The `pixi.toml` case still refuses
  `pages-build` and `pages-check`: `pages.yml` does not fire.
- **The generated pixi-tasks page.** The two task descriptions change, so `docs/how-to/pixi-tasks.md` and its stamp
  in `docs/map.yaml` are regenerated (`docs-pixi-tasks`; its `--check` had gone stale).
- **Unchanged.** `preflight.py`, `preflight_ci.py`, `DOCS_SITE_TASKS`, the pre-push hook, `pixi.lock`,
  `environment.yaml`, coverage-gates.yml and pages.yml.

**Rejected:**
- **A dependency on `pyforge-herald-coverage-gate`** (the brief's choice, refuted). coverage-gates.yml's matrix step
  runs `python scripts/coverage_gates_ci.py`, not the task, so the reader matches the gate's lane by its command line,
  and that match brings no dependency. On a diff of `scripts/coverage_gate.py` alone (the coverage gates' shared
  surface, which fires every station's gate and not herald's job), the reader selects the gate's lane without the
  install. A lane whose dependency lane is not in the run never becomes ready, and the scheduler loop spins. The probe
  `gate_dep_hang_probe.py` (scratch) ran `run_preflight` over such a repo with an injected runner: still running
  after 30 s. The gate runs herald's tests only when the branch touches a herald module, and then herald's job fires
  and the install runs first anyway.
- **Making the preflight close over dependencies in a full-scope run.** That is the general cure for the hang above,
  but it changes steward's runner (`pyforge-steward:CAP-159`) for a lane this story does not need. It is named under
  Residual risk.
- **Failing under `CI`, as atlas's `WASM_SMOKE_REQUIRED or CI` does.** CI's coverage leg runs herald's unit suite,
  `test_docs_site_nav.py`'s built-site test included, through its driver with no install. Under `CI` that leg would go
  red. The variable belongs to the task that promises the install.
- **Failing under a `PYFORGE_PREFLIGHT_*` variable.** The preflight sets none in a lane's environment. Its herald
  lane runs the task, so the task's variable already holds there.
- **Installing in a CI step** (`pixi run -e site docs-site-install` before the test step). It would fix CI alone,
  and a plain local `pixi run` would still skip.
- **Adding nodejs and npm to herald's own feature.** It already carries nodejs. The `site` environment owns the
  install, as every docs-site task does.

Ledger key: `45-1-the-built-site-tests-install-docs-site-first`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-herald` CAP-61 (one generator renders the whole Pages site). Its success says
  `pyforge-herald-test` is green, and the built-site tests are its evidence. This story restores that oracle, so it
  mints no CAP and changes no `SPEC.md` text.
- **Works with.** `pyforge-steward:CAP-159` (`spec-pyforge-steward`): the preflight's selection (Story 71.2) and its
  docs-site mutex and order (Story 105.1). Steward's code does not change.
- **Governance.** `pixi.toml` is shared surface. `pyforge-station-tests.yml` and steward's tests are on
  `spec-pyforge-steward`'s surface, and herald's tests on `spec-pyforge-herald`'s.
- **Flag.** None: under `spec-feature-flag-governance` Q1 a `fix` needs no flag. The spec also carries
  `flag-exempt: detector-or-gate`, because herald's suite task is a gate.
- **Origin.** `docs/dreams/pyforge-herald.md`, Realization log, the 2026-10-16 entry (the built-site tests skip
  silently), and steward Story 105.1's residual risk ("A herald-only diff does not select `docs-site-install`").

## Acceptance Criteria

- **AC1: the suite tasks install first.** `pyforge-herald-test` and `pyforge-herald-test-coverage` each have
  `depends-on = [{ task = "docs-site-install", environment = "site" }]` and `env.HERALD_DOCS_SITE_REQUIRED = "1"`;
  `docs-site-install` is `npm ci` with `cwd = "docs-site"`.
- **AC2: the gate takes no dependency.** `pyforge-herald-coverage-gate` has no `depends-on` and no
  `HERALD_DOCS_SITE_REQUIRED`.
- **AC3: CI runs them.** The herald job's `setup-pixi` sets up `pyforge-herald` and `site`, and its run step is `pixi
  run --frozen -e pyforge-herald pyforge-herald-test`, by task name.
- **AC4: the preflight selects the install.** In a scratch repo carrying the real workflows and `pixi.toml`, a branch
  that touches only a herald test-tree file gets both `pyforge-herald-test@pyforge-herald` and
  `docs-site-install@site` from `select_lanes`, and not `pages-check`. Herald's lane depends on the install, and
  `touched_cut` keeps the install because herald's lane depends on it.
- **AC5: a required, missing install is red.** `requires_astro(ready=False, required=True)` makes a test that fails
  with pytest's `Failed`, naming `HERALD_DOCS_SITE_REQUIRED` and the install, and keeps the test's fixture
  parameters. `required=False` makes a `skip` mark naming the install, and `ready=True` leaves the test unchanged. In a
  child pytest the two give `1 failed, 1 skipped`. `astro_build` with `RENDER_READY` false fails naming the install.
- **AC6: steward's set is still derived, and its oracle agrees.** `test_preflight_docs_site_lanes.py` passes. The
  install rule sees herald's two suite tasks, and `sbom-laptop-gate`, whose closure reaches the install only through
  other lanes, is not derived. `test_preflight_selection.py`'s oracle selects the install wherever herald's job fires,
  and equals the reader's selection on every parametrized diff.
- **AC7: mutation.** Each change below fails the named test (recorded under Verification run):
  - the install dependency dropped from `pyforge-herald-test` (AC1, AC4);
  - `HERALD_DOCS_SITE_REQUIRED` dropped from it (AC1);
  - `site` dropped from the herald job's `environments` (AC3);
  - `needs_astro`'s required branch skipping instead of failing (AC5);
  - the install rule reading the whole closure again (AC6).
- **AC8: the proof.** On a tree with no `docs-site/node_modules` and an untracked herald probe, through
  `run_preflight`'s own selection, the run selects `docs-site-install`, runs it before herald, and herald reports no
  skip naming the install. A plain `pixi run --frozen -e pyforge-herald pyforge-herald-test` from the same state runs
  `npm ci` and then the suite, with no such skip.
- **AC9: green, and the surface reconciled.** These exit 0: `pixi run --frozen -e pyforge-herald
  pyforge-herald-test`; steward's preflight, docs-site lane and trigger-map tests; `lint-types`;
  `ci_surface_gates.py --check`; the planning detectors. `pixi.lock` is unchanged and `environment.yaml` re-exports
  byte-identical. Each changed governed path gets a reconcile entry on the memlog of every Spec that governs it, and
  the scoped stamps are taken after the commit.

## Boundaries & Constraints

**Always:**
- Keep the install a dependency of the task, so every caller of the task (CI, the preflight, a person) gets it.
- Keep `needs_astro` declared once, in `pages_astro.py`.
- Keep a missing install loud under the task and quiet without it: only the task promises it.

**Never:**
- Never change `preflight.py`, `preflight_ci.py`, `DOCS_SITE_TASKS`, `pixi.lock`, `environment.yaml` or the pre-push
  hook.
- Never give `pyforge-herald-coverage-gate` a dependency the preflight's reader would not select with it.
- Never weaken an existing assertion.

**Residual risk:**
- **The preflight hangs on a selected lane whose dependency lane is not selected.** It is latent on the shipped graph:
  every lane with a dependency today is selected through a CI step whose task's closure holds that dependency. The
  next `depends-on` on a lane matched by its command line (as the gate's is) would make it reachable. The cure is
  steward's: close a full-scope selection over dependencies, as `touched_cut` already does, or refuse the run with
  the config exit code. Recorded for steward; not fixed here.
- **CI's coverage leg still skips the built-site tests.** It runs `coverage_gates_ci.py`, not the task, and installs
  no docs-site, so the one built-site test in herald's unit suite and the meta ones it takes in skip there.
  The herald job runs them, and their coverage contribution to herald's modules is nil: Astro builds in a child
  process.
- **A preflight-reduced herald lane does not carry the variable.** On a committed herald diff the suite reduction
  runs pytest's argv, not the task, so `HERALD_DOCS_SITE_REQUIRED` is unset there. The install lane still runs first,
  so the tests run; only the loud failure is lost in that lane.
- **Herald's suite now needs the npm registry.** `npm ci` downloads unless npm's cache holds the packages. The pytest
  run itself stays offline, behind `tests/conftest.py`'s egress fixture.
- **CI cost.** About 10 s more set-up and install, and about 60-80 s of Astro builds, on a job of about 2 minutes
  (measured under Verification run).

## I/O & Edge-Case Matrix

| Situation | Today (`d21af06fbc`) | After |
|---|---|---|
| herald-only diff, fresh worktree, preflight | herald alone; 25 built-site tests skip | the install, then herald; the 25 run |
| CI herald job | `pyforge-herald` only; the 25 skip | `pyforge-herald site`; `npm ci`, then the 25 run |
| plain `pixi run -e pyforge-herald pyforge-herald-test`, no install | the 25 skip | `npm ci`, then the 25 run |
| the task under `--skip-deps`, no install | the 25 skip | the 25 fail or error, each naming the install |
| bare `pytest` over herald's tests, no install | the 25 skip | the 25 skip (unchanged) |
| CI coverage leg (herald) | built-site tests skip | unchanged |
| a `scripts/coverage_gate.py`-only diff, preflight | the gate's lane alone | unchanged (no dependency to strand) |
| a diff that fires `pages.yml` too | the install first (105.1) | unchanged |
| `sbom-laptop-gate`'s place in the docs-site set | out | out (the install rule follows lane edges) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-herald` CAP-61 (one generator renders the whole Pages site). No CAP is minted,
  and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-16 entry (the built-site tests skip
  silently).
- Epic: Epic 45 (new; Epic 44 is `done` and its theme is the docs shelf).
- Ledger key: `45-1-the-built-site-tests-install-docs-site-first`.
- Ledger status at mint: `in-progress`.
- Deps: none. Steward Story 105.1 (PR #2242) is this branch's base.
- Spec: the `spec-pyforge-herald` memlog records the evidence, the design, the refutation and the surface reconcile.
- Surface: `marshal-policy.toml` `[epic_surfaces]."45"`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass, with no skip naming the docs-site
  install. This is the station's `verify_commands` (MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `PYTEST_ADDOPTS= pixi run --frozen -e pyforge-herald pytest
  src/shared/packages/pyforge-herald/tests/meta/test_built_site_tests_install_first.py
  src/shared/packages/pyforge-herald/tests/meta/test_preflight_pages_lane.py -q` — expected: exit 0 (AC1-AC5).
- `PYTEST_ADDOPTS= pixi run --frozen -e pyforge-steward pytest
  src/shared/packages/pyforge-steward/tests/meta/test_preflight_docs_site_lanes.py
  src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q` and `-k preflight` over
  steward's unit tests — expected: exit 0 (AC6).
- The AC7 mutations, one at a time, each re-running its named test — expected: each fails it; the file is restored
  byte for byte.
- The proof (AC8): with `docs-site/node_modules` removed and an untracked
  `src/shared/packages/pyforge-herald/tests/unit/preflight_probe.py`, `pixi run --frozen -e pyforge-guild python
  herald_lanes_run.py <repo> <scratch pixi.toml>` runs `preflight.run_preflight` over a scratch copy whose
  `pr-preflight-lanes` names only `pyforge-herald-test`, `pyforge-herald-coverage-gate`, `pages-check` and
  `docs-site-validate`. Then `PYTEST_ADDOPTS=-rs pixi run --frozen -e pyforge-herald pyforge-herald-test` from the
  same state. Remove the probe after.
- `pixi run --frozen -e pyforge-guild lint-types`, `python scripts/ci_surface_gates.py --check`, the planning
  detectors, `llms-full-check`, `pixi-version-check` and the `environment.yaml` export check — expected: exit 0.

## Verification run (2026-10-16)

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

## Spec Change Log

- 2026-10-16: minted from the Dream's 2026-10-16 entry and the orchestrating session's brief. `type: fix`, no flag,
  no CAP. Bound to `spec-pyforge-herald` CAP-61. The brief's dependency on `pyforge-herald-coverage-gate` is refuted
  (Rejected).
- 2026-10-16 (implementation): steward's `test_preflight_selection.py` joins the surface, because its oracle pinned
  the lanes herald's job runs; `docs/how-to/pixi-tasks.md` and its `docs/map.yaml` stamp are regenerated; herald's TEA
  matrix is regenerated. No AC changed.
