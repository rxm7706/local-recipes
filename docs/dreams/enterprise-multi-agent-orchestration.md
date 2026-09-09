---
title: Django, Langflow, and DB-GPT scale as isolated containers behind one gateway
type: dream
owner: steward
status: realized   # was `absorbed` (off-vocabulary, normalised 2026-09-05); 2026-08-22 pointer spec authored (spec-enterprise-multi-agent-orchestration); realized through python-agent-platform per the 2026-08-14 Realization log
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

**Routing layer — SUPERSEDED 2026-08-14 (see § Realization log).** As
seeded, this Dream specified Traefik prefix-routing over `docker-compose`
to per-engine container ports (`/langflow` → 7860, `/dbgpt` → 8000 with
the prefix stripped, everything else → Django on 5000) with no port
published to the host, declared by `traefik.enable=true` + `PathPrefix` +
`stripprefix` labels on cookiecutter-django's own Traefik-fronted
production compose file. The operator's same-day infrastructure ruling
(PostgreSQL + Redis + Kubernetes only) replaced that mechanism with a
Kubernetes Ingress / OpenShift Route in front of one Service; realized
through [[python-agent-platform]], whose live edge is
`src/platform/deploy/charts/platform/templates/ingress.yaml` and
`src/platform/deploy/overlays/ocp/chart/templates/route.yaml` (pap:AD-11).
The paragraph is retained as the record of the option that was not taken;
it is **not** a description of anything built.

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
- **No internal AI-engine port is ever exposed to the host** — the
  isolation intent survived the mechanism change (superseded 2026-08-14);
  today it is carried by one Service behind the chart's Ingress/Route, not
  by Traefik labels.
- **Statelessness is a hard requirement for horizontal scaling to mean
  anything**: if any container silently accumulates local state, adding a
  second replica of that container produces inconsistent behavior instead
  of more capacity — the "all state in PostgreSQL" rule isn't optional
  once more than one replica of anything exists.
- Environment surface named (shared `.env`, extending cookiecutter-django's
  existing `.envs/.production/` convention): `LANGFLOW_DATABASE_URL`,
  `DBGPT_DATABASE_URL` (each with its own `search_path` schema),
  `DBGPT_SESSION_STORAGE_TYPE=db`.
- Infrastructure floor (superseded 2026-08-14): as seeded, Docker Engine +
  Compose v2+, Traefik v2.10+, Redis 6+, PostgreSQL 14+. The governing
  floor is now the infra-kinds lock — PostgreSQL + Redis + Kubernetes only.

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
- **2026-08-14** — Owner reassigned `guild` → `steward` by operator decision (2026-08-14 dream-backlog audit): Charter §5 reserves `guild` for pyforge-charter and forbids it as a terminal owner; the whole Django/Langflow/DB-GPT family lands under one deployment-owning station. Status stays `dreamt` — the family's preconditions (monolith-vs-microservices decision, dependency-solve spike, a named subject project) are unchanged.
- **2026-08-14** — **Dependency-solve spike PASSED (conda-native).** Operator-requested feasibility gate run via `micromamba create --dry-run -c conda-forge langflow dbgpt dbgpt-serve "django>=5" python=3.12`: solves cleanly — 373 packages, one environment: langflow 1.11.2 + dbgpt/dbgpt-serve 0.8.1 + django 5.2.15 agreeing on pydantic 2.13.4 / sqlalchemy 2.0.52 / fastapi 0.141.1. Both engines are now conda-forge packages this factory itself shipped (langflow-feedstock pushed 2026-08-13, db-gpt-feedstock 2026-07-22), so the co-install premise is verified-to-solve, not asserted — the monolith is a live option and neither sibling wins by default. The pair choice is now a deliberate decision awaiting the family's last precondition: a named subject project. **Python-3.14 lane (operator constraint, same day: everything must be 3.14-compatible): FAILS today** — `langflow-base` pins `bcrypt ==4.0.1` (langflow-feedstock recipe line 198, upstream's passlib-compat pin) and no py3.14 build of that bcrypt exists, while `dbgpt`+`dbgpt-serve`+`django>=5` alone solve clean on 3.14 (61 pkgs). The family's sole 3.14 blocker is that one exact pin; remedy is upstream langflow dropping the passlib-era pin or a runtime-validated feedstock loosening — tracked as a langflow-feedstock maintenance item. **Infrastructure constraint (operator, same day): core infrastructure is exactly PostgreSQL + Redis + a Kubernetes container platform (Red Hat OCP or Google GCP/GKE, Docker/Podman images) — nothing else.** This fits the family's existing shape (one PostgreSQL with public/langflow_schema/dbgpt_schema; Redis as the Celery broker; hard statelessness now mandatory since pods are ephemeral — pgvector inside the same PostgreSQL if DB-GPT needs a vector store, no separate one), and shifts the deployment mechanism from Compose/Traefik to K8s ingress/OCP routes at Spec time. It tilts the pair choice toward the microservices topology (per-service pods behind one ingress; replicas = capacity; the in-process co-location the monolith trades for is worth less when in-cluster networking is the platform norm) — the monolith stays viable only as a single-container deployment. Final pair choice still deferred to Spec intake with the named subject project.
- **2026-08-14** — **Operator architecture direction (same day, supersedes the open pair framing):** all components build on and integrate into ONE Django service — cookiecutter-django based, WITH FastAPI integration — grounded in [[django-accelerator-framework]]; the engines integrate **preferably as pluggable Django applications** ([[langflow-django-plugin]] / [[db-gpt-django-plugin]] Pattern-A shapes: ASGI mount + schema isolation), deployed on the PostgreSQL + Redis + Kubernetes platform recorded above. Scaling = replicating the whole service (statelessness mandatory); a per-engine sidecar container remains the fallback ONLY where pluggability fails (dependency or lifecycle isolation). Remaining precondition before Spec intake: naming the subject project.
- **2026-08-14** — **Subject project NAMED: [[python-agent-platform]]** (operator). The family's last precondition is met — the subject Dream and its family Spec (spec-python-agent-platform, pyforge-steward) consolidate all four same-day operator decisions plus the spike evidence; this dream's remaining role is the decision trail and its named pattern contracts.
- **2026-09-09** — **Fleet readiness pass** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, row stA / § C1). The § *What it looks like when real* routing paragraph and the two Traefik/Compose constraints were still live prose describing a mechanism this Dream's own 2026-08-14 entry retired; all three are now marked superseded with the decision trail kept. Verified against `src/platform/deploy/**`: zero Traefik references anywhere in `src/`, `scripts/` or `pixi.toml`; the shipped edge is the chart's `ingress.yaml` (one `path: /` rule to the web Service) plus the OCP overlay's `route.yaml`. Status stays `realized`; this was the clearest "realized ≠ in effect" text in the steward half of the pass.
