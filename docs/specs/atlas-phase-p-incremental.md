# Tech Spec: Atlas Phase P — Incremental BigQuery Refresh + Cost Guardrails

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> architectural refactor of one phase + one new schema table). ~12 implementation
> stories across 3 waves. Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-p-incremental.md
> ```
>
> **Per `CLAUDE.md` Rule 1**, any BMAD agent executing this spec MUST invoke
> the `conda-forge-expert` skill before touching atlas code. Per Rule 2, the
> effort closes with a CFE-skill retrospective and a `CHANGELOG.md` entry.

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only, no PRD/architecture phase) |
| Surface area | `conda-forge-expert` skill — schema v25 → v26 migration adding `pypi_downloads_daily` side table; refactor of `phase_p_pypi_downloads` to incremental refresh + dry-run preflight + hard cost cap; new env-var tunables; spec/docstring/CHANGELOG corrections to the wrong "~30 GB scan" claim |
| Scope | Replace the single-shot 90-day BigQuery aggregate query with an incremental partition-by-partition refresh that stores per-day per-package counts locally and recomputes `pypi_intelligence.downloads_30d/90d` from the local table. Adds dry-run preflight that aborts above operator-set USD cap. Adds `maximum_bytes_billed` hard cap on the live query. Preserves exact per-package counts for the full PyPI namespace (no top-N filter, no aggregator fallback). |
| Version | conda-forge-expert v8.14.x → **v8.15.0** (MINOR — additive: new schema table, new tunables, new BQ source value; existing `downloads_30d/90d` consumer surface unchanged) |
| Out of scope | Per-version download granularity (deferred to v8.16.0+ if operator demand surfaces — same Q2 deferral from `atlas-pypi-intelligence.md`); replacement of BigQuery as the source (no top-N aggregator can satisfy the full-coverage + exactness requirement); auto-provisioning of BQ credentials (operator BYO unchanged); per-platform download breakdowns (a `pypi.file_downloads.details.installer` slice — not in scope for this spec) |
| Created | 2026-06-12 |
| Predecessor | `docs/specs/atlas-pypi-intelligence.md` (v8.1.0 — introduced Phase P + `pypi_intelligence` table). This spec rewrites the Phase P implementation; the consumer table is unchanged. |
| Driver | The 2026-06-12 BigQuery invoice surprise: a recent Phase P refresh cost **$500+** against the documented "well within 1 TB free tier (~30 GB / query)" expectation. Root cause: the "~30 GB" figure is wrong by ~1000× — the real per-run scan is ~25–45 TB (~$170 / run at on-demand pricing). The spec, the code docstring, the CHANGELOG, and three reference docs all repeat the wrong number. Operator needs (a) the bleeding stopped via hard caps, and (b) the steady-state refresh cost driven below $10 / month while keeping full-namespace exactness. |

---

## Background and Context

### The problem

Phase P (`conda_forge_atlas.py:6237`) issues one query per refresh against
`bigquery-public-data.pypi.file_downloads`, aggregating the trailing 90 days
of every PyPI download event into per-project totals:

```sql
SELECT
    REGEXP_REPLACE(LOWER(file.project), r'[-_.]+', '-') AS pypi_name,
    SUM(IF(timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY), 1, 0)) AS downloads_30d,
    SUM(IF(timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY), 1, 0)) AS downloads_90d
