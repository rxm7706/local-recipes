---
title: A web face for the compliance factory — upload a manifest, watch warden and atlas analyze it
type: dream
owner: warden
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-warden]]** on 2026-09-17 (one-chain-per-station warden fold; folded from `compliance-factory-web-face`).


# A web face for the compliance factory

## The Dream

The fleet's compliance engines are CLI-only: warden's six-axis gate, the
CycloneDX universe machinery, atlas intelligence. The dream: a service face
— upload any supported manifest (requirements/pyproject/pixi/conda), get
SBOMs + vulnerability/license/currency reports rendered from the SAME
engines, async via Celery, blobs kept out of brokers (keys-not-blobs).

## Grounding

FABRIC (millsks/django-python-generate-sbom, Apache-2.0, 2026-08-22
analysis) proves the shape in production: 8-phase Celery pipeline, derived
progress (`_phase_guard` — "no phase chooses its own number"), multi-tenant
orgs + API keys, 13-archetype × 6-format manifest corpus (folding into
warden fixtures regardless of this dream). Lower priority by design: the
engines exist; only the face is missing.

## Constraints / Non-goals

The engines stay canonical — the face calls warden/atlas, never reimplements
them (FABRIC's analyzers are NOT imported). Herald adjacency for UI. Not
multi-tenant SaaS on day one. Kin: `spec-pyforge-warden-compliance-gates`,
`package-inventory-eligibility`, cyclonedx-universe-inventory (shipped).

## Realization log

- **2026-08-22** — Seeded from the seven-repo external analysis (`f0c695758c`);
  `spec-compliance-factory-web-face` derived under pyforge-warden and decomposed into the station
  backlog the same day (`a20192dd84`). Spec status `ready`.
- **2026-09-09** — Fleet readiness pass (operator-approved batch, `fleet-readiness-decision-batch-2026-09-09.md`
  row warden-B7). Stories 8.1/8.2 read `done` and the app IS mounted —
  `django_warden_fabric` is registered through `_STATION_PORTAL_PACKAGES`
  (`src/platform/config/settings/base.py:28`), having relocated from
  `src/platform/compliance_face/` to `src/shared/packages/django-warden/` in `2394d850db`,
  with `/compliance/` a permanent redirect to `/stations/warden/`. **The host question this
  Dream left open was answered by delivery: a platform-mounted Django app, as predicted.**
  Two realization gaps found against live code, both recorded on the Spec as a residual:
  the platform env carries no `pyforge-warden` path dep (`pixi.toml`
  `[feature.python-agent-platform.dependencies]` has only `pyforge-steward`) while
  `tasks.py:97-102` lazy-imports `pyforge.warden.cli`, so the deployed image cannot reach
  the engines the face calls and every job lands `FAILED`; and `sbom_json` is hardcoded
  `"{}"` (`tasks.py:111`), half-stubbing CAP-2. The dependency fix is **steward Story 48.11**
  (steward's surface, warden's capability; it also regenerates `environment.yaml`). Spec
  moved `ready` → `in-progress`; this Dream stays `specified` — the contract exists and is
  sound, the estate has not caught up to it.
