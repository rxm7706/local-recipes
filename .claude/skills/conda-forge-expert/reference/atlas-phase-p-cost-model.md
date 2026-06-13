# Atlas Phase P — Cost Model + Operator Playbook

This reference is the single source of truth for Phase P (PyPI
download counts via BigQuery) cost claims, cap behaviour, and
recovery procedures. It supersedes the "~30 GB / within 1 TB free
tier" claims in the v8.1.0 spec and earlier docs (off by ~1000×).

When updating cost numbers, derive them from a dry-run preflight
against the live table, not from memory or copied napkin math. See
§ "Dry-run preflight" below for the procedure.

---

## TL;DR

| Mode | Window scanned | Cost estimate | Default cap |
|---|---|---|---|
| first-pull (`pypi_downloads_daily` empty) | trailing 90 d | ~$15–25 | $100 (`PHASE_P_MAX_COST_FIRST_PULL_USD`) |
| incremental refresh — monthly cadence | last ~30 d since previous run | ~$0.30–2 | $10 (`PHASE_P_MAX_COST_USD`) |
| incremental refresh — weekly cadence | last ~7 d | ~$0.07–0.40 | $10 |
| incremental refresh — daily cadence | last 1 d | ~$0.01–0.06 | $10 |
| gap > 90 days since last refresh | trailing 90 d (reverts to first-pull) | ~$15–25 | $100 |
| no new partitions since last run | 0 | $0 (BQ never queried) | n/a |

All caps are operator-overridable via the env vars listed in
§ "Tunables" below. Worst case under any combination is a
`maximum_bytes_billed`-aborted job that bills $0.

---

## Why the v8.1.0 number was wrong

The v8.1.0 PyPI intelligence spec (`docs/specs/atlas-pypi-intelligence.md`)
claimed:

> ~30 GB scanned per query, within the free tier monthly budget

This was a ~2016-era napkin number copied through the spec, code
docstring, CHANGELOG, three reference docs, and the quickref
cheatsheet without ever being re-verified against a dry-run. The 2026
empirical reality of `bigquery-public-data.pypi.file_downloads` at the
`file.project + _PARTITIONDATE` projection level is:

- **~30 GB scanned per day** (not per query). The whole table is ~1 PB
  uncompressed; daily partitions of just the two columns we touch are
  ~10–30 GB.
- **A 90-day query scans ~2.5–4 TB**, not 30 GB.
- **On-demand pricing**: $6.25/TB → **~$15–25/run typical**.
- Pre-v8.14.3 queries occasionally degraded to ~25–45 TB scans
  (~$170+/run) when planner partition-pruning faltered against the
  `CURRENT_TIMESTAMP() - INTERVAL` form.

A 2026-06-12 operator invoice of $500+ for ~3 Phase P runs against
the `--profile admin` preset surfaced the discrepancy. The v8.14.3
hot-patch added cost caps; v8.15.0 added the incremental architecture
that drives sustained refresh cost below $1/run.

**Discipline going forward**: cost claims in spec / code / docs MUST
be paired with a dry-run preflight as the source of truth, or
explicitly cite the date the dry-run was last run. Napkin numbers
without provenance are bugs.

---

## Dry-run preflight

BigQuery returns `total_bytes_processed` for free via a dry-run job
(no quota consumed, no cost billed). Phase P uses this internally
before every real query and aborts if the estimate exceeds the
operator cap. Operators can run the same preflight manually to
verify cost expectations against the current table:

```bash
# Resolve the dates Phase P will use today.
today=$(date -u +%Y-%m-%d)
d90=$(date -u -d '90 days ago' +%Y-%m-%d)

# Dry-run only; no quota consumed.
pixi run -e gcloud bq query --dry_run --use_legacy_sql=false \
  --project_id=<your-gcp-project-id> "$(cat <<EOF
SELECT
    REGEXP_REPLACE(LOWER(file.project), r'[-_.]+', '-') AS pypi_name,
    _PARTITIONDATE AS download_date,
    COUNT(*) AS downloads
FROM \`bigquery-public-data.pypi.file_downloads\`
WHERE _PARTITIONDATE >= DATE '$d90'
  AND _PARTITIONDATE <  DATE '$today'
GROUP BY pypi_name, _PARTITIONDATE
EOF
)"
```

