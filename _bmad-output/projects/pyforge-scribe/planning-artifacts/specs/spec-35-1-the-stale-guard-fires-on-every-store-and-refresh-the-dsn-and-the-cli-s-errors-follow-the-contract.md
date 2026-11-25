---
title: "35.1: The stale guard fires on every store, and refresh, the DSN and the CLI's errors follow the contract"
type: 'fix'
created: '2026-11-25'
status: 'done'
difficulty: 'medium'
story: 35-1-the-stale-guard-fires-on-every-store-and-refresh-the-dsn-and-the-cli-s-errors-follow-the-contract
spec: spec-pyforge-scribe
surface:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plane.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_compile.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_recall.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_recall_semantic.py
  - src/shared/packages/pyforge-scribe/tests/unit/conftest.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_cli.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_pg.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plane.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_extras_cocoindex_flow.py
  - src/shared/packages/pyforge-scribe/tests/meta/test_live_tree_split.py
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/contract.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-35-1-the-stale-guard-fires-on-every-store-and-refresh-the-dsn-and-the-cli-s-errors-follow-the-contract.md
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-scribe.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Row DW-scribe-review-2026-11-24-1 carries four reviewer-reported defects, none re-traced by the session that wrote it. (1) `compile_graph` sets `compiled_at` only when the store has that attribute (`compile.py:241-242`), and `PostgresGraphStore` and `PlaneGraphStore` have none, so `_withheld_as_stale` (`recall.py:299-302`) never withholds a node whose source was committed after the compile on the backends that serve `--semantic`. (2) `scribe index refresh` fingerprints `DEFAULT_GRAPHIFY_TARGET` alone (`cli.py:537,556-559`) while the ingest walks the three targets of `DEFAULT_GRAPHIFY_TARGETS`, so an edit under `src/platform/` or `scripts/` reads unchanged. (3) `_normalize_dsn` (`graph_store_pg.py:62-63`) cuts the DSN at its `?` and drops `sslmode`. (4) `capture` catches only `ValueError` (`cli.py:170-174`), so the capture lock's `TimeoutError` leaves as a traceback, on the `--type`/`--text` path and on `--promote`; `recall`, `graph compile` and `index` do not catch the `PluginError` that `open_graph_store` raises; and `graph compile`, `index build` and `index refresh` do not catch the `TimeoutError` of the flat-file store's commit lock.

**Approach:** Reproduce each defect with a failing test first. A defect the tree does not reproduce is recorded below as not a defect, with the command run and what it showed, and no code moves for it. Once reproduced: every shipped store keeps the compile time and returns it on reload (defect 1, below); a refresh with no `--target` fingerprints every target of `DEFAULT_GRAPHIFY_TARGETS` that exists; the DSN keeps its query string; a lock timeout and a plugin error end as one line on stderr with exit 2, the could-not-run code `contract.md` already lists.

Defect 1 is fixed (operator ruling of 2026-11-25, in session: "amend the scribe Spec too and restore that fix"). It was first left open, because `spec-pyforge-scribe` CAP-26 listed "PostgreSQL / plane `compiled_at` columns" as a non-goal; the ruling lifts that through a memlog correction and a re-derive of the Spec in this change, and CAP-26 as amended says every shipped store keeps the compile time in the schema it already has. The flat file keeps its `compiled_at` document key, unchanged. `PostgresGraphStore` and `PlaneGraphStore` each gain a `compiled_at` attribute, cleared by `reset()`, written by `commit()` and read by `_load()` as one reserved row of the node relation the store already has (`scribe_schema.graph_nodes`, `scribe_nodes`): id `scribe:compiled_at` (`models.COMPILED_AT_ROW_ID`), the stamp in `valid_from`. DML only: no column, no second relation, no changeset, no GraphStore Protocol method. The row is never a node: `_load` lifts it out, `upsert_node` refuses a node under that id, it has no embedding, an ended validity and `stale` set, and PostgreSQL's `query_similar` excludes the id. `compile.py` and `recall.py` change no code: `compile_graph`'s `hasattr(store, "compiled_at")` and recall's `getattr(store, "compiled_at", None)` now find the stamp, and a store with none still degrades to the stored `stale` bit. The comparison itself (a commit's authored date against `compiled_at`) is not changed by this story.

