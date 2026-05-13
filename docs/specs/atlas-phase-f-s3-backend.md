# Tech Spec: Atlas Phase F — S3 / condastats backend + Phase F+ metrics

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> well-bounded, single-skill scope, ~14 implementation stories in 4 waves).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-f-s3-backend.md
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
| Surface area | `conda-forge-expert` skill — atlas pipeline (Phase F / Phase F+) + 3 new CLIs / MCP tools |
| Scope | (1) S3 backfill backend for Phase F; (2) richer Phase F+ metrics from same sweep; (3) `platform_breakdown` / `pyver_breakdown` / `channel_split` CLIs and MCP tools |
| Out of scope | Daily-granularity downloads, defaults-channel atlas, BigQuery integration |
| Created | 2026-05-10 |

---

## Background and Context

### The problem

`conda-forge-expert`'s atlas pipeline Phase F is the only stage of the
9-phase build that has **no firewall-friendly alternative source**. It
fetches per-package download counts from `https://api.anaconda.org/package/conda-forge/{name}`
— one HTTP request per package, ~32k requests for a cold backfill — and
those counts feed `staleness_report`, `package_health`, `version_downloads`,
`release_cadence`, and the staleness-score column used by `find_alternative`
and `adoption_stage`.

Two problems compound:

1. **Air-gapped / enterprise-firewall users** that block `*.anaconda.org`
   today have no fallback. The atlas builds, but every `total_downloads`
   column ends up NULL and the affected MCP tools return blanks. The
   workaround documented in `_http.py` (`ANACONDA_API_BASE` env var) only
   helps if the operator has already stood up their own mirror of the
   anaconda.org API, which is rare.
2. **The API surface is information-poor.** It gives only cumulative
   `ndownloads` per artifact. Time-series, platform breakdown, and
   per-python-version distribution are absent — even though the
   downstream consumers (`platform_breakdown` is on the v8 roadmap;
   python_min policy enforcement currently relies on intuition rather
   than data) could use them.

### What's been ruled out

- **BigQuery (pypistats-style).** No public BigQuery dataset mirrors
  conda-forge downloads. `condastats` itself reads from S3, not BigQuery.
- **Defaults-channel-only data.** Plenty of internal Anaconda dashboards
  exist; none are publicly accessible.
- **Per-build-hash granularity.** The S3 dataset is keyed by version
  string, not build hash. Acceptable — Phase F doesn't use build hashes
  either.
- **Daily granularity.** S3 publishes monthly parquet files only.
  Acceptable — Phase F's TTL is already 7 days and downstream consumers
  use downloads as a coarse signal.

### What's available to leverage

- **Public S3 bucket `s3://anaconda-package-data/`** — `conda/monthly/{YYYY}/{YYYY-MM}.parquet`.
  No auth required, listable over HTTPS, served from `*.s3.amazonaws.com`
  (different host than `*.anaconda.org`). **Verified current 2026-05-10:**
  `2026-04.parquet` uploaded 2026-05-01 17:34 UTC, monthly cadence intact
  since the 2024 condastats relaunch.
- **Parquet schema** (verified):
  `time` (YYYY-MM) · `data_source` (channel) · `pkg_name` · `pkg_version` ·
  `pkg_platform` · `pkg_python` · `counts`. 6 dimensions, 1 metric, ~13MB/month.
- **`_http.py`** already provides the JFrog/GitHub/.netrc auth chain and
  truststore injection. Adding S3 HTTPS as a routable host is a small extension.
- **`pyarrow`** is already a dependency of the `local-recipes` pixi env
  via `pandas` and `duckdb`. No new top-level dep needed.
- **Existing Phase F schema** (`packages.total_downloads`,
  `latest_version_downloads`, `downloads_fetched_at`, `downloads_fetch_attempts`,
  `downloads_last_error`) and Phase I side-effect table
  (`package_version_downloads`) are well-defined; the S3 backend writes
  to the same shape.

### Verified discrepancies (informational)

Comparing API totals vs S3-lifetime sums for three packages on 2026-05-10:

| Package | API `ndownloads` sum | S3 lifetime sum (conda-forge) | Ratio |
|---|---:|---:|---:|
| `requests` | 81,699,781 | 122,921,283 | 1.50× |
| `django` | 3,317,504 | 1,861,625 | 0.56× |
| `bmad-method` | 3,625 | 3,084 | 0.85× (partial May missing) |

**Implication:** the two sources are not numerically identical and the
gap direction is not consistent. Phase F+ must persist a
`downloads_source` discriminator and report consumers must surface it.
Treat the two as correlated-but-distinct metrics, not interchangeable.

