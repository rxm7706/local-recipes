---
title: "116.4: A package-half test that opens a repository file outside the package fails, wherever the package half runs"
type: 'feature'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; nothing a user reaches at runtime (roster flag_exemptions; the exempt form of spec-110-38)
difficulty: medium
story: '116.4'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-marshal/tests/conftest.py
  - src/shared/packages/pyforge-marshal/tests/_support/tree_read_guard.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_tree_read_guard.py
  - src/shared/packages/pyforge-marshal/tests/**/*.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-marshal/tests/conftest.py
  - .github/workflows/pyforge-station-tests.yml
  - pixi.toml
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The oracle goal needs a check that runs. Steward's derivation is static and misses runtime reads: code under test that falls back to the checkout reads the repository and no static scan sees it.

**Approach:** Realizes spec-pyforge-marshal:CAP-305's guard clause. `tests/_support/tree_read_guard.py` installs one `sys.addaudithook` per process (xdist workers each load `tests/conftest.py`); the hook returns at once unless armed and the event is `open`, `os.listdir`, `os.scandir` or `glob.glob`. `tests/conftest.py` arms it in hookwrappers around each package-half test's setup, call and teardown (so module fixtures count) and fails the test naming each recorded path. The package directory is the guard file's `parents[2]`; the repository is the nearest ancestor of it holding `.git` (a file in a worktree), or none. Allowed under the repository: the package, `.pixi/`, `.steward/coverage/`, the directories of the installed `pyforge.core` and `pyforge.testing_kit` modules. A subprocess's reads (a test that runs `git -C <repo>`) are not seen: steward's static derivation stays the guard for those. A module the guard names is marked or fixed exactly as Stories 116.2 and 116.3 do. The off-tree copy run is one-time evidence recorded here, not a lane: an unsharded package-half run would exceed the 15-minute marshal-gate job, and running the shards from a copy would turn coverage.py's file keys absolute.

Ledger key: `116-4-a-package-half-test-that-opens-a-repository-file-outside-the-package-fails-wherever-the-package-half-runs`. Type / Effort / Deps: feature / M / S-116.3.

## Boundaries & Constraints

**Always:**
- A `live_tree` test is never armed; with no repository around the package the guard is inert.
- The guard runs inside the lanes that already run the package half (CI `marshal-test` shards, the pr-preflight marshal lane), at no extra suite run.

**Never:**
- No new lane and no new pixi task.
- Never skip or re-mark a test to quiet the guard.

## Acceptance Criteria

- **AC1 — The classifier and the hook: a read of `<repo>/scripts/x.py`, `<repo>/_bmad-output/...` or `<repo>/src/shared/packages/pyforge-doctor/...` is recorded; a read under the package, a tmp dir, `<repo>/.pixi/`, the installed pyforge-core or pyforge-testing-kit source, or outside the repository is not; a live_tree test is never armed; with no repository around the package the guard is inert.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_tree_read_guard.py -q
  ```

  Expected: exit 0.

- **AC2 — The guard runs in the package half and the half passes with it.**

  ```bash
  pixi run --frozen -e pyforge-marshal pyforge-marshal-test
  ```

  Expected: exit 0, and the run's header line names the guard (`tree-read guard: armed`).

- **AC3 — The lanes that run it: CI job `marshal-test` and the pr-preflight marshal lane both run `pyforge-marshal-test`.**

  ```bash
  grep -c 'pixi run --frozen -e pyforge-marshal pyforge-marshal-test' .github/workflows/pyforge-station-tests.yml && grep -c 'task = "pyforge-marshal-test"' pixi.toml
  ```

  Expected: each prints 1 or more.

- **AC4 — One-time evidence, recorded in this spec: the package half run from a copy of the package outside the repository passes.**

  ```bash
  R=$PWD; D=$(mktemp -d) && cp -r src/shared/packages/pyforge-marshal/tests src/shared/packages/pyforge-marshal/pyproject.toml $D/ && (cd $D && pixi run --manifest-path $R/pixi.toml --frozen -e pyforge-marshal python -m pytest tests/unit tests/meta -q -p no:cacheprovider -m 'not slow and not live_tree')
  ```

  Expected: exit 0.

- **AC5 — Lint and types hold.**

  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal:CAP-305` (memlog 2026-11-10; rendered by Story 114.1). FR-247 (written by Story 114.1).

