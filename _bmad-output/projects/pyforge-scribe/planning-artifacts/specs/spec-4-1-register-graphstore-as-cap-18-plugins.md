---
title: 'Register GraphStore as CAP-18 plugins (Story 4.1)'
type: 'feature'
created: '2026-08-24'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - src/shared/packages/pyforge-core/src/pyforge/core/hooks.py
  - src/shared/packages/pyforge-core/README.md
warnings: []
deferred: []
baseline_revision: 'e96b852227b36bb28cbc62cd44dd5071057081fe'
---

<intent-contract>

## Intent

**Problem:** Compile and recall still construct `FlatFileGraphStore` in-process. Swapping the recall store (steward S-28.1 PG driver) would fork those callers instead of loading a second plugin on the shared CAP-18 contract.

**Approach:** Publish a scribe-owned `HookSpec` on `pyforge.core.hooks`. Wrap today's `FlatFileGraphStore` as the default plugin. Reserve a second plugin slot for the durable PG driver without implementing PostgreSQL/pgvector. Resolve the store through the registry; keep `compile.py`/`recall.py` on the `GraphStore` protocol.

## Boundaries & Constraints

**Always:**
- Consume `pyforge.core.hooks` (`HookSpec`, `HookPlugin`, `PluginRegistry`, `ENTRY_POINT_GROUP`). Do not add `pluggy` or a station-local `pyforge.scribe.hooks` / `pyforge.scribe.plugins` entry-point group.
- Default backend remains `FlatFileGraphStore` (injected `store_path`). Tests that pass `store=` keep working.
- `compile.py` and `recall.py` (and CLI recall) obtain a store via a factory that uses the protocol only — no engine client imports outside a concrete adapter.
- Recall / memory completeness is never published via `publish_verdict` as a PR quality-gate verdict. Warden owns PR-gate verdicts.
- Write specs under `_bmad-output/projects/pyforge-scribe/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-scribe` only — never `scripts/bmad-switch`.

**Block If:** none.

**Never:**
- Do not implement PostgreSQL, pgvector, SQL, or a SQLite-over-RWX driver (steward Epic 28 / CAP-14).
- Do not change GraphStore protocol methods or FlatFile persistence format.
- Do not make Scribe a Kedro project. Do not invent scorecard metrics. Do not drain other stories.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default plugin | Registry loads `pyforge.core.hooks`; no extra plugins | Factory returns a `FlatFileGraphStore` at the given path; compile/recall behave as today | No error |
| Reserved PG slot | Second plugin registered in-process with owner `steward` on the same spec name (test double, not PG) | Factory can select it; compile/recall still talk only to `GraphStore` | Unknown owner → `PluginError` |
| Injected store | `compile_graph(..., store=existing)` | Plugin path is not required; existing store is used | No error |
| Second verdict | Plugin calls `publish_verdict` for Warden's process / a spec it does not own | `SecondVerdictError` | Owner-matched publish of a non-gate payload is unused here |
| No competing gate | Factory / recall path | No `publish_verdict` of recall completeness as a PR gate | Asserted by test (no call / no Warden verdict) |
| Parallel group | `pyproject.toml` would declare `pyforge.scribe.hooks` | Forbidden — only `pyforge.core.hooks` | Core conformance already fails this |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/hooks.py` — **read-only**. `HookSpec`, `PluginRegistry.register`/`load_entry_points`/`invoke(..., spec_name=)`, `publish_verdict`/`SecondVerdictError`, `ENTRY_POINT_GROUP = "pyforge.core.hooks"`. `invoke` filters by `spec_name` only (all matching plugins run).
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py` — keep `GraphStore` + `FlatFileGraphStore`. Add plugin wrapper + constants: `GRAPHSTORE_HOOK_SPEC = HookSpec(name="pyforge.scribe.graph_store", owner="scribe")`; `PG_GRAPHSTORE_OWNER = "steward"` (reserved slot for S-28.1); `FlatFileGraphStorePlugin` with `hook_spec`/`owner="scribe"`; `call("around", context)` reads `context["store_path"]`, writes `context["store"]`.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py` — **new** factory `open_graph_store(store_path, *, registry=None, owner="scribe")`: `load_entry_points()` when no registry is passed; register `FlatFileGraphStorePlugin` only if no matching scribe-owner plugin is present; select by `owner` and call that plugin's `around` (do not `invoke` the whole spec). Never import psycopg/pgvector.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py:127-130` — when `store is None`, call `open_graph_store(store_path or default_store_path(repo_root))` instead of constructing `FlatFileGraphStore` here.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py:279` — `recall_cmd` uses `open_graph_store(default_store_path(repo_root))` instead of `FlatFileGraphStore(...)`.
- `src/shared/packages/pyforge-scribe/pyproject.toml` — `[project.entry-points."pyforge.core.hooks"]` `scribe-graphstore-flatfile = "pyforge.scribe.graph_store:FlatFileGraphStorePlugin"`. Do **not** declare a PG entry point (class does not exist).
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plugins.py` — **new**; covers every matrix row.
- Existing `tests/unit/test_graph_store.py`, compile/recall tests — **read-only unless** a constructor path breaks; keep injecting `store=` in compile tests.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py` -- add HookSpec constants + `FlatFileGraphStorePlugin` wrapping the existing adapter -- default CAP-18 plugin
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py` -- factory + reserved steward-owner slot (no PG impl) -- callers stay protocol-only
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` -- default store via factory -- no fork to swap backends
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` -- recall uses factory -- same default plugin
- `src/shared/packages/pyforge-scribe/pyproject.toml` -- declare flatfile on `pyforge.core.hooks` -- canonical group only
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plugins.py` -- unit-test the I/O matrix -- including fake second plugin, not Postgres

**Acceptance Criteria:**
- Given the existing GraphStore port, when this story completes, then today's flat-file backend is the default plugin on `pyforge.core.hooks`.
- Given a second in-process plugin registered for the reserved steward owner (stand-in for S-28.1), when the factory selects that owner, then compile/recall still use the GraphStore protocol and no PostgreSQL/pgvector code is added.
- Given recall completeness, when the factory or recall path runs, then it is not published as a PR quality-gate verdict.

## Design Notes

`invoke` runs every plugin with the same `spec_name`. The factory therefore **selects by `owner`** (default `scribe`; reserved `steward` for PG) and calls that plugin's `around` itself rather than invoking the whole set. S-28.1 later adds a real class and an entry point named e.g. `scribe-graphstore-pg`; this story only reserves the owner string and proves a second plugin can register without forking callers.

Do not wrap `FlatFileGraphStore` in a second persistence format. The plugin is a registration/lifecycle adapter around the existing class.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` -- expected: full suite green including new plugin tests
- `git diff --stat` -- expected: scribe package + this spec only; no steward Epic 28 / pgvector files

