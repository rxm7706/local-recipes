---
status: shipped
implemented_by: bmad-quick-dev
shipped_ref: "Wave 1: v7.6.0 + v8.17.0; Wave 2: v8.18.0; Wave 3: v8.19.0"
spec_updated: 2026-07-02
---
> **Consolidated record (2026-07-02).** This file merges the three shipped Phase F / Phase F+
> intake specs into one historical record:
>
> - **[Part 1](#part-1)** — the original S3/parquet-backend umbrella spec (this file's original
>   body). Shipped **v7.6.0** (S3 backend + `PHASE_F_SOURCE` dispatcher) + **v8.17.0** (admin
>   profile default-flip).
> - **[Part 2](#part-2)** — the Wave 2 richer-metrics focused intake (formerly
>   `atlas-phase-f-wave2-richer-metrics.md`). Shipped **v8.18.0** (commit f28ed3ea56, 2026-06-13);
>   the v8.18.1 retro landed sub-rules (g)/(h)/(i) in `reference/atlas-phase-engineering.md` § 10.
> - **[Part 3](#part-3)** — the Wave 3 CLI-surface focused intake (formerly
>   `atlas-phase-f-wave3-cli-surface.md`). Shipped **v8.19.0** (commit d5095dde18, 2026-06-13);
>   the v8.19.1 retro landed sub-rules (j)/(k) in `reference/atlas-phase-engineering.md` § 10.
>
> Part bodies are preserved verbatim from the pre-merge files; only frontmatter was consolidated
> and cross-file links between the three parts rewritten to in-file anchors. Textual mentions of
> the two former filenames inside part bodies are historical and refer to the parts above.

<a id="part-1"></a>

# Part 1 — S3/parquet backend umbrella spec (Waves 0–1)

> Original frontmatter before the merge: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v7.6.0 + v8.17.0 (Wave 1; Waves 2-3 split to wave2/wave3 specs)"; spec_updated: 2026-06-20`

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


---

<a id="part-2"></a>

# Part 2 — Wave 2 focused intake: richer metrics

> Original frontmatter before the merge: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v8.18.0"; spec_updated: 2026-06-20`

# Tech Spec: Atlas Phase F+ Wave 2 — richer metrics from the existing parquet sweep

> **BMAD intake document.** Focused execution scope for `bmad-quick-dev`
> (Quick Flow track — well-bounded, single-skill, ~5 stories).
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-f-wave2-richer-metrics.md
> ```
>
> **Parent spec** (canonical detail): [`docs/specs/atlas-phase-f-s3-backend.md`](#part-1).
> This brief is the **subset** of that spec scoped to Wave 2 (stories
> 3, 7, 8, 9, 10). Wave 1 (S3 backend + dispatcher + `downloads_source`
> provenance column) already shipped in v7.6.0; Wave 1 default-flip for
> `--profile admin` shipped in v8.17.0. Wave 3 (new operator CLIs)
> waits for Wave 2 and ships as a separate effort.
>
> **Per `CLAUDE.md` Rule 1**, any BMAD agent executing this brief MUST
> invoke the `conda-forge-expert` skill before touching atlas code.
> Per Rule 2, the effort closes with a CFE-skill retrospective and a
> `CHANGELOG.md` entry.

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (no separate PRD / architecture phase — parent spec carries those) |
| Scope | (1) Schema migration v26 → v27; (2) rolling 30/90-day downloads + trend slope; (3) per-platform + per-Python download breakdowns. All computed in one extra parquet sweep — zero new network. |
| Out of scope | Wave 3 CLIs (`platform_breakdown`, `pyver_breakdown`, `channel_split`); daily-granularity downloads; defaults-channel atlas |
| Predecessor | `atlas-phase-f-s3-backend.md` Wave 1 (shipped v7.6.0 + v8.17.0) |
| Successor | Wave 3 CLI brief (to be written when Wave 2 lands) |
| Created | 2026-06-13 |

---

## Background and Context

The Phase F S3 backend already exists. `_phase_f_via_s3` in
`scripts/conda_forge_atlas.py` reads monthly parquet files from
`anaconda-package-data.s3.amazonaws.com` and writes the
`packages.total_downloads` + `latest_version_downloads` columns. The
parquet schema is:

```
time | data_source | pkg_name | pkg_version | pkg_platform | pkg_python | counts
```

— 6 dimensions, 1 metric, ~13 MB per month, ~110 months of history available. Wave 1 consumes
3 of the 6 dimensions (`time`, `pkg_name`, `counts`) and aggregates to
`(pkg_name → total)`. The 3 unused dimensions are sitting in the byte stream.

Wave 2 adds three more aggregations on the same cached parquet bytes:

1. **Rolling-window cuts** (`time` × `counts` filtered to N trailing months) — adoption signals comparable to the `pypi_intelligence` table's `downloads_30d/90d` columns, but for the conda-forge namespace.
2. **Trend slope** (rolling-window-now vs. rolling-window-prior ratio) — direction signal: growing vs. declining.
3. **Per-platform** and **per-Python** breakdowns (`pkg_platform` / `pkg_python` group-bys) — maintainer-triage data: how much of a package's traffic is ARM64? Python 3.8? defaults? Currently this requires reading parquet at query-time; we materialize it into the atlas DB so consumer CLIs are offline-safe.

The same parquet sweep produces all three. No new HTTP calls. No new top-level dependencies.

### What's already shipped (do not re-implement)

- `_parquet_cache.py` (Wave 0 Story 2) — month-list + per-month cache + filtered reader.
- `_http.py` S3 routing with `S3_PARQUET_BASE_URL` + JFrog auth (Wave 0 Story 1).
- `_phase_f_via_s3` (Wave 1 Story 5) — current parquet aggregation that populates `total_downloads`.
- `packages.downloads_source` provenance column (Wave 1 Story 3) — already accepts `{'anaconda-api', 's3-parquet', 'merged'}`.
- `PROFILES["admin"]["PHASE_F_SOURCE"] = "s3-parquet"` (v8.17.0) — admin runs hit the parquet path by default.

### Schema target — important correction vs. parent spec

The parent spec (written 2026-05-10) assumed migration `v17 → v18`.
Current schema is **v26** (verified 2026-06-13 via
`SCHEMA_VERSION = 26` at `conda_forge_atlas.py:137`). Wave 2's migration target is
**v26 → v27**.

---

## Goals

- **G1.** Populate three new rolling-window columns on `packages`: `downloads_30d`, `downloads_90d`, `downloads_trend_90d`.
- **G2.** Populate two new lifetime-history columns on `packages`: `first_nonzero_month`, `last_nonzero_month`.
- **G3.** Materialize per-platform breakdown into a new table `package_platform_downloads`.
- **G4.** Materialize per-Python-version breakdown into a new table `package_python_downloads`.
- **G5.** All five additions computed in **one** extended parquet sweep that runs in the existing `_phase_f_via_s3` path — no extra network, no separate phase.
- **G6.** Schema migration v26 → v27 is forward-only and idempotent (same pattern as existing additions).

---

## Non-Goals

- **NG1.** No new CLIs or MCP tools — those are Wave 3, separate ship.
- **NG2.** No backfill of channels other than `conda-forge` (parent spec NG2).
- **NG3.** No daily granularity (parent spec NG1 — S3 publishes monthly only).
- **NG4.** No retro-fitting the API path. `_phase_f_via_api` continues to populate only `total_downloads` + `latest_version_downloads`; the new columns stay `NULL` when `downloads_source='anaconda-api'`. Consumers detect via `downloads_source`.
- **NG5.** No materialization of full per-(package, platform, month) time-series (38M rows). We aggregate to the cuts we need: 90-day rollup and lifetime totals. Per-month detail stays in the parquet cache, queryable on demand by Wave 3 if needed.

---

## User Stories

### Story 1 — Schema migration v26 → v27

Add columns to `packages` table:

- `downloads_30d INTEGER` — sum of `counts` over the most recent month (monthly resolution; documented as such).
- `downloads_90d INTEGER` — sum of `counts` over the last 3 months available.
- `downloads_trend_90d REAL` — `(downloads_90d - downloads_prev_90d) / downloads_prev_90d` where `downloads_prev_90d` is months 4-6 trailing. `NULL` when either window is zero (avoid div-by-zero) or fewer than 6 months of data exist. Capped at `+10.0` to dampen new-package outliers.
- `first_nonzero_month TEXT` — `'YYYY-MM'` of earliest non-zero month.
- `last_nonzero_month TEXT` — `'YYYY-MM'` of most recent non-zero month.

Add two new tables:

```sql
CREATE TABLE IF NOT EXISTS package_platform_downloads (
    conda_name        TEXT NOT NULL,
    pkg_platform      TEXT NOT NULL,
    downloads_90d     INTEGER NOT NULL,
    downloads_total   INTEGER NOT NULL,
    fetched_at        INTEGER NOT NULL,
    PRIMARY KEY (conda_name, pkg_platform)
);
CREATE INDEX IF NOT EXISTS idx_package_platform_downloads_conda_name
    ON package_platform_downloads(conda_name);