- Epic: Epic 116 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 116.4: A package-half test that opens a repository file outside the package fails, wherever the package half runs`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Shares the glob over marshal's tests with Stories 116.2 and 116.3, hence the dependency on Story 116.3.

## Guard record (written at build)

Built 2026-11-11 on `cutover-readiness-2026-11-10` (base `7db7f6ed11`). All paths are under
`src/shared/packages/pyforge-marshal/tests/`.

**The guard.** `_support/tree_read_guard.py` holds `TreeReadGuard` and the audit hook. `conftest.py` (new) loads it
by path, installs it once per process, and arms it around the setup, call and teardown of each package-half test, a
test marked neither `live_tree` nor `slow`. A phase that read a repository path outside the package fails, naming
each path and its event. The run's first line names the guard, also under `-q`: `tree-read guard: armed (package
src/shared/packages/pyforge-marshal)`, or `tree-read guard: inert (no repository around <dir>)`. The first armed run
added two classifier rules:

- The import system's own directory listings are not reads. Its path finder lists the repository root, which xdist
  puts on `sys.path`, and `importlib.metadata` lists the working directory. The import system's `open` still counts,
  so importing a repository script is caught.
- An `os.open` of a relative name is not judged. Its event carries no `dir_fd`, and `shutil.rmtree` of a tmp git
  repository opens each entry by such a name (`objects`, `refs`, `pack`): 213 false records in 9 modules.

Two kinds of read stay unseen: a subprocess's reads, and an existence check (`os.stat`, `Path.is_file`), which raises
no audit event.

**What the first armed run found.** Before any test changed, the guard failed 1611 tests and errored 35 in `unit/`
and `integration/`, and failed 12 in `meta/`, run with the task's `PYTHONPATH`. Almost all came from two fallbacks
in the code under test:

- `pyforge.core`'s flag tree, found by walking up from the working directory. 1293 tests in 46 modules read
  `src/platform/config/flags.json` and `flag-overlays.json`: every CLI verb behind a kill switch reads them.
- `cli/config.py`'s `repo_root()` and `checkout_root()`, anchored on that module's `__file__` in the editable
  layout. They led to `_bmad-output/policy-defaults.toml` (424 tests, 15 modules), the stations' tracked
  `marshal-policy.toml` (322 tests, 13 modules), `scripts/promote_sprint_status.py` and `scripts/fleet_scan.py`
  (43 and 26 tests), and `_bmad-output/projects` and `docs/governance/guild-roster.json` (26 tests).

Marking all 1658 would have left the package half at about 85% of the suite, below the 90% floor of
spec-pyforge-marshal:CAP-305.

**The fix: an armed test starts off the tree.** `conftest.py`'s autouse fixture `_package_half_off_the_tree` gives
each armed test a working directory outside the repository. It also makes `cli/config.py`'s
`_editable_checkout_root()`, the one reader of that module's `__file__`, answer a bare checkout under the session's
tmp dir, which holds only the package's source path. `config.__file__` itself is never rebound (review round 1,
below). The flag walk then finds no tree, and `kill_switch_on` reads ON, as for a package run outside the
estate. `repo_root()` and `checkout_root()` name a checkout with no planning tree and no scripts, like a checkout that
is not this one. A test that sets its own directory or root still does. No test is skipped or re-marked by this: a
test whose outcome needs the tree still fails. After it, the guard recorded no read, and 32 tests in 8 modules failed
on the tree they lost.

**What moved.** Exactly as Stories 116.2 and 116.3 do: a module of 20 tests or fewer is marked whole, a larger one
is split. Shared helpers stay, and the sibling imports them by name. A fixture or autouse fixture the moved tests
take is declared in the sibling too. Each sibling carries `pytestmark = pytest.mark.live_tree`, and each moved test
fails, never skips, when what it reads is absent. These are the 36 tests Story 116.2's record handed to this story,
plus one more.

- `unit/test_land.py`: 10 tests moved to the new `unit/test_land_live_tree.py`. Each promotes or rolls the ledger
  through `scripts/promote_sprint_status.py`, which `cli/land.py` loads from `checkout_root()`.
- `unit/test_deploy.py`: 4 `reconcile-completions` tests moved to the new `unit/test_deploy_live_tree.py`. Without
  the script they journal MRS-DEPLOY-028.
- `unit/test_dispatch_land_finalize.py`: 2 tests moved to the new `unit/test_dispatch_land_finalize_live_tree.py`.
  They need the same script.
- `unit/test_harness_policy_render.py`: 2 tests moved to the new `unit/test_harness_policy_render_live_tree.py`.
  They check `repo_root()`'s `pixi.toml` and the convention layer's project policy.
- `unit/test_spin.py`: `test_spin_states_the_wire_layer_disposition_on_every_run` moved to the existing
  `unit/test_spin_live_tree.py`. It needs the repository default `[context.wire]`.
- `unit/test_status.py`: `TestRunDetail::test_run_status_with_default_ports_and_run_flag_does_not_crash` moved to
  the new `unit/test_status_live_tree.py`. Its default `GitVcs` reads the repository of the working directory. It
  is the test Story 116.2's list did not have: that copy ran from inside a git repository.
- `unit/test_land_epic_rollups.py` (9 tests, all of them through the script) and `unit/test_tier_routing.py` (20;
  one composes every station's tracked policy) are marked whole.
- `meta/test_tool_surface_coverage.py` (11) is marked whole. Five tests probe the root that `mcp/coverage.py`
  resolves from its own location. A probe raises no audit event, so the guard cannot name them, but Story 116.2's
  whole-package copy fails them, and so does the one below.

**Source found beside the tests.** AC4's copy holds only `tests/` and `pyproject.toml`. Its first run failed 95
tests in 16 modules. Each one read the package's own `src/` (the JSON schemas, `scope.py`, the harness profiles,
the recall plugin) or `pixi.toml` through a path beside the tests. Each module now finds them through the import
system (`from pyforge import marshal as marshal_package`; `Path(marshal_package.__file__).resolve().parent`, and
`.parents[3]` for the package root in `meta/test_manifest_sync.py`). The modules:
`meta/test_manifest_sync.py`, `meta/test_seed_manifest_scope_invariants.py`, `unit/test_cli.py`,
`unit/test_conformance_schema.py`, `unit/test_egress.py`, `unit/test_gate_record.py`, `unit/test_harness_profile.py`,
`unit/test_init.py`, `unit/test_journal.py`, `unit/test_landing_ci_pauses.py`, `unit/test_loop_runner_hook.py`,
`unit/test_marshal_recall_plugin.py`, `unit/test_spin.py`, `unit/test_status.py`, `unit/test_supervisor.py`,
`unit/test_verify_scope.py`, and `unit/test_mcp_story_103.py`. That last one's fastmcp scan passed off the tree only
because it scanned nothing.

**Evidence, recorded once (2026-11-11).**

- AC4, the command as written, run from `/tmp/tmp.tRjzHTpmVG`: the first line is `tree-read guard: inert (no
  repository around /tmp/tmp.tRjzHTpmVG)`. 13730 passed, 14 skipped, 498 deselected, exit 0. The 14 skips are flag
  parametrization and platform skips; the in-tree run skips the same 14.
- The whole package, `src/` included, was copied into an empty git repository at its own path. The package half
  ran there with `PYTHONPATH` on the copy's `src`, which is the copy Story 116.2's review used. The first line is
  `tree-read guard: armed (package src/shared/packages/pyforge-marshal)`: the guard is armed around the copy.
  13730 passed, 14 skipped, none failed. Before `meta/test_tool_surface_coverage.py` was marked, the same run failed
  its five tests and nothing else.
- AC2: the guard's armed line heads both segments of `pyforge-marshal-test`. 14227 passed and 14 skipped, then 34
  passed and 4 skipped; exit 0.
- Steward's derivation over the unmarked modules, with the untracked files added to its list: `reads == {}` and
  `handoffs == []`. The live half's derived hand-offs are the 17 files Story 116.3 recorded. No new sibling hands a
  root to code: the root reaches the code under test through `repo_root()` and `checkout_root()`.
- Story 116.2's partition: 13785 in the package half, 493 in the live half, 14278 in all; the package half keeps
  96.5%. Test functions: 8297 on this branch, 8188 on `origin/main`.
- AC5 exits 0 run as `pixi run --frozen -e pyforge-guild lint-types`. The command as first written, without
  `--frozen`, re-locked `pixi.lock` on this branch: other stories' package edits re-hash their source packages. Only
  steward Story 124.3 re-locks, so the lock was put back to `HEAD`'s bytes and the check re-run frozen. Review
  round 1 corrected AC5 to the `--frozen` form.

**Round 1 addendum (2026-11-11): coverage attributes `cli/config.py` to its real path.** The first build's off-tree
start rebound `config.__file__`, and coverage.py, which names a traced file by its frame's `__file__`, filed most of
`cli/config.py`'s lines under the bare checkout's missing `config.py`: 15.3% in the report, and
`pyforge-marshal-coverage-gate` exited 1. Now:

- `tests/conftest.py`'s `_package_half_off_the_tree` replaces `config._editable_checkout_root` with one that answers
  the bare checkout, and never touches `config.__file__`. A new fixture, `off_tree_checkout_anchor` (default
  `True`), lets a module that moves the anchor itself turn that replacement off; the working directory still moves
  off the tree and the guard stays armed.
- `unit/test_repo_root.py` and `unit/test_checkout_root.py` override it with `False`. They move the anchor through
  the new `unit/_config_anchor_support.py`'s `anchor_config_at`, which swaps the module's `Path` for a subclass that
  reads the real `__file__` as the made-up file, so the real `_editable_checkout_root()` runs against each layout.
  Their two mutation witnesses index `installed.resolve().parents[8]` instead of `config_module.__file__`'s.
- `meta/test_tree_read_guard.py::test_an_armed_test_starts_off_the_tree` now also asserts
  `config.__file__ == config.__spec__.origin`, so a rebound `__file__` reds in this module.

Re-run under the lock, each read from its exit code:

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` (which runs `pyforge-marshal-test` first):
  exit 0, `coverage gate OK for pyforge-marshal unit: 11 module(s) ≥ 80%`. In
  `.steward/coverage/marshal-unit.json`, `cli/config.py` is 94.0% (`HEAD` 92.3%, the first build 15.3%), every key
  is a `src/` path, and the run printed no `No source for code`.
