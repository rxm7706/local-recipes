---
title: "103.5: The preflight keys each lane by its task and its environment"
type: 'fix'
created: '2026-10-14'
status: 'done'
baseline_revision: '22e5c19c285e722bcf7d58203689d57e9cc4dd55'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-1-every-preflight-run-journals-each-lane-s-wall-time-and-exit-code.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-2-the-preflight-runs-the-lanes-ci-would-run-for-the-diff-read-from-the-workflow-files.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-10-a-stopped-lane-is-journaled-cancelled-and-the-lane-that-stopped-the-run-red.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-31-1-atlas-passes-mypy-in-pyforge-foundry-full-and-a-lane-keeps-it-so.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_budget.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_xdist.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pr-preflight-lanes` may name one task in two environments, and the runner then loses one of the two
lanes. Atlas Story 31.1 (PR #2221, branch `dispatch/pyforge-atlas/31.1`) adds `{ task = "mypy", environment =
"pyforge-foundry-full" }` beside the Guild's `mypy`, and CI's `steward-test` fails on it:
`test_preflight_selection.py::test_run_preflight_runs_selected_lanes_in_order_and_journals_the_selection` —
`assert 20 == (37 - 16)`. Line numbers are at `22e5c19c28`.

- **The lane list is right.** `list_preflight_lanes` (`preflight.py:172`) returns one `Lane` per `(task,
  environment)`, keyed `LaneKey = tuple[str, str]` (`:47`), and the pool's `pending` and `completed` maps use that
  key (`:892`-`:893`). Selection verdicts are per lane too (`preflight_ci.Selection.is_selected`, `:103`), and so
  are the service mutex keys (`static_service_mutex_keys`, `:1499`).
- **Everything else keys by the task name.** In `preflight.py`:
  - `results_by_task: dict[str, LaneResult]` (`:891`), written by `_record_done` (`:900`) and read to build the
    ordered results and the journal (`:990`-`:991`, `:1017`-`:1018`). Two lanes of one task share one entry, so the
    journal lists whichever finished last, twice.
  - each lane's scratch directory and log are `scratch_root / lane.task` and `scratch_root / f"{lane.task}.log"`
    (`:661`-`:662`), and the red-lane lines name `f"{lane.task}.log"` (`:1026`, `:1036`), so both lanes write one log.
  - `_RunCoordinator.terminated_lane_tasks` and `proc_lane_task` (`:286`-`:287`, `register_proc` `:304`), the
    `red_lanes` list (`:284`, `:694`), the `stop_trigger` (`:285`, `:697`) that becomes `cancelled_by`, the
    suite-reduction runtime journal (`:291`, `:481`, `_lane_journal_extra` `:528`) and the xdist share map (`:292`,
    `:664`) are keyed by the task. A stop that terminates one lane marks its twin cancelled too.
  - the CI-pause filter (`:752`-`:771`) drops every lane whose task is paused, so a pause on one lane drops its twin
    from the run and from the journal.
- **Selection.** `_step_matches` (`preflight_ci.py:455`) matches a `pixi run` step by the depends-on closure of its
  task (`_closure`, `:322`) and ignores the step's `-e`; the command-line match beside it (`_segment_in_run`, `:416`)
  compares the environment (`:428`-`:430`). The verdicts, `is_selected` and the journal's `selection` block are
  already per lane. *(Amended in implementation, 2026-10-14: the task match stays as it is; see Approach.)*
- **Budgeting.** `preflight_budget._selection_selected_lanes` (`:101`) returns a set of names, so two station-test
  lanes of one task count once in `is_single_station_budget` (`:112`); `_lane_timings` (`:121`) labels each lane by
  its task alone. `preflight_xdist.lane_xdist_worker_map` (`:46`) returns a share per task name.
- **Reproduced at `22e5c19c28`** (pixi `pyforge-steward`): with 31.1's `pixi.toml` and `lint-types.yml` checked out,
  `test_preflight_selection.py` gives 1 failed, 72 passed (37 lanes; 17 selected, 16 distinct task names). A
  two-lane fixture (`a` in `inv` exits 0, `a` in `other` exits 3, `--keep-going`) journals `a`/`other`/`red`/`3`
  twice, prints `lane 'a' in environment 'inv' exited 3`, and both lanes write one `a.log`.

**Approach:** a lane's identity is `(task, environment)` everywhere the preflight selects, runs, orders, journals,
logs and budgets lanes.

- **Results and order.** `results_by_task` becomes `results_by_key: dict[LaneKey, LaneResult]`; the ordered results
  and the journal read it by `_lane_key(lane)`.
- **Scratch and logs.** A new `lane_label(task, environment)` returns `<task>@<environment>`. Each lane's scratch
  directory is `scratch_root / lane_label(...)` and its log `scratch_root / f"{lane_label(...)}.log"`; the red-lane
  lines print that path. The root stays flat, one directory per lane (Story 71.8's property). Pixi environment names
  hold only lowercase letters, digits and hyphens, so the label is unique per lane.
- **The coordinator.** `terminated_lane_tasks` and `proc_lane_task` become `terminated_lanes: set[LaneKey]` and
  `proc_lane: dict[int, LaneKey]`, and `register_proc` takes the lane key; `red_lanes` holds lane keys; the
  suite-reduction runtime journal and the xdist share map are keyed by lane. The stop cause is one
  `stop_cause: tuple[str, str | None]` (the trigger and, for a lane, its environment), assigned once, so a reader
  never sees one half; `stop_trigger` stays as a read-only property.
- **The journal, additively.** `LaneResult` gains `cancelled_by_environment` and `blocked_by_environment`, written
  only when the cause is a lane (never for `interrupt`). Every existing key keeps its name and meaning.
- **The pause filter** keys paused lanes by `(task, environment)`. The pause banner still de-duplicates by task: its
  lines are CI surfaces from the registry, which names no environment.
- **Selection keeps its per-lane verdicts and its task match.** Each lane gets its own verdict, `is_selected`
  reads `(task, environment)`, and the journal's `selected` and `skipped` entries carry the environment; the tests
  now count them that way. A `pixi run <task>` step still matches by task whatever its `-e` (Story 71.2's "the
  lane's own task"): a bare `depends-on` lane runs in the environment `pr-preflight` is invoked from (the Guild or
  `local-recipes`), which need not be CI's. `_step_matches` says so in its docstring.
  - *Amended in implementation, 2026-10-14.* The mint planned an environment-aware closure (a step counting only in
    its own environment, an unstated or a dynamic one). It changed no match on `22e5c19c28`, and with 31.1's files it
    only re-attributed each `mypy` lane to its own step in the same `lint-types` job, so no verdict moved. But it
    failed `test_service_lanes_never_overlap`: lanes invoked from one environment lost their CI step in another, and
    with it the service mutex that keeps two Postgres lanes apart. The same would hit every bare lane of a
    `pixi run -e local-recipes pr-preflight`. So it was dropped; the `spec-pyforge-steward` memlog records why.
- **Budget.** `_selection_selected_lanes` returns `(lane, environment)` pairs and the single-station rule counts
  station-test lanes by pair; `_lane_timings` labels a lane `<task>@<environment>` when the journal entry carries an
  environment, and by its task alone when an older entry does not.
- **xdist.** `lane_xdist_worker_map` takes lane keys and returns a share per lane key.
- **Kept by task, on purpose.** The suite-reduction plan (`build_suite_lane_overrides`) is computed from a pixi task
  definition, which has no environment, so it stays keyed by task and each lane reads its own task's plan. The CI
  surfaces registry (`_registry_row_for_lane`, `local_twin`) names no environment. `estate verify --lane NAME`
  filters by task name and appends one row per lane, each carrying its environment, so nothing there is overwritten.

**Rejected:**
- **`<environment>/<task>.log`.** Unique too, but the lane directory's parent stops being the scratch root, which
  four scratch tests read as the root; they would keep passing while asserting less.
- **`<task>.log` unless the task repeats.** Two naming rules, and a lane's log name would depend on the other lanes.
- **De-duplicating `pr-preflight-lanes` by task.** CAP-159 reads the lane list from `pixi.toml` and never edits it;
  31.1's second lane is the point of that story.
- **Renaming `cancelled_by` to carry `task@environment`.** It would change the meaning of an existing journal field.
- **An environment-aware CI-counterpart match.** See the Approach's amendment: it moved no verdict and dropped the
  service mutex for lanes invoked from another environment.

Ledger key: `103-5-the-preflight-keys-each-lane-by-its-task-and-its-environment`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (Stories 71.1-71.3, 71.6, 71.7, 71.8, 71.10, 99.5): the lane
  list read from `pixi.toml`, the lanes CI's rules select, concurrent lanes that share no mutable state, a journal of
  every lane's wall time and exit code, and the budget check that reads it. This story makes each of those hold for
  two lanes of one task. It mints no CAP and changes no `SPEC.md`.
- **Governance.** The four modules are on `spec-pyforge-steward`'s and `spec-pyforge-core`'s surfaces; the tests on
  `spec-pyforge-steward`'s (`scripts/.spec-surface-baseline.json`).
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, the 2026-10-14 (CI and estate follow-ups) entry, its
  preflight lane identity addition.

## Acceptance Criteria

Every criterion runs the real `run_preflight` (or the real module function) on fixture `pixi.toml` files, with
injected lane runners or `subprocess_argv_for_lane` scripts. None runs pixi.

- **AC1 — Both lanes run.** A lane list `["a", { task = "a", environment = "other" }]` gives two lanes, and
  `run_preflight` runs both, each with its own `LaneRunContext` (its own lane, scratch directory and log path).
- **AC2 — Each journals its own result.** With `a` in the invoking environment exiting 0 and `a` in `other` exiting
  3 (`--keep-going`), the run exits 1 and its journal lists two `a` entries, in declaration order, with their own
  environment, status (`ok`, `red`), exit code and seconds; stderr names only `a` in `other` as red, each line with
  its own log path.
- **AC3 — Each writes its own log.** Run through real subprocesses, each lane's log is `<scratch root>/a@<env>.log`,
  holds only its own lane's output, and the kept scratch root holds one directory per lane.
- **AC4 — The cause names its environment.** When `a` in `other` goes red and a lane depending on it is stopped, that
  lane is journaled `cancelled` with `cancelled_by: a` and `cancelled_by_environment: other` (and `not-run` with
  `blocked_by` / `blocked_by_environment` under `--keep-going`). An interrupt's `cancelled_by: interrupt` carries no
  environment.
- **AC5 — A pause drops only its lane.** With CI pauses on and only `a` in `other` paused, `a` in the invoking
  environment runs and `a` in `other` is journaled `not-run` with its pause verdict.
- **AC6 — Selection decides each lane alone.** Given one verdict selecting `a` in the invoking environment and one
  skipping `a` in `other`, only the first runs, and the journal's `selected` and `skipped` entries name each with its
  environment. `_step_matches` keeps its task match, and every case of
  `test_step_matches_task_closure_or_own_command_line` keeps its expected value. *(Amended in implementation,
  2026-10-14; see the Approach.)*
- **AC7 — The selection tests count lanes.** `test_preflight_selection.py`'s journal and run-order checks count lanes
  by `(task, environment)`, and `test_run_preflight_runs_selected_lanes_in_order_and_journals_the_selection` passes
  with atlas 31.1's lane list.
- **AC8 — Budgeting.** Two station-test lanes of one task are two lanes to `is_single_station_budget`; the budget
  lines label a lane `<task>@<environment>`, and an entry without an environment by its task; two lanes of one xdist
  task each get a share in `lane_xdist_worker_map`, keyed by lane.
- **AC9 — With atlas 31.1 present.** With `git checkout origin/dispatch/pyforge-atlas/31.1 -- pixi.toml
  .github/workflows/lint-types.yml` (both files: the lane and the CI step that is its counterpart), `pixi run --frozen
  -e pyforge-steward pyforge-steward-test` exits 0; both files are restored and never committed.
- **AC10 — Nothing weakens.** Every existing assertion in the preflight tests keeps or raises its strength: a check of
  a task name becomes a check of the `(task, environment)` key, and a scratch path check names the lane's label. The
  journal's record keys are unchanged apart from the two optional fields of AC4.
- **AC11 — Mutation.** Each change below fails a named test, and the Auto Run Result records which:
  - keying `results_by_key` by the task again (AC2);
  - naming the lane log `<task>.log` again (AC3);
  - filtering paused lanes by task again (AC5);
  - dropping the red blocker's environment (AC4). *(Replaces the closure mutation, whose design was dropped.)*
- **AC12 — Green, and the surface reconciled.** `pixi run --frozen -e pyforge-steward pyforge-steward-test`, `pixi
  run -e pyforge-steward pyforge-steward-coverage-gate` and `pixi run --frozen -e pyforge-guild lint-types` exit 0.
  Each changed governed path gets a surface-reconcile entry on the memlog of every Spec that governs it
  (`spec-pyforge-steward`, `spec-pyforge-core`), then one scoped stamp per Spec, and `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Key every per-lane structure by `(task, environment)`; keep a per-task structure only where its source has no
  environment (the suite-reduction plan, the CI surfaces registry, the pause banner), and say so in the code.
