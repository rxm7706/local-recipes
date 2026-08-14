---
title: Langflow integrates into a cookiecutter-django project without fighting it
type: dream
owner: steward
status: dreamt
---

# Langflow integrates into a cookiecutter-django project without fighting it

## The Dream

`cookiecutter-django` gives a project a robust, opinionated ecosystem —
Docker, Uvicorn, Celery, PostgreSQL — and Langflow (v1.11.2) is a
FastAPI/SQLAlchemy application with its own migration and process model.
Bolting the two together forces a choice between tight coupling (one
process, one deploy) and loose coupling (separate services talking over
HTTP) — and the right choice depends on constraints (deployment topology,
scale, how much of Langflow's own UI is wanted) that vary per project. No
single pattern is universally right, so the dream is a small, named set of
integration architectures a project can pick from deliberately, each with
its own data-ownership story, dependency footprint, and failure mode —
not a single hard-coded "the" way to wire Langflow into Django.

## What it looks like when real

Four named patterns, each usable independently:

**Pattern A — ASGI Reusable App (primary, tightly coupled).** A Django data
migration (`RunSQL`) provisions an isolated PostgreSQL schema
(`langflow_schema`) in the SAME database as the Django project
(`[cookiecutter_project_db]`: `public` owned by Django's ORM via `manage.py
migrate`, `langflow_schema` owned by Langflow's own Alembic migrations at
Uvicorn startup). Langflow's `LANGFLOW_DATABASE_URL` carries a
`search_path` option so its SQLAlchemy/Alembic layer never touches the
`public` schema — no Django ORM collision, one database, one connection
pool. A custom ASGI dispatcher (`langflow_integration/asgi.py`) sits at the
root of the routing stack and forwards `/api/v1/`, `/health`, and
`/langflow/` to the embedded FastAPI app; everything else falls through to
Django. One process, one deploy, one Uvicorn.

**Pattern B — Native Python Execution (no server, loosest coupling).**
Langflow graphs are designed once (locally, via the Langflow UI or however)
and exported as static `.json` flow files committed to the Django repo.
Django views call `langflow.load.run_flow_from_json()` directly — a plain
library call, not an HTTP round-trip — to execute a graph synchronously.
No Langflow server, no extra process, no network hop; the tradeoff is that
flows are static artifacts, not live-editable through a running UI.

**Pattern C — Web Component Integration (frontend-only, microservice).**
Langflow runs as its own container in `docker-compose.yml`, fully separate
from Django — no shared database, no shared process. Django templates load
the `<langflow-chat>` web component from a CDN and point it at the
Langflow container's own API URL, rendering a floating chat widget whose
traffic goes straight from the browser to Langflow, bypassing the Django
backend entirely.

**Pattern D — Asynchronous Celery Execution (scalable backend, decoupled
compute).** Django captures user input and immediately hands it to Celery
via Redis rather than blocking the request on LLM inference latency. A
Celery worker makes an internal HTTP call (`httpx`) to the adjacent
Langflow container, gets the result, and writes it back into Django's own
database — Django and Langflow stay separate services, but the response
still lands in Django's data model instead of only existing inside
Langflow.

Realized means: a project can name which pattern it wants, follow a
concrete recipe for it (schema/migration steps for A, the library-call
shape for B, the compose + CDN snippet for C, the task/worker wiring for
D), and get a working integration without re-deriving the tradeoffs from
scratch each time.

## Constraints

- **Pattern A** needs `search_path` isolation to be real, not aspirational
  — Langflow's migrations must never be able to reach the `public` schema,
  and Django's ORM must never be pointed at `langflow_schema`. This is the
  one pattern where getting the boundary wrong causes silent data corruption
  across two ORMs sharing one database.
- **Pattern D** trades latency for durability: the HTTP call from Celery
  worker to Langflow container is a new failure mode (timeout, connection
  refused, partial response) that pattern A/B never have, since they never
  cross a process boundary for the actual inference call.
- **Pattern C** has zero backend integration by design — anything that
  needs the LLM's output back inside Django's own data model cannot use
  Pattern C alone.
- Dependencies vary by pattern, not a single fixed set: `langflow==1.11.2`
  + `uvicorn` for A/B; `httpx` additionally for D; Celery + Redis
  additionally for D; the Langflow chat-widget CDN script additionally for
  C. A project adopting one pattern should not need to pull in the
  dependency footprint of the other three.
- Environment surface named for Pattern A: `LANGFLOW_FRONTEND_PATH`,
  `LANGFLOW_BACKEND_URL`, and a `LANGFLOW_DATABASE_URL` carrying the
  `?options=-c%20search_path=langflow_schema` suffix.

## Realization log

- **2026-08-13** — Captured as a seed from an operator-supplied architecture
  brief (background/method/architecture/dependencies for all four patterns).
  Not yet researched against this repo's own factory or any specific
  downstream project — no station claimed, no Spec derived, no pattern
  chosen. Owner deliberately left as `guild` (intake, not a terminal owner)
  pending a decision on which project or station this belongs to.
- **2026-08-14** — Owner reassigned `guild` → `steward` by operator decision (2026-08-14 dream-backlog audit): Charter §5 reserves `guild` for pyforge-charter and forbids it as a terminal owner; the whole Django/Langflow/DB-GPT family lands under one deployment-owning station. Status stays `dreamt` — the family's preconditions (monolith-vs-microservices decision, dependency-solve spike, a named subject project) are unchanged.
