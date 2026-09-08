---
title: Supervisor tables in public
type: feature
created: '2026-08-24'
status: done
updated: '2026-08-24'
baseline_revision: 4dc8d8abda7b57691e7311ceff571415dff8b3c3
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
warnings: []
deferred:
  - summary: >-
      Timing, heartbeat, and ingest-at-completion columns for canopy:FR-41/canopy:FR-42
      are not on RunState yet.
    evidence: |-
      Story 21.1 lands the two public tables only; 21.5 owns front-door
      query and completed-run timing ingest.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/models.py
    severity: low
  - summary: >-
      expires_at has no secondary index; TTL sweep belongs to start/get.
    evidence: |-
      AD-6 TTL is stored; 21.3 will look up and expire handles.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/models.py
    severity: low
  - summary: >-
      sqlmigrate / Liquibase extraction is Epic 27, not this migration.
    evidence: |-
      Intent forbids 27-1; AD-9 production DDL comes later.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/migrations/0001_supervisor_tables.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Handles and run rows have no durable home on the estate database. Front-door and MCP `get` cannot be replica-safe until `public.run_state` and `public.mcp_handles` exist, and scraping `~/.bmad-loops` is why the retired board showed `unavailable`.

**Approach:** Add Django models and migrations in `django-pyforge` that create those two tables in the default `public` schema. The store is the shared DATABASES default; any replica reading the same DB can answer `get`. No Liquibase, no MCP dual-era, no start/get tools in this story.

## Boundaries & Constraints

**Always:** Tables named `run_state` and `mcp_handles` (Meta.db_table), in `public` / the Django default schema — not new schemas. DDL is Django migrations owned by the `django_pyforge` app. `mcp_handles` rows are a capability to a supervisor `run_id` (FK). Host settings stay on existing `DATABASES["default"]`. Physical writes under `_bmad-output/projects/pyforge-steward/` plus `src/shared/packages/django-pyforge/` and platform tests. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Parent AD-2: no `pyforge.*` under `src/platform/`.

**Block If:** Creating the tables would require a fifth PostgreSQL schema, MinIO, or operator Liquibase 27-1.

**Never:** Story 21.2 Atlas MCP dual-era. Story 21.3 start/get tools or assertion-gated fetch. Story 21.5 front-door supervisor UI. Epic 27 Liquibase changesets / Helm migrate-job rewrite. Epic 30 console deletion. Redis-backed handles. `CREATE SCHEMA` for supervisor state. `import pyforge.*` under `src/platform/`. MinIO.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Tables in public | migrate applied on test DB | `run_state` and `mcp_handles` exist; db_table names match; no supervisor schema created | migrate failure fails the test |
| Handle points at run | insert RunState then McpHandle with FK | handle row stores run_id; reverse lookup from handle yields that run | IntegrityError if run missing |
| Replica get | insert via connection A; read handle/run via connection B (same DATABASES default) | same row visible; no read of laptop disk | missing row is DoesNotExist, not a filesystem fallback |
| No laptop scrape | AST/source of front_door + django_pyforge + MCP url modules | no `~/.bmad-loops`, tmux, or journal path reads | test fails on a matching literal or Path.home()/bmad-loops |
| Isolation preserved | supervisor migrations | no `CREATE SCHEMA` for run_state/mcp_handles; langflow/dbgpt schemas unchanged | new fifth schema fails the test |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/apps.py` -- existing chrome AppConfig; keep label `django_pyforge`; models live on this app so migrations are owned here
- `src/shared/packages/django-pyforge/src/django_pyforge/models.py` -- new `RunState` + `McpHandle`; `Meta.db_table` `run_state` / `mcp_handles`; UUID PK on run; opaque handle unique; `expires_at` for TTL; FK `run` → RunState
- `src/shared/packages/django-pyforge/src/django_pyforge/migrations/0001_supervisor_tables.py` -- Django CreateModel only; no RunSQL CREATE SCHEMA
- `src/platform/tests/test_supervisor_tables.py` -- I/O matrix: introspection, FK, two-connection read, scrape-guard, no extra schema
- Read-only: `src/platform/langflow_integration/migrations/0001_create_langflow_schema.py` and `dbgpt_integration/migrations/0001_create_dbgpt_schema.py` (the only allowed extra schemas)
- Read-only: `src/platform/tests/meta/test_no_pyforge_import.py`
- Read-only: `src/platform/config/settings/base.py` LOCAL_APPS already includes `django_pyforge`
- Do not edit: Helm migrate-job, Liquibase, `src/platform/platformapp/front_door/` besides tests that scan it

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-pyforge/src/django_pyforge/models.py` -- add supervisor models -- durable store in chrome package
- `src/shared/packages/django-pyforge/src/django_pyforge/migrations/` -- initial CreateModel migration -- Django-owned DDL
- `src/platform/tests/test_supervisor_tables.py` -- cover I/O matrix -- replica-safe public tables, no scrape

