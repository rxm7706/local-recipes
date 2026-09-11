---
title: Postgres and Redis become consumed, not self-hosted, matching the IdP and object-storage pattern
type: dream
owner: steward
status: specified
---

# Postgres and Redis become consumed, not self-hosted, matching the IdP and object-storage pattern

## The Dream

`spec-pyforge-unifying-strategy`'s AD-1 names the platform's infrastructure as
"exactly PostgreSQL + Redis + Kubernetes," and until 2026-09-10 treated any
fourth backing service as a failed design review. The object-storage
exception (`docs/dreams/platform-object-storage-kind.md`,
`sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md`)
authorized a narrower, specific move for a *new* kind of service: **consumed,
never self-hosted** — pyforge holds an endpoint URL and credentials only; the
operations team runs the real thing (NetApp StorageGRID). That mirrors a
pattern already trusted once before, for the identity provider
(`canopy:AD-19`: *"pod specs carry secret references only; no Vault HTTP
from the platform image. Cluster ESO/Vault stays outside the image."*).

**The question this Dream asks, seeded from a live conversation
(2026-09-11):** if "consumed, not self-hosted" is the right shape for the
IdP and now object storage, why do Postgres and Redis — the other two of
AD-1's three *always* infrastructure kinds — not get the same treatment?

**Confirmed evidence, this session, each independently verified by direct
file reads:**

1. **Postgres and Redis are self-hosted by pyforge's own Helm chart today,
   in every deployment profile that exists, including the "enterprise" one.**
   `src/platform/deploy/charts/platform/templates/` ships
   `postgres-statefulset.yaml`, `postgres-backup-cronjob.yaml`,
   `postgres-backup-pvc.yaml`, `postgres-service.yaml`,
   `redis-deployment.yaml`, `redis-service.yaml`, `redis-broker-pvc.yaml` —
   pyforge's own chart deploys, patches, backs up, and is operationally
   responsible for both. Compare `pap:CAP-6`'s own admission language:
   *"third-party images (`postgres:17`, `redis:7`) under the internal-registry
   rule"* — the *image* is upstream, but pyforge is still the *operator*.
2. **The one existing "enterprise" overlay (OCP) does not change this.**
   `src/platform/deploy/overlays/ocp/core-overrides.yaml` (Story 12.1) only
   nulls `runAsUser`/`fsGroup` so the *same* self-hosted `postgres`/`redis`
   StatefulSet/Deployment pass OpenShift's `restricted-v2` admission policy.
   It does not switch to an externally-provided Enterprise Postgres/Redis.
   Kubernetes-as-substrate is enterprise-provided (OCP); the two stateful
   services running on top of it are not.
3. **The application already consumes both exactly the way it would consume
   an external service.** `src/platform/config/settings/base.py` reads
   `DATABASE_URL` and `REDIS_URL`/`REDIS_BROKER_URL`/`REDIS_CACHE_URL` via
   `env()` (django-environ) — an endpoint-and-credential seam, identical in
   shape to `canopy:AD-19`'s IdP pattern and the new object-storage S3
   client seam (`src/platform/config/object_storage.py`). Nothing at the
   application layer distinguishes "pyforge's own StatefulSet" from "an
   Enterprise-managed instance" — both are just a URL.

**Confirmed, operator-stated (2026-09-11): the real deployment target is all
four, Enterprise-managed.** *"When I deploy pyforge, I will have an
Enterprise Managed OCP Cluster, an Enterprise Managed PostgreSQL DB, an
Enterprise Managed Redis Instance, and an Enterprise Managed NetApp [object
storage] solution."* This is not a hypothetical symmetry argument — it is
the actual deployment shape. OCP (OpenShift Container Platform, Red Hat's
enterprise Kubernetes distribution) is self-managed by the enterprise's own
platform/ops org on infrastructure they control — on-prem, virtualized, or
cloud — not a third-party SaaS vendor; the operative distinction for this
Dream isn't "external company" but "a different org than pyforge's own
application/deployment team owns and operates it." All four backing pieces
(OCP, PostgreSQL, Redis, object storage) are provided and operated that way
in the real target environment; pyforge's job is to consume all four via
configuration, not to stand up any of them itself. (The object-storage
target is NetApp StorageGRID — internally also referred to as "HPOS" by the
operator; same target, informal name, no correction owed to the
already-merged Dream/Spec text that names it StorageGRID.)

**Refined, operator-stated (2026-09-11): the deployment topology, precisely.**
All four — Enterprise Managed PostgreSQL, Enterprise Managed Redis, the
Enterprise Managed OCP cluster, and Enterprise Managed StorageGRID — are
co-located at the same data center. Pyforge itself ships as a container
image (podman/docker) deployed into a **namespace within** that
enterprise-managed OCP cluster — pyforge is a tenant workload inside a
cluster it neither owns nor operates, not a cluster pyforge stands up
itself. From that namespace it reaches Postgres, Redis, and StorageGRID as
co-located network peers, the same shape `canopy:AD-19` already assumes for
the IdP (a namespace-scoped workload holding endpoint + credentials, never
cluster-admin-level access to anything it doesn't own).

**What this Dream asks for:** move Postgres and Redis to the same
*consumed, not self-hosted* model already proven for the IdP and object
storage — an Enterprise-managed PostgreSQL and Redis the operations team
runs, pyforge holding only connection config, the same way
`DATABASE_URL`/`REDIS_URL` already work today, minus the bundled
StatefulSet/Deployment as the *only* supported path.

## Non-goals

- **Not removing local-dev self-hosting.** Local development keeps a
  self-hosted Postgres/Redis path (matching how Silo/Garage stay locally
  self-hostable even though production consumes StorageGRID externally) —
  this Dream is about the *deployed platform's* operational model, not
  local dev ergonomics, exactly like the object-storage exception was scoped.
- **Not a unilateral removal of the bundled chart templates.** If this
  Dream is realized, the shape is additive/pluggable first (a BYO-endpoint
  overlay alongside the existing self-hosted default, mirroring the
  default-plus-alternative pattern already used for scribe's nightly-trigger
  backend and Silo/Garage) — not a breaking cutover that strands anyone
  currently relying on the bundled StatefulSet/Deployment.
- **Not reopening Kubernetes's own treatment.** Kubernetes is the substrate
  the chart deploys onto, not a backing service pyforge's chart stands up —
  a different kind of thing than Postgres/Redis/object storage, out of
  scope here.
- **Not resolving AD-1's own wording.** Whether this requires a dated
  exception (mirroring the object-storage precedent) or a rewrite of AD-1's
  "always" list itself (since Postgres/Redis are named directly, unlike
  object storage which was a genuinely new kind) is a real open question
  for whatever Spec follows this Dream, not decided here.
- **Not touching backup/DR responsibility without naming the handoff.** The
  chart's own `postgres-backup-cronjob.yaml` exists today; moving to a
  consumed model shifts backup/PITR responsibility to the ops-provided
  Enterprise instance entirely. That handoff needs to be explicit in
  whatever Spec follows, not silently assumed.

## Realization log

- **2026-09-11 (seeded from a live conversation)** — The operator, reviewing
  the object-storage exception, asked why Postgres and Redis don't get the
  same "consumed, not self-hosted" treatment already given to the IdP and
  object storage. Verified live: pyforge's own chart self-hosts both today,
  including under the one existing "enterprise" (OCP) overlay, which only
  adjusts security context rather than switching to external instances; the
  application's own `DATABASE_URL`/`REDIS_URL` consumption is already
  endpoint-and-credential shaped, identical to the IdP/object-storage
  pattern. Dream seeded rather than treated as a settled conclusion — the
  concrete "is there a real Enterprise Postgres/Redis target" confirmation
  the object-storage precedent had was still missing at this point.
- **2026-09-11 (same day, operator confirmation)** — The operator confirmed
  this is not hypothetical: the real deployment target is an Enterprise
  Managed OCP cluster, Enterprise Managed PostgreSQL, Enterprise Managed
  Redis, and Enterprise Managed NetApp object storage, all four ops-provided
  and externally operated. This resolves the Dream's own first open
  question (a confirmed real target, matching the bar the object-storage
  precedent already met) — the "not yet confirmed" caveat is retired.
  Separately clarified: "NetApp HPOS" is the operator's informal name for
  the same StorageGRID target already named in the merged object-storage
  Dream/Spec — no correction owed there.
- **2026-09-11 (processed via `bmad-correct-course`)** —
  `sprint-change-proposal-2026-09-11-ad-1-datastores-exception.md`. AD-1
  gained a second dated exception (PostgreSQL + Redis, consumed not
  self-hosted, mirroring the object-storage precedent); decomposed into
  steward Epic 51 (Stories 51.1-51.3): a BYO-external-PostgreSQL overlay, a
  BYO-external-Redis overlay, and the backup/PITR responsibility handoff.
  Existing self-hosted default preserved as a Non-goal, not removed. Status:
  dreamt → specified.
- **2026-09-11 (topology refinement, pre-approval)** — The operator refined
  the deployment topology while reviewing the proposal for approval: all
  four Enterprise-managed pieces (PostgreSQL, Redis, OCP, StorageGRID) are
  co-located at the same data center; pyforge itself ships as a
  podman/docker container into a namespace within the enterprise-managed
  OCP cluster — a tenant workload, not the cluster's owner/operator.
  Non-structural (no capability or story changes) — folded into the Dream's
  own topology paragraph and the Spec's Why section for accuracy.
