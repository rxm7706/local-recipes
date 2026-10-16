---
title: '107.1: A stranded preflight lane is refused, and pr-preflight-lanes resolves under pixi'
type: 'fix'
created: '2026-10-16'
status: 'done'
baseline_revision: '2ca62dbca09624fa3a8231123101acaf7c95f1d1'
flag-exempt: detector-or-gate   # a fix needs no flag (spec-feature-flag-governance Q1), and pr-preflight is a gate: a flag-OFF run would keep the spin reachable (Q2's gate exemption), as 105.1 and 106.1 recorded
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-88-1-the-preflight-runs-each-task-once-after-its-dependencies.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-6-a-touched-scope-preflight-leaves-the-other-lanes-to-ci-and-verify-deferred-catches-up.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-105-1-the-preflight-never-runs-two-docs-site-lanes-at-once.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-45-1-the-built-site-tests-install-docs-site-first.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - pixi.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a preflight lane can lose a dependency it needs, in the runner and under pixi. Line numbers are at
`2ca62dbca0` (herald Story 45.1's branch tip, PR #2244).

- **The stranded lane (`DW-steward-103-6-1`).** `run_preflight` builds every lane from `pr-preflight-lanes` with its
  dependency edges (`Lane.depends_on`), then keeps the lanes CI's rules select (`preflight.py:1074` with the CI pause
  flag on, `:1095` without), drops the paused ones (`:1092`), and in a touched run keeps only the cut and the fast core
  (`touched_cut`, `:342`). A lane whose dependency is not in that set is never ready (`_deps_all_ok`, `:849`, wants
  every dependency `ok`) and never blocked (`_mark_dependency_blocked` skips a lane while any dependency has no result,
  `:1245`). With no future in flight, `if not futures:` (`:1294`-`:1297`) `continue`s with no wait.
- **The fast core (`DW-steward-103-6-2`).** `_fast_core_lanes` (`:331`) builds the five fast-core detectors with their
  own dependency closure, and `touched_cut` keeps only the extras not already among the run's lanes (`:390`). A
  fast-core task that depends on a lane the cut deferred would run without it: the same stranded lane.
- **The pixi task (`DW-steward-45-1-1`).** `pixi run -e pyforge-guild pr-preflight-lanes` is the serial reference
  Story 71.1 kept. Its `{ task = "pages-check", environment = "site" }` leg (`pixi.toml:1621`) depends on the bare
  `pages-build` (`:980`). Pixi looks a bare `depends-on` entry up in the environment the run was invoked in, where the
  `site` feature's tasks do not exist. `pages-build` (`:975`), `docs-site-build` (`:970`), `docs-site-validate-sidebar`
  (`:993`) and `docs-site-validate` (`:997`) name bare dependencies too. The runner is unaffected: `_resolve_dep`
  (`preflight.py:220`) gives a bare entry its dependent's environment.

**Where CI's selection can strand a dependency** (read in `preflight_ci.py` at the base; the orchestrator's review
ruling, checked against the code):

- `_step_matches` (`:455`) matches a `pixi run W` step to every lane whose task is in `_closure(pixi_data, W)` (`:322`),
  and that closure is transitive. A dependent selected through a task match therefore has every dependency selected
  by the same step: one site, one job condition, one matrix leg (`_State._site`).
- `discover_paused_lanes` (`:754`) marks a lane paused only when it is unselected with the pause and selected without
  it. A dependency the dependent's unpaused step matches is selected with the pause on, so it is never paused while
  its dependent runs.
- That leaves four ways in: a dependent CI's reader matches by its own command line (`_step_matches`' second branch;
  `coverage-gates.yml:202` runs `python scripts/coverage_gates_ci.py`, not the gate task); a lane no CI step runs at
  all, which `_outcome` (`:1234`) selects as "no CI counterpart … (always runs)"; after the touched cut, which already
  keeps a kept lane's dependencies from the selected lanes, a dependency of a fast-core detector; and
  `--ignore-ci-pauses` *(added at re-review, 2026-10-16)*. The selection is read with the pause applied, so a paused
  lane and the dependency its `pixi run` step runs with it are both left out, and the flag re-adds only the lanes
  `discover_paused_lanes` returns, which are only lanes a `docs/governance/ci-surfaces.yaml` row names as a local twin
  (`_registry_row_for_lane`, `:694`); a dependency with no such row stays out. In each, nothing in CI runs the lane
  with the dependency: CI runs the first three without it, and runs neither the paused lane nor its dependency.
- On the shipped graph none is reached: the three lanes with a dependency (`pages-build`, `pages-check`,
  `docs-site-validate-sidebar`) are each matched by a `pixi run` step, the lanes matched only by their command line
  (the eight coverage gates) or by nothing (`detectors-ci`, `docs-map-render-test`, `docs-gen-test`) have no
  `depends-on` (scratchpad `sites_probe.py` over the live workflows), and no `local_twin` row names a preflight lane,
  so `--ignore-ci-pauses` re-adds nothing (the re-review).

**Measured at `2ca62dbca0`** (16 logical cores; pixi 0.81.0; every exit code read directly):