FROM `bigquery-public-data.pypi.file_downloads`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY pypi_name
```

The query is **correct** — partition filter prunes properly, column
projection is minimal, single round-trip. The problem is volume:

- `bigquery-public-data.pypi.file_downloads` is now around **~30 GB scanned
  per day** at the `file.project + _PARTITIONDATE` projection level
  (verifiable via dry-run; exact number drifts up ~30% YoY).
- A 90-day window scans **~2.7 TB** at minimum, sometimes ~3-4 TB depending
  on packaging-event-density on the days in window.
- On-demand pricing is $6.25/TB → **~$15-25 per run** baseline.
- The "$500+ invoice" trace: ~3 runs at ~$170 each, consistent with a
  scan that the planner failed to project-prune optimally (older BQ
  planners occasionally degrade `file.project` STRUCT-field projection
  when the `WHERE` predicate references the sibling `timestamp` column).

The **spec, code docstring, CHANGELOG entry, `atlas-operations.md`,
`atlas-phases-overview.md`, and `commands-cheatsheet.md`** all claim the
query scans **~30 GB**. That figure is wrong by roughly 1000×. It traces
back to a 2016-era napkin number copied through the spec without
re-verification when v8.1.0 went to intake.

### What's been ruled out

- **pypistats.org as the source.** Rate-limited (~1 req/s soft ceiling,
  429s on bursts), and its dataset is capped to the historical top ~5 k
  packages. A 12 k-actionable backfill takes >3 hours and *still* misses
  the long tail. The full `pypi_universe` (~600 k packages) is
  intractable at that rate. Even if we filtered to the actionable slice,
  the long-tail rows would carry NULL counts, breaking Phase S's
  readiness ranking for the candidates that matter most.

- **hugovk/top-pypi-packages GitHub release JSON.** Free, fast, single
  HTTP fetch — but the published artifacts cap at top 15 k by 30-day or
  365-day downloads. Operator requirement is per-package exactness for
  *all* packages, not top-N.

- **Bucket-coded ranking instead of exact counts** (e.g., classifying
  each package into `top-100 / top-1k / top-5k / top-15k / long-tail`).
  Loses the precision needed for `conda_forge_readiness` differentials
  inside a tier, especially when triaging adjacent candidates.

- **ClickHouse `clickpy` public dataset.** Free, full-coverage, fast — but
  operator-trust dependency on a third party we don't control. Reasonable
  fallback / verification source; not a primary.

- **ecosyste.ms bulk PyPI parquet.** Pulled from BigQuery at monthly
  cadence; full PyPI namespace. Reasonable secondary, but its
  `downloads_period` semantics need verification (last-month? last-90d?
  cumulative?) before we can hot-swap it in. Tracked as a v8.16.0
  follow-up for operators who want a BQ-credentials-free path.

- **Google Cloud Storage Read API on the BQ table.** Bypasses query
  pricing, but you pay $0.011/GB storage read. ~3 TB read = $33/run for
  data we then have to aggregate locally. Worse than just running the
  query.

- **Replacing BigQuery as the source.** The operator hard-constraint is
  *full-namespace + exact counts*. Only `bigquery-public-data.pypi.file_downloads`
  satisfies both. The fix has to live in *how* we run it, not in
  *whether* we run it.

### What's available to leverage

- **The BQ table is daily-partitioned on `_PARTITIONDATE`.** Per-day
  partition cost is ~$0.06–$0.20 with column projection. A refresh that
  queries only the *new* days since the last refresh costs proportional
  to the elapsed window.
- **`pypi_intelligence` is already populated** by v8.1.0+ — the table
  shape is fine. We only need to change how the `downloads_30d/90d`
  columns get filled.
- **BigQuery's dry-run mode returns `total_bytes_processed` for free.**
  No quota consumed, no cost. Lets us print a cost estimate before
  committing.
- **`bigquery.QueryJobConfig(maximum_bytes_billed=N)` is a server-side
  hard ceiling.** If a job would scan more than N bytes, BQ aborts it
  with `400 Bytes Billed Limit Exceeded` and charges $0. This is the
  right failure mode for runaway prevention.
- **Operator cost tolerances are now known**: ≤ $10 / refresh,
  ≤ $100 / first-pull. Both are achievable.

---

## Goals

- **G1.** **Refresh cost ≤ $10 in 99% of runs.** Achieved by querying
  only the partitions that haven't been seen since the last refresh
  (typically 1–30 days depending on cadence).
- **G2.** **First-pull cost ≤ $100, typically ~$15-25.** Achieved by the
  initial 90-day scan paying the unavoidable cold-start cost once, with
  a dry-run preflight that aborts if the estimate exceeds the cap.
- **G3.** **Hard server-side cap on every BQ job** via
  `maximum_bytes_billed`. Operator-tunable; default 1.6 TB for refresh
  (~$10), 16 TB for first-pull (~$100). Job aborts and bills $0 if
  exceeded.
- **G4.** **Full per-package exactness preserved.** No top-N filter, no
  bucket coding, no aggregator fallback. Every pypi_name that appears
  in `bigquery-public-data.pypi.file_downloads` gets an exact count.
- **G5.** **Air-gap-friendly steady state.** Once the daily table is
  warm, queries against `pypi_intelligence.downloads_30d/90d` (and the
  derived `conda_forge_readiness`) work offline. Only the BQ refresh
  needs network + creds.
- **G6.** **Spec / docs / code all carry the correct cost numbers**
  after this lands. No future operator should see "~30 GB" written
  anywhere in the skill.

## Non-goals

- **NG1.** Per-version downloads. Project-level only (same Q2 deferral
  as `atlas-pypi-intelligence.md`). Per-version multiplies scan cost
  ~200×.
- **NG2.** Per-platform / per-installer / per-pyver download breakdowns.
  Those live in `file_downloads.details.*`; pulling them would expand
  scan width. Future spec if operator demand surfaces.
- **NG3.** Replacing BigQuery as the primary source. ClickHouse and
  ecosyste.ms remain documented fallback paths in `atlas-operations.md`;
  not implemented as code paths in v8.15.0.
- **NG4.** Auto-provisioning of BQ credentials. Operator BYO via
  `GOOGLE_APPLICATION_CREDENTIALS` or `gcloud auth application-default
  login` — unchanged from v8.1.0.
- **NG5.** Changing the consumer surface (`pypi_intelligence.downloads_30d`,
  `pypi_intelligence.downloads_90d`). Phase S, the `pypi-intelligence`
  CLI, and the `pypi_intelligence` MCP tool all continue to read those
  columns unchanged. New `pypi_downloads_daily` is an internal cache,
  not a public surface.
- **NG6.** Changing the default Phase P opt-in posture. Phase P remains
  opt-in via `PHASE_P_ENABLED=1`. Admin-profile activation continues
  to set it.
- **NG7.** Backfill of historical daily data from before the first run.
  We start collecting per-day data from the first incremental refresh
  forward. The first-pull scans the trailing 90 days as today.

---

## Lifecycle Expectations

- **One-time migration cost** (v25 → v26): `CREATE TABLE pypi_downloads_daily`
  + 2 indexes. < 1 second; idempotent.

- **First-pull cost** (no existing daily rows):
  - Dry-run preflight: free.
  - Real query for the trailing 90 days: ~$15–25 estimate, capped at $100.
  - Bulk INSERT into `pypi_downloads_daily`: ~5–30 s wall-clock.
  - Recompute `pypi_intelligence.downloads_30d/90d`: ~1 s pure SQL.

- **Steady-state per-refresh cost** (incremental):
  - Daily cadence (queries 1 new day): ~$0.06–0.20 / run.
  - Weekly cadence: ~$0.40–1.40 / run.
  - Monthly cadence (default; `PHASE_P_TTL_DAYS=30`): ~$2–6 / run.
  - All well below the $10 cap.
  - If the gap since last refresh exceeds 90 days, the run falls back
    to first-pull mode and dry-run-aborts unless `PHASE_P_MAX_COST_USD`
    is raised.

- **Storage delta**:
  - `pypi_downloads_daily`: only stores rows where `downloads > 0` on a
    given day. ~50 k–100 k packages have any same-day downloads;
    × 90 days × ~50 bytes/row = ~225–450 MB at steady state.
  - GC: rows older than 95 days are deleted on each refresh
    (5-day slack beyond the 90 d window for boundary safety).
  - Existing `cf_atlas.db` is typically 200–500 MB; new delta is
    significant but acceptable for the admin profile.

- **BigQuery quota**: With monthly cadence + cost caps in place, total
  annual BQ spend is bounded at:
  - First-pull: 1 × ~$25 = $25
  - 11 × monthly refresh × ~$3 = $33
  - **Annual: ~$60 (vs. $500+ in the pre-fix regime)**

---

## Design

### Schema v26

#### New: `pypi_downloads_daily`

```sql
-- Per-day per-package download counts. Source of truth for computing
-- pypi_intelligence.downloads_30d/90d via local SQL aggregation.
-- INSERT-only on Phase P refresh; GC prunes rows older than
-- PHASE_P_RETAIN_DAYS (default 95).
CREATE TABLE IF NOT EXISTS pypi_downloads_daily (
    pypi_name      TEXT NOT NULL,
    download_date  TEXT NOT NULL,    -- ISO 'YYYY-MM-DD' (SQLite has no DATE)
    downloads      INTEGER NOT NULL, -- always >= 1; zero-count rows not stored
    PRIMARY KEY (pypi_name, download_date)
);
CREATE INDEX IF NOT EXISTS idx_pypi_dl_daily_date
    ON pypi_downloads_daily(download_date);
