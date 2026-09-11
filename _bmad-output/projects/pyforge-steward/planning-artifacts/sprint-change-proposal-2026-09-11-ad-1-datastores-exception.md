---
title: Sprint Change Proposal — AD-1 datastores exception (PostgreSQL + Redis, consumed not self-hosted)
date: 2026-09-11
project: pyforge-steward
chain: pyforge-unifying-strategy
status: approved — Option B, applied 2026-09-11 in the same PR
trigger: docs/dreams/platform-datastores-consumed-not-self-hosted.md (seed Dream, 2026-09-11) — the direct follow-up the 2026-09-10 object-storage exception's own Non-goals left open (scoped to object storage only, not Postgres/Redis)
mode: batch
scope: moderate — one dated exception paragraph, one new Epic (three stories), no ledger regression
operator: Rxm7706
follows: sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md
---

# Sprint Change Proposal — AD-1 datastores exception

## 1. Issue summary

`spec-pyforge-unifying-strategy/SPEC.md`'s AD-1 Constraint: *"infrastructure is
exactly PostgreSQL + Redis + Kubernetes. A component demanding a fourth backing
service has failed its design review."* The 2026-09-10 pass
(`sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md`) authorized
object storage as a fourth, consumed-not-self-hosted kind, on the strength of one
distinction: AD-1 exists to stop the estate becoming the *operator* of a backing
service, not to forbid *consuming* an externally-operated one (the same shape
`canopy:AD-19` already trusts for the identity provider).

That pass scoped itself to object storage only. This one asks the same question
of the other two named kinds: are PostgreSQL and Redis themselves self-hosted or
consumed?

**Verified live, this session, before this proposal was drafted:**

1. `src/platform/deploy/charts/platform/templates/` ships `postgres-statefulset.yaml`,
   `postgres-backup-cronjob.yaml`, `postgres-backup-pvc.yaml`, `postgres-service.yaml`,
   `redis-deployment.yaml`, `redis-service.yaml`, `redis-broker-pvc.yaml` — pyforge's
   own chart deploys, patches, and backs up both today, in every profile that exists.
2. The one existing "enterprise" overlay (`src/platform/deploy/overlays/ocp/
   core-overrides.yaml`, Story 12.1) does not change this — it only nulls
   `runAsUser`/`fsGroup` so the *same* self-hosted StatefulSet/Deployment pass
   OpenShift's `restricted-v2` admission policy. Kubernetes-as-substrate is
   enterprise-provided there (OCP); the two stateful services running on top of it
   are not.
3. `src/platform/config/settings/base.py` already reads `DATABASE_URL` and
   `REDIS_URL`/`REDIS_BROKER_URL`/`REDIS_CACHE_URL` via `env()` — an
   endpoint-and-credential seam, identical in shape to `canopy:AD-19`'s IdP pattern
   and the object-storage exception's own S3 client seam
   (`src/platform/config/object_storage.py`).

**Operator-confirmed, not hypothetical (2026-09-11):** the real deployment target
is an Enterprise Managed OCP cluster (Red Hat OpenShift Container Platform,
self-managed by the enterprise's own platform/ops org on infrastructure they
control — not a third-party SaaS), an Enterprise Managed PostgreSQL DB, an
Enterprise Managed Redis instance, and Enterprise Managed NetApp object storage
(StorageGRID — confirmed the same target already named in the 2026-09-10
exception; "HPOS" was the operator's own informal name for it, not a different
product). All four are provided and operated by the enterprise's own org, not by
pyforge.

**Topology, precisely (operator-refined, 2026-09-11):** all four are co-located
at the same data center. Pyforge itself ships as a podman/docker container image
deployed into a **namespace within** that Enterprise-managed OCP cluster —
pyforge is a tenant workload, not the cluster's owner or operator. From that
namespace it reaches PostgreSQL, Redis, and StorageGRID as co-located network
peers, the same namespace-scoped, endpoint-and-credential shape `canopy:AD-19`
already assumes for the IdP.

## 2. Impact analysis

**Spec impact.** `spec-pyforge-unifying-strategy/SPEC.md`'s AD-1 Constraint gains a
second dated exception paragraph (§4.1 below), mirroring the 2026-09-10 technique
exactly — the "Always" sentence naming PostgreSQL + Redis + Kubernetes as the
three infrastructure kinds is not rewritten (it remains true: those are still the
three kinds); only the *operational model* for two of them is clarified as an
additive option, the same way the object-storage exception clarified consumption
for a new kind.

