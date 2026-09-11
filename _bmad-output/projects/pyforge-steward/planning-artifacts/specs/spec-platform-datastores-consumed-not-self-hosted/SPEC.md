---
id: SPEC-platform-datastores-consumed-not-self-hosted
spec: platform-datastores-consumed-not-self-hosted
status: ready
updated: "2026-09-11"
owner-dream: docs/dreams/platform-datastores-consumed-not-self-hosted.md
covers-dreams:
  - docs/dreams/platform-datastores-consumed-not-self-hosted.md
companions: []
sources:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/sprint-change-proposal-2026-09-11-ad-1-datastores-exception.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to
> build, test, and validate. `sources:` is for traceability only — consult it for narrative
> rationale this contract intentionally omits.

# PostgreSQL and Redis become consumable, without pyforge mandating self-hosting

## Why

`spec-pyforge-unifying-strategy`'s own AD-1 names PostgreSQL, Redis, and Kubernetes as the
platform's exactly-three infrastructure kinds. The 2026-09-10 exception already proved
"consumed, not self-hosted" is the right shape for a fourth kind (object storage) when the real
target is ops-provided and externally operated — the same distinction `canopy:AD-19` already
draws for the identity provider. PostgreSQL and Redis, though named directly in AD-1 rather than
being a new kind, are self-hosted by pyforge's own Helm chart today in every profile that exists,
including the one "enterprise" (OCP) overlay — which only adjusts security context, not
operational ownership. The operator's real deployment target is an Enterprise Managed OCP
cluster, Enterprise Managed PostgreSQL, and Enterprise Managed Redis, all co-located at the same
data center — confirmed live, not hypothetical. Pyforge itself ships as a podman/docker
container into a namespace within that enterprise-managed OCP cluster: a tenant workload, not
the cluster's owner or operator, reaching Postgres/Redis/StorageGRID as co-located network peers.
Processed via `bmad-correct-course`
(`sprint-change-proposal-2026-09-11-ad-1-datastores-exception.md`), applied 2026-09-11.

## Capabilities

- **CAP-1** — The AD-1 exception itself
  - **intent:** PostgreSQL and Redis are permitted as consumed, never mandatorily self-hosted,
    backing services — endpoint/credentials as configuration, the existing self-hosted default
    preserved as a fully supported alternative.
  - **success:** `spec-pyforge-unifying-strategy/SPEC.md` carries the dated 2026-09-11 exception
    bullet under AD-1 (the second such bullet, after object storage's 2026-09-10 one); the
    existing self-hosted default is not withdrawn or deprecated. (Landed.)
  - **verified:** the dated exception bullet is live in `spec-pyforge-unifying-strategy/SPEC.md`'s
    Constraints, applied via `sprint-change-proposal-2026-09-11-ad-1-datastores-exception.md`.

- **CAP-2** — A BYO-external-PostgreSQL deployment overlay exists, additive to the self-hosted
  default
  - **intent:** Mirrors the existing OCP overlay's own additive shape
    (`src/platform/deploy/overlays/ocp/core-overrides.yaml`) — a
    `.Values.postgres.external.enabled` toggle (default `false`) that, when `true`, deploys zero
    self-hosted Postgres resources and points `DATABASE_URL`/`MIGRATION_DATABASE_URL` at an
    externally-supplied endpoint and credential secret instead.
  - **success:** with the overlay applied, `postgres-statefulset.yaml`/`postgres-service.yaml`/
    `postgres-backup-pvc.yaml` all render empty and the application's database URLs resolve to
    the external endpoint; with the overlay NOT applied, a `helm template` render is
    byte-identical to today's output. (Story 51.1.)

- **CAP-3** — A BYO-external-Redis deployment overlay exists, additive to the self-hosted default
  - **intent:** Same pattern as CAP-2 applied to Redis — a `.Values.redis.external.enabled`
    toggle; `REDIS_URL`/`REDIS_BROKER_URL`/`REDIS_CACHE_URL` point external when `true`.
  - **success:** with the overlay applied, `redis-deployment.yaml`/`redis-service.yaml`/
    `redis-broker-pvc.yaml` all render empty and the application's Redis URLs resolve to the
    external endpoint; with the overlay NOT applied, a `helm template` render is byte-identical
    to today's output. (Story 51.2.)

- **CAP-4** — The backup/PITR handoff is explicit when the BYO-PostgreSQL overlay is active
  - **intent:** `postgres-backup-cronjob.yaml` must not run a shadow backup of an instance
    pyforge doesn't own; the handoff to the enterprise's own database team must be documented,
    not silently assumed.
  - **success:** when CAP-2's overlay is active, the backup CronJob is not deployed, and
    `deploy/README.md` names the enterprise database team as the owner of backup/PITR for the
    BYO path; with the overlay NOT applied, the backup CronJob still deploys exactly as today.
    (Story 51.3.)

## Constraints

- Local dev keeps self-hosting Postgres/Redis unconditionally — this Spec is about the deployed
  platform's operational model only, not local dev ergonomics, matching object storage's own
  Silo/Garage precedent.
- The shape is additive/pluggable, never a breaking cutover — the self-hosted default must
  remain byte-identical (via `helm template` diff) when the BYO overlay is not applied, for both
  CAP-2 and CAP-3.
- Endpoint and credentials are configuration only, never hardcoded — the same
  `DATABASE_URL`/`REDIS_URL` seam already in `settings/base.py` must work unmodified whether it
  resolves to the self-hosted default or an external Enterprise instance.
- Kubernetes/OCP's own treatment is out of scope — already externally-provided via the existing
  OCP overlay, a different kind of thing than a backing service, not reopened here.

## Non-goals

- Migrating any existing feature onto the BYO overlay in this chain — the overlay exists and is
  proven; consumption is separate, future, story-by-story work, matching object storage's own
  CAP-4 precedent.
- Provisioning real Enterprise PostgreSQL/Redis credentials or endpoints — an operator/ops
  action outside this repo's scope, the same boundary the IdP's and object storage's own
  credentials already sit behind.
- Changing Kubernetes/OCP's own already-external treatment — unchanged by this chain.

## Success signal

`spec-pyforge-unifying-strategy/SPEC.md` carries the dated AD-1 datastores exception bullet
(true today). A `.Values.postgres.external.enabled`/`.Values.redis.external.enabled` toggle
each independently switches the chart between the self-hosted default and a BYO-external-
endpoint overlay, with the default path proven byte-identical when neither toggle is set. The
backup CronJob's deployment tracks the Postgres toggle, and the ownership handoff for an
external instance is named in `deploy/README.md`, not silently assumed.