Ledger key: `35-1-the-stale-guard-fires-on-every-store-and-refresh-the-dsn-and-the-cli-s-errors-follow-the-contract`.

### Living CAP citations

- spec-pyforge-scribe CAP-26: amended 2026-11-25 (memlog correction and re-derive of that date, operator ruling), keeping its id, order and marker: every shipped store (flat file, PostgreSQL, plane) keeps the compile time in the schema it already has; the non-goal now names a dedicated column or a schema change. Defect 1 is realized against the amended text.
- spec-pyforge-scribe CAP-33 and CAP-9 (the refresh fingerprints the targets the ingest walks), CAP-3 (the shared store on `SCRIBE_GRAPH_DSN`) and CAP-4 (the exit codes of `contract.md`): realized, no text change. No AD moves.

## Boundaries & Constraints

**Always:**
- Write the failing test before the fix, one per defect, and keep it as the regression test.
- Keep the PostgreSQL store DML-only.
- Keep a store with no stamp degrading to the stored `stale` bit, as CAP-26 states.
- Keep the compile time in the form each store already has: the flat file's `compiled_at` document key, and one reserved row (`models.COMPILED_AT_ROW_ID`) of the node relation on the PostgreSQL and the plane store.
- Keep the reserved row out of every read: no scan, citation lookup, similarity query, compile count or recall answer returns it, and no store accepts a node under its id.
- Keep the staleness comparison as it is (a commit's authored date against `compiled_at`).

**Never:**
- Never issue DDL from the PostgreSQL store.
- Never add a relation, a column, a changeset or a runtime DDL statement for `compiled_at`, on any store.
- Never add a GraphStore Protocol method, a flag, or an exit code that `contract.md` does not list.
- Never hand-edit `SPEC.md`; never fix a defect the tree did not reproduce.

## Acceptance Criteria

**Given** `compile_graph` stamps `compiled_at` only on a store that has the attribute and `PostgresGraphStore` and `PlaneGraphStore` have none, `index refresh` fingerprints `DEFAULT_GRAPHIFY_TARGET` alone while the ingest walks `DEFAULT_GRAPHIFY_TARGETS`, `_normalize_dsn` cuts the DSN at its `?`, and `capture`, `recall`, `graph compile` and `index` catch neither a lock's `TimeoutError` (the capture lock, the flat-file store's commit lock) nor a `PluginError` from `open_graph_store`
**When** each of the four defects is first reproduced by a failing test, then the PostgreSQL and the plane store keep the compile time as one reserved row of the node relation they already have, a refresh with no `--target` fingerprints every target of `DEFAULT_GRAPHIFY_TARGETS` that exists, the DSN keeps its query string, and the lock and plugin errors end as one line on stderr with exit 2, a code `contract.md` already lists
**Then** a store reloaded after a compile still knows `compiled_at` and recall withholds a node whose source was committed after it, lexical and semantic, on the flat file, PostgreSQL and the plane, an edit under `src/platform/` or `scripts/` recomputes `graphify-ingest`, a DSN with `?sslmode=require` reaches `psycopg.connect` with it, and no lock or plugin error prints a traceback, on `capture` (`--type`/`--text` and `--promote`), `recall`, `graph compile`, `index build` and both modes of `index refresh`
**And** the reserved row is never a graph node (no scan, citation lookup, similarity query, compile count or recall answer returns it) and no relation, column or changeset is added for it; a defect the tree does not reproduce is recorded in the story spec as not a defect, with the command run and what it showed, and no code moves for it; the PostgreSQL store issues no DDL; both halves of scribe's suite pass

The PostgreSQL tests need the server: `pixi run --frozen -e pyforge-scribe-pg scribe-pg-up` first. Each command is read from its exit code; a `-k` that selects no test exits 5 and fails the criterion. A defect recorded under *Reproduction record* as not a defect drops its criterion, and the record says so.

