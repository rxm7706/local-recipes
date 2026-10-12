---
title: "95.1: Dispatch applies ruff to a story's files under each tree's own config"
type: 'fix'
created: '2026-10-11'
status: 'done'
baseline_revision: 'c8f274ef27fec91e296fc7f8d47a30d999c7ea92'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-9-dispatch-applies-ruff-format-to-a-story-s-files-before-it-verifies.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-15-dispatch-applies-ruff-s-safe-fixes-before-it-verifies.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_ruff_format.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_cfe_commit.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_ruff_format.py
  - src/platform/pyproject.toml
  - scripts/lint_types.py
  - scripts/platform-ci-local.sh
  - pixi.toml
  - scripts/.spec-surface-baseline.json
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** dispatch's pre-verify pass (Stories 83.9 and 83.15) runs ruff's safe fixes and `ruff format` only on a
story's changed `.py` files under `src/shared/packages/pyforge-*`. A story's files under `src/platform`, and under
the nine `src/shared/packages/django-*` portal packages, get no pass, so verify refuses them on fixes ruff could have
made. Line numbers below are at `3c85a29a64`.

**How the pass works today.**
- **Where it runs.** The supervisor calls it before every verification (`_run_and_journal_ruff_format`,
  `dispatch_supervisor/__main__.py:2335`, from :2469) and before a fix turn's reconcile (:1608). The land-only CAP-4
  path calls it too (`cli/dispatch.py:1195`), without a journal. All three reach
  `apply_dispatch_ruff_format_before_verify` (`core/dispatch_ruff_format.py:63`) through
  `dispatch_verify.run_dispatch_ruff_format_before_verify` (:1048).
- **Which files.** It reads the story's change set, `vcs.changed_files(..., base=origin/main)`: the committed diff plus
  the worktree's dirty and untracked paths. `story_scoped_pyforge_py_paths` (:32) keeps a path only when it ends in
  `.py` and its first four parts are `src/shared/packages/pyforge-<x>`. `src/platform/foo.py` is dropped, and its test
  pins that. Deleted paths are not filtered out.
- **Which config.** It groups the kept paths by package name (`_group_by_package`, :49). For each package whose
  `pyproject.toml` is a file (it never checks for a `[tool.ruff]` table), it runs `ruff check --fix <paths>` and then
  `ruff format <paths>`, with `cwd` the package directory and paths relative to it. It passes no `--config` and no
  `--force-exclude`. That is the `cwd` that `scripts/lint_types.py` gives the gate, so ruff reads the package's own
  table.
- **Failures.** A `ProcessError` from the check step skips that package's format step. A non-zero exit from either
  step is ignored (`ruff check --fix` exits 1 whenever a finding it cannot fix remains). No failure stops the next
  package, and no failure is recorded anywhere.
- **The commit.** It then commits the story-set paths that are dirty against `HEAD`, in one `commit_paths` call with
  the subject `marshal: ruff check --fix and format story files (Story 83.9, 83.15)`. It returns
  `DispatchRuffFormatResult(reformatted_paths, committed)`.
- **The journal.** The supervisor journals a `dispatch-ruff-format` INTENT/OUTCOME pair
  (`KIND_DISPATCH_RUFF_FORMAT`, `core/dispatch.py:57`) only when `reformatted_paths` is non-empty. The payload holds
  `story_key`, `paths`, `committed` and `ok` (the same value as `committed`). It names no package, and a pass with
  nothing changed journals nothing.

**The evidence.**
- **Steward 91.1** (run `pyforge-steward-20261011T235216324Z-30fdeec5`, journal under the primary checkout's
  `_bmad-output/projects/pyforge-steward/implementation-artifacts/dispatch-runs/`). Verify refused at 00:29:48Z (UTC,
  2026-10-12) under `MRS-GATE-015`: `pixi run -e pyforge-guild platform-ci-local -- --test` exited 1. Its ruff step
  reported "Found 1 error. [*] 1 fixable with the `--fix` option": an I001 import block in
  `src/platform/tests/test_stations_index.py`. The verify-fix turn launched at 00:29:49Z and was killed at 00:44:49Z
  (`MRS-DISP-059`, 900.19 s), and the run ended `failed`. Replayed on 2026-10-11 with ruff 0.16.9 on that file at the
  run's head `1c88d2a5cc`: `ruff check --fix` and `ruff format` from `src/platform` leave "All checks passed!".
