---
name: 'python-agent-platform (SPEC companion)'
type: architecture-spine
purpose: build-substrate
altitude: feature
scope: 'spec-python-agent-platform — the invariant set shared by the 11 stories of Epics 10-12 (10.1-12.3) in pyforge-steward epics.md'
status: final
created: '2026-08-14'
binds: [CAP-1, CAP-2, CAP-3, CAP-4, CAP-5, CAP-6]
companion-of: SPEC.md
sources:
  - 'SPEC.md (this dir — the canonical contract; the three 2026-08-14 operator resolutions and the Docker+Podman constraint are read-only inputs here, not re-derived)'
  - '../../epics.md §§ Epic 10-12 (the 11 consuming stories)'
  - '../../../../../../docs/dreams/python-agent-platform.md (owner Dream; Realization log carries the decision trail)'
---

# Architecture Spine — python-agent-platform (companion to SPEC.md)

This spine restates the SPEC's invariants as numbered ADs so every dev session across
Epics 10–12 binds to one stable set. It is **derived, additive, and non-normative beyond the
SPEC** — on any conflict, `SPEC.md` (and its dated resolutions) wins and this file gets
corrected. No new decisions are minted here.

## Invariants & Rules

**AD-1 — Infrastructure is exactly PostgreSQL + Redis + Kubernetes.** A component that
demands a fourth piece of infrastructure has failed its design review. pgvector rides inside
the same PostgreSQL instance (AD-5) and Redis carries both cache and Celery-broker duty —
neither is a licence for a fourth piece.

**AD-2 — The platform roots at `src/platform/` and never imports `pyforge.*`.** The
factory/platform boundary is an import rule, not a repo wall: `src/platform/` consumes the
factory's published conda packages only. A lint/test enforces the rule (story 10.1); a
`pyforge.*` import anywhere under `src/platform/` is a review-blocking finding.

**AD-3 — The host is the accelerator shape, rendered — not hand-grown.** One
cookiecutter-django service with FastAPI integration: `env()`-split settings, health
endpoints wired to K8s liveness/readiness probes, mirror endpoints (conda/pypi/registry)
parameterized at render time, static assets vendored zero-CDN. Anything the render didn't
produce joins as a Django app, never as a second service.

**AD-4 — One ASGI process; the dispatch order is fixed.** Django is the default handler;
`/api/v1/`, `/health`, and `/langflow/` forward to the mounted Langflow app; `/api/dbgpt/`
routes to the DB-GPT app with the prefix stripped. No engine gets its own server process or
public port — the one Django front door is the only public edge.

**AD-5 — Three schemas in one PostgreSQL; `search_path` by migration + connection string,
never by convention.** `public` is Django's; `langflow_schema` is provisioned by a `RunSQL`
migration and bound via the `LANGFLOW_DATABASE_URL` `search_path` suffix; `dbgpt_schema` is
provisioned by a Django data migration — Django's ORM never crosses in, and DB-GPT's Alembic
never touches `public`. If a vector store is needed, pgvector lives in this same instance.

**AD-6 — Statelessness is mandatory; any pod is disposable.** All state lives in PostgreSQL
or Redis; every engine local-disk state path is forced off (`DBGPT_SESSION_STORAGE_TYPE=db`;
no Langflow local-disk state survives); replicas = capacity. Kill-and-replace losing any
flow, session, or state is a failing test, not a bug report.

**AD-7 — Celery over Redis is the only async path.** LLM/AWEL and other long-running work
dispatches to Celery workers; workers call the engines in-process or over the internal
network — never through the public edge. Each async task's failure mode (timeout / partial
result) is named and handled up front, not discovered.

**AD-8 — One conda-space environment, lockfile-pinned; py3.12 env-scoped now, 3.14 as a
release gate.** A single `[feature.python-agent-platform]` pixi feature+env pins
`python = "3.12.*"` env-scoped (the rest of the repo stays 3.14) and carries langflow,
dbgpt, dbgpt-serve, django and all host deps in one solve; the pin flips to 3.14 the release
after the langflow-base `bcrypt ==4.0.1` prerequisite clears (release gate, not entry gate).
The lockfile must solve reproducibly from a mirror-only channel config.

**AD-9 — The factory is the package source: consume and file upstream, never fork.** Engine
fixes travel as upstream issues/PRs or as runtime-validated feedstock maintenance in this
factory (e.g., the bcrypt loosening) — never as vendored patches or forks inside
`src/platform/`.

**AD-10 — The image is the Docker∩Podman intersection: UBI-minimal, multi-stage,
rootless-clean.** One UBI-minimal multi-stage Containerfile: secrets only via the
`--mount=type=secret` form both BuildKit and `podman build --secret`/buildah honor, OCI
manifests, no Docker-only extensions. It runs rootless under an arbitrary UID (the OCP
`restricted-v2` predictor), CI builds and runs it under BOTH engines, and rootless Podman is
the reference posture.