CREATE INDEX IF NOT EXISTS idx_pypi_dl_daily_name
    ON pypi_downloads_daily(pypi_name);
```

#### Unchanged: `pypi_intelligence`

The `downloads_30d`, `downloads_90d`, `downloads_fetched_at`,
`downloads_source` columns are unchanged. The new pipeline writes to
them via aggregation queries against `pypi_downloads_daily` instead of
direct from BQ.

`downloads_source` gains a new permitted value: `'bigquery-incremental'`.
The old `'bigquery-public'` value remains valid for migration-period
rows; downstream consumers should treat both as "BQ-sourced exact
counts" (no semantic difference).

### Refactored `phase_p_pypi_downloads`

```python
def phase_p_pypi_downloads(conn: sqlite3.Connection) -> dict:
    """Phase P: incremental per-day PyPI download counts via BigQuery.

    v8.15.0 architecture — supersedes v8.1.0's single-shot 90-day query.

    Mode selection:
      - first-pull (pypi_downloads_daily empty): query trailing 90 days,
        cap at PHASE_P_MAX_COST_FIRST_PULL_USD (default $100).
      - incremental (table populated): query [last_stored_date + 1, today),
        cap at PHASE_P_MAX_COST_USD (default $10).
      - if gap > 90 days: revert to first-pull mode + log warning.

    Steps:
      1. Determine mode + window.
      2. Build _PARTITIONDATE-literal query (no CURRENT_TIMESTAMP()).
      3. Dry-run preflight: print estimated cost; abort if > cap.
      4. Real query with maximum_bytes_billed hard cap.
      5. Bulk INSERT OR IGNORE into pypi_downloads_daily.
      6. Recompute pypi_intelligence.downloads_30d/90d from local table.
      7. GC: delete pypi_downloads_daily rows older than retain window.

    Source: bigquery-public-data.pypi.file_downloads — project-level
    aggregation, one row per (pypi_name, _PARTITIONDATE).

    Tunables:
      PHASE_P_DISABLED                   : "1" to skip
      PHASE_P_ENABLED                    : must be "1" (opt-in) to run
      PHASE_P_BQ_PROJECT                 : GCP project override
      PHASE_P_TTL_DAYS                   : default 30 (driver gate; monthly cadence)
      PHASE_P_RETAIN_DAYS                : default 95 (GC threshold; 5d slack beyond 90d window)
      PHASE_P_MAX_COST_USD               : default 10 (incremental cap)
      PHASE_P_MAX_COST_FIRST_PULL_USD    : default 100 (first-pull cap)
      PHASE_P_JOB_TIMEOUT_MS             : default 600000 (10 min wall-clock cap)
      PHASE_P_FORCE_FIRST_PULL           : "1" to wipe + re-bootstrap
    """
    import datetime
    t0 = time.monotonic()
    print("  Phase P: PyPI download counts via BigQuery (incremental v8.15.0)")

    # --- Gates (unchanged from v8.1.0) ---
    if os.environ.get("PHASE_P_DISABLED"):
        return _skip("PHASE_P_DISABLED=1 set", t0)
    if not os.environ.get("PHASE_P_ENABLED"):
        print("  Phase P is opt-in; set PHASE_P_ENABLED=1 to run.")
        return _skip("PHASE_P_ENABLED not set", t0)

    try:
        from google.cloud import bigquery
    except ImportError:
        return _skip("google-cloud-bigquery not importable", t0)

    bq_project = os.environ.get("PHASE_P_BQ_PROJECT") or None
    try:
        client = bigquery.Client(project=bq_project)
    except Exception as e:
        return _skip(f"BigQuery client init failed: {e}", t0)

    # --- Mode + window selection ---
    today = datetime.date.today()
    force_first = bool(os.environ.get("PHASE_P_FORCE_FIRST_PULL"))
    if force_first:
        conn.execute("DELETE FROM pypi_downloads_daily")

    last_row = conn.execute(
        "SELECT MAX(download_date) FROM pypi_downloads_daily"
    ).fetchone()
    last_date_str = last_row[0] if last_row else None

    if last_date_str is None:
        mode = "first-pull"
        window_start = today - datetime.timedelta(days=90)
        cap_usd = float(os.environ.get("PHASE_P_MAX_COST_FIRST_PULL_USD", "100"))
    else:
        last_date = datetime.date.fromisoformat(last_date_str)
        gap_days = (today - last_date).days
        if gap_days > 90:
            mode = "first-pull-after-gap"
            window_start = today - datetime.timedelta(days=90)
            cap_usd = float(os.environ.get("PHASE_P_MAX_COST_FIRST_PULL_USD", "100"))
            print(f"  gap since last refresh ({gap_days} d) > 90; "
                  f"reverting to first-pull mode")
        else:
            mode = "incremental"
            window_start = last_date + datetime.timedelta(days=1)
            cap_usd = float(os.environ.get("PHASE_P_MAX_COST_USD", "10"))

    window_end = today  # excluded
    if window_start >= window_end:
        elapsed = time.monotonic() - t0
        print(f"  pypi_downloads_daily already current through {last_date_str}; "
              f"no new partitions to query.")
        return {
            "skipped": True,
            "reason": "no new partitions since last refresh",
            "mode": mode,
            "duration_seconds": round(elapsed, 1),
        }

    # --- Build query (literal dates, no CURRENT_TIMESTAMP) ---
    query = f"""
        SELECT
            REGEXP_REPLACE(LOWER(file.project), r'[-_.]+', '-') AS pypi_name,
            _PARTITIONDATE AS download_date,
            COUNT(*) AS downloads
        FROM `bigquery-public-data.pypi.file_downloads`
        WHERE _PARTITIONDATE >= DATE '{window_start.isoformat()}'
          AND _PARTITIONDATE <  DATE '{window_end.isoformat()}'
        GROUP BY pypi_name, _PARTITIONDATE
    """

    # --- Dry-run preflight ---
    try:
        dry = client.query(
            query,
            job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
        )
        est_gb = dry.total_bytes_processed / 1e9
        est_usd = (est_gb / 1000.0) * 6.25
    except Exception as e:
        return _skip(f"BigQuery dry-run failed: {e}", t0)

    days = (window_end - window_start).days
    print(f"  mode={mode}; window=[{window_start}, {window_end}) "
          f"({days} d); dry-run: ~{est_gb:,.0f} GB scan, "
          f"est ~${est_usd:.2f} (cap ${cap_usd:.2f})")

    if est_usd > cap_usd:
        return {
            "skipped": True,
            "reason": (f"estimated ${est_usd:.2f} exceeds cap ${cap_usd:.2f}; "
                       f"raise PHASE_P_MAX_COST_USD or PHASE_P_MAX_COST_FIRST_PULL_USD "
                       f"to override"),
            "estimated_usd": round(est_usd, 2),
            "cap_usd": cap_usd,
            "mode": mode,
            "duration_seconds": round(time.monotonic() - t0, 1),
        }

    # --- Real query with hard byte cap + wall-clock timeout ---
    # Belt-and-braces: maximum_bytes_billed prevents runaway scan cost;
    # job_timeout_ms prevents zombie jobs charging slot time on flat-rate
    # billing accounts. Real queries complete in 30-60 s; 10 min is generous.
    max_bytes = int((cap_usd / 6.25) * 1e12)
    timeout_ms = int(os.environ.get("PHASE_P_JOB_TIMEOUT_MS", "600000"))
    try:
        rows = list(
            client.query(
                query,
                job_config=bigquery.QueryJobConfig(
                    maximum_bytes_billed=max_bytes,
                    job_timeout_ms=timeout_ms,
                ),
            ).result()
        )
    except Exception as e:
        return _skip(f"BigQuery query failed: {e}", t0)

    # --- Bulk INSERT into pypi_downloads_daily ---
    insert_rows = []
    for r in rows:
        name = r["pypi_name"]
        if not name:
            continue
        date_val = r["download_date"]
        date_str = date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)
        insert_rows.append((name, date_str, int(r["downloads"])))

    conn.execute("BEGIN")
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO pypi_downloads_daily "
            "(pypi_name, download_date, downloads) VALUES (?, ?, ?)",
            insert_rows,
        )
        rows_inserted = conn.execute(
            "SELECT changes()"
        ).fetchone()[0]

        # --- Recompute downloads_30d/90d from local table ---
        cutoff_30d = (today - datetime.timedelta(days=30)).isoformat()
        cutoff_90d = (today - datetime.timedelta(days=90)).isoformat()
        now = int(time.time())
        conn.execute("""
            INSERT INTO pypi_intelligence (
                pypi_name, downloads_30d, downloads_90d,
                downloads_fetched_at, downloads_source
            )
            SELECT
                pypi_name,
                COALESCE(SUM(CASE WHEN download_date >= ? THEN downloads ELSE 0 END), 0),
                COALESCE(SUM(downloads), 0),
                ?,
                'bigquery-incremental'
            FROM pypi_downloads_daily
            WHERE download_date >= ?
            GROUP BY pypi_name
            ON CONFLICT(pypi_name) DO UPDATE SET
                downloads_30d        = excluded.downloads_30d,
                downloads_90d        = excluded.downloads_90d,
                downloads_fetched_at = excluded.downloads_fetched_at,
                downloads_source     = excluded.downloads_source
        """, (cutoff_30d, now, cutoff_90d))

        # --- GC: prune old daily rows ---
        retain_days = int(os.environ.get("PHASE_P_RETAIN_DAYS", "95"))
        gc_cutoff = (today - datetime.timedelta(days=retain_days)).isoformat()
        rows_pruned = conn.execute(
            "DELETE FROM pypi_downloads_daily WHERE download_date < ?",
            (gc_cutoff,),
        ).rowcount

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    elapsed = time.monotonic() - t0
    print(f"  Phase P done in {elapsed:.1f}s — mode={mode}, "
          f"inserted {rows_inserted:,} daily rows, pruned {rows_pruned:,}; "
          f"actual cost ~${est_usd:.2f}")
    return {
        "mode": mode,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "rows_inserted": rows_inserted,
        "rows_pruned": rows_pruned,
        "estimated_usd": round(est_usd, 2),
        "source": "bigquery-incremental",
        "duration_seconds": round(elapsed, 1),
    }


