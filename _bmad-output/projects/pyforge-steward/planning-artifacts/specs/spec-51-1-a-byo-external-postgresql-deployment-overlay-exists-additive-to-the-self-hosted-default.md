---
title: 'A BYO-external-PostgreSQL deployment overlay exists, additive to the self-hosted default'
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

**Problem:** pyforge's own Helm chart (`src/platform/deploy/charts/platform/templates/`)
unconditionally deploys a self-hosted PostgreSQL `StatefulSet`
(`postgres-statefulset.yaml`), its `Service` (`postgres-service.yaml`), and its backup
`PersistentVolumeClaim` (`postgres-backup-pvc.yaml`) in every existing profile, including the
one "enterprise" overlay (`src/platform/deploy/overlays/ocp/core-overrides.yaml`), which only
nulls `runAsUser`/`fsGroup` for `restricted-v2` admission — it does not change operational
ownership. The 2026-09-11 AD-1 datastores exception (`spec-pyforge-unifying-strategy/SPEC.md`
§ Constraints) permits PostgreSQL as a consumed, not mandatorily self-hosted, backing service,
mirroring the identity provider's (`canopy:AD-19`) and object storage's own already-shipped
pattern. This story builds the BYO overlay that pattern requires.

**Approach:** Mirror the existing OCP overlay's own additive shape exactly — a values file
layered with `helm install -f`, never a rewrite of the base chart. Add a new
`.Values.postgres.external.enabled` toggle (default `false`) to `values.yaml`. When `true`,
the three self-hosted Postgres templates guard themselves out (render nothing), and
`DATABASE_URL`/`MIGRATION_DATABASE_URL` — already read via `env()` in
`src/platform/config/settings/base.py:107` — resolve to an externally-supplied endpoint and
credential Secret reference the new overlay's values file names, instead of the in-cluster
Postgres Service. No application-layer code changes: the `env()` seam already reads whatever
`DATABASE_URL` the Deployment's environment provides.

## Boundaries & Constraints

**Always:**
- With the overlay NOT applied, a `helm template` render of the chart must be byte-identical
  to today's output — the self-hosted default is unconditionally preserved, proven by a diff,
  not just assumed unaffected.
- Endpoint and credentials are configuration only (a values-supplied Secret reference), never
  hardcoded — the same `DATABASE_URL` seam in `settings/base.py` must work unmodified whether
  it resolves to the self-hosted default or the external instance.
- The new overlay lives in its own directory (`src/platform/deploy/overlays/external-postgres/`),
  mirroring the OCP overlay's own placement convention (`overlays/ocp/`) — never folded into
  the base chart's `values.yaml` defaults.

**Never:**
- Do not touch Redis, Kubernetes/OCP's own already-external treatment, or any already-shipped
  feature — scoped to Postgres only.
- Do not migrate any existing consumer onto the BYO overlay in this story — the overlay exists
  and is proven; consumption is separate, future work (per the owning Spec's Non-goals).
- Do not provision real Enterprise PostgreSQL credentials or endpoints — that is an
  operator/ops action outside this repo's scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Overlay not applied | Base chart render only | `postgres-statefulset.yaml`/`postgres-service.yaml`/`postgres-backup-pvc.yaml` render exactly as today (byte-identical diff) | n/a |
| Overlay applied, `postgres.external.enabled: true` | Overlay values + external endpoint/Secret ref | All three self-hosted Postgres templates render empty; `DATABASE_URL`/`MIGRATION_DATABASE_URL` resolve to the external endpoint | n/a |
| Overlay applied, `postgres.external.enabled: false` (or key absent) | Overlay file present but toggle off | Identical to overlay-not-applied — the toggle default, not the overlay's mere presence, gates behavior | n/a |

</intent-contract>

## Code Map

- `src/platform/deploy/overlays/external-postgres/` — new: values overlay (`values.yaml` or
  equivalent) + `README.md`, mirroring `src/platform/deploy/overlays/ocp/`'s own shape.
- `src/platform/deploy/charts/platform/templates/postgres-statefulset.yaml`,
  `postgres-service.yaml`, `postgres-backup-pvc.yaml` — add a `{{- if not
  .Values.postgres.external.enabled }}` guard (or equivalent) around each template's content.
- `src/platform/deploy/charts/platform/values.yaml:207` (`postgres:` block) — add
  `external.enabled: false` default plus placeholders for the external endpoint/Secret
  reference fields the overlay populates.
- `src/platform/config/settings/base.py:107` — read-only reference; `DATABASE_URL`'s `env()`
  seam needs no change.
- `src/platform/deploy/overlays/ocp/core-overrides.yaml`, `README.md` — read-only reference
  for the overlay pattern to mirror.

## Tasks & Acceptance

**Execution:**
- `feature` — add `postgres.external.enabled` (default `false`) plus external
  endpoint/credential-Secret-reference fields to `values.yaml`.
- `feature` — guard `postgres-statefulset.yaml`/`postgres-service.yaml`/
  `postgres-backup-pvc.yaml` on the new toggle.
- `feature` — author `overlays/external-postgres/values.yaml` + `README.md` (usage mirroring
  `overlays/ocp/README.md`'s own install-command shape).

**Acceptance Criteria:**
- Given pyforge's own chart unconditionally deploys a self-hosted PostgreSQL StatefulSet
  today, when a new overlay is applied setting `postgres.external.enabled: true` plus an
  externally-supplied endpoint and credential Secret reference, then the chart deploys zero
  self-hosted Postgres resources and the application's `DATABASE_URL`/`MIGRATION_DATABASE_URL`
  resolve to the externally-supplied endpoint instead.
- Given the overlay is NOT applied, when the chart is rendered, then the `helm template` output
  is byte-identical to today's — the self-hosted default is unconditionally preserved.

## Verification

**Commands:**
- `helm template src/platform/deploy/charts/platform` (no overlay) — diff against the
  pre-change render; expect zero diff.
- `helm template src/platform/deploy/charts/platform -f
  src/platform/deploy/overlays/external-postgres/values.yaml` — expect
  `postgres-statefulset.yaml`/`postgres-service.yaml`/`postgres-backup-pvc.yaml` to render
  empty and the Deployment's `DATABASE_URL` env value to reflect the external endpoint.
