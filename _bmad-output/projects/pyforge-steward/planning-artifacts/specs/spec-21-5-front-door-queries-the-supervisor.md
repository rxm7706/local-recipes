---
title: Front door queries the supervisor
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: e52e6203512b1de3ea67202562bfc8a9bc0f9183
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
warnings: []
deferred:
  - summary: >-
      Last-ok age lives in Django cache; redis-cache IGNORE_EXCEPTIONS can
      swallow the write so a later outage shows never.
    evidence: |-
      Review noted locmem tests cannot see a swallowed redis set.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
    severity: low
  - summary: >-
      load_board_rows has no LIMIT; a large run_state table can miss the
      500ms budget.
    evidence: |-
      FR-42 budget vs unbounded SELECT; retention is not this story.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Live runs and completed timing still cannot be shown by a deployed front door. The retired board scraped `~/.bmad-loops`, tmux, and journals, so Pages rendered `unavailable`.

**Approach:** Persist station + start/complete timing on `public.run_state`. The supervisor is the only query API. The front door GET `/runs/` renders that snapshot — never a filesystem fallback. Unreachable supervisor is explicit unavailable plus last-ok age, inside a 500ms budget.

## Boundaries & Constraints

**Always:** Query `django_pyforge.supervisor.query_board` only. Ingest timing in `complete_run`, not at page generation. Cross-machine visibility is the same PostgreSQL (second DB connection). FR-26 budget is 500ms (`QUERY_BUDGET_SECONDS`). Live board is not a Wagtail field. Parent AD-2: no `import pyforge` under `src/platform/`. Physical writes under `_bmad-output/projects/pyforge-steward/` plus the Code Map. `BMAD_ACTIVE_PROJECT=pyforge-steward`.

**Block If:** Implementation would need MinIO, Liquibase 27-1, a fifth PostgreSQL schema, or `pyforge.*` under `src/platform/`.

**Never:** Story 22.1 pyforge grammar. Epic 30 console deletion. Helm/Liquibase. MinIO. Filesystem fallback to home-dir loop state, tmux, or journals.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Supervisor only | GET `/runs/` with rows in `run_state` | HTML lists live runs from `query_board`; no home-dir scrape | No error expected |
| Cross-machine | Insert run via connection A; GET `/runs/` via default | Same `run_id` visible | Missing row is empty list, not a scrape |
| Timing ingest | `complete_run` then GET `/runs/` | Completed duration/started/completed queryable; not only latest | No error expected |
| Unreachable | `query_board` raises `SupervisorUnavailable` | Body contains `unavailable` plus last-ok age (or `never`); not an empty list as current | Degrades; does not hang past 500ms |
| Empty current | `query_board` succeeds with zero rows | Empty list plus `age` of this query — marked current, not unavailable | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/models.py` — add `station`, `started_at`, `heartbeat_at`, `completed_at`, `duration_ms` on `RunState` (21.1 deferred FR-41 columns here)
- `src/shared/packages/django-pyforge/src/django_pyforge/migrations/0003_run_state_timing.py` — Django AddField only; no CREATE SCHEMA
- `src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py` — persist station/timestamps in `publish_start` / `complete_run`; add `query_board` (live + completed timing), `SupervisorUnavailableError`, 500ms statement timeout, cache last-ok
- `src/platform/platformapp/front_door/views.py` — **new** `runs_board` calls `query_board` only
- `src/platform/platformapp/front_door/urls.py` — **new** `path("runs/", ...)`
- `src/platform/config/urls.py` — include front_door urls **before** Wagtail catch-all
- `src/platform/platformapp/front_door/templates/front_door/runs.html` — live rows or `unavailable` + age; empty current vs unavailable distinguishable
- `src/platform/tests/test_front_door_queries_supervisor.py` — I/O matrix; AST scrape-guard on front_door + supervisor query path
- Read-only: `test_supervisor_tables.py` scrape roots, `test_start_get_survives_disconnect.py`, `test_no_pyforge_import.py`
- Do not edit: Epic 30 `docs/dashboard/`, Helm/Liquibase, `src/platform/` packages named `pyforge`, station MCP faces, 22.1 grammar

## Tasks & Acceptance

**Execution:**
- `django_pyforge/models.py` + `migrations/0003_*.py` — timing columns — FR-41
- `django_pyforge/supervisor.py` — `query_board` + ingest in `complete_run` — AD-12
- `platformapp/front_door/views.py` + `urls.py` + template + `config/urls.py` — `/runs/` — FR-40/FR-42
- `src/platform/tests/test_front_door_queries_supervisor.py` — I/O matrix

**Acceptance Criteria:**
- Given a deployed egress-blocked namespace, when the front door renders run state, then it uses the supervisor API only — no filesystem fallback
- Given a run started on one machine, when a front door on another queries, then that run is visible
- Given run completion, when timing is queried across runs, then ingest happened at completion and history is not only the latest row
- Given an unreachable supervisor, when `/runs/` is requested, then the body is explicit unavailable plus age within the 500ms budget — not an empty list presented as current

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 2, low 4)
- defer: 2: (high 0, medium 0, low 2)
- reject: 10
- addressed_findings:
  - `[medium]` `[patch]` last-ok cache now `timeout=None`; success-then-fail test writes last-ok via `query_board`
  - `[medium]` `[patch]` test spies `SET LOCAL statement_timeout`
  - `[low]` `[patch]` catch `DatabaseError`; coerce ISO last-ok; assert `12s` age; drop unused `BoardSnapshot.unavailable`

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** GET `/runs/` renders live runs and completed timing from `django_pyforge.supervisor.query_board` only. `complete_run` ingests duration at completion. Unreachable DB/query maps to HTML `unavailable` plus last-ok age (or `never`), with PostgreSQL `statement_timeout` 500ms.

**Files:**
- `django_pyforge/models.py` + `migrations/0003_*` — station and timing columns
- `django_pyforge/supervisor.py` — query_board, last-ok cache, complete_run ingest
- `platformapp/front_door/views.py` + `urls.py` + `runs.html` + `config/urls.py` — `/runs/`
- `tests/test_front_door_queries_supervisor.py` — I/O matrix
- tracked spec `spec-21-5-front-door-queries-the-supervisor.md`

**Review:** 6 patches applied; 2 deferred; 10 rejected (Wagtail home, PyBreaker/Epic 25, k8s two-machine, loop ingest, auth, heartbeat worker, journal.jsonl, pagination, homepage link, sqlite skip-as-fail). Follow-up recommended: true (score 10 = 3×2 medium + 4 low).

**Verification:** 27 passed under `platform-ci-test` with `DATABASE_URL=postgres://postgres:platform@127.0.0.1:5432/platform`. ruff clean on touched files.

**Residual risks:** Replica proof is a second DB connection. Timeout is SET LOCAL, not a hung-query integration. Last-ok is process cache, not PostgreSQL.

## Design Notes

`query_board` is the supervisor API. The view must not call `RunState.objects` or `Path.home`. Cache last successful `queried_at` under a django-cache key so unavailable can show age.

500ms: PostgreSQL `SET LOCAL statement_timeout` inside `query_board`'s atomic block (`QUERY_BUDGET_SECONDS`). Do not add PyBreaker (Epic 25). Do not add pybreaker to pixi. Same-thread ORM so a replica and a test transaction both see committed/visible rows.

Distinguish empty-current (`data-board="current"`) from unavailable (`data-board="unavailable"`).

Coverage `fail_under = 100` on `platformapp/**` — keep the view a thin try/except.
