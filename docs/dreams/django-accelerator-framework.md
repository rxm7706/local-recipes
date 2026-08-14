---
title: A Django-service scaffolding engine, if this repo ever births new Django-based stations
type: dream
owner: mason
status: specified
---

# A Django-service scaffolding engine, if this repo ever births new Django-based stations

## The Dream

The source dream's actual subject — a FreeMarker-templated, three-repo pipeline stamping out
production-ready Django services (OIDC, DRF, Celery, Helm/CD) from a continuously-maintained
sample app — solves "teams keep hand-building the same Django scaffolding." This repo has exactly
one Django-backed surface today (Steward's dashboard app, Story 9.1+), hand-built once, not
repeatedly re-scaffolded across many services. There is no current pattern of "a new Django
service is needed" recurring often enough to justify a dedicated stamping-out engine. Captured
for parity, not because a real gap exists.

## What it looks like when real

Left thin — no scoped feature, because the premise (repeated Django service scaffolding) doesn't
recur here yet:

- IF this repo ever needs a second, third, or Nth Django-backed station beyond Steward's
  dashboard, revisit whether a scaffolding engine earns its keep at that point — one hand-built
  Django app doesn't justify a templating pipeline; three or four might.
- The one concretely useful idea independent of that premise: whatever Steward's dashboard app
  already got right (OIDC-equivalent identity-at-the-boundary via `middleware.py`, the
  adopter-declaration schema in `declarations.py`) is the reference a second Django surface should
  copy from directly, not from this WF source's own FreeMarker templates.

## What is real

Nothing — this repo has one Django surface (Steward's dashboard), hand-built, no scaffolding
engine, no recurring pain from lacking one.

## Constraints

- **Not to be built until a second Django-backed station is actually planned.** One data point
  (Steward's dashboard) is not evidence of a recurring pattern.

## Non-goals

- **Not FreeMarker or a three-repo template pipeline** — no evidence this repo's own scaffolding
  needs, if they ever exist, would look like WF's specific tooling choice.
- **Not runtime application logic** — carried from the source dream's own non-goals unchanged
  (moot, but recorded for parity).

## Full feature audit against `django-accelerator-framework`

| Source feature | Disposition | Why |
|---|---|---|
| Three-repo FreeMarker template pipeline | **Omitted, no target** | No recurring Django-scaffolding need exists to justify a templating engine. |
| OIDC auth, group-based RBAC, 15-min session idle timeout | **Pattern noted, partially already-realized differently** | Steward's dashboard already solved the adjacent "identity at the boundary" problem (`middleware.py`) with its own, narrower design — not this source's OIDC-specific shape, but covering the same underlying concern for the one Django surface that exists. |
| DRF + JSON:API, FastAPI demo mount | **Omitted, no target** | Nothing currently needs a second API surface. |
| Celery + Redis, django-health-check | **Omitted, no target** | No background-job or health-check need identified beyond what Doctor's own fleet-health role already covers differently. |
| structlog/django-structlog + OpenTelemetry | **Omitted, no target** | This repo has its own structured-logging conventions already, unrelated to Django specifically. |
| pytest + behave-django, Ruff/MyPy/pre-commit | **Already this repo's own convention** | Not something to port — pytest + Ruff + pre-commit discipline already applies repo-wide, Django-backed or not. |
| Dockerfile + Helm + Harness CD | **Omitted, no target** | See [[pixi-container-image]] and [[reusable-cicd-workflows]] — no containers, no Harness. |

## Kinships

[[pyforge-steward]] (owns the one real Django surface this Dream would draw its actual local
precedent from, not the source's own FreeMarker sample app) · [[pixi-container-image]] and
[[reusable-cicd-workflows]] (siblings sharing the same "no current target" disposition) ·
[[pyforge-mason]] (nominal owner by the source label; genuinely unclaimed)

## Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Checked this repo's actual Django footprint before drafting — exactly one hand-built surface
  (Steward's dashboard, Story 9.1+), not a recurring scaffolding pain. Kept intentionally thin;
  noted that Steward's own `middleware.py`/`declarations.py` design is the real local reference a
  second Django surface should copy, not this source dream's FreeMarker tooling.
- **2026-08-14** — **Activation trigger recorded (operator direction):** the Django/Langflow/DB-GPT family is to build on a cookiecutter-django Django service WITH FastAPI integration **based on this dream** — the engines joining as pluggable Django applications ([[langflow-django-plugin]] / [[db-gpt-django-plugin]]), on PostgreSQL + Redis + Kubernetes. This is the concrete second-Django-surface signal this dream's own Constraint was waiting for, affirmed by the operator rather than inferred. Stays `dreamt` only until the family's subject project is named; at that intake this dream is the basis and should be spec'd with (not after) the family.
- **2026-08-14** — **Air-gapped realization requirements (operator, from the source original
  django-accelerator-framework.md):** the source accelerator treats the private network as ground
  truth — Artifactory coordinates are first-class template substitutions stamped into
  `pyproject.toml`, `pixi.toml`, Helm charts, CI workflows, and the conda recipe of every
  rendered service, and the pipeline publishes to Artifactory and deploys to OpenShift. The
  cookiecutter-django + FastAPI host recorded above must carry the same posture from its first
  render: (1) template renders parameterize the mirror endpoints so every pip/conda/pixi install
  in a generated service resolves from Artifactory-mirrored indexes only (pixi channels swappable
  to internal mirrors, as this repo already practices); (2) frontend assets follow the source's
  Bootstrap 5.3 + HTMX + Django Compressor shape — vendored and bundled locally, served
  WhiteNoise/`collectstatic`-style, zero CDN `<script>`/`<link>` references in base templates
  (the CAP-4 CDN-rewrite precedent from spec-atlas-query-dashboards applies at template-authoring
  time, not as a later patch); (3) all runtime config flows through the source's
  `env()`-helper/split-settings pattern — DB, Redis broker, OIDC endpoints, and secret keys via
  env/secret mounts, never committed, matching `_http.py`'s env-only enterprise routing;
  (4) auth binds to an internal OIDC IdP (the source uses PINGi via django-allauth; form login
  only in DEBUG) — no external identity callbacks; (5) deployment per the
  K8s/OCP+PostgreSQL+Redis decision: images pulled from an internal registry, `/ht/`
  django-health-check endpoints wired to K8s liveness/readiness probes, Celery's Redis broker
  in-cluster. Python 3.14 compatibility is orthogonal but constrains which mirrored package
  versions the template may pin.
- **2026-08-14** — **Subject project NAMED: [[python-agent-platform]]** (operator). The family's last precondition is met — the subject Dream and its family Spec (spec-python-agent-platform, pyforge-steward) consolidate all four same-day operator decisions plus the spike evidence; this dream's remaining role is the decision trail and its named pattern contracts.
- **2026-08-14** — Spec authored (spec-django-accelerator-framework, pyforge-mason) closing the "spec'd with the family" obligation: CAP-1 = the accelerator contract (first realization: python-agent-platform's src/platform render, Story 10.1; second reference: steward's dashboard); CAP-2 = the templating engine, explicitly parked on the dream's own third-surface trigger.