- **The spin, full scope.** A fixture `pixi.toml` with lanes `b`, `a` (depends on `b`) and `detectors-ci`, the CI
  pause flag off, and a selection of `a` alone, run through the real `run_preflight` with an injected runner
  (scratchpad `probe_stranded.py full`): still running after 8 s, 7.96 s of user time in 8.03 s of wall time, until
  `timeout -s INT` ended it. Its stderr stopped at `preflight: running 1 of 3 lanes, 2 skipped by their workflow's own
  rules` and `scope full`; no lane ran.
- **The spin, touched scope.** The same fixture with `flag-gate-check` depending on `b` and a diff that touches no
  lane (`probe_stranded.py fastcore`): the cut deferred `b`, `a` and `detectors-ci`, the fast core ran four of its
  five detectors, `flag-gate-check` never started, and the run spun until SIGINT (7.98 s user in 8.03 s; exit 130).
- **On the shipped graph** both are latent: herald 45.1's review swept 1100 one-path diffs and every pause combination
  and found no selection that strands a dependency (the DW row's `verified:` line).
- **The pixi task.** `pixi run --as-is --dry-run -e pyforge-guild pr-preflight-lanes` in this worktree: exit 1,
  `× could not find the task 'pages-build'`. `pixi run --as-is --dry-run -e site pages-check`: exit 0, three tasks
  (`docs-site-install`, `pages-build`, `pages-check`, all in `site`); `… -e site docs-site-validate`: exit 0, four tasks
  (`docs-site-validate-links`, `docs-site-install`, `docs-site-validate-sidebar-order`, `docs-site-validate-sidebar`).
- **Pixi's lookup rule, measured** (scratchpad `stepwise2.py`, a scratch copy of `2ca62dbca0` made with `git archive`,
  each `site` task's entries made explicit one task at a time, pixi's own dry-run after each):

  | State | pixi 0.81.0 | The walk this story's test does (first pair named) |
  |---|---|---|
  | as committed | exit 1, `pages-build` | `pages-build@pyforge-guild`, named by `pages-check@site` |
  | `pages-check` fixed | exit 1, `docs-site-validate-links` | `docs-site-validate-links@pyforge-guild` |
  | `pages-build` fixed too | exit 1, `docs-site-validate-links` | `docs-site-validate-links@pyforge-guild` |
  | `docs-site-validate` fixed too | exit 1, `docs-site-install` | `docs-site-install@pyforge-guild`, named by `docs-site-validate-sidebar@site` |
  | `docs-site-validate-sidebar` fixed too | exit 0 | nothing |
  | `docs-site-build` fixed too | exit 0 | nothing |

  After the second step pixi did not report `pages-build`'s bare `docs-site-install`, which was still missing: it
  walks breadth-first, so `docs-site-validate`'s legs, a level up, come first. That is how the walk was found to be
  breadth-first.

**Approach:** a run that would strand a lane is refused, never widened, and the `site` tasks name their environment.

