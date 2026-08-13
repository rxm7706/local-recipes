---
title: Django, Langflow, and DB-GPT scale as isolated containers behind one gateway
type: dream
owner: guild
status: dreamt
---

# Django, Langflow, and DB-GPT scale as isolated containers behind one gateway

## The Dream

The sibling [[asgi-multiplexer-monolith]] Dream folds Django, Langflow, and
DB-GPT into one process for latency; this Dream is its structural opposite
— the microservices answer to the same three-framework combination,
chosen specifically BECAUSE the monolithic path may be structurally
unviable (Langflow and DB-GPT's own FastAPI/SQLAlchemy dependency trees
can conflict badly enough that co-locating them in one Python environment
just doesn't solve). Each framework runs in its own container, isolated
by design, with one edge gateway (Traefik) doing path-based routing so a
single public hostname still fronts all three — and Celery/Redis in
between so long-running LLM/agent work never blocks Django's own request
cycle. The point is horizontal scalability and blast-radius containment
(one container crashing doesn't take the other two down) traded against
the network hop the monolith avoids.

## What it looks like when real

**Routing layer — Traefik as the one ingress, container isolation
preserved.** Traefik intercepts all incoming HTTP inside the Docker
network and does prefix-based routing with prefix-stripping — `/langflow`
→ the Langflow container (internal port 7860), `/dbgpt` → the DB-GPT
container (internal port 8000, prefix stripped so DB-GPT sees standard
root routes), everything else → Django (internal port 5000) — with NO
internal container port ever exposed directly to the host. `docker-
compose`/`production.yml` labels declare the routing rules per-service
(`traefik.enable=true` + a `PathPrefix` rule + a `stripprefix` middleware
per AI-engine service), extending cookiecutter-django's own existing
Traefik-fronted production compose file rather than replacing it.

**Orchestration layer — Django dispatches, Celery executes, nothing
blocks.** Django handles UI/user input only; a long-running LLM/agent task
goes to Redis and a Celery worker picks it up, talking to Langflow/DB-GPT
over the internal Docker network (not through the public Traefik edge) —
mirrors the sibling Dreams' own "Pattern B/D" async-orchestration option,
but as the ONLY path here, not one of several.

**Data layer — the same three-schema PostgreSQL split, now owned by
independent containers.** `public` (Django), `langflow_schema`,
`dbgpt_schema` — identical schema-isolation contract to both
[[langflow-django-plugin]] and [[db-gpt-django-plugin]], but each schema's
owning framework now runs in its own container rather than sharing
Django's own process.

**Statelessness — every container is genuinely ephemeral.** No container
in the fleet keeps state that matters on its own local disk — local logs,
DuckDB files, local cache directories are all disabled or treated as
throwaway; conversational memory, agent configuration, and session data
all persist to PostgreSQL, so any container can be killed and replaced
without losing anything.

## Constraints

- **This is a DIFFERENT choice from the monolith Dream, not a fallback
  built the same way twice.** The decision between this and
  [[asgi-multiplexer-monolith]] is real engineering tradeoff (blast-radius
  containment + independent scaling vs. lower latency + one process to
  operate), not a default — whichever is chosen should be chosen on
  purpose, with the dependency-conflict feasibility check from the
  monolith Dream as one deciding input.
- **DB-GPT's own container needs a custom build**, not an off-the-shelf
  image (unlike Langflow, which ships `langflowai/langflow:1.11.2`
  directly) — its dependency chain sources from the Conda Enterprise Core
  repository specifically, the same constraint the sibling Dreams name,
  now expressed as a Dockerfile requirement rather than a pip/conda
  environment requirement.
- **Traefik must never expose an internal AI-engine port to the host** —
  the whole point of container isolation is defeated if `langflow`/`dbgpt`
  publish ports directly instead of routing exclusively through the
  Traefik network.
- **Statelessness is a hard requirement for horizontal scaling to mean
  anything**: if any container silently accumulates local state, adding a
  second replica of that container produces inconsistent behavior instead
  of more capacity — the "all state in PostgreSQL" rule isn't optional
  once more than one replica of anything exists.
- Environment surface named (shared `.env`, extending cookiecutter-django's
  existing `.envs/.production/` convention): `LANGFLOW_DATABASE_URL`,
  `DBGPT_DATABASE_URL` (each with its own `search_path` schema),
  `DBGPT_SESSION_STORAGE_TYPE=db`.
- Infrastructure floor: Docker Engine + Compose v2+, Traefik v2.10+,
  Redis 6+, PostgreSQL 14+.

## Realization log

- **2026-08-13** — Captured as a seed from an operator-supplied
  architecture brief, immediately after [[asgi-multiplexer-monolith]] —
  the two are a deliberate pair (monolith vs. microservices) for the same
  three-framework combination, and this one arrived with a concrete
  `docker-compose`/`production.yml` extension (Traefik labels, service
  definitions for `langflow`/`dbgpt`/`celeryworker`) rather than prose
  alone. Not yet researched against this repo's own factory or any
  specific downstream project — no station claimed, no Spec derived, no
  decision made between this and the monolith option. Owner deliberately
  left as `guild` (intake, not a terminal owner) pending that decision.