- **Herald 37.1** (run `pyforge-herald-20261011T190323017Z-deb8f4a9`). The pass journaled at 19:10:46Z for one file,
  `src/shared/packages/pyforge-herald/tests/meta/test_portal_herald_guard.py`, and none for the story's platform
  test. Verify refused under `MRS-GATE-015` from 19:13:45Z. The 19:48:00Z and 21:46:00Z tails show "Found 3 errors",
  E501 at `tests/test_herald_portal_without_herald.py:66:89` and RET504 at `:108:12`, and "No fixes available (1
  hidden fix can be enabled with the `--unsafe-fixes` option)". The session's commit `e62682df15` cleared E501, RET504
  and PLC0415 by hand. Replayed on the file at `e62682df15^`, the safe fixes and format under the platform table clear
  none of the three. This story would not have saved that run, and it must not pretend to.
- **The portal packages.** None of the nine `django-*/pyproject.toml` files declares a `[tool.ruff]` table at
  `3c85a29a64`. Steward Story 93.1 (dispatched now) gives each package its own table at target `py312` and puts the
  packages under `lint-types`, which dispatch runs on every story (Story 79.2). Steward Story 95.1 (chained on `main`,
  `backlog`) moves those targets, and `src/platform`'s, to `py314`.
- **Why each tree's own config matters.** Measured with ruff 0.16.9:
  - The platform table sets `force-single-line = true` for isort, so an import block the `pyforge-*` table accepts is
    I001 under the platform table.
  - A `py314` table makes `ruff format` rewrite `except (ValueError, TypeError):` as `except ValueError, TypeError:`
    (PEP 758), a SyntaxError on Python 3.12 and 3.13. A `py312` table keeps the parentheses.
  - With paths named on the command line, ruff ignores the table's `extend-exclude`. Run from `src/platform`,
    `ruff check --fix` and `ruff format` both rewrote `app/migrations/0001_initial.py`, although the platform table
    excludes `*/migrations/*.py`. With `--force-exclude` they left it byte for byte. The gates walk the tree
    (`ruff check .` in `platform-ci-local.sh`; `ruff check src tests` in `lint_types.py`), so they never read an
    excluded file. All ten `pyforge-*` tables declare the same `extend-exclude`, so today's pass already rewrites a
    station's dashboard migration when a story changes one.
  - With a path that no longer exists, `ruff format` exits 2 ("No such file or directory").

**Approach:** group the story's files by the tree whose ruff table governs them, and run today's two steps once per
group, from that tree's directory.
- **Selection.** Keep a changed path when all three hold:
  - it ends in `.py`;
  - it is not a CFE-surface path (`is_cfe_surface_path`, `core/dispatch_cfe_commit.py:65`), which keeps Story 83.24's
    rule that dispatch's own commits leave the CFE surface out;
  - it is a file in the worktree. A path the story deleted is never handed to ruff.
- **The group root.** Walk the path's parent directories upwards, from the nearest. Stop before the worktree root,
  which is never a group root. The first directory whose `pyproject.toml` parses with `tomllib` and has a `tool.ruff`
  table is the group root. A `pyproject.toml` without that table, or one that does not parse, is passed over, as ruff
  itself passes over it. A path with no group root is not handed to ruff.
- **The roots this gives today.** At `3c85a29a64` the only tracked tables are the ten `pyforge-*` packages and
  `src/platform` (checked with `tomllib` over every tracked `pyproject.toml`; there is no tracked `ruff.toml`). The
  nine `django-*` packages become roots when Story 93.1's tables land, and need no further marshal change.
- **The invocation.** For each group, in root order, with `cwd` the group root and the group's files relative to it,
  sorted:
  - run `["ruff", "check", "--fix", <--force-exclude>, *files]`, then `["ruff", "format", <--force-exclude>, *files]`;
  - pass `--force-exclude` when the root's table declares `exclude` or `extend-exclude`, so that a file the tree
    excludes is left as the session wrote it. A root that declares neither key is invoked exactly as today;
  - never pass `--unsafe-fixes`, `--config`, a directory or `.`.
- **The outcome of each group.**
  - `ruff check --fix` exiting 0 or 1 is a completed step. Exit 1 means findings without a safe fix remain, and verify
    judges those.
  - A `ProcessError`, an exit of 2 or more from the check step, or any non-zero exit from the format step records the
    group as failed, with the step and the exit code (none for a `ProcessError`).
  - A `ProcessError` from the check step skips that group's format step, as today.
  - A failed group never stops the next one, and a failed group is never reported as ok (AD-8).
