---
title: DB-GPT's agentic, file-hungry model integrates into a stateless Django control plane
type: dream
owner: steward
status: dreamt
---

# DB-GPT's agentic, file-hungry model integrates into a stateless Django control plane

## The Dream

DB-GPT is built around agentic personas and data-driven LLM operations —
text-to-SQL, data chat, multi-agent workflows (AWEL) — and it assumes it
owns its own filesystem for vector indices and session state. That
assumption is exactly what a 12-factor, `cookiecutter-django`-shaped
deployment refuses to allow: no local session-state paths, no
per-instance DuckDB files that vanish on redeploy, no state that isn't
recoverable from a shared store. The dream is a small set of named
integration patterns that let a project pull in DB-GPT's real
capabilities — SQL generation, data chat, multi-agent orchestration —
while forcing every piece of DB-GPT's own state through one shared
PostgreSQL control plane instead of the local filesystem it defaults to,
plus a lighter-weight path for projects that don't need the full agent
server at all.

## What it looks like when real

Three named patterns:

**Pattern A — ASGI Reusable App (API mount, tightly coupled).** A Django
data migration provisions an isolated `dbgpt_schema` namespace inside the
SAME PostgreSQL database as the Django project (`public` owned by
Django's ORM, `dbgpt_schema` owned by DB-GPT's own Alembic engine — same
shape as the Langflow ASGI pattern's schema split). DB-GPT is configured,
via environment variables alone, to bypass every local session-state path
it would otherwise default to (`~/.dbgpt/logs`, local DuckDB) and persist
all conversational/agent state into that schema instead. A custom ASGI
dispatcher in a `dbgpt_integration` Django app intercepts `/api/v1/`
traffic and routes it to DB-GPT's own FastAPI app; Django keeps the rest
of the web traffic.

**Pattern B — Asynchronous Multi-Agent Orchestration (Celery +
microservice, loosely coupled).** DB-GPT runs as its own service in
`docker-compose.yml`, managing its own model worker and API server
processes independently of Django. Django captures a complex data
request (e.g. "run a multi-agent SDLC analysis") and hands it to Redis;
a Celery worker issues the REST call that actually drives DB-GPT's AWEL
task graph, then writes the finished analysis back into Django's own
data model.

**Pattern C — Native DB-GPT SDK (library integration, no server at
all).** For lightweight text-to-SQL or a single agent execution that
doesn't warrant a running DB-GPT server, the `db-gpt` Python package is
imported directly into a Django service/view, initialized at runtime with
Django's own database credentials, and run statelessly — no background
daemon, no separate process.

Realized means: a project can pick a pattern, follow a concrete recipe
for it, and DB-GPT's state — regardless of which pattern — never lands on
a local, per-instance filesystem path that a redeploy or a second replica
would silently lose.

## Constraints

- **The storage rule is the load-bearing constraint, not a nice-to-have**:
  every local session-state path DB-GPT would use by default
  (`~/.dbgpt/logs`, local DuckDB instances) must be disabled/bypassed via
  configuration (`DBGPT_SESSION_STORAGE_TYPE=db`), with all metadata
  forced into PostgreSQL's `dbgpt_schema`. A pattern that lets any DB-GPT
  state fall back to local disk defeats the entire reason for this dream.
- **Pattern A** needs the same schema-isolation discipline Langflow's own
  ASGI pattern needs: Django's ORM never reaches into `dbgpt_schema`,
  DB-GPT's Alembic migrations never reach `public`.
- **Pattern B** adds a network hop (Celery worker -> DB-GPT container)
  DB-GPT's own AWEL orchestration doesn't have when run in-process — a new
  failure mode (timeout, partial multi-agent result) Patterns A/C don't
  carry.
- **Pattern C** is single-shot and stateless by design — it is not a
  substitute for A/B when a real multi-turn agent session or AWEL
  workflow is actually needed.
- Package sourcing is a named constraint, not an afterthought: `db-gpt`'s
  target version is sourced from the Conda Enterprise Core repository
  specifically, not the generic conda-forge upstream — a different
  provenance rule than Langflow's plain `langflow==1.11.2` conda-forge
  dependency.
- Environment surface named for Patterns A/B: `DBGPT_WEB_PORT`,
  `DBGPT_DATABASE_URL` (carrying the same `?options=-c%20
  search_path=dbgpt_schema` shape Langflow's `LANGFLOW_DATABASE_URL`
  uses), `DBGPT_SESSION_STORAGE_TYPE=db`.

## Realization log

- **2026-08-13** — Captured as a seed from an operator-supplied
  architecture brief, immediately after the sibling
  [[langflow-django-plugin]] Dream (same shared-PostgreSQL-schema
  pattern family, applied to a second agentic LLM tool). Not yet
  researched against this repo's own factory or any specific downstream
  project — no station claimed, no Spec derived, no pattern chosen.
  Owner deliberately left as `guild` (intake, not a terminal owner)
  pending a decision on which project or station this belongs to. Note:
  `docs/dreams/db-gpt-packaging.md` already exists and is a DIFFERENT,
  unrelated Dream (conda-forge packaging of DB-GPT itself, delivered via
  external PR #33883) — this Dream is about consuming DB-GPT inside a
  Django application, not packaging it.
- **2026-08-14** — Owner reassigned `guild` → `steward` by operator decision (2026-08-14 dream-backlog audit): Charter §5 reserves `guild` for pyforge-charter and forbids it as a terminal owner; the whole Django/Langflow/DB-GPT family lands under one deployment-owning station. Status stays `dreamt` — the family's preconditions (monolith-vs-microservices decision, dependency-solve spike, a named subject project) are unchanged.
- **2026-08-14** — **Operator integration direction:** this dream's Pattern A (pluggable Django application: ASGI mount + schema isolation) is the PREFERRED shape — the host is a cookiecutter-django Django service with FastAPI integration based on [[django-accelerator-framework]]; infra is PostgreSQL + Redis + Kubernetes only; the same-day conda solve spike proved py3.12 co-install feasibility (py3.14 blocked solely by langflow-base's bcrypt==4.0.1 pin — everything must become 3.14-compatible). Other patterns remain fallbacks where pluggability fails.
- **2026-08-14** — **Subject project NAMED: [[python-agent-platform]]** (operator). The family's last precondition is met — the subject Dream and its family Spec (spec-python-agent-platform, pyforge-steward) consolidate all four same-day operator decisions plus the spike evidence; this dream's remaining role is the decision trail and its named pattern contracts.
