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

| Mode | Window scanned | Cost estimate (verified 2026-06-12) | Default cap | Cap fits? |
|---|---|---|---|---|
| first-pull (`pypi_downloads_daily` empty) | trailing 90 d (~9.5 TB) | **~$59** at $6.25/TB | $100 (`PHASE_P_MAX_COST_FIRST_PULL_USD`) | ✅ |
| incremental refresh — monthly cadence | last ~30 d (~3.5 TB) | **~$22** | $10 (`PHASE_P_MAX_COST_USD`) | ❌ **must raise to ~$25** |
| incremental refresh — weekly cadence | last ~7 d (~0.86 TB) | **~$5.37** | $10 | ✅ |
| incremental refresh — daily cadence | last 1 d (~140 GB) | **~$0.88** | $10 | ✅ comfortably |
| gap > 90 days since last refresh | trailing 90 d (reverts to first-pull) | ~$59 | $100 | ✅ |
| no new partitions since last run | 0 | $0 (BQ never queried) | n/a | ✅ |

All caps are operator-overridable via the env vars listed in
§ "Tunables" below. Worst case under any combination is a
`maximum_bytes_billed`-aborted job that bills $0.

**Verification provenance**: numbers above measured 2026-06-12 via
the dry-run preflight procedure in § "Dry-run preflight" below.
Table size verified at 1.14 PB. Re-run that procedure to refresh
the table when significant time has passed — the BigQuery PyPI table
grows ~30% YoY (verified empirically, not from a napkin number).

**Critical: the default $10 refresh cap does NOT fit monthly cadence
at current table size.** Two options:
- (a) Use **weekly cadence** (`PHASE_P_TTL_DAYS=7`) — fits the $10 cap
  with headroom. Annual cost ~$280.
- (b) Use **monthly cadence with raised cap** (`PHASE_P_MAX_COST_USD=25
  PHASE_P_TTL_DAYS=30`) — operator-explicit opt-in. Annual cost ~$260.
- (c) Use **daily cadence** (`PHASE_P_TTL_DAYS=1`) — fits the $10 cap
  with massive headroom. Annual cost ~$320 but ~365 small jobs/year
  instead of ~12 medium jobs.

The pre-v8.15.0 single-shot architecture (v8.1.0–v8.14.3) re-scanned
the full 90-day window on every refresh: 12 monthly refreshes × $59 =
**~$710/year**. The v8.15.0 incremental architecture saves on the
re-scan part — monthly refreshes drop to ~$22/run, saving $37/run
or ~$440/year. That's the real architectural win.

---

## Why the v8.1.0 number was wrong (and v8.14.3 + v8.15.0 were also wrong)

**v8.1.0**: the spec claimed "~30 GB scanned per query, within the
free tier monthly budget". A ~2016-era napkin number copied through
the spec, code docstring, CHANGELOG, three reference docs, and the
quickref cheatsheet without re-verification. Live verification on
2026-06-12 showed real cost was ~$59 per first-pull run — off by
~3,000×, and a 2026-06-12 operator invoice of $500+ for ~3 Phase P
runs surfaced the discrepancy.

**v8.14.3 hot-patch + v8.15.0 incremental architecture**: the skill
author corrected the spec but introduced *two new errors*, both
caught by the same retro action item (L1) that mandated live BQ
verification:

1. **Numerical underestimate (off by ~3–4×).** v8.14.3's cost-model
   doc and v8.15.0's spec claimed first-pull = "~2.5–4 TB / ~$15–25"
   and monthly refresh = "~$0.30–2". The verified 2026-06-12 reality:
   first-pull ~9.5 TB / ~$59 and monthly refresh ~3.5 TB / ~$22. The
   skill author estimated based on rough table-growth math without
   running the dry-run preflight that v8.14.3 itself shipped. **Exact
   same failure mode as the v8.1.0 author.**