**Acceptance Criteria:**
- Given the platform database after migrate, when inspecting tables, then `run_state` and `mcp_handles` exist as tables in `public` (or SQLite default schema), not as new schemas
- Given django-pyforge migrations, when applied, then DDL is Django-owned CreateModel for those tables (Epic 27 extracts Liquibase later)
- Given front-door and MCP Python paths, when scanned, then none read `~/.bmad-loops`, tmux, or journals
- Given a handle/run inserted on one DB connection, when a second connection reads it, then the same row is returned (any replica can answer get; the front door never reads a laptop disk)

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 3, low 3)
- defer: 3: (high 0, medium 1, low 2)
- reject: 18
- addressed_findings:
  - `[medium]` `[patch]` Second connection now SELECTs `run_state` as well as `mcp_handles`
  - `[medium]` `[patch]` Scrape-guard is pathish for tmux/journal, covers expanduser, and fails if scan roots are empty
  - `[medium]` `[patch]` `CheckConstraint` `run_state_status_valid` on status
  - `[low]` `[patch]` `MinLengthValidator(32)` on handle
  - `[low]` `[patch]` Isolation allow-list includes `liquibase` (AD-9 fourth schema)
  - `[low]` `[patch]` Isolation test asserts langflow/dbgpt migration files exist

## Design Notes

Exact table names are the contract (`public.run_state`, `public.mcp_handles`). Django's default PostgreSQL schema is `public`; SQLite tests prove names via `connection.introspection.table_names()` plus `Meta.db_table`. Do not add a `search_path` / `db_schema` split.

`McpHandle.handle` is a unique CharField (opaque token), not the PK of the run. `get` in 21.3 will look up handle → run_id; this story only lands the FK.

Status on `RunState` is a small CharField with pending/running/succeeded/failed so 21.3 is not blocked on a second migration; this story does not publish via `start_*`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** django-pyforge now owns `public.run_state` and `public.mcp_handles` via Django `CreateModel` migration `0001_supervisor_tables`. Handles are unique opaque tokens with TTL column and FK to a UUID run row. No Liquibase, no MCP dual-era, no start/get tools.

**Files:**
- `src/shared/packages/django-pyforge/src/django_pyforge/models.py` — `RunState` + `McpHandle`
- `src/shared/packages/django-pyforge/src/django_pyforge/migrations/0001_supervisor_tables.py` — Django DDL
- `src/platform/tests/test_supervisor_tables.py` — I/O matrix
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-21-1-supervisor-tables-in-public.md` — tracked spec

**Review:** 6 patches applied; 3 deferred; 18 rejected (21.3/21.5 runtime, canopy:FR-12 disconnect, replica alias vs same-DB second connection). Follow-up recommended: patched medium 3 + low 3 → score 12 (≥ 5).

**Verification:** `pixi run -e platform-ci-test pytest tests/test_supervisor_tables.py tests/meta/test_no_pyforge_import.py -q` — 8 passed. `ruff check` on new files — clean.

**Residual risks:** Platform tests need PostgreSQL (`DATABASE_URL`); unix-socket default may fail locally. Replica proof is two connections to the same default DB, not a second Kubernetes replica. Front door is not yet wired to these tables (21.5).
