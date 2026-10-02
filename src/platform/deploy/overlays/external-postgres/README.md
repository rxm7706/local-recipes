# External PostgreSQL overlay (Story 51.1)

**Prerequisite:** an operator-managed PostgreSQL instance reachable from the
cluster and a pre-created Secret holding `DATABASE_URL` and
`MIGRATION_DATABASE_URL` for that endpoint — see `../../README.md` §
Prerequisites for the full key contract. That instance must provide the
pgvector `vector` extension: the Liquibase hook applies `pyforge-scribe:1`
(`CREATE EXTENSION IF NOT EXISTS vector`, a superuser or trusted-extension
step — see `../../../db/README.md`) on every install and upgrade, and fails
the release without it.

This overlay skips the in-cluster postgres `StatefulSet`, its `Service`s,
and the backup `PersistentVolumeClaim`. Platform pods still read
`DATABASE_URL` / `MIGRATION_DATABASE_URL` from `existingSecret` via
`secretKeyRef` — no application-layer change.

```sh
# Pre-create the Secret with external URLs, then install the core chart
# with this overlay layered on:
pixi run -e platform-dev helm install platform src/platform/deploy/charts/platform \
    -f src/platform/deploy/overlays/external-postgres/values.yaml \
    --set-file flags.tree=src/platform/config/flags.json \
    --set-file flags.overlays=src/platform/config/flag-overlays.json \
    --set flags.environment=<dev|staging|production> \
    --set image.digest=sha256:<digest-from-platform-ci>
```

With `postgres.external.enabled: false` (the chart default), applying this
file's other keys alone does not change behavior — the toggle gates the
self-hosted templates, not the overlay's mere presence.

See `../README.md` for the Secret contract and honest limitations.
Consumption by a specific enterprise deployment profile is separate future
work; this overlay exists and is proven by chart invariant tests.