- **AC1 — Every shipped store keeps the compile time, and recall's guard fires on each** (defect 1; CAP-26 as amended 2026-11-25). The first command needs no server (the PostgreSQL and the plane store run on in-memory stand-ins for their driver); the second needs PostgreSQL; the third shows no changeset moved. Expected: exit 0, exit 0, exit 0.

  ```bash
  PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_recall.py -k "every_store or relational_store" -q
  ```

  ```bash
  PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_pg.py src/shared/packages/pyforge-scribe/tests/unit/test_recall_semantic.py -k compiled_at -q
  ```

  ```bash
  git diff --quiet origin/main -- src/platform/db/changelog src/platform/db/sqlmigrate-map.yaml
  ```

- **AC2 — A refresh fingerprints every graphify target** (defect 2). Expected: exit 0.

  ```bash
  PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_cli.py src/shared/packages/pyforge-scribe/tests/unit/test_extras_cocoindex_flow.py -k "refresh and every_graphify_target" -q
  ```

- **AC3 — The DSN keeps its query string** (defect 3). Expected: exit 0.

  ```bash
  PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_pg.py -k dsn_keeps_query -q
  ```

- **AC4 — A lock timeout and a plugin error exit 2 without a traceback** (defect 4: the capture lock on `--type`/`--text` and `--promote`, the graph-store lock on `graph compile`, `index build` and both `index refresh` modes, and the plugin error). Expected: exit 0.

  ```bash
  PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_cli.py -k "lock_timeout or plugin_error" -q
  ```

- **AC5 — The PostgreSQL store issues no DDL.** Expected: exit 1 (no match).

  ```bash
  git grep -nE "CREATE TABLE|ALTER TABLE" -- src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py
  ```

- **AC6 — The public contract still holds.** Expected: exit 0.

  ```bash
  PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_public_contract.py -q
  ```

- **AC7 — Both halves of the suite pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-scribe pyforge-scribe-test && pixi run --frozen -e pyforge-scribe pyforge-scribe-live-test
  ```

- **AC8 — Touched modules hold the coverage floor.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-scribe pyforge-scribe-coverage-gate
  ```

- **AC9 — Lint and types.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

</intent-contract>

## Reproduction record

One line per defect: the command run on the unchanged tree, its exit code, and `reproduced` or `not a defect`. Each command is `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest <file> -k <name> -q`.

