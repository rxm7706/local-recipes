# Deploying the platform (Story 12.1)

Helm deployment for the python-agent-platform host: a **vanilla-Kubernetes
core chart** (`charts/platform/`) plus a **thin OCP overlay**
(`overlays/ocp/`) — AD-11's shape. The core chart renders only plain
Kubernetes kinds; everything OpenShift-specific lives in the overlay.
Invariants are enforced by `src/platform/tests/test_chart_invariants.py`.
Disaster recovery contract and restore runbook: `DR.md` and `restore.md`
(Story 41.1).

## Prerequisites

- **helm from the `platform-dev` pixi env** (AD-16 — never a system helm):
  every command below is `pixi run -e platform-dev helm ...` from the repo
  root. Verified against Helm v4.2.4 (conda-forge).
- The **Story 10.3 platform image** pushed somewhere the cluster can pull
  (values: `image.registry`/`image.repository` plus **`image.digest`** (preferred)
  or a pinned non-latest `image.tag` — Story 43.4 refuses `latest` and bare
  renders; CAP-6 registry relocation uses `registry` alone).
- A **pre-created Secret** (AD-12: the chart never renders a Secret and
  carries no credential defaults). Default name `platform-secrets`
  (values: `existingSecret`), keys:

  | key | value |
  |---|---|
  | `DJANGO_SECRET_KEY` | Django's `SECRET_KEY` |
  | `DATABASE_URL` | app-role DML URL, e.g. `postgres://platform_app:<password>@<release>-postgres:5432/platform` |
  | `MIGRATION_DATABASE_URL` | migration-role DDL URL for the Liquibase Job, e.g. `postgres://platform:<password>@<release>-postgres:5432/platform` (postgres Service DNS, not a pooler) |
  | `POSTGRES_PASSWORD` | the same `<password>`, consumed by the postgres container |
  | `REDIS_PASSWORD` | Redis AUTH password (Story 12.6); consumed by redis and wired into platform pods' `REDIS_URL` |

  `helm install` prints the exact in-cluster DNS names (NOTES.txt), so the
  operator composes `DATABASE_URL` from them — the chart never composes it
  (that would drag the password into the render path).

## Vanilla Kubernetes

```sh
kubectl create secret generic platform-secrets \
    --from-literal=DJANGO_SECRET_KEY=... \
    --from-literal=DATABASE_URL=postgres://platform_app:...@platform-postgres:5432/platform \
    --from-literal=MIGRATION_DATABASE_URL=postgres://platform:...@platform-postgres:5432/platform \
    --from-literal=POSTGRES_PASSWORD=... \
    --from-literal=REDIS_PASSWORD=...
pixi run -e platform-dev helm install platform src/platform/deploy/charts/platform \
    --set-file flags.tree=src/platform/config/flags.json \
    --set image.digest=sha256:<digest-from-platform-ci>
```

**Golden-path CD (Story 43.4):** Platform CI's `golden-path-promotion` job
uploads one artifact (`golden-path-promotion.json`) with the three chart
image digests and the Warden verdict for the commit. Deploy only that digest
via `.github/workflows/platform-deploy.yml` (`workflow_dispatch` with the
CI run id and digests) — the workflow refuses a digest that is not recorded
with a Warden verdict. Sidecar images use `sidecar.image.digest` and
`mcpHost.image.digest` the same way. Optional registry push:
`PLATFORM_CI_PUSH_REGISTRY=true` + `PLATFORM_CI_REGISTRY` repo variable.

Renders: web Deployment (gunicorn, probes `/api/health` liveness + `/ht/`
readiness), Celery worker Deployment (the general pool), a `worker-builds`
Deployment (the builds pool) and a single-replica `beat` Deployment (Story
42.4), one `consume-events-<station>`
Deployment per station in `events.consumers` (Story 42.3), migrate hook Job
(`post-install,pre-upgrade` — the image CMD never migrates), postgres:17
StatefulSet + PVC, redis:7 Deployment, Services, ServiceAccounts, and an
Ingress on `ingress.host` (default `platform.internal`).

**TLS:** the default values assume a TLS-terminating ingress controller —
`ingress.tls` supplies the cert blocks, and `django.secureSslRedirect:
"True"` relies on the edge sending `X-Forwarded-Proto` (production.py's
`SECURE_PROXY_SSL_HEADER`). For a bare-HTTP dev install with no TLS
terminator, set `django.secureSslRedirect: "False"` — the same switch the
compose stack flips locally.

## OpenShift

**Cluster bring-up** (CRC 2.63.0 / OpenShift 4.22.7, internal-registry image
push, keys inventory): follow
`overlays/ocp/cluster-bringup.md` end to end before installing the chart.

