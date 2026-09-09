---
title: Django, Langflow, and DB-GPT co-locate in one ASGI process without starving each other
type: dream
owner: steward
status: realized   # was `absorbed` (off-vocabulary, normalised 2026-09-05); 2026-08-22 pointer spec authored (spec-asgi-multiplexer-monolith); realized through python-agent-platform per the 2026-08-14 Realization log
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
- **2026-08-14** — Owner reassigned `guild` → `steward` by operator decision (2026-08-14 dream-backlog audit): Charter §5 reserves `guild` for pyforge-charter and forbids it as a terminal owner; the whole Django/Langflow/DB-GPT family lands under one deployment-owning station. Status stays `dreamt` — the family's preconditions (monolith-vs-microservices decision, dependency-solve spike, a named subject project) are unchanged.
- **2026-08-14** — **Dependency-solve spike PASSED (conda-native).** Operator-requested feasibility gate run via `micromamba create --dry-run -c conda-forge langflow dbgpt dbgpt-serve "django>=5" python=3.12`: solves cleanly — 373 packages, one environment: langflow 1.11.2 + dbgpt/dbgpt-serve 0.8.1 + django 5.2.15 agreeing on pydantic 2.13.4 / sqlalchemy 2.0.52 / fastapi 0.141.1. Both engines are now conda-forge packages this factory itself shipped (langflow-feedstock pushed 2026-08-13, db-gpt-feedstock 2026-07-22), so the co-install premise is verified-to-solve, not asserted — the monolith is a live option and neither sibling wins by default. The pair choice is now a deliberate decision awaiting the family's last precondition: a named subject project. **Python-3.14 lane (operator constraint, same day: everything must be 3.14-compatible): FAILS today** — `langflow-base` pins `bcrypt ==4.0.1` (langflow-feedstock recipe line 198, upstream's passlib-compat pin) and no py3.14 build of that bcrypt exists, while `dbgpt`+`dbgpt-serve`+`django>=5` alone solve clean on 3.14 (61 pkgs). The family's sole 3.14 blocker is that one exact pin; remedy is upstream langflow dropping the passlib-era pin or a runtime-validated feedstock loosening — tracked as a langflow-feedstock maintenance item. **Infrastructure constraint (operator, same day): core infrastructure is exactly PostgreSQL + Redis + a Kubernetes container platform (Red Hat OCP or Google GCP/GKE, Docker/Podman images) — nothing else.** This fits the family's existing shape (one PostgreSQL with public/langflow_schema/dbgpt_schema; Redis as the Celery broker; hard statelessness now mandatory since pods are ephemeral — pgvector inside the same PostgreSQL if DB-GPT needs a vector store, no separate one), and shifts the deployment mechanism from Compose/Traefik to K8s ingress/OCP routes at Spec time. It tilts the pair choice toward the microservices topology (per-service pods behind one ingress; replicas = capacity; the in-process co-location the monolith trades for is worth less when in-cluster networking is the platform norm) — the monolith stays viable only as a single-container deployment. Final pair choice still deferred to Spec intake with the named subject project.
- **2026-08-14** — **Operator architecture direction (same day, supersedes the open pair framing):** all components build on and integrate into ONE Django service — cookiecutter-django based, WITH FastAPI integration — grounded in [[django-accelerator-framework]]; the engines integrate **preferably as pluggable Django applications** ([[langflow-django-plugin]] / [[db-gpt-django-plugin]] Pattern-A shapes: ASGI mount + schema isolation), deployed on the PostgreSQL + Redis + Kubernetes platform recorded above. Scaling = replicating the whole service (statelessness mandatory); a per-engine sidecar container remains the fallback ONLY where pluggability fails (dependency or lifecycle isolation). Remaining precondition before Spec intake: naming the subject project.
- **2026-08-14** — **Subject project NAMED: [[python-agent-platform]]** (operator). The family's last precondition is met — the subject Dream and its family Spec (spec-python-agent-platform, pyforge-steward) consolidate all four same-day operator decisions plus the spike evidence; this dream's remaining role is the decision trail and its named pattern contracts.
- **2026-09-09** — **Fleet readiness pass, realization gate** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, row stA / § C10). The Pattern-A/B integration, schema split and statelessness criteria are exercised in the running estate (`src/platform/config/engine_patterns.py`, `config/settings/base.py:172-175`, `config/estate_dsn.py`). **One named criterion is not:** "the ASGI server's thread pool is sized deliberately (not left at a framework default)" — there is no `ANYIO_MAX_THREADS` or any thread-pool sizing anywhere in `src/platform/`. The residue is recorded (`spec-local-ocp-hybrid-environment/reconciliation-and-corrections.md:41`, `.memlog.md:15`) but had **no story and no ledger key**; it now lands as an acceptance clause on steward **Story 48.2** (R-18 sizing), whose Surface was chart-only. Status stays `realized`.