- AC1: 17 passed, exit 0. AC2 alone: both segments headed `tree-read guard: armed (package
  src/shared/packages/pyforge-marshal)`, 14227 passed and 14 skipped, then 34 passed and 4 skipped; exit 0. AC3
  prints 1 and 2. AC4, the command as written, from `/tmp/tmp.dHxp1IZflA`: `tree-read guard: inert`, 13730 passed,
  14 skipped, 498 deselected, exit 0. AC5 (`--frozen`): exit 0, `pixi.lock` byte-identical to `HEAD`.
- Steward's derivation over the 260 unmarked modules, the new helper among them: `reads == {}`,
  `handoffs == []`. The live half's hand-offs are still the 17 files Story 116.3 recorded.
- The whole-package copy into an empty git repository was not re-run in round 1.

**For steward S-124.1 and S-124.2.** The package-half task needs nothing from this story: `tests/conftest.py` arms
the guard wherever the half runs. The live half gains `unit/test_land_live_tree.py`, `unit/test_deploy_live_tree.py`,
`unit/test_dispatch_land_finalize_live_tree.py`, `unit/test_harness_policy_render_live_tree.py`,
`unit/test_status_live_tree.py`, and the three modules marked whole. `ROOT_HANDOFF_INPUTS` is unchanged by this
story.