- **The commit.** Unchanged: one `commit_paths` call over the story-set files that are dirty against `HEAD`, under
  the same subject prefix `marshal: ruff check --fix and format`. A group's changed files are the dirty files among its
  own.
- **The result.** `DispatchRuffFormatResult` keeps its two positional fields, `reformatted_paths` and `committed`,
  with today's meaning. It gains `groups`: one record per group, holding the root (repo-relative), the files handed to
  ruff (repo-relative), the files changed, `ok`, and for a failed group the step and the exit code. `groups` is
  declared with a default of `()` and `compare=False`, so every existing equality assertion still holds.
- **The journal.** `_run_and_journal_ruff_format` journals its pair when any file changed or any group failed. The
  INTENT and OUTCOME payloads keep `story_key`, `paths`, `committed` and `ok` as today (`ok` is still `committed`),
  and add `groups`, one object per record in root order. A pass with nothing changed and no failure journals nothing,
  as today. The CAP-4 path still journals nothing (83.9's review rejected that as out of scope; it stays so).
- **Unchanged:**
  - `story_scoped_pyforge_py_paths`, which keeps its signature and behaviour (its test pins that
    `src/platform/foo.py` is not a pyforge path);
  - the three callers and their order (ruff, then the `environment.yaml` step, then verify; ruff before the fix turn's
    reconcile);
  - `KIND_DISPATCH_RUFF_FORMAT`, `ProcessPort`, `CommittingVcs`, every finding code, every verify command and
    `MRS-GATE-015`'s cross-surface rule.
- **AD-4.** `core/` still imports no `os` or `subprocess`. ruff runs through `ProcessPort`, and the table is read with
  `tomllib` over the file's text, as `core/harness_profile.py` already does.

**What pre-verify can and cannot clear.**
- **It can clear** what `ruff check --fix` fixes without `--unsafe-fixes` under the tree's own rule set (I001 import
  order, F401 unused imports and the other rules with a safe fix), and what `ruff format` rewrites.
- **It cannot clear** a finding with no fix or only an unsafe fix. Those are left as written and still reach verify,
  which refuses them as today:
  - E501 on a line the formatter cannot shorten, such as a long string literal;
  - RET504, whose fix is unsafe;
  - PLC0415, which has no fix.

**The test environment (operator ruling 2026-10-11).** The real-ruff oracle cannot be allowed to skip itself.
- **The defect.** The `pyforge-marshal` pixi environment has no ruff. At `3c85a29a64`, `pixi.lock` locks no ruff
  package for `pyforge-marshal` on linux-64, osx-arm64 or win-64. `pyforge-guild`, `platform-ci-test`,
  `local-recipes` and `pyforge-foundry-full` all lock ruff 0.16.9.
- **The effect.** `pixi run --frozen -e pyforge-marshal pytest -rs .../test_dispatch_ruff_format.py` from a clean
  shell reports `SKIPPED [1] ...test_dispatch_ruff_format.py:155: ruff not on PATH`. 83.15's mutation oracle therefore
  never runs in the station's own suite or in CI's `pyforge-station-tests.yml` marshal job. It runs only where an outer
  `PATH` happens to carry another environment's ruff, as a dispatch's does.
- **The ruling.** Asked whether to fold the environment change into this story, the operator chose "Fold into 95.1
  (Recommended)", verbatim: "95.1 also adds ruff to the pyforge-marshal feature in pixi.toml, re-locks, regenerates
  environment.yaml, and makes the real-ruff tests fail instead of skip when ruff is missing. pixi.toml is
  steward-governed, so it needs a co-governor memlog and a scoped stamp."
- **The pin.** `ruff = ">=0.16.9"` in `[feature.pyforge-marshal.dependencies]`, the floor the other three sites
  declare (`[feature.pyforge-guild.dependencies]`, `[feature.platform-ci-test.dependencies]`,
  `[feature.local-recipes.dependencies]`). ruff has no single-version registry: `pixi-version-check` covers pixi's own
  version only (`scripts/pixi_version_registry.py`). `llms-full-check` checks each site's spec against the catalog's
  floor (`docs/reference/library-llms-full.md`, ruff `>=0.16.9`), so a fourth site with the same floor keeps it green.
  The feature is a test environment; the package's own `[package.run-dependencies]` and `pyproject.toml` do not change.