`bq query --dry_run` prints `Total bytes processed`. Divide by
`1e12` and multiply by `$6.25` (US on-demand) to get the cost
estimate in USD. If you're on a non-US region with different
on-demand pricing, override Phase P's `PHASE_P_USD_PER_TB`.

When Phase P runs it prints the same preflight output:

```
  Phase P: PyPI download counts via BigQuery (incremental v8.15.0)
  mode=incremental; window=[2026-05-13, 2026-06-12) (30 d);
  dry-run: ~280 GB scan, est ~$1.75 (cap $10.00)
  submitting query against bigquery-public-data.pypi.file_downloads
    (maximum_bytes_billed=1,600,000,000,000, job_timeout_ms=600000)
```

The two `est` and `cap` numbers are the audit trail. If `est`
exceeds `cap` the run aborts and prints the same numbers in the
skip reason.

---

## Hard cap behaviour (`maximum_bytes_billed`)

`bigquery.QueryJobConfig(maximum_bytes_billed=N)` is a **server-side
hard ceiling**:

- If the planner estimates ≤ N bytes, the query runs normally and
  bills against actual processed bytes (not against the cap).
- If actual processed bytes would exceed N, BigQuery aborts with
  HTTP 400 `Query exceeded limit for bytes billed` and **bills $0**
  for that job.
- Operator sees a fail-fast error with `$0 charged`, not a runaway
  bill.

The dry-run preflight is a *softer* gate: it aborts the run *before*
submitting the real job, with a printable estimate. The real query
also carries `maximum_bytes_billed` as defence-in-depth in case the
planner re-estimates upward between dry-run and live run.

Both gates respect the same operator-set cap. Tuning is one env var
per mode (refresh vs first-pull).

---

## Wall-clock cap (`job_timeout_ms`)

`bigquery.QueryJobConfig(job_timeout_ms=N)` prevents zombie jobs from
accumulating slot time on flat-rate billing accounts. On-demand
billing accounts don't pay for slot time, but the timeout also
prevents pathological hung queries from running indefinitely. Default
10 minutes is generous — real queries complete in 30–60 s.

Override via `PHASE_P_JOB_TIMEOUT_MS` (milliseconds). Set higher on
slow regions where a first-pull might need 5+ minutes of wall-clock
to complete the GROUP BY.

---

## Tunables

| Env var | Default | Purpose |
|---|---|---|
| `PHASE_P_DISABLED` | (unset) | "1" → skip Phase P unconditionally |
| `PHASE_P_ENABLED` | (unset) | "1" required for opt-in; admin profile sets this automatically |
| `PHASE_P_BQ_PROJECT` | (unset) | GCP project override; defaults to ADC project |
| `PHASE_P_TTL_DAYS` | 30 | Driver-side cadence gate (monthly default) |
| `PHASE_P_RETAIN_DAYS` | 95 | GC threshold for `pypi_downloads_daily` (5d slack beyond 90d window) |
| `PHASE_P_MAX_COST_USD` | 10 | Refresh-mode cap (USD); BQ aborts above |
| `PHASE_P_MAX_COST_FIRST_PULL_USD` | 100 | First-pull cap (USD) |
| `PHASE_P_JOB_TIMEOUT_MS` | 600000 | Wall-clock cap on the real query (10 min) |
| `PHASE_P_USD_PER_TB` | 6.25 | BQ on-demand price; override for non-US regions |
| `PHASE_P_FORCE_FIRST_PULL` | (unset) | "1" wipes `pypi_downloads_daily` + forces 90-day re-bootstrap |
| `PHASE_P_BQ_WINDOW_DAYS` | DEPRECATED | Logs warning if set; ignored (v8.15.0) |

### Tuning recipes