CREATE TABLE IF NOT EXISTS package_python_downloads (
    conda_name        TEXT NOT NULL,
    pkg_python        TEXT NOT NULL,
    downloads_90d     INTEGER NOT NULL,
    downloads_total   INTEGER NOT NULL,
    fetched_at        INTEGER NOT NULL,
    PRIMARY KEY (conda_name, pkg_python)
);
CREATE INDEX IF NOT EXISTS idx_package_python_downloads_conda_name
    ON package_python_downloads(conda_name);
```

Migration is forward-only and follows the existing
`_apply_pending_migrations` pattern. Bump `SCHEMA_VERSION` from 26 to 27.
Add an entry to the migrations list and update
`tests/meta/test_schema_migration.py` if it asserts on the version number.

### Story 2 — Rolling 30 / 90-day download windows + lifetime months

Extend `_phase_f_via_s3` to compute, in the same parquet pass:

- `downloads_30d` = SUM(counts) WHERE time == most-recent available month.
  Documented as "single-month resolution at monthly granularity";
  callers needing finer resolution must consult `pypi_intelligence`.
- `downloads_90d` = SUM(counts) WHERE time IN (last 3 months available).
- `first_nonzero_month` = MIN(time) WHERE counts > 0.
- `last_nonzero_month` = MAX(time) WHERE counts > 0.

All four computed in one pyarrow group-by. Bulk-update `packages` in
batches of 500 (same transaction pattern as Wave 1).

### Story 3 — 90-day trend slope

Compute `downloads_trend_90d` as
`(downloads_90d - downloads_prev_90d) / downloads_prev_90d`
where `downloads_prev_90d` = SUM(counts) over months 4-6 trailing.

- Returns `NULL` if either window has zero downloads (avoid
  ZeroDivisionError) or if fewer than 6 months of data exist for the
  package.
- Sign convention: positive = growing, negative = declining.
- Cap at `+10.0` to dampen new-package "infinite growth" outliers in
  downstream reporting.

Same parquet sweep as Story 2 — one additional aggregation, no new
reads.

### Story 4 — Per-platform breakdown

In the same parquet sweep, group by `(pkg_name, pkg_platform)` for:

- `downloads_90d` (last 3 months)
- `downloads_total` (lifetime)

Bulk-insert into `package_platform_downloads` (Story 1 table) with
`fetched_at = current Unix time`. Use `INSERT OR REPLACE` keyed on
`(conda_name, pkg_platform)`.

Filter out empty `pkg_platform` values — noarch packages have
`pkg_platform=''` in the parquet; map them to a synthetic `'noarch'`
platform string for clarity in output tables.

### Story 5 — Per-Python-version breakdown + data-quality regex

Mirror Story 4 against `pkg_python` into `package_python_downloads`.

**Data-quality filter (parent spec Story 10 caveat).** The parquet
contains dirty `pkg_python` values like `2.30`, `7.3`, `3.81`
(confirmed via inspection 2026-05-10). Drop rows where `pkg_python`
doesn't match `^(2\.7|3\.[0-9]{1,2})$`. Document the regex in code
comments so future maintainers know why it's there.

### Story 6 — Tests, docs, SKILL.md updates, CHANGELOG, retro

- **Schema migration test** (`tests/meta/test_schema_migration.py`
  or equivalent) — assert `SCHEMA_VERSION == 27`, columns exist with
  correct types, new tables exist with correct columns, indexes
  created.
- **Aggregation correctness tests** (unit) — given a known parquet
  fixture, verify per-story numbers come out right. Specifically:
  trend slope NULL on insufficient data; trend slope cap at +10.0;
  per-platform/per-python `INSERT OR REPLACE` idempotency; dirty
  `pkg_python` regex filter (e.g. `7.3` dropped, `3.11` kept).
- **Integration test** — mock parquet pull, run `_phase_f_via_s3`
  end-to-end, assert all five new columns + both new tables populated.
- **Reference doc updates** —
  `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`
  Phase F section gains the new columns/tables and updates the
  "what gets written" bullet.
- **Actionable-intelligence catalog** —
  `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md`
  gets new rows for `downloads_30d/90d`, `downloads_trend_90d`,
  per-platform/per-python tables — marked `✅ shipped (v8.<NEW>.0)`.
- **CHANGELOG.md** entry per CLAUDE.md Rule 2. MINOR bump
  (additive — new columns + new tables; no breaking).
- **CFE-skill retrospective** per CLAUDE.md Rule 2 — focused on what
  this Wave 2 effort surfaced that future Phase F+ work or future
  parquet-sweep extensions should know.

---

## Functional Requirements

### FR-1: Same-sweep computation

All five new outputs (3 columns + 2 tables) must be computed in **one**
extended `_phase_f_via_s3` pass. No additional `urlopen` calls relative
to current Wave 1 behavior. Verified by net-call assertion in
integration test.

### FR-2: Source attribution

The new columns + new tables are populated **only** when
`packages.downloads_source = 's3-parquet'` (or `'merged'`). Rows with
`downloads_source = 'anaconda-api'` retain `NULL` for the new columns
and have no rows in the new tables. Consumers tolerating missing
metrics check `downloads_source` first.

### FR-3: Trend slope discipline

- `NULL` when either window is empty or fewer than 6 months of data.
- Capped at `+10.0` (i.e. 1000% growth) to dampen new-package outliers.
- Sign: positive = growing, negative = declining.
- Floored at `-1.0` is implicit (downloads can't go below zero).

### FR-4: Data-quality filter on `pkg_python`

Dirty values like `2.30`, `7.3`, `3.81` MUST be dropped before
aggregation. Regex `^(2\.7|3\.[0-9]{1,2})$` documented in code comments
with the inspection-date provenance.

### FR-5: Idempotent table writes

`package_platform_downloads` + `package_python_downloads` use
`INSERT OR REPLACE` keyed on PK. Re-running Phase F replaces, doesn't
accumulate. `fetched_at` tracks the most recent write.

### FR-6: Schema migration safety

Migration v26 → v27 runs cleanly on:

- Fresh DB (`--fresh`).
- Existing v26 DB (in-place upgrade).
- Already-v27 DB (idempotent no-op).

Verified by `tests/meta/test_schema_migration.py` covering all three
paths.

---

## Technical Approach

### Where the code lands

- **`scripts/conda_forge_atlas.py`** — `_phase_f_via_s3` extended.
  Schema migration entry added to `_apply_pending_migrations`.
  `SCHEMA_VERSION` bumped 26 → 27.
- **`scripts/_parquet_cache.py`** — likely no changes. If a
  read-path helper makes the multi-aggregation cleaner, add it here.
- **`tests/unit/test_phase_f_s3.py`** (or wherever current
  `_phase_f_via_s3` is tested) — extended with the new assertions.
- **`tests/meta/test_schema_migration.py`** — updated to v27.

### Key implementation notes

- **One read, multiple aggregations.** pyarrow tables are zero-copy
  views; pass the same loaded Table to multiple group-by passes
  without re-reading the parquet file.
- **Memory budget.** A 12-month rolling window of conda-forge data is
  ~150 MB of parquet → ~600-900 MB pyarrow Table in memory. Acceptable
  for the local-recipes env's typical 16+ GB host. If this surfaces as a
  concern, fall back to per-month streaming aggregation with a
  running-dict accumulator — but only if profiling shows it matters.
- **Trend slope's prior-90d window.** Months 4-6 trailing from
  `last_nonzero_month` (not from today's calendar) so the trend isn't
  thrown off by recently-uploaded packages that have a 6-month
  hiatus before activity began.

### Env-var matrix (no new env vars)

Wave 2 ships with **no new env vars**. The existing `PHASE_F_SOURCE` /
`PHASE_F_S3_MONTHS` / `S3_PARQUET_BASE_URL` cover the new behavior. If
operators want to disable just the breakdown tables (e.g. to save the
~50 MB they'd add to the DB), they can already use
`PHASE_F_SOURCE=anaconda-api` to skip the parquet path entirely. Don't
add a separate disable knob unless real demand surfaces.

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** Schema migration v26 → v27 runs cleanly on fresh + existing
  + already-migrated DBs. Tests cover all three.
- **AC-2.** After running `--profile admin` against a populated DB,
  `packages.downloads_30d` is non-NULL for ≥95% of rows with
  `downloads_source = 's3-parquet'`.
- **AC-3.** `downloads_trend_90d` is non-NULL for ≥80% of packages
  with `first_nonzero_month` more than 6 months in the past.
- **AC-4.** `package_platform_downloads` contains ≥1 row per package
  with non-empty `pkg_platform` in the parquet.
- **AC-5.** `package_python_downloads` contains only rows matching
  the data-quality regex; no `7.3`, `3.81`, `2.30` values present.
- **AC-6.** Phase F wall-clock under `--profile admin --fresh` does
  NOT increase by more than 30 seconds vs. v8.17.0 baseline (parquet
  is already loaded; new aggregations are cheap).
- **AC-7.** The whole test suite passes (`pixi run -e local-recipes
  test`) with no new failures introduced.
- **AC-8.** Per CLAUDE.md Rule 2: a CHANGELOG.md entry lands, a
  retrospective runs against the CFE skill, and the actionable-
  intelligence catalog rows for the new signals flip from `📋 open`
  to `✅ shipped (v8.<NEW>.0)`.

---

## Open Questions

### Pre-resolved (recommendations)

- **OQ-1.** Should `downloads_30d` use calendar-month or rolling-30-day
  resolution? **Recommendation: calendar-month** — that's what the
  parquet gives natively (monthly cadence). Rolling-30-day would
  require per-day data the parquet doesn't carry. Document explicitly:
  "single most-recent month at monthly resolution, not 30 calendar
  days from today." Aligns with parent spec Story 7.

- **OQ-2.** Should `last_nonzero_month` exclude the current
  (in-progress) month? **Recommendation: no** — include it. The
  parquet's current-month file updates daily; whatever value is
  cached reflects the actual data and is the right thing to surface.
  Document the staleness: "current-month value reflects parquet
  refresh time; consult `downloads_fetched_at` for staleness."

- **OQ-3.** Cap `downloads_trend_90d` at `+10.0` (per parent spec)
  but also floor at what? **Recommendation: floor at `-1.0`** — a
  100% decline is the worst case (zero downloads); negative-infinity
  values are nonsense. Per Story 3 FR-3.

### Genuinely open (design call — get user input at intake)

- **OQ-4.** Should v8.<NEW>.0 ship trigger an opportunistic Phase F
  re-run on `--profile admin` even when the TTL hasn't expired, so
  operators see populated v8.<NEW> columns on first run after upgrade?
  Cost: ~30-60 seconds re-aggregating the cached parquet. Benefit:
  immediately-useful new columns instead of a 7-day wait for TTL
  expiry. **Recommendation: yes** — add `PHASE_F_FORCE_REFRESH=1`
  env tag that the v8.<NEW> migration step sets once on the first
  post-migration run, then clears. Operators can also set it
  manually.

- **OQ-5.** Should the breakdown tables track `first_nonzero_month` /
  `last_nonzero_month` per (package, platform) and per (package,
  python) too? **Recommendation: no** — that's 38M rows of dimension
  history; Wave 2 sticks to 90-day + lifetime totals. If demand
  surfaces later, add as Wave 4.

---

## Dependencies and Constraints

- **`pyarrow`** — already in the `local-recipes` pixi env (Wave 0).
  Verified.
- **Atlas schema** at v26 prior to migration. Verified
  `SCHEMA_VERSION = 26` at `scripts/conda_forge_atlas.py:137` on
  2026-06-13.
- **`_phase_f_via_s3`** as the integration point. Wave 1 implementation
  intact.
- **CLAUDE.md Rules 1 + 2** apply (CFE skill invocation + closeout retro).
- **No new top-level dependencies.** Stays inside the existing env footprint.

---

## Out of Scope (Explicit)

- **OoS-1.** Wave 3 CLIs (`platform_breakdown`, `pyver_breakdown`,
  `channel_split`). Separate effort once Wave 2 lands.
- **OoS-2.** API-path retrofit. `_phase_f_via_api` keeps its
  current 2-column output; the new columns stay NULL when source is
  `anaconda-api`.
- **OoS-3.** Daily-granularity downloads, defaults-channel atlas,
  per-build-hash detail — all carry through from parent spec NG1,
  NG2, NG5.
- **OoS-4.** Schema migration tooling improvements. The existing
  `_apply_pending_migrations` pattern is sufficient; don't fold
  refactor work into Wave 2.

---

## References

### Parent spec (source of truth for detail)

- [`docs/specs/atlas-phase-f-s3-backend.md`](#part-1)
  — full Wave 0 + 1 + 2 + 3 detail. This brief is the Wave 2 subset.

### Code (entry points)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`
  — `_phase_f_via_s3` (extend), `SCHEMA_VERSION` (bump),
  `_apply_pending_migrations` (add migration entry).