**Outside this story's files.** None is edited here.

- `meta/test_spec_names_live_paths.py` still carries the two `ALLOW` entries for `tests/_support/tree_read_guard.py`
  and `tests/meta/test_tree_read_guard.py`, written "open while CAP-305 reads ready". Both paths resolve once the
  wave commits. The closer (Story 116.5) removes the entries with CAP-305's marker.
- `spec-pyforge-marshal/SPEC.md` lists `tests/unit/test_tier_routing.py` in its surface (lines 101 and 198), and
  this story edits it along with the other modules above. The closer's surface reconcile names them.
- Name-only, still true: `cli/config.py`'s `repo_root()` docstring and `specs/spec-82-1-*.md` name
  `test_conventional_project_policy_path_lands_on_the_repo_root`. `specs/spec-46-4-*.md` names
  `test_spin_states_the_wire_layer_disposition_on_every_run`. `specs/spec-92-1-*.md` names
  `test_run_status_with_default_ports_and_run_flag_does_not_crash`. The marshal `deferred-work-ledger.md` names
  the first. Each now sits in a live sibling.

## Review findings (build, round 1, 2026-11-11)

An independent review failed the first build. Its findings, as received:

1. **Blocker.** `tests/conftest.py`, `_package_half_off_the_tree`:
   `monkeypatch.setattr(config, "__file__", str(bare_module))`. coverage.py names a traced file by the frame's
   `__file__` before its `co_filename`, so in each xdist worker the lines of `cli/config.py` were filed under the
   bare checkout's `config.py`, which does not exist, and dropped from the report. `cli/config.py` fell from 92.3%
   (`HEAD`) to 15.3%, and `pyforge-marshal-coverage-gate` exited 1 on it: this branch touches `cli/config.py`
   (Story 115.1), so the touched-module floor of 80% judges it. CI's `marshal-gate` job and a full `pr-preflight`
   judge the same reports. `unit/test_repo_root.py` and `unit/test_checkout_root.py` rebind the same `__file__`
   themselves, the same misattribution on a smaller scale.
