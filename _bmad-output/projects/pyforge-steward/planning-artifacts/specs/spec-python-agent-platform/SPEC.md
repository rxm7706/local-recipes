---
spec: python-agent-platform
status: ready
owner-dream: docs/dreams/python-agent-platform.md
surface:
  - src/platform/**
  - pixi.toml
  - environment.yaml
sources:
  - ../../../../../../docs/dreams/python-agent-platform.md
  - ../../../../../../docs/dreams/django-accelerator-framework.md
  - ../../../../../../docs/dreams/langflow-django-plugin.md
  - ../../../../../../docs/dreams/db-gpt-django-plugin.md
  - ../../../../../../docs/dreams/enterprise-multi-agent-orchestration.md
  - ../../../../../../docs/dreams/asgi-multiplexer-monolith.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. The Dream and the five family dreams listed in `sources:` carry
> the decision trail (spike evidence, operator directions, air-gap mechanics) this contract
> intentionally compresses.

# python-agent-platform — one Django service hosts the agentic engines, anywhere

## Why

The Django/Langflow/DB-GPT family spent its life as four guild-then-steward dreams with every
question open. As of 2026-08-14 every input is decided and dated in their Realization logs: the
operator fixed the infrastructure (PostgreSQL + Redis + Kubernetes/OCP-or-GKE, nothing else),
the architecture (one cookiecutter-django host with FastAPI integration, based on
django-accelerator-framework; engines as pluggable Django applications, Pattern A-first,
sidecars only where pluggability fails), the compatibility bar (python 3.14 end-to-end), and
air-gap parity (mirrored indexes, internal registries, zero-CDN, secret-mount credentials).
Feasibility is verified, not asserted: the conda-native trio (langflow 1.11.2 + dbgpt/dbgpt-serve
0.8.1 + django 5.2.15) solves on py3.12 in one environment of 373 packages, from feedstocks this
factory itself shipped; the py3.14 lane is blocked by exactly one pin (langflow-base
`bcrypt ==4.0.1`). What was missing was the subject that binds the family into one buildable
thing. The operator named it: **python-agent-platform**.

## Capabilities

- **CAP-1 — The host renders from the accelerator shape.**
  - **intent:** A cookiecutter-django service with FastAPI integration is the platform's one
    control plane: `env()`-split settings, health endpoints wired to K8s liveness/readiness
    probes, mirror endpoints (conda/pypi/registry) parameterized at render time per
    django-accelerator-framework's air-gap entry, vendored zero-CDN static assets.
  - **success:** The rendered host boots against PostgreSQL + Redis with no other
    infrastructure, passes its probes on K8s, and a render pointed at internal mirrors
    produces an image with zero external-network references.
- **CAP-2 — Langflow joins as a pluggable Django application.**
  - **intent:** Pattern A of langflow-django-plugin: ASGI mount forwarding `/api/v1/`,
    `/health`, `/langflow/`; `langflow_schema` isolation made real via `RunSQL` migration +
    `LANGFLOW_DATABASE_URL` `search_path` suffix; no local-disk state.
  - **success:** Langflow flows execute through the mounted app with its tables confined to
    `langflow_schema` (verified by schema inspection), and killing/replacing the pod loses no
    state.
- **CAP-3 — DB-GPT joins as a pluggable Django application.**
  - **intent:** Pattern A of db-gpt-django-plugin: `dbgpt_schema` provisioned by Django data
    migration (Django ORM never crosses in; DB-GPT's Alembic never touches `public`),
    `DBGPT_SESSION_STORAGE_TYPE=db` + every local state path forced off, ASGI dispatcher
    routing `/api/dbgpt/`; pgvector inside the same PostgreSQL if a vector store is needed.
  - **success:** Text-to-SQL / data-chat round-trips succeed through the mount with all DB-GPT
    state in `dbgpt_schema`, and pod replacement loses no session.
- **CAP-4 — Async work never blocks Django.**
  - **intent:** Celery over Redis carries LLM/AWEL work (the plugin dreams' Pattern B/D
    element); workers call the engines in-process or over the internal network, never through
    the public edge.
  - **success:** A long-running agent task completes via the worker path while the host stays
    responsive; the task's failure mode (timeout/partial result) is named and handled.
- **CAP-5 — One environment, factory-sourced, 3.14-bound.**
  - **intent:** The platform's environment is a single conda-space solve from mirrored
    conda-forge (langflow, dbgpt, dbgpt-serve, django + host deps) — pinned, locked, and
    rendered into the container build; python 3.14 compatibility is a tracked gate with the
    bcrypt pin as its named prerequisite (open question 3 sequences it).
  - **success:** The lockfile solves reproducibly from a mirror-only channel config; the 3.14
    gate flips green the release after the bcrypt prerequisite clears.
- **CAP-6 — Air-gap parity is a test, not a hope.**
  - **intent:** Every deployment artifact resolves inside the boundary: internal-registry
    images, mirrored indexes, zero-CDN assets, env/secret-mount credentials (BuildKit
    `--mount=type=secret` at build time; K8s secrets at run time), internal-CA trust.
  - **success:** A build + deploy executed with external egress blocked succeeds end-to-end;
    any external reference is a failing check, not a warning.

## Constraints

- **Always:** infrastructure is exactly PostgreSQL + Redis + Kubernetes — a component that
  demands a fourth piece has failed its design review.
- **Always:** statelessness is mandatory; replicas = capacity; any pod is disposable.
- **Always:** schema isolation is real — three schemas in one PostgreSQL, `search_path`
  enforced by migration + connection string, never by convention.
- **Always:** the factory's feedstocks are the package source; the platform consumes and files
  issues upstream, it never forks the engines.
- **Always:** a per-engine sidecar container is admissible ONLY on demonstrated pluggability
  failure (dependency or lifecycle isolation), recorded as a dated deviation in the Dream.
- **Always:** images build and run under BOTH Docker and Podman (operator, 2026-08-14) — the
  Containerfile stays in the engines' intersection (secret mounts via the
  `--mount=type=secret` form both BuildKit and `podman build --secret`/buildah honor; OCI
  manifests; no Docker-only extensions), local compose works under both `docker compose` and
  `podman-compose`, and **rootless Podman is the reference posture** — it enforces the same
  arbitrary-UID discipline OCP's `restricted-v2` demands, so passing rootless Podman locally
  predicts passing the first deployment target. CI exercises both engines, not one.

## Non-goals

- **Not** a re-decision of the topology pair — enterprise-multi-agent-orchestration and
  asgi-multiplexer-monolith's Realization logs carry the closed decision trail; the monolith
  survives only as "one service" and the microservices shape only as the sidecar fallback.
- **Not** a packaging effort or a new station — the platform is built from steward's deployment
  craft and mason's packages. *(Corrected 2026-08-14, operator monorepo decision: the platform's
  code DOES live in this repo, at `src/platform/` — the original "no in-repo platform code"
  framing is superseded; the factory/platform boundary survives as an import rule, not a repo
  wall: `src/platform/` consumes the factory's published conda packages only and never imports
  `pyforge.*` code.)*
- **Not** frontend-only embedding (plugin Pattern C) or SDK-only usage (Pattern C/B) as the
  primary shape — those stay documented fallbacks in the plugin dreams.

## Success signal

A fresh render of the platform deploys onto a Kubernetes namespace carrying only PostgreSQL,
Redis, and the platform image(s) from an internal registry; Langflow and DB-GPT capabilities
are exercised through the one Django front door with state provably confined to their schemas;
the same render succeeds with egress blocked; and the environment lockfile shows every package
resolved from mirrored channels — with the py3.14 gate either green or explicitly waiting on
the named bcrypt prerequisite.

## Open Questions — all three resolved 2026-08-14 (operator)

- **First deployment target → Red Hat OCP; GKE is the portability check.** OCP's
  `restricted-v2` SCC discipline (arbitrary UIDs, no root) is a strict superset — an image
  passing it runs unmodified on GKE, while the reverse commonly fails; disconnected installs
  are a first-class OpenShift pattern, so CAP-6's air-gap parity is exercised where it is
  *real*; and every inherited source-org mechanic (UBI8-minimal, Artifactory mirrors, internal
  OIDC, in-cluster Kaniko) is OpenShift-shaped. The core chart stays vanilla-Kubernetes
  (Deployment/Service/Ingress or Gateway API) with a thin OCP Route overlay; GKE runs as a CI
  smoke profile, never a second implementation.
- **Repository home → THIS repo (monorepo goal), at `src/platform/`.** The cookiecutter-django
  render roots there (`src/platform/manage.py`; image build context `src/platform/`), beside
  the existing `src/shared/` (libraries) and `src/pptx/` (exports) tiers. Mitigations, all
  standing conventions: platform PRs take the `maintenance` label; platform CI filters on
  `paths: [src/platform/**]` with `working-directory` defaults; one new pixi feature+env
  `python-agent-platform` pinning `python = "3.12.*"` env-scoped (the rest of the repo stays
  3.14; flips to 3.14 when the bcrypt prerequisite clears), with the known env-count ripple
  (bmad-drift surface-changed + llms-full + environment.yaml) reconciled in the same PR that
  adds the env; this SPEC's `surface:` now governs `src/platform/`. Knock-on corrections:
  `reusable-cicd-workflows` stays parked (no second consuming repo materializes);
  `pixi-container-image` gains its first real `FROM` consumer when the platform containerizes.
- **bcrypt / py3.14 sequencing → ship the first render on py3.12 now; fix the pin in parallel;
  3.14 is a release gate, not an entry gate.** Verified 2026-08-14: langflow upstream `main`
  still pins `bcrypt==4.0.1` beside `passlib>=1.7.4`, so no free fix is coming. Two lanes run
  in parallel: (a) upstream issue/PR asking langflow to drop passlib (direct `bcrypt` or
  `pwdlib`); (b) runtime-validated loosening in this factory's own langflow-feedstock
  (`bcrypt >=4.0.1,<5`, build-number bump) whose recipe test exercises the actual
  API-key/password-hashing path under bcrypt ≥4.1 — an import check is not sufficient. The
  platform's 3.14 gate (CAP-5) flips green the release after either lane lands; dbgpt + django
  5.2.15 are already 3.14-clean.
