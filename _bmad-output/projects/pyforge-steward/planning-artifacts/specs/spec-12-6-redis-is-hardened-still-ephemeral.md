---
title: Redis is hardened, still ephemeral
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-12-1-the-vanilla-chart-with-an-ocp-overlay.md'
warnings: []
baseline_revision: 88be2d2e07
---

<intent-contract>

## Intent

**Problem:** Chart Redis uses emptyDir without AUTH; 12.1 deferred unauthenticated Redis hardening (spec-local-ocp-hybrid-environment CAP-3).

**Approach:** Wire Redis AUTH via `existingSecret` key into `REDIS_URL` for platform pods; add NetworkPolicy restricting Redis ingress to platform pods only. Keep persistence as emptyDir (ephemeral by design — Celery re-queues).

## Acceptance Criteria

- Given `helm template`, Redis Deployment uses password from existingSecret reference in env/REDIS_URL wiring.
- NetworkPolicy rendered restricting Redis to platform pod selectors.
- Both asserted in `test_chart_invariants.py`; suite green.
- Persistence remains emptyDir (no PVC for Redis).

## Boundaries & Constraints

**Never:** Live-cluster deploy claims. No sidecar or postgres changes (12.5 scope separate).

</intent-contract>

## Code Map

- `src/platform/deploy/charts/platform/templates/` — redis deployment, networkpolicy
- `src/platform/deploy/charts/platform/values.yaml` — redis auth secret key refs
- `src/platform/tests/test_chart_invariants.py`

## Verification

- `pixi run --frozen -e platform-dev pytest src/platform/tests/test_chart_invariants.py`