- `.claude/skills/conda-forge-expert/scripts/_parquet_cache.py`
  — likely no changes; existing reader is enough.

### Tests

- `.claude/skills/conda-forge-expert/tests/unit/test_phase_f_s3.py`
  (or wherever current Wave 1 tests live — confirm path at intake).
- `.claude/skills/conda-forge-expert/tests/meta/test_schema_migration.py`
  — update for v27.

### Documentation to update

- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`
  — Phase F section + catalog row.
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md`
  — new rows for the 5 new signals.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — new entry per
  Rule 2.
- `.claude/skills/conda-forge-expert/config/skill-config.yaml`
  — version bump.


---

<a id="part-3"></a>

# Part 3 — Wave 3 focused intake: CLI surface

> Original frontmatter before the merge: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v8.19.0"; spec_updated: 2026-06-20`

# Tech Spec: Atlas Phase F+ Wave 3 — `platform_breakdown` / `pyver_breakdown` / `channel_split` CLIs + MCP

> **BMAD intake document.** Focused execution scope for `bmad-quick-dev`
> (Quick Flow track — well-bounded, single-skill, ~6 stories).
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-f-wave3-cli-surface.md
> ```
>
> **Parent specs** (canonical detail):
> - [`docs/specs/atlas-phase-f-s3-backend.md`](#part-1) — full Wave 0–3 design (Stories 11/12/13/14 are Wave 3).
> - [`docs/specs/atlas-phase-f-wave2-richer-metrics.md`](#part-2) — Wave 2 brief (shipped as v8.18.0).
>
> Wave 1 (S3 backend + dispatcher + provenance column) shipped in v7.6.0;
> Wave 1 admin default-flip in v8.17.0; Wave 2 (richer metrics + breakdown
> tables) in v8.18.0. Wave 3 ships the consumer-facing CLIs that read the
> Wave 2 tables.
>
> **Per `CLAUDE.md` Rule 1**, any BMAD agent executing this brief MUST
> invoke the `conda-forge-expert` skill before touching atlas code.
> Per Rule 2, the effort closes with a CFE-skill retrospective and a
> `CHANGELOG.md` entry.

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (parent spec carries PRD/architecture detail) |
| Scope | (1) `platform_breakdown` CLI + MCP tool; (2) `pyver_breakdown` CLI + MCP tool incl. `--policy-check`; (3) `channel_split` CLI + MCP tool; (4) Wave 2 leftover — populate `package_channel_downloads` during the existing parquet sweep so `channel_split` has data to read. |
| Out of scope | Wave 4 richer metrics; new aggregation tables beyond `package_channel_downloads`; recipe-format consumers (the CLIs are read-only) |
| Predecessor | `atlas-phase-f-wave2-richer-metrics.md` (shipped v8.18.0) |
| Successor | none planned |
| Created | 2026-06-13 |

---

## Background and Context

Wave 2 (v8.18.0) materialized two read-side tables in the atlas DB:

- `package_platform_downloads(conda_name, pkg_platform, downloads_90d, downloads_total, fetched_at)`
- `package_python_downloads(conda_name, pkg_python, downloads_90d, downloads_total, fetched_at)`

Both populated from the same `_phase_f_via_s3` parquet sweep that runs under `--profile admin`. No CLI exposes them yet — they exist for Wave 3 to consume.

Wave 3 ships **three new operator CLIs**, each backed by an existing Wave 2 table (plus one minor Wave 2 leftover for channel_split):

1. **`platform_breakdown`** — reads `package_platform_downloads`. Maintainer-triage signal for "should I drop osx-x86_64 from feedstock X?" questions.
2. **`pyver_breakdown`** — reads `package_python_downloads`. Includes a `--policy-check` flag that compares the recipe's declared `python_min` against the empirical downloads floor and flags bump-safe candidates.
3. **`channel_split`** — reads a NEW `package_channel_downloads` table that Wave 3 adds + populates during the existing parquet sweep. Surfaces packages with significant defaults-channel share (migration opportunity targets).

All three CLIs are **offline-safe by construction** — they read only from `cf_atlas.db`, never from the network. They're symmetric in shape to existing CLIs (`staleness-report`, `feedstock-health`, `behind-upstream`): markdown table by default, `--json` for machine output, `--top N` for ranking, `--feedstock-roundup` where applicable.

### What's already shipped (do not re-implement)

- `package_platform_downloads` + `package_python_downloads` tables — v8.18.0 schema v27.
- `_phase_f_via_s3` extended parquet sweep — v8.18.0; reads 6 parquet dimensions.
- `downloads_30d` / `downloads_90d` / `downloads_trend_90d` / `first_nonzero_month` / `last_nonzero_month` on `packages` — v8.18.0.
- `PHASE_F_FORCE_REFRESH=1` sentinel + env-var — v8.18.0.
- CLI wrapper pattern (`.claude/scripts/conda-forge-expert/<name>.py` → `python .claude/skills/conda-forge-expert/scripts/<name>.py`) — used by every existing CLI.
- MCP tool registration pattern in `.claude/tools/conda_forge_server.py` — 30+ tools already registered.

### Schema target

Wave 3 adds **one new table** for channel_split:

```sql
CREATE TABLE IF NOT EXISTS package_channel_downloads (
    conda_name        TEXT NOT NULL,
    data_source       TEXT NOT NULL,   -- channel: conda-forge / bioconda / defaults / etc.
    downloads_90d     INTEGER NOT NULL,
    downloads_total   INTEGER NOT NULL,
    fetched_at        INTEGER NOT NULL,
    PRIMARY KEY (conda_name, data_source)
);
CREATE INDEX IF NOT EXISTS idx_package_channel_downloads_conda_name
    ON package_channel_downloads(conda_name);
