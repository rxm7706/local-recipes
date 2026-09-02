# Disaster recovery contract (Story 41.1)

One-page contract for the platform Helm release. Every store names RPO, RTO,
mechanism, owner and drill cadence. Standby replica or a PostgreSQL operator
(CloudNativePG, Crunchy) is a **sizing** choice documented in the Dream — not
proof of recoverability without backups.

## Stores

| Store | RPO | RTO | Mechanism | Owner | Drill cadence |
|-------|-----|-----|-----------|-------|---------------|
| **PostgreSQL** (canonical anchor) | 24 h base + continuous WAL (`archive_mode=on`) | 4 h | Helm CronJob on the platform image: `pg_basebackup` to the RWX backup PVC; WAL archived via `archive_command` to the same volume (object-store destination via steward deploy-profile is a profile plugin, not required here) | Platform SRE / release captain | Monthly: `pyforge steward restore --drill` against the latest base backup |
| **redis-broker** | Last AOF fsync (`appendfsync everysec` → ≤1 s under normal load) | 30 min | RWO PVC + AOF (`redis.broker.persistence`); rebuild Celery queues from supervisor reconciliation after broker loss | Platform SRE | Quarterly: restore broker PVC snapshot or accept queue replay from PostgreSQL `run_state` reconciliation |
| **redis-cache** | None (ephemeral) | 0 (cold) | `emptyDir`; sessions and HTMX partials re-warm on miss | Platform SRE | N/A — verify cache miss degrades gracefully |
| **media RWX** | 24 h (same cadence as Postgres file references) | 4 h | RWX PVC (`media.persistence`); copy/snapshot at storage-class layer; Wagtail metadata lives in PostgreSQL | Content ops / Platform SRE | Quarterly: restore PVC snapshot into scratch namespace; spot-check file hashes against DB references |
| **DB-GPT SQLite PVC** | 24 h | 2 h | RWO PVC (`sidecar.persistence`); sidecar metadata is re-creatable from PostgreSQL-backed datasources but conversation metadata is not | Platform SRE | Semi-annual: restore PVC snapshot; verify sidecar boots |
| **DuckDB cache** (atlas query plane) | Pipeline run (rebuild) | 2 h | Not in the platform chart — single-writer `atlas.duckdb` rebuilt by re-running the atlas ingest pipeline (BS-5); treat as derived, not authoritative | Atlas pipeline owner | Quarterly: delete cache file and re-run Phase ingest; compare row counts to PostgreSQL anchors |

## BS-8 startup reconciliation order

After any disaster that touches more than one store, reconcile in this order
(PostgreSQL is the canonical anchor; nothing upstream of a restored database
may write authoritative state first):

1. **Restore PostgreSQL** from the latest verified base backup + WAL archive
   (see [restore.md](restore.md)).
2. **Run Liquibase hook** (`liquibase update`) then **`migrate --fake`** so
   Django migration history matches the restored schema without emitting DDL.
3. **Restore redis-broker** from PVC snapshot or accept broker loss; run
   supervisor reconciliation to mark orphaned `RUNNING` rows (Story 42.4 /
   BS-8 partial).
4. **Restore media RWX** when file blobs are missing or stale; Wagtail page
   rows already came from step 1.
5. **Restore DB-GPT SQLite PVC** when sidecar-local metadata is required;
   datasource definitions remain in PostgreSQL.
6. **Rebuild DuckDB cache** by re-running atlas pipeline phases (derived
   read model only).
7. **Mason boot reconcile** — upsert index rows from PostgreSQL (+ RWX scan
   when files exist); no object-store scan (canopy AD-13 / parent AD-1).
8. **Application smoke** — `/api/health`, `/ht/`, steward `validate-fast`.

## Explicit non-goals (this contract)

- No PostgreSQL operator or second Postgres image in the default chart.
- No backup that lands only on the same PVC as live data with no second copy.
- `pg_dump` alone is not called point-in-time recovery; WAL archiving is
  required when backup is enabled.
