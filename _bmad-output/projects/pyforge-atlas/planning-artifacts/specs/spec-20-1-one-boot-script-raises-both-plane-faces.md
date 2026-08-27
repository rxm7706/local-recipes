---
title: 'Story 20.1: One boot script raises both plane faces (CAP-5)'
type: 'feature'
created: '2026-08-27'
status: 'ready'
updated: '2026-08-27'
baseline_revision: 'cc8b3b2b1c09d6e56a5aebf752e25f507c846571'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-1-read-only-live-attach.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** the CAP-19 engine's first slice (steward 34.1–34.5) shipped the in-process
DuckDB plane primitives — the single-writer `atlas.duckdb` discipline
(`duckdb_writer.py::connect_writer`/`connect_reader`), the read-only live Postgres attach
(`live_attach.py::attach_postgres_readonly`), and vector persistence (`query_plane_vectors.py`)
— but nothing raises them as a coherent, bootable "plane". There is also no HTTP/Arrow face:
`duckdb-server` (Mosaic's DuckDB server, already reciped at `recipes/duckdb-server`, version
0.30.0) is confirmed absent from every `pixi.toml` today (`stack.md:43`: "Not in `pixi.toml`
until `query-plane-face` is answered"). Filesystem-less consumers (DB-GPT/Langflow estate
reads, live console queries) have no face to bind to at all.

**Approach:** the 2026-08-26 `query-plane-face` operator ruling answered this as "both, one
boot script": add ONE new pixi-sourced boot script/module in `pyforge-atlas` that (1) always
raises the in-process library face by opening `atlas.duckdb` through the existing
`connect_reader`/`connect_writer` seam (never a second writer, never a second `.duckdb` file),
and (2) launches the Mosaic `duckdb-server` HTTP/Arrow process from the SAME script, but only
when a platform-stack-up signal is present — degrading to library-face-only with a structured
notice (never a crash) when the stack is down. Add `duckdb-server` as a new
`[feature.pyforge-atlas.dependencies]` entry (it is not there today) and a new pixi task
exposing the boot script, mirroring the existing `kedro-test`/`duckdb-singularity` task shapes.
Prove there is exactly one launch site with a grep-verifiable gate, mirroring the F1
`tests/singularity/test_duckdb_sole_engine.py` AST-scan style.

## Acceptance Criteria

Lifted verbatim from `epics.md` (Story 20.1):

> **Given** the shipped CAP-19 engine (steward 34.1–34.5) **When** the single pixi-sourced boot
> script runs **Then** the in-process library face is available by default (AD-16 local-first;
> DuckDB stays a query face, never a fourth backing store) **And** the Mosaic `duckdb-server`
> HTTP/Arrow face is raised by the SAME script only when the platform stack is up — with the
> stack down it degrades to library-face-only with a structured notice, never a crash **And**
> no second boot path exists (grep-verifiable: exactly one `duckdb-server` launch site)
> (`query-plane-face` ruling, 2026-08-26).

## Boundaries & Constraints

**Always:** `BMAD_ACTIVE_PROJECT=pyforge-atlas` when resolving BMAD config; ledger key
`20-1-one-boot-script-raises-both-plane-faces`; the library face is available by default in
every environment (AD-16 local-first) — the HTTP/Arrow face is strictly additive, never a
replacement; reuse `duckdb_writer.py::connect_writer`/`connect_reader` verbatim for the library
face — never mint a second writable `.duckdb`; if the boot script needs to preflight an OLTP
attach, reuse `live_attach.py::attach_postgres_readonly`'s LOAD-only-never-INSTALL discipline
rather than inventing a second attach path; the boot script is the ONE and ONLY place that
launches `duckdb-server` — provable by grep/AST, mirroring
`tests/singularity/test_duckdb_sole_engine.py`'s `_sqlite_hits`-style scan.

