---
title: PostgreSQL driver behind the existing GraphStore port (Story 28.1)
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
context:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-4-1-register-graphstore-as-cap-18-plugins.md
warnings: []
deferred: []
baseline_revision: f68b595b31
review_loop_iteration: 1
followup_review_recommended: false
---

<intent-contract>

## Intent

**Problem:** Scribe's compiled graph is one JSON file (`FlatFileGraphStore`). The unifying-strategy Dream treated dual-driver Scribe as already shipped; ground truth is a single local adapter. Production cannot use that file as the durable backend (canopy:FR-35 / CAP-14).

**Approach:** Add the first durable driver — PostgreSQL with `pgvector` in `scribe_schema` — as a steward-owned plugin behind the existing `GraphStore` port. Keep the JSON local path. One operation suite must pass against both. Callers stay on the protocol.

## Boundaries & Constraints

**Always:**
- Existing `GraphStore` protocol methods stay unchanged. `compile.py` / `recall.py` / CLI obtain a store via `open_graph_store` or injected `store=`; they do not `isinstance` the driver.
- Durable adapter lives in `src/shared/packages/pyforge-scribe/` (`graph_store_pg.py`). Engine client imports (`psycopg`) stay inside that adapter module (parent AD-5). Factory (`graph_store_plugins.py`) still must not import `psycopg` / `pgvector` / `sqlite3`.
- Schema isolation: tables in `scribe_schema` only (parent AD-5). `CREATE EXTENSION vector` in the same PostgreSQL instance (parent AD-1 — not a fourth kind, not MinIO).
- Local path remains `FlatFileGraphStore` (owner `scribe`). Durable plugin owner is `steward` (`PG_GRAPHSTORE_OWNER`).
- Concurrent `commit()` calls serialize (transaction + advisory lock) so the durable table is never a torn mix of two writers.
- `BMAD_ACTIVE_PROJECT=pyforge-steward`. Write this spec at `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` literally.

**Block If:** none.