2. **Minor.** The Approach does not name the suite-wide autouse fixture that starts every armed test off the tree.
   It changes the run of about 13.7k tests and so quiets the guard's fallback reads; it is not a per-module fix.
   The Guard record discloses and justifies it, but the contract does not say it.
3. **Minor.** AC5 as written, `pixi run -e pyforge-guild lint-types` without `--frozen`, re-locks `pixi.lock` on
   this branch. The `--frozen` form checks the same thing.

**Resolution.**

1. Fixed. The fixture no longer rebinds `__file__`. It replaces `cli/config.py`'s `_editable_checkout_root`, the
   one reader of `__file__` behind `repo_root()` and `checkout_root()`, with one that answers the bare checkout.
   The two modules that drive that anchor themselves opt out by overriding the conftest's
   `off_tree_checkout_anchor` fixture with `False`. They now move the anchor through
   `unit/_config_anchor_support.py`'s `anchor_config_at`, which swaps the module's `Path` for a subclass that reads
   the real `__file__` as the made-up file. `config.__file__` is never rebound anywhere in the suite. The two
   mutation witnesses in `unit/test_repo_root.py` now index the installed layout's own file, not
   `config_module.__file__`. Results are in the Guard record's round-1 addendum below.
2. Not fixed here: a contract change. The closer, Story 116.5, records the off-tree start as part of
   spec-pyforge-marshal:CAP-305's guard mechanism, through a memlog entry and the approved render (see
   `## Planned deferral (written at build)`).
3. Fixed under the ORACLE RULE. AC5 now reads `pixi run --frozen -e pyforge-guild lint-types`, here and in
   `plan.json`. The criterion checks the same thing; `--frozen` only stops the run from re-locking.

## Planned deferral (written at build)

- **The off-tree start in spec-pyforge-marshal:CAP-305's contract.** The guard as built has two parts: the audit
  hook, and `tests/conftest.py`'s `_package_half_off_the_tree`, which starts every armed test in a working directory
  outside the repository with `cli/config.py`'s checkout anchor on a bare checkout. CAP-305's guard clause and this
  story's Approach name only the first. Recording the second is a contract change, outside this story's files: the
  closer, Story 116.5, appends it to `spec-pyforge-marshal`'s memlog and carries it through the approved render,
  and writes the ledger row if it cannot. Raised by review round 1, finding 2.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