```

**Schema migration**: v27 → v28. Same forward-only + IF NOT EXISTS pattern as v8.18.0. No new columns on `packages`.

---

## Goals

- **G1.** `platform_breakdown` CLI + MCP tool reading `package_platform_downloads` with three modes: single-package detail, `--top N --platform <p>` ranking, `--feedstock-roundup` maintainer grouping.
- **G2.** `pyver_breakdown` CLI + MCP tool reading `package_python_downloads` with a `--policy-check <pkg>` flag that surfaces the empirical Python floor vs. the recipe's declared `python_min`.
- **G3.** `channel_split` CLI + MCP tool reading a new `package_channel_downloads` table, with a defaults-channel-share filter (>10% by default).
- **G4.** Populate `package_channel_downloads` from the existing `_phase_f_via_s3` parquet sweep — one additional group-by on the loaded pyarrow Table, same single-pass discipline as Wave 2 (§ 10 (g) + (h) of `atlas-phase-engineering.md`).
- **G5.** All three CLIs registered as MCP tools in `conda_forge_server.py` and as `pixi.toml` tasks.
- **G6.** Schema migration v27 → v28 is forward-only, idempotent, and follows the `INSERT OR REPLACE` semantic discipline from v8.18.1 § 10 (g) (DELETE + INSERT for breakdown tables on partial re-runs).

---

## Non-Goals

- **NG1.** No new external data sources. Wave 3 reads only from `cf_atlas.db` and the cached parquet (via the existing `_phase_f_via_s3` extension for `package_channel_downloads`).
- **NG2.** No "recommend python_min bump" auto-fixer. `pyver_breakdown --policy-check` surfaces the data; the maintainer decides.
- **NG3.** No dashboard / web UI. CLI + MCP tools only.
- **NG4.** No retro-fitting Wave 2 columns to per-channel resolution (`packages.downloads_90d` stays conda-forge-scoped; `package_channel_downloads` carries the per-channel cuts).
- **NG5.** No per-(package, channel, month) full time-series materialization. 90-day + lifetime totals only, same discipline as Wave 2.
- **NG6.** No write-side surface from any of the three CLIs. Read-only.

---

## User Stories

### Story 1 — Schema migration v27 → v28 + `package_channel_downloads` Wave 2 leftover

Add the new table to `SCHEMA_DDL`:

```sql
CREATE TABLE IF NOT EXISTS package_channel_downloads (
    conda_name        TEXT NOT NULL,
    data_source       TEXT NOT NULL,
    downloads_90d     INTEGER NOT NULL,
    downloads_total   INTEGER NOT NULL,
    fetched_at        INTEGER NOT NULL,
    PRIMARY KEY (conda_name, data_source)
);
CREATE INDEX IF NOT EXISTS idx_package_channel_downloads_conda_name
    ON package_channel_downloads(conda_name);