**Never:**
- Do not implement Story 28.2 semantic recall.
- Do not start 26-3/26-4 or any 27.x Liquibase/packaging story.
- Do not put `pyforge.*` under `src/platform/`.
- Do not add SQLite-over-RWX. Do not make JSON the durable production backend.
- Do not change GraphStore protocol methods or FlatFile persistence format.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dual suite | Same GraphStore ops (reset/upsert/invalidate/query/iter/commit/reopen) | Passes against FlatFile **and** PostgresGraphStore | PG missing vector/`scribe_schema` → fail, not skip-as-green |
| Callers unaware | `compile_graph` / `recall` / CLI | Talk only to `GraphStore` / `open_graph_store`; no driver branch | AST/source scan fails if `psycopg` or `PostgresGraphStore` imported outside the adapter |
| Concurrent writers | Two threads `commit()` the durable store | Each commit is a complete snapshot; reopen is valid JSON-free PG state | Torn rows / half-applied DELETE+INSERT fail the test |
| Durable is not JSON | PostgresGraphStore `commit()` | Does not write `graph.json`; nodes live in `scribe_schema` | Test fails if durable path is FlatFile-only or writes the JSON document |
| Steward plugin | `open_graph_store(..., owner="steward")` with DSN | Returns `PostgresGraphStore`, not `FlatFileGraphStore` | Missing DSN → `PluginError` |
| Default local | `open_graph_store(path)` | Still `FlatFileGraphStore` at that path | Unchanged |
| Isolation | After PG commit | `graph_nodes` relation exists only in `scribe_schema` (not `public` / `langflow_schema` / `dbgpt_schema`) | Cross-schema write fails the test |
| Host boundary | Implementation files | No new `pyforge.*` under `src/platform/` | Test fails if adapter is added there |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py` — **keep** `GraphStore` Protocol + `FlatFileGraphStore` + `FlatFileGraphStorePlugin`. `PG_GRAPHSTORE_OWNER = "steward"` already reserved. Do not import `psycopg` here (offline FlatFile / AD-6 tests).
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py` — **new** `PostgresGraphStore` + `PostgresGraphStorePlugin`. Lazy-import `psycopg` inside the adapter so entry-point class load does not require the extra. DDL: `CREATE EXTENSION vector`; `scribe_schema.graph_nodes` with nullable `embedding vector` (unused until 28.2). `commit()` = `pg_advisory_xact_lock` + replace-all in one transaction.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py` — still owner-selecting factory; still no engine imports. Default owner `scribe` unless `owner=` or `PYFORGE_GRAPHSTORE_OWNER`. Copy `SCRIBE_GRAPH_DSN` / `DATABASE_URL` (strip `?query`) into plugin context as `dsn`.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` / `cli.py` / `recall.py` — **read-only** unless a constructor path breaks. Keep protocol-only.
- `src/shared/packages/pyforge-scribe/pyproject.toml` — add `scribe-graphstore-pg = "pyforge.scribe.graph_store_pg:PostgresGraphStorePlugin"` on `pyforge.core.hooks`. Optional extra `postgres = ["psycopg>=3.3.4"]`.
- `pixi.toml` `[feature.pyforge-scribe.dependencies]` — `psycopg >=3.3.4` so `pyforge-scribe-test` can open the durable driver.
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store.py` — keep FlatFile-only JSON/offline tests.
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_operations.py` — **new** parametrized suite vs both drivers (matrix dual suite).
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_pg.py` — **new** concurrency, isolation, not-JSON, plugin+DSN, no `src/platform/` adapter, callers do not import engine.
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plugins.py` — expect the PG entry point; keep factory AST scan (no `psycopg` in factory).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py` — PostgreSQL/pgvector adapter + steward plugin — canopy:FR-35 durable driver
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py` — env owner + DSN context; no engine import — callers unaware
- `src/shared/packages/pyforge-scribe/pyproject.toml` — register `scribe-graphstore-pg` — CAP-18
- `pixi.toml` — `psycopg` on pyforge-scribe feature — tests can connect
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_operations.py` — same suite vs JSON and PG — canopy:FR-35
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_pg.py` — concurrency, isolation, anti-JSON, host boundary — canopy:FR-35 / parent AD-1 / AD-5
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plugins.py` — PG entry point present; factory still engine-free
- this spec — tracked under steward `planning-artifacts/specs/` — include in the implementation PR

**Acceptance Criteria:**
- Given the existing GraphStore port, when the suite runs, then it passes against both the durable driver and the local path.
- Given compile/recall/CLI, when a driver is selected, then callers do not branch on which driver is active.
- Given concurrent writers, when they commit the durable store, then they do not corrupt it.
- Given the durable path, when tests run, then they fail if the port is bypassed or the durable path is JSON-only.
- Given parent AD-1 / AD-5, when the adapter lands, then there is no `pyforge.*` under `src/platform/` and no MinIO/fourth-kind store.

## Design Notes

`reset()`/`upsert_node()` stay in-memory on both drivers; `commit()` persists a full snapshot. PostgreSQL matches FlatFile last-writer-wins: a transaction deletes all schema rows then inserts the snapshot under `pg_advisory_xact_lock`, so two racing commits never interleave rows.

DSN is not a second argument on `compile_graph`. Cluster sets `PYFORGE_GRAPHSTORE_OWNER=steward` and `SCRIBE_GRAPH_DSN`. Local default remains the JSON file.

DDL bootstrap in the adapter is allowed because Epic 27 Liquibase stories are operator-skipped; 28.2 owns filling `embedding`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Spec Change Log

Empty until the first bad_spec loopback.

## Review Triage Log

### 2026-08-25 — Review pass (same-session; subagent reviewers unavailable)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 4 (semantic recall 28.2; Liquibase 27.x DDL; SQLite dual-driver; MinIO/fourth kind)
- addressed_findings: []

## Auto Run Result

Status: done

Summary: First durable GraphStore driver is PostgreSQL/pgvector in `scribe_schema` behind the existing port. Local JSON path remains the default plugin. Same operation suite passes against both; callers stay protocol-only; concurrent commits serialize.

Verification: `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — 176 passed (SCRIBE_GRAPH_DSN to pgvector/pgvector:pg17 on :5433).