- **The lock.** `pixi.lock` is regenerated with `pixi lock`, never `pixi add` or `pixi update`, which the session hook
  denies.
- **`environment.yaml`.** It is regenerated in the same change with `pixi project export conda-environment -e build
  2>/dev/null > environment.yaml`, stderr discarded (Story 91.1's trap). The `build` environment composes only the
  `python` and `build` features, so the file is expected byte-identical, and the regeneration proves that.
- **The tests resolve ruff from their own environment.** They take ruff from the test interpreter's environment
  (`sysconfig.get_path("scripts")`) and put that directory first on `PATH` for the test, so that `PosixProcess` runs
  that ruff. When it is absent, they fail with a message naming the missing dependency. An outer `PATH` that carries
  another environment's ruff (a dispatch inherits `pyforge-guild`'s) can no longer hide its removal.
- **Governed files.** `pixi.toml`, `pixi.lock` and `environment.yaml` are governed paths (`scripts/.spec-surface-baseline.json`
  at `3c85a29a64`):
  - `pixi.toml`: `pyforge-doctor/spec-pixi-candidate-currency`, `pyforge-herald/spec-deck-family-currency`,
    `pyforge-herald/spec-deck-family-lockstep`, `pyforge-herald/spec-pyforge-pages`, `pyforge-marshal/spec-pyforge-core`,
    `pyforge-marshal/spec-pyforge-marshal` and `pyforge-steward/spec-pyforge-unifying-strategy`;
  - `pixi.lock`: `pyforge-doctor/spec-pixi-candidate-currency`;
  - `environment.yaml`: `pyforge-marshal/spec-pyforge-marshal` and `pyforge-steward/spec-pyforge-unifying-strategy`.

  Each of them gets a surface-reconcile memlog entry naming the path and this story, and one scoped stamp, as does
  every further Spec `spec-surface-check` names when the story runs.

Ledger key: `95-1-dispatch-applies-ruff-to-a-story-s-files-under-each-tree-s-own-config`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-161 (← `spec-marshal-single-story-dispatch` CAP-3): Story 22.3's
  verification, under which Stories 83.9 and 83.15 run their pre-verify step (as Story 91.1 cites it). 83.9 promised
  to reformat "only the files the story changed (each package's own ruff configuration)"; a story's platform and
  portal files are files the story changed. This story fixes that shipped behaviour, so it mints no CAP and changes no
  `SPEC.md`.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. A flag would keep the refusals reachable.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-11 (pre-verify ruff covers the platform and
  the portal packages). The operator's ask, verbatim: "Do this task here: Extend marshal pre-verify ruff to platform
  and portals". The environment change is the operator's ruling "Fold into 95.1 (Recommended)", quoted above.

## Acceptance Criteria

New tests go in a new module, `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_ruff_format_trees.py`.
The only change to an existing test module is AC12's change to 83.15's precondition (AC6). Each fixture is a
temporary worktree built in the test:
- **Fake-process tests** drive `apply_dispatch_ruff_format_before_verify` with a VCS fake that reports the story's
  change set against `origin/main` and the dirty set against `HEAD` (the shape of `_FormatVcs` and `_DiskDirtyVcs` in
  `test_dispatch_ruff_format.py`), and a process fake that records `(tokens, cwd)`. They never skip.
- **Real-ruff tests** (`PosixProcess`) take ruff from the test interpreter's own environment, as AC12 states, and
  fail, never skip, when it is absent. Each real-ruff assertion runs that `ruff` from the fixture's group root, as the
  gate does.

- **AC1 — A platform file is fixed under the platform table.**
  - **Given** a fixture worktree that carries a copy of the live `src/platform/pyproject.toml` (and
    `src/platform/tests/__init__.py`), and a story file `src/platform/tests/test_probe.py`. The file's import block is
    I001 under that table: one `from` line imports two names, which `force-single-line` splits. It imports only the
    standard library and one third-party name, so the result does not depend on first-party detection. The worktree
    also holds a `src/shared/packages/pyforge-marshal` package carrying a copy of the live marshal table.
  - **When** the pass runs with real ruff.
  - **Then** `ruff check --select I001 tests/test_probe.py` and `ruff format --check tests/test_probe.py`, run from
    `src/platform`, both exit 0. The file is in `reformatted_paths` and in the commit.
  - **And**, with fakes, a change set of one `pyforge-marshal` file and one `src/platform` file gives exactly four
    calls, in root order (`src/platform` sorts first): check and format for `src/platform` (cwd `src/platform`, path
    `tests/test_probe.py`), then check and format for `pyforge-marshal` (cwd the package, path relative to it).
