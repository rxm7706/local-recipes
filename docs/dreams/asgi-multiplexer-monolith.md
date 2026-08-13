---
title: Django, Langflow, and DB-GPT co-locate in one ASGI process without starving each other
type: dream
owner: guild
status: dreamt
---

# Django, Langflow, and DB-GPT co-locate in one ASGI process without starving each other

## The Dream

The sibling [[langflow-django-plugin]] and [[db-gpt-django-plugin]] Dreams
each describe integrating ONE agentic LLM tool into Django, with
microservice separation as one of their named options. This Dream is the
more aggressive third path: fold ALL THREE — Django (serving a React UI),
Langflow, and DB-GPT — into a SINGLE Python process on a shared ASGI event
loop, trading the network hop and container boundary away entirely for the
lowest possible latency between the web layer and both AI engines. That
trade is only worth taking if the process can actually survive hosting
three frameworks with conflicting dependency trees (FastAPI, SQLAlchemy,
Pydantic across all three) and wildly different execution models (Django's
async-first web serving vs. Langflow/DB-GPT's synchronous LLM inference)
without one starving the others or the whole thing becoming unmaintainable
dependency archaeology.

## What it looks like when real

**Ingress & routing — one ASGI multiplexer, not three servers behind a
proxy.** `config/asgi.py` instantiates all three applications in-process
(`get_asgi_application()`, `create_langflow_app()`, `create_dbgpt_app()`)
and a master async function inspects `scope["path"]` on every incoming
request to hand execution to the right one: `/api/v1/`, `/health`,
`/langflow` → Langflow; `/api/dbgpt/` (prefix stripped) → DB-GPT; anything
else → Django. No Docker-level reverse proxy — routing happens inside the
one process.

**Dependency resolution — a real, solved manifest, not a hope.** Standard
package managers fail outright on three frameworks' conflicting
requirements; realized means an actual environment manifest exists that
strictly pins the lowest common denominator for every shared core library
(e.g., Pydantic — whichever major version both Langflow and DB-GPT can
actually agree to run under), verified to solve, not asserted.

**Statelessness — DB-GPT's filesystem habit is fully disabled, not
partially.** Same rule as the [[db-gpt-django-plugin]] Dream: every local
session-state path DB-GPT would default to must be overridden at runtime,
before the DB-GPT application factory is ever called, forcing all state
into PostgreSQL's `dbgpt_schema`.

**Blocking isolation — the event loop never stalls on an LLM call.**
DB-GPT and Langflow both run synchronous inference that would otherwise
block Django's async event loop and starve ordinary HTTP responses to the
React UI; realized means the ASGI server's thread pool is sized
deliberately (not left at a framework default) so a slow inference never
means a stalled page load.

**Data layer — one PostgreSQL database, three schemas, one owner each.**
`public` (Django), `langflow_schema` (Langflow), `dbgpt_schema` (DB-GPT) —
the same three-schema split the two sibling Dreams each describe on their
own, now co-existing in the same database because all three frameworks
are, for the first time, genuinely in the same process.

## Constraints

- **This is NOT a superset of the sibling Dreams — it is a distinct,
  harder option**, only worth choosing when the latency win from
  same-process execution outweighs the real cost: a much larger blast
  radius (one crashing framework can take the other two down with it,
  where separate containers would not) and a dependency-resolution problem
  that may simply be infeasible for a given trio of versions.
- **Thread-pool sizing is a load-bearing tuning decision, not a constant to
  copy-paste.** An under-sized pool starves the UI; an over-sized one
  invites its own resource-exhaustion failure mode. Whatever value is
  chosen needs to be justified against real measured inference latency,
  not picked once and forgotten.
- **Package sourcing inherits DB-GPT's own constraint** from the
  [[db-gpt-django-plugin]] Dream: its dependency chain is sourced from the
  Conda Enterprise Core repository specifically, for controlled,
  enterprise-compliant pinning — this monolith's dependency-matrix
  resolution has to reconcile against that source, not generic PyPI/
  conda-forge.
- **Statelessness and schema-isolation constraints are inherited
  verbatim** from both sibling Dreams — nothing about running all three in
  one process relaxes either rule; if anything, sharing one process makes
  a state leak between the three harder to detect, not easier.
- Environment surface named: `ANYIO_MAX_THREADS` (or equivalent — prevents
  ASGI event-loop blocking), `LANGFLOW_DATABASE_URL` and
  `DBGPT_DATABASE_URL` (each carrying its own `search_path` schema
  isolation), `DBGPT_SESSION_STORAGE_TYPE=db`.

## Realization log

- **2026-08-13** — Captured as a seed from an operator-supplied
  architecture brief, immediately after the sibling
  [[langflow-django-plugin]] and [[db-gpt-django-plugin]] Dreams — this one
  is their more aggressive "all three, one process" variant rather than a
  fourth independent pattern. Not yet researched against this repo's own
  factory or any specific downstream project — no station claimed, no
  Spec derived, dependency-matrix feasibility unverified. Owner
  deliberately left as `guild` (intake, not a terminal owner) pending a
  decision on which project or station this belongs to, and pending
  confirmation that the underlying dependency conflict is even solvable
  before committing engineering time to it.