**Block If:** raising the HTTP/Arrow face would require a network `INSTALL` of a DuckDB
extension at boot rather than `LOAD` from a pre-provisioned local cache (mirrors AD-13 /
`live_attach.py`'s existing LOAD-only discipline) — report and stop; this needs an operator
decision on extension provisioning, not a silent `INSTALL`.

**Never:** open a second writable `.duckdb` file; make `duckdb-server` a hard requirement (it
is optional, raised only when the platform stack is up); crash when the platform stack is down
(the contract is graceful degrade + a structured notice); implement the face-parity gate
(Story 20.2 — depends on this story); implement the dashboard-store pipeline (Story 20.3) or
the CIS spine specs (Story 20.4) here.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| STACK_DOWN | no platform-stack-up signal present | library face raised; structured "HTTP face not raised: stack down" notice | no exception, no crash |
| STACK_UP | platform-stack-up signal present, `duckdb-server` provisioned | both faces raised; boot returns handles/endpoints for each | no exception |
| MISSING_PROVISIONING | stack up but the `duckdb-server` binary or its extension cache is absent | boot fails loud with a typed error naming the missing provisioning step | never falls back to a silent network `INSTALL` |
| SECOND_BOOT_INVOCATION | boot script invoked a second time while the first still holds the writer lock | second invocation's library-face open is refused | `SecondWriterRefused` (existing `duckdb_writer.py` behavior), not a new error type |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/duckdb_writer.py` — existing
  single-writer discipline (`connect_writer`, `connect_reader`, `LockedDuckDB`,
  `SecondWriterRefused`, `ATLAS_DUCKDB_NAME`) the boot script's library face MUST reuse
  verbatim; never re-implement.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/live_attach.py` — the existing
  LOAD-only-never-INSTALL pattern (`load_postgres_offline`, `attach_postgres_readonly`,
  `PostgresNotProvisionedError`, `_disable_extension_network`) to mirror for the new
  `duckdb-server` face's own "fail loud, never INSTALL" boot behavior.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/query_plane_vectors.py` —
  `open_plane_rag_store`/`extract_real_arrays_onto_plane`, existing plane-writer consumers the
  boot script's library face must stay compatible with (both open `atlas.duckdb` via
  `connect_writer`).
- `src/shared/packages/pyforge-atlas/tests/singularity/test_duckdb_sole_engine.py` — the
  AST/grep-gate STYLE precedent (`_sqlite_hits`, `test_no_sqlite_in_the_migrated_surface`) to
  mirror for a new sibling test (e.g. `test_one_duckdb_server_launch_site.py`, same
  `tests/singularity/` home) proving exactly one `duckdb-server` launch site exists.
- `recipes/duckdb-server/recipe.yaml` — the already-reciped conda-forge package
  (`duckdb-server` 0.30.0, "A DuckDB server for Mosaic") this story adds to
  `[feature.pyforge-atlas.dependencies]` in `pixi.toml` (~line 1938–1976). Confirmed absent from
  every `pixi.toml`/`pyproject.toml` in the repo today via grep.
- `pixi.toml` `[feature.pyforge-atlas.dependencies]` (~line 1938) and a new
  `[feature.pyforge-atlas.tasks.<name>]` block — mirror the existing task shape at
  `[feature.pyforge-atlas.tasks.kedro-test]` (~line 1978) / `[feature.pyforge-atlas.tasks.duckdb-singularity]`
  (~line 2006) for the new boot-script task.
- No existing boot-script module was found anywhere under
  `src/shared/packages/pyforge-atlas/src/pyforge/atlas/` (confirmed by exhaustive grep for
  `duckdb-server`/`duckdb_server`/`boot`/`serve` across the package) — this is genuinely NEW
  code, most naturally a new module (e.g. `pyforge/atlas/query_plane_boot.py`) alongside
  `duckdb_writer.py`/`live_attach.py`, plus a console-script or `python -m` entrypoint following
  the existing `__main__.py`'s `--version`-intercept-before-Kedro-import pattern if it needs to
  be Click/Kedro-routable.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md:43`
  — the `duckdb-server` stack-row entry ("Optional HTTP/Arrow face. Not in `pixi.toml` until
  `query-plane-face` is answered. Not a Helm backing store.") — now answered, this story acts on
  it.
