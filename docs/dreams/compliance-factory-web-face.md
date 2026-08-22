---
title: A web face for the compliance factory — upload a manifest, watch warden and atlas analyze it
type: dream
owner: warden
status: dreamt
---

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
