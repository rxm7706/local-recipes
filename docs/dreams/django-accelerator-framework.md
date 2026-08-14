---
title: A Django-service scaffolding engine, if this repo ever births new Django-based stations
type: dream
owner: mason
status: dreamt
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