**AD-11 — The chart core is vanilla Kubernetes; OCP is a thin Route overlay; GKE is a
profile.** The core chart holds only plain Deployment/Service/Ingress (or Gateway API)
resources — nothing OCP-specific in it; OCP specifics live in a thin overlay, and GKE runs
as a CI smoke profile, never a second implementation.

**AD-12 — Credentials enter only via env and secret mounts.** Build-time: the
`--mount=type=secret` form (AD-10); run-time: K8s Secrets surfaced through the
`env()`-split settings. No credential is committed, baked into an image layer, or read
through a bespoke config channel.

**AD-13 — Air-gap parity is a failing check, not a warning.** A build + deploy executed with
external egress blocked must succeed end-to-end — image from an internal registry, lockfile
resolved from mirror-only channels, zero CDN references in served assets. Any external
reference FAILS the check.

**AD-14 — Sidecar fallback only on demonstrated pluggability failure, Dream first.** Pattern
A (pluggable Django application) is the default for every engine; a per-engine sidecar
container is admissible only after a demonstrated dependency- or lifecycle-isolation
failure, and the deviation is recorded as a dated entry in the owner Dream *before* the
sidecar lands.

**AD-15 — Platform CI is paths-filtered; repo ripples reconcile in the causing PR.**
Platform jobs filter on `paths: [src/platform/**]` with `working-directory: src/platform`
defaults — factory and platform jobs never pay for each other; platform PRs take the
`maintenance` label; the env-count ripple (environment.yaml export, llms-full catalog,
bmad-drift baseline) reconciles in the same PR that adds or changes the env.

- **AD-16 — Local-first development on the guaranteed baseline.** The guaranteed developer
  baseline is exactly: pixi, conda-forge (or an internal Artifactory conda mirror), VS Code,
  and GitHub Copilot — on Windows the posture is WSL2. Every development dependency ships as
  a conda package through pixi: a `platform-dev` feature provisions per-user `postgresql` +
  `pgvector` + `redis-server` (verified solving together from conda-forge 2026-08-14, with
  `kubernetes-helm` + `kubernetes-client` for chart work), and the serverless dev mode is
  eager-Celery + in-memory Channels. The ONLY system-level installs permitted are the
  container engine (Podman/Docker Desktop) and the `kind` binary it hosts — everything else
  that cannot arrive via pixi is a design smell. The Copilot surface connects to the
  existing copilot-bridge lineage for dev-time assistant/LLM needs; live engine flows still
  require an env-var-pointed model endpoint (never hardcoded).

## Local development tiers (AD-16 in practice)

| Tier | Requires | Covers |
|---|---|---|
| 0 | pixi + checkout only | All factory/station work; platform app code, `manage.py check`/`runserver`, boundary lint, mocked-engine tests, eager-Celery/in-memory-Channels |
| 1 | + `platform-dev` pixi feature (per-user PG/pgvector/redis-server as local processes) | All of Epic 11: schema isolation, `search_path`, pgvector, the isolation proof suite |
| 2 | + container engine (Podman Desktop preferred) & `kind` | Story 10.3 image (rootless Podman = the OCP `restricted-v2` predictor), 11.4 replacement sim, chart work incl. the GKE-shaped kind profile and the egress-blocked air-gap check |
| 3 | a real cluster (attended) | Final OCP acceptance only: Route admission, SCC enforcement, real registry/OIDC wiring |

## Consumed by

| AD | Stories |
|---|---|
| AD-1 | 10.1, 10.3, 11.1, 11.2, 11.3, 12.1, 12.3 |
| AD-2 | 10.1, 11.1, 11.2, 11.3 |
| AD-3 | 10.1 |
| AD-4 | 10.1, 11.1, 11.2, 11.4 |
| AD-5 | 11.1, 11.2, 11.4 |
| AD-6 | 10.1, 11.1, 11.2, 11.3, 11.4, 12.1 |
| AD-7 | 11.3 |
| AD-8 | 10.2, 10.3, 10.4, 12.3 |
| AD-9 | 10.4 |
| AD-10 | 10.3, 12.1, 12.3 |
| AD-11 | 12.1, 12.2 |
| AD-12 | 10.3, 12.1, 12.3 |
| AD-13 | 10.1, 10.2, 10.3, 12.3 |
| AD-14 | 11.1, 11.2 |
| AD-15 | 10.1, 10.2, 10.3, 12.2, 12.3 |
| AD-16 | 10.2 (env), 11.1 (platform-dev feature AC), 10.3, 11.3, 11.4, 12.1, 12.2, 12.3 |
