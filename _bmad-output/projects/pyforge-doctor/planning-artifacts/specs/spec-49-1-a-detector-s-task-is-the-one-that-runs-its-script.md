---
title: "49.1: A detector's task is the one that runs its script"
type: 'fix'
created: '2026-10-17'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-3-pyforge-ci-is-stdlib-only-as-its-tasks-say.md
  - docs/dreams/pyforge-doctor.md
  - scripts/detectors.py
  - scripts/docs_detectors.py
  - tests/scripts/test_pyforge_ci_is_stdlib_only.py
  - tests/scripts/test_detectors_doctor_sources.py
  - tests/scripts/scripts-lib-test.txt
  - pixi.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `scripts/detectors.py`'s `discover()` gives a scanned detector the first pixi task whose `cmd` contains
the detector's file name. The test is a substring test (`scripts/detectors.py:166`-`:167` at `ab38be642f`):

```python
task = next((t for t, c in tasks.items()
             if path.name in c and "--json" not in c), None)
```

`test_flag_gate_check.py` contains `flag_gate_check.py`, so a task earlier in `pixi.toml` order whose `cmd` names
`tests/scripts/test_flag_gate_check.py` becomes `flag_gate_check`'s task. Steward Story 103.3's independent review of
`b1270318ed` saw it: with `scripts-lib-test`'s 32 files written inline in its `cmd`, six detectors mapped to
`scripts-lib-test`, and `tests/scripts/test_flag_gate_check.py::test_the_registry_discovers_the_gate_as_a_repo_detector_with_its_pixi_task`
failed (`assert 'scripts-lib-test' == 'flag-gate-check'`). Story 103.3 moved the list into a pytest argument file
(`tests/scripts/scripts-lib-test.txt`) and pinned only its own library tasks
(`tests/scripts/test_pyforge_ci_is_stdlib_only.py:677`, `test_no_detector_maps_to_a_library_task`). The matcher stayed,
and the review filed `DW-doctor-103-3-1` with Doctor, which owns the registry's task mapping (FR-15, Story 6.2).

**The evidence, measured at `ab38be642f`:**
- The live registry finds 28 scanned detectors, with no registry finding, and each maps to its own task. Every one of
  those 28 tasks runs `python scripts/<name>.py`; two add a flag (`pin-policy-check` and `ci-surface-gates-check`,
  each `--check`). One detector's path is in a second task as well: `bmad-cursor-mdc-generate` runs
  `python scripts/bmad_cursor_mdc_check.py --write`, after `bmad-cursor-mdc-check` in feature order.
- With the 36 files of `tests/scripts/scripts-lib-test.txt` inline in one task placed first, nine detectors map to
  it: `bmad_estate_check`, `bmad_loop_baseline_drift_check`, `cfe_rebuild_guard_check`, `ci_surface_gates`,
  `failure_catalog_check`, `flag_gate_check`, `pin_policy_check`, `realization_register_check` and
  `upstream_todos_check`. The review saw six with 32 files; the list has grown since.
- The registry never runs a task: `run_one` runs `sys.executable <ROOT>/<path>` (`scripts/detectors.py:450`). The
  `DW-doctor-103-3-1` summary's "`detectors-ci` runs that task (a pytest run) as the detector's verdict" is not what
  the code does. The task is what `--list` and `--json` print, what `docs/reference/detectors.md` names
  (`scripts/docs_detectors.py:88`), and what the registry's own gap check reads: a detector with no task is the finding
  "declares scope=… but has no pixi task" (`scripts/detectors.py:168`-`:171`). A wrong match hides that gap. If a
  detector's own task is removed while any task names its test file, the detector still reads as tasked, and nothing
  reds.

**Approach:**
1. A task runs a detector when its `cmd` holds the detector's repo-relative path (`rel`, already computed in
   `discover()`), optionally prefixed `./`, as one shell word. The character before the path is the start of the
   `cmd`, whitespace or a quote; the character after it is the end of the `cmd`, whitespace, a quote, or one of
   `;`, `&`, `|`, `)`. A new helper, `_runs_detector(cmd, rel)`, holds the rule. `discover()` keeps its order (first
   match in `_pixi_tasks()` order) and its `--json` skip.
2. The path, not the bare file name. The row's suggested `(?<![\w])<name>` would stop `test_flag_gate_check.py`, but
   would still take `tests/scripts/flag_gate_check.py` or `vendor/flag_gate_check.py`, which are other files. The
   registry runs `ROOT / rel`, so the task that runs the detector names `rel`.
3. A new stdlib-only test file, `tests/scripts/test_detectors_task_match.py`, runs in `pyforge-ci`
   (`pyforge-doctor-scripts-test`, which runs all of `tests/scripts`). It reproduces the capture, the hidden gap and the
   boundary cases, and checks the live tree.
