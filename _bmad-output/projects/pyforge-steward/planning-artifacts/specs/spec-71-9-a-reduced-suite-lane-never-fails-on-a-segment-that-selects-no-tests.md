---
title: "71.9: A reduced suite lane never fails on a segment that selects no tests"
type: 'fix'
created: '2026-10-08'
status: 'done'
baseline_revision: '5525712c62b310d8f0a499e3ac08296234e762eb'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-4-a-station-s-coverage-gate-reuses-its-own-suite-s-run.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-8-a-preflight-lane-s-scratch-lives-outside-the-checkout.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_suite_reduction.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_suite_reduction.py
  - scripts/coverage_gates_ci.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 71.4's reduced suite lane reds on a segment that selects no tests. Every station it reduces is
affected: four lanes exit 5, and the fifth runs a test its own task excludes. 71.4's partition test cannot catch
either, because the sets it compares are always empty.

- **How a lane is reduced.** `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_suite_reduction.py`:
  `_build_reduced_shell_cmd` (`:203`) builds two segments. The first runs the task's test directories that the gate
  does not run, under the task's own marker (`:212`-`:223`). The second runs the gate's directories under
  `_complement_marker` (`:224`-`:228`). They are joined with ` && ` (`:231`), and `derive_suite_lane_override` runs
  the result as one `bash -lc` (`:316`), so the lane gets one exit code. The gate runs `unit` and `meta`
  (`scripts/coverage_gates_ci.py:140`) under `GATE_MARKER_EXPR = "not slow"` (`:271`). Its pytest exit code,
  including 5, fails the gate on its own (`:417`-`:422`).
- **Defect 1: an empty segment reds the lane.** With no task marker, `_complement_marker` returns `slow` (`:200`).
  Where `unit` and `meta` hold no `slow` test, the second segment deselects everything, pytest exits 5, and the lane
  is red. The station's own task passes.
- **Defect 2: an equal marker runs excluded tests.** If the task's marker equals the gate's, the complement is still
  `slow` (`:196`-`:197`). The remainder is empty, yet the lane runs `slow` tests that the task deselects and CI's
  station job never runs.
- **Defect 3: the partition test is vacuous.** `collect_pytest_node_ids` (`:383`) rewrites `pytest` as
  `pytest --collect-only -q` (`:391`) in commands that already pass `-q`. At `-qq` pytest prints per-file counts
  (`path: N`), and the parser keeps only lines containing `::`, so it returns an empty set. It also raises on any
  non-zero exit (`:399`-`:400`), including 5. As a result, `test_reduced_and_gate_collections_partition_task`
  (`tests/unit/test_preflight_suite_reduction.py:66`) compares empty sets and passes for both parametrizations. Its
  `-m "not slow"` case would fail on real node ids, because of defect 2. Reproduced on `875f418334` with the test's
  own fixture: all three sets are empty.
- **Measured, per station**, on `875f418334`. Each reduced lane was derived with `derive_suite_lane_override` from a
  gate plan for that station's `unit` suite, and each gate-directory segment was run as the lane runs it
  (`pixi run --frozen -e pyforge-<s> python -m pytest <unit> <meta> -q -m slow`):

  | Station | Reduced lane | Gate-directory segment |
  |---|---|---|
  | doctor | that segment alone | exit 5, 3494 deselected |
  | scribe | that segment alone | exit 5, 440 deselected |
  | herald | `integration` (5 passed), then that segment | exit 5, 1738 deselected |
  | warden | `integration -m "not slow"`, then that segment | exit 5, 2001 deselected |
  | marshal | `integration -m "not slow"`, then that segment | runs 1 test the task excludes (below) |
  | steward | not reduced: `tests/unit/test_sprint_ledger_query.py` imports `fleet_scan` | — |
  | atlas, mason | not reduced: a two-command task (atlas also imports `scripts/`) | — |
  | core | no coverage gate | — |

  The marshal test is
  `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_spin.py::test_spin_recovers_the_run_id_from_a_real_unbuffered_subprocess`
  (`@pytest.mark.slow` at `:251`), which `pyforge-marshal-test`'s `-m "not slow"` (`pixi.toml:736`) excludes.
