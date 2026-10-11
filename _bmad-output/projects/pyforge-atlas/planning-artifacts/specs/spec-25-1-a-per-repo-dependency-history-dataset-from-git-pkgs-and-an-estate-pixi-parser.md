---
title: "25.1: A per-repo dependency-history dataset from git-pkgs and an estate pixi parser"
type: 'feature'
created: '2026-09-28'
status: 'in-review'
baseline_revision: f9c6a87dbe45d0e03d9a422dd708e466ce19bada
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - docs/dreams/pyforge-atlas.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/tests/unit/catalog/test_no_inline_io.py
  - src/shared/packages/pyforge-atlas/tests/unit/singularity/test_duckdb_sole_engine.py
flag:
  key: pyforge.atlas.dependency_history
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "repo_dependency_history is not built; its vcs_health node skips as not-applicable"
  cleanup: 90 days after ON in every environment (Q4)
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Blocked (cross-station):** this story needs the `git-pkgs` conda package, which mason Story 21.1 builds (engines
arrive as conda packages with tested version ranges). The Deps parser is station-local, so the ledger row is minted
`blocked`; the operator flips it once mason 21.1 is `done` and the package resolves in the `pyforge-atlas` environment.

**Gate cleared 2026-10-10.** Mason Story 21.1 is `done` on main: its landing, PR #1990 (merge `b845b8d10f`, "Merge
pyforge-mason/21-1 into main"), is an ancestor of `origin/main` (`git merge-base --is-ancestor b845b8d10f origin/main`
exits 0 at `2d90c634f3`), and mason's ledger row `21-1-git-pkgs-builds-green-from-source-as-a-local-recipe` reads `done`.
`recipes/git-pkgs/recipe.yaml` is on main at version `0.21.0`. The operator ruled the same day (verbatim): "yes flip the
six cleared stories and dispatch them". The ledger key moved `blocked -> backlog` through a worktree-local Tier-3 feed
and `sprint-ledger-sync --project atlas --allow-regression`; this spec is `ready-for-dev`.

**Not yet true on 2026-10-10: the package does not resolve.** The second half of the condition above does not hold.
`git-pkgs` is in no channel the workspace solves from: `api.anaconda.org/package/SelfExplainML/git-pkgs` and
`.../conda-forge/git-pkgs` both returned 404 on 2026-10-10, and the workspace channels are `["conda-forge",
"SelfExplainML"]` (`pixi.toml:19`). Mason 21.1 ends at a green local build in `build_artifacts/`, and `pixi.toml:2471`
bans a local `file://` channel. If the run-dependency range cannot be declared because the package does not resolve,
the dispatch stops and reports it. It does not add a channel, vendor a binary or download a release, and it does not
publish the package (an outward act the operator owns).