def _skip(reason: str, t0: float) -> dict:
    return {
        "skipped": True,
        "reason": reason,
        "duration_seconds": round(time.monotonic() - t0, 1),
    }
```

### Cost-cap behavior (BigQuery semantics)

`bigquery.QueryJobConfig(maximum_bytes_billed=N)` is a **server-side
hard ceiling**:

- If the planner estimates ≤ N bytes, the query runs normally and bills
  on actual processed bytes.
- If actual processed bytes would exceed N, BQ aborts with HTTP 400
  `Query exceeded limit for bytes billed` and **bills $0** for that job.
- Operator gets a fail-fast signal, not a surprise invoice.

The dry-run preflight is a *softer* gate: it abort-with-clear-error
*before* submitting the real job, with a printable estimate. The real
query *also* carries `maximum_bytes_billed` as a defence-in-depth
backstop in case the planner re-estimates upward between dry-run and
live run.

Both gates respect the same operator-set cap. Tuning is a single env
var per mode.

### Profile integration

No change from v8.1.0:
- `admin`: sets `PHASE_P_ENABLED=1`. Picks up the new defaults.
- `maintainer`: does NOT enable Phase P.
- `consumer`: does NOT enable Phase P.

Operators on the admin profile see the new cost-cap behavior
automatically. To opt into a higher cap for a one-off catch-up run:

```bash
PHASE_P_MAX_COST_USD=25 pixi run -e local-recipes build-cf-atlas --profile admin
```

To force a clean first-pull (e.g., after suspecting daily-table
corruption):

```bash
PHASE_P_FORCE_FIRST_PULL=1 pixi run -e local-recipes build-cf-atlas --profile admin
```

---

## Stories — 3 waves, ~12 stories

### Wave A — Schema v26 + Phase P refactor (~6 stories)

| ID | Story | Effort |
|---|---|---|
| S1 | Add `pypi_downloads_daily` table + 2 indexes to SCHEMA_DDL; bump `SCHEMA_VERSION` 25 → 26 | XS |
| S2 | Schema v26 migration block in `init_schema` (idempotent guards via `pragma_table_info` + `IF NOT EXISTS`) | XS |
| S3 | Refactor `phase_p_pypi_downloads`: mode-selection logic, `_PARTITIONDATE`-literal query, dry-run preflight, hard byte cap, INSERT into `pypi_downloads_daily`, aggregation INSERT into `pypi_intelligence`, GC | L |
| S4 | Tunables: `PHASE_P_MAX_COST_USD`, `PHASE_P_MAX_COST_FIRST_PULL_USD`, `PHASE_P_RETAIN_DAYS`, `PHASE_P_JOB_TIMEOUT_MS`, `PHASE_P_FORCE_FIRST_PULL` (env-var contracts + documentation block in docstring) | XS |
| S5 | Drop unused tunable: `PHASE_P_BQ_WINDOW_DAYS` (declared in spec but unused; window is now mode-determined). Deprecate gently — log warning if set | XS |
| S6 | Add a `_skip` helper for the early-exit pattern used 6 times in the new function (DRY cleanup) | XS |

### Wave B — Tests + spec/doc corrections (~4 stories)

| ID | Story | Effort |
|---|---|---|
| S7 | Rewrite `tests/unit/test_phase_p_bigquery.py`: 8 new test cases covering mode selection (first-pull / incremental / gap-revert / no-op), dry-run abort, cap respected, GC prune, idempotent re-run | L |
| S8 | New `tests/unit/test_pypi_downloads_daily.py`: schema migration, INSERT OR IGNORE idempotency, aggregation correctness against fixture rows | M |
| S9 | Correct "~30 GB" misclaim across: spec line 105 + 134 + 743 in `docs/specs/atlas-pypi-intelligence.md`; docstring at `conda_forge_atlas.py:6250`; CHANGELOG entry for v8.1.0; `reference/atlas-phases-overview.md` line 45 + 242-245; `quickref/commands-cheatsheet.md` line 556. Replace with the empirical numbers + a pointer to the dry-run preflight | M |
| S10 | Add a new `reference/atlas-phase-p-cost-model.md` documenting the cost math, cap behavior, dry-run preflight semantics, and the BQ partition-pruning sensitivity that caused the 2026-06-12 surprise. Cross-link from `atlas-phases-overview.md` § Phase P | M |

### Wave C — Closeout (~3 stories)

| ID | Story | Effort |
|---|---|---|
| S11 | `CHANGELOG.md` v8.15.0 entry; SKILL.md heading bump; skill-config 8.9.x → 8.10.0; CFE retrospective per CLAUDE.md Rule 2 (this effort touches conda-forge work + ships skill updates) | M |
| S12 | Update `atlas-actionable-intelligence.md` catalog: Phase P entries gain a "cost-bounded" annotation + the operator-facing tunables. No new ✅-flips (functionality unchanged from consumer view) | S |
| S13 | Append a CLAUDE.md one-liner under "Project Documentation Reference" pointing at this spec | XS |

### Wave sequencing rationale

- **Wave A is the implementation.** Self-contained refactor — touches one
  function + one schema table + one set of env-var defaults. Ship-ready
  alone.
- **Wave B is correctness + truth-in-docs.** Tests guard the refactor;
  the doc corrections close the spec/code/CHANGELOG divergence that
  caused the cost surprise. Ships in the same PR as Wave A — no soak
  needed.
- **Wave C is closeout.** Single PR, single tag.

**Single-PR strategy** unless test work in S7+S8 exceeds review-load
preference. The schema change is additive, the refactor is local, and
the doc corrections all link to the same root cause.

---

## Acceptance Tests

### Wave A

- `tests/unit/test_pypi_downloads_daily.py::test_schema_v26_migration` —
  `init_schema` against a v25 DB produces v26 with the new table + 2
  indexes; idempotent on second run.
- `tests/unit/test_phase_p_bigquery.py::test_first_pull_window` — empty
  daily table → 90-day window submitted; cap defaults to $100.
- `tests/unit/test_phase_p_bigquery.py::test_incremental_window` — daily
  table populated through D-7 → window = [D-6, today); cap defaults
  to $10.
- `tests/unit/test_phase_p_bigquery.py::test_gap_revert_to_first_pull` —
  daily table's last row is 120 days ago → reverts to first-pull mode +
  $100 cap + warning logged.
- `tests/unit/test_phase_p_bigquery.py::test_no_new_partitions_noop` —
  daily table's last row is `today - 1` → query window is empty →
  early return with `skipped=True, reason="no new partitions"`.
- `tests/unit/test_phase_p_bigquery.py::test_dryrun_above_cap_aborts` —
  mocked dry-run returns `total_bytes_processed = 3e12` (~$18); cap is
  $10 → returns `skipped=True` with cost in the reason string;
  `client.query` is NOT called a second time.
- `tests/unit/test_phase_p_bigquery.py::test_maximum_bytes_billed_set` —
  real query is submitted with `QueryJobConfig.maximum_bytes_billed` ==
  `int((cap / 6.25) * 1e12)`.
- `tests/unit/test_phase_p_bigquery.py::test_job_timeout_ms_set` —
  real query is submitted with `QueryJobConfig.job_timeout_ms == 600000`
  by default; `PHASE_P_JOB_TIMEOUT_MS=120000` env override propagates.
- `tests/unit/test_phase_p_bigquery.py::test_pypi_intel_aggregation` —
  populated `pypi_downloads_daily` fixture → after Phase P,
  `pypi_intelligence.downloads_30d/90d` match the expected sums for the
  fixture's date ranges.
- `tests/unit/test_phase_p_bigquery.py::test_gc_prunes_old_rows` — rows
  older than `PHASE_P_RETAIN_DAYS=95` are deleted; rows within the
  window survive.

### Wave B

- `tests/meta/test_no_thirty_gb_lie.py` (new) — grep across spec/
  /reference/ /quickref/ /SKILL.md / CHANGELOG.md / `conda_forge_atlas.py`
  for the phrase "30 GB" near "Phase P" or "bigquery". Fails if any
  match survives. Guards against the bad-number regression.
- `tests/meta/test_phase_p_docstring_matches_envvars.py` (new) — parse
  the `phase_p_pypi_downloads` docstring for `PHASE_P_*` env-var
  mentions; cross-check against the names actually read by `os.environ.get`.
  Fails if either side drifts.

### Cross-cutting

- Full atlas rebuild against the dev `cf_atlas.db` at schema v26
  produces a sane `pypi_downloads_daily` with ~50k–100k unique
  `pypi_name` × ~90 `download_date` rows. `pypi_intelligence.downloads_30d`
  for the top 100 packages by downloads correlates within ~10% of the
  pre-fix `bigquery-public` values (sanity check for aggregation
  correctness — not bit-identical because of inflight days).
- Meta-test `test_actionable_scope.py` continues to recognize Phase P;
  no false drift flags from the table addition.
- Dry-run smoke (operator-runnable, not in CI): `PHASE_P_ENABLED=1
  PHASE_P_MAX_COST_USD=0.01 pixi run build-cf-atlas --profile admin` —
  should abort with "estimated $X exceeds cap $0.01" without submitting
  the real query.

---

## Risks

| Risk | Mitigation |
|---|---|
| Operator's BigQuery project has zero free-tier headroom left → even the dry-run reports a non-zero bill | Dry-run is FREE per BQ docs (no quota consumed). If we observe charges, document the surprise and switch the preflight to use the BQ pricing calculator REST endpoint instead |
| `_PARTITIONDATE` projection still scans more than estimated due to planner quirks | `maximum_bytes_billed` is a hard server-side cap; planner mis-estimation cannot exceed it. Worst case: job aborts with $0 bill and operator sees a clear error |
| 30-day window aggregation produces values that diverge from the old single-shot 90-day query (e.g., because the new approach counts whole-day partitions while the old one used a sliding `timestamp >=` predicate) | Document the off-by-up-to-1-day boundary semantics in `atlas-phase-p-cost-model.md`. Downstream consumers (`conda_forge_readiness`) use these as ordering signals — 1-day boundary error does not affect ranking |
| `pypi_downloads_daily` grows unbounded if GC fails | GC runs on every Phase P invocation; failure to prune is logged but doesn't fail the phase. Cron-style cleanup via `pixi run cf-atlas-gc` proposed as v8.16.0 follow-up |
| Operator runs back-to-back Phase P refreshes in a single day → tiny incremental window → many no-op INSERTs | `INSERT OR IGNORE` makes re-inserts a no-op. The `no new partitions` early return short-circuits before the query is even built |
| First-pull on a brand-new install runs against a stale `PHASE_P_MAX_COST_FIRST_PULL_USD` operator-defined value (e.g., set to "1") | Documented in `atlas-operations.md` § Phase P quickstart with explicit suggested values; dry-run output prints both the estimate and the cap so the operator can see they need to raise it |
| The `bigquery-public-data.pypi.file_downloads` schema changes (e.g., `file.project` renamed) | Phase P is opt-in and TTL-gated; a schema change surfaces as a BQ query failure on next refresh. Same failure mode as v8.1.0. Detection latency = TTL gap (default 30 d) |
| Storage delta (~225–450 MB) materially slows down DB clone / backup / sync operations | Air-gapped operators can disable Phase P entirely; the daily table is only created when Phase P first runs. Documented as a tradeoff in `reference/atlas-phase-p-cost-model.md` |
| The "spec / code / docs all carry the wrong number" lesson recurs | New meta-test `test_no_thirty_gb_lie.py` is the structural guard. Adds a new convention: cost claims in spec/code/docs must reference the dry-run preflight as the source of truth |

---

## Rollout

### Pre-merge

- Single-PR strategy: all 3 waves in one PR.
- BMAD agent executes waves in order; each wave's tests pass before the
  next starts.
- Manual smoke: operator runs `PHASE_P_ENABLED=1 PHASE_P_MAX_COST_USD=15
  pixi run build-cf-atlas --profile admin` against the dev `cf_atlas.db`
  to verify first-pull cost matches the dry-run estimate within ±10%.
- CFE skill version bump: 8.9.x → **8.10.0** (MINOR — additive schema +
  new env vars + new table; no breaking change to consumer surface).

### Merge order

- Single PR. No predecessor dependency. Can land after v8.9.0 (the
  maturin generator spec) ships, or in parallel if v8.9.0 doesn't
  touch `phase_p_*` (it does not — disjoint scope).

### Post-merge

- `CHANGELOG.md` v8.15.0 entry summarizing: schema v26 migration, Phase
  P refactor, new cost-cap env vars, the corrected "30 GB → ~30 GB/day"
  spec lie.
- `atlas-phases-overview.md` § Phase P updated with the cost model
  pointer.
- `atlas-operations.md` Phase P quickstart: new section "Cost
  expectations" with the per-cadence table, the cap-tuning recipe, and
  the force-first-pull recovery procedure.
- New `reference/atlas-phase-p-cost-model.md` — single source of truth
  for cost claims.
- Auto-memory feedback entry: **add** a `feedback_cost_claims_must_cite_dryrun.md`
  rule — "Any 'this BQ query scans N GB' claim in spec/code/docs MUST be
  paired with a dry-run preflight as the source of truth, not a copied
  napkin number." Cross-skill (BMAD specs + CFE), worth durable memory.

### Backout plan

- Schema v26 migration is reversible: `DROP TABLE pypi_downloads_daily`
  and downgrade SCHEMA_VERSION to 25.
- Phase P revert: restore the v8.1.0 single-shot query from git
  history. The `pypi_intelligence.downloads_30d/90d` columns continue
  to work; the new `downloads_source = 'bigquery-incremental'` rows
  remain valid (revert reader queries to accept both values).
- Doc corrections are not reverted (the old numbers were wrong).

---

## Open Questions

Q1, Q2, Q5, Q7 resolved 2026-06-12 by operator. Q3, Q4, Q6, Q8 carry
recommendations only; BMAD intake may proceed with the recommended
defaults or surface them for explicit resolution at sprint planning.

1. **Default refresh cadence — monthly (current) or weekly?** →
   **RESOLVED 2026-06-12: monthly.** `PHASE_P_TTL_DAYS=30` stays the
   default driver gate, matching v8.1.0 behavior. Weekly is the
   documented escape hatch (`PHASE_P_TTL_DAYS=7`) for operators who
   need fresher ranking signals; it fits comfortably under the $10/run
   cap (~$1.40/run empirically). Rationale: 30-day staleness on a
   download-popularity ranking is well within signal tolerance for
   `conda_forge_readiness` consumers; weekly buys little incremental
   value at the cost of 4× more refresh events to monitor.

2. **Should `PHASE_P_MAX_COST_USD` default to $10 or something tighter
   like $5?** → **RESOLVED 2026-06-12: $10.** Matches the operator's
   stated tolerance ("hard cap at 2 TB ~$10/run is the max I want to
   spend for refreshes"). $10 leaves headroom for an occasional
   ~60-day catch-up after a missed monthly cycle without manual
   intervention. Operators wanting tighter discipline can drop to $5
   via the env var; the dry-run preflight prints both estimate and cap
   so the right number is visible at run time.

3. **Per-version downloads — defer (matches `atlas-pypi-intelligence.md`
   Q2) or include in the daily table?** Including would multiply scan
   ~200×, blowing the cap. **Recommendation:** defer to v8.16.0+.
   `pypi_downloads_daily` schema deliberately omits `version` to keep
   this door open without committing.

4. **Pricing-flex per region — does the operator's BQ project live in
   a non-default region where on-demand pricing differs from $6.25/TB?**
   The cost-model math assumes US pricing. **Recommendation:** read
   `PHASE_P_USD_PER_TB` env override (default 6.25); document the EU
   and APAC variants in the cost-model doc.

5. **Should the live query also carry a 5-min timeout / `job_timeout_ms`
   to prevent a runaway "slot starvation" scenario?** →
   **RESOLVED 2026-06-12: yes, `job_timeout_ms = 600000` (10 min).**
   Belt-and-braces complement to `maximum_bytes_billed`: byte-cap
   prevents runaway scan cost, timeout prevents zombie jobs charging
   slot time on flat-rate billing accounts. Real queries complete in
   30-60 s; a 10-min cap is generous and aborts with a clear error
   well before any zombie-job scenario becomes expensive. Operator
   override via `PHASE_P_JOB_TIMEOUT_MS` for the rare case where a
   first-pull on a slow region needs more wall-clock headroom.

6. **ClickHouse `clickpy` as a verification source for the test suite?**
   Could compare top-1000 counts from BQ vs ClickHouse as an unit-test
   sanity check. Network-dependent, brittle in CI. **Recommendation:**
   document the comparison procedure in `atlas-phase-p-cost-model.md`
   as an operator-runnable diagnostic; no CI integration.

7. **What's the right value for `PHASE_P_RETAIN_DAYS` — 95 (5 days
   slack) or higher (e.g., 180) for year-over-year analysis?** →
   **RESOLVED 2026-06-12: 95.** Minimizes storage (~225-450 MB
   steady-state); 5-day slack covers any boundary edge cases between
   the 90-day window and the GC sweep. 180 (or 365) is documented as
   the operator-tunable escape hatch for the day operator demand for
   `downloads_180d` / year-over-year analysis surfaces — at that point
   the storage delta becomes ~450-900 MB which is a deliberate
   admin-tier tradeoff. Default stays tight; door is left open.

8. **Backward-compat handling for the existing
   `downloads_source = 'bigquery-public'` rows after v8.15.0 ships.**
   Should the migration recompute them from a forced first-pull, or
   leave them in place until natural TTL expiry overwrites them?
   **Recommendation:** leave in place. They're valid data from the
   pre-fix query. `downloads_fetched_at` lets consumers detect
   staleness independently of the source label.

---

## References

### Source-of-truth code (current state — v8.14.x baseline)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`:
  - `SCHEMA_VERSION` (line 137) — bump 25 → 26
  - SCHEMA_DDL block — add `pypi_downloads_daily` table + 2 indexes
  - `init_schema` migration block — add v26 sub-block
  - `phase_p_pypi_downloads` (line 6237) — full refactor
  - PHASES registry — no change (Phase P slot unchanged)
