---
title: '107.1: A preflight lane runs with its dependencies, in the runner and under pixi run'
type: 'fix'
created: '2026-10-16'
status: 'in-review'
baseline_revision: '2ca62dbca09624fa3a8231123101acaf7c95f1d1'
flag-exempt: detector-or-gate   # a fix needs no flag (spec-feature-flag-governance Q1), and pr-preflight is a gate: a flag-OFF run would keep the spin reachable (Q2's gate exemption), as 105.1 and 106.1 recorded
review_loop_iteration: 0
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
  (`touched_cut`, `:342`). Nothing closes that set over `depends_on`. A lane whose dependency is not in it is never
  ready (`_deps_all_ok`, `:849`, wants every dependency `ok`) and never blocked (`_mark_dependency_blocked` skips a lane
  while any dependency has no result, `:1245`). With no future in flight, `if not futures:` (`:1294`-`:1297`)
  `continue`s with no wait.
- **The fast core (`DW-steward-103-6-2`).** `_fast_core_lanes` (`:331`) builds the five fast-core detectors with their
  own dependency closure, and `touched_cut` keeps only the extras not already among the run's lanes (`:390`). A
  fast-core task that depends on a lane the cut deferred would run without it: the same stranded lane.
- **The pixi task (`DW-steward-45-1-1`).** `pixi run -e pyforge-guild pr-preflight-lanes` is the serial reference
  Story 71.1 kept. Its `{ task = "pages-check", environment = "site" }` leg (`pixi.toml:1621`) depends on the bare
  `pages-build` (`:980`). Pixi looks a bare `depends-on` entry up in the environment the run was invoked in, where the
  `site` feature's tasks do not exist. `pages-build` (`:975`), `docs-site-build` (`:970`), `docs-site-validate-sidebar`
  (`:993`) and `docs-site-validate` (`:997`) name bare dependencies too. The runner is unaffected: `_resolve_dep`
  (`preflight.py:220`) gives a bare entry its dependent's environment.

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

**Approach:** the lanes a run runs are closed over their dependencies, a run that would still strand one refuses, and
the `site` tasks name their environment.

- **A selected lane brings the lanes it depends on, as `pixi run` itself does.** `close_over_dependencies(run_lanes,
  all_lanes)` adds every lane the chosen lanes depend on, transitively, from the full lane list. `run_preflight` calls
  it after the selection and the CI pause filter and before `touched_cut`. That includes a dependency whose own CI job
  is paused: CI's dependent job runs `pixi run`, which runs the dependency inside that job, so the preflight runs it
  too, and its paused `not-run` row is dropped, because it runs. Each pulled-in lane is named on stderr
  (`preflight: pulled in <lane>@<env>: <dependent>@<env> depends on it`, and `, paused in CI, where its dependent's job
  runs it through pixi run` for a paused one), and journaled in an optional `selection.pulled_in` list of
  `{lane, environment, reason}`, the shape of `selection.selected`, in the run record and the interrupted record. A
  pulled-in lane names the first lane, in run order, that needs it. With nothing pulled in the function returns the
  run set as it was, order included, and no key is written. With something pulled in the lanes come back in
  declaration order, which puts every dependency before the lanes that need it.
- **No stranded lane reaches the pool.** After the touched cut, fast core included, and before any `pixi install` or
  lane, `stranded_dependencies(lanes)` names each lane that depends on a lane outside the run. If there is one, the run
  prints `preflight: <lane>@<env> depends on <dep>@<env>, which this run does not run` for each, then `preflight:
  refusing the run before any install or lane starts`, and returns `EXIT_CONFIG` (2), journaling nothing, as every
  config refusal does. After the closure only the fast core can reach it. The scheduler loop is not restructured: the
  invariant makes the spin unreachable.
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

**Rejected:**
- **`DW-steward-103-6-1`'s option (b) alone, refuse every selection that strands a dependency.** It keeps the run set
  exactly CI's, but it would refuse a selection `pixi run` itself would run, and `pixi run` is what CI's dependent job
  runs. The refusal stays, as the backstop.