Two installs after the cluster is Running and the platform image is in the
internal registry (see `overlays/ocp/README.md` for detail):

```sh
pixi run -e platform-dev helm install platform src/platform/deploy/charts/platform \
    -f src/platform/deploy/overlays/ocp/core-overrides.yaml \
    --set-file flags.tree=src/platform/config/flags.json
pixi run -e platform-dev helm install platform-ocp src/platform/deploy/overlays/ocp/chart
```

The overrides turn the Ingress off and null the data services'
`runAsUser`/`fsGroup` so the `restricted-v2` SCC assigns arbitrary UIDs;
the overlay chart adds the Route. The platform-image pods carry the
`restricted-v2` contract hardcoded in the core templates (runAsNonRoot,
RuntimeDefault seccomp, no privilege escalation, drop ALL, **no fixed UID
anywhere** — the image's own `USER 1001:0` covers vanilla K8s).

## Verifying locally (no cluster)

```sh
pixi run -e platform-dev helm lint src/platform/deploy/charts/platform src/platform/deploy/overlays/ocp/chart
pixi run -e platform-dev helm template platform src/platform/deploy/charts/platform \
    --set-file flags.tree=src/platform/config/flags.json \
    --set image.digest=sha256:<digest> \
    --set sidecar.image.digest=sha256:<digest> \
    --set mcpHost.image.digest=sha256:<digest>
```

`src/platform/tests/test_chart_invariants.py` asserts the story's
invariants over parsed `helm template` output (vanilla-kinds allowlist,
Route-only overlay, restricted-v2 on the platform pods, the exact
three-image AD-1 inventory, override behavior) and skips with a
capability-naming reason where helm/PyYAML are absent.

## Honest limitations

- **OCP live-cluster verification is opt-in CI (Story 12.9), with attended
  closeout still Story 12.7.** Bring-up and internal-registry push are
  documented in `overlays/ocp/cluster-bringup.md` (Story 12.4). The optional
  `ocp-portability-smoke` job in `.github/workflows/platform-ci.yml` (default
  off; requires `CRC_PULL_SECRET` and `PLATFORM_CI_OCP_PORTABILITY_SMOKE=true`
  or workflow_dispatch) deploys core + overlay on CRC and curls through an
  admitted Route — proving SCC-assigned UIDs and the OCP edge path when enabled.
  Story 12.7 remains the attended verification for sidecar contingencies,
  postgres/redis image fallbacks, and full Tier-3 closeout. Story 12.2's
  `gke-portability-smoke` job DOES deploy this same core chart onto a real
  ephemeral `kind` cluster and curl it through a live `Ingress` +
  ingress-nginx controller — so the vanilla-K8s path is live-verified.
- **Fresh installs have a transient migration window.** On a FIRST
  install the web pods go Ready before the post-install migrate Job has
  run: the `/ht/` readiness `Database` check is connectivity-only (a bare
  `SELECT` — `config/urls.py` documents exactly this), so an unmigrated
  database still answers 200 while ORM-touching pages 500 with
  `relation "django_site" does not exist` — the same behavior
  `compose/compose.yml` documents for its stack. The window closes when
  the migrate Job completes; **upgrades are not affected** (the
  `pre-upgrade` hook runs migrations before the new pods roll out). The
  hook shape is deliberate — see the deadlock rationale in
  `charts/platform/templates/migrate-job.yaml`.
- **Redis is AUTH-protected with a NetworkPolicy (Story 12.6).** The
  pre-created Secret's `REDIS_PASSWORD` key feeds `--requirepass` on the
  redis container and is wired into platform pods' `REDIS_URL` via
  secretKeyRef + runtime env expansion. A NetworkPolicy restricts ingress
  on port 6379 to web/worker/worker-builds/beat/migrate and `consume-events-*` pods only. **redis-cache** stays
  on `emptyDir` (ephemeral, `allkeys-lru`). **redis-broker** is durable
  and bounded (Story 40.2): AOF on a dedicated RWO PVC at `/data`,
  `--maxmemory` strictly below the container memory limit, and
  `noeviction`. Clusters without a CNI that enforces NetworkPolicy get
  AUTH only, not network isolation.
- **Event delivery (Story 42.3).** `events.consumers` renders one
  `consume-events-<station>` Deployment per station
  (`manage.py consume_events --station <name>`; consumer group = station).
  A handler failure leaves the entry pending, records the (secret-redacted)
  error under `pyforge.events.lasterror:<stream_id>` (TTL = the applied-key
  TTL) and retries after 1s/2s/4s/8s (`DJANGO_PYFORGE_EVENT_BACKOFF_BASE_MS`
  / `_MAX_MS`); after `DJANGO_PYFORGE_EVENT_MAX_ATTEMPTS` (5) the event is
  written to the DLQ with `reason`, `error`, `attempts`, `group`,
  `stream_id`, `quarantined_at` and only then ACKed (`manage.py
  list_event_dlq` prints them). `harvest_poison` reclaims entries another
  consumer abandoned only once idle ≥ `DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS`
  (300s). These `DJANGO_PYFORGE_EVENT_*` knobs are process environment
  variables, not chart values. The envelope carries `traceparent`;
  `enqueue_supervised_run` forwards it as a Celery header.
- **Celery hardening and the builds pool (Story 42.4).** Delivery is
  at-least-once (`task_acks_late`, `task_reject_on_worker_lost`,
  `worker_prefetch_multiplier = 1`): a worker killed mid-task hands its
  message back and the task re-runs once; a second loss terminalises the
  run as `worker_lost` instead of looping. Queues are declared once, in
  `django_pyforge.queues`: `priority` (Doctor remedies, supervisor
  housekeeping), `default`, one per station, and `builds`. The `worker`
  Deployment consumes `worker.queues` in that order (`priority` first;
  the render refuses a list naming `builds`); `worker-builds` consumes only
  `builds` with `--time-limit worker.builds.taskTimeLimitSeconds` (4h by
  default, must exceed 300s) and a `terminationGracePeriodSeconds` derived
  as limit + `drainSlackSeconds`. The same limit is exported to every
  platform pod as `CELERY_BUILDS_TASK_TIME_LIMIT`, which sizes the broker
  visibility timeout and the supervisor's sweep. `beat` (one replica,
  Recreate) fires `prune-run-state` and `sweep-lost-runs`; the sweep marks
  a live run FAILED with reason `worker_lost` once it has been silent for
  its pool's limit and no worker reports holding its task (`manage.py
  sweep_lost_runs` runs it by hand).
- **Dead-letter retention (Story 40.2).** The `pyforge.events.dlq` stream
  is never auto-trimmed. Operators inspect it with
  `manage.py list_event_dlq` and purge deliberately, e.g.
  `redis-cli -a "$REDIS_PASSWORD" XTRIM pyforge.events.dlq MAXLEN 0` on
  the broker pod, after triage.
- **The official `postgres`/`redis` images may need image overrides under
  OCP `restricted-v2`.** Both declare a root `USER` and step down at
  runtime; under an SCC-assigned arbitrary UID they generally run, but
  hardened clusters may require UID-agnostic builds (e.g. Bitnami or Red
  Hat images) via `postgres.image`/`redis.image`. The **platform image is
  the one that passes `restricted-v2` by contract** (Story 10.3's
  arbitrary-UID design); the data-service images are documented, not
  solved, here. When swapping the postgres image, also set
  `postgres.dataMountPath` to **that image's data directory** (Bitnami
  uses `/bitnami/postgresql`, Red Hat `/var/lib/pgsql/data`) — the PVC
  mounts at `dataMountPath` and `PGDATA` derives from it, so a mismatch
  silently lands the database on the container's ephemeral filesystem
  instead of the PVC. The official **redis:7** image stores AOF/RDB under
  `/data` — the broker PVC mounts there (`redis.broker.persistence`).
- **DB-GPT sidecar (Story 12.5).** The chart renders a singleton sidecar
  Deployment (`replicas: 1`, `strategy: Recreate`), a dedicated SQLite PVC
  at `sidecar.metadataMountPath` (default
  `/app/.home/.dbgpt/workspace/pilot/meta_data`), and an internal ClusterIP
  Service. Platform web/worker pods receive `DBGPT_SIDECAR_BASE_URL` pointing
  at that Service. Override `sidecar.image` for air-gap registry relocation;
  optional `sidecar.llm.*` keys mirror compose.yml's LLM passthrough (unset
  keys fall through to the image's baked TOML defaults). LLM API keys, when
  wired, come from the same pre-created `existingSecret` via
  `sidecar.llm.apiKeySecretKey` — the chart never renders Secrets (AD-12).
- No HPA/PDB. Media is a `ReadWriteMany` PVC (Story 20.2, canopy AD-13) mounted by every
  platform Deployment (web, worker, worker-builds, beat, consume-events); on a multi-node
  cluster set `media.persistence.storageClassName` to an RWX-capable class or the claim stays
  `Pending` and nothing that mounts it schedules. Proven on CRC (`crc-csi-hostpath-provisioner`,
  single-node, 2026-08-25).