- Keep the journal additive: no renamed or removed key, no changed meaning.
- Reconcile every governed path on each governing Spec's memlog, then stamp each scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never commit `pixi.toml` or a workflow file: atlas 31.1 owns its lane and its CI step.
- Never edit `pr-preflight-lanes` to avoid the duplicate.
- Never weaken or delete an existing assertion.

**Residual risk:**
- Lane logs and scratch directories are now `<task>@<environment>`. Operators who open a kept scratch root by a
  remembered `<task>.log` name find the label instead; every red-lane line prints the full path.
- `estate verify --lane NAME` still selects by task name, so it runs both lanes of a task. That is a name filter, not
  an overwrite; a `task@environment` form would be a feature of its own.

## I/O & Edge-Case Matrix

| Situation | Today (`22e5c19c28`) | After |
|---|---|---|
| one task, two environments, both green | journal lists the last to finish twice | two entries, each its own environment |
| one green, one red (`--keep-going`) | both journaled red; stderr names the green one red | the red one red, the green one ok |
| both lanes' logs | one `a.log`, last writer wins | `a@inv.log`, `a@other.log` |
| a stop terminates one of the two | both marked terminated (by task) | only the terminated lane is cancelled |
| a dependent of the red twin | `cancelled_by: a` | `cancelled_by: a`, `cancelled_by_environment: other` |
| a pause on one of the two | both dropped; only the paused one journaled | the other runs |
| a step `pixi run -e E mypy` | counts for `mypy` in every environment | unchanged: a bare lane's environment is the invoking one |
| one verdict selects `a`@`inv`, one skips `a`@`other` | both dropped or both kept by any task-keyed filter | only `a`@`inv` runs; both journaled with their environment |
| budget, one station test in two environments | one station lane | two lanes |
| an old journal entry without `environment` | labelled by task | labelled by task |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-159 (the preflight: lane list, selection, concurrent runner,
  journal, budget). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-14 (CI and estate follow-ups) entry, its
  preflight lane identity addition.