**Tighter refresh discipline ($5 instead of $10):**

```bash
PHASE_P_MAX_COST_USD=5 pixi run -e local-recipes bootstrap-data --profile admin
```

**One-off catch-up after a missed cycle (60 days of gap, want $30):**

```bash
PHASE_P_MAX_COST_USD=30 pixi run -e local-recipes bootstrap-data --profile admin
```

**Force a clean re-bootstrap (suspect daily-table corruption):**

```bash
PHASE_P_FORCE_FIRST_PULL=1 pixi run -e local-recipes bootstrap-data --profile admin
```

**Tighter timeout on a flat-rate slot account (5 min instead of 10):**

```bash
PHASE_P_JOB_TIMEOUT_MS=300000 pixi run -e local-recipes bootstrap-data --profile admin
```

**Override for an EU multi-region project ($7.25/TB):**

```bash
PHASE_P_USD_PER_TB=7.25 pixi run -e local-recipes bootstrap-data --profile admin
```

---

## Modes — decision tree

```
                    pypi_downloads_daily empty?
                    /                          \
                 YES                            NO
                  ↓                              ↓
              first-pull            MAX(download_date) gap > 90d?
              (90-day window)        /                            \
              cap = $100           YES                            NO
                                    ↓                              ↓
                            first-pull-after-gap         incremental
                            (90-day window)              (window = last_date+1 → today)
                            cap = $100                   cap = $10
                            + warning logged             ↓
                                                      window empty?
                                                      /          \
                                                    YES          NO
                                                     ↓            ↓
                                                  no-op       submit query
                                                  (no BQ      → dry-run preflight
                                                   traffic)   → if est < cap, run
                                                              → else abort with reason
```

---

## Operator runbook

### Routine refresh (monthly)

```bash
pixi run -e local-recipes bootstrap-data --profile admin
```

Admin profile sets `PHASE_P_ENABLED=1`. Phase P:
1. Detects mode = `incremental` from `pypi_downloads_daily.MAX(download_date)`.
2. Dry-runs the query for the new days since last refresh.
3. If estimate ≤ $10, submits real query with `maximum_bytes_billed`.
4. INSERTs new rows into `pypi_downloads_daily`.
5. Recomputes `pypi_intelligence.downloads_30d/90d` via local SQL aggregation.
6. GCs rows older than 95 days.

Typical wall-clock: 30–60 s per refresh.

### Cost-spike investigation

If a Phase P run reports an unexpected cost:

1. Inspect the printed `dry-run: ~N GB scan, est ~$X` line — the
   estimate at submission time. Compare against the table size you
   expect.
2. Check `bq query --dry_run` from the operator runbook above for an
   independent estimate.
3. If estimates differ between Phase P and the manual `bq` command,
   one of the input dates is off — verify the system clock and
   `PHASE_P_FORCE_FIRST_PULL` state.
4. If estimates agree and seem high, the partition-pruning may have
   degraded. Re-run with `bq query --dry_run` and inspect the table
   sizes — `bq show --schema bigquery-public-data:pypi.file_downloads`
   for current partition statistics.

### Recovery from suspected daily-table corruption

```bash
PHASE_P_FORCE_FIRST_PULL=1 pixi run -e local-recipes bootstrap-data --profile admin
```

Costs one first-pull ($15–25 typical, capped at $100). Resets the
table to a clean trailing-90-day state.

### Air-gap operator (no BQ access)

Disable Phase P entirely; the consumer profile already does this:

```bash
pixi run -e local-recipes bootstrap-data --profile consumer
```

Existing `pypi_intelligence.downloads_30d/90d` data (last populated
when Phase P last ran) remains available for read-side CLIs and the
MCP tool. The `downloads_fetched_at` column lets consumers detect
staleness independently of the data being air-gapped.

---

## Verification against alternative sources

Phase P uses `bigquery-public-data.pypi.file_downloads` as canonical.
Operators wanting an independent cross-check have two options:

### ClickHouse `clickpy` public dataset