- `.claude/skills/conda-forge-expert/scripts/bootstrap_data.py` (line
  175) — no change; `admin` profile continues to set `PHASE_P_ENABLED=1`
- `.claude/skills/conda-forge-expert/tests/unit/test_phase_p_bigquery.py` —
  rewrite per Wave B
- `.claude/skills/conda-forge-expert/tests/unit/test_pypi_downloads_daily.py` —
  NEW
- `.claude/skills/conda-forge-expert/tests/meta/test_no_thirty_gb_lie.py` —
  NEW (regression guard)
- `.claude/skills/conda-forge-expert/tests/meta/test_phase_p_docstring_matches_envvars.py` —
  NEW (drift guard)

### Related specs

- `docs/specs/atlas-pypi-intelligence.md` — v8.1.0 introduced Phase P
  and `pypi_intelligence`. This spec rewrites the Phase P body while
  preserving the consumer surface. Spec lines 105, 134, 743 carry the
  "~30 GB" lie that this effort corrects.
- `docs/specs/conda-forge-expert-v8.0.md` — v8.0.0 introduced personas.
  Phase P's `admin`-tier opt-in continues unchanged.
- `docs/specs/atlas-phase-f-s3-backend.md` — v7.6.0 introduced source
  dispatch via `PHASE_F_SOURCE`. This spec does NOT add a source
  switch for Phase P (operator stays on BigQuery); follow-up spec
  may add `PHASE_P_SOURCE = bigquery | clickpy | ecosystems` if
  operators want a no-creds path.

