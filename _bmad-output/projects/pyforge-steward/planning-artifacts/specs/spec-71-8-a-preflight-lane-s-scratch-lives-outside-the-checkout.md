---
title: "71.8: A preflight lane's scratch lives outside the checkout"
type: 'fix'
created: '2026-10-08'
status: 'done'
baseline_revision: 'd5a23fb37a857f657bb4d5338697891ec385509d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-3-selected-lanes-run-concurrently-and-share-no-mutable-state.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-6-the-large-suites-run-under-pytest-xdist-locally-and-in-ci-alike.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-7-the-one-minute-budget-is-a-check-that-reads-the-journal.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py
  - .gitignore
  - scripts/pre_push_preflight.sh
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 71.3 gave every `pr-preflight` lane its own scratch, inside the checkout. Each lane's pytest
`tmp_path` therefore sits inside a git work tree, which four `tests/scripts/` tests cannot pass in. Nothing removes
the scratch, and git does not ignore it.

- **Where the scratch goes.** `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py`:
  `RUN_SCRATCH_RELATIVE = Path(".steward") / "preflight"` (`:35`); `run_preflight` makes
  `scratch_root = repo_root / RUN_SCRATCH_RELATIVE / run_id` after the install phase (`:447`-`:448`);
  `_run_lane_in_pool` (`:300`) sets `lane_dir = scratch_root / lane.task` and
  `log_path = scratch_root / f"{lane.task}.log"` (`:320`-`:321`); `_lane_scratch_env` (`:165`) exports `lane_dir` as
  `TMPDIR` (`:171`) and `lane_dir / ".coverage"` as `COVERAGE_FILE` (`:172`), and appends
  `--basetemp=<lane_dir>/pytest-basetemp -o cache_dir=<lane_dir>/pytest-cache` to `PYTEST_ADDOPTS` (`:174`-`:175`).
- **What fails.** Four tests need `git` run in `tmp_path` to fail; inside the checkout it finds the enclosing work
  tree and succeeds:
  - `tests/scripts/test_cfe_rebuild_guard_check.py::test_main_exit_2_git_log_fails` (`:1087`; `assert rc == 2` at
    `:1107` sees 1);
  - `tests/scripts/test_flag_inventory.py::test_a_git_checkout_whose_tracked_files_cannot_be_listed_exits_2`
    (`:876`; an empty `.git` dir is not a repository, so `git ls-files` walks up; `:884` sees 0);
  - `tests/scripts/test_fleet_picture_baseline_drift_attention.py::test_primary_checkout_staleness_silent_on_missing_repo`
    (`:548`; `:552` sees the enclosing branch's distance behind `origin/main`, 12 in the measured run). It fails only
    when that branch is behind, and `primary_checkout_staleness` (`scripts/fleet_picture.py:411`-`:444`) runs a
    live `git fetch origin refs/heads/main` in the pushing checkout on the way;
  - `tests/scripts/test_mason_cfe_surface_check.py::test_mason_commits_returns_none_when_git_log_cannot_run`
    (`:411`; `:413` sees `[]`).
- **Measured** on `21141248ca` (`preflight.py`, `.gitignore`, the hook and the four test files are unchanged at
  `09bdfcf17b`): `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` exits 0 (1246 passed, 20 skipped,
  91.5 s). The same task with `TMPDIR`, `PYTEST_ADDOPTS="--basetemp=… -o cache_dir=…"` and `COVERAGE_FILE` pointed
  under `.steward/preflight/repro/`, as the lane's environment points them, exits 1: those four fail, 1242 pass,
  20 skip, 177.6 s. A four-test run on a branch level with `origin/main` failed the other three and passed the
  fleet-picture test.
- **Who hits it.** The `pre-push` hook runs `pixi run --frozen -e pyforge-guild pr-preflight`
  (`scripts/pre_push_preflight.sh:131`), so every hand push since 71.3 landed that selects
  `pyforge-doctor-scripts-test` (every branch: Story 71.2) is refused on four correct tests. `dispatch/*` branches
  skip the hook (`:57`-`:62`); CI runs the task with the runner's own temp dir and stays green.
- **What is left behind.** No line in `preflight.py` removes the scratch, so every run, green or red, leaves
  `.steward/preflight/<run-id>/`. `.gitignore`'s steward block names `.steward/preflight-skips.log` and
  `.steward/preflight-runs.jsonl` (`:952`-`:953`), not `.steward/preflight/`. `*.log` (`:375`) and `*.coverage`
  (`:434`) hide the lane logs and coverage files; the `pytest-basetemp/` and `pytest-cache/` trees are untracked
  (`git status` listed them as `??` in the measured run), so a `git add -A` commits them.
- **What is printed today.** Each lane's log is printed whole when the lane ends (`_print_lane_log`, `:272`, called
  at `:333`); the red-lane lines (`:556`, `:563`) name the lane, its environment and exit code, not where its log
  is.