- **AC2 — A portal package is fixed under its own table, not a pyforge one.**
  - **Given** a fixture package `src/shared/packages/django-fixture/` whose `pyproject.toml` declares its own table in
    Story 93.1's shape at `target-version = "py312"` (`line-length = 120`, `extend-exclude = ["*/migrations/*.py"]`,
    `select = ["E", "F", "W", "I"]`, `ignore = ["E501"]`). Its story file `src/django_fixture/views.py` has an I001
    import block and an `except (ValueError, TypeError):` clause. The worktree also holds the `pyforge-marshal` package
    from AC1 (live table, `py314`). The test does not depend on Story 93.1 having landed.
  - **When** the pass runs with real ruff.
  - **Then** `ruff check --select I001` from the fixture package exits 0, and the file still reads
    `except (ValueError, TypeError):`.
  - **And**, with fakes, the file's calls run with cwd the fixture package and the path `src/django_fixture/views.py`.
- **AC3 — A file with no ruff table above it is untouched.** With fakes and with real ruff, each of these files is
  byte-identical afterwards, and no recorded call names it or runs in its directory:
  - a file under a package whose `pyproject.toml` has only a `[project]` table (the nine `django-*` packages at
    `3c85a29a64`), holding an I001 block and `x=1`;
  - `scripts/tool.py`, with no `pyproject.toml` above it, while the fixture's worktree root carries a
    `pyproject.toml` with a `[tool.ruff]` table (the worktree root is never a group root);
  - a CFE-surface `.py` file in the change set;
  - a changed path that is absent from the worktree (deleted). It is never named in a call.
- **AC4 — Files outside the change set are untouched.**
  - In AC1's fixture, `src/platform/tests/test_other.py` is format-dirty and not in the change set. It is
    byte-identical afterwards.
  - With fakes, every recorded token list names only change-set files, relative to its cwd, and never a directory or
    `.`.
- **AC5 — The journal names each group, and one group's failure stops nothing.**
  - **Pass-level, with fakes.** Two groups, where the first group's `ruff check --fix` raises `ProcessError`. The
    second group's file is still changed and committed. `result.groups` lists both roots in order. The first group
    has `ok` false and step `check`, and no format call is recorded for it. The second group lists its file as
    changed, with `ok` true.
    - A format step that exits 2, or a check step that exits 2, marks its group failed with that exit code.
    - A check step that exits 1 is ok.
  - **Supervisor-level.** Beside `test_verification_journals_ruff_format_when_paths_change`, through
    `test_dispatch_supervisor_main_loop`'s `_verify`, with `run_dispatch_ruff_format_before_verify` returning a result
    that carries `groups`:
    - the OUTCOME payload's `groups` equals those records in order, and `story_key`, `paths`, `committed` and `ok`
      read as today;
    - a result whose only news is a failed group (no path changed) journals a pair with `committed: false` and that
      group;
    - a result with nothing changed and no failure journals nothing.
- **AC6 — The existing tests pass, edited only where the ruling says.**
  - These pass, and `git diff origin/main --` on each is empty:
    - `tests/unit/test_dispatch_cfe_commit.py` (`test_ruff_format_commit_never_carries_the_cfe_surface`);
    - `tests/unit/test_dispatch_supervisor_verify_fix.py` (the two ruff-format fix-turn tests);
    - `tests/unit/test_dispatch_environment_yaml.py`.
  - `tests/unit/test_dispatch_ruff_format.py` passes. Its diff touches only
    `test_apply_ruff_check_fix_removes_safe_violations`'s ruff precondition (the `shutil.which` / `pytest.skip` lines,
    :154-:155), which AC12 turns from a skip into a failure. Every other line is unchanged, so the pyforge-package
    token lists and the call count that 83.9's test pins (a root whose table declares no exclude key) do not change.
- **AC7 — What ruff cannot fix safely still reaches verify.**
  - **Given** AC1's fixture with a platform story file that holds three findings:
    - a function-local `import` (PLC0415);
    - a module-level string literal longer than 88 characters (E501);
    - `value = compute(); return value` (RET504).
  - **When** the pass runs with real ruff.
  - **Then** `ruff check --select E501,RET504,PLC0415` from `src/platform` still reports all three.
  - **And** no recorded token list, fake or real, carries `--unsafe-fixes`.
