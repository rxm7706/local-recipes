---
title: "25.1: A per-repo dependency-history dataset from git-pkgs and an estate pixi parser"
type: 'feature'
created: '2026-09-28'
status: 'ready-for-dev'
review_loop_iteration: 0
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

**Manual checks:**
- Flag ON/OFF: a test writes two flagd trees (`pyforge.atlas.dependency_history` on, then off; the `src/platform/tests/test_openfeature_file_flags.py` shape until the `spec-feature-flag-governance:CAP-4` fixture lands): ON builds the dataset for the fixture repo, OFF skips the node as `not-applicable`. *(2026-10-10: that fixture has landed, marshal Story 74.1: write the trees with `pyforge.testing_kit.flags.flagd_tree` and parametrize with `flag_states`.)*
- `pixi run -e pyforge-atlas pyforge-atlas-test -k dependency_history` — expected: pass.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (`pixi.lock` moved for the run-dependency).
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Review Triage Log

- No review yet (minted 2026-09-28, `blocked`; `ready-for-dev` 2026-10-10). Implementation and review stay separate.