- **No stranded lane reaches the pool.** After the touched cut, fast core included, and before any `pixi install` or
  lane, `stranded_dependencies(lanes)` names each lane that depends on a lane outside the run. If there is one, the run
  prints, for each stranded lane, `preflight: <lane>@<env> runs (<why>) but depends on <dep>@<env>, which this run
  does not run`, a line on what CI does with the lane, and a `fix:` line, then `preflight: refusing the run before any
  install or lane starts`, and returns `EXIT_CONFIG` (2), journaling nothing, as every config refusal does.
  `stranded_lane_message` builds the lines:
  - `<why>` is the lane's selection verdict reason (for a touched run's kept lane too); for a fast-core detector, the
    cut's reason (`fast core, in place of detectors-ci@<env>`); for a lane `--ignore-ci-pauses` re-added, which has no
    selected verdict, its pause (`paused in CI (<switch> since <date>, review_by <date>), re-added by
    --ignore-ci-pauses`). `run_preflight` picks one of three kinds (`STRANDED_SELECTED`, `STRANDED_FAST_CORE`,
    `STRANDED_PAUSE_IGNORED`) from the cut, the verdicts and the paused lanes the flag re-added.
  - A lane CI's reader matched by its command line: `CI runs <task>'s command without <deps>: the step that selects it
    runs the command, not \`pixi run <task>\`, which is what runs a task's dependencies`, and `fix: make the CI step
    run \`pixi run <task>\`, or drop <task>'s depends-on`.
  - A lane no CI step runs (its reason opens with `NO_CI_COUNTERPART`, pinned against `preflight_ci._outcome`):
    `no CI step runs <task>, so CI never runs it, with <deps> or without`, and, since there is no step to change,
    `fix: add a CI step that runs \`pixi run <task>\`, or drop <task>'s depends-on` *(the re-review's nit)*.
  - A lane `--ignore-ci-pauses` re-added: `<deps> is held back by the same pause, and --ignore-ci-pauses re-adds only
    the lanes docs/governance/ci-surfaces.yaml names as a local twin`, and `fix: name <deps> as the local twin of its
    surface's docs/governance/ci-surfaces.yaml row, or run without --ignore-ci-pauses`. Which lanes the flag re-adds
    does not change *(added at re-review)*.
  - A fast-core detector: `CI runs <task> inside detectors-ci (scripts/detectors.py), never as \`pixi run <task>\`, so
    never with <deps>`, and `fix: drop <task>'s depends-on, or take <task> out of FAST_CORE_TASKS`.
  The scheduler loop is not restructured: the refusal makes the spin unreachable. With nothing stranded the run set,
  its order, its stderr and the journal are what they were at the base.
- **The `site` tasks name their environment on their own dependencies.** In `pixi.toml` every `depends-on` entry of a
  `[feature.site.tasks.*]` task becomes `{ task = "<name>", environment = "site" }`, as herald 45.1's
  `pyforge-herald-test-built` does, with a comment that says why. The sweep of `pr-preflight-lanes`' whole closure (the
  new meta test's walk) found no other entry pixi cannot resolve. `preflight_ci._closure` and the runner read both
  forms the same way, so the selection and `list_preflight_lanes` do not move.
- **Pinned by a test that reads `pixi.toml` the way pixi does.** `tests/meta/test_pr_preflight_lanes_resolve_under_pixi.py`
  walks `pr-preflight-lanes` from `pyforge-guild` by pixi's rule, measured above: a bare entry in the invoking
  environment, an explicit one in its named environment, an environment's features from `[environments]` with the
  default feature unless `no-default-feature`, breadth-first. It fails naming every `(task, environment)` pair that does
  not exist. It also rebuilds the old shape from the live tree and pins that the walk stops first at `pages-build`,
  where pixi did, and that `-e site pages-check` and `-e site docs-site-validate` resolve, as pixi's did. It
  cross-checks the walk against `list_preflight_lanes`: the same 36 pairs.
- **The herald coverage gate's stated reason.** Herald 45.1 kept `pyforge-herald-coverage-gate` free of an install
  dependency because "the run hangs". The rule stands for a reason that survives this story: CI's matrix step runs the
  script, not the task, so CI never runs the install with the gate, and a `depends-on` there would now be refused
  (exit 2). The `pixi.toml` comment and the docstring of herald's `test_the_coverage_gate_takes_no_install_dependency`
  say so.

**Rejected:**
- **Pull the missing dependency in, as `pixi run` does** (`DW-steward-103-6-1`'s option (a); this story's first cut,
  commit `043eed5557`). Everywhere it fires, nothing in CI runs the lane with that dependency (above), so it would run
  locally what CI does not, and the dependent would see the dependency's output where CI's step never does: a CI red
  could pass locally. Dropped by the orchestrator's review ruling, 2026-10-16.
- **`_mark_dependency_blocked` journals a dependency absent from the run as blocked** (the row's first follow-up). The
  dependent would never run, and the run would read green or `not-run` where CI runs the lane.
- **`_fast_core_lanes` refuses a fast-core task that has dependencies** (`DW-steward-103-6-2`'s follow-up). It refuses
  even when the dependency is not among the run's lanes, where `_fast_core_lanes` already brings it; the general
  refusal covers the one case that strands.
- **Restructuring the scheduler loop** (a sleep or a deadlock check in `if not futures:`). It would hide the cause; the
  refusal removes it.
- **Saying in `pr-preflight-lanes`' description that it is a graph for the runner only** (`DW-steward-45-1-1`'s second
  option). The task is the serial reference, and it should run.

Ledger key: `107-1-a-stranded-preflight-lane-is-refused-and-pr-preflight-lanes-resolves-under-pixi`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159: the preflight runs the lanes a PR gates on, each after its own
  dependencies (Story 88.1), selected from CI's rules (Story 71.2), with CI pauses (Story 99.5) and a touched scope
  (Story 103.6). This story refuses the one run shape in which a lane could never start. It mints no CAP and changes
  no `SPEC.md`.
- **Governance.** `preflight.py` and the two new tests are on `spec-pyforge-steward`'s surface, `preflight.py` also on
  `spec-pyforge-core`'s (every station's `src/`); `pixi.toml` has the co-governors `spec-surface-check` names; herald's
  four meta tests are on `spec-pyforge-herald`'s.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag; the frontmatter records
  `flag-exempt: detector-or-gate` (pr-preflight is a gate).
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, the 2026-10-16 (a selected lane strands its dependency)
  entry; `DW-steward-103-6-1`, `DW-steward-103-6-2`, `DW-steward-45-1-1`.

## Acceptance Criteria

AC1-AC6 run the real `run_preflight` or `stranded_dependencies` over fixture `pixi.toml`s, with an injected lane
runner and, where a run needs one, a monkeypatched selection, each under Story 105.1's hang guard; a refused run's
install and lane runner raise if reached. AC7 reads the live `pixi.toml`. No test runs pixi.

- **AC1 — The check.** `stranded_dependencies` names each lane and each of its missing dependencies, returns nothing for
  a run that holds every dependency, and treats a lane as its task and its environment (Story 103.5). The no-counterpart
  prefix the message keys on is the one `preflight_ci._outcome` gives.
- **AC2 — Full scope.** CI's reader selects `app` by its command line and drops `build`, which `app` depends on: exit
  2, no install, no lane, no journal; stderr ends with exactly the three lines for `app` (why, the command-line case,
  the fix) and the refusal line.
- **AC3 — A paused dependency.** With the CI pause flag on and `install` paused alone, `app` (selected, depends on
  `install`): refused after the pause banner, before any install, naming `install`. *(Added at re-review:)* with
  `--ignore-ci-pauses`, a paused `app` the flag re-adds while its paused dependency `install` stays out (no local-twin
  row): refused with exactly the pause-ignored lines (the pause in the why, the same pause holding `install` back, the
  local-twin fix); and the line agrees in number with two missing dependencies.
- **AC4 — Touched scope.** The diff touches `app`, which the cut keeps; the selection dropped `build`: refused with the
  same lines as AC2.
- **AC5 — The fast core.** A touched run whose fast-core `flag-gate-check` depends on `build`, which the cut deferred:
  refused, naming the fast-core reason, detectors-ci and the fast core's two fixes; no install, no lane, no journal.
- **AC6 — Nothing stranded.** A run whose dependencies are all selected (`lint`, skipped, has no dependent): the run
  set and order, the whole stderr, and both journal records (the install record and the run record, with only the run's
  identity, the checkout's head, the clocks and the host left out) equal a pinned copy, which passes against the base
  revision's `preflight.py` too. A lane no CI step runs gets its own explanation line and an "add a CI step" fix.
- **AC7 — The pixi graph.** The meta test's walk of `pr-preflight-lanes` from `pyforge-guild` finds every pair; finds
  the same pairs `list_preflight_lanes` builds; on the old `site` shape, rebuilt from the live tree, names
  `pages-build@pyforge-guild` (named by `pages-check@site`) first, then the two `docs-site-validate` legs, and resolves
  `pages-check` and `docs-site-validate` from `site`; every `site` task's `depends-on` entry names `site`; `pixi.toml`
  declares no platform tasks and no `depends_on` key the walk does not read; and three fixture tests pin the rule
  (bare entries in the invoking environment, breadth-first; the default feature unless `no-default-feature`; an entry
  without an environment is bare).
- **AC8 — Mutation.** Each change below fails a named test, and the Implementation Result records which: no refusal;
  the refusal after the install; the check before the touched cut; the environment ignored in the check; the why left
  out; the fast-core lines for every lane; the command-line lines for a fast-core lane; the no-counterpart branch
  dropped; no `fix:` line; the fast-core why read from the selection; *(added at re-review)* the pause-ignored branch
  dropped, its why replaced by the old fallback string, and the no-counterpart fix line back to "make the CI step
  run"; and in the walk: a bare entry in its dependent's environment, depth-first, the default
  feature always, an explicit environment ignored; and `pixi.toml`'s `site` entries back to bare names.
- **AC9 — The real tree.** `pixi run --as-is --dry-run -e pyforge-guild pr-preflight-lanes` exits 0 with 36 tasks;
  `-e site pages-check` and `-e site docs-site-validate` exit 0 and list the same tasks, in the same order, as before;
  `list_preflight_lanes` on the live `pixi.toml` gives the same lanes, order and edges as at `2ca62dbca0`; `pixi.lock`
  and `environment.yaml` do not change.
- **AC10 — Green, the surface reconciled.** `pixi run --frozen -e pyforge-steward pyforge-steward-test`, herald's
  suite, `lint-types` and the steward coverage gate exit 0; each changed governed path gets a surface-reconcile entry
  on the memlog of every Spec that governs it.

## Boundaries & Constraints

**Always:**
- Keep CI's selection what it is: the run is refused, never widened, and the journal's `selected` and `skipped` lists
  stay CI's.
- Keep the scheduler loop as it is; keep the exit codes (`EXIT_CONFIG` is the code every config refusal already uses).

**Never:**
- Never change a dependency, a version, `pixi.lock` or `environment.yaml`; never move a lane in `list_preflight_lanes`.
- Never weaken or delete an existing assertion: herald's three meta tests restate the `site` tasks' `depends-on` in
  the new shape, entry for entry.

**Residual risk:**
- **A `depends-on` on a lane CI matches by its command line now stops every run whose diff strands it.** That is the
  point (the alternative runs what CI does not), and the refusal names both fixes. On the shipped graph no such
  `depends-on` exists: the eight coverage-gate lanes, the only command-line matches, have none.
- **A `depends-on` on a lane no CI step runs is refused too.** CI never runs that lane, so pulling its dependency in
  could not mask a CI red; refusing it costs only the run, and the message says no CI step runs the lane.
  `detectors-ci`, `docs-map-render-test` and `docs-gen-test` are such lanes today, and none has a `depends-on`.
- **`--ignore-ci-pauses` refuses a paused lane whose paused dependency has no local-twin row** *(added at re-review)*.
  The flag's purpose, running what CI pauses, then stops at the refusal until the dependency is named as a local twin
  in its surface's `docs/governance/ci-surfaces.yaml` row, or the run drops the flag. Widening what the flag re-adds
  is out of scope (the ruling: which lanes it re-adds does not change). Today no `local_twin` row names a preflight
  lane, so the flag re-adds nothing.
- **A fast-core task with a dependency refuses touched runs.** `_fast_core_lanes` brings a fast-core task's dependency
  when it is not among the run's lanes, so the refusal fires only when it is and the cut deferred it. Then every such
  touched run exits 2 until the fast-core task drops its dependency or leaves the fast core. None of the five has a
  `depends-on` today.
- **The `--ignore-ci-pauses` lines fit the usual case only** (re-review 2's two optional nits, accepted as latent):
  "held back by the same pause" is false when the re-added lane is matched by its command line in its paused job,
  where its dependency is never selected, paused or not; and "name it as the local twin of its surface's row" would
  displace the lane when that row is the lane's own (the workable form is a second row on the same switch, as
  `PAUSE_PLATFORM_CONTAINER_BUILDS` has). Both need a `local_twin` row naming a preflight lane, and none does today.
  The refusal still fires; only its advice is off.
- **The walk models pixi 0.81.0.** A pixi release that resolves a bare entry in its dependent's environment would make
  the test stricter than pixi, never looser. Platform tasks (`target.<platform>.tasks`) and the `depends_on` key are
  outside the walk; a guard test fails when `pixi.toml` starts to use either. Feature `platforms` restrictions are
  outside it too (the review's note); no feature in the walk's closure declares one that excludes linux-64.

## I/O & Edge-Case Matrix

| Situation | Before (`2ca62dbca0`) | After |
|---|---|---|
| full run, CI's reader keeps `a` by its command line and drops `b`, which `a` depends on | spins with nothing in flight until SIGINT (7.96 s user in 8.03 s) | exit 2 before any install: `a`, why it runs, `b`, CI runs `a`'s command without `b`, the fixes |
| CI pause on the dependency alone, the dependent matched by its command line | spins | exit 2 after the pause banner, naming the paused dependency |
| a lane no CI step runs depends on a lane the selection dropped | spins | exit 2; "no CI step runs" it |
| touched run, a kept lane's dependency dropped by the selection | spins | exit 2, as the full run |
| touched run, a fast-core task depends on a lane the cut deferred | spins (the fast core's other four run) | exit 2, the fast-core reason and fixes |
| `--ignore-ci-pauses` re-adds a paused lane; its paused dependency has no local-twin row | spins | exit 2: the pause, the same pause holds the dependency back, the local-twin fix or drop the flag |
| nothing stranded | the run as it was | unchanged (pinned) |
| `pixi run --as-is --dry-run -e pyforge-guild pr-preflight-lanes` | exit 1, `could not find the task 'pages-build'` | exit 0, 36 tasks, the runner's 36 lanes in the runner's order |
| `pixi run --as-is --dry-run -e site pages-check` / `docs-site-validate` | exit 0: 3 / 4 tasks | exit 0: the same tasks in the same order |
| `list_preflight_lanes` on the live `pixi.toml` | 36 lanes | byte-identical dump |

</intent-contract>

## Binding

- Parent Spec capability: a fix under `spec-pyforge-steward` CAP-159 (the preflight's run contract). No CAP is minted,
  and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-16 (a selected lane strands its dependency)
  entry.
- Epic: Epic 107 (new), Story 107.1; `epic-107` and `epic-107-retrospective` are minted with it. A new epic because
  Epic 106, the last CAP-159 fix, is `done`.
- Ledger key: `107-1-a-stranded-preflight-lane-is-refused-and-pr-preflight-lanes-resolves-under-pixi` (renamed at
  review from `107-1-a-preflight-lane-runs-with-its-dependencies-in-the-runner-and-under-pixi-run`, which never left
  this branch; the sync dropped the old `backlog` key with `--allow-regression`, naming it).
- Ledger status at mint: `backlog`, as 106.1's was while it was in review; `done` in the landing merge, with `epic-107`
  rolled up to `done`.
- Deps: none.
- Closes: `DW-steward-103-6-1`, `DW-steward-103-6-2`, `DW-steward-45-1-1` (`status: closed` on this branch, each with a
  `closed:` line citing this story and its tests).
- Surface: `marshal-policy.toml` `[epic_surfaces]."107"`.
- Flag: none — a fix (`spec-feature-flag-governance` Q1); `flag-exempt: detector-or-gate` recorded above.

## Epic excerpt

Story 107.1 in `epics.md` § Epic 107: a stranded preflight lane is refused, and pr-preflight-lanes resolves under pixi.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`;
  MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest -q src/shared/packages/pyforge-steward/tests/unit/test_preflight_stranded_lane.py src/shared/packages/pyforge-steward/tests/meta/test_pr_preflight_lanes_resolve_under_pixi.py` — expected: 22 passed (AC1-AC7).
- The AC8 mutations, one at a time on a scratch copy (never the worktree), re-running the two files — expected: each
  fails its named tests; the copy restored after each.
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: exit 0.
- `pixi run --as-is --dry-run -e pyforge-guild pr-preflight-lanes` — expected: exit 0 (AC9).
- `pixi run --as-is --dry-run -e site pages-check` and `pixi run --as-is --dry-run -e site docs-site-validate` —
  expected: exit 0, the same task lists as at the base revision (AC9).
- `pixi project export conda-environment -e build`, compared with `environment.yaml` — expected: byte-identical (AC9).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- The steward coverage gate, `COVERAGE_GATES_STATIONS=steward pixi run --frozen -e pyforge-steward python scripts/coverage_gates_ci.py --paths-file <changed paths> --suites unit` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and one scoped stamp per
  Spec (AC10).

## Spec Change Log

- 2026-10-16: minted from the Dream's 2026-10-16 entry and the three DW rows, on the orchestrating session's design.
  `type: fix`, no flag, no CAP; bound to `spec-pyforge-steward` CAP-159. Measured first: the spin in both scopes, and
  pixi's lookup rule at six states.
- 2026-10-16 (implementation): hand-implemented on branch `chain-preflight-stranded-deps-2026-10-16` from
  `2ca62dbca0` as commit `043eed5557`: the selected lanes closed over their `depends-on` (`close_over_dependencies`, a
  `selection.pulled_in` journal key, a paused dependency run anyway), the refusal as the backstop, the `site` tasks'
  environments and the meta test; status `in-review`.
- 2026-10-16 (review): FAIL, two should-fix findings and four nits (scratchpad `r107/review.md`, read against this
  spec at `043eed5557`). (1) The `pixi.toml` comment on `pyforge-herald-coverage-gate` and herald's
  `test_the_coverage_gate_takes_no_install_dependency` docstring gave a reason this story makes false (the run hangs).
  (2) The design's claim that CI's dependent job runs `pixi run <task>`, and so runs the dependency, fails for a lane
  CI's reader matches by its command line, where the closure would run locally what CI does not. Nits: the interrupted
  record's `pulled_in` untested; the stderr skipped count against the journal's `skipped`; the breadth-first
  attribution of a pulled-in lane; no run-level `--ignore-ci-pauses` case.
- 2026-10-16 (the orchestrator's ruling, replacing design item 1): drop the closure, keep the refusal
  (`DW-steward-103-6-1`'s option (b)). Checked against `preflight_ci.py`: a `pixi run` step selects the task's whole
  closure, a dependency its dependent's unpaused step matches is never paused, so the selection strands a dependency
  only where nothing in CI runs the lane with it; the touched cut already keeps a kept lane's selected dependencies,
  which leaves the fast core. The builder found one more such shape, a lane no CI step runs (`_outcome`'s "always
  runs"), where pulling in could not mask a CI red but is not CI's behaviour either; the ruling's refusal applies, with
  a message of its own (reported to the orchestrator). Rewritten to match: `preflight.py` loses the closure, its
  wiring, `selection.pulled_in` and the pulled-in stderr lines, and the refusal names each lane, why it runs, each
  missing dependency, what CI does and the fixes; the unit tests become `test_preflight_stranded_lane.py`; the story is
  retitled and its ledger key, spec file and `marshal-policy.toml` comment follow. Should-fix (1): both rationales now
  say CI's matrix step runs the script, not the task, so CI never runs the install with the gate, and a `depends-on`
  there would be refused (exit 2). Should-fix (2) and the first three nits went with the closure. The fourth nit (no
  run-level `--ignore-ci-pauses` case) was recorded here as gone too; it was not (next entry). The `pixi.toml` `site`
  fix and its meta test are unchanged, as the review found them sound.
- 2026-10-16 (re-review of `42c3ffff5d`): FAIL, one should-fix and one nit (scratchpad `r107/review.md`, "Re-review";
  probe `r107/tools/probe_ignore.py`). (should-fix) `--ignore-ci-pauses` is a fourth way to strand a lane: it re-adds
  only the paused lanes a ci-surfaces.yaml row names as a local twin, so a paused lane's dependency from the same
  paused `pixi run` step stays out when it has no row, and the refusal said "CI runs L's command without P … make the
  CI step run `pixi run L`", false for that step. That is the fourth nit above, which outlived the closure. Fixed: a
  lane the flag re-added gets its own lines (its pause as the why, the same pause holding the dependency back, the
  flag re-adding only local-twin lanes; fix: name the dependency as its surface's local twin, or run without the
  flag), a run-level test pins them, and the four-case list replaces the three-case one here, in the Dream entry,
  Epic 107 and the DW-steward-103-6-1 `closed:` line. Which lanes the flag re-adds does not change. (nit) A lane no CI
  step runs has no step to change: its fix line now reads "add a CI step that runs `pixi run <task>`, or drop <task>'s
  depends-on".

- 2026-10-16 (re-review 2 of `e3c9a61a75`): RESOLVED; both findings fixed. Two optional nits on the
  `--ignore-ci-pauses` lines are accepted as latent and recorded under Residual risk; the reviewer confirmed the
  `KeyError` branch in the refusal's kind lookup is unreachable by construction (every lane in the run is selected, a
  paused lane the flag re-added, or a fast-core extra).
- 2026-10-16 (landing): status `done`; the ledger key and `epic-107` `done`; the three DW rows closed.

## Implementation Result

Hand-implemented on branch `chain-preflight-stranded-deps-2026-10-16`, from baseline `2ca62dbca0`, revised after the
review. The diff is for an independent review against this spec, not against this summary.

- **`preflight.py`:** `stranded_dependencies`, `NO_CI_COUNTERPART`, the three `STRANDED_*` kinds and
  `stranded_lane_message` beside `list_preflight_lanes`; `run_preflight` refuses a stranded lane after `_print_scope`
  and before the install, with each lane's kind and why taken from the cut (a fast-core detector), its selection
  verdict, or the pause of a lane `--ignore-ci-pauses` re-added; the module and `run_preflight` docstrings say so. Against `2ca62dbca0` the file gains only these (no closure, no journal key; the
  scheduler, the selection and the journal code are byte-identical).
- **`pixi.toml`:** the five `site` tasks with a `depends-on` (`docs-site-build`, `pages-build`, `pages-check`,
  `docs-site-validate-sidebar`, `docs-site-validate`) name `environment = "site"` on every entry, under a comment that
  says why; the comment above `pyforge-herald-coverage-gate` restates its reason. No other line changes.
- **Tests (new):** `tests/unit/test_preflight_stranded_lane.py` (AC1-AC6, 12 cases after the re-review) and
  `tests/meta/test_pr_preflight_lanes_resolve_under_pixi.py` (AC7, 10 cases).
- **Herald (cross-station):** `tests/meta/test_docs_site.py` (`docs-site-build`),
  `tests/meta/test_docs_site_validators.py` (`docs-site-validate-sidebar`, `docs-site-validate`) and
  `tests/meta/test_one_generator.py` (`pages-check`) expect the explicit entries;
  `tests/meta/test_built_site_tests_install_first.py`'s `test_the_coverage_gate_takes_no_install_dependency` docstring
  restates its reason (no assertion changes).
- **AC2-AC6 against the base.** The unit file run against `2ca62dbca0`'s `preflight.py` (a `git archive` copy with only
  the new test file added, `PYTHONPATH` on the copy), re-run after the re-review: 11 failed, 1 passed. The pinned
  record test passed; the six run tests each failed on `pixi install was reached` (the run went on to its pool, where
  the probe above spun); the five check and message tests failed on the missing names.
- **AC7 against the base.** The meta test run on `2ca62dbca0`'s tree: 3 failed, 7 passed. The graph test named
  `pages-build@pyforge-guild (named by pages-check@site); docs-site-validate-links@pyforge-guild (named by
  docs-site-validate@site); docs-site-validate-sidebar@pyforge-guild (named by docs-site-validate@site)`; the
  cross-check and the shape test failed with it.
- **AC8, each mutation on a scratch copy of the staged tree, the copy restored after each** (scratchpad
  `mutate3.py`, after the re-review): 22 passed before and after.

  | Mutation | Failed |
  |---|---|
  | R1 no refusal | 6: every run test (full, paused, no-counterpart, `--ignore-ci-pauses`, touched, fast core), each on `pixi install was reached` |
  | R2 the refusal after the install | 6: the same tests |
  | R3 the check on the lanes before the touched cut | 1: `test_a_fast_core_task_whose_dependency_the_cut_deferred_refuses` |
  | R4 the environment ignored in the check | 1: `test_a_dependency_is_a_task_in_its_own_environment` |
  | R5 the why left out | 5: the full, paused, `--ignore-ci-pauses`, touched and fast-core tests |
  | R6 the fast-core lines for every lane | 5: the full, no-counterpart, `--ignore-ci-pauses`, touched and two-dependencies tests |
  | R7 the command-line lines for a fast-core lane | 1: the fast-core test |
  | R8 the no-counterpart branch dropped | 1: `test_a_lane_no_ci_step_runs_says_so` |
  | R9 no `fix:` line in the command-line case | 2: the full and touched tests |
  | R10 the fast-core why read from the selection | 1: the fast-core test |
  | R11 the pause-ignored branch dropped | 2: `test_a_paused_lane_ignore_ci_pauses_re_adds_without_its_dependency_says_why`, `test_two_missing_dependencies_are_named_together` |
  | R12 a re-added lane's why back to the old fallback string | 1: the `--ignore-ci-pauses` test (it survived all 10 tests before the re-review) |
  | R13 the old fallback whole (the command-line kind and the old string) | 1: the `--ignore-ci-pauses` test |
  | R14 the no-counterpart fix line back to "make the CI step run" | 1: the no-counterpart test |
  | R15 the pause line's verb fixed to "is" | 1: `test_two_missing_dependencies_are_named_together` |
  | W1 walk: a bare entry in its dependent's environment | 2: the old-shape test and the bare-entry fixture test |
  | W2 walk: depth-first | 1: `test_on_the_old_site_shape_the_walk_stops_where_pixi_did` |
  | W3 walk: the default feature always | 2: the bare-entry and default-feature fixture tests |
  | W4 walk: an explicit environment ignored | 5: the graph, cross-check, old-shape, bare-entry and entry-form tests |
  | P1 `pixi.toml`'s `site` entries bare again (`2ca62dbca0`'s file) | 3: the graph, cross-check and shape tests |

## Verification run (2026-10-16, after the re-review)

On the 16-core host, at the branch's staged tree (`42c3ffff5d` plus the re-review fixes); every exit code read
directly, never through a pipe.

- The two new files, `pixi run --frozen -e pyforge-steward python -m pytest -q` on them: exit 0, 22 passed.
- The AC8 mutations (`mutate3.py`, Implementation Result): each of the 20 failed its named tests; the scratch copy
  passed 22 before and after.
- The re-review's probe, `r107/tools/probe_ignore.py`, against the staged `preflight.py`: exit 2 with the
  pause-ignored lines (the old command-line lines are gone).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test`: exit 0, 2882 passed, 2 skipped, 1 warning, in 399 s.
- The steward coverage gate (`--paths-file`, as below): exit 0; `preflight.py` 95%.
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0.
- Planning detectors, each `pixi run --frozen -e pyforge-guild <task>` on the staged tree: chain-completeness,
  dream-chain, dreams-hygiene, deferred-work, ledger-regression, story-status, flag-gate, chain-currency-sweep,
  ad-citation, tea-playwright-check and frontmatter-duplicate-keys, each exit 0;
  `python scripts/ci_surface_gates.py --check` exit 0. `bmad_tea_playwright.py --project pyforge-steward` exit 0.
- `spec-surface-check`: exit 0, last, after the memlog entries (`spec-pyforge-steward`, `spec-pyforge-core`, the two
  Specs the detector named) and their scoped stamps.
- `pixi.toml` and herald's files do not change in this unit, so the dry-runs, the lane dump, the export and herald's
  suite stand as recorded below.

## Verification run (2026-10-16, after the review)

On the 16-core host, at the branch's staged tree (`043eed5557` plus the review fixes); every exit code read directly,
never through a pipe.

- The two new files, `pixi run --frozen -e pyforge-steward python -m pytest -q` on them: exit 0, 20 passed.
- The AC8 mutations (Implementation Result): each failed its named tests; the scratch copy passed 20 before and after.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` (the station's `verify_commands`): exit 0, 2880 passed,
  2 skipped, 1 warning, in 429 s.
- `pixi run --frozen -e pyforge-herald pyforge-herald-test`: exit 0, 2049 passed, 30 skipped.
- The steward coverage gate, `COVERAGE_GATES_STATIONS=steward pixi run --frozen -e pyforge-steward python
  scripts/coverage_gates_ci.py --paths-file <origin/main...HEAD plus the staged paths> --suites unit`: exit 0;
  `preflight.py` 95% (floor 80%). The paths file stands in for `--base origin/main --head HEAD`, which cannot see an
  uncommitted change.
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0.
- `pixi run --as-is --dry-run -e pyforge-guild pr-preflight-lanes`: exit 0, 36 tasks, listed in the runner's lane
  order (`diff` empty). `-e site pages-check` and `-e site docs-site-validate`: exit 0 each, output byte-identical to
  the base revision's (`diff` empty).
- `list_preflight_lanes` on the live `pixi.toml`, dumped as `(task, environment, depends_on)` rows (scratchpad
  `lanes_dump.py`): byte-identical to the base revision's dump (`cmp` exit 0), 36 rows.
- `pixi project export conda-environment -e build` compared with `environment.yaml`: byte-identical (`cmp` exit 0);
  `pixi.lock` unchanged. `python scripts/docs_pixi_tasks.py --check`: exit 0.
- `sprint-ledger-sync -- --project steward --allow-regression` from the worktree-local feed with the old key removed:
  exit 0, `droping 1 key(s): 107-1-a-preflight-lane-runs-with-its-dependencies-in-the-runner-and-under-pixi-run`,
  `# stories: 601`; `story-status-check` and `ledger-regression-check` exit 0 after it.
- `bmad_tea_playwright.py --project pyforge-steward`: exit 0, 387 stories, 140 test files.
- Planning detectors, each `pixi run --frozen -e pyforge-guild <task>` on the staged tree: chain-completeness,
  dream-chain, dreams-hygiene, deferred-work, ledger-regression, story-status, flag-gate, chain-currency-sweep,
  ad-citation and tea-playwright-check, each exit 0. `llms-full-check` exit 0;
  `python scripts/ci_surface_gates.py --check` exit 0.
- `spec-surface-check`: exit 0 after the memlog entries and nine scoped stamps, one per Spec the detector or the
  baseline names for a changed path: `spec-pyforge-steward`, `spec-pyforge-core`, `spec-pyforge-herald`,
  `spec-pyforge-marshal`, `spec-pixi-candidate-currency`, `spec-deck-family-currency`, `spec-deck-family-lockstep`,
  `spec-pyforge-pages`, `spec-pyforge-unifying-strategy`. `pixi run --frozen -e pyforge-guild detectors-ci`: exit 0,
  49 detectors pass.
- Not run here: the full `pr-preflight` (left to the orchestrator before the push), and the station suites other than
  steward's and herald's; no other station's tests read a changed file's changed lines.

## Verification run (2026-10-16, before the review)

The first cut's run, kept as the record: the steward suite exit 0 (2882 passed, 2 skipped); herald's suite exit 0
(2049 passed, 30 skipped); the coverage gate, `lint-types`, the planning detectors, `ci_surface_gates.py --check`,
`llms-full-check` and `detectors-ci` (49 detectors pass) each exit 0; `spec-surface-check` exit 0 after nine scoped
stamps.