- Epic: Epic 103. Epics 71, 88, 90 and 98, which shipped CAP-159 and its fixes, are `done`.
- Ledger key: `103-5-the-preflight-keys-each-lane-by-its-task-and-its-environment`.
- Ledger status at mint: `backlog`.
- Deps: none. Atlas Story 31.1 (PR #2221) needs this story to land first for its `steward-test` to pass.
- Spec: the `spec-pyforge-steward` memlog records the approval, the evidence, the design and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."103"` already covers `src/shared/packages/pyforge-steward/**`.
- Minted 2026-10-14 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass. This is the station's
  `verify_commands` (MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit -q -k preflight` — expected: exit 0 (AC1-AC8, AC10).
- `git checkout origin/dispatch/pyforge-atlas/31.1 -- pixi.toml .github/workflows/lint-types.yml`, then `pixi run --frozen -e pyforge-steward pyforge-steward-test`, then `git checkout HEAD -- pixi.toml .github/workflows/lint-types.yml` — expected: exit 0, and `git status --short` empty after (AC9).
- The AC11 mutations, one at a time, re-running the named test each time — expected: each fails the named test. Revert each.
- `pixi run -e pyforge-steward pyforge-steward-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (AC12).
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0.

## Implementation Result

Hand-implemented on branch `chain-steward-103-5-preflight-lane-identity-2026-10-14`, from baseline `22e5c19c28`.
The diff is for an independent review against this spec, not against this summary.

- **Per-lane state** (`preflight.py`):
  - `results_by_key` replaces `results_by_task`, and `lane_label` names each lane's scratch directory and log.
  - `_RunCoordinator.red_lanes`, `terminated_lanes`, `proc_lane`, `suite_reduction_runtime_journal` and
    `xdist_workers` are keyed by lane. `stop_cause` holds the cause, and `stop_trigger` is now a read-only property.
  - `LaneResult` adds `cancelled_by_environment` and `blocked_by_environment`.
  - The pause filter checks `paused_keys`. The banner still de-duplicates by task, and the code says why.
- **Budget and xdist:** `preflight_budget.py` keys and labels lanes by pair, and `preflight_xdist.py` keys shares by
  lane.
- **Selection:** `_step_matches` changed only its docstring (Approach, amended).
- **Tests:** the new `test_preflight_lane_identity.py` (AC1-AC6, AC8, AC10). Existing checks moved from task names to
  lane keys and labels in `test_preflight_selection.py` (AC7), `test_preflight_concurrency.py`,
  `test_preflight_scratch.py`, `test_preflight_suite_reduction.py`, `test_preflight_workers.py` and
  `test_preflight_ci.py`.
  - Two `if late_pgid.is_file()` guards now point at the lane label, so they keep asserting.
  - `test_preflight_ci.py`'s two pause tests now run in the environment their paused lane names. Task keying had hidden
    that mismatch.
- **AC9:** with `origin/dispatch/pyforge-atlas/31.1`'s `pixi.toml` and `.github/workflows/lint-types.yml` checked out,
  `pixi run --frozen -e pyforge-steward pyforge-steward-test` exited 0: 2616 passed, 2 skipped. Both files were then
  restored, and `git status` showed neither.
- **AC11:** each mutation failed named tests in `test_preflight_lane_identity.py`:
  - results keyed by task failed `test_both_lanes_of_one_task_run_and_journal_their_own_results`,
    `test_each_lane_of_one_task_writes_its_own_log` and both `test_a_stop_names_the_environment_of_the_lane_that_caused_it`
    cases;
  - `<task>.log` failed the first two of those;
  - the pause filter by task failed `test_a_pause_on_one_lane_leaves_its_twin_running`;
  - dropping the blocker's environment failed both `test_a_stop_names_the_environment_of_the_lane_that_caused_it` cases.
- **Green:**
  - `pixi run --frozen -e pyforge-steward pyforge-steward-test`: exit 0, 2616 passed, 2 skipped.
  - `pixi run --frozen -e pyforge-guild lint-types`: exit 0.
  - The coverage gate and `pr-preflight` are recorded on the PR.

## Review

The independent review (2026-10-14) of PR #2225 at `8dd1fd00ad` returned **PASS**, with one should-fix and five
nits. The reviewer's mutants and logs are in the orchestrating session's scratch (`r103-5/`). Each finding below has
its resolution; the fixes land on the same branch.

- **1 (should-fix) — Two re-keyed coordinator paths were untested.**
  - **Finding:** two mutants passed all 270 preflight tests: comparing terminated marks by task again at both
    `key in coord.terminated_lanes` sites (m5), and dropping `cancelled_by_environment=trigger_env` from the
    terminated-lane result (m6). Neither `_skip_lane_on_red_stop` path in `_run_lane_in_pool` had an assertion; only
    the dependency-blocked path was covered.
  - **Resolution:** three tests in `test_preflight_lane_identity.py`:
    - `test_a_stop_marks_only_the_twin_it_terminated`: `fail` goes red, its stop terminates `a`@inv, and `a`@other,
      which already exited on its own, stays `ok`; `coord.terminated_lanes == {("a", "inv")}`.
    - `test_a_lane_the_stop_keeps_from_starting_names_its_twin`: the first stop check.
    - `test_a_lane_stopped_while_it_waits_for_its_service_names_its_twin`: the second stop check, after the service
      lock; deterministic through a lock that signals its waiter.
    - `test_real_subprocess_red_lane_cancels_running_peer` also asserts `cancelled_by_environment`.
  - **Mutants, re-run against `test_preflight_lane_identity.py` and `test_preflight_concurrency.py`; each now fails:**
    - m5 fails `test_a_stop_marks_only_the_twin_it_terminated`;
    - m6 fails it and `test_real_subprocess_red_lane_cancels_running_peer`;
    - m7 (no environment on the first stop check) fails `test_a_lane_the_stop_keeps_from_starting_names_its_twin`;
    - m8 (no environment on the second stop check) fails
      `test_a_lane_stopped_while_it_waits_for_its_service_names_its_twin`.
- **2 (nit) — The interrupt clause of AC4 was checked only on a hand-built `LaneResult`.**
  **Resolution:** `test_sigint_cancels_real_subprocess_lanes` asserts that no cancelled journal entry carries
  `cancelled_by_environment`.
- **3 (nit) — The comment said the stop cause is "assigned once", but the code checked and set it without a lock.**
  - **Resolution:** a new `_RunCoordinator.set_stop_cause` checks and sets under a dedicated reentrant `stop_lock`,
    and both callers (the red lane and the SIGINT handler) use it. `test_the_first_stop_cause_wins` covers it.
  - **Why not `proc_lock`:** the handler runs on the main thread and may re-enter, and `proc_lock` is a plain lock
    the handler already takes through `terminate_children`.
- **4 (nit) — The suite reduction is applied by task across environments.**
  **Resolution:** the `suite_lane_plan` comment says so and names the case where it would matter: a station test in
  two environments while its coverage gate runs in one.
- **5 (nit) — Atlas 31.1's two `mypy` lanes share `.mypy_cache` when they run concurrently.**
  **Resolution:** not changed here; the orchestrating session tracks it separately.

## Spec Change Log

- 2026-10-14: minted from the Dream's preflight lane identity addition, under the operator's standing direction of
  2026-10-14. `type: fix`, no flag, no CAP. Bound to `spec-pyforge-steward` CAP-159.
- 2026-10-14 (implementation): the environment-aware CI-counterpart match was dropped (Approach, amended; AC6
  restated; AC11's closure mutation replaced). It moved no verdict and failed `test_service_lanes_never_overlap`.
- 2026-10-14 (review): PASS with one should-fix and five nits; four resolved on the branch, nit 5 tracked separately
  (§ Review). No AC changed.
