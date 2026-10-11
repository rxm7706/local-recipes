---
title: "25.1: A per-repo dependency-history dataset from git-pkgs and an estate pixi parser"
type: 'feature'
created: '2026-09-28'
status: 'in-review'
baseline_revision: f9c6a87dbe45d0e03d9a422dd708e466ce19bada
review_loop_iteration: 3
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

**Resolved later on 2026-10-10: the package now resolves** (Spec Change Log, iteration 2). When the gate cleared, the
second half of the condition above did not hold: `git-pkgs` was in no channel the workspace solves from
(`api.anaconda.org/package/SelfExplainML/git-pkgs` and `.../conda-forge/git-pkgs` both returned 404, and the workspace
channels are `["conda-forge", "SelfExplainML"]`, `pixi.toml:19`); mason 21.1 ends at a green local build in
`build_artifacts/`, and `pixi.toml` bans a local `file://` channel. Later the same day `git-pkgs 0.21.0` (build
`h1fb1ff7_0`, linux-64) was on the `SelfExplainML` channel: the root `[feature.pyforge-atlas.target.linux-64.dependencies]`
table declares `git-pkgs = ">=0.21.0,<0.22"` and `pixi.lock` pins
`https://conda.anaconda.org/SelfExplainML/linux-64/git-pkgs-0.21.0-h1fb1ff7_0.conda`. The dispatch added no channel,
vendored no binary and published nothing (publishing is an outward act the operator owns).

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

### 2026-10-10 — Implementer response to review iteration 2

- **Intent, git-pkgs resolution (dated 2026-10-10).** The Intent paragraph that said git-pkgs "does not resolve" is
  superseded: later the same day git-pkgs 0.21.0 resolved from `SelfExplainML` (linux-64), as the root pin and the
  `pixi.lock` URL record. The original condition is kept, in the past tense, for the history.
- **The clone follows its remote.** An existing clone is fetched (a failed fetch reads `stale`, the clone kept) and
  hard-reset to its upstream, so an amended or force-pushed upstream is followed instead of reading `stale` forever. A
  clone that is not a usable repository (a partial `.git` a killed run left) or cannot be reset is removed and cloned
  afresh; a clone attempt that fails in any way, a timeout included, leaves no directory behind.
- **One repo never fails the others.** Any exception while building one repo reads `unresolved` for that repo (its
  last-good partition kept, its head not advanced) and the build goes on; a `pixi.lock` whose `packages` is not a list
  is an unparsable revision, and git-pkgs JSON too deep to decode is a git-pkgs walk error (the pixi half still lands).
- **Repo-locating git variables are not inherited.** `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`,
  `GIT_OBJECT_DIRECTORY` and `GIT_ALTERNATE_OBJECT_DIRECTORIES` are dropped from every child environment.
- **scp-style clone URLs** must open user, host and path with a non-`-` character.
- **Pruning.** A repo dropped from a non-empty `dependency_history.repos` loses its state entry, its partition and
  Atlas's clone of it, so a dropped degraded repo no longer keeps `.staleness.json` alive. An empty list (the shipped
  offline default) scans nothing and prunes nothing, so an unconfigured run never wipes the history; turning the scan
  off is the flag's job.
- **Follow-up, not in this story (review `[note]`).** Story 25.2's fleet sensor re-runs this job over
  `params:dependency_history.repos` only, so its link to Warden's inventory (`spec-pyforge-warden:CAP-26`) is nominal:
  the moved repos it detects never reach the job, and a repo Warden inventories but the params do not list is never
  scanned. Recorded as `DW-atlas-25-1-1` (open, low) in `planning-artifacts/deferred-work-ledger.md`.

### 2026-10-10 — Implementer response to review iteration 3

- **A clone is never an enclosing repository.** The cache defaults to `data/` inside the operator's checkout, so a
  partial `.git` there let git discover the checkout. Every git call against a clone (and the clone and version
  probe run from the cache) now sets `GIT_CEILING_DIRECTORIES` to the parent of the directory it runs in, so
  discovery looks only at the clone; a clone is used only when `git rev-parse --show-toplevel` is the clone
  directory itself. Anything else is removed inside the cache and cloned afresh.
