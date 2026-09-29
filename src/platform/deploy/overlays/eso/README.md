# External Secrets Operator overlay (Story 48.4 / R-20)

Example manifests for the **enterprise secrets profile**: Vault (or
compatible) remains the system of record; [External Secrets
Operator](https://external-secrets.io/) syncs material into the
`platform-secrets` Kubernetes Secret the core chart consumes via
`secretKeyRef` (canopy:AD-12 / AD-19).

These files are **examples only** — edit Vault paths, auth, and namespaces
before apply. The core chart is unchanged; nothing here is wired into
`helm install` automatically.

## Prerequisites

1. ESO installed in the target cluster (`external-secrets` namespace is
   common; match your operator docs).
2. Vault (or compatible) reachable from the cluster with a policy granting
   read on the paths you map below.
3. A namespace for the platform release (this example uses `platform`).

## Apply order

```sh
# 1. Edit secretstore-vault.example.yaml — server URL, auth, mount
kubectl apply -f secretstore-vault.example.yaml

# 2. Edit externalsecret-platform-secrets.example.yaml — remoteRef paths
kubectl apply -f externalsecret-platform-secrets.example.yaml

# 3. Wait until the target Secret exists
kubectl -n platform get secret platform-secrets

# 4. Install the core chart (from repo root)
pixi run -e platform-dev helm install platform src/platform/deploy/charts/platform \
  --namespace platform \
  --set-file flags.tree=src/platform/config/flags.json \
  --set image.digest=sha256:<digest>
```

## Key mapping

| `platform-secrets` key | Chart consumer | Example Vault path (placeholder) |
|---|---|---|
| `DJANGO_SECRET_KEY` | web, worker, beat, consumers | `secret/data/platform/django` → `secret_key` |
| `DATABASE_URL` | web, worker, … | `secret/data/platform/postgres` → `database_url` |
| `MIGRATION_DATABASE_URL` | Liquibase migrate Job | `secret/data/platform/postgres` → `migration_database_url` |
| `POSTGRES_PASSWORD` | postgres StatefulSet | `secret/data/platform/postgres` → `password` |
| `REDIS_PASSWORD` | redis + platform pods | `secret/data/platform/redis` → `password` |
| `PYFORGE_ASSERTION_PRIVATE_KEY` | optional env (mint path) | `secret/data/platform/assertion` → `private_pem` |
| `PYFORGE_ASSERTION_PUBLIC_KEY` | optional env (verify path) | `secret/data/platform/assertion` → `public_pem` |

Rotation procedures: `src/shared/packages/pyforge-steward/docs/keys-runbook.md`.
Custody and profile comparison: `docs/explanation/enterprise-deployment.md` § 7.
