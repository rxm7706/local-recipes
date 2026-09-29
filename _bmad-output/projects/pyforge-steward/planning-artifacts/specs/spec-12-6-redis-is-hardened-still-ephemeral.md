---
title: Redis is hardened, still ephemeral
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-12-1-the-vanilla-chart-with-an-ocp-overlay.md'
warnings: []
baseline_revision: 88be2d2e07
final_revision: b33964096f7bd2d2428fac45bf9caf3f8a88423d
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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `b33964096f` (2026-08-23, "Merge pull request #644 from rxm7706/steward/12-6-redis-hardened"). Ledger row `12-6-redis-is-hardened-still-ephemeral: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `src/platform/deploy/README.md`, `src/platform/deploy/charts/platform/templates/NOTES.txt`, `src/platform/deploy/charts/platform/templates/_helpers.tpl`, `src/platform/deploy/charts/platform/templates/redis-deployment.yaml`, `src/platform/deploy/charts/platform/templates/redis-networkpolicy.yaml`, `src/platform/deploy/charts/platform/values.yaml`, `src/platform/tests/test_chart_invariants.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