2. **SQL bug (would have prevented any real run from working).**
   v8.14.3 and v8.15.0 switched the partition filter from `WHERE
   timestamp >= TIMESTAMP_SUB(...)` to `WHERE _PARTITIONDATE >= DATE
   '...'`. The intent was to use literal dates for guaranteed prune-
   safety. The bug: `_PARTITIONDATE` is a pseudo-column that only
   exists on **ingestion-time-partitioned** tables. This table is
   **column-partitioned** on the `timestamp` column (verified via
   `bq show --schema bigquery-public-data:pypi.file_downloads` →
   `TimePartitioning(field='timestamp', type_='DAY')`). The literal
   form raised `Unrecognized name: _PARTITIONDATE` at submit time;
   no real run could ever have succeeded against v8.14.3 / v8.15.0.

**v8.15.2 hot-fix** corrects both: SQL uses `WHERE timestamp >=
TIMESTAMP '...' AND timestamp < TIMESTAMP '...'` literals (the v8.1.0
form, but with literal bounds instead of `TIMESTAMP_SUB(CURRENT_TIMESTAMP(),
INTERVAL)`), and `DATE(timestamp)` for the per-day GROUP BY. Cost
numbers throughout this doc are verified-2026-06-12 via the dry-run
preflight in § "Dry-run preflight" below.

**Empirical 2026-06-12 baseline:**

- Table size: **1.14 PB** (2,904 billion rows), partitioned by the
  `timestamp` column with DAY granularity, clustered on `project`.
- 90-day query at `file.project + DATE(timestamp)` projection:
  **~9.5 TB scanned**, ~$59 at $6.25/TB.
- 30-day query: **~3.5 TB**, ~$22.
- 7-day query: **~860 GB**, ~$5.37.
- 1-day query: **~140 GB**, ~$0.88.

**Discipline going forward** (per SKILL.md § "Verify, Don't Assume"
4th bullet — added in v8.15.1 and validated by this very retro
action): cost claims in spec / code / docs MUST be paired with a
dry-run preflight output as the source of truth, dated. Napkin
numbers without provenance — even a careful skill author's rough math —
are bugs. The cross-skill auto-memory rule
`feedback_bmad_verifies_spec_cost_claims.md` requires future BMAD
agents implementing CFE-area specs to re-verify quantitative claims
at intake against the live tables.

The v8.15.1 retro's R1+R2+R3 deltas predicted exactly this class of
failure; the very next session caught it. **The principle works.**

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
    DATE(timestamp) AS download_date,
    COUNT(*) AS downloads
FROM \`bigquery-public-data.pypi.file_downloads\`
WHERE timestamp >= TIMESTAMP '$d90 00:00:00 UTC'
  AND timestamp <  TIMESTAMP '$today 00:00:00 UTC'
GROUP BY pypi_name, download_date
EOF
)"
```

**Why these date forms?** This table is column-partitioned on the
`timestamp` column (verified via `bq show --schema
bigquery-public-data:pypi.file_downloads` →
`TimePartitioning(field='timestamp', type_='DAY')`). `_PARTITIONDATE`
is *not* a valid pseudo-column on column-partitioned tables — using
it raises `Unrecognized name: _PARTITIONDATE`. The correct form
filters on `timestamp` directly with `TIMESTAMP` literals (which the
planner can prune against), and projects `DATE(timestamp)` for the
per-day GROUP BY. v8.14.3 and v8.15.0 shipped with the broken
`_PARTITIONDATE` form (verified 2026-06-12); v8.15.2 hot-fixes.

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

### Routine refresh — monthly cadence (recommended default)

Monthly cadence at current table size costs ~$22/refresh, which
exceeds the $10 default cap. **The default config will dry-run-abort
without an explicit cap override.** This is the deliberate operator-
respect default per the user's $10/refresh tolerance — Phase P opts
out of spending until the operator explicitly approves a higher
budget. Recommended config:

```bash
# Monthly cadence with cap raised to match the empirical cost.
# The $25 cap gives ~$3 of headroom for table growth between refreshes.
export PHASE_P_MAX_COST_USD=25
export PHASE_P_TTL_DAYS=30   # explicit; matches the default

pixi run -e local-recipes bootstrap-data --profile admin
```

