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
- ~~Nothing of the platform itself exists yet — no `src/platform/` tree, no rendered host, no
  pluggable app.~~ *(Written 2026-08-14; **superseded 2026-09-09**, fleet readiness pass.
  `src/platform/` is a live cookiecutter-django host: Langflow on Pattern A with real
  `search_path` isolation (`config/settings/base.py:613-633`), DB-GPT on Pattern B
  (`config/asgi.py:67-85`), a Helm chart with an OCP overlay, and Epics 10–12 / 16 / 43 shipped.
  The original line is kept struck through as the record of where the Dream started — see
  § Realization log.)*

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
- **Not** a fork of the factory's engines — the platform consumes the factory's published conda
  packages only; **`src/platform/` must not import `pyforge.*` station code** as the default
  boundary rule, with the two recorded brownfield carve-outs until their owning stories land:
  `src/platform/ingest/github_projects/*` (eight `pyforge.steward.*` imports) and
  `django-atlas` portal tests (allow-listed `pyforge.steward.dashboard` imports). *(Corrected
  2026-08-14: originally "not owned by this repo's codebase"; the operator's monorepo decision
  places the platform IN this repo at `src/platform/` — the boundary survives as this import
  rule, not a repo wall. Qualified 2026-09-10, Story 48.8 — the absolute ban was knowingly
  false against live code.)*

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
- **2026-08-14** — **All three Spec open questions resolved (operator), recorded in spec-python-agent-platform:** (1) first deployment target = Red Hat OCP (strictest-superset image discipline, air-gap exercised where it is real), GKE as the CI portability profile; (2) the platform lives IN this repo at `src/platform/` per the monorepo goal — cookiecutter-django roots there, one new env-scoped pixi feature pins py3.12 until the bcrypt prerequisite clears, and the factory/platform boundary becomes an import rule (published conda packages only, never `pyforge.*`); (3) first render ships on py3.12 with the bcrypt fix running in parallel (upstream passlib-drop ask + runtime-validated langflow-feedstock loosening — upstream main re-verified today still pinning bcrypt==4.0.1) and py3.14 as a release gate. Knock-ons: reusable-cicd-workflows stays parked; pixi-container-image activates when the platform containerizes. The Spec is now decomposition-ready.
- **2026-08-21** — **DB-GPT deviates to Pattern B (sidecar), per AD-14 — and pattern selection becomes a config switch, not a fork.** Story 11-2 hit a real fastapi-pin conflict between `dbgpt-app` and `langflow-base` in the shared environment — no version satisfies both, confirmed live. Full deviation record: [[db-gpt-django-plugin]] Realization log. The "sidecars only on pluggability failure" default (line 29 above) held as designed; Langflow remains on Pattern A. Operator direction: rather than a one-off DB-GPT code path, the platform host gains a per-engine, per-pattern configuration seam (A vs. B) that any future integration reuses and that lets DB-GPT revert to Pattern A later as a config change once upstream resolves the conflict — formalized as an architecture-spine addition via `bmad-correct-course` ahead of Story 11-2's re-scoping.
- **2026-09-09 (fleet readiness pass)** — Body corrected, history kept (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, Class B row stB / § 2.3 **C7**). § *What is real* still asserted "Nothing of the platform itself exists yet — no `src/platform/` tree" in a Dream whose Spec's `surface:` **is** `src/platform/**`; the line is now struck through and dated rather than deleted. Two further staleness findings recorded here rather than edited, because they are contract-shaped and belong to the merge, not to a doc sweep: (1) § *Constraints* still narrates the py3.12 / `bcrypt ==4.0.1` gate that Story 43.6 closed — `[feature.python-agent-platform.dependencies]` pins `python = "3.14.*"` (`pixi.toml:47`); (2) § *Non-goals* states the `pyforge.*` import ban **absolutely** while live code knowingly violates it at two carve-outs — `src/platform/ingest/github_projects/` imports `pyforge.steward.{keys,sync}` at 8 sites and sits outside the import-linter's `root_packages` (`src/platform/pyproject.toml:288-289`), and `django-atlas`'s portal imports `pyforge.steward.dashboard.*` under a test allow-list (`src/platform/tests/test_station_portal_shells.py:113`). Either narrow the rule to the request path or name the two carve-outs; do not leave an absolute that live code contradicts. **Sequencing:** Story 48.8 supersedes `spec-python-agent-platform` into `spec-pyforge-unifying-strategy`, and 48.8 precedes the regeneration drill — a merge that copies text forward would carry these lines into the surviving contract, so 48.8 must be sequenced after, or explicitly include, this correction. Four sibling Specs point `absorbed-into: spec-python-agent-platform` (`spec-asgi-multiplexer-monolith`, `spec-langflow-django-plugin`, `spec-enterprise-multi-agent-orchestration`, `spec-db-gpt-django-plugin`, each at `SPEC.md:5`) and must be retargeted in the same story; `pap:` stays a live id prefix (280 citations across 60 files and four other stations, incl. `scripts/ad_citation_check.py:123-124`) — the merge moves the TEXT, never the namespace. Status unchanged.