4. Steward's `test_a_library_task_listing_a_detectors_test_inline_is_named` asserts the capture this story removes, so
   it fails on the fix. It is changed in place and renamed for what it now checks,
   `test_a_library_task_is_named_when_it_runs_a_detector_not_when_it_lists_its_test`: the inline listing maps no
   detector, and a library task that runs a detector's script is still named. Its helper
   `detectors_run_by_a_library_task` keeps its rule; its docstring and message say what is true after the fix.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-doctor` FR-15 (PRD § FR-15, "Doctor holds the verdict for every conformance
  detector"): Story 6.2 built the registry Doctor owns, with its "declares scope but has no pixi task" gap, and Story
  6.9 its run path. No CAP of `spec-pyforge-doctor` names `scripts/detectors.py`; the same binding closed the
  registry's declared half (`DW-FU-6-9-3`, Story 41.2: "FR-15 (Stories 6.2, 6.4, 6.9, 20.3)") and Story 6.12 ("FR-15
  (Story 6.8)"). No CAP is minted, and no `SPEC.md` text changes.
- **No flag.** A `fix` (`spec-feature-flag-governance` Q1): it restores the registry's intended mapping. Q2's closed
  exemption list binds only `type: feature`, so no `flag-exempt:` value is needed.
- **Origin.** `docs/dreams/pyforge-doctor.md` § Realization log, 2026-10-17 (the detector registry finds a detector's
  task by its path); steward Story 103.3's independent review, 2026-10-17, out-of-surface defect (b).
- **`DW-FU-6-9-3`, how it relates.** Same file, other half. `DW-FU-6-9-3` (resolved by Story 41.2,
  `tests/scripts/test_detectors_doctor_sources.py:287`) pins the declared half: each `_DOCTOR_SOURCE_TASKS` task is a
  `pixi.toml` task running its own source. Its summary called the scanned half's task cross-reference a "free" check;
  this story makes that cross-reference sound. `_DOCTOR_SOURCE_TASKS` and its test do not change, and `DW-FU-6-9-3`
  stays resolved.

## Acceptance Criteria

- **AC1 — The path, as one word.** `discover()` gives a detector the first task, in `_pixi_tasks()` order, whose
  `cmd` contains no `--json` and holds `rel` (or `./` + `rel`) as one shell word: preceded by the start of the `cmd`,
  whitespace, `"` or `'`, and followed by the end of the `cmd`, whitespace, `"`, `'`, `;`, `&`, `|` or `)`.
- **AC2 — The capture is gone.** With a task placed first whose `cmd` lists the files of
  `tests/scripts/scripts-lib-test.txt` inline, no detector maps to it, every detector keeps its live task, and the
  inline `cmd` contains the file name of `flag_gate_check.py` and of the other detectors the old matcher took. With a
  task placed first that runs only `pytest tests/scripts/test_flag_gate_check.py`, `flag_gate_check` maps to
  `flag-gate-check`.
- **AC3 — A hidden gap is named.** With `flag-gate-check` removed and a task left whose `cmd` names
  `tests/scripts/test_flag_gate_check.py`, `flag_gate_check`'s task is `None` and the registry reports
  `scripts/flag_gate_check.py: declares scope=repo but has no pixi task`.
- **AC4 — Boundaries.** For `rel = scripts/flag_gate_check.py`, `_runs_detector` is true for
  `python scripts/flag_gate_check.py`, `python ./scripts/flag_gate_check.py --check`,
  `python "scripts/flag_gate_check.py"`, `python 'scripts/flag_gate_check.py'`,
  `python scripts/flag_gate_check.py && echo ok`, `(python scripts/flag_gate_check.py)` and
  `python scripts/flag_gate_check.py;echo ok`; it is false for `pytest tests/scripts/test_flag_gate_check.py`,
  `python tests/scripts/flag_gate_check.py`, `python vendor/scripts/flag_gate_check.py`,
  `python xscripts/flag_gate_check.py`, `python scripts/flag_gate_check.pyc`, `python scripts/flag_gate_check.py.bak`
  and `python scripts/flag_gate_check_v2.py`.
- **AC5 — The `--json` skip stays.** With a task placed first whose `cmd` is `python scripts/flag_gate_check.py --json`,
  `flag_gate_check` maps to `flag-gate-check`.