- **Observed in a live run** on 2026-10-08, on a one-file herald branch (`hygiene-herald-shelf-two-headings`):
  - `pixi run --frozen -e pyforge-guild pr-preflight -- --keep-going` journaled `pyforge-herald-test` exit 5 after
    12.4 s. The lane log ends `5 passed`, then `1738 deselected`.
  - `pixi run --frozen -e pyforge-herald pyforge-herald-test` passes 1739.
  - Without `--keep-going`, that red stopped the run, and `pyforge-herald-coverage-gate`, terminated, was journaled
    `-15 red` (two runs).

  So, since 71.4 landed, any branch that selects one of these stations' suite and gate lanes is refused by the
  `pre-push` hook.
- **Adjacent, not in this story.** A lane the coordinator terminates is journaled `red` with its signal exit
  (`preflight.py:336`-`:342` treat every non-zero exit as red). Story 71.3's AC says such lanes are journaled
  `cancelled`. That finding is recorded on the Dream and waits for its own fix story.

**Approach:**

- **Exit 5 from a segment the reduction added counts as passed.** This is the chosen mechanism, rather than skipping
  segments whose `--collect-only` selects nothing, for four reasons:
  - Pytest decides at run time, on the same tree and arguments that run, inside the lane's own slot. A plan-time
    collection would sit, serially, ahead of every lane: herald's gate directories took 1.9 s to collect and
    marshal's 9.9 s, measured against Story 71.7's 60 s budget.
  - Exit 5 is pytest's own "no tests were collected" code (`ExitCode.NO_TESTS_COLLECTED`). It is the exact signal,
    and every other non-zero exit still reds.
  - Nothing can drift between a collection and the run.
  - `collect_pytest_node_ids` could not serve the other route as written: it raises on 5 and returns empty sets.
- **Segments run as separate processes.** `SuiteLaneOverride` carries the lane's segments as data: each segment's
  argv after `pixi run --frozen -e <env>`, and a label (`rest-of-task` or `gate-dirs-complement`). The single
  `bash -lc` string goes away.
  - The runner (`preflight._subprocess_lane`, `:238`) runs the segments in order, each as its own process. Each one
    writes to the lane's log, and each is registered for termination as today.
  - A segment that exits 5 is `no-tests-selected` and counts as passed. Any other non-zero exit is `failed`: it ends
    the lane with that exit code, and the later segments are `not-run`.
  - No segment starts once the run is cancelled or stopped on red.
  - Why separate processes: the journal needs each segment's exit code, and a `&&` chain yields only one.