- **`_mark_dependency_blocked` journals a dependency absent from the run as blocked** (the row's first follow-up). The
  dependent would never run, and the run would go green or `not-run` without the lane CI would have run.
- **`_fast_core_lanes` refuses a fast-core task that has dependencies** (`DW-steward-103-6-2`'s follow-up). It refuses
  even when the dependency is not among the run's lanes, where `_fast_core_lanes` already brings it; the general
  refusal covers the one case that strands.
- **Restructuring the scheduler loop** (a sleep or a deadlock check in `if not futures:`). It would hide the cause; the
  invariant removes it.
- **Saying in `pr-preflight-lanes`' description that it is a graph for the runner only** (`DW-steward-45-1-1`'s second
  option). The task is the serial reference, and it should run.

Ledger key: `107-1-a-preflight-lane-runs-with-its-dependencies-in-the-runner-and-under-pixi-run`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159: the preflight runs the lanes a PR gates on, each after its own
  dependencies (Story 88.1), selected from CI's rules (Story 71.2), with CI pauses (Story 99.5) and a touched scope
  (Story 103.6). This story makes the run set closed under its own dependency edges and refuses the one case that still
  is not. It mints no CAP and changes no `SPEC.md`.
- **Governance.** `preflight.py` and the two new tests are on `spec-pyforge-steward`'s surface, `preflight.py` also on
  `spec-pyforge-core`'s (every station's `src/`); `pixi.toml` has the co-governors `spec-surface-check` names; herald's
  three meta tests are on herald's Specs.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag; the frontmatter records
  `flag-exempt: detector-or-gate` (pr-preflight is a gate).
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, the 2026-10-16 (a selected lane strands its dependency)
  entry; `DW-steward-103-6-1`, `DW-steward-103-6-2`, `DW-steward-45-1-1`.

## Acceptance Criteria

AC1-AC6 run the real `run_preflight` or its two new functions over fixture `pixi.toml`s, with an injected lane runner
and, where a run needs one, a monkeypatched selection, each under Story 105.1's hang guard. AC7 reads the live
`pixi.toml`. No test runs pixi.

- **AC1 — The closure.** `close_over_dependencies` returns the chosen lanes unchanged, order included, when nothing is
  missing; pulls a missing dependency in transitively, in declaration order; names each pulled-in lane with the first
  lane in run order that needs it; treats a lane as its task and its environment (Story 103.5); and leaves a dependency
  outside the lane list out. `stranded_dependencies` names each lane and each of its missing dependencies.
- **AC2 — Full scope.** A selection that keeps `app` and drops `build` and `install` (`app` depends on `build`,
  `build` on `install`): all four run, each dependency before its dependent; exit 0; the journal's lanes are in
  declaration order; `selection.pulled_in` names `install` (for `build`) and `build` (for `app`); `selection.skipped`
  is still CI's; stderr names each pulled-in lane. A red pulled-in lane cancels its dependents (exit 1).
- **AC3 — A paused dependency.** With the CI pause flag on and `install` paused alone, `app` (selected, depends on
  `install`) runs after `install`; the journal has one `install` row, `ok`, and no paused `not-run` row; the reason
  says it was paused; the pause banner still prints.
- **AC4 — Touched scope.** A diff that touches `app`, whose dependency `build` the selection dropped: `build` is pulled
  in and kept, and runs before `app`; `detectors-ci` alone is deferred.
- **AC5 — The refusal.** A touched run whose fast-core `flag-gate-check` depends on `build`, which the cut deferred:
  exit 2; stderr names `flag-gate-check@pyforge-guild` and `build@pyforge-guild` and ends with the refusal line; no
  environment is installed, no lane starts, nothing is journaled.