---

## Goals

- **G1.** **Air-gap parity for Phase F.** With `*.anaconda.org` blocked, an
  atlas build must still populate `total_downloads` and
  `latest_version_downloads` to within "order-of-magnitude-correct, ranking-correct"
  fidelity, using only `*.s3.amazonaws.com` (or a JFrog mirror of it).
- **G2.** **No regression for online users.** When `*.anaconda.org` is
  reachable and `PHASE_F_SOURCE=auto`, behavior matches today's Phase F
  exactly — same numbers, same TTL gating, same throughput envelope.
- **G3.** **Source attribution.** Every `packages` row carries a
  `downloads_source` column so reports can disclose which dataset
  produced the number.
- **G4.** **Richer metrics from the same data pass** — rolling 30/90-day
  downloads, 90-day trend slope, first/last non-zero month, per-platform
  and per-python download breakdowns. Computed in one parquet sweep, no
  extra network.
- **G5.** **Three new operator CLIs / MCP tools** —
  `platform_breakdown`, `pyver_breakdown`, `channel_split` — each
  reading only from the atlas DB (offline-safe by construction).
- **G6.** **JFrog/enterprise-mirror routable.** S3 HTTPS URLs route
  through `_http.py` so `JFROG_API_KEY` / `JFROG_USERNAME+PASSWORD`
  authenticate transparently against a mirrored copy.
- **G7.** **Local cache for parquet.** Static monthly files cache to
  `.claude/data/conda-forge-expert/cache/parquet/` and are re-fetched
  only when the current month rolls over or the cache file is corrupt.

## Non-Goals

- **NG1.** No daily granularity. Monthly is what S3 publishes; we don't
  synthesize finer resolution.
- **NG2.** No backfill of channels other than `conda-forge`. Phase F
  has always been conda-forge-scoped; the `data_source` filter stays.
- **NG3.** No BigQuery integration. Spec stays within the published S3
  parquet surface.
- **NG4.** No automatic anaconda.org → S3 reconciliation logic.
  Discrepancies are surfaced (via `downloads_source`), not "fixed."
- **NG5.** No per-build-hash drill-down. Version is the finest grain.
- **NG6.** No new persistence of data we already compute on demand
  (e.g., we don't materialize "downloads per (package, platform, month)"
  for all 32k × 11 × 110 = 38M rows; we aggregate to the cuts we need).
- **NG7.** No web UI / dashboard. CLI + MCP tools only; rendering is
  downstream's job.
- **NG8.** No `condastats` Python package dependency. We read parquet
  directly via `pyarrow` — same data source, fewer dep layers.

---

## Lifecycle Expectations

- **One-time backfill cost** when first enabled: ~110 parquet files
  (~13 MB each, ~1.4 GB total) downloaded sequentially over residential
  bandwidth in ~5–10 minutes. Cached locally; subsequent runs fetch only
  the new current-month file (~13 MB).
- **Per-atlas-run cost** in steady state: one HTTP GET for the current
  month's parquet (if it's the first run that month) plus the existing
  Phase F TTL gating; otherwise zero new network.
- **Schema migration** is forward-only and idempotent — same pattern as
  existing Phase F column additions.

---

## User Stories

Stories grouped into 4 waves. **Wave 1 ships the air-gap fix as a
minimum-viable result** (G1, G2, G3); subsequent waves layer on G4–G7.

### Wave 0 — Foundations

#### Story 1 — S3 HTTPS routing in `_http.py`

Extend `_http.py` so requests to `https://anaconda-package-data.s3.amazonaws.com/`
participate in the same resolver chain that already handles
`https://conda.anaconda.org/conda-forge/`:

- Add `resolve_s3_parquet_urls(month: str) -> list[str]` returning, in
  order: `S3_PARQUET_BASE_URL` env override, JFrog-mirrored URL if
  configured, then the public S3 HTTPS URL.
- Inject JFrog auth headers automatically when `JFROG_API_KEY` or
  `JFROG_USERNAME+PASSWORD` are set and the resolved host matches the
  enterprise prefix.
- Add `list_s3_parquet_months() -> list[str]` that probes the S3
  list-objects-v2 XML endpoint (`?list-type=2&prefix=conda/monthly/`)
  and parses out `YYYY-MM` keys. Cached for the lifetime of one atlas run.

#### Story 2 — Parquet cache + reader helper

