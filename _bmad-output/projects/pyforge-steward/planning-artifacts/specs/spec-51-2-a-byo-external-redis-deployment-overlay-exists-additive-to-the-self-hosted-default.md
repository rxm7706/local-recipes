---
title: 'A BYO-external-Redis deployment overlay exists, additive to the self-hosted default'
type: 'feature'
created: '2026-09-11'
status: 'backlog'
baseline_revision: 'db1cc4bb4c8d948be1218c44827b0b219a6ba790'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** pyforge's own Helm chart unconditionally deploys a self-hosted Redis `Deployment`
(`src/platform/deploy/charts/platform/templates/redis-deployment.yaml`), its `Service`
(`redis-service.yaml`), and its broker `PersistentVolumeClaim` (`redis-broker-pvc.yaml`) in
every existing profile, the same gap Story 51.1 closes for PostgreSQL. The 2026-09-11 AD-1
datastores exception (`spec-pyforge-unifying-strategy/SPEC.md` § Constraints) permits Redis as
a consumed, not mandatorily self-hosted, backing service.

**Approach:** Same pattern as Story 51.1, applied to Redis. Add a
`.Values.redis.external.enabled` toggle (default `false`) to `values.yaml`. When `true`, the
three self-hosted Redis templates guard themselves out, and `REDIS_URL`/`REDIS_BROKER_URL`/
`REDIS_CACHE_URL` — already read via `env()` in `src/platform/config/settings/base.py:409-411`
— resolve to an externally-supplied endpoint instead of the in-cluster Redis Service. No
application-layer code changes.

## Boundaries & Constraints

**Always:**
- With the overlay NOT applied, a `helm template` render of the chart must be byte-identical
  to today's output.
- Endpoint and credentials are configuration only, never hardcoded — the same
  `REDIS_URL`/`REDIS_BROKER_URL`/`REDIS_CACHE_URL` seam in `settings/base.py` must work
  unmodified whether it resolves to the self-hosted default or an external instance.
- The new overlay lives in its own directory (`src/platform/deploy/overlays/external-redis/`),
  mirroring `overlays/ocp/`'s and Story 51.1's `overlays/external-postgres/`'s own placement
  convention.

**Never:**
- Do not touch PostgreSQL (Story 51.1's own scope), Kubernetes/OCP's own already-external
  treatment, or any already-shipped feature.
- Do not migrate any existing consumer onto the BYO overlay in this story.
- Do not provision real Enterprise Redis credentials or endpoints.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Overlay not applied | Base chart render only | `redis-deployment.yaml`/`redis-service.yaml`/`redis-broker-pvc.yaml` render exactly as today (byte-identical diff) | n/a |
| Overlay applied, `redis.external.enabled: true` | Overlay values + external endpoint | All three self-hosted Redis templates render empty; `REDIS_URL`/`REDIS_BROKER_URL`/`REDIS_CACHE_URL` resolve to the external endpoint | n/a |
| Overlay applied, `redis.external.enabled: false` (or key absent) | Overlay file present but toggle off | Identical to overlay-not-applied | n/a |

</intent-contract>

## Code Map

- `src/platform/deploy/overlays/external-redis/` — new: values overlay + `README.md`,
  mirroring `overlays/ocp/`'s own shape.
- `src/platform/deploy/charts/platform/templates/redis-deployment.yaml`, `redis-service.yaml`,
  `redis-broker-pvc.yaml` — add a `{{- if not .Values.redis.external.enabled }}` guard (or
  equivalent) around each template's content.
- `src/platform/deploy/charts/platform/values.yaml:255` (`redis:` block) — add
  `external.enabled: false` default plus a placeholder for the external endpoint field the
  overlay populates.
- `src/platform/config/settings/base.py:409-411` — read-only reference;
  `REDIS_URL`/`REDIS_BROKER_URL`/`REDIS_CACHE_URL`'s `env()` seam needs no change.

## Tasks & Acceptance

**Execution:**
- `feature` — add `redis.external.enabled` (default `false`) plus an external-endpoint field
  to `values.yaml`.
- `feature` — guard `redis-deployment.yaml`/`redis-service.yaml`/`redis-broker-pvc.yaml` on
  the new toggle.
- `feature` — author `overlays/external-redis/values.yaml` + `README.md`.

**Acceptance Criteria:**
- Given pyforge's own chart unconditionally deploys a self-hosted Redis Deployment today, when
  a new overlay is applied setting `redis.external.enabled: true` plus an externally-supplied
  endpoint, then the chart deploys zero self-hosted Redis resources and the application's
  `REDIS_URL`/`REDIS_BROKER_URL`/`REDIS_CACHE_URL` resolve to the externally-supplied endpoint
  instead.
- Given the overlay is NOT applied, when the chart is rendered, then the `helm template` output
  is byte-identical to today's.

## Verification

**Commands:**
- `helm template src/platform/deploy/charts/platform` (no overlay) — diff against the
  pre-change render; expect zero diff.
- `helm template src/platform/deploy/charts/platform -f
  src/platform/deploy/overlays/external-redis/values.yaml` — expect
  `redis-deployment.yaml`/`redis-service.yaml`/`redis-broker-pvc.yaml` to render empty and the
  Deployment's `REDIS_URL` env value to reflect the external endpoint.