The ClickHouse Cloud team mirrors the BigQuery dataset to a free
public ClickHouse instance. Query via HTTPS SQL:

```bash
curl 'https://play.clickhouse.com/?user=play' --data-binary "$(cat <<'EOF'
SELECT
    project,
    countIf(date >= today() - 30) AS downloads_30d,
    countIf(date >= today() - 90) AS downloads_90d
FROM pypi.pypi_downloads
WHERE date >= today() - 90
  AND project IN ('numpy', 'pandas', 'rich')
GROUP BY project
ORDER BY downloads_90d DESC
EOF
)"
```

Reasonable for verification queries on a small slice of packages.
Not a primary because operator-trust depends on a third party we
don't control. Note: dataset name and access details may drift —
verify at https://clickpy.clickhouse.com/ before using.

### ecosyste.ms PyPI bulk export

`https://packages.ecosyste.ms/api/v1/registries/pypi.org` exposes
per-package metadata including download counts. Bulk dumps at
`https://packages.ecosyste.ms/open-data` carry monthly snapshots.

Reasonable as a v8.16.0+ fallback path for operators without BQ
credentials. `downloads_period` field semantics need verification
before substituting into Phase P's pipeline.

### Manual `bq` CLI verification

For a single package's exact daily counts:

```bash
pixi run -e gcloud bq query --use_legacy_sql=false \
  --project_id=<your-gcp-project-id> "$(cat <<'EOF'
SELECT _PARTITIONDATE AS day, COUNT(*) AS downloads
FROM `bigquery-public-data.pypi.file_downloads`
WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND _PARTITIONDATE <  CURRENT_DATE()
  AND file.project = 'numpy'
GROUP BY day
ORDER BY day DESC
EOF
)"
```

Costs ~$0.20 for a 30-day single-project query. Useful for
spot-checking the SQL aggregation against Phase P's bulk result.

---

## Storage profile

`pypi_downloads_daily` adds steady-state DB storage:

- Only rows where `downloads >= 1` are stored (zero-count days are
  implicit absence).
- ~50k–100k packages have any daily activity (the long tail is
  inactive at any given moment).
- × 90 days retention → ~5M–9M rows × ~50 bytes/row = **~225–450 MB
  steady state**.
- 95-day retention (`PHASE_P_RETAIN_DAYS` default) gives 5-day slack
  beyond the 90d window for boundary safety.

DB size delta is significant relative to a typical `cf_atlas.db`
(~200–500 MB pre-v8.15.0). Tradeoff: ~225 MB of storage in exchange
for ~$200/year saved on BQ queries.

To shrink at the cost of losing the 90-day window's precision:

```bash
PHASE_P_RETAIN_DAYS=30 pixi run -e local-recipes bootstrap-data --profile admin
```

The next aggregation cycle will produce `downloads_90d` values that
match `downloads_30d` (since only 30 days of data survive). This
trade-off is operator-tunable, not enforced.

---

## Annual cost projection

Assuming 12 refreshes per year and 1 first-pull at the start:

| Architecture | Per-run | Annual |
|---|---|---|
| Pre-v8.14.3 (no caps, lie-driven planning) | ~$170 surprise | ~$2,000+ |
| v8.14.3 hot-patch (caps on existing single-shot query) | ~$15–25 | ~$200 |
| **v8.15.0 incremental** (this doc) | ~$1 sustained, $15–25 first-pull | **~$30** |

The v8.15.0 incremental architecture is the durable fix. v8.14.3's
caps are the safety net.

---

## See also

- `docs/specs/atlas-phase-p-incremental.md` — the v8.15.0 spec.
- `docs/specs/atlas-pypi-intelligence.md` — v8.1.0 predecessor; carries
  a top-of-document erratum banner pointing here.
- `reference/atlas-phases-overview.md` § Phase P — phase-indexed
  catalog entry.
- `quickref/commands-cheatsheet.md` § Phase P run — operator quickref.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` v8.14.3 + v8.15.0
  entries — shipping notes.