Create `scripts/_parquet_cache.py` (NEW; private module like `_http.py`,
`_sbom.py`):

- `cache_dir()` → `.claude/data/conda-forge-expert/cache/parquet/`
  (created on first use, gitignored).
- `ensure_month(month: str) -> Path`: downloads `YYYY-MM.parquet` via
  `_http.py` if not cached or if `month` equals the current month (always
  refresh current month in case mid-month updates land — they don't, per
  the dataset docs, but cheap insurance).
- `read_filtered(months: list[str], pkg_names: set[str] | None = None,
  data_source: str = 'conda-forge') -> pa.Table`: reads listed parquet
  files with pushdown filters on `data_source` and (optional) `pkg_name`.
  Uses `pyarrow.parquet.read_table` with the `filters=` arg — no
  pandas/duckdb round-trip in the hot path.

#### Story 3 — Atlas schema migration v17 → v18

Add columns to `packages` table:

- `downloads_source TEXT` — one of `'anaconda-api'`, `'s3-parquet'`,
  `'merged'`, or `NULL` if Phase F has never run for this row.
- `downloads_30d INTEGER`
- `downloads_90d INTEGER`
- `downloads_trend_90d REAL` — pct change vs prior 90-day window
  (positive = growing); `NULL` if fewer than 6 months of data.
- `first_nonzero_month TEXT` — `'YYYY-MM'` of earliest non-zero
  downloads month.
- `last_nonzero_month TEXT` — `'YYYY-MM'` of most recent non-zero
  downloads month.

Add two new tables:

- `package_platform_downloads` — `(conda_name, pkg_platform,
  downloads_90d, downloads_total, fetched_at)`. Indexed on
  `(conda_name)`.
- `package_python_downloads` — `(conda_name, pkg_python,
  downloads_90d, downloads_total, fetched_at)`. Indexed on
  `(conda_name)`.

Migration is forward-only and follows the existing
`_apply_pending_migrations` pattern. Schema version bumps to **v18**
(currently v17 per `conda_forge_atlas.py`); add an entry to the
migrations list and verify the test that asserts the migration version.

### Wave 1 — Phase F S3 backfill (air-gap fix; minimum viable)

#### Story 4 — `PHASE_F_SOURCE` env var + source dispatch

Refactor `phase_f_downloads` to read `PHASE_F_SOURCE` (default `auto`):

- `anaconda-api` — current behavior, unchanged.
- `s3-parquet` — skip the API entirely; read from cached parquet.
- `auto` — try API per row; on `urllib.error.URLError` or 5xx without
  successful response after retries, fall back to S3 for that row
  (`downloads_source = 'merged'` when API succeeded for *most* rows
  but S3 filled gaps; `'s3-parquet'` when API was unreachable entirely).

`auto` mode probes reachability by attempting one API call against a
small known package (`pip`) before launching the worker pool; on failure
it short-circuits to `s3-parquet` for the whole run rather than burning
retries 32k times.

#### Story 5 — `s3-parquet` Phase F implementation

When `s3-parquet` mode is selected:

- Determine the months to load (default: all available; respect
  `PHASE_F_S3_MONTHS` env var as a count of trailing months, e.g.
  `PHASE_F_S3_MONTHS=24` for the last 2 years only — useful for
  reduced-disk-footprint deployments).
- Download missing months via Story 2's `ensure_month`.
- Run a single `pyarrow` aggregation:
  ```python
  SELECT pkg_name,
         SUM(counts) AS total_downloads,
         MIN(time) AS first_nonzero_month,
         MAX(time) AS last_nonzero_month
  FROM <parquets>
  WHERE data_source = 'conda-forge' AND counts > 0
  GROUP BY pkg_name
  ```
- For `latest_version_downloads`, run a second aggregation grouped by
  `(pkg_name, pkg_version)` and pluck the row matching each package's
  `latest_conda_version`.