**Dream impact.** `docs/dreams/platform-datastores-consumed-not-self-hosted.md`
gains a Realization-log entry recording this proposal's outcome (§4.2), and its
`status` moves `dreamt` → `specified` (this proposal plus its epics decomposition
is the Spec-equivalent artifact, same technique the 2026-09-10 pass used).

**Epic/story impact.** No existing story or epic changes shape. A new Epic 51 is
minted on `pyforge-steward` (§4.3) carrying three stories: a BYO-external-endpoint
overlay for PostgreSQL, the same for Redis, and the backup/PITR responsibility
handoff the Postgres overlay creates. None touch Lane 1 media, object storage, or
any other already-shipped feature. **The existing self-hosted default (today's
only supported path) is not removed or changed by any of the three stories** —
each adds an *additional*, opt-in overlay; the bundled StatefulSet/Deployment
stays the default for local dev and for anyone not opting into the BYO overlay.

**No ledger regression.** All three new story keys mint `backlog` — nothing flips
a `done` row backward.

**Technical impact.** None yet — this proposal authorizes the exception and mints
the stories; the stories themselves do the file-level (Helm chart) work.

## 3. Recommended approach

**Direct adjustment — mint a new epic, no rollback or MVP-scope change.**
Additive to the estate: a second, narrower operational-model clarification for two
already-named infrastructure kinds, not a new kind. Effort: moderate (three
stories, each touching the Helm chart's data-service templates and values
schema). Risk: low — the consumption pattern (endpoint + credentials via config)
is already proven twice (`canopy:AD-19`'s IdP, the object-storage exception), and
the existing self-hosted default is preserved unconditionally as a Non-goal, so
no current deployment path regresses.

## 4. Detailed change proposals

### 4.1 — `spec-pyforge-unifying-strategy/SPEC.md`, AD-1 Constraint

**OLD** (the existing bullet plus the 2026-09-10 exception, both unchanged,
immediately followed by the new one):

> - **Always:** infrastructure is exactly PostgreSQL + Redis + Kubernetes. A
>   component demanding a fourth backing service has failed its design review.
>   DuckDB is a **library / query face** (in-process or an optional
>   `duckdb-server` process on the platform image), not a fourth Helm backing
>   store.
> - **Exception (dated 2026-09-10, AD-1 object storage).** [unchanged — object
>   storage's own consumed-not-self-hosted exception]

**NEW** (appended immediately after, as its own bullet):

> - **Exception (dated 2026-09-11, AD-1 datastores).** PostgreSQL and Redis —
>   two of AD-1's own three named infrastructure kinds — are permitted as
>   *consumed*, never mandatorily self-hosted, backing services, the same shape
>   already granted to the identity provider (`canopy:AD-19`) and to object
>   storage (the 2026-09-10 exception above). Production target: Enterprise
>   Managed PostgreSQL and Enterprise Managed Redis, ops-provided and externally
>   operated on the same Enterprise Managed OCP cluster that already hosts the
>   platform. This does not withdraw or deprecate the existing self-hosted
>   default — the bundled `postgres-statefulset.yaml`/`redis-deployment.yaml`
>   remain the supported path for local dev and for any deployment not opting
>   into the BYO-endpoint overlay; both paths are supported, selected by
>   configuration, never assumed. When the BYO-PostgreSQL overlay is selected,
>   `postgres-backup-cronjob.yaml` does not run against an instance pyforge does
>   not own — backup/PITR responsibility for an externally-managed PostgreSQL
>   belongs to the enterprise's own database team, named explicitly, never
>   silently assumed away.

### 4.2 — `docs/dreams/platform-datastores-consumed-not-self-hosted.md`, Realization log

Append: *"2026-09-11 — processed via `bmad-correct-course`
(`sprint-change-proposal-2026-09-11-ad-1-datastores-exception.md`). AD-1 gained a
second dated exception (PostgreSQL + Redis, consumed not self-hosted, mirroring
the object-storage precedent); decomposed into steward Epic 51 (Stories
51.1-51.3): a BYO-external-PostgreSQL overlay, a BYO-external-Redis overlay, and
the backup/PITR responsibility handoff. Existing self-hosted default preserved as
a Non-goal, not removed. Status: dreamt → specified."*

Frontmatter `status` moves `dreamt` → `specified`.

### 4.3 — New Epic 51 on `pyforge-steward`

```
## Epic 51: PostgreSQL and Redis become consumable, without pyforge mandating self-hosting

### Story 51.1: A BYO-external-PostgreSQL deployment overlay exists, additive to the self-hosted default
### Story 51.2: A BYO-external-Redis deployment overlay exists, additive to the self-hosted default
### Story 51.3: The backup/PITR handoff is explicit when the BYO-PostgreSQL overlay is active
```

Full story bodies land in `epics.md` directly (Section 5); summarized here for
the proposal record:

- **51.1**: a new Helm values overlay (mirroring the OCP overlay's own additive
  shape — a values file layered with `-f`, never a rewrite of the base chart)
  that points `DATABASE_URL`/`MIGRATION_DATABASE_URL` at an externally-supplied
  endpoint and credential secret, and conditionally disables
  `postgres-statefulset.yaml`/`postgres-service.yaml`/`postgres-backup-pvc.yaml`
  when selected. The bundled self-hosted path stays the unconditional default —
  this overlay is opt-in only.
- **51.2**: the same pattern for Redis — an overlay pointing
  `REDIS_URL`/`REDIS_BROKER_URL`/`REDIS_CACHE_URL` at an external endpoint,
  conditionally disabling `redis-deployment.yaml`/`redis-service.yaml`/
  `redis-broker-pvc.yaml` when selected, self-hosted default unchanged otherwise.
- **51.3**: when 51.1's overlay is active, `postgres-backup-cronjob.yaml` is also
  conditionally disabled (backing up an instance pyforge doesn't own is not just
  pointless but potentially wrong — it would create a shadow, unauthorized backup
  of enterprise-managed data), and `deploy/README.md` gains an explicit line
  naming the enterprise database team as the owner of backup/PITR for the BYO
  path. Not a code capability on its own so much as a documentation +
  conditional-disable pairing — kept as its own story because it is a real,
  separately-reviewable decision the Dream deliberately did not pre-decide.

## 5. Implementation handoff

**Scope: Moderate.** Developer agent(s) implement 51.1-51.3 as three separate
dispatches (matching this session's own established `marshal factory dispatch`
workflow), each on its own branch, PR to `rxm7706/local-recipes` with the
`maintenance` label (all three touch `src/platform/deploy/` and possibly
`src/platform/config/settings/`, outside `recipes/`).

Gates before each PR: `dreams-hygiene-check`, `dream-chain-check`,
`chain-completeness-check`, `spec-surface-check` (scoped re-stamp), `detectors-ci`
diffed against `main`. 51.1/51.2 additionally: a live `helm template` render of
both the default and BYO-overlay paths, confirming the default path's rendered
manifests are byte-identical to today's (the Non-goal that the self-hosted
default is unchanged is testable, not just asserted).

**Explicitly not in this proposal:** removing or deprecating the self-hosted
default in any profile; any production Enterprise PostgreSQL/Redis
credential/endpoint provisioning (an operator/ops action, out of this repo's
scope, the same boundary the IdP's and object storage's own credentials already
sit behind); Kubernetes/OCP's own treatment (already externally-provided,
unchanged by this proposal); any change to local-dev tooling (local dev keeps
self-hosting Postgres/Redis exactly as it does today).

## 6. Operator ruling

**2026-09-11 — Option B.** AD-1 gains the second dated, bounded datastores
exception; Epic 51 (Stories 51.1-51.3) is minted `backlog` on `pyforge-steward`;
the existing self-hosted default remains the supported path everywhere it is
today.

## 7. Applied (2026-09-11)

- `spec-pyforge-unifying-strategy/SPEC.md`: second dated exception bullet under
  AD-1 (§4.1).
- Dream `docs/dreams/platform-datastores-consumed-not-self-hosted.md`:
  Realization-log entry, `status: dreamt` → `specified` (§4.2).
- `epics.md`: Epic 51 minted, Stories 51.1-51.3 (§4.3).
- `sprint-status-ledger.yaml`: `51-1-...`, `51-2-...`, `51-3-...` minted
  `backlog`.
- Spec-surface baseline re-stamped scoped to the specs whose sources changed.