```

Bump `SCHEMA_VERSION` 27 → 28. Add v27 → v28 comment block to `init_schema`. No new `packages` columns. Migration is purely additive (CREATE TABLE IF NOT EXISTS).

**Force-refresh sentinel** (carried forward from v8.18.0 v26 → v27): the v27 → v28 migration writes `meta.phase_f_force_refresh_pending = '1'` so the first post-migration Phase F run re-aggregates the cached parquet and populates `package_channel_downloads` immediately.

### Story 2 — Extend `_phase_f_via_s3` with a per-(pkg, channel) group-by

In the same parquet sweep, group by `(pkg_name, data_source)` (i.e. raw parquet channel column) for:

- `downloads_90d` (last 3 months — same window as Wave 2)
- `downloads_total` (lifetime)

Bulk-write into `package_channel_downloads` using **DELETE-by-scope-key + INSERT OR REPLACE** in the same transaction (per v8.18.1 § 10 (g)). The DELETE pattern mirrors Wave 2's v8.18.0 H1 fix:

```sql
DELETE FROM package_channel_downloads WHERE conda_name IN (<chunked, 500-row batches>);
-- then bulk INSERT OR REPLACE for the new rows
```

**No new env vars.** No filter on `data_source` (unlike Wave 2's parquet sweep which filters to `'conda-forge'` for the main aggregations) — the channel breakdown intentionally captures all channels the parquet ships, including `defaults` / `bioconda` / `pytorch` / `nvidia` / etc.

### Story 3 — `platform_breakdown` CLI + MCP tool

**File**: `.claude/skills/conda-forge-expert/scripts/platform_breakdown.py` (canonical) + `.claude/scripts/conda-forge-expert/platform_breakdown.py` (thin wrapper).

**CLI surface**:

```
platform-breakdown <package>                                # one-package detail
platform-breakdown --top 50 --platform linux-aarch64        # rank packages by aarch64 share
platform-breakdown --top 50 --platform win-64               # ARM/win-64 share table
platform-breakdown --feedstock-roundup --maintainer X       # group by feedstock_name for maintainer triage
platform-breakdown --json                                   # machine output
```

**Output (single-package, default)**:

```
numpy — per-platform downloads (90d)
─────────────────────────────────────────────
Platform          90d downloads    Share
linux-64          1,234,567        62.3 %
linux-aarch64       234,567        11.8 %
osx-arm64           198,765        10.0 %
osx-64              112,345         5.7 %
win-64               98,765         5.0 %
noarch                5,432         0.3 %
─────────────────────────────────────────────
Total             1,984,441        100 %
```

Reads only from `cf_atlas.db` (`packages` join `package_platform_downloads`). Offline-safe.

### Story 4 — `pyver_breakdown` CLI + MCP tool incl. `--policy-check`

**File**: `.claude/skills/conda-forge-expert/scripts/pyver_breakdown.py` (canonical) + wrapper.

**Two-mode CLI**:

```
pyver-breakdown <package>                          # single-package python-version distribution
pyver-breakdown --policy-check <package>           # compare declared python_min vs. empirical floor
pyver-breakdown --policy-check --maintainer X      # batch policy-check across maintainer's feedstocks
pyver-breakdown --policy-check --threshold-pct 2.0 # change the "noise floor" (default 2 %)
```

**Single-package mode output**:

```
numpy — per-Python downloads (90d)
─────────────────────────────────────────────
Python            90d downloads    Share
3.12              1,234,567        62.3 %
3.11                567,890        28.7 %
3.10                123,456         6.2 %
3.13                 45,678         2.3 %
3.9                  10,234         0.5 %
─────────────────────────────────────────────
Empirical python_min floor (≥2%): 3.10
```

**Policy-check mode**:

For each package, read the recipe's declared `python_min` (via the existing recipe parser used by `validate_recipe.py`) AND compute the empirical floor (the smallest python with ≥`--threshold-pct` share of 90-day downloads). Flag packages where:

- `empirical_floor > declared_min` → **bump-safe candidate** (operator can raise the recipe's python_min without losing material adoption).
- `empirical_floor < declared_min` → **already-aggressive** (no action; recipe is already at or below the empirical floor).
- `empirical_floor == declared_min` → **aligned** (no action).

**Output (policy-check, default)**:

```
Python-min policy check — maintainer rxm7706
─────────────────────────────────────────────────────────────────
Feedstock              Declared    Empirical   Status         90d Δ
numpy                  3.10        3.11        bump-safe     -123k (3.10 share)
pandas                 3.10        3.10        aligned       —
some-niche             3.11        3.10        aggressive    +12k (3.10 share)
─────────────────────────────────────────────────────────────────
```

Reads from `packages` (declared `python_min` via recipe parser; cached column if available) + `package_python_downloads`.

### Story 5 — `channel_split` CLI + MCP tool

**File**: `.claude/skills/conda-forge-expert/scripts/channel_split.py` (canonical) + wrapper.

**CLI surface**:

```
channel-split <package>                          # single-package channel distribution
channel-split --defaults-share-min 10.0          # rank packages by defaults share (migration targets)
channel-split --defaults-share-min 10.0 --top 50 # top-50 by defaults share
channel-split --json
```

**Single-package output**:

```
matplotlib — per-channel downloads (90d)
─────────────────────────────────────────────
Channel           90d downloads    Share
conda-forge       2,345,678        72.1 %
defaults            567,890        17.5 %
bioconda            234,567         7.2 %
pytorch             100,000         3.1 %
nvidia                3,210         0.1 %
─────────────────────────────────────────────
Migration opportunity: 17.5 % on defaults — consider rerendering for cross-channel adoption.
```

**Top-50 mode**: list packages with `>= --defaults-share-min` defaults share, ranked by absolute defaults 90d downloads (not share — high-absolute-volume is the actionable target).

### Story 6 — Tests, docs, SKILL.md updates, MCP registration, CHANGELOG, retro

- **Unit tests** for each of the 3 new scripts: fixture DB with seeded data, assert table-output shape, assert `--json` payload, assert `--policy-check` correctly compares declared vs. empirical.
- **Schema migration test**: `tests/unit/test_schema_v28_migration.py` mirrors v27's pattern. Fresh DB / v27 → v28 upgrade / already-v28 idempotency cases. Asserts `SCHEMA_VERSION == 28` + new table exists.
- **Phase F dispatch test extension**: 1 new case in `TestS3ParquetWave2Metrics` (now arguably `TestS3ParquetWave2And3Metrics`) verifying `package_channel_downloads` populates with expected channel cuts after a sweep.
- **MCP registration** in `.claude/tools/conda_forge_server.py` for all 3 new tools, following the existing pattern (one decorator per tool, one wrapper function each).
- **`pixi.toml` tasks** for all 3 new CLIs (`platform-breakdown`, `pyver-breakdown`, `channel-split`).
- **Reference docs**: update `atlas-phases-overview.md` Phase F section with the new table; update `atlas-actionable-intelligence.md` — five rows for `platform_breakdown` modes + four rows for `pyver_breakdown` + two rows for `channel_split` all flip from `📋 open` to `✅ shipped (v8.19.0)`.
- **`SKILL.md` Atlas Intelligence Layer section** gains the three new CLIs in the "Daily-use CLIs" list.
- **`CHANGELOG.md`** v8.19.0 entry per Rule 2.
- **Retro** at `_bmad-output/projects/local-recipes/implementation-artifacts/retro-cfe-phase-f-wave3-<DATE>.md`.

---

## Functional Requirements

### FR-1: Read-only contract

All three CLIs read only from `cf_atlas.db`. No `urllib`, no `requests`, no network access at runtime. Verified by `grep -r "urllib\|requests" .claude/skills/conda-forge-expert/scripts/{platform_breakdown,pyver_breakdown,channel_split}.py` returning zero hits.

### FR-2: Offline-safe by atlas dependency

If the atlas DB is missing or stale, the CLIs print a clear error message pointing at `bootstrap-data --profile admin` and exit non-zero. No partial output.

### FR-3: `--json` machine output on all three

Every CLI supports `--json` and emits a stable, documented schema (list of records keyed by `conda_name` + dimension). Consumers should be able to pipe to `jq` and `gh` without parsing the markdown table.

### FR-4: `--policy-check` data freshness

`pyver_breakdown --policy-check` skips packages whose `package_python_downloads.fetched_at` is older than `PHASE_F_TTL_DAYS=7` and prints a "stale; run `bootstrap-data --profile admin` to refresh" notice. Threshold is per-package, not global.

### FR-5: Channel breakdown discipline (v8.18.1 § 10 (g))

`_phase_f_via_s3`'s new `package_channel_downloads` write uses **DELETE-by-scope-key + INSERT OR REPLACE** in the same transaction. Re-running Phase F replaces per-package channel rows, doesn't accumulate zombies when a channel's downloads drop to zero.

### FR-6: Provenance attribution (v8.18.1 § 10 (h))

The new `package_channel_downloads` rows are populated **only** when the parquet sweep runs (i.e. when `_phase_f_via_s3` writes the corresponding `packages.downloads_source='s3-parquet'`). The API-path fallback (`_phase_f_via_api`) does NOT touch `package_channel_downloads`. Verified by grepping the writers.

### FR-7: Schema migration safety

v27 → v28 runs cleanly on:
- Fresh DB (`--fresh`).
- Existing v27 DB (in-place upgrade — adds the new table).
- Already-v28 DB (idempotent no-op).

Per v8.18.1 § 10 (i), this Wave-3 ship goes through the step-04 three-reviewer adversarial pass.

---

## Technical Approach

### Where the code lands

- **`scripts/conda_forge_atlas.py`** — `SCHEMA_VERSION` bump 27 → 28; new `CREATE TABLE IF NOT EXISTS package_channel_downloads` in `SCHEMA_DDL`; v27 → v28 comment block; `_phase_f_via_s3` extended with one more group-by + DELETE+INSERT writer (mirrors v8.18.0's H1 pattern).
- **`scripts/platform_breakdown.py`** (NEW) — argparse + SQL queries + markdown formatter + `--json` mode.
- **`scripts/pyver_breakdown.py`** (NEW) — same pattern; `--policy-check` mode reads recipe's `python_min` (use the existing recipe parser from `validate_recipe.py` if helpful).
- **`scripts/channel_split.py`** (NEW) — same pattern; `--defaults-share-min` filter.
- **`.claude/scripts/conda-forge-expert/{platform_breakdown,pyver_breakdown,channel_split}.py`** — thin wrappers (5-line subprocess.run pattern as documented).
- **`pixi.toml`** — 3 new tasks.
- **`.claude/tools/conda_forge_server.py`** — 3 new MCP tool decorators.
- **`tests/unit/test_schema_v28_migration.py`** (NEW) — mirrors v27 test.
- **`tests/unit/test_platform_breakdown.py`** (NEW), **`tests/unit/test_pyver_breakdown.py`** (NEW), **`tests/unit/test_channel_split.py`** (NEW).
- **`tests/unit/test_phase_f_dispatch.py`** — 1 new case for `package_channel_downloads` write.

### Key implementation notes

- **Recipe parser for `--policy-check`**: prefer to read the cached `python_min` from `packages` (if Wave 2 or earlier stored it; if not, this becomes a Wave 4 issue). If not cached, parse `recipes/<name>/recipe.yaml` via the existing recipe parser. Document the fallback.
- **Channel-name normalization**: parquet ships `data_source` as raw channel string (e.g. `'conda-forge'`, `'defaults'`, `'bioconda'`). No normalization — write as-is. Consumers see exactly what the parquet has.
- **`platform_breakdown --top --platform`**: rank by **absolute 90d downloads on that platform**, not share. High-absolute-volume on a niche platform is the actionable signal (e.g. "this 50k-download-on-aarch64 package is one of the top-20 aarch64-loved packages").

### Env-var matrix

Wave 3 ships **no new env vars**. CLI flags are the only operator-tunable surface.

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** Schema migration v27 → v28 runs cleanly on fresh + existing v27 + already-v28 DBs; tests cover all three.
- **AC-2.** After `--profile admin` populates the DB, `package_channel_downloads` has ≥1 row per `(conda_name, 'conda-forge')` pair for packages with `downloads_source='s3-parquet'`.
- **AC-3.** `platform_breakdown numpy` (or any populated package) prints a markdown table with ≥3 platform rows + a Total line; `--json` returns a list of dicts with `conda_name`, `pkg_platform`, `downloads_90d`, `downloads_total`, `share_pct`.
- **AC-4.** `pyver_breakdown --policy-check <pkg>` flags ≥1 known bump-safe candidate from the seeded test fixture; categories are `bump-safe`, `aligned`, `aggressive`.
- **AC-5.** `channel_split --defaults-share-min 10.0 --top 10` returns ≤10 rows, each with `defaults_share_pct >= 10.0`, sorted by absolute 90d defaults downloads DESC.
- **AC-6.** All 3 CLIs registered as pixi tasks AND as MCP tools; `mcp list` shows them.
- **AC-7.** Test suite 1,386 → ≥1,410 passing (≥24 new tests across 3 CLI test files + schema migration test + dispatch extension). 0 failed, 0 errors.
- **AC-8.** Step-04 adversarial review pass runs (per v8.18.1 § 10 (i)); any HIGH/MED findings either auto-patched (`patch` classification) or pre-resolved (`bad_spec`/`intent_gap` triggers loopback to step-02).
- **AC-9.** Closeout per CLAUDE.md Rule 2: CHANGELOG v8.19.0 + retro artifact + actionable-intelligence catalog rows flipped to `✅ shipped (v8.19.0)`.

---

## Open Questions

### Pre-resolved (recommendations)

- **OQ-1.** Should `pyver_breakdown --policy-check` consume the recipe's declared `python_min` from the SQLite atlas (if cached) or always reparse `recipes/<name>/recipe.yaml`? **Recommendation: cached if available, fall back to reparse with a stale-warning if not.** Reparse on every `--policy-check` invocation would be slow for `--maintainer X` batch runs.

- **OQ-2.** Should `platform_breakdown --feedstock-roundup` group by `feedstock_name` (which exists on `packages`) or `conda_name` (one row per package)? **Recommendation: `feedstock_name`** — that's the maintainer's mental model (one feedstock = one rerender target).

- **OQ-3.** Should `channel_split` use the parquet's raw `data_source` strings or normalize to a canonical channel name (e.g. `'main'` vs `'defaults'`)? **Recommendation: raw, no normalization.** Consumers see exactly what the parquet has; if normalization is needed later, it lives in a Wave 4 layer.

- **OQ-4.** What's the noise floor for `--policy-check`? **Recommendation: 2 % default**, overridable via `--threshold-pct N.M`. Aligns with the parent spec's "smallest python with ≥2% downloads" definition.

### Genuinely open (design call — surface at intake)

- **OQ-5.** Should `pyver_breakdown --policy-check` also surface packages where the empirical floor is *strictly less than* the declared min (`aggressive` category)? Or hide them since the maintainer can't act ("already-good" feedback)? **Recommendation: surface but de-prioritize** — sort the output so `bump-safe` candidates appear first; `aggressive` rows are background information.

- **OQ-6.** Should the three CLIs share a common `--format markdown|json|csv` flag, or keep `--json` as the single non-default? **Recommendation: just `--json`** — CSV is rare for atlas consumers (most pipe to `jq`); a single flag is simpler.

- **OQ-7.** Should `channel_split` add a `--migration-checklist` mode that emits a markdown checklist suitable for pasting into a GitHub issue ("[ ] Open conda-forge feedstock for <pkg>; defaults has X% share")? **Recommendation: defer to Wave 4** — keep Wave 3 read-only and stick to numeric output.

---

## Dependencies and Constraints

- **`package_platform_downloads`** + **`package_python_downloads`** at v27 (shipped v8.18.0). Verified `SCHEMA_VERSION == 27` at start of Wave 3.
- **Wave 2's `_phase_f_via_s3` extension** — adds one more group-by + table write inside the same single-pass discipline.
- **`pyarrow`** — already in the `local-recipes` pixi env.
- **CLAUDE.md Rules 1 + 2** apply (CFE skill invocation + closeout retro).
- **v8.18.1 § 10 (g), (h), (i)** apply — Wave 3 has both a many-to-many breakdown table (DELETE + INSERT) and a new write target (provenance-attribution discipline).

---

## Out of Scope (Explicit)

- **OoS-1.** Wave 4 features: `--migration-checklist` mode; recipe-edit automation; per-channel time-series; per-channel rolling window cuts. All deferred.
- **OoS-2.** Per-month time-series data — Wave 3 keeps 90d + lifetime totals only, same discipline as Wave 2.
- **OoS-3.** Non-CLI consumers (dashboards, web UIs). MCP tools count as machine consumers; UI is downstream's job.
- **OoS-4.** Channel-name normalization (parquet's raw `data_source` strings are written as-is; future normalization is Wave 4).
- **OoS-5.** Write-side automation: `pyver_breakdown --policy-check` flags candidates; it does NOT edit recipes or open PRs. The maintainer decides.

---

## References

### Parent specs (source of truth for detail)

- [`docs/specs/atlas-phase-f-s3-backend.md`](#part-1) — Wave 0-3 full design. Wave 3 = Stories 11/12/13/14.
- [`docs/specs/atlas-phase-f-wave2-richer-metrics.md`](#part-2) — Wave 2 brief (shipped v8.18.0).

### Code (entry points)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` — `SCHEMA_VERSION` (bump), `SCHEMA_DDL` (new table), `_phase_f_via_s3` (extend with channel group-by + DELETE+INSERT).
- `.claude/skills/conda-forge-expert/scripts/{platform_breakdown,pyver_breakdown,channel_split}.py` — NEW.
- `.claude/scripts/conda-forge-expert/{platform_breakdown,pyver_breakdown,channel_split}.py` — NEW wrappers.
- `.claude/tools/conda_forge_server.py` — 3 new MCP tool decorators.

### Tests

- `.claude/skills/conda-forge-expert/tests/unit/test_schema_v28_migration.py` — NEW.
- `.claude/skills/conda-forge-expert/tests/unit/test_{platform_breakdown,pyver_breakdown,channel_split}.py` — NEW.
- `.claude/skills/conda-forge-expert/tests/unit/test_phase_f_dispatch.py` — 1 new case for `package_channel_downloads` write.

### Documentation to update

- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` — Phase F section.
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md` — ~11 new rows flipped to `✅ shipped (v8.19.0)`.
- `.claude/skills/conda-forge-expert/SKILL.md` Atlas Intelligence Layer — three new CLIs in the daily-use list.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — v8.19.0 entry.
- `.claude/skills/conda-forge-expert/config/skill-config.yaml` — version bump.
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` — three new CLI examples.
- `pixi.toml` — 3 new tasks.
