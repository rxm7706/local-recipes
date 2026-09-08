---
title: start/get survives disconnect
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: 24f670472b44e412cd718a8a05e57d14b5a1c8fe
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Atlas MCP long work still runs in the request. An ingress idle timeout drops the client and the result is lost or recomputed.

**Approach:** Atlas `start_*` publishes a run through the django-pyforge supervisor (one ledger: `public.run_state` + `public.mcp_handles`) and returns an opaque TTL'd handle before the worker finishes. `get_*` reattaches with handle plus AD-7 assertion and reads the stored result from any replica.

## Boundaries & Constraints

**Always:** `start_*` is a supervisor publish — no second ledger (Redis handle store, in-memory dict, filesystem). Handles are opaque high-entropy (`secrets.token_urlsafe` ≥32 chars) with `expires_at`. `get_*` requires a valid RS256 assertion (`aud` = `mcp:atlas`) **and** the handle; possession alone is refused. Survival is PostgreSQL rows, not progress notifications, sticky sessions, or stream replay. Physical writes under `_bmad-output/projects/pyforge-steward/` plus Code Map. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Parent AD-2: no `pyforge.*` under `src/platform/`.

**Block If:** Implementation would need MinIO, Liquibase 27-1, or a fifth PostgreSQL schema.

**Never:** Story 21.4 other station MCP faces. Story 21.5 front-door supervisor UI. Epic 30 console deletion. `import pyforge` under `src/platform/`. Dual-endpoint SSE as the reconnect path. Tasks-extension / SEP-2663 as the store.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Start returns early | `start_run_pipeline` with valid assertion; worker latched | JSON handle; `run_state.status` is `running`; work not finished | No error expected |
| Disconnect then get | Drop after start; worker completes once; reconnect `get_run` with handle + assertion | Same stored result; work callable invoked once | No recompute |
| Other replica | Insert/complete on connection A; `get_run` via supervisor on connection B | Same result | `DoesNotExist` if missing, not a filesystem fallback |
| Handle only | `get_run` with handle, no assertion or invalid JWT | Refused (401 / JSON-RPC error); no result body | AssertionRefusedError path |
| TTL / entropy | New handle | `len >= 32`; lookup after `expires_at` refused | Expired handle is not a success |
| Survival mechanism | Source of start/get + mcp_http | No progress-notification / sticky-session / stream-replay reconnect | AST fail on those as the store |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/models.py` — add `RunState.result` JSONField (nullable) and `McpHandle.subject` (IdP `sub` bound at start); keep `db_table` names
- `src/shared/packages/django-pyforge/src/django_pyforge/migrations/0002_run_result_and_handle_subject.py` — Django AddField only; no CREATE SCHEMA; not Liquibase
- `src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py` — **new** `publish_start` / `complete_run` / `get_run`; only publisher of run rows (canopy:AD-12)
- `src/shared/packages/django-pyforge/src/django_pyforge/tasks.py` — **new** Celery `execute_supervised_run`; autodiscover via AppConfig
- `src/shared/packages/django-pyforge/src/django_pyforge/mcp_start_get.py` — **new** register `start_run_pipeline` + `get_run` on an official `MCPServer` (assertion + handle args)
- `src/shared/packages/django-atlas/src/django_atlas_portal/mcp_asgi.py` — after `build_server()`, register start/get; domain work stays `pyforge.atlas.mcp.tools` (lazy, not at host import in platform tests)
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/crypto.py` — reuse `verify_assertion` (read-only)
- `src/platform/tests/test_start_get_survives_disconnect.py` — I/O matrix; dummy runner; two connections; AST survival-mechanism scan
- Read-only: `mcp_http.py` dual-era gate, `models.py` table names from 21.1, `test_no_pyforge_import.py`, atlas `tools.py` bodies
- Do not edit: other stations' `mcp_asgi_app`, Helm/Liquibase, Epic 30 console, `src/platform/` Python packages named `pyforge`

## Tasks & Acceptance

**Execution:**
- `django_pyforge/models.py` + `migrations/0002_*.py` — persist result + subject — get without recompute
- `django_pyforge/supervisor.py` + `tasks.py` — one ledger + Celery after commit — start returns first
- `django_pyforge/mcp_start_get.py` + `django_atlas_portal/mcp_asgi.py` — atlas MCP tools — canopy:FR-12 surface
- `src/platform/tests/test_start_get_survives_disconnect.py` — I/O matrix

**Acceptance Criteria:**
- Given a simulated ingress disconnect mid-operation, when the client reconnects with the handle and a valid assertion, then it receives the same result without recomputation
- Given `start_*`, when called, then it returns before the work finishes and publishes through the supervisor (no second ledger)
- Given `get_*` on a different replica (second DB connection), when the handle and assertion are valid, then it succeeds; when the handle is presented without the assertion, then it is refused
- Given handles, when issued, then they are opaque, high-entropy, and TTL'd; progress notifications / sticky sessions / stream replay are not the survival mechanism

## Design Notes

`publish_start` must COMMIT the handle row before enqueue. Tests patch `execute_supervised_run.delay` (or latch the dummy runner) so eager Celery cannot finish work before `start_*` returns.

Dummy runner in platform tests avoids importing Kedro. Atlas production runner lazy-imports `tools.run_pipeline`.

`get_run` verifies AD-7 assertion for `aud=mcp:atlas` and matches `McpHandle.subject`. Possession-only is a hard fail.

Do not add start/get to the other seven stations (21.4).

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 0, low 3)
- defer: 0
- reject: 4
- addressed_findings:
  - `[low]` `[patch]` ruff I001/E501/COM812 on the new platform test
  - `[low]` `[patch]` MCP tools/call needs `_meta` + `mcp-method`/`mcp-name` headers (SDK 2.0 envelope)
  - `[low]` `[patch]` restore lazy-import noqa on atlas `mcp_asgi.py`; drop unused `Callable` import

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** Atlas `start_run_pipeline` / `get_run` publish through django-pyforge supervisor into `public.run_state` + `public.mcp_handles`. Start commits a handle then enqueues Celery; get requires AD-7 assertion plus handle and returns the stored result without recomputation.

**Files:**
- `django_pyforge/models.py` + `migrations/0002_*` — result JSON + handle subject
- `django_pyforge/supervisor.py` + `tasks.py` + `mcp_start_get.py` — one ledger, Celery, MCP tools
- `django_atlas_portal/mcp_asgi.py` — attach start/get to existing `build_server`
- `src/platform/tests/test_start_get_survives_disconnect.py` — I/O matrix
- tracked spec `spec-21-3-start-get-survives-disconnect.md`

**Review:** 3 low patches applied; 0 deferred; 4 rejected (k8s two-replica vs second DB connection already 21.1 shape; 21.4 other faces; 21.5 UI; Liquibase 27-1). Follow-up recommended: false (score 3).

**Verification:** 29 passed under `platform-ci-test` with `DATABASE_URL=postgres://postgres:platform@127.0.0.1:5432/platform`. ruff clean on touched files.

**Residual risks:** Replica proof is a second DB connection, not a second Deployment. Production runner is registered on first atlas MCP ASGI build; tests inject a dummy runner.