- **AC8 — A tree's excludes hold for named files.**
  - With real ruff, `src/platform/app/migrations/0001_initial.py` (format-dirty, with an I001 block) is in the change
    set. It is byte-identical afterwards and is not in `reformatted_paths`.
  - The same holds for `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dashboard/migrations/0001_initial.py`
    under the live marshal table.
  - With fakes, a root whose table declares `extend-exclude` gets `--force-exclude` in both token lists, and a root
    whose table declares neither `exclude` nor `extend-exclude` gets none.
- **AC9 — Mutation.** Each of these fails its named test:
  - skipping `src/platform` files, as today's selection does: AC1;
  - running every group under one table, or from the worktree root, or from the nearest `pyforge-*` package: AC1 or
    AC2 (the `py314` table writes `except ValueError, TypeError:`);
  - falling back to the worktree root or to ruff's defaults for a file with no table: AC3;
  - running ruff on `.` or on a group directory: AC4;
  - stopping at the first failed group, or dropping `groups` from the journal payload: AC5;
  - adding `--unsafe-fixes`: AC7 (RET504 is cleared);
  - dropping `--force-exclude`: AC8 (the migration is rewritten);
  - removing `ruff` from `[feature.pyforge-marshal.dependencies]`, then `pixi lock` and `pixi install -e
    pyforge-marshal`: AC12. Every real-ruff test, 83.15's included, fails with the missing-dependency message, even
    with `pyforge-guild`'s bin directory on the outer `PATH`;
  - restoring the skip in 83.15's test, or resolving ruff from `PATH` instead of the interpreter's environment: AC12.
- **AC10 — ruff is a dependency of the `pyforge-marshal` feature.**
  - `[feature.pyforge-marshal.dependencies]` in `pixi.toml` declares `ruff = ">=0.16.9"`, the floor the other three
    ruff sites declare, with a comment naming Story 95.1. No other ruff site, feature or environment changes.
  - `pixi.lock` is regenerated with `pixi lock` (never `pixi add` or `pixi update`). It locks a ruff package for
    `pyforge-marshal` on every platform the environment targets (linux-64, osx-arm64, win-64 at `3c85a29a64`).
  - `pixi run --frozen -e pyforge-marshal ruff --version` exits 0 from a clean shell.
  - The Auto Run Result records the version locked for `pyforge-marshal` beside the version `pyforge-guild` locks
    (0.16.9 at `3c85a29a64`).
  - `pixi run --frozen -e pyforge-guild llms-full-check` exits 0.
- **AC11 — `environment.yaml` is regenerated in the same change.**
  - `pixi project export conda-environment -e build 2>/dev/null > environment.yaml` is run after the lock, and the
    file is committed with `pixi.toml` and `pixi.lock`.
  - `yaml.safe_load` reads it.
  - Its diff against `origin/main` is what the export wrote. Empty is expected, because `build` does not compose the
    `pyforge-marshal` feature. Any other diff is recorded in the Spec Change Log.
- **AC12 — The real-ruff tests fail, never skip, without ruff.**
  - 83.15's `test_apply_ruff_check_fix_removes_safe_violations` and every real-ruff test of this story resolve ruff
    through one helper: a `tests/unit/conftest.py` fixture, or a function both modules use.
  - The helper takes the executable from `sysconfig.get_path("scripts")` of the running interpreter and puts that
    directory first on `PATH` for the test (`monkeypatch.setenv`), so `PosixProcess` runs that ruff.
  - When it is absent, the test fails through `pytest.fail` with a message naming `[feature.pyforge-marshal.dependencies]`
    and `pixi install -e pyforge-marshal`.
  - `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` from a clean shell reports no skipped real-ruff test.

## Boundaries & Constraints

**Always:**
- Hand ruff only the story's changed `.py` files that exist in the worktree, from the directory of the nearest table
  that governs them, so that each tree's target, line length, import style and excludes apply.
- Record a group whose ruff could not run, or exited outside its success codes, as failed (AD-8), and go on to the
  next group.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped, one `--spec` each, after `git add` and from a clean tree (AGENTS.md pre-PR item 5):
  - `spec-pyforge-marshal`, and every co-governor `spec-surface-check` names (`spec-pyforge-core` co-governs station
    `src/`);
  - for `pixi.toml`, `pixi.lock` and `environment.yaml`, the seven Specs named under *The test environment*, whose
    memlogs carry this story's co-governor note from its chain.
