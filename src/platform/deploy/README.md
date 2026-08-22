# Deploying the platform (Story 12.1)

Helm deployment for the python-agent-platform host: a **vanilla-Kubernetes
core chart** (`charts/platform/`) plus a **thin OCP overlay**
(`overlays/ocp/`) — AD-11's shape. The core chart renders only plain
Kubernetes kinds; everything OpenShift-specific lives in the overlay.
Invariants are enforced by `src/platform/tests/test_chart_invariants.py`.

## Prerequisites

- **helm from the `platform-dev` pixi env** (AD-16 — never a system helm):
  every command below is `pixi run -e platform-dev helm ...` from the repo
  root. Verified against Helm v4.2.4 (conda-forge).
- The **Story 10.3 platform image** pushed somewhere the cluster can pull
  (values: `image.registry`/`image.repository`/`image.tag` — fully
  parameterized, so an internal mirror works with values alone, CAP-6).
- A **pre-created Secret** (AD-12: the chart never renders a Secret and
  carries no credential defaults). Default name `platform-secrets`
  (values: `existingSecret`), keys:

  | key | value |
  |---|---|
  | `DJANGO_SECRET_KEY` | Django's `SECRET_KEY` |
  | `DATABASE_URL` | the whole URL, e.g. `postgres://platform:<password>@<release>-postgres:5432/platform` |
  | `POSTGRES_PASSWORD` | the same `<password>`, consumed by the postgres container |

  `helm install` prints the exact in-cluster DNS names (NOTES.txt), so the
  operator composes `DATABASE_URL` from them — the chart never composes it
  (that would drag the password into the render path).

## Vanilla Kubernetes

```sh
kubectl create secret generic platform-secrets \
    --from-literal=DJANGO_SECRET_KEY=... \
    --from-literal=DATABASE_URL=postgres://platform:...@platform-postgres:5432/platform \
    --from-literal=POSTGRES_PASSWORD=...
pixi run -e platform-dev helm install platform src/platform/deploy/charts/platform
```

Renders: web Deployment (gunicorn, probes `/api/health` liveness + `/ht/`
readiness), Celery worker Deployment, migrate hook Job
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

Two installs (see `overlays/ocp/README.md` for detail):

```sh
pixi run -e platform-dev helm install platform src/platform/deploy/charts/platform \
    -f src/platform/deploy/overlays/ocp/core-overrides.yaml
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
pixi run -e platform-dev helm template platform src/platform/deploy/charts/platform
```

`src/platform/tests/test_chart_invariants.py` asserts the story's
invariants over parsed `helm template` output (vanilla-kinds allowlist,
Route-only overlay, restricted-v2 on the platform pods, the exact
three-image AD-1 inventory, override behavior) and skips with a
capability-naming reason where helm/PyYAML are absent.

## Honest limitations

- **No OCP live-cluster verification in this repo.** OCP-specific behavior
  (Route admission, SCC enforcement, registry/OIDC wiring) is AD-16 Tier 3 —
  attended-only. Story 12.2's `gke-portability-smoke` CI job (`.github/
  workflows/platform-ci.yml`) DOES deploy this same core chart onto a real
  ephemeral `kind` cluster and curl it through a live `Ingress` +
  ingress-nginx controller on every relevant PR/push — so the vanilla-K8s
  path is live-verified; only the OCP overlay's own resources remain
  parsed-manifest-only.
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
- **Redis is an unauthenticated in-namespace broker.** Any workload in
  the namespace (or, without a NetworkPolicy, the cluster) that can reach
  `<fullname>-redis:6379` can poison the cache and enqueue arbitrary
  Celery tasks. NetworkPolicy and Redis AUTH are explicitly out of this
  story's scope (spec Never: no NetworkPolicy) — named here as follow-up
  hardening, not solved.
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
  instead of the PVC.
- **No DB-GPT sidecar in the chart** — deliberately (the 2026-08-21
  sprint-change proposal deferred its chart membership to Epic-12
  follow-up; the AD-1 inventory here is exactly postgres + redis + the
  platform image).
- No HPA/PDB/NetworkPolicy/media PVC — out of this story's scope.
