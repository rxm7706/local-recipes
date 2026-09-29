# PostgreSQL restore runbook (Story 41.1)

Operator steps for restoring the platform PostgreSQL database from chart
backups. Pair with [DR.md](DR.md) for RPO/RTO and reconciliation order.

## Prerequisites

- A recent base backup under the backup PVC mount (default
  `/var/lib/postgresql/backup/base/<timestamp>/` on the postgres pod when
  backup is enabled).
- WAL segments under `/var/lib/postgresql/backup/wal/` when point-in-time
  recovery is required.
- The pre-created Secret (`existingSecret`) with `MIGRATION_DATABASE_URL`
  and `POSTGRES_PASSWORD`.
- `kubectl` / `oc` access to the release namespace.

## Verify backup inventory

```sh
# List base backups (platform image CronJob writes manifest.json per run)
kubectl exec -it statefulset/<release>-postgres -- \
  ls -la /var/lib/postgresql/backup/base/

kubectl exec -it statefulset/<release>-postgres -- \
  cat /var/lib/postgresql/backup/base/latest/manifest.json
```

Each `manifest.json` records `run_state_count`, `wagtail_page_count`, and
the backup timestamp — the same fields `pyforge steward restore --drill`
asserts.

## Automated restore drill (monthly)

From a checkout with steward wired:

```sh
export MIGRATION_DATABASE_URL='postgres://platform:<password>@<host>:5432/platform'
pixi run -e pyforge-steward pyforge steward restore --drill \
  --backup-path /var/lib/postgresql/backup/base/latest
```

The duty restores into a scratch database (`platform_drill_<timestamp>`),
compares row counts to the manifest, drops the scratch database, and exits
non-zero on mismatch. Crash exits use steward exit code 70 (AD-8).

## Full restore (operator — production)

**Warning:** destructive to the live data directory. Scale web/worker to zero
first.

1. Scale platform Deployments to zero replicas.
2. Delete the postgres pod (StatefulSet recreates it).
3. On the backup volume, identify the target base backup directory.
4. Replace `PGDATA` contents from the base backup (physical restore) **or**
   follow your storage-class snapshot restore procedure for the data PVC.
5. Replay WAL to the desired recovery target if PITR is needed (`recovery.signal`
   + `restore_command` — consult PostgreSQL 17 docs for your layout).
6. Start postgres; confirm `pg_isready`.
7. Run the BS-8 reconciliation order in [DR.md](DR.md) from step 2 onward.
8. Scale web/worker back up; run `pyforge steward validate-fast`.

For scratch-namespace validation before touching production, install a second
release with restored PVC clones and run the drill there first.

## Disabling backup

Set `postgres.backup.enabled: false` in Helm values. The chart renders a loud
warning in `NOTES.txt` — backup disabled is never silent. WAL archiving is
not configured when backup is disabled.
