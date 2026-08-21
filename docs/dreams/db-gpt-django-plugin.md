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
- **2026-08-21** — **DEVIATION: Pattern A → Pattern B for DB-GPT (AD-14 sidecar-fallback trigger, demonstrated).** Story 11-2 (pyforge-steward, spec-python-agent-platform) hit a real, verified pluggability failure: `dbgpt-app` (needed for DB-GPT's FastAPI mount, including the AgenticData text-to-SQL router) pins `fastapi<0.113.0`; `langflow-base` — already resident in the shared `platform-dev` environment since Story 11.1 — requires `fastapi>=0.135.0`. The ranges are disjoint; no `fastapi` version satisfies both, confirmed live by adding `dbgpt-app` to `pixi.toml` and watching `pixi install -e platform-dev` fail to solve with exactly this conflict. Per AD-14 ("sidecar fallback only on demonstrated pluggability failure, Dream first"), DB-GPT moves from Pattern A to this dream's existing **Pattern B** (Celery + microservice, DB-GPT run via `docker-compose.yml` independently of Django) for Stories 11-2/11-3/11-4 — Pattern B was already specified above, not invented for this deviation. Operator decision (2026-08-21): file the fastapi-ceiling conflict upstream with DB-GPT (`eosphoros-ai/DB-GPT`'s `dbgpt-client` extra) — operator-owned, filed by hand, not automated — while proceeding with Pattern B now rather than blocking indefinitely on an upstream timeline with no guarantee; revisit Pattern A if/when upstream relaxes the pin. This is the first time AD-14's fallback clause has actually fired; the operator intends it as a reusable precedent (demonstrated-conflict → Pattern B, dated here first) for future engine integrations on this platform, not a one-off DB-GPT exception. Langflow is unaffected and stays on Pattern A.
- **2026-08-21** — **Operator direction: pattern selection becomes a per-engine config switch, not a hardcoded fork.** Rather than wiring DB-GPT to Pattern B as a bespoke, one-off code path, Story 11-2 builds the pattern choice (A vs. B, per engine) as a configuration seam every future integration on this platform reuses — so reverting DB-GPT to Pattern A later (once the upstream fastapi conflict resolves) is a config change, not a rewrite, and the next engine that hits a Pattern-A pluggability conflict picks up the same switch instead of re-deriving it. This is a platform-level capability, not an 11-2-local implementation detail — formalized as an architecture-spine addition via `bmad-correct-course` before 11-2's spec is re-scoped (see spec-python-agent-platform's Realization/change log for the resulting AD).
- **2026-08-21 (later)** — **A second, independent DB-GPT limitation found, on Pattern B this time: its own metadata store cannot use PostgreSQL, permanently.** Building the real Pattern-B integration, Story 11-2 live-verified the whole registry-driven design working — schema migration, no ASGI mount, a real Celery text-to-SQL round trip through the sidecar (Gemini-backed, live SQL result returned) — but found `dbgpt-app` 0.8.1 structurally cannot wire its own `service.web.database` metadata store (chat history, knowledge/RAG, flow/plugin configs — real state, not disposable cache) to Postgres: connector-type rejection, a SQLite-only migration path, and MySQL-only `TEXT(length)` SQLAlchemy columns that fail real PostgreSQL DDL. Operator decision: accept SQLite behind a dedicated Kubernetes `PersistentVolumeClaim` as the *permanent* architecture for this one store — not the "interim" label Story 10.5 gave its own volume-backed fix — recorded as a bounded exception to AD-6 (statelessness) in `spec-python-agent-platform`'s architecture spine, narrowly scoped to `dbgpt-app`'s own metadata store, no other engine or component. The PVC still satisfies AD-6's real guarantee (state survives redeploy, never silently lost); the cost is that this one container stays a singleton, not horizontally replicable. Operator files the Postgres-support gap upstream with `eosphoros-ai/DB-GPT` directly (AD-9) — real dialect-portability work, not bankable as a near-term fix, so not gated on. Same shape of decision as the fastapi/Pattern-B deviation above: name the upstream engine's real limitation, record a dated bounded exception, keep moving rather than block the platform on someone else's codebase.