- **A changed source is followed.** Before fetching, the clone's `remote.origin.url` is compared with the declared
  `clone_url` (or the resolved `local_path`); on a mismatch the clone is replaced by a fresh clone of the declared
  source (re-cloning rather than `remote set-url`, so no object, branch or default-branch state of the old remote
  is carried over).
- **An empty repository is an explicit empty history.** A reachable repository with no commits (unborn `HEAD`)
  writes an empty partition, reads degradation `""` with the state reason "repository has no commits yet", and is
  only fetched on later runs (not re-cloned) until its first commits arrive.
- **The unchanged-head skip requires the partition.** A repo whose head has not moved is skipped only while its
  partition file exists; a deleted or damaged partition is rebuilt on the next run.
- **Malformed repo entries.** Each list entry that cannot be read as a repo source (not a mapping, no `full_name`,
  or a list that is not a list) is warned by index and counted on the request (`malformed_entries`); while any
  exists, nothing is pruned, so a mistyped entry never deletes a repo's state, last-good partition or clone.

## Review Triage Log

### 2026-10-10 — Independent review, iteration 3: sent back (1 high, 1 medium, 3 low)

Separate agent, on `74ded30ecc`. Every iteration-2 fix re-probed: nine hunk reverts each redden their named test. All seven gates exit 0 (kedro-test, kedro-catalog-check, lint-types, flag gate, spec-surface, deferred-work, pyforge-core-test). New findings (`dh.py` = `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/dependency_history.py`):

- `[high]` `[patch]` `dh.py:669-678`, `:709-716`: a partial `.git` in the clone cache makes git climb to the enclosing repository — `_clone_is_usable` only checks `dest/.git` is a directory and `rev-parse HEAD` succeeds, and `data_root` defaults to the relative `data` inside the operator's checkout. Probe: with the cache inside a repo tracking an upstream, the run discarded that repo's uncommitted edit, reset away its unpushed commit, then walked it and ran `git pkgs init` on it (breaks the Never rule on the operator's working copy), every run. New in iteration 2 (`reset --hard`). Fix: `_clone_is_usable` requires `git rev-parse --show-toplevel` (or `--absolute-git-dir`) to equal `dest`; set `GIT_CEILING_DIRECTORIES=<cache dir>` on every git call against a clone; test with the cache inside an enclosing git repo that has an uncommitted edit and an unpushed commit, asserting both survive.
- `[medium]` `[patch]` `dh.py:690-716`: a changed `clone_url`/`local_path` is never followed — the fetch uses the clone's stored `origin`. Verified: switching from a fork to the canonical remote kept reporting the fork's rows; after the old remote vanished the repo read `stale` forever. Fix: compare `remote.origin.url` with the declared origin before fetching; `remote set-url` or re-clone on mismatch; test it.
- `[low]` `[patch]` `dh.py:186-205`, `:845-849` (read): `_parse_repo_sources` silently drops a malformed entry and pruning then deletes that repo's state/partition/clone (even an unreachable repo's last-good partition). Warn per dropped entry; skip pruning when any entry was malformed.
- `[low]` `[patch]` `dh.py:768-770` (read): the unchanged-head skip trusts state without checking the partition exists, so a deleted/damaged partition is never rebuilt until the head moves (and a case-only rename on case-insensitive filesystems can leave it missing). Skip only when the partition file exists.
- `[low]` `[patch]` `dh.py:763-767` (read): a reachable empty repo (unborn HEAD) reads `stale` and re-clones every run; read it `unresolved` (or an explicit empty state) without re-cloning.

### 2026-10-10 — Independent review, iteration 2: sent back (2 medium, 5 low)

Separate agent, on `5d516fbf1e`. Every iteration-1 finding re-probed and fixed (reverted hunks redden the named tests); every recorded deviation judged justified, none drops an AC. Gates green: kedro-test, kedro-catalog-check, lint-types, flag gate (also with status simulated `done`), spec-surface; `environment.yaml` and `pixi.lock` correct. New findings (`dh.py` = `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/dependency_history.py`):