- **The station's own empty selection is not masked.** If every segment ends `no-tests-selected`, the runner runs the
  station task's own collection: its command with `--collect-only` appended, as `pixi run --frozen -e <env> <task>
  --collect-only` passes it. Its exit code becomes the lane's: 0 when the task collects anything, and 5 (red) when it
  collects nothing, as CI's station job would report. A lane run whole, with no override, keeps pytest's exit 5 as
  today.
- **An equal marker adds no gate-directory segment.** `_complement_marker` returns no complement when the task's
  marker equals the gate's. The no-marker (`slow`) and different-marker (`(task) and not (gate)`) results are
  unchanged. If no segment remains, `derive_suite_lane_override` returns `None` and the lane runs whole, journaled
  as today (`no reducible overlap with gate unit plan`).
- **Real node ids.** `collect_pytest_node_ids` drops the command's own `-q`/`-qq` before adding `--collect-only -q`,
  so it reads node ids. It treats exit 5 as an empty set, and still raises on any other non-zero exit.
- **The journal.** The lane's entry gains `suite_reduction_segments`: one `{label, command, exit_code, outcome}` per
  segment, with `outcome` one of `passed`, `no-tests-selected`, `failed` or `not-run`. When the collection check
  ran, it also gains `suite_reduction_task_collect_exit`. Both are additive fields; Story 71.7 reads only `seconds`
  and `status`.

Ledger key: `71-9-a-reduced-suite-lane-never-fails-on-a-segment-that-selects-no-tests`.
Type / Effort / Deps: fix / M / S-71.8.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (FR-32): "A station's suite lane skips the tests its
  coverage gate's own run already covers, so every test runs once and the floor stays the driver's verdict". Story
  71.4 built it, citing CAP-159 (FR-32), with `spec-coverage-gate-independence` CAP-1 (the driver) as Kinship. Its
  AC is that the gate's run and the reduced run are disjoint and together equal the task's own collection. This fix
  makes that AC hold and makes its test able to fail. It mints no CAP and changes no `SPEC.md` text.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.
- **Deps.** S-71.8, which edits `preflight.py`'s lane environment and through it follows 71.5-71.7. At
  `875f418334`, none of 71.5-71.8 touches `preflight_suite_reduction.py`. Story 71.6 adds `-n auto` to some station
  tasks: `_parse_single_pytest` keeps `-n` in each segment, and pytest-xdist still exits 5 when nothing is selected.

## Acceptance Criteria

- **(1) An empty gate-directory segment passes.** Given a fixture station with `tests/unit`, `tests/meta` and
  `tests/integration`, no `slow` test, a task `pytest <tests> -q` and a gate plan for `unit` and `meta` under
  `not slow`. When `derive_suite_lane_override` builds the lane and the runner runs it, with the pixi prefix replaced
  in the test by the current interpreter. Then the lane exits 0, and the journal lists `rest-of-task` `passed` and
  `gate-dirs-complement` `no-tests-selected` (exit 5).
- **(2) A failing test in a kept segment still reds.** Given the same fixture with one failing test in
  `integration`. When the lane runs. Then it exits 1, `rest-of-task` is `failed` and `gate-dirs-complement` is
  `not-run`. And a failing `slow`-marked test in `unit` reds the lane with `gate-dirs-complement` `failed`.
- **(3) The herald and doctor shapes, end to end.**
  - Given a fixture repo shaped like herald (`unit`, `meta`, `integration`, no `slow` test, a no-marker task),
    with both `pyforge-<name>-test` and `pyforge-<name>-coverage-gate` selected, and `_read_gate_plan` returning the
    driver's plan for it. When `build_suite_lane_overrides` builds the plan and `run_preflight` runs the lane
    through the segment runner. Then the lane is `ok`, the run exits 0, and the journal shows both segments as in
    (1).
  - For a fixture shaped like doctor and scribe (`unit` and `meta` only), the one segment is `no-tests-selected`,
    `suite_reduction_task_collect_exit` is 0, and the lane exits 0.
- **(4) The station's own empty selection is not masked.**
  - Given a fixture task whose own registered marker selects no test. When its reduced lane runs. Then every
    segment is `no-tests-selected`, the task's collection exits 5, and the lane exits 5 (red).
  - Given a lane run whole whose pytest exits 5. Then the lane is red, as today.
- **(5) An equal marker partitions exactly.** Given a task `-m "not slow"` and a `slow` test in `unit`. When the
  lane is derived. Then it has no `gate-dirs-complement` segment. By node ids, the gate's collection and the reduced
  collection are disjoint, their union equals the task's collection, every one of those sets is non-empty, and the
  `slow` unit test is in none of them.
- **(6) `collect_pytest_node_ids` reads node ids.** For a command that already passes `-q` it returns node ids, it
  returns an empty set for pytest exit 5, and it raises for any other non-zero exit.
  `test_collect_pytest_node_ids_raises_on_failure` (`:403`) still passes.
- **(7) Existing tests still pass.** The 71.1-71.4 preflight tests pass with two named changes only:
  - `test_complement_marker_variants` (`:151`-`:154`) expects no complement for equal markers at `:152`;
  - `test_reduced_and_gate_collections_partition_task` (`:66`) also asserts that every set it compares is non-empty.
- **(8) Mutations fail the new tests.**
  - Removing the exit-5 mapping fails (1) and (3).
  - Restoring `slow` for equal markers fails (5).
  - Restoring the doubled `-q` fails (5) and (6).
  - Removing the collection check fails (4).

## Boundaries & Constraints

**Always:**
- Change only `preflight_suite_reduction.py`, `preflight.py` (the segment runner and the lane's journal entry) and
  their unit tests under `src/shared/packages/pyforge-steward/tests/unit/`.
- Map only pytest exit 5, and only for segments of a reduced lane.
- Keep 71.4's skip rules unchanged: a two-command task, a `scripts/` import, no plan, and no gate lane each run the
  lane whole.
- Stdlib only.

**Never:**
- Never change `scripts/coverage_gates_ci.py`, its plan, its marker or its verdict, or any `pixi.toml` task.
- Never change which lanes run (Story 71.2).
- Never skip, deselect or `xfail` a test to make a lane pass.
- Never treat a lane run whole as reduced.
- Never change how a terminated lane is journaled (the adjacent finding above), or 71.8's scratch location.
- Never hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

**At landing:** `preflight.py` and `preflight_suite_reduction.py` are in the surfaces of `spec-pyforge-steward` and
`spec-pyforge-core`, and `test_preflight_suite_reduction.py` in `spec-pyforge-steward`'s. Append the reconcile to
each Spec `spec-surface-check` names, then one scoped stamp each (AGENTS.md § Pre-PR item 5).

## I/O & Edge-Case Matrix

| Reduced lane | Segment results | Lane |
|---|---|---|
| herald, warden shape | `rest-of-task` 0, `gate-dirs-complement` 5 | 0 |
| doctor, scribe shape | `gate-dirs-complement` 5; task collects | 0 |
| any shape | every segment 5; task collects nothing | 5 (red) |
| any shape | `rest-of-task` 1 | 1; the next segment `not-run` |
| any shape | `gate-dirs-complement` 1 | 1 |
| marshal shape (equal marker) | `rest-of-task` only | its exit code |
| run cancelled mid-lane | current segment terminated | no later segment starts |
| lane run whole (no override) | pytest 5 | 5 (red), unchanged |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-08 (suite reduction) entry.
- Epic: Epic 71 (CAP-159, FR-32; `in-progress`, 71.5-71.8 `backlog`).
- Ledger key: `71-9-a-reduced-suite-lane-never-fails-on-a-segment-that-selects-no-tests`.
- Ledger status at mint: `backlog`.
- Deps: S-71.8 (and through it 71.5-71.7).
- Spec: `spec-pyforge-steward/.memlog.md` records the mint; `SPEC.md` untouched.
- Surface: `preflight_suite_reduction.py`, `preflight.py`, and their unit tests. Epic 71 declares no
  `[epic_surfaces]` entry in steward's `marshal-policy.toml`, so marshal's derived default applies
  (`src/shared/packages/pyforge-steward/**` among it). Every path here is inside it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- On a one-file herald branch, run `pixi run -e pyforge-guild pr-preflight -- --keep-going` and then run it
  without the flag. Expected: `pyforge-herald-test` is `ok`, its journal entry shows `gate-dirs-complement`
  `no-tests-selected`, `pyforge-herald-coverage-gate` is `ok`, and the run exits 0.
- The same on one-file doctor, scribe and warden branches. Expected: each reduced lane is `ok`.
- On a one-file marshal branch, run the same. Expected: the marshal suite lane's log does not contain
  `test_spin_recovers_the_run_id_from_a_real_unbuffered_subprocess`.
- `pixi run --frozen -e pyforge-steward python -m pytest
  src/shared/packages/pyforge-steward/tests/unit/test_preflight_suite_reduction.py -q -rA`. Expected: pass, with
  `test_reduced_and_gate_collections_partition_task` comparing non-empty sets.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- No change yet.

## Review Triage Log

### 2026-10-09 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none)

## Auto Run Result

Status: done

Summary: Reduced suite lanes run each pytest segment as its own process; pytest exit 5 on a reduction segment counts as `no-tests-selected` (lane still ok). Equal task/gate markers omit the gate-directory segment. `collect_pytest_node_ids` strips duplicate `-q` and treats exit 5 as an empty set. Journal entries include `suite_reduction_segments` and optional `suite_reduction_task_collect_exit`.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_suite_reduction.py` — segment model, complement fix, collection helper
- `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py` — multi-segment runner and runtime journal merge
- `src/shared/packages/pyforge-steward/tests/unit/test_preflight_suite_reduction.py` — AC coverage and partition non-empty asserts

Review: no findings; no patches or deferrals.

Verification:
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — pass (2238 tests after fix)
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_suite_reduction.py -q` — 23 passed
- `python scripts/spec_surface_reconcile.py` — OK

Surface reconcile memlog paths (Story 71.9):
- `spec-pyforge-steward/.memlog.md`: `preflight_suite_reduction.py`, `preflight.py`, `test_preflight_suite_reduction.py`
- `spec-pyforge-core/.memlog.md` (co-governor): `preflight_suite_reduction.py`, `preflight.py`

Residual risk: live herald/doctor/scribe/marshal branch preflight smoke checks listed under Manual checks were not run in this dispatch.