- **AC6 — The whole scan.** On a fixture tree (its own `pixi.toml`, one `scripts/*_check.py` and one
  `docs/dashboard/check_*.py` detector, and a task listing the first one's test file ahead of its own task), each
  detector maps to the task that runs its path, with no registry finding.
- **AC7 — The live tree.** On the live tree `discover()` reports no registry finding; each of the 28 detectors maps to
  the task it maps to at `ab38be642f` (a table in the test; a retired detector drops its row); and every detector's
  task, the 28 and any added later, runs that detector's path by AC1's rule.
- **AC8 — Steward's guard says what is true.** `test_a_library_task_listing_a_detectors_test_inline_is_named`, renamed
  `test_a_library_task_is_named_when_it_runs_a_detector_not_when_it_lists_its_test`, asserts that a library task
  listing `tests/scripts/test_flag_gate_check.py` inline maps no detector, and that a library task whose `cmd` also
  runs `python scripts/flag_gate_check.py` is named, with a message that does not tell the author to move files into
  an argument file. `detectors_run_by_a_library_task`'s docstring describes the path match.
  `test_no_detector_maps_to_a_library_task` is unchanged and passes.
- **AC9 — Stdlib only, lanes green.** The new test imports only the standard library and `pytest`.
  `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` and `pixi run --frozen -e pyforge-guild
  scripts-lib-test` exit 0 (`test_pyforge_ci_is_stdlib_only.py` passes in both). `detectors-ci` has no new finding,
  and `docs/reference/detectors.md` is unchanged (`docs_detectors.py --check` exits 0).
- **AC10 — Mutation.** Each change below fails a named test in the new file. Restore each.
  - the substring matcher restored (`path.name in c`);
  - the left boundary dropped;
  - the right boundary dropped;
  - the bare file name matched with both boundaries (the row's first option);
  - the `--json` skip dropped;
  - the optional `./` prefix dropped.
- **AC11 — The row closes.** `DW-doctor-103-3-1` reads `status: closed`, with a `closed:` line citing this story, the
  tests and the evidence.

## Boundaries & Constraints

**Always:**
- Every live detector keeps the task it maps to at `ab38be642f`; no registry finding appears or disappears on the
  live tree.
- Read every verdict from the exit code, never through a pipe.
- Kill each new rule with a mutation on a scratch copy, never in the worktree.
- Reconcile every governed path on the memlogs of the Specs that govern it, then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never change `run_one`, the scope split, the `--json` skip, `_DOCTOR_SOURCE_TASKS` or `_run_doctor_sources`.
- Never import a library in `scripts/detectors.py` or the new test; `pyforge-ci` stays stdlib-only (steward Story 103.3).
- Never edit `pixi.toml`, `.github/workflows/` or `docs/reference/detectors.md`.

**Residual risk:**
- A task that runs a detector through another spelling (an absolute path, `$PIXI_PROJECT_ROOT/scripts/…`, or `cd
  scripts && python x_check.py`) no longer counts. None does today. Such a detector reads as a registry gap, which is
  loud, never a silent wrong match.
- The first match still wins when two tasks run a detector (`bmad-cursor-mdc-check` before `bmad-cursor-mdc-generate`).
  That is today's behaviour, and the live table pins it.

## I/O & Edge-Case Matrix

| Tasks (first first) | `flag_gate_check` maps to | Registry finding |
|---|---|---|
| the live tasks | `flag-gate-check` | none |
| `lib: pytest tests/scripts/test_flag_gate_check.py …`, then the live tasks | `flag-gate-check` | none |
| `lib: pytest <36 files inline>`, then the live tasks | `flag-gate-check` (and each detector its own) | none |
| the live tasks without `flag-gate-check`, plus `lib: pytest tests/scripts/test_flag_gate_check.py` | `None` | `scripts/flag_gate_check.py: declares scope=repo but has no pixi task` |
| `j: python scripts/flag_gate_check.py --json`, then the live tasks | `flag-gate-check` | none |
| `o: python tests/scripts/flag_gate_check.py`, then the live tasks | `flag-gate-check` | none |

</intent-contract>

## Binding

- Parent: `spec-pyforge-doctor` FR-15 (Stories 6.2 and 6.9). No CAP of the Spec names `scripts/detectors.py`; no CAP
  is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-17 entry (the detector registry finds a
  detector's task by its path).
- Epic: Epic 49 (new), minted with this story. Epic 6, which built the registry, is `done`.
- Ledger key: `49-1-a-detector-s-task-is-the-one-that-runs-its-script`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Closes: `DW-doctor-103-3-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."49"`, added with this mint. `scripts/detectors.py` stays allowlisted
  "governed by none" (`scripts/spec_surface_allowlist.txt:54`); whether `spec-pyforge-doctor` should claim it is named
  below for the coordinator.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_detectors_task_match.py -q` — expected: pass
  (AC1-AC7, AC9's import rule).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`;
  MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: exit 0 (AC9).
- `pixi run --frozen -e pyforge-guild scripts-lib-test` — expected: exit 0 (AC8, AC9).
- `pixi run --frozen -e pyforge-guild python scripts/docs_detectors.py --check` — expected: exit 0 (AC9).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new findings against `main`.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- `pixi run --frozen -e pyforge-guild tea-playwright-check` — expected: exit 0 after the Story Coverage Matrix is
  regenerated for Story 49.1.
- `pixi run --frozen -e pyforge-guild chain-currency-sweep-check` — expected: exit 0 after the PRD and spine
  re-stamps.
- The six mutations of AC10, on a scratch copy — expected: each fails a named test. Restore each.

## Named, not fixed here

- **`pixi.toml:1369`-`:1372` gives the old matcher as the reason for the argument file.** The `scripts-lib-test`
  comment reads "scripts/detectors.py maps a detector to the first task whose `cmd` contains its file name, and
  `test_flag_gate_check.py` contains `flag_gate_check.py`". After this story that sentence is history. The argument
  file stays useful (`test_pyforge_ci_is_stdlib_only.py` reads it), so only the comment's reason is stale. `pixi.toml`
  is not edited here: a `pixi.toml` change fires every station suite and the `environment.yaml` rule (Story 47.1's
  precedent). The coordinator decides whether the comment moves with this story or later.
- **`scripts/detectors.py` is governed by no Spec surface.** The allowlist line says "§6 re-home decides its home".
  Doctor owns its task mapping under FR-15, and `spec-pyforge-doctor`'s surface already claims four `scripts/`
  files. Claiming `scripts/detectors.py` there is a `bmad-spec` re-derive, a surface baseline and an allowlist edit. It
  is left to the coordinator.

## Spec Change Log

- 2026-10-17: minted from `DW-doctor-103-3-1` (steward Story 103.3's independent review, out-of-surface defect b) on
  the coordinator's assignment. The evidence is the live registry and the inline reproduction at `ab38be642f` above.
- 2026-10-17, implemented on `chain-doctor-49-1-detector-task-match-2026-10-17` (base `ab38be642f`).
  - `scripts/detectors.py`: `_runs_detector(cmd, rel)` (the regex
    `(?<![^\s"'])(?:\./)?<rel>(?![^\s"';&|)])`, `rel` escaped) and `discover()` calls it in place of
    `path.name in c`; the module docstring says what "has no pixi task" now means. `run_one`, the `--json` skip and the
    Doctor-source half are unchanged.
  - `tests/scripts/test_detectors_task_match.py` (new): 30 tests, stdlib + `pytest`. AC2: the inline reproduction and a
    test-only task; AC3: the hidden gap; AC4: 10 command shapes that run the path and 12 that do not, and a literal
    `.`; AC5: the `--json` skip; a same-named file elsewhere through `discover()`; AC6: a fixture tree with its own
    `pixi.toml`; AC7: the live tree.
  - `tests/scripts/test_pyforge_ci_is_stdlib_only.py` (steward's): the inline-listing test is renamed
    `test_a_library_task_is_named_when_it_runs_a_detector_not_when_it_lists_its_test` and checks both halves;
    `detectors_run_by_a_library_task`'s docstring and message describe the path match. Its rule is unchanged.
  - Measured: the inline reproduction (`scripts-lib-test.txt`'s 36 files in a task placed first) maps 9 detectors on
    the base and 0 after; the live mapping of all 28 is identical before and after (`discover()` name and task, line
    by line).
  - AC10, six mutations on a scratch copy of the staged tree, each run against the new test file and steward's: the
    substring matcher restored, 6 failed (the inline, test-only, hidden-gap, same-named-file and fixture-tree tests, and
    steward's renamed test); the left boundary dropped, 6 (five non-matching shapes and the same-named-file test); the
    right boundary dropped, 3 (`.pyc`, `.py.bak`, `:main`); the row's bare-name option `(?<![\w])<name>`, 9; the
    `--json` skip dropped, 1; the `./` prefix dropped, 2 (the `./` shape and the fixture tree). The restored copy:
    63 passed, 3 skipped. The sixth mutation is added to AC10 here; the mint listed five.
  - Generated and chain files the mint touched that the Surface line does not name: `test-architecture.md` regenerated
    by `_bmad/scripts/bmad_tea_playwright.py --project pyforge-doctor` (`tea-playwright-check` reported "missing story
    id(s) in matrix: 49.1"); the PRD and the spine re-stamped 2026-10-17 with a *Currency reconciliation — 2026-10-17*
    section each, because the mint's memlog entries put the spec→prd edge three days past the PRD's 2026-10-14 stamp
    (`chain-currency-sweep-check` exit 1, then 0). No FR or AD moved.
  - Correction to `DW-doctor-103-3-1`'s summary, recorded in its `closed:` line: `detectors-ci` never runs a
    detector's task. The registry runs the script; the wrong task showed in `--list`, `--json` and
    `docs/reference/detectors.md`, and it hid the registry's gap finding.
  - `spec-surface-check` exits 0 with no drift: `scripts/detectors.py` and `tests/**` are allowlisted, and the planning
    files sit under `_bmad-output/**`, so no Spec is named and no stamp is taken.
