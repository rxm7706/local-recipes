---
title: '106.1: The two mypy lanes keep separate caches'
type: 'fix'
created: '2026-10-16'
status: 'done'
baseline_revision: 'f44a99ba0c04b48b2d406c603181f80c61ba50d2'
flag-exempt: detector-or-gate   # a fix to the lint gate's own task; a gated gate reports a silent green
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-5-the-preflight-keys-each-lane-by-its-task-and-its-environment.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-31-1-atlas-passes-mypy-in-pyforge-foundry-full-and-a-lane-keeps-it-so.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
  - scripts/lint_types.py
  - pixi.toml
  - .github/workflows/lint-types.yml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/tests/unit/test_lint_types_not_yet_clean.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** two lanes in two environments read and write one mypy cache. Line numbers are at `f44a99ba0c`.

- **Two lanes, one task.** Since atlas Story 31.1 (#2221), `pr-preflight-lanes` (`pixi.toml:1621`) names the `mypy`
  task twice: through `lint-types` in the invoking environment, `pyforge-guild`, and as `{ task = "mypy", environment
  = "pyforge-foundry-full" }`. The preflight runs lanes in a thread pool sized to the logical core count
  (`preflight.py:1036`, `:1147`), each as `pixi run --frozen --skip-deps -e <env> <task>` (`:703`-`:713`), so the two
  run at the same time. CI's `lint-types` job runs both, one after the other, in one checkout
  (`.github/workflows/lint-types.yml:59`, `:61`).
- **One cache.** Both lanes run `python scripts/lint_types.py mypy`, which runs `mypy -p pyforge.<station>` with the
  package as its working directory and no cache dir (`scripts/lint_types.py:181`). No package's `[tool.mypy]` sets
  `cache_dir`, so both write `<package>/.mypy_cache/3.14/`: mypy 2.4.0's default SQLite cache, sixteen
  `cache.<n>.db` shards. The preflight gives each lane its own `TMPDIR`, pytest basetemp and cache dir, and coverage
  file (`_lane_scratch_env`, `preflight.py:431`), and nothing for mypy.
- **Two views of the world.** The two environments resolve third-party imports differently. The Guild has no Vizro,
  Dagster, Kedro or OpenLineage and reads them as `Any` (atlas's `ignore_missing_imports`); foundry-full has them all.
  Their `site-packages` paths differ too, so every cache entry for a third-party module names a different source path.
- **The rule it breaks.** CAP-159: "Concurrent lanes share no mutable state". Named as nit 5 of steward Story 103.5's
  review ("tracked separately") and recorded by atlas's 2026-10-15 retrospective as `DW-atlas-retro-2026-10-15-2`
  (owner steward, severity low).

**Measured at `f44a99ba0c`** (16 logical cores, load average 2-4; mypy 2.4.0 and Python 3.14.7 in both
environments; every exit code read directly):

- **Alone.** Guild: cold 32 s, then warm 3 s, exit 0. Foundry-full: cold 53 s, then warm 3 s, exit 0.
- **Both at once, as the preflight runs them.** 5 trials on a cold cache (36-37 s) and 3 on a warm one (8-11 s): every
  run exited 0, and no log held a traceback, `database is locked`, `OperationalError`, `INTERNAL ERROR` or any `error:`.
- **With a planted error only foundry-full can see.** `_MYPY_CACHE_PLANT: int = dg.AssetKey("plant")` appended to
  `pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py` (Dagster is `Any` in the Guild):
  - in sequence on one cache (foundry, Guild, foundry, Guild; then Guild cold, foundry): foundry-full exited 1 naming
    the plant every time, and the Guild exited 0 every time;
  - both lanes at once: 5 cold and 3 warm trials, Guild 0 and foundry-full 1 each time;
  - `mypy -p pyforge.atlas` in both environments at once, 10 trials (alternately cold and warm): the same verdicts,
    no anomaly.
  - The plant was then removed; `git status` showed the file clean.
- **Why the verdicts held.** Read in mypy's own log (`-v`), a foundry-full run after a Guild run finds the atlas modules
  "fresh" and then re-checks them, because their dependency sets differ (113 `pyforge` modules re-written); entries
  whose source content is the same in both environments are re-pointed ("Updating mtime"), not trusted blind.
- **What it costs.** Churn: each lane rewrites the other's entries. Two warm lanes at once took 8-11 s against 3 s for
  each on a cache of its own.
- **Could not reproduce** a changed verdict, a corrupt cache, or a crash. The defect is the shared mutable state CAP-159
  rules out, and the churn it causes, not a wrong answer seen.

**Approach:** each environment keeps its own cache, in the script both lanes run.

- **The key.** `mypy_cache_env()` returns `PIXI_ENVIRONMENT_NAME`, else the basename of `CONDA_PREFIX`, else the
  basename of `sys.prefix`. A nested `pixi run -e <env>` sets `PIXI_ENVIRONMENT_NAME` over an inherited value (checked:
  run from the Guild, a nested `pixi run -e pyforge-foundry-full` reads `pyforge-foundry-full`, with that env's `mypy`).
- **The path.** `mypy_cache_dir(pkg)` returns `<package>/.mypy_cache/<environment>`. It stays under `.mypy_cache/`,
  which the root `.gitignore` ignores at any depth (`.mypy_cache/`, `:214`; `src/**/packages/*/**/.mypy_cache/`,
  `:539`), as do `.dockerignore`, doctor's `env_hygiene` walk and the CFE and SKF tree walkers. Nothing reads the old
  path.
- **The argv.** The `mypy` verb runs `mypy --cache-dir <package>/.mypy_cache/<environment> -p pyforge.<station>` and
  prints the cache it uses once. A command-line `--cache-dir` outranks `MYPY_CACHE_DIR` and the config file (mypy's
  `main.py`), so neither can put two environments back on one cache.
- **Kept as it is.** The lane list, the preflight runner, `pixi.toml`, both workflow steps and the ruff verbs. CI caches
  no `.mypy_cache` (`setup-pixi` caches the environments only), so no CI cache key moves.

**Rejected:**
- **A preflight mutex for the two `mypy` lanes.** It would serialize them, which costs the warm-cache time back, and
  would leave CI's two steps on one cache. It would also extend Story 105.1's `tree:docs-site` mutex in `preflight.py`
  (#2242, merged `94a77d724d` while this story was in review).
- **`MYPY_CACHE_DIR` set by the preflight per lane.** It fixes the preflight and leaves CI and a hand run sharing; the
  cache path belongs to the task, which every runner calls.
- **`.mypy_cache-<environment>` beside `.mypy_cache`.** Unique too, but no ignore rule or tree walker knows that name.
- **A cache per lane run, under the lane's scratch directory.** Cold on every run: the 3 s warm run becomes 32-53 s.

Ledger key: `106-1-the-two-mypy-lanes-keep-separate-caches`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (Stories 71.1-71.3, 71.6-71.8, 71.10, 99.5, 103.5, 103.6,
  104.1): concurrent lanes that share no mutable state. Story 71.3 gave each lane its own temp dir, pytest basetemp
  and cache dir, and coverage file, and Story 71.8 moved them out of the checkout. This story extends that property to
  mypy's cache. It mints no CAP and changes no `SPEC.md`.
- **Why CAP-159, not CAP-153.** The change sits in CAP-153's task script, but CAP-153's intent and success (the tasks,
  one CI lane and one preflight leg that run them, a planted violation red in both) hold before and after. The rule
  the shared cache breaks is CAP-159's, and it arises because CAP-159 runs the two lanes at once.
- **Governance.** `scripts/lint_types.py` and the two new tests are on `spec-pyforge-steward`'s surface
  (`scripts/.spec-surface-baseline.json`); the atlas deferred-work ledger is on `spec-pyforge-atlas`'s.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag; the frontmatter records
  `flag-exempt: detector-or-gate` (the lint gate's own task).
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, the 2026-10-16 (the two mypy lanes share one cache)
  entry; `DW-atlas-retro-2026-10-15-2`.

## Acceptance Criteria

AC1-AC4 run the real `scripts/lint_types.py` over a fixture tree with `_run` and the tool lookup stubbed; AC5 reads the
live `pixi.toml`, workflow and `.gitignore`. None runs pixi or mypy.

- **AC1 — The key.** `mypy_cache_env` returns `PIXI_ENVIRONMENT_NAME` when it is set and non-blank, even beside a
  `CONDA_PREFIX`; else the basename of `CONDA_PREFIX`; else the basename of `sys.prefix`, never an empty name. With no
  argument it reads the process environment. `mypy_cache_dir(pkg)` is `pkg / ".mypy_cache" / <key>`.
- **AC2 — Every package's run names its cache.** `main(["mypy"])` runs mypy once per `pyforge-*` package, in package
  order, each with argv `["mypy", "--cache-dir", "<package>/.mypy_cache/<key>", "-p", "pyforge.<station>"]`, and
  prints `[lint-types] mypy cache  <package>/.mypy_cache/<key>/`. *(Added at review, 2026-10-16:)* that line and every
  status line are printed with `flush=True`, so a piped log shows each beside the tool output it describes.
- **AC3 — Two environments, two caches.** Run under `pyforge-guild` and then `pyforge-foundry-full`, the two runs'
  cache directories are disjoint for all ten packages, and each package's two share the parent
  `<package>/.mypy_cache`.
- **AC4 — Ruff is unchanged.** The `ruff` and `ruff-format` verbs pass no `--cache-dir`.
- **AC5 — The live tree.** The environments that run `mypy` (directly or through `lint-types`) in `pr-preflight-lanes`
  and in `lint-types.yml` include `pyforge-guild` and `pyforge-foundry-full` (a blindness guard); the real
  `mypy_cache_dir` gives each of them a different directory under `<package>/.mypy_cache/` in every live `pyforge-*`
  package; the root `.gitignore` carries the unanchored `.mypy_cache/` rule.
- **AC6 — Mutation.** Each change below fails a named test, and the Implementation Result records which:
  - dropping `--cache-dir` from the mypy argv (AC2, AC3);
  - keying the cache on a constant (AC1, AC3, AC5);
  - dropping the `CONDA_PREFIX` fallback (AC1);
  - returning an empty name with neither variable set (AC1);
  - reading `CONDA_PREFIX` before `PIXI_ENVIRONMENT_NAME` (AC1, AC2), under `pixi run` and in a bare shell alike;
  - *(added at review)* dropping `flush=True` from the cache line, or from the per-package status line (AC2).
- **AC7 — The real lanes.** `pixi run --frozen -e pyforge-guild lint-types` exits 0 twice, the second run warm;
  `pixi run --frozen -e pyforge-foundry-full mypy` exits 0 twice; the two run at once three times, both exit 0 each
  time, and every package then holds `.mypy_cache/pyforge-guild/` and `.mypy_cache/pyforge-foundry-full/`.
- **AC8 — Green, the surface reconciled.** `pixi run --frozen -e pyforge-steward pyforge-steward-test` and
  `tests/scripts/test_lint_types_gate.py` exit 0; each changed governed path gets a surface-reconcile entry on the
  memlog of every Spec that governs it.

## Boundaries & Constraints

**Always:**
- Keep the cache under `<package>/.mypy_cache/`, so every existing ignore rule and tree walker covers it.
- Keep the verdicts: the mypy argv changes only by `--cache-dir`, and each package's own `[tool.mypy]` still decides
  what is checked.

**Never:**
- Never touch `preflight.py` (Story 105.1's, #2242, merged `94a77d724d`), `pixi.toml`, `pixi.lock` or a workflow,
  with one exception, Story 98.1's rule *(amended at landing, 2026-10-16)*: `pyforge-station-tests.yml`'s steward
  job lists `.gitignore`, because AC5's meta test reads it.
- Never weaken or delete an existing assertion.

**Residual risk:**
- CI's second step, foundry-full `mypy`, no longer reads the cache the Guild step just wrote. Measured locally, a cold
  foundry-full run after a cold Guild run took 41-42 s on the shared cache and takes 53-54 s on its own, so the job
  may take about 12 s longer. Both preflight lanes run cold the same way the first time (36 s together before, 58 s
  after), and warm after that (8-11 s before, 3-4 s after).
- **Disk** *(added at review, 2026-10-16)*. One shared cache was about 259 MB per checkout; split, it is about 124 MB
  for `pyforge-guild` plus 252-258 MB for `pyforge-foundry-full`, about 376-382 MB (+~123 MB, +48%) in every checkout
  or worktree that runs both lanes (the review measured 382 MB on archive copies; 376 MiB here). `steward workspace
  clean`'s tarballs include `.mypy_cache`, because `_archive_worktree` drops only `REINSTALLABLE_ENV_DIRS`
  (`.pixi/{envs,solve-group-envs,bld}`, `workspace.py:748`), so the archives grow by the same amount. An existing
  checkout also keeps its old `<package>/.mypy_cache/3.14/` as dead data, up to about 259 MB (ignored by git);
  deleting it is safe. Dropping tool caches from the archive filter is out of scope here.
- A run with neither `PIXI_ENVIRONMENT_NAME` nor `CONDA_PREFIX` set keys on `sys.prefix`'s basename, so two such runs
  from interpreters whose prefixes share a basename would share a cache. Every lane and CI step runs through pixi.

## I/O & Edge-Case Matrix

| Situation | Before (`f44a99ba0c`) | After |
|---|---|---|
| preflight runs both `mypy` lanes at once | both write `<pkg>/.mypy_cache/3.14/` | `<pkg>/.mypy_cache/pyforge-guild/` and `<pkg>/.mypy_cache/pyforge-foundry-full/` |
| CI's `lint-types` job, two steps in one checkout | step 2 reads and rewrites step 1's cache | each step its own cache |
| a second warm run of one lane | 3 s alone; 8-11 s while the other lane rewrites it | 3 s |
| `PIXI_ENVIRONMENT_NAME` set and `CONDA_PREFIX` names another env | n/a | the pixi name wins |
| `PIXI_ENVIRONMENT_NAME` unset or blank | n/a | the basename of `CONDA_PREFIX` |
| neither set | `.mypy_cache/` in the package | `.mypy_cache/<basename of sys.prefix>/` |
| `MYPY_CACHE_DIR` set by the operator | used, shared by both lanes | outranked by `--cache-dir`; never created |
| `ruff`, `ruff-format` | no cache flag | unchanged |

</intent-contract>

## Binding

- Parent Spec capability: a fix under `spec-pyforge-steward` CAP-159 (concurrent lanes share no mutable state), in
  CAP-153's task script. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-16 (the two mypy lanes share one cache)
  entry.
- Epic: Epic 106 (new), Story 106.1; `epic-106` and `epic-106-retrospective` are minted with it. Epic 106, not 105:
  Epic 105 is Story 105.1's (#2242, merged `94a77d724d`).
- Ledger key: `106-1-the-two-mypy-lanes-keep-separate-caches`.
- Ledger status at mint: `backlog` (as 103.5's was while it was in review); `done` in the landing merge, with
  `epic-106` rolled up to `done`.
- Deps: none.
- Closes: `DW-atlas-retro-2026-10-15-2` (`status: closed` in the landing merge, with a `verified:` line citing
  steward 106.1).
- Surface: `marshal-policy.toml` `[epic_surfaces]."106"`.
- Flag: none — a fix (`spec-feature-flag-governance` Q1); `flag-exempt: detector-or-gate` recorded above.

## Epic excerpt

Story 106.1 in `epics.md` § Epic 106: the two `mypy` lanes keep separate caches.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`;
  MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest -q src/shared/packages/pyforge-steward/tests/unit/test_lint_types_mypy_cache.py src/shared/packages/pyforge-steward/tests/meta/test_lint_types_mypy_cache_per_environment.py` — expected: 15 passed (AC1-AC5).
- The AC6 mutations, one at a time against `scripts/lint_types.py`, re-running the two files — expected: each fails
  its named tests; restore the file after each.
- `pixi run --frozen -e pyforge-ci python -m pytest -q tests/scripts/test_lint_types_gate.py` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types`, twice — expected: exit 0 both times (AC7).
- `pixi run --frozen -e pyforge-foundry-full mypy`, twice — expected: exit 0 both times (AC7).
- Both of the above `mypy` runs at once, three times — expected: both exit 0 each time, and both cache directories in
  every package (AC7).
- `pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and one scoped stamp per
  Spec (AC8).

## Spec Change Log

- 2026-10-16: minted from the Dream's 2026-10-16 entry and `DW-atlas-retro-2026-10-15-2`. `type: fix`, no flag, no
  CAP; bound to `spec-pyforge-steward` CAP-159. Measured first: no verdict change, corruption or crash reproduced;
  the shared cache and its churn are the defect.
- 2026-10-16 (implementation): hand-implemented on branch `chain-preflight-mypy-cache-2026-10-16` from `f44a99ba0c`;
  status `in-review` for an independent review against this spec (commit `3df4461dbd`).
- 2026-10-16 (review): PASS with two should-fix findings and four nits (§ Review), all resolved on the branch in the
  merge of `origin/main` (steward 105.1, `94a77d724d`). AC2 and AC6 gained the flush clause; no other AC changed.
- 2026-10-16 (landing): status `done`; the ledger key and `epic-106` `done`; `DW-atlas-retro-2026-10-15-2` closed.

## Implementation Result

Hand-implemented on branch `chain-preflight-mypy-cache-2026-10-16`, from baseline `f44a99ba0c`. The diff is for an
independent review against this spec, not against this summary.

- **`scripts/lint_types.py`:** `mypy_cache_env(environ=None)` and `mypy_cache_dir(pkg, environ=None)`; the `mypy`
  verb runs `mypy --cache-dir <package>/.mypy_cache/<environment> -p pyforge.<station>` and prints
  `[lint-types] mypy cache  <package>/.mypy_cache/<environment>/` once; the module docstring says why. `_run` passes
  `check=False` explicitly: ruff's PLW1510 on the touched file, fixed in passing; behaviour is unchanged.
- **Tests (new):** `tests/unit/test_lint_types_mypy_cache.py` (AC1-AC4, 12 cases after the review) and
  `tests/meta/test_lint_types_mypy_cache_per_environment.py` (AC5, 3 cases), both in `pyforge-steward`, the home of
  the existing `lint_types` tests.
- **AC6, each mutation against `scripts/lint_types.py`, the file restored after each (`cmp` clean):**
  - no `--cache-dir` in the argv failed `test_mypy_passes_each_package_its_environment_cache_dir` and
    `test_two_environments_never_share_a_cache_dir`;
  - a constant key (`"shared"`) failed all 10 key, argv and disjointness cases, including the meta test's
    `test_every_mypy_environment_gets_its_own_cache_in_every_package`;
  - no `CONDA_PREFIX` fallback failed the three `test_without_a_pixi_environment_the_conda_prefix_names_the_cache`
    cases;
  - an empty name with neither variable set failed `test_without_either_variable_the_interpreter_prefix_names_the_cache`;
  - `CONDA_PREFIX` read first failed `test_the_cache_is_keyed_on_the_pixi_environment_first`,
    `test_the_cache_key_reads_the_process_environment_by_default`, the argv test and the disjointness test.
  - *Re-run after the review, under `pixi run` and in a bare shell (`env -u CONDA_PREFIX -u PIXI_ENVIRONMENT_NAME`),
    seven mutations:* the five above failed 2, 10, 3, 1 and 4 tests in both runners (the fifth had failed only 1 in a
    bare shell before the three tests pinned `CONDA_PREFIX`); no `flush=True` on the cache line, and none on the
    status line, each failed `test_every_line_the_mypy_run_prints_is_flushed_before_the_tool_runs` in both.
- **Not changed:** `preflight.py`, `pixi.toml`, `pixi.lock`, `environment.yaml`, `lint-types.yml`, `.gitignore`. The one
  workflow edit, found at landing: `.github/workflows/pyforge-station-tests.yml`'s `steward_paths` gains `.gitignore`
  (Story 98.1's rule; atlas, herald and marshal already list it), so the job that runs AC5's meta test fires when
  the file it reads changes.

## Review

The independent review (2026-10-16) of commit `3df4461dbd`, read against this spec, returned **PASS** with two
should-fix findings and four nits (scratchpad `review-106-1.md`). Each resolution lands on the same branch, in the
merge of `origin/main` at `94a77d724d` (steward 105.1).

- **1 (should-fix) — Residual risk left out the disk cost.** **Resolution:** the Disk bullet under Residual risk
  (about 259 MB to 376-382 MB per checkout that runs both lanes, the `workspace clean` tarballs, the dead `3.14/`).
- **2 (should-fix) — Five merge conflicts with `origin/main`, three of them traps.** **Resolution:** as the review
  set out. `epics.md` keeps one `updated:` key (106.1's amendment, then ` Prior: ` and 105.1's) and orders Epic 105
  before Epic 106; `marshal-policy.toml` closes the `"105"` array before `"106"` (checked with `tomllib`); the
  memlog keeps one `updated:` key, 105.1's entries first; the ledger is main's, re-synced from a worktree-local feed
  (`# stories: 598`); `test-architecture.md` is regenerated (386 stories, 138 test files, 106 epics).
- **3 (nit) — Three tests inherited `CONDA_PREFIX`,** so a key reading it first was killed by one test in a bare
  shell. **Resolution:** they set `CONDA_PREFIX` to another environment; the mutation now fails four tests in both
  runners.
- **4 (nit) — The `"106"` surface left out `test-architecture.md`.** **Resolution:** added.
- **5 (nit) — The new cache line, like the status lines, was not flushed,** so a piped log printed it after all ten
  packages' mypy output. **Resolution:** `flush=True` on the cache line and the three in-loop status prints, a
  docstring sentence, and `test_every_line_the_mypy_run_prints_is_flushed_before_the_tool_runs`; a piped real run
  now prints the cache line first and each status line after its package's `Success:` line.
- **Found at landing, not by the review — AC5's meta test reads `.gitignore`, and steward's CI job did not fire on
  it.** On the merged tree, `test_station_tests_trigger_map.py::test_every_read_and_declared_glob_fires_its_job`
  failed: "steward: read `.gitignore` (from …/test_lint_types_mypy_cache_per_environment.py) … the `changes` step left
  output `steward` false". It passed in the pre-review suite run only because that run started before the new test
  file was staged, and the derivation reads tracked files. **Resolution:** `.gitignore` joins `steward_paths` in
  `pyforge-station-tests.yml` (Story 98.1's rule, as atlas, herald and marshal already have it); the trigger-map and
  path-filter tests then passed (46). The alternative, dropping the `.gitignore` assertion, would leave AC5 short.
- **6 (nit) — Wording that goes stale once 105.1 merges.** **Resolution:** this spec, the Epic 106 intro, the
  `epics.md` amendment and the two 106.1 memlog entries now say Epic 105 is Story 105.1's (#2242, merged
  `94a77d724d`).

## Verification run (2026-10-16)

On the 16-core host, at the branch's working tree (baseline `f44a99ba0c` plus this change); every exit code read
directly, never through a pipe.

- New tests, `pixi run --frozen -e pyforge-steward python -m pytest -q` on the two files: exit 0, 14 passed.
- `pixi run --frozen -e pyforge-ci python -m pytest -q tests/scripts/test_lint_types_gate.py`: exit 0, 30 passed.
- `pixi run --frozen -e pyforge-guild lint-types`, cold then warm: exit 0 (28 s), exit 0 (4 s); every package then
  held `.mypy_cache/pyforge-guild/` and no top-level `.mypy_cache/3.14/`.
- `pixi run --frozen -e pyforge-foundry-full mypy`, cold then warm: exit 0 (54 s), exit 0 (3 s).
- Both `mypy` lanes at once, 3 cold trials (58-59 s) and 3 warm (3-4 s): every run exit 0, no traceback, lock or
  `error:` in any log, and all ten packages held both `.mypy_cache/pyforge-guild/` and
  `.mypy_cache/pyforge-foundry-full/`.
- `git check-ignore -v` on a new cache file: ignored (`.gitignore:539`).
- `MYPY_CACHE_DIR=<scratch dir> pixi run --frozen -e pyforge-guild mypy`: exit 0, and the scratch dir was never
  created (`--cache-dir` outranks it).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` (the station's `verify_commands`): exit 0, 2828 passed,
  2 skipped, 1 warning, in 455 s.
- `pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check`: exit 0.
- Planning detectors (`pixi run --frozen -e pyforge-guild <task>`), on the staged tree: chain-completeness,
  dream-chain, dreams-hygiene, deferred-work, ledger-regression, story-status, chain-currency-sweep, ad-citation,
  flag-gate, tea-playwright and spec-surface, each exit 0. ad-citation first exited 1 on a bare `CAP-159` in the atlas
  deferred-work row; it now reads `spec-pyforge-steward:CAP-159`.
- `spec-surface-check`: exit 0 once the memlog entries named every governed path (`spec-pyforge-steward`: the script,
  the two tests, the story spec; `spec-pyforge-atlas`: its deferred-work ledger). No baseline is stamped on this
  branch; the landing stamps each Spec scoped.
- Not run here: the full `pr-preflight`, `detectors-ci` and the steward coverage gate (left to the landing).

## Verification run (2026-10-16, after the review and the merge of `origin/main`)

On the merged tree (`3df4461dbd` + `origin/main` at `94a77d724d` + the review fixes), staged; every exit code read
directly.

- New tests, under `pixi run --frozen -e pyforge-steward` and in a bare shell (`env -u CONDA_PREFIX -u
  PIXI_ENVIRONMENT_NAME`): exit 0, 15 passed in each. The seven mutations (Implementation Result) each failed their
  named tests in both.
- `pixi run --frozen -e pyforge-ci python -m pytest -q tests/scripts/test_lint_types_gate.py`: exit 0, 30 passed.
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0 (4 s, warm). `pixi run --frozen -e pyforge-foundry-full mypy`:
  exit 0 (4 s, warm). A piped `pixi run --frozen -e pyforge-guild mypy` printed the cache line first and each status
  line after its package's `Success:` line.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test`: first exit 1, 1 failed and 2855 passed
  (`test_every_read_and_declared_glob_fires_its_job`, § Review, found at landing); after `.gitignore` joined
  `steward_paths`, exit 0, 2856 passed, 2 skipped, 1 warning, in 535 s.
- `pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check`: exit 0.
- `marshal-policy.toml` read with `tomllib`: `"105"` and `"106"` both whole.
- `sprint-ledger-sync -- --project steward` from a worktree-local feed (deleted after): exit 0, `# stories: 598`,
  `106-1-…: done`, `epic-106: done`; `story-status-check` exit 0 (373 audited) before and after the feed was removed.
- `bmad_tea_playwright.py --project pyforge-steward`: exit 0, 386 stories, 138 test files, 106 epics.
- Planning detectors, each `pixi run --frozen -e pyforge-guild <task>`: chain-completeness, dream-chain,
  dreams-hygiene, deferred-work, ledger-regression, story-status, chain-currency-sweep, ad-citation, flag-gate,
  tea-playwright and spec-surface, each exit 0. `deferred-work-check` first exited 2 on the closing `verified:` line
  (`verified-line-uncited`); it now cites `scripts/lint_types.py:219` and two commands with their exit codes.
- No baseline stamped: `spec-pyforge-steward` and `spec-pyforge-atlas` are left for the scoped stamps after the merge
  commit.