- Bulk-update `packages` in batches of 500 (same transaction pattern as
  today's API path). Set `downloads_source='s3-parquet'`.

Update `package_version_downloads` (Phase I side-effect table) from the
same per-version aggregation — but **set `upload_unix` to `NULL` when
sourcing from S3** since the parquet has no upload-time column. Add a
`source TEXT` column to `package_version_downloads` to track this.

#### Story 6 — `auto` mode merge + reachability probe

Implement the reachability probe and the per-row merge:

- Probe: `urllib.urlopen(API_URL_FOR_PIP, timeout=10)`. On success, run
  the existing API path. On failure, log the reason and fall through to
  `s3-parquet`.
- Per-row failure recovery: when `PHASE_F_CONCURRENCY` workers report
  >25% failure rate after the first 1,000 rows, abort the API pool, drop
  to `s3-parquet`, and continue.
- Source attribution: `downloads_source='anaconda-api'` for rows
  fetched cleanly via API; `'s3-parquet'` for rows whose API call failed
  and were filled from S3; `'merged'` when both contributed.

### Wave 2 — Phase F+ richer metrics

#### Story 7 — Rolling 30 / 90-day download windows

In the parquet aggregation pass, compute:

- `downloads_30d` = SUM(counts) WHERE time = most-recent-month and time
  is no more than 30 days behind today. (Single-month at monthly
  resolution; documented as such.)
- `downloads_90d` = SUM(counts) WHERE time IN (last 3 months available).

Write to the new columns from Story 3. Do this in the same parquet
sweep — no extra reads.

#### Story 8 — 90-day trend slope

Compute `downloads_trend_90d` as
`(downloads_90d - downloads_prev_90d) / downloads_prev_90d` where
`downloads_prev_90d` is the SUM over months 4–6 trailing.

- Returns `NULL` if either window has zero downloads (avoid div-by-zero)
  or if fewer than 6 months of data exist for the package.
- Sign convention: positive = growing; negative = declining.
- Cap at `+10.0` to dampen new-package "infinite growth" outliers in
  reporting.

#### Story 9 — Platform breakdown aggregation

Per package, aggregate per-platform downloads over the last 3 months
(`downloads_90d`) and lifetime (`downloads_total`), write to
`package_platform_downloads`. Filter out empty `pkg_platform` (noarch
folds into `''` which becomes a synthetic platform `'noarch'` in the
output table for clarity).

#### Story 10 — Python-version breakdown aggregation

Same pattern as Story 9, against `pkg_python`. Add a data-quality
filter: drop rows where `pkg_python` doesn't match the regex
`^(2\.7|3\.[0-9]{1,2})$` (the parquet contains a few dirty values like
`2.30`, `7.3`, `3.81` — confirmed via inspection on 2026-05-10).

### Wave 3 — New CLIs and MCP tools

#### Story 11 — `platform_breakdown` CLI + MCP tool

Create `.claude/skills/conda-forge-expert/scripts/platform_breakdown.py`
(canonical) and `.claude/scripts/conda-forge-expert/platform_breakdown.py`
(CLI wrapper).

CLI surface:

```
platform-breakdown <package>                  # one-package detail
platform-breakdown --top 50 --platform linux-aarch64    # rank packages by aarch64 share
platform-breakdown --feedstock-roundup        # group by feedstock_name for maintainer triage
```

Reads only from atlas SQLite. Emits markdown table by default, JSON
with `--json`. Add to `pixi.toml` as a task; register as MCP tool in
`conda_forge_server.py`.

#### Story 12 — `pyver_breakdown` CLI + MCP tool

Mirror of Story 11 against `package_python_downloads`. Two
domain-specific modes:

- `pyver-breakdown <package>` — single-package table; calls out the
  smallest python version with ≥2% downloads as the "empirical
  python_min floor."
- `pyver-breakdown --policy-check <package>` — compares the recipe's
  declared `python_min` (read via the existing recipe parser) against
  the empirical floor; flags packages where `python_min` is more
  conservative than the data justifies (i.e., bump-safe candidates).

#### Story 13 — `channel_split` CLI + MCP tool

Aggregates downloads across `data_source` (channels). Unlike Stories 11–12,
this requires reading parquet at query time because the atlas DB only
stores conda-forge data. So:

- Cache the channel-split aggregation in a fourth small table,
  `package_channel_downloads` (`conda_name, data_source, downloads_90d,
  downloads_total`), populated during the Phase F+ sweep (one extra
  group-by, ~negligible cost).
- CLI: `channel-split <package>` — table of channel × download volume
  for the last 90 days; flags packages with significant defaults-channel
  share (>10%) as migration-opportunity targets.

#### Story 14 — Tests, docs, SKILL.md updates

- Unit tests for `_parquet_cache.py` (mock S3 responses, verify cache
  hit/miss logic, verify month list parsing).
- Integration test for Phase F `auto` mode: mocked API failure forces
  S3 path; assert `downloads_source` is set correctly.
- Add `PHASE_F_SOURCE`, `PHASE_F_S3_MONTHS`, `S3_PARQUET_BASE_URL` to
  `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md`.
- Update `.claude/skills/conda-forge-expert/SKILL.md` "Atlas
  Intelligence Layer" section with the new CLIs.
- Update
  `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md`
  with the three new tools mapped to personas (esp.
  `pyver-breakdown --policy-check` under § Feedstock Maintainer →
  Decisions, and `platform-breakdown --feedstock-roundup` under same
  section). Also update the Phase F row in
  `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`
  with the new aggregate tables and CLIs.
- Per CLAUDE.md Rule 2, end with a CHANGELOG.md entry and a
  `bmad-retrospective` run focused on the CFE skill.

---

## Functional Requirements

### FR-1: Air-gap parity (G1)

With `PHASE_F_SOURCE=s3-parquet` and only `*.s3.amazonaws.com` (or a
JFrog-mirrored equivalent) reachable, `pixi run -e local-recipes
build-cf-atlas` must complete Phase F with non-NULL `total_downloads`
for ≥95% of active conda-forge packages.

### FR-2: Online no-regression (G2)

With `PHASE_F_SOURCE=auto` (default) and full network, the atlas's
Phase F output must match the current production behavior — same
columns populated, same TTL gating, same ±0% throughput. Verified by
running both old and new code paths on the same DB snapshot and diffing
the `packages` table.

### FR-3: Source attribution (G3)

Every populated `downloads_*` cell carries a non-NULL `downloads_source`
value (`anaconda-api` | `s3-parquet` | `merged`). MCP tools that emit
download counts (`package_health`, `staleness_report`,
`version_downloads`) include the source in their output.

### FR-4: Cache discipline

- Parquet cache lives under
  `.claude/data/conda-forge-expert/cache/parquet/`; gitignored.
- Current-month file always refreshed on first atlas run of a month
  (timestamp-based).
- `cache_dir` cleanup CLI: `clean-parquet-cache --older-than 12m` for
  operators wanting to bound disk usage.

### FR-5: JFrog routing

S3 HTTPS URLs flow through `_http.py`'s resolver. The env-var sequence
that wins:

1. `S3_PARQUET_BASE_URL` — full base, e.g.
   `https://jfrog.internal/anaconda-package-data` (host + path prefix
   that mirrors S3 layout).
2. `JFROG_API_KEY` or `JFROG_USERNAME+PASSWORD` → injected on requests
   whose host matches `*.jfrog.*` or the `S3_PARQUET_BASE_URL` host.
3. Public S3 HTTPS — fallback.

### FR-6: Schema migration safety

Migration v17 → v18 must run cleanly on:

- Fresh DB (creates new columns / tables alongside existing schema).
- v17 DB with existing Phase F data (adds columns with `NULL` defaults;
  no data loss).
- v18 DB (idempotent — no-op).

### FR-7: New-CLI offline guarantee

`platform_breakdown`, `pyver_breakdown`, and `channel_split` must
complete with zero network access when the atlas DB has been built.
Verified by running them under `unshare -n` (or equivalent) in CI.

### FR-8: Data quality guardrails

- Empty/dirty `pkg_python` values are filtered out of `pyver_breakdown`
  output (Story 10 regex).
- Packages with zero downloads in the last 90 days are omitted from
  "top N" rankings (avoid noise from dead packages).
- Packages first published in the current or previous month are flagged
  as "insufficient history" rather than reported as `downloads_90d=0`.

---

## Technical Approach

### Stack

- **Reader:** `pyarrow.parquet.read_table` with `filters=`. Already
  available via `local-recipes` pixi env. No `duckdb`, no `pandas`, no
  `s3fs`, no `boto3`.
- **HTTP:** existing `_http.py` extended with one new resolver function.
- **Cache:** plain filesystem under existing
  `.claude/data/conda-forge-expert/cache/` tree.
- **Schema:** SQLite migrations in the existing
  `_apply_pending_migrations` framework in `conda_forge_atlas.py`.

### File layout (delta only)

```
.claude/skills/conda-forge-expert/scripts/
  _parquet_cache.py            NEW  (private module, ~120 LOC)
  _http.py                     EDIT (+~40 LOC for S3 resolver)
  conda_forge_atlas.py         EDIT (Phase F refactor; Phase F+ aggregations;
                                     schema v18 migration)
  platform_breakdown.py        NEW  (~150 LOC)
  pyver_breakdown.py           NEW  (~180 LOC; includes --policy-check)
  channel_split.py             NEW  (~120 LOC)

.claude/scripts/conda-forge-expert/
  platform_breakdown.py        NEW  (thin subprocess wrapper)
  pyver_breakdown.py           NEW  (thin subprocess wrapper)
  channel_split.py             NEW  (thin subprocess wrapper)

.claude/tools/
  conda_forge_server.py        EDIT (+3 @mcp.tool registrations)

.claude/data/conda-forge-expert/cache/parquet/    NEW DIR (gitignored)

.claude/skills/conda-forge-expert/
  SKILL.md                     EDIT (Atlas Intelligence Layer + Critical Constraints
                                     section noting api.anaconda.org failure mode)
  CHANGELOG.md                 EDIT (v7.x or v8.0.0 entry per retro semver call)
  quickref/commands-cheatsheet.md  EDIT
  reference/atlas-actionable-intelligence.md    EDIT
  reference/atlas-phases-overview.md            EDIT (Phase F row)

pixi.toml                      EDIT (+3 task entries)

tests/                         EDIT (+new test files; +meta-test SCRIPTS list
                                     per feedback_cfe_new_script_three_places)
```

**Memory checkpoint:** per `feedback_cfe_new_script_three_places`, each
new script touches three places: pixi.toml task + SCRIPTS list in
`test_all_scripts_runnable.py` + wrapper. Story 14 must verify all
three for each of `platform_breakdown`, `pyver_breakdown`,
`channel_split`.

### Schemas

```sql
-- packages additions (migration v18)
ALTER TABLE packages ADD COLUMN downloads_source TEXT;
ALTER TABLE packages ADD COLUMN downloads_30d INTEGER;
ALTER TABLE packages ADD COLUMN downloads_90d INTEGER;
ALTER TABLE packages ADD COLUMN downloads_trend_90d REAL;
ALTER TABLE packages ADD COLUMN first_nonzero_month TEXT;
ALTER TABLE packages ADD COLUMN last_nonzero_month TEXT;

CREATE TABLE IF NOT EXISTS package_platform_downloads (
    conda_name       TEXT NOT NULL,
    pkg_platform     TEXT NOT NULL,
    downloads_90d    INTEGER,
    downloads_total  INTEGER,
    fetched_at       INTEGER,
    PRIMARY KEY (conda_name, pkg_platform)
);
CREATE INDEX idx_ppd_conda_name ON package_platform_downloads(conda_name);

CREATE TABLE IF NOT EXISTS package_python_downloads (
    conda_name       TEXT NOT NULL,
    pkg_python       TEXT NOT NULL,
    downloads_90d    INTEGER,
    downloads_total  INTEGER,
    fetched_at       INTEGER,
    PRIMARY KEY (conda_name, pkg_python)
);
CREATE INDEX idx_ppyd_conda_name ON package_python_downloads(conda_name);

CREATE TABLE IF NOT EXISTS package_channel_downloads (
    conda_name       TEXT NOT NULL,
    data_source      TEXT NOT NULL,
    downloads_90d    INTEGER,
    downloads_total  INTEGER,
    fetched_at       INTEGER,
    PRIMARY KEY (conda_name, data_source)
);
CREATE INDEX idx_pcd_conda_name ON package_channel_downloads(conda_name);

-- existing package_version_downloads gets a source column
ALTER TABLE package_version_downloads ADD COLUMN source TEXT;
```

### Env-var matrix (final)

| Var | Default | Purpose |
|---|---|---|
| `PHASE_F_SOURCE` | `auto` | `auto` / `anaconda-api` / `s3-parquet` |
| `PHASE_F_DISABLED` | unset | (existing) skip Phase F entirely |
| `PHASE_F_TTL_DAYS` | `7` | (existing) per-row skip cutoff |
| `PHASE_F_CONCURRENCY` | `8` | (existing) API worker pool |
| `PHASE_F_LIMIT` | `0` | (existing) row cap for debugging |
| `PHASE_F_S3_MONTHS` | `0` (= all) | trailing months to load from S3 |
| `S3_PARQUET_BASE_URL` | unset | enterprise mirror override |
| `ANACONDA_API_BASE` | unset | (existing) enterprise API mirror |
| `CONDA_FORGE_BASE_URL` | unset | (existing) enterprise channel mirror |
| `JFROG_API_KEY` / `JFROG_USERNAME` / `JFROG_PASSWORD` | unset | (existing) injected by `_http.py` |

### Key decisions

- **Why not `s3fs` / `boto3`?** Anonymous public-read of static URLs
  doesn't justify the dep weight. Direct HTTPS via `_http.py` reuses
  the JFrog auth path we already maintain.
- **Why not store full monthly time-series in SQLite?** 32k pkgs ×
  110 months ≈ 3.5M rows of low-value data. The aggregated derivatives
  (rolling 30/90-day, trend, first/last nonzero) deliver 90% of the
  utility at ~32k rows. Operators wanting the full series can read the
  parquet directly.
- **Why one consolidated parquet sweep instead of streaming?** All
  Phase F+ metrics (rolling windows, trend, platform/python/channel
  breakdowns) derive from the same data — running them as one pyarrow
  pass with multiple group-bys is much cheaper than 5 separate passes.
- **Why `auto` mode probes with `pip`?** It's the most-downloaded
  package; the API call returns a small payload (~5KB metadata) but
  reliably exercises the same code path as the real fetches. A failure
  there is a strong signal the rest will fail.
- **Why cap `downloads_trend_90d` at +10.0?** New packages can show
  +1000% growth (1 download → 1000 downloads in 3 months); uncapped,
  they dominate "top growing" rankings. +10.0 (1000%) is the threshold
  beyond which the signal stops being useful for triage.

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** `pixi run -e local-recipes build-cf-atlas` with
  `PHASE_F_SOURCE=s3-parquet` and `*.anaconda.org` blocked at the
  network level populates `total_downloads` for ≥95% of active
  conda-forge packages.
- **AC-2.** `pixi run -e local-recipes build-cf-atlas` with default
  env (no `PHASE_F_SOURCE` set, `*.anaconda.org` reachable) produces
  output that diffs identically against pre-change behavior on the
  `total_downloads`, `latest_version_downloads`,
  `downloads_fetched_at`, `downloads_fetch_attempts`,
  `downloads_last_error` columns.
- **AC-3.** `staleness_report`, `package_health`, `version_downloads`
  MCP tools include `downloads_source` in their response payloads.
- **AC-4.** New CLIs `platform-breakdown`, `pyver-breakdown`,
  `channel-split` each run end-to-end against a real
  `local-recipes`-built atlas DB and emit sensible markdown +
  `--json`.
- **AC-5.** `pyver-breakdown --policy-check requests` (or any other
  popular package) returns an empirical python_min suggestion that's
  internally consistent with the per-version download distribution.
- **AC-6.** `unshare -n env PHASE_F_SOURCE=s3-parquet pixi run …` —
  or equivalent network-disabled test — fails with a clear error
  pointing at S3, NOT with a cryptic socket error.
- **AC-7.** Re-running with a pre-warmed cache completes the parquet
  step in <5 seconds; verified by timing log.
- **AC-8.** All three new scripts pass the
  `test_all_scripts_runnable.py` meta-test (i.e., the SCRIPTS list +
  pixi.toml task + wrapper trio per the
  `feedback_cfe_new_script_three_places` rule).
- **AC-9.** CHANGELOG.md has a new version entry (PATCH if no
  unexpected gotchas surfaced; MINOR if new ones did); the retro
  CHANGELOG entry references this spec by filename.

---

## Open Questions

### Must answer (v1-blocking)

- **OQ-1.** Should `auto` mode's API failure trigger an S3 backfill for
  *only the failed rows*, or fall back to the bulk S3 read for *all
  rows*? Bulk is simpler and pre-warms the cache; per-row is more
  precise. Recommendation: bulk-fallback on probe failure; per-row
  marker only when the API path mostly worked but had isolated 5xxs.
- **OQ-2.** Is `pip` the right reachability probe target, or should it
  be a hash-stable "canary" package the team owns? `pip` is robust to
  Anaconda Inc. reorganizations of its API; a canary is more
  deterministic but adds maintenance burden. Recommendation: `pip`.

### Behavior — confirm or override

- **OQ-3.** Should `downloads_source='merged'` apply when EITHER the
  per-package total OR the per-version table was sourced from S3 (not
  both)? Recommendation: yes, to make the discriminator broadly
  meaningful as "treat this row's download data as approximate."
- **OQ-4.** Should the S3 backfill respect `PHASE_F_LIMIT`? In API
  mode, limit caps per-row HTTP requests. In S3 mode, the cost is one
  big read regardless of row count. Recommendation: limit caps which
  rows get *written* (post-aggregation slice), not which rows get
  read.

### v2 — explicitly deferred

- **OQ-5.** `condastats`-style pip install path for users who don't
  want `pyarrow` directly? Defer to user request; `pyarrow` is already
  in env.
- **OQ-6.** Full per-month time-series materialized in SQLite for use
  in dashboards? Defer; the parquet cache is the source for that.
- **OQ-7.** Daily granularity via anaconda.org S3 `daily/` prefix
  (if it exists — unconfirmed)? Defer; verify the prefix exists before
  speccing.

### Genuinely open (design call)

- **OQ-8.** Should `find_alternative` rank candidates with the new
  `downloads_90d` instead of cumulative `total_downloads`? Recent
  activity is a better "is this maintained" signal but breaks
  ranking-stability across atlas rebuilds. Defer to Wave 3 user
  feedback.

---

## Dependencies and Constraints

- **`pyarrow`** — already in `local-recipes` pixi env via pandas.
  Verified.
- **Python 3.11+** — same baseline as the atlas pipeline today.
- **No new top-level deps.** Stays inside the existing env footprint.
- **Conda-forge atlas DB at v17+** before migration to v18. Migration
  framework handles the version bump itself.
- **`_http.py`** must already inject SSL truststore + JFrog auth
  (verified; the existing code path handles this for conda-forge
  channel URLs and will extend cleanly to S3).
- **CLAUDE.md Rule 1** (BMAD invokes `conda-forge-expert` first) and
  **Rule 2** (effort closes with a CFE-skill retro) apply.

---

## Out of Scope (Explicit)

- **OoS-1.** Mirroring the S3 dataset to a non-AWS location is the
  operator's problem; the spec provides the env-var hooks
  (`S3_PARQUET_BASE_URL`) but doesn't ship mirroring tooling.
- **OoS-2.** Backfilling `package_version_downloads.upload_unix` from
  some third source when S3 is used as the data source. The column is
  set to `NULL` and tagged `source='s3-parquet'`; consumers must
  tolerate missing upload times in that case.
- **OoS-3.** `bioconda`-channel or `pytorch`-channel atlas pipelines.
  The parquet sweep reads only `data_source='conda-forge'`. The
  channel-split CLI surfaces the others for awareness but doesn't
  build an atlas over them.
- **OoS-4.** Reconciling specific numeric discrepancies between API
  and S3. The `downloads_source` discriminator is the documentation;
  fixing the upstream is Anaconda Inc.'s call.
- **OoS-5.** Web dashboards consuming the new tables. MCP tools and
  CLIs only.

---

## References

### Code (source of truth)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`
  Phase F at `phase_f_downloads` (~L1453); Phase I side-effect at
  `package_version_downloads` schema (~L233).
- `.claude/skills/conda-forge-expert/scripts/_http.py` — JFrog auth
  chain at `_make_req`; conda-forge URL resolver at
  `resolve_conda_forge_urls`.
- `.claude/tools/conda_forge_server.py` — `@mcp.tool` registration
  pattern for the three new tools.

### Documentation

- `.claude/skills/conda-forge-expert/SKILL.md` — Atlas Intelligence
  Layer section; Critical Constraints; Operating Principles.
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md`
  — persona map for the new CLIs.
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`
  — Phase F row gets the new aggregate tables and CLIs.
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md`
  — env-var matrix lands here.
- `docs/enterprise-deployment.md` — JFrog routing context; the air-gap
  case study this spec resolves.

### External

- Public S3 bucket: `https://anaconda-package-data.s3.amazonaws.com/`
  — list endpoint: `?list-type=2&prefix=conda/monthly/`.
- condastats: `https://github.com/conda-incubator/condastats` —
  reference implementation, not a dependency.
- condastats relaunch announcement:
  `https://conda.org/blog/condastats-is-back/` — confirms the dataset
  is live and updated monthly.

### Memory

- `feedback_cfe_new_script_three_places.md` — each new script touches
  pixi.toml + SCRIPTS list + wrapper.
- `project_cf_atlas_rattler_502.md` — context on why Phase B uses
  `current_repodata.json` (parallel rationale: HTTPS-static URLs are
  more enterprise-friendly than fancier protocols).
- `project_cf_atlas_suite.md` — atlas evolves quickly; this spec
  bumps to **v8.0.0** (MINOR for new schema + tools, MAJOR if Wave 1
  ships with a behavior change to `total_downloads` defaults — retro
  team decides).

---

## Suggested BMAD Invocation

```
# From repo root:
run quick-dev — implement the intent in docs/specs/atlas-phase-f-s3-backend.md

# Wave-by-wave execution recommended:
# - Wave 0+1 in one pass (foundations + air-gap fix; ships value alone)
# - Wave 2 in a second pass (Phase F+ metrics)
# - Wave 3 in a third pass (new CLIs / MCP tools)
# Close with bmad-retrospective per CLAUDE.md Rule 2.
```