- Change `pixi.toml` by hand in `[feature.pyforge-marshal.dependencies]` only, re-lock with `pixi lock`, and
  regenerate `environment.yaml` from the export's stdout alone.

**Never:**
- Never pass `--unsafe-fixes`, and never name a file outside the story's change set, a directory or `.`.
- Never use the worktree root, or ruff's defaults, as the config for a file that has no table above it.
- Never stage or commit a CFE-surface path from this pass.
- Never edit `src/platform/pyproject.toml`, a `django-*` or `pyforge-*` table, `scripts/lint_types.py`,
  `scripts/platform-ci-local.sh` or any gate from this story. Steward owns those (Stories 93.1 and 95.1).
- Never run `pixi add` or `pixi update`, never hand-edit `pixi.lock` or `environment.yaml`, and never change another
  ruff site, feature or environment in `pixi.toml`. The one `pixi.toml` change is the ruling's.
- Never let a real-ruff test skip on a missing ruff.
- Never change a verify command, `MRS-GATE-015`'s rule, a finding code or the order of the pass and verify.

## I/O & Edge-Case Matrix

| Story file | Nearest `[tool.ruff]` table | At `3c85a29a64` | After |
|---|---|---|---|
| `src/shared/packages/pyforge-<x>/…/*.py` | the package's | fixed and formatted from the package | unchanged, plus `--force-exclude` (every live table declares `extend-exclude`) |
| `src/platform/…/*.py` | `src/platform` | untouched; verify refuses I001 under `MRS-GATE-015` | fixed and formatted from `src/platform` |
| `src/shared/packages/django-<x>/…/*.py`, no table (today) | none | untouched | untouched |
| `src/shared/packages/django-<x>/…/*.py`, after 93.1 | the package's | untouched | fixed and formatted from the package |
| `…/migrations/*.py` under a table that excludes it | that table | rewritten (pyforge) or untouched (platform) | untouched (`--force-exclude`) |
| `scripts/*.py`, `recipes/…`, `src/prototype/…` | none | untouched | untouched |
| a CFE-surface `.py` | none today | untouched | untouched (excluded by rule) |
| a deleted `.py` | any | named to ruff (`ruff format` exits 2) | never named |
| a file not in the change set | any | untouched | untouched |
| E501 the formatter cannot shorten, RET504, PLC0415 | any | reaches verify | reaches verify |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-11 (pre-verify ruff covers the platform and
  the portal packages) entry.