## Spec Change Log

- 2026-08-24 review: Code Map told the factory to `invoke(..., spec_name=)` which would run every plugin on the spec. Amended Code Map to match Design Notes (select by owner, call `around` on the selected plugin). Avoids re-deriving a factory that would construct both flat-file and a future PG store in one compile. KEEP: owner-based selection; no PG implementation.

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 3, low 3)
- defer: 0
- reject: 12
- addressed_findings:
  - `[medium]` `[patch]` spy that `compile_graph` without `store=` calls `open_graph_store`
  - `[medium]` `[patch]` spy that `recall_cmd` calls `open_graph_store`
  - `[medium]` `[patch]` register default FlatFile plugin only if no scribe-owner plugin is already present after entry-point load
  - `[low]` `[patch]` missing `store_path` in around context raises `PluginError`
  - `[low]` `[patch]` extend no-`publish_verdict` source scan to `compile.py` and `graph_store.py`
  - `[low]` `[patch]` Code Map no longer documents `invoke` for store resolution

## Auto Run Result

Status: done

Summary: Registered `FlatFileGraphStore` as the default CAP-18 plugin on `pyforge.core.hooks`. Compile and CLI recall open the store through `open_graph_store`. Reserved steward owner for S-28.1 with an in-process test double only — no PostgreSQL/pgvector.

Files changed:
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py` — HookSpec constants + `FlatFileGraphStorePlugin`
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py` — owner-selecting factory
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` — default store via factory
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — recall via factory
- `src/shared/packages/pyforge-scribe/pyproject.toml` — `scribe-graphstore-flatfile` on `pyforge.core.hooks`
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plugins.py` — I/O matrix + factory spies
- this spec

Review: 6 patches applied (3 medium, 3 low; follow-up score 12). 0 deferred. Rejected CLI owner flag, production PG stub, `recall.py` factory (library already takes `GraphStore`), README/epics.md drift, first-match races beyond register-if-missing, and `invoke` as the resolution API.

Verification: `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — 152 passed.

Residual: production compile/recall CLI always open owner `scribe`. Selecting steward remains a factory `owner=` / injected `store=` concern until S-28.1 ships a real plugin. `followup_review_recommended: true` (score 12).