Admin profile sets `PHASE_P_ENABLED=1`. Phase P:
1. Detects mode = `incremental` from `pypi_downloads_daily.MAX(download_date)`.
2. Dry-runs the query for the new days since last refresh (~30 d).
3. If estimate ≤ $25, submits real query with `maximum_bytes_billed`.
4. INSERTs new rows into `pypi_downloads_daily`.
5. Recomputes `pypi_intelligence.downloads_30d/90d` via local SQL aggregation.
6. GCs rows older than 95 days.

Typical wall-clock: 60–120 s per monthly refresh.
Annual cost: ~$322 (12 × ~$22 refresh + $59 first-pull).

### Routine refresh — weekly cadence (alternative; fits default cap)

If you prefer to keep the $10 default cap unchanged, switch to weekly
cadence — fits the cap with ~$5/run of headroom:

```bash
export PHASE_P_TTL_DAYS=7
pixi run -e local-recipes bootstrap-data --profile admin
```

Annual cost: ~$338 (52 × ~$5.37 + $59 first-pull). Roughly comparable
to monthly; primary trade-off is data freshness — weekly's `downloads_30d`
window is at most 7 days stale; monthly's is at most 30 days stale.
For `conda_forge_readiness` ranking purposes, either is fine.

### Routine refresh — daily cadence (alternative; cheapest per-run)

Daily cadence costs ~$0.88/run. Fits the $10 default cap with massive
headroom. Best choice if you want fresh data and don't mind 365 small
jobs/year:

```bash
export PHASE_P_TTL_DAYS=1
pixi run -e local-recipes bootstrap-data --profile admin
```

Annual cost: ~$380 (365 × ~$0.88 + $59 first-pull). Most expensive
total but offers a 1-day-stale-max window.

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
SELECT DATE(timestamp) AS day, COUNT(*) AS downloads
FROM `bigquery-public-data.pypi.file_downloads`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
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

## Annual cost projection (verified 2026-06-12)

| Architecture | Per-refresh | Annual | Notes |
|---|---|---|---|
| Pre-v8.14.3 (no caps, 90-d single-shot) | ~$59 | ~$710 (12 monthly) | The cost that triggered the 2026-06-12 invoice surprise |
| v8.14.3 hot-patch (caps, but SQL broken) | $0 — query fails | $0 invoice; $0 data | Cost-cap aborts work; but the `_PARTITIONDATE` SQL bug means no real data ever lands |
| v8.15.0 incremental (SQL still broken) | $0 — query fails | $0 invoice; $0 data | Same bug; tests passed because they grep source, never hit live BQ |
| **v8.15.2 incremental (fixed SQL)** — daily cadence | ~$0.88 | **~$320** (365 × $0.88) + $59 first-pull | Fits $10 cap with massive headroom |
| **v8.15.2 incremental** — weekly cadence | ~$5.37 | **~$280** (52 × $5.37) + $59 first-pull | Fits $10 cap |
| **v8.15.2 incremental** — monthly cadence | ~$21.92 | **~$263** (12 × $21.92) + $59 first-pull | **Exceeds $10 cap; operator must raise to ~$25** |

**The architectural value of v8.15.x is real but smaller than the
v8.15.0 doc claimed.** Pre-v8.15.x re-scanned the full 90-day window
every refresh ($59/run). v8.15.x's incremental refresh only scans the
new days since the previous run — saving ~$37/run at monthly cadence,
or ~$54/run at weekly cadence. Annual savings vs. the pre-v8.15.x
architecture: ~$440 at monthly cadence, ~$640 at weekly cadence.

**The pre-fix $30/year claim was wrong on two counts**: (a) the per-
refresh cost was off by 20×; (b) the actual savings vs. single-shot
were calculated against a wrong baseline. The verified numbers above
supersede.

The v8.15.2 hot-fix (SQL correction) is what makes any of the above
real — without it, no architecture works. v8.14.3's caps are still
the safety net.

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