- **AC6 — Nothing pulled in.** A run whose dependencies are all selected (`lint`, skipped, has no dependent): the run
  set and order, the whole stderr, and both journal records (the install record and the run record, with only the run's
  identity, the checkout's head, the clocks and the host left out) equal a pinned copy, which passes against the base
  revision's `preflight.py` too; no `pulled_in` key.
- **AC7 — The pixi graph.** The meta test's walk of `pr-preflight-lanes` from `pyforge-guild` finds every pair; finds
  the same pairs `list_preflight_lanes` builds; on the old `site` shape, rebuilt from the live tree, names
  `pages-build@pyforge-guild` (named by `pages-check@site`) first, then the two `docs-site-validate` legs, and resolves
  `pages-check` and `docs-site-validate` from `site`; every `site` task's `depends-on` entry names `site`; `pixi.toml`
  declares no platform tasks and no `depends_on` key the walk does not read; and three fixture tests pin the rule
  (bare entries in the invoking environment, breadth-first; the default feature unless `no-default-feature`; an entry
  without an environment is bare).
- **AC8 — Mutation.** Each change below fails a named test, and the Implementation Result records which: no closure;
  no refusal; the refusal after the install; the paused row kept; no `pulled_in` key; a `pulled_in` key always; the
  closure not transitive; pulled-in lanes appended instead of declaration order; declaration order always; the last
  dependent named; the paused note dropped; and in the walk: a bare entry in its dependent's environment, depth-first,
  the default feature always, an explicit environment ignored; and `pixi.toml`'s `site` entries back to bare names.
- **AC9 — The real tree.** `pixi run --as-is --dry-run -e pyforge-guild pr-preflight-lanes` exits 0 with 36 tasks;
  `-e site pages-check` and `-e site docs-site-validate` exit 0 and list the same tasks, in the same order, as before;
  `list_preflight_lanes` on the live `pixi.toml` gives the same lanes, order and edges as at `2ca62dbca0`; `pixi.lock`
  and `environment.yaml` do not change.
- **AC10 — Green, the surface reconciled.** `pixi run --frozen -e pyforge-steward pyforge-steward-test`, herald's three
  changed meta tests, `lint-types` and the steward coverage gate exit 0; each changed governed path gets a
  surface-reconcile entry on the memlog of every Spec that governs it.

## Boundaries & Constraints

**Always:**
- Keep CI's selection what it is: the closure only adds the dependencies of lanes the run runs, and the journal's
  `selected` and `skipped` lists stay CI's.
- Keep the scheduler loop as it is; keep the exit codes (`EXIT_CONFIG` is the code every config refusal already uses).

**Never:**
- Never change a dependency, a version, `pixi.lock` or `environment.yaml`; never move a lane in `list_preflight_lanes`.
- Never weaken or delete an existing assertion: herald's three meta tests restate the `site` tasks' `depends-on` in
  the new shape, entry for entry.

**Residual risk:**
- **A local run can run a lane CI's rules skipped.** When a selected lane depends on a lane the selection dropped, the
  preflight runs the dependency, as the dependent's CI job does through `pixi run`. A CI step that runs its task with
  `--skip-deps` (pages.yml's `docs-site-validate` legs) does not, and gets the dependency from an earlier step of the
  same job; the preflight then runs it as a lane of its own, which costs that lane's time. Nothing on today's graph is
  pulled in by any selection herald 45.1's review swept.
- **A pulled-in paused lane runs.** A paused CI surface stays off in CI, but a lane that a selected lane depends on
  runs locally whatever its pause says. Today none can be held back: the lanes with dependents are
  `docs-site-install`, `pages-build` and `docs-site-validate-sidebar-order`, and no row of
  `docs/governance/ci-surfaces.yaml` names one of them as its `local_twin`, which is how the pause filter finds a lane
  (`preflight_ci._registry_row_for_lane`).
- **A fast-core task with a dependency refuses touched runs.** `_fast_core_lanes` brings a fast-core task's dependency
  when it is not among the run's lanes, so the refusal fires only when it is and the cut deferred it. Then every such
  touched run exits 2 until the fast-core task drops its dependency or the cut learns to keep it. None of the five has
  a `depends-on` today; the refusal says which lane and which dependency.
- **The walk models pixi 0.81.0.** A pixi release that resolves a bare entry in its dependent's environment would make
  the test stricter than pixi, never looser. Platform tasks (`target.<platform>.tasks`) and the `depends_on` key are
  outside the walk; a guard test fails when `pixi.toml` starts to use either.

## I/O & Edge-Case Matrix

| Situation | Before (`2ca62dbca0`) | After |
|---|---|---|
| full run, the selection keeps `a` and drops `b`, which `a` depends on | spins with nothing in flight until SIGINT (7.96 s user in 8.03 s) | `b` pulled in, runs first; stderr and `selection.pulled_in` name it |
| CI pause on the dependency alone | spins | the dependency runs; its paused `not-run` row is dropped; the reason says it was paused |
| touched run, a kept lane's dependency dropped by the selection | spins | pulled in before the cut, kept by the cut |
| touched run, a fast-core task depends on a lane the cut deferred | spins (the fast core's other four run) | exit 2 before any install or lane, naming the lane and the dependency |
| nothing pulled in | the run as it was | unchanged (pinned) |
| a pulled-in lane goes red | n/a | its dependents are cancelled, exit 1 |
| `--ignore-ci-pauses` | paused lanes appended after the selected ones | unchanged when nothing is pulled in; declaration order when something is |
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
- Ledger key: `107-1-a-preflight-lane-runs-with-its-dependencies-in-the-runner-and-under-pixi-run`.
- Ledger status at mint: `backlog`, as 106.1's was while it was in review; `done` in the landing merge, with `epic-107`
  rolled up to `done`.
- Deps: none.
- Closes: `DW-steward-103-6-1`, `DW-steward-103-6-2`, `DW-steward-45-1-1` (`status: closed` in this commit, each with a
  `closed:` line citing this story and its tests).
- Surface: `marshal-policy.toml` `[epic_surfaces]."107"`.
- Flag: none — a fix (`spec-feature-flag-governance` Q1); `flag-exempt: detector-or-gate` recorded above.

## Epic excerpt

Story 107.1 in `epics.md` § Epic 107: a preflight lane runs with its dependencies, in the runner and under pixi run.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`;
  MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest -q src/shared/packages/pyforge-steward/tests/unit/test_preflight_dependency_closure.py src/shared/packages/pyforge-steward/tests/meta/test_pr_preflight_lanes_resolve_under_pixi.py` — expected: 22 passed (AC1-AC7).
- The AC8 mutations, one at a time on a scratch copy (never the worktree), re-running the two files — expected: each
  fails its named tests; the copy restored after each.
- `pixi run --frozen -e pyforge-herald python -m pytest -q src/shared/packages/pyforge-herald/tests/meta/test_docs_site.py src/shared/packages/pyforge-herald/tests/meta/test_docs_site_validators.py src/shared/packages/pyforge-herald/tests/meta/test_one_generator.py` — expected: exit 0.
- `pixi run --as-is --dry-run -e pyforge-guild pr-preflight-lanes` — expected: exit 0 (AC9).
- `pixi run --as-is --dry-run -e site pages-check` and `pixi run --as-is --dry-run -e site docs-site-validate` —
  expected: exit 0, the same task lists as at the base revision (AC9).
- `pixi project export conda-environment -e build`, compared with `environment.yaml` — expected: byte-identical (AC9).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- The steward coverage gate, `pixi run --frozen -e pyforge-steward python scripts/coverage_gates_ci.py --station steward --suites unit` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and one scoped stamp per
  Spec (AC10).

## Spec Change Log

- 2026-10-16: minted from the Dream's 2026-10-16 entry and the three DW rows, on the orchestrating session's design.
  `type: fix`, no flag, no CAP; bound to `spec-pyforge-steward` CAP-159. Measured first: the spin in both scopes, and
  pixi's lookup rule at six states.
- 2026-10-16 (implementation): hand-implemented on branch `chain-preflight-stranded-deps-2026-10-16` from
  `2ca62dbca0`; status `in-review` for an independent review against this spec.

## Implementation Result

Hand-implemented on branch `chain-preflight-stranded-deps-2026-10-16`, from baseline `2ca62dbca0`. The diff is for an
independent review against this spec, not against this summary.

- **`preflight.py`:** `DependencyClosure`, `close_over_dependencies` and `stranded_dependencies`, beside
  `list_preflight_lanes`; `_pulled_in_reason`; `run_preflight` keeps the full lane list, closes the selected lanes over
  their dependencies after the pause filter and before `touched_cut`, prints and journals each pulled-in lane, drops a
  pulled-in lane's paused row, and refuses a stranded lane after `_print_scope` and before the install; the module,
  `touched_cut` and `run_preflight` docstrings say so.
- **`pixi.toml`:** the five `site` tasks with a `depends-on` (`docs-site-build`, `pages-build`, `pages-check`,
  `docs-site-validate-sidebar`, `docs-site-validate`) name `environment = "site"` on every entry, under a comment that
  says why. No other line changes.
- **Tests (new):** `tests/unit/test_preflight_dependency_closure.py` (AC1-AC6, 12 cases) and
  `tests/meta/test_pr_preflight_lanes_resolve_under_pixi.py` (AC7, 10 cases).
- **Herald (cross-station, restated):** `tests/meta/test_docs_site.py` (`docs-site-build`),
  `tests/meta/test_docs_site_validators.py` (`docs-site-validate-sidebar`, `docs-site-validate`) and
  `tests/meta/test_one_generator.py` (`pages-check`) expect the explicit entries.
- **AC6 against the base.** The pinned record test, run against `2ca62dbca0`'s `preflight.py` (a `git archive` copy
  with only the new test file added, `PYTHONPATH` on the copy): 1 passed. The four run tests that need the closure,
  run there one at a time under `timeout 20`, each spun until killed (exit 124); the refusal test failed fast on
  `pixi install was reached`.
- **AC7 against the base.** The meta test run on `2ca62dbca0`'s tree: 3 failed, 7 passed. The graph test named
  `pages-build@pyforge-guild (named by pages-check@site); docs-site-validate-links@pyforge-guild (named by
  docs-site-validate@site); docs-site-validate-sidebar@pyforge-guild (named by docs-site-validate@site)`; the
  cross-check and the shape test failed with it.
- **AC8, each mutation on a scratch copy of the staged tree, the copy restored after each** (scratchpad `mutate.py`;
  22 passed before and after):

  | Mutation | Failed |
  |---|---|
  | M1 no closure | 4: the full-run, red-dependency, paused and touched-keep tests (each refused with exit 2; none hung) |
  | M2 no refusal | 1: `test_a_lane_stranded_after_the_cut_refuses_before_any_install_or_lane` (`pixi install was reached`) |
  | M3 the refusal after the install | 1: the same test |
  | M4 the paused row kept | 1: `test_a_paused_dependency_runs_and_loses_its_paused_row` |
  | M5 no `pulled_in` key | 3: the full-run, paused and touched-keep tests |
  | M6 a `pulled_in` key always | 1: `test_a_run_that_pulls_nothing_in_is_todays_run` |
  | M7 the closure not transitive | 3: the transitive unit test, the full-run and red-dependency tests |
  | M8 pulled-in lanes appended | 5: the transitive, first-dependent and environment unit tests, the full-run and paused tests |
  | M9 declaration order always | 1: `test_nothing_to_pull_in_returns_the_chosen_lanes_as_they_were` |
  | M10 the last dependent named | 1: `test_a_pulled_in_lane_names_the_first_lane_in_run_order_that_needs_it` |
  | M11 the paused note dropped | 1: the paused test |
  | M12 walk: a bare entry in its dependent's environment | 2: the old-shape test and the bare-entry fixture test |
  | M13 walk: depth-first | 1: `test_on_the_old_site_shape_the_walk_stops_where_pixi_did` |
  | M14 walk: the default feature always | 2: the bare-entry and default-feature fixture tests |
  | M15 walk: an explicit environment ignored | 5: the graph, cross-check, old-shape, bare-entry and entry-form tests |
  | M16 `pixi.toml`'s `site` entries bare again | 3: the graph, cross-check and shape tests |

## Verification run (2026-10-16)

On the 16-core host, at the branch's staged tree (baseline `2ca62dbca0` plus this change); every exit code read
directly, never through a pipe.

- The two new files, `pixi run --frozen -e pyforge-steward python -m pytest -q` on them: exit 0, 22 passed in 0.58 s.
- The AC8 mutations (Implementation Result): each failed its named tests; the scratch copy passed 22 before and after.
- Herald: the three changed meta tests with `test_built_site_tests_install_first.py` and `test_preflight_pages_lane.py`,
  `pixi run --frozen -e pyforge-herald python -m pytest -q`: exit 0, 47 passed, 16 skipped. Herald's whole suite,
  `pixi run --frozen -e pyforge-herald pyforge-herald-test`: exit 0, 2049 passed, 30 skipped.
- `pixi run --as-is --dry-run -e pyforge-guild pr-preflight-lanes`: exit 0, 36 tasks, listed in the runner's lane
  order (`diff` of the two lists empty). `-e site pages-check` and `-e site docs-site-validate`: exit 0 each, output
  byte-identical to the base revision's (`diff` empty).
- `list_preflight_lanes` on the live `pixi.toml`, dumped as `(task, environment, depends_on)` rows (scratchpad
  `lanes_dump.py`): byte-identical to the base revision's dump (`cmp` exit 0), 36 rows.
- `pixi project export conda-environment -e build` compared with `environment.yaml`: byte-identical (`cmp` exit 0);
  `pixi.lock` unchanged (`git status`).
- `pixi run --frozen -e pyforge-guild python scripts/docs_pixi_tasks.py --check`: exit 0 (`how-to/pixi-tasks.md`
  current).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` (the station's `verify_commands`): exit 0, 2882 passed,
  2 skipped, 1 warning, in 402 s. It ran before `ruff format` re-wrapped the two new test files; the coverage gate
  below ran the same unit and meta suites after it: 2882 passed.
- The steward coverage gate, `COVERAGE_GATES_STATIONS=steward pixi run --frozen -e pyforge-steward python
  scripts/coverage_gates_ci.py --paths-file <origin/main...HEAD plus the staged paths> --suites unit`: exit 0;
  `preflight.py` 95%, `estate_verify.py` 83% (floor 80%). The paths file stands in for `--base origin/main --head
  HEAD`, which cannot see an uncommitted change.
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0.
- Planning detectors, each `pixi run --frozen -e pyforge-guild <task>` on the staged tree: chain-completeness,
  dream-chain, dreams-hygiene, deferred-work, ledger-regression, story-status, flag-gate, chain-currency-sweep,
  ad-citation and tea-playwright-check, each exit 0; chain-currency-sweep exit 0 again after the co-governor memlog
  entries.
- `pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check`: exit 0.
  `pixi run --frozen -e pyforge-guild llms-full-check`: exit 0. `pixi run --frozen -e pyforge-guild detectors-ci`:
  exit 0, 49 detectors pass.
- `sprint-ledger-sync -- --project steward` from a worktree-local feed seeded from the tracked twin: exit 0,
  `# stories: 601`; `story-status-check` exit 0 after it.
- `bmad_tea_playwright.py --project pyforge-steward`: exit 0, 387 stories, 140 test files, 107 epics.
- `spec-surface-check`: exit 0 after the memlog entries and nine scoped stamps, one per Spec the detector or the
  baseline names for a changed path: `spec-pyforge-steward`, `spec-pyforge-core`, `spec-pyforge-herald`,
  `spec-pyforge-marshal`, `spec-pixi-candidate-currency`, `spec-deck-family-currency`, `spec-deck-family-lockstep`,
  `spec-pyforge-pages`, `spec-pyforge-unifying-strategy`.
- Not run here: the full `pr-preflight` (left to the orchestrator before the push), and the station suites other than
  steward's and herald's. No other station's tests read the `site` tasks' `depends-on` or a changed file
  (`git grep` of every `tests/` for the five tasks' names in a `depends-on` assertion).