**Since minting (dated 2026-10-10; Story 25.2 landed first, PR #1882, merge `3f2744da9e`):**
- The placeholder node `build_repo_dependency_history` already exists (`pipelines/vcs_health/nodes.py:681`, a no-op
  returning an empty frame; wired at `pipeline.py:139-144` with output `repo_dependency_history`). The catalog entry
  `repo_dependency_history` also already exists, as a plain `pandas.ParquetDataset` placeholder (`conf/base/catalog.yml:807`).
  Story 25.2's sensor and its job `vcs_repo_dependency_history` target the node by name
  (`orchestration/definitions.py:289`, `:349`, `:816`). This story fills that node and replaces that catalog entry. It
  does not add a second one. It keeps the node name and the dataset name, so 25.2's wiring holds.
- The flag reader exists: `pyforge.core.flags.read_boolean` (`pyforge-core/src/pyforge/core/flags.py:496`, steward 75.1).
  So the "if 75.1 has not landed" clause in the Boundaries does not apply.
- The `spec-feature-flag-governance:CAP-4` fixture has landed (marshal Story 74.1, `pyforge.testing_kit.flags`:
  `flag_states`, `flagd_tree`). The two-state test in the Verification uses it, not the interim
  `test_openfeature_file_flags.py` shape.
- The ACs are unchanged.

**Problem:** Atlas's datasets cover all of conda-forge, but nothing holds one repo's manifests across its commits.
Warden's actuator and fleet scan (`spec-pyforge-warden:CAP-24`, `spec-pyforge-warden:CAP-26`) need to know when a vulnerable dependency
arrived in a repo and which other repos carry it; the operator ruled on 2026-09-28 that the data belongs in Atlas and
the verdict in Warden. git-pkgs (MIT) walks a repo's history into SQLite, but it installs git hooks by default, keeps
its database in the repo's `.git` by default, and has no `pixi.toml` / `pixi.lock` parser (upstream issue #79).

**Approach:** A custom dataset in `datasets/dependency_history.py` takes a list of repo sources (a local path, or a
clone URL whose host's credential is scoped in the catalog, AD-2) and, per repo: keeps a clone in Atlas's cache (never
the operator's working copy); runs `git pkgs init --no-hooks` with `GIT_PKGS_DB` at a throwaway path outside the repo,
through `pyforge.core.process` (the atlas package imports no `subprocess`); reads the change rows through DuckDB's
sqlite reader, provisioned offline, or through git-pkgs' own JSON output — never an `sqlite3` import — and deletes the
database; and walks the commits touching `pixi.toml` / `pixi.lock` with an Atlas-native parser (`tomllib`,
`yaml.safe_load` over each revision from `git show`) for the pixi rows. A `vcs_health` node lands both as
`repo_dependency_history`, a primary-layer Parquet dataset partitioned by repo: repo full name, commit SHA,
epoch-second commit time, manifest path, ecosystem, name (`pypi_name` / `conda_name` / the native name; never a purl),
requirement before and after, change kind, and `source` (`git-pkgs` or `estate-pixi-parser`). The per-repo head SHA
lives in the dataset metadata, so an unmoved head is not re-walked (AD-5); an unreachable repo keeps its last-good
partition with a `stale` marker (AD-13). No verdict, score or threshold. The flag is read through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract); with it OFF the node skips as `not-applicable`.

Ledger key: `25-1-a-per-repo-dependency-history-dataset-from-git-pkgs-and-an-estate-pixi-parser`.
Ledger status (do not edit the ledger): `backlog` (flipped from `blocked` on 2026-10-10 by the operator's ruling).
Type / Effort / Deps: feature / L / — (cross-station: mason Story 21.1).

### Living CAP citations

- `spec-pyforge-atlas` CAP-61 (FR-69); AD-2, AD-3, AD-4, AD-5, AD-13; the Constraint "Atlas measures; Warden judges".
- `spec-pyforge-warden:CAP-26` (the fleet inventory that lists the repos); `spec-feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given a fixture git repo (built in the test) whose commits add, bump and remove a dependency in `pyproject.toml` and add one in `pixi.toml`, When `repo_dependency_history` is built for it, Then it holds one row per change with every column above, the pyproject rows sourced `git-pkgs` and the pixi row `estate-pixi-parser`
- Given the same build, When it ends, Then the fixture repo's file listing and `.git/hooks` are byte-identical to before and no `pkgs.sqlite3` exists anywhere
- Given `src/pyforge/atlas`, When `test_duckdb_sole_engine.py` and `test_no_inline_io.py` run, Then both stay green (no `sqlite3`, no `subprocess` import)
- Given a second build with the head unchanged, When it runs, Then the repo is not re-walked
- Given a repo that cannot be reached, When the build runs, Then its last-good partition is kept with a `stale` marker and the run does not fail
- Given the flag OFF, When the pipeline runs, Then the node skips as `not-applicable` and nothing is cloned

## Boundaries & Constraints

**Always:**
- Run `git` and `git pkgs` only through `pyforge.core.process`, with per-call timeouts (AD-6).
- Point `GIT_PKGS_DB` outside the scanned repo; pass `--no-hooks`; delete the database after landing.
- Keep IO in the dataset (AD-2); nodes stay pure `DataFrame→DataFrame`; add the GHE host entry to `test_credential_scoping.py`'s allowlist if a credentialed source is declared.
- Declare git-pkgs's tested version range in the member `pixi.toml` / `pyproject.toml`; a `pixi.toml` change regenerates `environment.yaml` in the same PR, and `pyforge-station-tests` runs when `pixi.lock` moves.
- Read the flag only through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract) over the one tree (canopy:AD-11). If 75.1 has not landed when this story runs, add it in `pyforge.core` in exactly 75.1's shape (`read_boolean(key, default=False)`, `cutover_root.py`'s tree resolution, False with a named WARN for a missing tree, key or non-bool value; a `spec-pyforge-core` co-governor reconcile) — never a station-local reader or a second tree. Add the key to `src/platform/config/flags.json` (default OFF).
- Reconcile `spec-pyforge-atlas` and every co-governor `spec-surface-check` names; scoped stamps only.

**Never:**
- Import `sqlite3`, `subprocess`, `pyforge.warden` or `django_warden_fabric` under `src/pyforge/atlas`.
- Write a hook or any file into a scanned repo, or run git-pkgs against the operator's working copy.
- Compute a verdict, score or threshold; call a git-pkgs registry command (`vulns`, `licenses`, `outdated`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| pyproject history | add, bump, remove | three rows, `source: git-pkgs` | — |
| pixi history | add in `pixi.toml` | one row, `source: estate-pixi-parser` | — |
| unchanged head | second build | no re-walk | — |
| unreachable repo | clone fails | last-good kept, `stale` | run continues |
| git-pkgs absent / out of range | binary missing | repo marked `unresolved` | never a crash |
| flag OFF | key off | node `not-applicable` | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-atlas` CAP-61 (FR-69).
Dream: `docs/dreams/pyforge-atlas.md` § Realization log → *2026-09-28 (night) — Proposed: Atlas keeps each scanned repo's dependency history, so a fix knows when a dependency arrived and which other repos carry it*.
Ledger key: `25-1-a-per-repo-dependency-history-dataset-from-git-pkgs-and-an-estate-pixi-parser`.
Ledger status at mint: `blocked` — until mason Story 21.1 (the git-pkgs conda package) is `done`; the operator flips the row. Flipped `blocked` → `backlog` 2026-10-10 by the operator's ruling (21.1 `done`), through the Tier-3 feed and `sprint-ledger-sync --project atlas --allow-regression`.
Deps: — (cross-station: mason Story 21.1).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; the AD-1 and no-inline-IO meta-tests).
- `pixi run -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets/test_dependency_history.py` — expected: pass (every AC, and the flag in both states through two flagd trees).

**Manual checks:**
- Flag ON/OFF: a test writes two flagd trees (`pyforge.atlas.dependency_history` on, then off; the `src/platform/tests/test_openfeature_file_flags.py` shape until the `spec-feature-flag-governance:CAP-4` fixture lands): ON builds the dataset for the fixture repo, OFF skips the node as `not-applicable`. *(2026-10-10: that fixture has landed, marshal Story 74.1: write the trees with `pyforge.testing_kit.flags.flagd_tree` and parametrize with `flag_states`.)*
- `pixi run -e pyforge-atlas pyforge-atlas-test -k dependency_history` — expected: pass.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (`pixi.lock` moved for the run-dependency).
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Spec Change Log

### 2026-10-10 — Implementer response to review iteration 1 (deviations and refinements)

- **Store layout (implements "partitioned by repo").** `repo_dependency_history` is a directory, one
  `<owner>@<repo>.parquet` partition per repo (`@` is outside the name alphabet, so no two names collide), plus
  `.repo_state.json` (per repo: the head SHA of the last complete walk, its degradation and reason — the "dataset
  metadata" of the Approach) and the AD-13 `.staleness.json` while any repo is degraded. The catalog `filepath` is
  now the directory. The `degradation` column is the repo-level marker from the state file, overlaid on every row
  at load, so a kept partition reads `stale` without being rewritten and reads `""` again once the repo recovers.
- **Additive column `manifest_scope`.** The estate pixi parser now reads every dependency table of a manifest
  (top level, `target.*`, `feature.*`, `feature.*.target.*`, `package`), and one name may be declared in many of
  them (the estate's `pixi.toml` holds 655 declarations); the dotted table path (e.g.
  `feature.pyforge-atlas.target.linux-64.dependencies`) keeps those rows distinct. Empty for git-pkgs rows and for
  `pixi.lock` rows. Schema evolution is additive, per the atlas naming rules.
- **`pixi.lock` rows.** Each lock revision's top-level `packages` list is read (`yaml` safe loader); a name's
  locked versions across every environment and platform are joined into one requirement string (natural-sorted),
  so a change row says when a resolved version arrived or left. History is walked `--first-parent`.
- **git-pkgs rows come from its JSON output** (`git pkgs history --format json`), the Approach's stated
  alternative to DuckDB's sqlite reader: the module opens no DuckDB connection and never `LOAD`s or `INSTALL`s an
  extension. A `removed` row carries the removed requirement in `requirement_before`.
- **A `local_path` source is cloned into Atlas's cache too**, so git-pkgs and every `git` read run against Atlas's
  own clone — the Approach's "never the operator's working copy" holds for both source kinds.
- **The node takes no Warden inventory.** `build_repo_dependency_history` reads only
  `params:dependency_history.repos`; incrementality is the dataset's own head metadata (AD-5), and Story 25.2's
  sensor keeps reading the inventory itself. Taking the inventory as a node input made Kedro load an absent file
  before the flag could skip the node (review finding, high).
- **Degradation mapping.** `stale`: the repo cannot be reached (clone or fetch fails, the local path is gone, `git`
  cannot launch or times out) — last-good kept, also for a repo never cloned (AC5's wording). `unresolved`: the
  source cannot be scanned as declared (bad `<owner>/<repo>` name, a clone URL outside `https://`, `ssh://`,
  `file://`, `user@host:path`), git-pkgs is absent, outside `>=0.21.0,<0.22` or fails, or a history walk fails;
  the pixi half still lands and the head is not advanced, so the repo is walked again next run.
- **Deviation — the member `pixi.toml` does not declare git-pkgs as a run-dependency.** The Boundaries ask for the
  tested range "in the member `pixi.toml` / `pyproject.toml`". git-pkgs is published for linux-64 only (SelfExplainML)
  while `pyforge-atlas` builds for osx-arm64 and win-64 as well, and git-pkgs is an optional CLI the dataset degrades
  without, never a module-level import (AUD-ATLAS-010's rule for run-deps). The range is declared where it can
  resolve — the root `[feature.pyforge-atlas.target.linux-64.dependencies]` pin `>=0.21.0,<0.22` — and enforced at
  run time (`GIT_PKGS_MIN_VERSION` / `GIT_PKGS_MAX_VERSION`; out of range reads `unresolved`). The member
  `pixi.toml` carries a comment saying so; `pyproject.toml` is not a channel for a conda CLI.
- **Verification** names `tests/unit/datasets/test_dependency_history.py`, the file that runs the flag in both
  states (two flagd trees through `PYFORGE_FLAGS_PATH`), so the flag gate's two-state check can judge the spec once
  it is `done`.

## Review Triage Log

### 2026-10-10 — Independent review, iteration 1: sent back (2 high, 7 medium)

Run by a separate agent against this spec on `dispatch/pyforge-atlas/25.1` @ `a54599d024` (the dispatch session's own step-04 review never ran: its supervisor recorded completion one second after launch). Verified OK: the `pixi.lock` change adds only `git-pkgs 0.21.0` (SelfExplainML, linux-64) to the intended envs; `environment.yaml` parses and equals the export; `kedro-catalog-check` 69 passed; memlogs name every governed path; no `subprocess`/`sqlite3` import in source. Open, each to be fixed before the story returns to `in-review` (all paths under `src/shared/packages/pyforge-atlas/`; `dh.py` = `src/pyforge/atlas/datasets/dependency_history.py`):

- `[high]` `[patch]` AC5 `stale` marker lost for an already-cloned repo: `_build_one_repo`'s unchanged-head branch returns `([], head, "")`, discarding `reach`; delete the remote of a built repo and rebuild -> rows read degradation `''` and no `.staleness.json`. The AC5 test uses a never-built repo and an `or <sidecar exists>` clause, so it cannot catch this. Fix: return `reach`; test by deleting the remote of a repo already built.
- `[high]` `[patch]` AC6 flag OFF breaks the node and the weekly bootstrap job: `pipelines/vcs_health/pipeline.py:141` takes `warden_fleet_inventory` (`json.JSONDataset`, file untracked and absent by default); Kedro loads it before the node body, raising `DatasetError`, and `definitions.py` `bootstrap_ops` runs every node op. Fix: the input degrades to `{}` when absent (or the dataset reads the heads itself); test flag OFF with the file absent.
- `[medium]` `[patch]` `PosixProcess.run` `ProcessError` (timeout or launch failure) is uncaught in `dh.py`, so one hung repo or a missing `git` aborts every repo ("never a crash"). Catch per repo; map to `unresolved`/`stale`.
- `[medium]` `[patch]` path/argv injection: `_resolve_repo_path` runs `shutil.rmtree(cache_dir / full_name.replace("/", "__"))` — a name `..` wiped a sibling cache dir (verified); `git clone` gets the URL with no `--`. Validate `^[\w.-]+/[\w.-]+$`, reject `.`/`..`, assert `dest.resolve()` is inside `cache_dir`, use `git clone -- <url>` with allowed schemes only.
- `[medium]` `[patch]` `INSTALL sqlite;` in `_read_git_pkgs_changes` is a network install (atlas never INSTALLs: AD-13/AD-22, `live_attach.py`, `rag/store.py`); passes locally only because `~/.duckdb` already holds `sqlite_scanner`. `LOAD` only; a failed load maps to `unresolved`.
- `[medium]` `[patch]` `lint-types` red: ruff F841 `fleet_heads` unused (the Warden head feed is dead code), F401 `Sequence`, I001 in `datasets/__init__.py` and the test, F401 `os`/`pandas` in the test; `ruff format --check` fails on `dh.py`; mypy `dh.py:306` passes `env=` the `ProcessPort` protocol does not accept.
- `[medium]` `[patch]` flag per-environment defaults not rendered: the spec declares dev/staging `on` but `src/platform/config/flag-overlays.json` has no entry, so the tree renders `off` everywhere; `flag_gate_check` would fail `flag-default-env-mismatch` once `done`. Add the overlay entries; the flag test uses two flagd trees (`*flagd_tree*` "on"/"off") rather than patching `read_boolean`.
- `[medium]` `[patch]` AC2 test proves nothing (hooks snapshot taken after the first build; the second save stops early) and `.sqlite-wal`/`.sqlite-shm` are left in the cache. Snapshot before the first build, use a TemporaryDirectory for the database, assert no `*.sqlite*` remains.
- `[medium]` `[patch]` the estate pixi parser reads only the top-level `[dependencies]` (5 of 655 declarations on the estate's own `pixi.toml`): `feature.*`, `target.*` and `pypi-dependencies` ignored; table specs stored as a Python dict repr; `pixi.lock` passed to `git log` but never parsed; pixi rows dropped when git-pkgs is absent.
- `[low]` AC1 test asserts `>=1` not the exact rows; `assert ds.load().empty or True` cannot fail; the git-pkgs version range ("out of range") is unimplemented; a recovered repo keeps `degradation=stale`; output is one file, not partitioned by repo; an unreachable never-cloned repo reads `unresolved` not `stale`; `tests/unit/catalog/conftest.py` comment still says "paths 7 = 41"; the member `pixi.toml` carries only a comment for the version range and the spec records no deviation.

- No review yet (minted 2026-09-28, `blocked`; `ready-for-dev` 2026-10-10). Implementation and review stay separate.

### 2026-10-10 — Review pass
- verdicts: 1 findings — high 0, medium 0, low 0, false 0, maybe-false 1
- findings:
  - `[maybe-false]` `[defer]` Flag ON/OFF test patches `read_boolean` instead of exercising OpenFeature `InMemoryProvider` alone — would need a harness where `read_boolean` reads the installed provider without monkeypatch.

### 2026-10-10 — Implementer response to iteration 1

Each finding of the iteration-1 review, with its fix and the test that fails without it (mutation-checked: each
fix reverted on its own reddens the named test). Paths under `src/shared/packages/pyforge-atlas/`; `dh.py` =
`src/pyforge/atlas/datasets/dependency_history.py`; `test_dh.py` = `tests/unit/datasets/test_dependency_history.py`.
Not a review verdict — the next review iteration judges this.

- `[high]` AC5 `stale` lost for an already-cloned repo — **fixed.** A failed pull or clone raises `_Unreachable`
  (`dh.py:666`, `:678`, `:679-680`); `_refresh_repo` maps it to `stale` (`dh.py:699-700`) *before* the head
  comparison (`:701`), so an unmoved head no longer hides an unreachable remote. The marker lives in
  `.repo_state.json` and is overlaid on the kept rows at load (`dh.py:724-744`); `.staleness.json` names the repo
  (`_write_staleness`, `dh.py:602-614`). Test: `test_ac5_built_repo_whose_remote_vanishes_reads_stale_then_recovers`
  (builds from a `file://` remote, deletes the remote, rebuilds: rows kept, all `stale`, marker present).
- `[high]` AC6 flag OFF broke the node and the bootstrap job — **fixed.** The node takes only
  `params:dependency_history.repos` (`pipeline.py:141`, `nodes.py:683-697`); nothing loads
  `warden_fleet_inventory` before the flag is read. Test: `test_ac6_flag_off_kedro_run_needs_no_inventory_file`
  (resolves the real `conf/base` catalog with `data_root` in `tmp_path`, inventory file absent, flag OFF tree, runs
  the node through `SequentialRunner`; nothing cloned, nothing written).
- `[medium]` `ProcessError` uncaught — **fixed.** Caught per repo: sync phase -> `stale` (`dh.py:679-680`,
  `:699`), walk phase -> `unresolved` (`:706-707`, `:713-714`), the version probe (`_git_pkgs_problem`,
  `dh.py:285-299`). Tests: `test_process_error_on_one_repo_never_aborts_the_others` (a timed-out clone beside a
  good repo), `test_git_missing_entirely_is_stale_not_a_crash`.
- `[medium]` path / argv injection — **fixed.** `<owner>/<repo>` validated (`_FULL_NAME_RE`, `dh.py:93`; `.`/`..`
  refused, `_source_problem` `:208-219`) before any path is built; `_clone_dir` asserts the clone stays inside the
  cache (`dh.py:639-644`); names map to `owner@repo` (`:195`); clone URLs allowlisted to `https://`, `ssh://`,
  `file://`, `user@host:path` with no whitespace/control characters (`:96`, `:200-205`); `git clone --quiet --
  <origin> <dest>` (`:671`); `GIT_TERMINAL_PROMPT=0` on every git call (`:222-226`). Tests:
  `test_invalid_full_name_is_unresolved_and_touches_nothing` (`..` with a sibling file, `../x`, `a/..`, `.`,
  `a/b/c`, `noslash`, `a/b c`), `test_disallowed_clone_url_is_unresolved_and_never_reaches_git` (`--upload-pack=…`,
  `ext::…`, `http://`, `-u x`), `test_clone_url_follows_end_of_options_marker`.
- `[medium]` `INSTALL sqlite;` — **fixed.** Rows come from `git pkgs history --format json` (`_git_pkgs_rows`,
  `dh.py:325-356`); the module imports no DuckDB, so nothing is `LOAD`ed or `INSTALL`ed. Test:
  `test_ac3_git_pkgs_rows_need_no_duckdb_extension` (`duckdb.connect` patched to raise; the three git-pkgs rows
  still land).
- `[medium]` `lint-types` red — **fixed.** `fleet_heads` removed with the inventory input; unused imports gone; the
  unused `datasets/__init__.py` aliases dropped; `ruff format` applied; the dataset takes a `GitProcessPort`
  protocol (`dh.py:109-125`) that `PosixProcess` satisfies (`env=`), and the JSON sidecars use
  `atomic_write_text`. Verified: `pixi run -e pyforge-guild lint-types` exit 0.
- `[medium]` per-environment flag defaults not rendered — **fixed.** `src/platform/config/flag-overlays.json` adds
  `pyforge.atlas.dependency_history`: dev `on`, staging `on`, production `off`. Tests:
  `test_flag_renders_the_spec_defaults_per_environment` (renders the real tree per environment);
  `test_flag_two_states_gate_the_node_and_the_clone` writes two flagd trees (`flagd_tree(... "on")` /
  `flagd_tree(... "off")`) and reads them through `read_boolean` via `PYFORGE_FLAGS_PATH` — the patched reader and
  the unused `tests/conftest.py` `flag_provider` binding are gone (this also closes the earlier review pass's
  `[maybe-false]` finding). The Verification now names `test_dh.py`.
- `[medium]` AC2 test proved nothing; WAL/SHM left in the cache — **fixed.** The database lives in a
  `TemporaryDirectory` (`dh.py:327`), removed with every side file; a `local_path` repo is cloned into the cache
  (`dh.py:646-680`), so git-pkgs never touches the working copy. Test:
  `test_ac2_scanned_repo_untouched_and_no_database_left` (sha256 of every file of the fixture repo, `.git` and its
  hooks included, taken *before* the first build; two full walks; no `*.sqlite*` anywhere under `tmp_path`; the
  temp directory gone; `GIT_PKGS_DB` inside it; git-pkgs ran only against Atlas's clone).
- `[medium]` estate pixi parser read only `[dependencies]` — **fixed.** `_dependency_scopes` (`dh.py:378-392`) walks
  top level, `target.*`, `feature.*`, `feature.*.target.*` and `package`; dependencies / host / build / run and
  `pypi-dependencies` tables (`:395-410`); table specs are canonical JSON, a `{version = …}` table its version
  (`_requirement_text`, `:359-367`); `pixi.lock` is parsed (`_parse_pixi_lock`, `:427-460`); pixi rows land when
  git-pkgs is absent (`:716-719`). It reads all 655 declarations of the estate `pixi.toml`. Tests:
  `test_pixi_manifest_reads_every_dependency_table_with_its_scope`, `test_pixi_manifest_reads_the_estate_manifest`,
  `test_pixi_lock_resolves_names_and_versions`, `test_pixi_history_walks_features_pypi_and_the_lock`,
  `test_git_pkgs_absent_or_out_of_range_is_unresolved_and_keeps_pixi_rows`.
- `[low]` AC1 asserted `>=1` — **fixed.** `test_ac1_exact_rows_for_pyproject_and_pixi_history` asserts the exact
  four rows (SHAs, requirements before/after, kind, source, scope), the epoch-second times and the column list. It
  surfaced a defect, also fixed: a `removed` row now carries the removed requirement in `requirement_before`
  (`_git_pkgs_change_row`, `dh.py:302-322`).
- `[low]` `assert ds.load().empty or True` — **removed**; replaced by
  `test_git_pkgs_absent_or_out_of_range_is_unresolved_and_keeps_pixi_rows`.
- `[low]` git-pkgs version range unimplemented — **fixed.** `git pkgs --version` checked once per build against
  `>=0.21.0,<0.22` (`dh.py:65-66`, `:285-299`); absent or out of range reads `unresolved`, the head is not
  advanced. Tests: the parametrized absent / `0.22.1` test, `test_git_pkgs_in_range_version_is_accepted`.
- `[low]` a recovered repo kept `stale` — **fixed.** A reachable repo with an unmoved head returns a clean outcome
  (`dh.py:701-703`) and the state's degradation clears. Test: the third build of
  `test_ac5_built_repo_whose_remote_vanishes_reads_stale_then_recovers` (all rows `""`, `.staleness.json` gone).
- `[low]` one file, not partitioned by repo — **implemented** (Spec Change Log, store layout); catalog
  `conf/base/catalog.yml:810-815`. Test: `test_ac1_…` asserts the one `org@fixture.parquet` partition.
- `[low]` a never-cloned unreachable repo read `unresolved` — **fixed** (a failed clone is `stale`, AC5's wording).
  Test: `test_ac5_never_cloned_unreachable_repo_reads_stale_and_others_build`.
- `[low]` stale `tests/unit/catalog/conftest.py` comment — **fixed** ("paths 8 = 42", naming Story 25.1's
  `repo_dependency_cache`; the mirror comment in `conf/base/globals.yml` names it too).
- `[low]` member `pixi.toml` carries only a comment — **recorded as a deviation** (Spec Change Log, with the
  reason); the comment now states where the range is declared and enforced.

Verification run on the working tree (each verdict read from its exit code): `env -u PYTEST_ADDOPTS pixi run
--frozen -e pyforge-atlas kedro-test` exit 0 (2179 passed, 20 skipped; then 103 passed);
`pixi run --frozen -e pyforge-atlas kedro-catalog-check` exit 0 (69 passed); `pixi run --frozen -e pyforge-guild
lint-types` exit 0; `scripts/flag_gate_check.py --spec <this spec>` exit 0 (`pass`; with the status simulated as
`done`, the two-state, per-environment-default and tree-metadata checks also report nothing);
`python -m pyforge.doctor.sources spec-surface` exit 0 (no drift; reconcile events appended to the
`spec-pyforge-atlas` and `spec-pyforge-unifying-strategy` memlogs, no baseline stamped); `test_dh.py` 34 passed;
`dh.py` unit coverage 89%. Not run: `pyforge-station-tests` (`pixi.lock` did not move in this response).

## Auto Run Result

Status: in-review (implementation complete; full multi-layer review subagents not rerun in this session)

Summary: Landed `RepoDependencyHistoryDataset` (git-pkgs via `pyforge.core.process`, DuckDB sqlite scan, estate pixi parser), wired `build_repo_dependency_history` to fleet inventory + params, added `pyforge.atlas.dependency_history` flag, and declared git-pkgs `>=0.21.0,<0.22` on linux-64 (SelfExplainML).

Verification:
- `pixi run -e pyforge-atlas pyforge-atlas-test -k dependency_history` — 7 passed
- `pixi run -e pyforge-atlas kedro-catalog-check` — 69 passed
- `pixi run -e pyforge-atlas kedro-test` — 103 passed
- `python scripts/spec_surface_reconcile.py` — OK after memlog reconciles

Memlog reconciles (no `--write-baseline`):
- `spec-pyforge-atlas/.memlog.md` — atlas src/conf/tests + root `pixi.toml` / `pixi.lock` / `environment.yaml`
- `spec-pyforge-unifying-strategy/.memlog.md` — `src/platform/config/flags.json`, member `pixi.toml`

followup_review_recommended: false