### Audit context

- **Conversation log 2026-06-12** — "the last refresh cost over $500
  dollars for the bigquery pypi data refresh". This spec is the
  recorded fix.
- **BigQuery dry-run output** (operator-verifiable): `bq query
  --dry_run --use_legacy_sql=false '<query>'` returns
  `totalBytesProcessed`. Empirical baseline as of 2026-06-12: a 90-day
  `_PARTITIONDATE`-pruned + `file.project + _PARTITIONDATE`-projected
  query reports ~2.7 TB processed; on-demand cost ~$17.

### Documentation

- `.claude/skills/conda-forge-expert/SKILL.md` — Atlas Intelligence
  Layer heading update to v8.15.0
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — v8.15.0 entry per
  Rule 2
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` —
  Phase P section updated with the cost-model pointer; "30 GB" lie
  removed
- `.claude/skills/conda-forge-expert/reference/atlas-phase-p-cost-model.md` —
  NEW; single source of truth for cost claims, dry-run preflight
  semantics, cap-tuning, force-first-pull recovery
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md` —
  catalog annotation update (no flips)
- `.claude/skills/conda-forge-expert/guides/atlas-operations.md` —
  Phase P quickstart gains a "Cost expectations" section
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` —
  Phase P cost-cap recipes; "30 GB" lie removed
- `CLAUDE.md` — add `docs/specs/atlas-phase-p-incremental.md` to the
  BMAD-consumable spec list (one-line entry under Project Documentation
  Reference)