- `[medium]` `[patch]` `dh.py:658-667`, `:679-680`: a failed `git pull --ff-only` always maps to `stale` and the clone is never rebuilt — after an upstream `commit --amend` every later run reads `stale`; a clone killed by its timeout leaves a partial `.git` (the `ProcessError` path does no `rmtree`) and every later run reads `stale` with zero rows even once the network is back. Fix: `rmtree(dest)` on any clone exception; replace the pull with `git fetch` (failure -> `stale`) plus `git reset --hard` to the fetched head (or re-clone on a non-fast-forward).
- `[medium]` `[patch]` `dh.py:440` and the save loop `:762-764`: only `ProcessError`/walk errors are isolated per repo — a `pixi.lock` with `packages: 5` raises `TypeError` (surfaces as `DatasetError`) and deeply nested `git pkgs history` JSON raises `RecursionError`; either fails the whole node and saves no repo's state. Fix: validate `packages` is a list; catch `Exception` per repo -> `unresolved`.
- `[low]` `[patch]` `dh.py:222-226` `_git_env` passes `GIT_DIR`/`GIT_WORK_TREE` through (verified: a set `GIT_DIR` made the dataset fetch into another repo); strip `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES` there and in the test helper `_git`.
- `[low]` `[patch]` `dh.py:95` scp-style URL pattern accepts a leading `-` (git's own guard blocks it, but the repo reads `stale` not `unresolved`); require an alphanumeric first character.
- `[low]` `[patch]` `dh.py:602-614`, `:776` (read, not run): state entries never pruned — a repo dropped from params while degraded keeps `.staleness.json` alive and its partition keeps loading.
- `[low]` `[patch]` stale text: `tests/unit/parity/test_parity_complete.py:17` and `tests/unit/pipelines/test_dag_resolves.py:44` still say "25.1 placeholder"; the spec Intent still says git-pkgs "does not resolve" with no dated Change Log line; `test_pixi_manifest_reads_the_estate_manifest` ties a unit test to the root `pixi.toml` pin (read-only).
- `[low]` `[note]` Story 25.2's sensor now re-triggers a scan over `params:dependency_history.repos` (default `[]`), so the CAP-26 link is nominal — record a follow-up in the Spec Change Log / deferred work. `pyforge-station-tests` is required because `pixi.lock` moved and is not recorded as run.

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

### 2026-10-10 — Implementer response to iteration 2

Each finding of the iteration-2 review, with its fix and the test that fails without it (mutation-checked: each fix
reverted on its own reddens the named test). `dh.py` = `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/dependency_history.py`;
`test_dh.py` = `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_dependency_history.py`. Not a review verdict.

- `[medium]` a failed pull or a partial clone stayed `stale` forever — **fixed.** `_sync_clone` (`dh.py:680-737`) no
  longer pulls: a usable clone (`_clone_is_usable`, `dh.py:669-678`, `rev-parse --verify HEAD`) is fetched
  (`dh.py:702`; a failed fetch is `stale`, clone kept) and hard-reset to `@{upstream}` (`dh.py:710`), so a rewritten
  upstream is followed; a clone that is not usable or cannot be reset is removed and cloned afresh; a clone attempt that
  raises (a timeout) removes its directory (`dh.py:729-731`), as does a non-zero clone. Tests:
  `test_amended_upstream_is_followed_not_stale` (amend + force-push to the `file://` remote: `""`, new head, new rows),
  `test_timed_out_clone_leaves_nothing_and_the_next_run_builds`, `test_partial_clone_left_by_a_killed_run_is_cloned_afresh`.
- `[medium]` only `ProcessError` / walk errors were isolated per repo — **fixed.** The save loop catches any `Exception`
  per repo and records it `unresolved` (last-good partition kept, head not advanced) (`dh.py:829-838`); `pixi.lock`
  `packages` must be a list or the revision is unparsable (`dh.py:457-461`); git-pkgs JSON too deep to decode is a
  git-pkgs walk error, so that repo's pixi half still lands (`dh.py:365`). Tests:
  `test_any_error_in_one_repo_is_unresolved_and_never_fails_the_others` (a `KeyError` from one repo's manifest),
  `test_deeply_nested_git_pkgs_json_is_unresolved_for_that_repo_only` (200 000-deep JSON),
  `test_pixi_lock_resolves_names_and_versions` (`packages: 5` -> `None`).
- `[low]` `_git_env` passed `GIT_DIR` and its siblings through — **fixed.** `_GIT_REPO_ENV` (`dh.py:102-109`) is dropped
  from every child environment (`_git_env`, `dh.py:239-244`); the test helper `_git` and every test `subprocess` call
  use `_clean_env()` (`test_dh.py:92-100`). Test: `test_repo_locating_git_variables_are_not_inherited` (`GIT_DIR` /
  `GIT_WORK_TREE` point at a decoy repo across a clone and a fetch-and-reset build; the decoy is byte-identical and the
  rows are the fixture's).
- `[low]` scp URL accepted a leading `-` — **fixed.** User, host and path must open with a non-`-` character
  (`_SCP_URL_RE`, `dh.py:98`). Tests: `test_disallowed_clone_url_is_unresolved_and_never_reaches_git` gains
  `-x@host:org/r.git`, `git@-host:org/r.git`, `git@host:-org/r.git` (`unresolved`, no git call);
  `test_clone_url_follows_end_of_options_marker` gains a valid scp URL that reaches `git clone --`.
- `[low]` state never pruned — **fixed.** A repo dropped from a non-empty list loses its state entry, partition and clone
  (`_forget`, `dh.py:739-748`; `save`, `dh.py:845-849`); an empty list prunes nothing (Spec Change Log). Test:
  `test_repos_dropped_from_the_list_are_pruned` (`.staleness.json` gone, partition and clone removed, empty list a no-op).
- `[low]` stale text — **fixed.** `tests/unit/parity/test_parity_complete.py:17` and
  `tests/unit/pipelines/test_dag_resolves.py:44` no longer say "25.1 placeholder"; the Intent's git-pkgs paragraph is
  superseded with a dated line (Spec Change Log, iteration 2); `test_pixi_manifest_reads_the_estate_manifest` no longer
  pins the root `git-pkgs` range, it asserts table shapes only (`test_dh.py:497-505`).
- `[low]` `[note]` the 25.2 sensor's CAP-26 link is nominal — **recorded**: Spec Change Log (iteration 2) and
  `DW-atlas-25-1-1` (open, low) in `planning-artifacts/deferred-work-ledger.md` (the ledger's sub-row count prose moved
  178 -> 180, it was already one behind). `pyforge-station-tests` run below.
- **Found by `pyforge-station-tests` (not in the review), fixed.** Its first run exited 1 on three `pyforge-core` tests
  this story had redded: `test_no_unreparented_exception_root[…dependency_history.py]` (the module's exception roots
  lacked `PyforgeError`, spec-pyforge-core CAP-5 — now `class _InvalidSource(PyforgeError, Exception)` and its two
  siblings, `dh.py:170-181`), and `test_every_flag_in_the_shipped_tree_carries_the_five_string_fields` /
  `test_the_shipped_tree_reads_the_same_values_in_every_environment_as_before_the_metadata` (the new flag was undated —
  `src/shared/packages/pyforge-core/tests/unit/test_flags.py` now dates `pyforge.atlas.dependency_history` in
  `_SHIPPED_CLOCKS` and pins dev on / staging on / production off; reconcile event on the `spec-pyforge-core` memlog).

Verification on the working tree (each verdict from its exit code): `env -u PYTEST_ADDOPTS pixi run --frozen -e
pyforge-atlas kedro-test` exit 0 (2190 passed, 20 skipped; then 103 passed) — one of four runs exited 1 on
`tests/integration/publish/test_emit_range.py::test_count_star_reads_footer_only_over_range` (the range server
recorded no request), a file this story does not touch; it passed alone (12 passed) and on the rerun; `kedro-catalog-check` exit 0 (69
passed); `pixi run --frozen -e pyforge-guild lint-types` exit 0; `scripts/flag_gate_check.py --spec <this spec>` exit
0 (`pass`; with the status simulated `done` the two-state, per-environment-default and tree-metadata checks report
nothing); `python -m pyforge.doctor.sources spec-surface` exit 0 (reconcile events appended to the `spec-pyforge-atlas`
and `spec-pyforge-core` memlogs, no baseline stamped); `python -m pyforge.doctor.sources deferred-work` exit 0; `test_dh.py` 45 passed;
`env -u PYTEST_ADDOPTS pixi run --frozen -e pyforge-guild pyforge-station-tests` (`pixi.lock` moved in this story): first run exit 1 (the three `pyforge-core` failures above), after their fix exit 0 — core 2384 passed, testing kit 95, atlas 2190 + 103, doctor 3520 + 1, herald 1744, marshal 12203, mason 1622 + 12, scribe 428, steward 2297, warden 2266.

### 2026-10-10 — Implementer response to iteration 3

Each finding of the iteration-3 review, with its fix and the test that fails without it (mutation-checked: each
fix reverted reddens the named test). `dh.py` = `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/dependency_history.py`;
`test_dh.py` = `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_dependency_history.py`. Not a review verdict.

- `[high]` a partial `.git` in the cache made git climb to the enclosing checkout — **fixed, two independent guards.**
  (1) `_bounded_env` (`dh.py:262-270`) sets `GIT_CEILING_DIRECTORIES` to the parent of the directory a call runs in;
  every git call against a clone goes through `_git_in` (`dh.py:585-587`) or passes it directly (git-pkgs `:372`,
  the version probe `:332`, the clone `:762-767`). (2) `_clone_is_usable` (`dh.py:698-705`) requires `.git` to be a
  directory and `git rev-parse --show-toplevel` to resolve to exactly the clone directory; otherwise the directory
  is removed (inside the cache, `_clone_dir`) and cloned afresh (`dh.py:759-760`). Tests:
  `test_partial_clone_inside_an_enclosing_checkout_never_touches_it` (the cache inside an enclosing checkout that
  tracks an upstream, with an unpushed commit and an uncommitted edit, plus a partial `.git` in the clone slot; two
  builds: the checkout's `HEAD`, its one unpushed commit, the edited file's bytes and its tracked status are unchanged,
  `git pkgs init` ran only where `--show-toplevel` is Atlas's clone, and every `-C` call carried the ceiling — reverting
  both guards reddens it, and reverting the ceiling alone reddens its ceiling assertion);
  `test_a_clone_whose_top_level_is_elsewhere_is_cloned_afresh` (pins the top-level equality on its own).
- `[medium]` a changed `clone_url` / `local_path` was never followed — **fixed.** `remote.origin.url` is compared with
  the declared source before any fetch (`dh.py:742-749`); a mismatch re-clones. Test:
  `test_a_changed_origin_is_followed_fork_to_canonical` (fork rows gone after the switch, the canonical head
  recorded, and the fork remote's removal no longer reads `stale`).
- `[low]` malformed entries dropped silently, then pruned — **fixed.** `_parse_repo_sources` (`dh.py:192-220`) warns
  per dropped entry by index and counts it; the request carries `malformed_entries` (`dh.py:161`, `:921-922`); `save`
  prunes nothing while it is non-zero (`dh.py:889-900`). Tests: `test_malformed_entries_warn_and_are_counted`,
  `test_a_malformed_entry_prunes_nothing`.
- `[low]` the unchanged-head skip trusted state without the partition — **fixed** (`dh.py:810`). Test:
  `test_missing_partition_is_rebuilt_on_an_unchanged_head`.
- `[low]` an empty repository (unborn `HEAD`) read `stale` and re-cloned every run — **fixed.** `_repo_head`
  returns `""` for an unborn `HEAD` (`dh.py:590-598`), `_refresh_repo` records an explicit empty history
  (`dh.py:807-809`), and `_follow_upstream` keeps an empty clone of a still-empty remote instead of re-cloning
  (`dh.py:707-716`). Test: `test_an_empty_repository_is_an_empty_history_not_a_reclone` (one clone across three
  builds; `""` with "no commits"; its first pushed commits are then followed).

Verification on the working tree (each verdict from its exit code): `env -u PYTEST_ADDOPTS pixi run --frozen -e
pyforge-atlas kedro-test` exit 0 (2197 passed, 20 skipped; then 103 passed); `kedro-catalog-check` exit 0 (69
passed); `pixi run --frozen -e pyforge-guild lint-types` exit 0; `env -u PYTEST_ADDOPTS pixi run --frozen -e
pyforge-core pyforge-core-test` exit 0 (2384 passed, 1 skipped); `scripts/flag_gate_check.py --spec <this spec>` exit 0
(`pass`; with the status simulated `done` the two-state and per-environment-default checks report nothing);
`python -m pyforge.doctor.sources spec-surface` exit 0 (reconcile event appended to the `spec-pyforge-atlas` memlog,
no baseline stamped); `python -m pyforge.doctor.sources deferred-work` exit 0; `test_dh.py` 52 passed. Only atlas files changed in this
response (plus this spec and the `spec-pyforge-atlas` memlog), so `pyforge-station-tests` was not re-run.

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