- Epic: Epic 95, its first story. A new epic because Epic 83, which shipped Stories 83.9 and 83.15, is `done`.
- Ledger key: `95-1-dispatch-applies-ruff-to-a-story-s-files-under-each-tree-s-own-config`.
- Ledger status at mint: `backlog`.
- Deps: none. AC2 uses a fixture table, so steward Story 93.1 need not have landed.
- Surface: `[epic_surfaces]` `"95"` in `marshal-policy.toml`. It holds the default surface (including `pixi.toml`,
  `pixi.lock` and `environment.yaml`, which the ruling's environment change needs), `scripts/.spec-surface-baseline.json`
  and every Spec memlog.
- Related: steward Story 93.1 (the `django-*` tables and the `lint-types` gate over them), steward Story 95.1 (the
  `py314` targets), herald Story 37.1 and steward Story 91.1 (the refusals above).
- Operator ruling 2026-10-11 "Fold into 95.1 (Recommended)": the environment change (AC10-AC12).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 after the memlog reconciles.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: exit 0. A `pixi.toml` or `pixi.lock` change fires
  pyforge-core's suite, the testing kit's and every station's in CI (AGENTS.md pre-PR item 7).
- `pixi run --frozen -e pyforge-marshal ruff --version` — expected: exit 0 from a clean shell (AC10).
- `pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_ruff_format.py
  src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_ruff_format_trees.py -q -rs` — expected: pass from a
  clean shell, with no skipped test (AC12).
- `pixi project export conda-environment -e build 2>/dev/null > environment.yaml && git diff --exit-code
  environment.yaml` — expected: exit 0 once the regenerated file is committed (AC11).
- `pixi run --frozen -e pyforge-guild llms-full-check` — expected: exit 0 (AC10).
- The nine mutations of AC9 — expected: each fails its named test. Restore each, re-lock and re-install after the
  feature mutation.
- `git diff origin/main -- src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_cfe_commit.py
  src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_verify_fix.py
  src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_environment_yaml.py` — expected: empty; and
  `git diff origin/main -- src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_ruff_format.py` — expected:
  only 83.15's ruff precondition (AC6).

## Named, not fixed here

- **Three ruff binaries.** Each one is used in a different place:
  - the pass runs the ruff on the supervisor's `PATH` (`pyforge-guild`);
  - `platform-ci-local` runs `platform-ci-test`'s;
  - after AC10, the station's tests run `pyforge-marshal`'s.

  The first two resolve to 0.16.9 in `pixi.lock` at `3c85a29a64`. The three sites share a floor, not a version, so a
  lock that moves one and not the others could make the pass's format disagree with a gate's `--check`. AC10 records
  the version `pyforge-marshal` locks; a registry that holds one ruff version is not this story's.
- **The marshal package does not declare ruff.** The pass shells to `ruff`, but `[package.run-dependencies]` in
  `src/shared/packages/pyforge-marshal/pixi.toml` and `pyproject.toml` do not change; the ruling names the feature.
  An install of the package alone, with no ruff on `PATH`, gets a `ProcessError` for every group. Each group is then
  journaled as failed (AD-8), and verify judges the story's files as written.
- **`ruff.toml` and `.ruff.toml`.** No tracked tree uses one. A tree that adopts one instead of a `pyproject.toml`
  table is not a group root, so its files stay untouched until a story widens the walk.
- **Findings with no safe fix still cost a verify-fix turn.** That covers E501 the formatter cannot shorten, RET504
  and PLC0415. Steward 91.1's turn was killed at 900 s on a finding this pass will clear first; the turn's budget is
  not this story's.
- **The CAP-4 land-only path** runs the pass without a journal, as since 83.9.

## Spec Change Log

## Review Triage Log

### 2026-10-11 — Review pass
- verdicts: 1 findings — high 0, medium 0, low 1, false 0, maybe-false 0
- findings:
  - `[low]` `[patch]` Unused assignment in `test_dispatch_ruff_format_trees.py` — removed during verify lint-types leg.

## Auto Run Result

Status: done

Summary: Dispatch pre-verify ruff now groups each story `.py` file under the nearest `[tool.ruff]` tree (platform, portal packages, pyforge packages), honors `--force-exclude` when the table declares excludes, skips deleted/CFE/non-table paths, records per-group outcomes, and journals failures without paths changing. Added `ruff >=0.16.9` to `[feature.pyforge-marshal.dependencies]` with lock/export refresh.

Files changed:
- `dispatch_ruff_format.py` — tree grouping, group results, CFE/deleted filtering, force-exclude.
- `dispatch_supervisor/__main__.py` — journal when any group fails or paths change; payload `groups`.
- `tests/unit/conftest.py` — `ruff_from_test_env` / `require_ruff_from_test_env` (AC12).
- `tests/unit/test_dispatch_ruff_format.py` — real-ruff oracle uses test env ruff, never skips.
- `tests/unit/test_dispatch_ruff_format_trees.py` — AC1–AC8, AC5 journal coverage.
- `pixi.toml`, `pixi.lock`, `environment.yaml` — marshal feature ruff pin (AC10–AC11).
- Co-governor `.memlog.md` entries on spec-pyforge-marshal, spec-pyforge-core, spec-pixi-candidate-currency, spec-pyforge-unifying-strategy, herald pixi co-governors.

Review: 1 low patch applied (unused variable); nothing deferred.

Follow-up review recommended: false (0 high/medium patches).

Verification:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 12436 passed, 20 skipped.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed.
- `pixi run --frozen -e pyforge-marshal pytest … test_dispatch_ruff_format*.py -q -rs` — 16 passed, 0 skipped.
- `pixi run -e pyforge-guild lint-types` — exit 0.
- `pixi run --frozen -e pyforge-guild llms-full-check` — clean.
- `python scripts/spec_surface_reconcile.py` — OK.
- `pyforge-marshal` locks ruff **0.17.0** (`.pixi/envs/pyforge-marshal/bin/ruff --version`); guild env not installed in this worktree for a side-by-side 0.16.9 read.

Residual: Scoped `spec-surface` baseline stamps for co-governors remain for the PR author (`--write-baseline --spec …` after memlog); this run did not stamp per dispatch guard.