- Defect 1 (the stale guard on the PostgreSQL and plane stores): reproduced. `test_recall.py -k "every_store or relational_store"` (no server) exited 1 against the unchanged stores: `AttributeError: 'PostgresGraphStore' object has no attribute 'compiled_at'`, the same for `PlaneGraphStore`, and `test_every_store_withholds_a_source_committed_after_compiled_at[postgres]` and `[plane]` served the node after the later commit (`assert True is False` on `grounded`). With PostgreSQL up, `test_graph_store_pg.py -k keeps_compiled_at` and `test_recall_semantic.py -k withholds_source_committed_after_compiled_at` exited 1 with the same `AttributeError`. (The first pass of this story reproduced it the same way on 2026-11-25, then removed its tests and store changes while CAP-26's non-goal stood; they are restored.)
- Defect 2 (the refresh's fingerprinted targets): reproduced. `test_cli.py -k "refresh and every_graphify_target"` exited 1: an edit under `src/platform` left `graphify-ingest` in the skipped half.
- Defect 3 (the DSN's query string): reproduced. `test_graph_store_pg.py -k dsn_keeps_query` exited 1: `store.dsn` ended at `/scribe_graph`, `?sslmode=require&connect_timeout=5` gone.
- Defect 4 (the lock and plugin errors): reproduced. `test_cli.py -k "lock_timeout or plugin_error"` exited 1: `CliRunner` returned exit code 1 with `result.exception` a `TimeoutError` (the capture lock on `--type`/`--text` and on `--promote`; the graph-store lock on `graph compile`, `index build` and both `index refresh` modes) or a `PluginError` (`recall`, `graph compile`, `index build`, both `index refresh` modes).

## Binding

- Capabilities: spec-pyforge-scribe CAP-33, CAP-9, CAP-3, CAP-4 (realized, no text change); CAP-26 (amended 2026-11-25 by a memlog correction and re-derive, operator ruling: every shipped store keeps the compile time in its existing schema); no AD moves.
- Dream: `docs/dreams/pyforge-scribe.md`, the 2026-11-25 entry (the stale guard fires on every store); operator rulings of 2026-11-25, the second in session: "amend the scribe Spec too and restore that fix".
- Deferred work: closes DW-scribe-review-2026-11-24-1, all four defects; defect 1 with the amendment of `spec-pyforge-scribe` CAP-26.
- Epic: Epic 35, minted with this story.
- Ledger key: `35-1-the-stale-guard-fires-on-every-store-and-refresh-the-dsn-and-the-cli-s-errors-follow-the-contract`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."35"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date; `ready-for-dev`.
- 2026-11-25: defect 1: left open - lifting CAP-26's non-goal ("PostgreSQL / plane `compiled_at` columns") needs a Spec re-derive, the operator's; reproduced first (`test_graph_store_pg.py -k keeps_compiled_at`, exit 1, `AttributeError: 'PostgresGraphStore' object has no attribute 'compiled_at'`), then every change made for it reverted, so both stores, `compile.py` and `test_recall_semantic.py` read as at main. (superseded the same day by the operator ruling 'amend the scribe Spec too and restore that fix'; see the last entry)
- 2026-11-25: defect 2: reproduced and fixed - `test_cli.py::test_index_refresh_fingerprints_every_graphify_target` (exit 1 on the unchanged tree: an edit under `src/platform` read unchanged).
- 2026-11-25: defect 3: reproduced and fixed - `test_graph_store_pg.py::test_postgres_dsn_keeps_query_string` (exit 1 on the unchanged tree: the DSN was cut at its `?`).
- 2026-11-25: defect 4: reproduced and fixed - `test_cli.py -k "lock_timeout or plugin_error"` (exit 1 on the unchanged tree: `TimeoutError` and `PluginError` left as tracebacks); the review added the `--promote` path and the graph-store lock on `graph compile`, `index build` and both `index refresh` sites, each red first; the exit-2 row of `contract.md` names the two could-not-run causes.
- 2026-11-25: also fixed in the surface - `test_graph_store_plane.py`'s two read-only plugin tests seed the plane file first (DuckDB refuses a read-only open of a missing file); assertions unchanged.
- 2026-11-25: the story is implemented and in review.
- 2026-11-25: defect 1: restored and fixed - `test_recall.py::test_every_store_keeps_compiled_at_across_commit_and_reload` and `::test_every_store_withholds_a_source_committed_after_compiled_at` (flat file, PostgreSQL and plane, no server; exit 1 against the unchanged stores: `AttributeError: 'PostgresGraphStore' object has no attribute 'compiled_at'`, the same for `PlaneGraphStore`, and a grounded answer served after the later commit), with `test_graph_store_pg.py::test_postgres_store_keeps_compiled_at_across_commit_and_reload` and `test_recall_semantic.py::test_postgres_recall_withholds_source_committed_after_compiled_at` against the server; the non-goal is lifted by the memlog correction and re-derive of 2026-11-25 (operator ruling). The stamp is one reserved row of the relation each store already has (`models.COMPILED_AT_ROW_ID`); no column, relation, changeset or runtime DDL; `models.py` joins the surface for the row's id and its docstring.
- 2026-11-25: defect 3: also closed on the `open_graph_store` path - `graph_store_plugins.py` cut the environment's DSN at its `?` before the PostgreSQL plugin read it, so `SCRIBE_GRAPH_DSN=...?sslmode=require` still connected without `sslmode` from the CLI; `test_graph_store_pg.py::test_open_graph_store_passes_the_dsn_query_string_to_the_driver` (exit 1 before the fix, on `SCRIBE_GRAPH_DSN` and on `DATABASE_URL`) and the DSN now passes through whole; `tests/unit/conftest.py::require_pg_dsn` cut it the same way and hands the store the whole DSN too; `graph_store_plugins.py`, `conftest.py` and `tests/meta/test_live_tree_split.py` (its closed list of skip sites gains the plane stamp test) join the surface. `test_graph_store_plane.py::test_compile_stamp_round_trips_against_live_duckdb` runs the plane store's stamp against real DuckDB (it skips where `duckdb` is absent, as that file's other DuckDB tests do).
- 2026-11-25: closed. PR #2385 merged as 080f89c4df (`Merge pyforge-steward/133-1 into main`) after its 51 CI checks passed and the full local `pr-preflight` exited 0 on 48 lanes; an independent reviewer read the diff against this spec before the merge, its findings were applied and re-reviewed.