**Approach:**

- **One scratch root per run, outside the checkout.** After the install phase, where `:447` makes it today,
  `run_preflight` creates the run's root with `tempfile.mkdtemp(prefix="pyforge-preflight-")` in the system temp
  dir. `tempfile.gettempdir()` honours the invoking process's `TMPDIR`; Story 71.3 added no other override, and this
  story adds none. A keyword-only `scratch_parent: Path | None = None` on `run_preflight` (the `dir=` given to
  `mkdtemp`) lets tests place the root; `main()` never passes it. The journal record does not change shape.
- **Refuse a root inside the checkout.** If the resolved root `is_relative_to(repo_root)` (an invoking `TMPDIR` that
  points into the checkout), the runner removes it and exits 2 before any lane runs, naming the path; it never runs
  lanes with scratch inside the work tree.
- **Per lane, the same shape.** Under the root: `<lane>/` as `TMPDIR`, `<lane>/pytest-basetemp` and
  `<lane>/pytest-cache` in `PYTEST_ADDOPTS`, `<lane>/.coverage` as `COVERAGE_FILE`, `<lane>.log` as the lane log.
  Each lane still gets its own of each (71.3's no-shared-mutable-state property). Whatever else the lane environment
  carries by then (Story 71.6's per-lane `PYTEST_XDIST_AUTO_NUM_WORKERS`) is kept.
- **The journal stays.** `JOURNAL_RELATIVE` (`:34`, `.steward/preflight-runs.jsonl`) and every write to it are
  unchanged; Story 71.7's `--budget` reads it there.
- **Green removes, red keeps.** A run that exits 0 removes its root (`shutil.rmtree`); a failed removal prints a
  warning naming the path and never changes the exit code. A run that exits 1 (a red lane, with or without
  `--keep-going`) or 130 (interrupted) keeps its root and prints `preflight: lane logs and scratch kept at <root>`
  to stderr; each red-lane line names that lane's log, `<root>/<lane>.log`. A run that ends before the root exists
  (exit 2, an install failure) creates none.
- **A guard for older runs.** `.gitignore`'s steward block gains `.steward/preflight/`, so trees that runs before
  this story left are never committed. The runner does not delete them: it removes only the root it created.
- **`RUN_SCRATCH_RELATIVE` goes.** No code writes under `.steward/preflight/` any more; the constant and its one use
  are removed, and the test that imports it is updated (below).

Ledger key: `71-8-a-preflight-lane-s-scratch-lives-outside-the-checkout`.
Type / Effort / Deps: fix / S / S-71.7.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (FR-32): "each lane gets its own temp dir, pytest basetemp
  and cache dir, and coverage data file", built by Story 71.3. CAP-159 names no location; this fix moves it and
  keeps the property. It mints no CAP and changes no `SPEC.md` text.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.
- **Deps.** S-71.7. Stories 71.5, 71.6 and 71.7 are `backlog` and queued; none moves the scratch. 71.5 (in flight on
  `dispatch/pyforge-steward/71.5` at `01484e98ac`) touches `scripts/detectors.py`, `pixi.toml` and `tests/scripts/`,
  not `preflight.py` or `.gitignore`. 71.6 adds per-lane `PYTEST_XDIST_AUTO_NUM_WORKERS` to the lane environment in
  `preflight.py`; 71.7 adds `--budget`, which reads the journal this story leaves in place. 71.6 and 71.7 edit the
  module this story edits, so it lands after them.
- **Origin.** Found 2026-10-08 on a hand push refused by the `pre-push` hook; re-measured on `21141248ca` (above).

## Acceptance Criteria

- Given a fixture repo under `tmp_path` and two lanes, and a `run_lane_ctx` that records each `ctx.env` and
  `ctx.log_path` When `run_preflight` runs Then for each lane `TMPDIR`, the `--basetemp=` and `cache_dir=` values
  parsed from `PYTEST_ADDOPTS`, `COVERAGE_FILE` and `log_path` each satisfy
  `not Path(p).resolve().is_relative_to(repo.resolve())`, and every one of them differs between the two lanes.
- Given a fixture git repo (`git init`) under `tmp_path` and one lane whose `run_lane_ctx` runs
  `[sys.executable, "-m", "pytest", <fixture test file>, "-q", "-p", "no:cacheprovider"]` with `env=ctx.env`, whose
  one test asserts `subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "--is-inside-work-tree"]).returncode
  != 0` When `run_preflight` runs with the default scratch parent Then the lane exits 0 and the run exits 0. With
  the root put back at `repo_root / ".steward" / "preflight" / run_id` the same test fails (mutation).
- Given a run whose lanes all exit 0 When `run_preflight` returns 0 Then the run's root no longer exists and
  `repo / ".steward" / "preflight"` does not exist. Given a run with one red lane When it returns 1 Then the root
  still exists and holds `<lane>.log`, and stderr names the root and the red lane's log path; the same holds under
  `--keep-going`. Given a SIGINT mid-run When it returns 130 Then the root is kept and named.
- Given an invoking `TMPDIR` (or `scratch_parent`) inside the fixture repo When `run_preflight` runs Then it exits 2
  naming the path, no lane runs, and nothing is left under the repo.
- Given a removal that raises (a patched `shutil.rmtree`) on a green run When the run ends Then it exits 0 and
  stderr names the path it could not remove.
- Given the repository `.gitignore` When `git check-ignore -q .steward/preflight/x/lane/pytest-basetemp/t0/f.txt`
  runs Then it exits 0.
- Given the change When the 71.1-71.4 preflight suites (`test_preflight.py`, `test_preflight_selection.py`,
  `test_preflight_concurrency.py`, `test_preflight_suite_reduction.py`) run Then they pass. The one location
  assertion that names the old place, `test_each_lane_gets_isolated_scratch_env`
  (`test_preflight_concurrency.py:85`; `:111`-`:114` read `repo / preflight.RUN_SCRATCH_RELATIVE`), keeps its
  distinctness checks (`:109`-`:110`) and instead asserts both lanes' `TMPDIR` share one root outside `repo`; no
  other existing assertion changes.

## Boundaries & Constraints

**Always:**
- Change only `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py`, its tests under
  `src/shared/packages/pyforge-steward/tests/unit/`, and `.gitignore`.
- Keep the scratch per lane and per run: no two lanes, and no two runs, share a directory.
- Keep the journal at `.steward/preflight-runs.jsonl`, written as today.
- Stdlib only (`tempfile`, `shutil`).
- Tests that run `run_preflight` with a red lane pass `scratch_parent=tmp_path / "scratch"` (outside the fixture
  repo) so a kept root never collects in the system temp dir.

**Never:**
- Never change which lanes run (Story 71.2), what a lane runs (71.4-71.6), or a lane's verdict.
- Never change, skip, deselect or `xfail` the four `tests/scripts/` tests: they are right to need a temp dir outside
  any work tree.
- Never point `TMPDIR`, `--basetemp`, `cache_dir`, `COVERAGE_FILE` or a lane log inside `repo_root`.
- Never remove a red or interrupted run's scratch, or anything this run did not create (older
  `.steward/preflight/` trees stay until the operator removes them).
- Never let a scratch-removal failure change the exit code.
- Never change `scripts/pre_push_preflight.sh`, `pixi.toml` or `.github/workflows/`.
- Never hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

**At landing:** `preflight.py` is in the surfaces of `spec-pyforge-steward` and `spec-pyforge-core`, and
`.gitignore` in 14 Specs' surfaces at `09bdfcf17b`; append the reconcile to the memlog of every Spec
`spec-surface-check` names, then one scoped stamp each (AGENTS.md § Pre-PR item 5).

## I/O & Edge-Case Matrix

| Run | Scratch root | Exit |
|---|---|---|
| every lane exits 0 | removed | 0 |
| one red lane | kept; stderr names the root and the lane's log | 1 |
| `--keep-going`, two reds | kept; both logs named | 1 |
| SIGINT | kept; root named | 130 |
| an environment fails to install | never created | 1 |
| no `pixi.toml`, missing aggregate | never created | 2 |
| invoking `TMPDIR` inside the checkout | removed at once, path named, no lane run | 2 |
| removal fails on a green run | warning names the path | 0 |
| older `.steward/preflight/<id>/` trees present | untouched; ignored by git | unchanged |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-08 (preflight scratch) entry.
- Epic: Epic 71 (CAP-159, FR-32; `in-progress`, 71.5-71.7 `backlog`).
- Ledger key: `71-8-a-preflight-lane-s-scratch-lives-outside-the-checkout`.
- Ledger status at mint: `backlog`.
- Deps: S-71.7 (and through it 71.5 and 71.6).
- Spec: `spec-pyforge-steward/.memlog.md` records the mint; `SPEC.md` untouched.
- Surface: `preflight.py`, its unit tests, `.gitignore`. Epic 71 declares no `[epic_surfaces]` entry in
  steward's `marshal-policy.toml`, so marshal's derived default applies (`src/shared/packages/pyforge-steward/**`,
  steward's specs and implementation artifacts, `.gitignore`, `pixi.toml`, `pixi.lock`, `environment.yaml`,
  `scripts/.spec-surface-baseline.json`; `pyforge-marshal` `core/gate.py`, `default_epic_surface`); every path here
  is inside it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- On a branch behind `origin/main`, `pixi run -e pyforge-guild pr-preflight` — expected: the
  `pyforge-doctor-scripts-test` lane passes, the four tests above among its passes; the run exits 0; afterwards
  `git status --porcelain --untracked-files=all` lists nothing under `.steward/preflight/` and the stderr root no
  longer exists.
- The lane's environment by hand, outside the checkout: `R=$(mktemp -d) && TMPDIR=$R
  PYTEST_ADDOPTS="--basetemp=$R/pytest-basetemp -o cache_dir=$R/pytest-cache" COVERAGE_FILE=$R/.coverage pixi run
  --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass, as without the variables; then `rm -rf "$R"`.
- A red run: make one lane fail (e.g. a fixture `pixi.toml`, or `--keep-going` on a branch with a known red) —
  expected: exit 1, stderr names the kept root and each red lane's log, and those paths exist outside the checkout.
- `git check-ignore -v .steward/preflight/x/lane/pytest-basetemp/t0/f.txt` — expected: exit 0, naming the new line.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- No change yet.

## Review Triage Log

### 2026-10-09 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — implementation matches intent-contract and matrix tests cover all rows)

## Auto Run Result

Status: done

**Summary:** `run_preflight` now creates each run's scratch with `tempfile.mkdtemp` outside the checkout (optional `scratch_parent` for tests). Green runs remove the tree; red or interrupted runs keep it and print log paths on stderr. Scratch inside the repo is refused with exit 2. Legacy `.steward/preflight/` is gitignored.

**Files changed:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py` — external scratch, cleanup, guard, stderr naming
- `src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py` — Story 71.8 acceptance and matrix tests
- `src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py` — outside-repo scratch assertions; `scratch_parent` on red-lane tests
- `.gitignore` — `.steward/preflight/` guard for pre-71.8 trees

**Review:** No patch/defer/intent_gap items.

**Verification:** `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2232 passed, 5 skipped. `python scripts/spec_surface_reconcile.py` — OK.

**Surface reconcile (memlog paths named):**
- `spec-pyforge-steward/.memlog.md`: `preflight.py`, `test_preflight_concurrency.py`, `test_preflight_scratch.py`, `.gitignore`
- `spec-pyforge-core/.memlog.md` (co-governor): `preflight.py`

**Residual risk:** SIGINT test is timing-sensitive; full suite passed once in this run.
