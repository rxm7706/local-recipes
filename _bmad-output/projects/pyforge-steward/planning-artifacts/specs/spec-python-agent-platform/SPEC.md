---
spec: python-agent-platform
status: draft
owner-dream: docs/dreams/python-agent-platform.md
surface:
  - "(downstream subject — no in-repo code surface; steward planning artifacts + the five family dreams are the governed surface)"
sources:
  - ../../../../../../docs/dreams/python-agent-platform.md
  - ../../../../../../docs/dreams/django-accelerator-framework.md
  - ../../../../../../docs/dreams/langflow-django-plugin.md
  - ../../../../../../docs/dreams/db-gpt-django-plugin.md
  - ../../../../../../docs/dreams/enterprise-multi-agent-orchestration.md
  - ../../../../../../docs/dreams/asgi-multiplexer-monolith.md
open_questions:
  - "Which Kubernetes platform is the first deployment target — Red Hat OCP or Google GKE? (Both must be supported; the first target sequences the Helm/route vs ingress work.)"
  - "Where does the platform's own repository live — a new sibling repo scaffolded per django-accelerator-framework, or a directory under an existing one? (Decomposition-time decision.)"
  - "bcrypt sequencing: is the py3.14 prerequisite cleared upstream (langflow drops the passlib-era pin) or via a runtime-validated feedstock loosening — and does the platform's first render wait for it or ship on py3.12 with 3.14 as a follow-up gate?"
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

## Non-goals

- **Not** a re-decision of the topology pair — enterprise-multi-agent-orchestration and
  asgi-multiplexer-monolith's Realization logs carry the closed decision trail; the monolith
  survives only as "one service" and the microservices shape only as the sidecar fallback.
- **Not** a packaging effort, a new station, or in-repo platform code — this is a downstream
  subject built from steward's deployment craft and mason's packages.
- **Not** frontend-only embedding (plugin Pattern C) or SDK-only usage (Pattern C/B) as the
  primary shape — those stay documented fallbacks in the plugin dreams.

## Success signal

A fresh render of the platform deploys onto a Kubernetes namespace carrying only PostgreSQL,
Redis, and the platform image(s) from an internal registry; Langflow and DB-GPT capabilities
are exercised through the one Django front door with state provably confined to their schemas;
the same render succeeds with egress blocked; and the environment lockfile shows every package
resolved from mirrored channels — with the py3.14 gate either green or explicitly waiting on
the named bcrypt prerequisite.

## Open Questions

- "Which Kubernetes platform is the first deployment target — Red Hat OCP or Google GKE?"
- "Where does the platform's own repository live — a new sibling repo scaffolded per
  django-accelerator-framework, or a directory under an existing one?"
- "bcrypt sequencing: upstream pin drop vs runtime-validated feedstock loosening — and does the
  first render wait for 3.14 or ship on 3.12 with 3.14 as a follow-up gate?"
