---
title: One Django service hosts the agentic engines as pluggable applications, anywhere — including air-gapped
type: dream
owner: steward
status: specified
---

# One Django service hosts the agentic engines as pluggable applications, anywhere — including air-gapped

## The Dream

A single Django service — cookiecutter-django based, FastAPI-integrated — is the control plane
for the agentic engines this factory itself packaged: Langflow and DB-GPT join it as pluggable
Django applications, not as a constellation of bespoke deployments. The whole platform needs
exactly three pieces of infrastructure — PostgreSQL, Redis, and a Kubernetes container platform
(Red Hat OCP or Google GCP/GKE, Docker/Podman images) — and it deploys identically on the open
internet and inside an air-gapped enterprise network. Scaling is replicating the service;
statelessness is mandatory, not aspirational.

## What it looks like when real

- The host service renders from the [[django-accelerator-framework]] shape: cookiecutter-django
  with FastAPI integration, `env()`-split settings, health endpoints wired to K8s probes,
  mirror endpoints parameterized at render time.
- Langflow and DB-GPT integrate per their plugin dreams' **Pattern A** ([[langflow-django-plugin]],
  [[db-gpt-django-plugin]]): ASGI mount + schema isolation — one PostgreSQL carrying
  `public` / `langflow_schema` / `dbgpt_schema` (pgvector in the same instance if DB-GPT needs a
  vector store); Redis as the Celery broker for anything that must not block Django. A
  per-engine sidecar container is the fallback ONLY where pluggability fails.
- Every dependency resolves in conda space from packages this factory shipped
  (langflow-feedstock, db-gpt-feedstock) — the co-install is *verified to solve, not asserted*
  (2026-08-14 spike: py3.12 clean, 373 pkgs).
- Python 3.14 compatibility holds end-to-end (operator constraint); today's sole blocker is
  langflow-base's `bcrypt ==4.0.1` pin — a named prerequisite, not a surprise.
- Air-gapped deployment is first-class: internal-registry images, mirrored conda/pypi indexes
  only, zero-CDN static assets, env/secret-mount credentials through the existing config seams,
  internal-CA trust — the posture [[enterprise-airgap]] established and the five enriched
  source-catalog dreams detail.

## What is real

- Both engines are live conda-forge packages this factory delivered (langflow-feedstock pushed
  2026-08-13; db-gpt-feedstock 2026-07-22).
- The feasibility spike passed (py3.12), the py3.14 blocker is isolated to one pin, and the
  topology/infra/architecture decisions are recorded with dates in the five family dreams.
- Nothing of the platform itself exists yet — no repo, no rendered host, no pluggable app.

## Constraints

- **Infrastructure is exactly** PostgreSQL + Redis + Kubernetes. A component that demands a
  fourth piece of infrastructure has failed its design review.
- Statelessness is mandatory — every container ephemeral, all state in PostgreSQL/Redis.
- Air-gap parity: any capability that only works with internet egress is incomplete.
- The strict engine-isolation rules from the plugin dreams stand: schema isolation is real
  (`search_path`), local-disk state paths are forced off, dependency footprints stay per-pattern.
- This repo's factory remains the package source; the platform consumes, it does not fork.

## Non-goals

- **Not** a re-litigation of the monolith-vs-microservices pair — the operator direction
  (2026-08-14) is pluggable-apps-in-one-service with sidecars only on pluggability failure;
  the sibling topology dreams record the full decision trail.
- **Not** a new packaging effort — the engines are already on conda-forge.
- **Not** owned by this repo's codebase: the platform is a downstream subject; this factory
  ships its packages and (via Steward) its deployment craft.

## Kinships

- [[django-accelerator-framework]] — the host's basis; its activation trigger is this platform.
- [[langflow-django-plugin]] / [[db-gpt-django-plugin]] — the pluggable-app contracts.
- [[enterprise-multi-agent-orchestration]] / [[asgi-multiplexer-monolith]] — the decided
  topology pair; their Realization logs carry the spike evidence and constraints.
- [[enterprise-airgap]] — the air-gap posture this platform inherits.

## Realization log

- **2026-08-14** — Captured and spec'd the same day (spec-python-agent-platform, pyforge-steward)
  as the named subject project the Django/Langflow/DB-GPT family was waiting for. Consolidates
  the operator's four same-day decisions: (1) core infra = PostgreSQL + Redis + K8s only;
  (2) one cookiecutter-django host with FastAPI integration based on
  [[django-accelerator-framework]]; (3) engines as pluggable Django applications, sidecars only
  on pluggability failure; (4) air-gap parity per the enriched source-catalog dreams. Feasibility:
  conda-native co-install solves on py3.12 (373 pkgs); py3.14 blocked solely by langflow-base's
  `bcrypt ==4.0.1` (langflow-feedstock maintenance item). Name chosen by the operator:
  **python-agent-platform**.
